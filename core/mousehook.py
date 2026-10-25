"""全局鼠标钩子：只负责发现「拖选 / 双击选词」，真正的取词交给工作线程。

低级钩子回调必须在 ~300ms 内返回，否则 Windows 会静默摘掉钩子，
所以回调里只记录坐标并投递事件，不做任何阻塞操作。
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time
from ctypes import wintypes

IS_WINDOWS = sys.platform == "win32"

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONDOWN = 0x0204

if IS_WINDOWS:  # pragma: no cover - 平台相关
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    HOOKPROC = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    )
    user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD
    ]
    user32.SetWindowsHookExW.restype = ctypes.c_void_p
    user32.CallNextHookEx.argtypes = [
        ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    ]
    user32.CallNextHookEx.restype = ctypes.c_ssize_t
    user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
    user32.GetMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT
    ]
    user32.WindowFromPoint.argtypes = [wintypes.POINT]
    user32.WindowFromPoint.restype = wintypes.HWND
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


def point_is_own_process(x: int, y: int) -> bool:
    """光标是否落在本程序自己的窗口上（弹窗、控制台）。"""
    if not IS_WINDOWS:
        return False
    import os

    hwnd = user32.WindowFromPoint(wintypes.POINT(x, y))
    if not hwnd:
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == os.getpid()


def cursor_pos() -> tuple[int, int]:
    if not IS_WINDOWS:
        return (0, 0)
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


# 这些窗口里的拖动通常不是选文字（拖文件、拖窗口、点任务栏），直接跳过
SKIP_CLASSES = {
    "Progman", "WorkerW", "SHELLDLL_DefView", "SysListView32",
    "DirectUIHWND", "CabinetWClass", "Shell_TrayWnd", "TrayNotifyWnd",
    "MSTaskListWClass", "SysTreeView32",
}


def window_class_at(x: int, y: int) -> str:
    if not IS_WINDOWS:
        return ""
    hwnd = user32.WindowFromPoint(wintypes.POINT(x, y))
    if not hwnd:
        return ""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


class MouseWatcher(threading.Thread):
    """检测鼠标拖选与双击选词。

    on_select(x, y)  选中结束（拖拽距离足够，或双击）
    on_press(x, y)   任意左/右键按下（用于关闭悬浮窗）
    """

    def __init__(self, on_select, on_press=None, drag_min: float = 18.0) -> None:
        super().__init__(daemon=True, name="englearn-mouse")
        self.on_select = on_select
        self.on_press = on_press
        self.drag_min = drag_min
        self._down: tuple[float, float, float] | None = None
        self._hook = None
        self._proc = HOOKPROC(self._handler) if IS_WINDOWS else None
        self.ready = threading.Event()
        self.failed = ""

    # ---------- 内部 ----------
    @staticmethod
    def _safe(fn, *args) -> None:
        if not fn:
            return
        try:
            fn(*args)
        except Exception:  # noqa: BLE001
            import traceback

            traceback.print_exc()

    def _handler(self, nCode, wParam, lParam):  # pragma: no cover - 平台相关
        if nCode >= 0:
            info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            x, y = info.pt.x, info.pt.y
            if wParam == WM_LBUTTONDOWN:
                self._down = (x, y, time.time())
                self._safe(self.on_press, x, y)
            elif wParam == WM_LBUTTONUP:
                down, self._down = self._down, None
                if down:
                    dx, dy = x - down[0], y - down[1]
                    if dx * dx + dy * dy >= self.drag_min * self.drag_min:
                        self._safe(self.on_select, x, y)
            elif wParam == WM_LBUTTONDBLCLK:
                self._safe(self.on_select, x, y)
            elif wParam == WM_RBUTTONDOWN:
                self._safe(self.on_press, x, y)
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    # ---------- 线程 ----------
    def run(self) -> None:  # pragma: no cover - 平台相关
        if not IS_WINDOWS:
            self.ready.set()
            return
        self._hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._proc, None, 0)
        self.ready.set()
        if not self._hook:
            self.failed = "鼠标钩子安装失败（可能被安全软件拦截）"
            return
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self) -> None:  # pragma: no cover
        if IS_WINDOWS and self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
