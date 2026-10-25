"""鼠标旁的操作悬浮窗（Tkinter，标准库实现）。

交互：选中英文 → 鼠标旁弹出小窗 → 选择「翻译 / 长难句 / 收藏 / 页面」。
窗口本身不抢焦点，点击窗外任意位置即关闭。
"""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
import urllib.request

BG = "#ffffff"
FG = "#1b2421"
MUTED = "#7c8a85"
ACCENT = "#10a37f"
ACCENT_DARK = "#0b7f63"
SOFT = "#f6f8f7"
BORDER = "#dfe7e4"
DANGER = "#b03a2e"

FONT = ("Microsoft YaHei", 9)
FONT_BOLD = ("Microsoft YaHei", 9, "bold")
FONT_SMALL = ("Microsoft YaHei", 8)

KIND_LABEL = {"word": "单词", "phrase": "短语", "sentence": "句子"}


class PopupController:
    def __init__(self, root: tk.Tk, base_url: str, max_chars: int = 4000) -> None:
        self.root = root
        self.base_url = base_url.rstrip("/")
        self.max_chars = max_chars
        self.win: tk.Toplevel | None = None
        self.bounds = (0, 0, 0, 0)
        self.text = ""
        self.analysis: dict | None = None
        self._busy = False

        dpi = root.winfo_fpixels("1i")
        self.s = max(1.0, dpi / 96.0)
        root.tk.call("tk", "scaling", dpi / 72.0)

        self._inbox: queue.Queue = queue.Queue()
        self._ui_queue: queue.Queue = queue.Queue()
        self._timer: str | None = None
        root.after(40, self._poll)

    # ---------------- 对外接口（线程安全） ----------------
    def submit(self, text: str, x: int, y: int) -> None:
        self._inbox.put((text.strip(), x, y))

    def handle_press(self, x: int, y: int) -> None:
        """鼠标在别处按下：收起窗口。"""
        if self.win is None:
            return
        left, top, right, bottom = self.bounds
        if not (left <= x <= right and top <= y <= bottom):
            self._ui_queue.put(self.close)

    def close(self) -> None:
        if self._timer:
            self.root.after_cancel(self._timer)
            self._timer = None
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
            self.bounds = (0, 0, 0, 0)
        self.analysis = None
        self._busy = False

    # ---------------- 事件循环 ----------------
    def _poll(self) -> None:
        try:
            while True:
                fn = self._ui_queue.get_nowait()
                try:
                    fn()
                except Exception:  # noqa: BLE001
                    import traceback

                    traceback.print_exc()
        except queue.Empty:
            pass
        try:
            while True:
                text, x, y = self._inbox.get_nowait()
                self._open(text, x, y)
        except queue.Empty:
            pass
        self.root.after(40, self._poll)

    # ---------------- 构建窗口 ----------------
    def _open(self, text: str, x: int, y: int) -> None:
        self.close()
        if not text:
            return
        self.text = text

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(bg=BORDER)

        body = tk.Frame(win, bg=BG, padx=int(12 * self.s), pady=int(10 * self.s))
        body.pack(padx=1, pady=1, fill="both", expand=True)

        head = tk.Frame(body, bg=BG)
        head.pack(fill="x")
        kind = "选中文本"
        tk.Label(
            head, text=kind, bg=BG, fg=MUTED, font=FONT_SMALL, anchor="w"
        ).pack(side="left")
        close_btn = tk.Label(
            head, text="✕", bg=BG, fg="#a9b5b1", font=FONT_SMALL, cursor="hand2"
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda _e: self.close())

        preview = text if len(text) <= 70 else text[:70] + "…"
        tk.Label(
            body, text=preview, bg=BG, fg=FG, font=FONT, anchor="w", justify="left",
            wraplength=int(320 * self.s),
        ).pack(fill="x", pady=(2, 8))

        row = tk.Frame(body, bg=BG)
        row.pack(fill="x")
        self._button(row, "翻译", self._act_translate, primary=True).pack(side="left")
        self._button(row, "长难句", self._act_structure).pack(side="left", padx=(6, 0))
        self._button(row, "收藏", self._act_save).pack(side="left", padx=(6, 0))
        self._button(row, "页面", self._act_page).pack(side="left", padx=(6, 0))

        self.result = tk.Label(
            body, text="", bg=BG, fg="#40504a", font=FONT, anchor="w",
            justify="left", wraplength=int(320 * self.s),
        )
        self.win = win
        self._place(win, x, y)
        self._timer = self.root.after(25000, self.close)

    def _button(self, parent, text, command, primary=False):
        bg = ACCENT if primary else SOFT
        fg = "#ffffff" if primary else "#40504a"
        active = ACCENT_DARK if primary else "#e8eeec"
        btn = tk.Button(
            parent, text=text, command=command, relief="flat", bd=0,
            bg=bg, fg=fg, activebackground=active, activeforeground=fg,
            font=FONT, padx=int(10 * self.s), pady=int(3 * self.s), cursor="hand2",
        )
        return btn

    def _place(self, win: tk.Toplevel, x: int, y: int) -> None:
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        px = min(max(8, x + int(16 * self.s)), max(8, sw - w - 8))
        py = min(max(8, y + int(18 * self.s)), max(8, sh - h - 8))
        self._geometry(win, px, py)

    def _geometry(self, win: tk.Toplevel, px: int, py: int) -> None:
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        win.geometry(f"+{px}+{py}")
        self.bounds = (px, py, px + w, py + h)

    # ---------------- 动作 ----------------
    def _set_result(self, text: str, color: str = "#40504a") -> None:
        if self.win is None:
            return
        self.result.configure(text=text, fg=color)
        self.result.pack(fill="x", pady=(8, 0))
        self._geometry(self.win, self.bounds[0], self.bounds[1])

    def _act_translate(self) -> None:
        self._ensure(lambda d: self._set_result(self._translation_text(d)))

    def _act_structure(self) -> None:
        self._ensure(lambda d: self._set_result(self._structure_text(d)))

    def _act_save(self) -> None:
        def done(d):
            kind = d.get("type", "word")
            rid = (d.get("_record") or {}).get("id")
            if not rid:
                self._set_result("保存失败：缺少记录编号", DANGER)
                return
            path = "/api/sentences" if kind == "sentence" else "/api/words"
            self.request(path, {"record_id": rid}, lambda r: self._set_result(
                "句子已收藏" if kind == "sentence" else f"已加入生词本：{r['word']['lemma']}"
            ), lambda e: self._set_result(e, DANGER))

        self._ensure(done)

    def _act_page(self) -> None:
        def done(_d):
            import webbrowser

            webbrowser.open(self.base_url)
            self._set_result("已推送到页面，切到浏览器查看")
        self._ensure(done, publish=True)

    # ---------------- 文案 ----------------
    @staticmethod
    def _translation_text(data: dict) -> str:
        if data.get("type") in ("word", "phrase"):
            senses = data.get("senses") or []
            if senses:
                return "\n".join(
                    f"{s.get('pos', '')} {s.get('meaning', '')}".strip()
                    for s in senses[:3]
                )
        return data.get("translation") or "（没有返回译文）"

    @staticmethod
    def _structure_text(data: dict) -> str:
        st = data.get("structure") or {}
        if not st.get("main") and not st.get("clauses"):
            return data.get("translation") or "这是一句话，点「翻译」查看译文"
        lines = []
        if st.get("main"):
            lines.append("主干：" + st["main"])
        for c in (st.get("clauses") or [])[:2]:
            lines.append(f"{c.get('type', '从句')}：{c.get('text', '')}")
        if st.get("difficulty"):
            lines.append("难点：" + st["difficulty"])
        return "\n".join(lines)

    # ---------------- 请求 ----------------
    def _ensure(self, on_ok, publish: bool = True) -> None:
        if self._busy:
            return
        if self.analysis is not None:
            on_ok(self.analysis)
            return
        self._busy = True
        self._set_result("分析中…", MUTED)

        def ok(data):
            self._busy = False
            self.analysis = data
            on_ok(data)

        def err(msg):
            self._busy = False
            self._set_result(msg, DANGER)

        self.request(
            "/api/analyze",
            {"text": self.text, "mode": "auto", "publish": publish, "source": "划词"},
            lambda r: ok(dict(r["data"], _record=r.get("record"))),
            err,
        )

    def request(self, path: str, payload: dict, on_ok, on_err) -> None:
        url = self.base_url + path

        def work() -> None:
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=90) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                if not raw.get("ok"):
                    raise RuntimeError(raw.get("error") or "请求失败")
                self._ui_queue.put(lambda: on_ok(raw))
            except Exception as exc:  # noqa: BLE001
                msg = str(exc) or "网络错误"
                self._ui_queue.put(lambda m=msg: on_err(m))

        threading.Thread(target=work, daemon=True).start()
