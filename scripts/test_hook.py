"""验证全局鼠标钩子能识别「拖选」：合成一次按下→移动→抬起。

会短暂移动鼠标，结束后恢复原位。
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import mousehook  # noqa: E402

user32 = ctypes.windll.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

fired: list[tuple[int, int]] = []


def on_select(x, y):
    fired.append((x, y))


def main() -> None:
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    origin = (pt.x, pt.y)

    watcher = mousehook.MouseWatcher(on_select=on_select, drag_min=18)
    watcher.start()
    watcher.ready.wait(2)
    print("hook:", bool(watcher._hook), watcher.failed)
    time.sleep(0.3)

    start = (origin[0] + 40, origin[1] + 40)
    user32.SetCursorPos(*start)
    time.sleep(0.15)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.08)
    user32.SetCursorPos(start[0] + 80, start[1] + 10)   # 拖动 80px
    time.sleep(0.12)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.8)

    # 再点一下（不拖动），不应该触发
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.6)

    user32.SetCursorPos(*origin)
    watcher.stop()

    print("drag events:", fired)
    print("single-click triggered extra:", len(fired) > 1)
    print("RESULT:", "PASS" if len(fired) == 1 else "FAIL")


if __name__ == "__main__":
    main()
