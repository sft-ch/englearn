"""用无头 Chrome + CDP 给 Englearn 界面截图（教程配图）。

用法：先启动服务（python app.py --mock --no-open --no-hotkey），再运行本脚本。
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "images"
PROFILE = ROOT / "docs" / ".chrome-profile"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEBUG_PORT = 9333
BASE = "http://127.0.0.1:8899"


class WS:
    """够用就好的 WebSocket 客户端（只处理文本帧）。"""

    def __init__(self, url: str) -> None:
        assert url.startswith("ws://")
        hostport, path = url[5:].split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("WebSocket 握手失败")
            buf += chunk
        if b"101" not in buf.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"握手未升级：{buf[:120]!r}")
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self.next_id = 1

    def _exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("连接已关闭")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text: str) -> None:
        payload = text.encode()
        header = bytearray([0x81])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def recv(self) -> str:
        while True:
            b1, b2 = self._exact(2)
            opcode, masked = b1 & 0x0F, b2 & 0x80
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._exact(8))[0]
            mask = self._exact(4) if masked else b""
            data = self._exact(n)
            if masked:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if opcode == 0x1:
                return data.decode()
            if opcode == 0x8:
                raise ConnectionError("服务端关闭连接")
            # ping/pong/其他帧忽略


class CDP:
    def __init__(self, ws_url: str) -> None:
        self.ws = WS(ws_url)

    def call(self, method: str, params: dict | None = None, timeout: float = 30) -> dict:
        mid = self.ws.next_id
        self.ws.next_id += 1
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method} 失败：{msg['error']}")
                return msg.get("result", {})
        raise TimeoutError(method)

    def js(self, expression: str, await_promise: bool = False):
        r = self.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        })
        if "exceptionDetails" in r:
            raise RuntimeError(f"JS 异常：{r['exceptionDetails']}")
        return r.get("result", {}).get("value")

    def wait_js(self, expression: str, timeout: float = 20) -> None:
        end = time.time() + timeout
        while time.time() < end:
            if self.js(expression):
                return
            time.sleep(0.15)
        raise TimeoutError(f"等待超时：{expression}")


def launch_chrome() -> subprocess.Popen:
    if PROFILE.exists():
        shutil.rmtree(PROFILE, ignore_errors=True)
    proc = subprocess.Popen(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={PROFILE}",
            "--window-size=1440,920",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(80):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=1):
                return proc
        except OSError:
            time.sleep(0.25)
    raise RuntimeError("Chrome 调试端口未就绪")


def page_ws_url() -> str:
    with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json/list", timeout=5) as r:
        targets = json.loads(r.read().decode())
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("没有可用的页面目标")


def crop_bottom(path: Path, margin: int = 28, x_frac: float = 0.68) -> None:
    """裁掉图片底部（左栏）的纯背景区域。"""
    from PIL import Image

    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    bg = px[2, h - 2]
    x_max = int(w * x_frac)
    last = h - 1
    for y in range(h - 2, 0, -6):
        if any(px[x, y] != bg for x in range(0, x_max, 11)):
            last = y
            break
    new_h = min(h, last + margin)
    if new_h < h - 4:
        im.crop((0, 0, w, new_h)).save(path)
        print(f"    crop -> {w}x{new_h}")


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    proc = launch_chrome()
    try:
        cdp = CDP(page_ws_url())
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")
        cdp.call("Emulation.setDeviceMetricsOverride", {
            "width": 1440, "height": 920, "deviceScaleFactor": 1.5, "mobile": False,
        })
        cdp.call("Page.navigate", {"url": BASE + "/"})
        cdp.wait_js("document.readyState === 'complete'")
        cdp.wait_js("!!document.querySelector('#list')")
        time.sleep(1.5)

        def shot(name: str) -> None:
            data = base64.b64decode(cdp.call("Page.captureScreenshot", {"format": "png"})["data"])
            path = SHOTS / f"{name}.png"
            path.write_bytes(data)
            print(f"  {name}.png  {len(data) // 1024} KB")

        # 1 主界面
        shot("01-main")

        # 2 设置弹窗
        cdp.js("document.querySelector('#btn-settings').click()")
        cdp.wait_js("!document.querySelector('#modal').classList.contains('hidden')")
        time.sleep(0.4)
        shot("02-settings")
        cdp.js("document.querySelector('#btn-close').click()")
        time.sleep(0.3)

        # 3 单词结果：从历史里点开
        cdp.js("""document.querySelector('[data-tab="history"]').click()""")
        time.sleep(0.4)
        cdp.js("""(() => {
            const el = [...document.querySelectorAll('#list [data-rec-id]')]
                .find(e => e.textContent.includes('ubiquitous'));
            if (el) el.click();
            return !!el;
        })()""")
        cdp.wait_js("!!document.querySelector('#result .res-title')")
        time.sleep(0.5)
        shot("03-word")

        # 4 长难句结果（临时加高视口 + 卡片自适应高度，让整段结构一屏装下）
        cdp.call("Emulation.setDeviceMetricsOverride", {
            "width": 1440, "height": 1500, "deviceScaleFactor": 1.5, "mobile": False,
        })
        cdp.js("""(() => {
            const el = [...document.querySelectorAll('#list [data-rec-id]')]
                .find(e => e.textContent.includes('The committee'));
            if (el) el.click();
            return !!el;
        })()""")
        cdp.wait_js("!!document.querySelector('#result .struct-main')")
        cdp.js("""(() => {
            const r = document.querySelector('#result');
            r.style.flex = '0 0 auto';
            r.style.height = 'auto';
            r.style.overflow = 'visible';
            return true;
        })()""")
        time.sleep(0.4)
        content_h = cdp.js("""(() => {
            const el = document.querySelector('#result');
            return Math.ceil(el.getBoundingClientRect().bottom) + 34;
        })()""")
        cdp.call("Emulation.setDeviceMetricsOverride", {
            "width": 1440, "height": min(int(content_h) + 12, 2400),
            "deviceScaleFactor": 1.5, "mobile": False,
        })
        time.sleep(0.5)
        shot("04-sentence")
        cdp.call("Emulation.setDeviceMetricsOverride", {
            "width": 1440, "height": 920, "deviceScaleFactor": 1.5, "mobile": False,
        })

        # 5 生词本
        cdp.js("""document.querySelector('[data-tab="words"]').click()""")
        cdp.wait_js("!!document.querySelector('#list [data-word-id]')")
        time.sleep(0.4)
        shot("05-words")

        # 6 历史
        cdp.js("""document.querySelector('[data-tab="history"]').click()""")
        time.sleep(0.4)
        shot("06-history")

        # 7 导出菜单
        cdp.js("document.querySelector('#btn-export').click()")
        cdp.wait_js("!document.querySelector('#export-menu').classList.contains('hidden')")
        time.sleep(0.3)
        shot("07-export")

        print("截图完成 ->", SHOTS)
    finally:
        proc.terminate()
        time.sleep(1)
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(PROFILE, ignore_errors=True)


if __name__ == "__main__":
    main()
