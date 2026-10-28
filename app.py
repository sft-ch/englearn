#!/usr/bin/env python3
"""Englearn：本地英语精读助手。

启动后访问 http://127.0.0.1:8765 ，在任意软件中选中英文按 Ctrl+Alt+D 即可取词分析。
"""

from __future__ import annotations

import argparse
import ctypes
import json
import mimetypes
import os
import queue
import re
import socket
import sys
import threading
import time
import traceback
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import analyze as analyzer          # noqa: E402
from core import autostart, capture, config, export, mousehook, store  # noqa: E402
from core.llm import LLMError                 # noqa: E402

WEB_DIR = ROOT / "web"
# 允许用 ENGL_DATA_DIR 指向另一份数据目录（教程截图、多实例调试时用）
DATA_DIR = Path(os.environ.get("ENGL_DATA_DIR") or (ROOT / "data"))
LOG_DIR = ROOT / "logs"
VERSION = "0.1.0"


class EventBus:
    """把热键触发的分析结果推给所有打开的前端页面。"""

    def __init__(self) -> None:
        self._subs: set[queue.Queue] = set()
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=200)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            self._subs.discard(q)

    def publish(self, event: dict) -> None:
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass


class App:
    def __init__(self, cfg: dict, force_mock: bool = False) -> None:
        self.cfg = cfg
        self.force_mock = force_mock
        self.bus = EventBus()
        self.store = store.Store(DATA_DIR / "app.db")
        self.hotkey: capture.HotkeyListener | None = None
        self.watcher: capture.ClipboardWatcher | None = None
        self.popup = None
        self.mouse: mousehook.MouseWatcher | None = None
        self.tk_root = None
        self.sel_queue: queue.Queue = queue.Queue()

    @property
    def mock(self) -> bool:
        return bool(self.force_mock or self.cfg.get("mock"))

    # ---------- 分析 ----------
    def analyze_text(self, text: str, mode: str = "auto", source: str = "",
                     publish: bool = False) -> dict:
        text = (text or "").strip()
        if not text:
            raise ValueError("文本为空")
        limit = int(self.cfg.get("max_chars", 4000))
        if len(text) > limit:
            raise ValueError(f"文本过长（{len(text)} 字符，上限 {limit}）")
        started = time.time()
        run_cfg = dict(self.cfg)
        run_cfg["mock"] = self.mock
        data = analyzer.analyze(run_cfg, text, mode)
        record = self.store.add_record(data.get("type", "sentence"), text, source, data)
        result = {
            "data": data,
            "record": record,
            "elapsed": round(time.time() - started, 2),
            "source": source,
        }
        if publish:
            self.bus.publish({"type": "result", **result})
        return result

    def _hotkey_flow(self) -> None:
        try:
            text = capture.capture_selection()
            if not text:
                self.bus.publish({
                    "type": "error",
                    "message": "没有捕获到选中文本：请先在其他软件里选中英文，再按热键",
                })
                return
            if self.popup is not None:
                x, y = mousehook.cursor_pos()
                self.popup.submit(text, x, y)
                return
            self.analyze_text(text, source="划词", publish=True)
        except (LLMError, ValueError) as exc:
            self.bus.publish({"type": "error", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.bus.publish({"type": "error", "message": f"分析失败：{exc}"})

    # ---------- 热键 / 剪贴板 ----------
    FALLBACK_HOTKEYS = ("alt+q", "ctrl+alt+e", "alt+shift+z", "ctrl+alt+d")

    def start_hotkey(self) -> None:
        if not capture.IS_WINDOWS or not self.cfg.get("hotkey"):
            return

        def trigger() -> None:
            threading.Thread(target=self._hotkey_flow, daemon=True).start()

        wanted = str(self.cfg.get("hotkey")).lower()
        candidates = [wanted] + [c for c in self.FALLBACK_HOTKEYS if c != wanted]
        for combo in candidates:
            listener = capture.HotkeyListener(
                {combo: trigger},
                on_error=lambda msg: self.bus.publish({"type": "error", "message": msg}),
            )
            listener.start()
            listener.ready.wait(1.0)
            if listener.registered:
                self.hotkey = listener
                self.cfg["hotkey"] = combo
                if combo != wanted:
                    print(f"[Englearn] 热键 {wanted} 已被占用，自动改用 {combo}")
                return
            listener.stop()
        self.bus.publish({
            "type": "error",
            "message": "全局热键注册失败，可改用页面上的「取选区」按钮",
        })

    def start_watcher(self) -> None:
        if not capture.IS_WINDOWS:
            return

        def on_clip(text: str) -> None:
            try:
                self.analyze_text(text, source="剪贴板", publish=True)
            except (LLMError, ValueError) as exc:
                self.bus.publish({"type": "error", "message": str(exc)})

        self.watcher = capture.ClipboardWatcher(on_clip)
        self.watcher.enabled = bool(self.cfg.get("clipboard_watch"))
        self.watcher.start()

    # ---------- 划词悬浮窗 ----------
    def start_popup(self, host: str, port: int) -> None:
        import tkinter as tk

        from core.popup import PopupController

        _enable_dpi()
        root = tk.Tk()
        root.withdraw()
        root.title("Englearn")
        self.tk_root = root
        self.popup = PopupController(
            root, f"http://{host}:{port}",
            max_chars=int(self.cfg.get("max_chars", 4000)),
        )
        threading.Thread(
            target=self._selection_worker, daemon=True, name="englearn-select"
        ).start()
        self.mouse = mousehook.MouseWatcher(
            on_select=lambda x, y: self.sel_queue.put((x, y)),
            on_press=self.popup.handle_press,
        )
        self.mouse.start()

    def _selection_worker(self) -> None:
        limit = int(self.cfg.get("max_chars", 4000))
        while True:
            x, y = self.sel_queue.get()
            try:
                time.sleep(0.12)  # 等目标程序把选区定下来
                if mousehook.point_is_own_process(x, y):
                    continue
                if mousehook.window_class_at(x, y) in mousehook.SKIP_CLASSES:
                    continue
                text = (capture.capture_selection() or "").strip()
                if not text or len(text) > limit:
                    continue
                if not re.search(r"[A-Za-z]", text):
                    continue
                if self.popup is not None:
                    self.popup.submit(text, x, y)
            except Exception:  # noqa: BLE001
                traceback.print_exc()


def _enable_dpi() -> None:
    """让 Tk 在 125%/150% 缩放下也是清晰的，必须在创建 Tk 之前调用。"""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass


class EnglearnServer(ThreadingHTTPServer):
    """浏览器握手被中途关闭属于常态，不需要打印堆栈。"""

    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address) -> None:
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    app: App
    server_version = "Englearn/" + VERSION
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # 静默访问日志
        pass

    # ---------- 工具 ----------
    def _send(self, code: int, body, ctype: str = "application/json; charset=utf-8") -> None:
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _ok(self, **payload) -> None:
        self._send(200, {"ok": True, **payload})

    def _fail(self, code: int, message: str) -> None:
        self._send(code, {"ok": False, "error": message})

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}

    # ---------- GET ----------
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)
        try:
            if path == "/api/health":
                llm = self.app.cfg.get("llm") or {}
                self._ok(
                    version=VERSION,
                    mock=self.app.mock,
                    has_key=bool((llm.get("api_key") or "").strip()),
                    model=llm.get("model", ""),
                    hotkey=self.app.cfg.get("hotkey", ""),
                    popup=self.app.popup is not None,
                    autostart=autostart.is_enabled(),
                    platform=sys.platform,
                    stats=self.app.store.stats(),
                )
                return
            if path == "/api/config":
                view = config.public_view(self.app.cfg)
                view["autostart"] = autostart.is_enabled()
                view["autostart_supported"] = autostart.supported()
                self._ok(config=view)
                return
            if path == "/api/words":
                self._ok(
                    words=self.app.store.words(
                        q=(qs.get("q") or [""])[0],
                        status=(qs.get("status") or [""])[0],
                        kind=(qs.get("kind") or [""])[0],
                    ),
                    kinds=self.app.store.word_kind_counts(),
                )
                return
            if path == "/api/history":
                limit = int((qs.get("limit") or ["60"])[0])
                self._ok(records=self.app.store.records(
                    limit=limit, q=(qs.get("q") or [""])[0]))
                return
            if path == "/api/sentences":
                rows = self.app.store.sentences(limit=200)
                for row in rows:
                    row["analysis"] = json.loads(row.get("analysis") or "{}")
                    row["marks"] = json.loads(row.get("marks") or "[]")
                self._ok(sentences=rows)
                return
            if path == "/api/day":
                day = (qs.get("date") or [""])[0] or datetime.now().strftime("%Y-%m-%d")
                sents = self.app.store.sentences_on(day)
                for row in sents:
                    row["analysis"] = json.loads(row.get("analysis") or "{}")
                    row["marks"] = json.loads(row.get("marks") or "[]")
                self._ok(
                    date=day,
                    words=self.app.store.words_on(day),
                    sentences=sents,
                    records=self.app.store.records_on(day, limit=100),
                    days=self.app.store.days(90),
                )
                return
            if path.startswith("/api/words/"):
                try:
                    wid = int(path.rsplit("/", 1)[-1])
                except ValueError:
                    self._fail(400, "无效的单词编号")
                    return
                word = self.app.store.word(wid)
                if not word:
                    self._fail(404, "单词不存在")
                    return
                self._ok(word=word)
                return
            if path == "/api/stats":
                self._ok(stats=self.app.store.stats())
                return
            if path == "/api/events":
                self._sse()
                return
            self._static(path)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._fail(500, str(exc))

    # ---------- POST / PATCH / DELETE ----------
    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/analyze":
                result = self.app.analyze_text(
                    body.get("text", ""), body.get("mode", "auto"),
                    body.get("source", "手动"), publish=bool(body.get("publish")))
                self._ok(**result)
                return
            if path == "/api/capture":
                text = capture.capture_selection()
                if not text:
                    self._fail(400, "没有捕获到选中文本，请先在目标软件中选中英文")
                    return
                self._ok(text=text)
                return
            if path == "/api/words":
                payload = body.get("payload")
                source = body.get("source", "")
                if body.get("record_id"):
                    rec = self.app.store.record(int(body["record_id"]))
                    if not rec:
                        self._fail(404, "记录不存在")
                        return
                    payload = json.loads(rec["payload"])
                    source = source or rec["text"]
                if not isinstance(payload, dict):
                    self._fail(400, "缺少 payload")
                    return
                word = self.app.store.save_word(payload, source=source)
                self._ok(word=word)
                return
            if path == "/api/sentences":
                if not body.get("record_id"):
                    self._fail(400, "缺少 record_id")
                    return
                rec = self.app.store.record(int(body["record_id"]))
                if not rec:
                    self._fail(404, "记录不存在")
                    return
                payload = json.loads(rec["payload"])
                sentence = self.app.store.save_sentence(
                    rec["text"], payload.get("translation", ""), payload, source=rec["text"]
                )
                self._ok(sentence=sentence)
                return
            if path == "/api/export":
                result = export.write_export(self.app.store, body.get("format", "md"))
                self._ok(**result)
                return
            if path == "/api/config":
                self._update_config(body)
                return
            self._fail(404, "未知接口")
        except (LLMError, ValueError) as exc:
            self._fail(400, str(exc))
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._fail(500, str(exc))

    def do_PATCH(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path.startswith("/api/words/"):
                wid = int(path.rsplit("/", 1)[-1])
                word = self.app.store.update_word(wid, self._body())
                if not word:
                    self._fail(404, "单词不存在")
                    return
                self._ok(word=word)
                return
            if path.startswith("/api/sentences/"):
                sid = int(path.rsplit("/", 1)[-1])
                body = self._body()
                if not isinstance(body.get("marks"), list):
                    self._fail(400, "缺少 marks 列表")
                    return
                row = self.app.store.update_sentence_marks(sid, body["marks"])
                if not row:
                    self._fail(404, "句子不存在")
                    return
                row["analysis"] = json.loads(row.get("analysis") or "{}")
                row["marks"] = json.loads(row.get("marks") or "[]")
                self._ok(sentence=row)
                return
            self._fail(404, "未知接口")
        except ValueError as exc:
            self._fail(400, str(exc))

    def do_DELETE(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/api/words/"):
            self.app.store.delete_word(int(path.rsplit("/", 1)[-1]))
            self._ok()
            return
        if path.startswith("/api/history/"):
            self.app.store.delete_record(int(path.rsplit("/", 1)[-1]))
            self._ok()
            return
        if path.startswith("/api/sentences/"):
            self.app.store.delete_sentence(int(path.rsplit("/", 1)[-1]))
            self._ok()
            return
        self._fail(404, "未知接口")

    # ---------- 内部 ----------
    def _update_config(self, body: dict) -> None:
        cfg = self.app.cfg
        llm_in = body.get("llm") or {}
        for key in ("base_url", "model", "api_key"):
            if key in llm_in and isinstance(llm_in[key], str):
                if key == "api_key" and llm_in[key].strip() == "":
                    continue  # 留空表示不修改
                cfg.setdefault("llm", {})[key] = llm_in[key].strip()
        if "hotkey" in body and isinstance(body["hotkey"], str) and body["hotkey"].strip():
            cfg["hotkey"] = body["hotkey"].strip().lower()
        if "clipboard_watch" in body:
            cfg["clipboard_watch"] = bool(body["clipboard_watch"])
            if self.app.watcher:
                self.app.watcher.enabled = cfg["clipboard_watch"]
                if cfg["clipboard_watch"]:
                    self.app.watcher.mark_current()
        if "mock" in body:
            cfg["mock"] = bool(body["mock"])
        if "autostart" in body:
            try:
                if body["autostart"]:
                    autostart.enable()
                else:
                    autostart.disable()
            except Exception as exc:  # noqa: BLE001
                self._fail(400, f"设置开机自启失败：{exc}")
                return
        config.save(cfg)
        restart = "hotkey" in body and body.get("hotkey")
        view = config.public_view(cfg)
        view["autostart"] = autostart.is_enabled()
        view["autostart_supported"] = autostart.supported()
        self._ok(config=view, restart_required=bool(restart))

    def _static(self, path: str) -> None:
        if path in ("/", ""):
            rel = "index.html"
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
        else:
            self._fail(404, "not found")
            return
        target = (WEB_DIR / rel).resolve()
        if WEB_DIR.resolve() not in target.parents:
            self._fail(403, "forbidden")
            return
        if not target.is_file():
            self._fail(404, "not found")
            return
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)

    def _sse(self) -> None:
        q = self.app.bus.subscribe()
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
            while True:
                try:
                    event = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                payload = json.dumps(event, ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.app.bus.unsubscribe(q)


def serve(host: str, port: int, open_browser: bool, mock: bool,
          no_hotkey: bool = False, no_popup: bool = False) -> None:
    cfg = config.load()
    if no_hotkey:
        cfg["hotkey"] = ""
    if not config.CONFIG_PATH.exists():
        config.save(cfg)

    app = App(cfg, force_mock=mock)
    Handler.app = app

    httpd = None
    for candidate in range(port, port + 10):
        try:
            httpd = EnglearnServer((host, candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    if httpd is None:
        raise SystemExit(f"端口 {port}~{port + 9} 都被占用，请用 --port 指定其他端口")

    # 先让 HTTP 服务真正开始接受连接，再打开浏览器，避免白屏
    threading.Thread(target=httpd.serve_forever, daemon=True, name="englearn-http").start()
    _wait_ready(host, port)

    url = f"http://{host}:{port}"
    print("=" * 56)
    print(f"  Englearn v{VERSION} 已启动")
    print(f"  地址：{url}")
    print(f"  模式：{'MOCK 演示' if app.mock else '真实模型'}"
          f"　模型：{(cfg.get('llm') or {}).get('model', '')}")
    print("  关闭本窗口或按 Ctrl+C 即可退出")
    print("=" * 56, flush=True)

    if open_browser:
        webbrowser.open(url)

    app.start_hotkey()
    app.start_watcher()
    print(f"  热键：{cfg.get('hotkey', 'alt+d')}（选中英文后按下取词）", flush=True)

    popup_ok = False
    if not no_popup and bool(cfg.get("select_popup", True)) and sys.platform == "win32":
        try:
            app.start_popup(host, port)
            popup_ok = True
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            print(f"  划词悬浮窗启动失败：{exc}（退回页面推送模式）", flush=True)

    if popup_ok:
        print("  划词：选中英文后鼠标旁会弹出操作窗，点窗外或 Esc 关闭", flush=True)
        try:
            app.tk_root.mainloop()
        except KeyboardInterrupt:
            print("\n正在退出…")
    else:
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n正在退出…")
    try:
        if app.mouse:
            app.mouse.stop()
        if app.hotkey:
            app.hotkey.stop()
        if app.watcher:
            app.watcher.stop()
        if app.tk_root:
            app.tk_root.destroy()
    except Exception:  # noqa: BLE001
        pass
    httpd.shutdown()
    httpd.server_close()


def _wait_ready(host: str, port: int, timeout: float = 5.0) -> bool:
    """等端口真正可连，最多等 timeout 秒。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _install_crash_log() -> None:
    def hook(exc_type, exc, tb) -> None:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_DIR / "error.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n")
                traceback.print_exception(exc_type, exc, tb, file=f)
        except Exception:  # noqa: BLE001
            pass
        traceback.print_exception(exc_type, exc, tb)

    sys.excepthook = hook


def main() -> None:
    _install_crash_log()
    parser = argparse.ArgumentParser(prog="englearn", description="本地英语精读助手")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--mock", action="store_true", help="使用离线演示数据")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--no-hotkey", action="store_true", help="不注册全局热键")
    parser.add_argument("--no-popup", action="store_true", help="不启用划词悬浮窗")
    sub = parser.add_subparsers(dest="cmd")
    ex = sub.add_parser("export", help="命令行导出")
    ex.add_argument("--format", default="md", choices=["md", "json", "csv", "anki", "html"])
    args = parser.parse_args()

    cfg = config.load()

    if args.cmd == "export":
        st = store.Store(DATA_DIR / "app.db")
        result = export.write_export(st, args.format)
        print(f"已导出：{result['path']}")
        return

    host = args.host or cfg.get("host", "127.0.0.1")
    port = args.port or int(cfg.get("port", 8765))
    serve(host, port, open_browser=not args.no_open, mock=args.mock,
          no_hotkey=args.no_hotkey, no_popup=args.no_popup)


if __name__ == "__main__":
    main()
