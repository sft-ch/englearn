"""全局热键与划词捕获（仅 Windows，其他平台自动降级为空实现）。"""

from __future__ import annotations

import ctypes
import random
import sys
import threading
import time
import traceback

IS_WINDOWS = sys.platform == "win32"

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040
VK_CONTROL = 0x11
VK_C = 0x43
KEYEVENTF_KEYUP = 0x0002
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x0001, 0x0002, 0x0004, 0x0008

if IS_WINDOWS:  # pragma: no cover - 平台相关
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.CloseClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user32.RegisterHotKey.restype = wintypes.BOOL
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalUnlock.restype = wintypes.BOOL


def _open_clipboard(retries: int = 6) -> bool:
    for _ in range(retries):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.03)
    return False


def get_clipboard_text() -> str:
    if not IS_WINDOWS:
        return ""
    if not _open_clipboard():
        return ""
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return ""
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str) -> bool:
    if not IS_WINDOWS:
        return False
    if not _open_clipboard():
        return False
    try:
        if not user32.EmptyClipboard():
            return False
        if not text:
            return True
        buf = ctypes.create_unicode_buffer(text)
        size = ctypes.sizeof(buf)
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE | GMEM_ZEROINIT, size)
        if not handle:
            return False
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return False
        try:
            ctypes.memmove(ptr, buf, size)
        finally:
            kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            return False
        return True
    finally:
        user32.CloseClipboard()


def _press_ctrl_c() -> None:
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def capture_selection(timeout: float = 0.9) -> str:
    """模拟 Ctrl+C 取当前选中文本，结束后还原原剪贴板内容。"""
    if not IS_WINDOWS:
        return ""
    backup = get_clipboard_text()
    marker = "__englearn_%d__" % random.randint(100000, 999999)
    if not set_clipboard_text(marker):
        return ""
    try:
        _press_ctrl_c()
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.05)
            current = get_clipboard_text()
            if current and current != marker:
                return current.strip()
        return ""
    finally:
        time.sleep(0.05)
        set_clipboard_text(backup)


def _parse_combo(combo: str) -> tuple[int, int] | None:
    parts = [p.strip().lower() for p in (combo or "").split("+") if p.strip()]
    if len(parts) < 2:
        return None
    mods = 0
    for p in parts[:-1]:
        mods |= {"alt": MOD_ALT, "ctrl": MOD_CONTROL, "control": MOD_CONTROL,
                 "shift": MOD_SHIFT, "win": MOD_WIN}.get(p, 0)
    key = parts[-1]
    if len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    else:
        aliases = {"space": 0x20, "enter": 0x0D, "tab": 0x09, "esc": 0x1B}
        vk = aliases.get(key, 0)
    if not mods or not vk:
        return None
    return mods, vk


class HotkeyListener(threading.Thread):
    """在独立线程里跑 RegisterHotKey 消息循环。"""

    def __init__(self, bindings: dict[str, callable], on_error=None) -> None:
        super().__init__(daemon=True, name="englearn-hotkey")
        self.bindings = bindings
        self.on_error = on_error
        self._stop_event = threading.Event()
        self.registered: list[str] = []
        self.ready = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:  # pragma: no cover - 平台相关
        if not IS_WINDOWS:
            self.ready.set()
            return
        handlers: dict[int, callable] = {}
        hid = 0xB000
        for combo, callback in self.bindings.items():
            spec = _parse_combo(combo)
            if not spec:
                continue
            if user32.RegisterHotKey(None, hid, spec[0], spec[1]):
                handlers[hid] = callback
                self.registered.append(combo)
                hid += 1
        self.ready.set()
        if not handlers:
            if self.on_error:
                self.on_error("热键注册失败：可能被其他程序占用，请在设置里换一组组合键")
            return

        msg = ctypes.wintypes.MSG()
        while not self._stop_event.is_set():
            if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                if msg.message == WM_HOTKEY:
                    callback = handlers.get(int(msg.wParam))
                    if callback:
                        try:
                            callback()
                        except Exception:  # noqa: BLE001
                            traceback.print_exc()
                continue
            time.sleep(0.02)
        for h in handlers:
            user32.UnregisterHotKey(None, h)


class ClipboardWatcher(threading.Thread):
    """可选：监听剪贴板变化，手动 Ctrl+C 也能触发分析。"""

    def __init__(self, callback, interval: float = 0.7) -> None:
        super().__init__(daemon=True, name="englearn-clipboard")
        self.callback = callback
        self.interval = interval
        self.enabled = False
        self._stop_event = threading.Event()
        self._last = ""

    def stop(self) -> None:
        self._stop_event.set()

    def mark_current(self) -> None:
        self._last = get_clipboard_text().strip()

    def run(self) -> None:  # pragma: no cover - 平台相关
        while not self._stop_event.is_set():
            time.sleep(self.interval)
            if not self.enabled:
                continue
            text = get_clipboard_text().strip()
            if not text or text == self._last:
                continue
            self._last = text
            if 2 <= len(text) <= 4000:
                try:
                    self.callback(text)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
