"""悬浮窗冒烟测试：建窗 → 截图 → 触发「翻译 / 长难句」→ 再截图。

用法：先起一个服务（python app.py --mock --no-open --no-hotkey --no-popup --port 8899），
再运行本脚本。
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import ImageGrab  # noqa: E402

from app import _enable_dpi  # noqa: E402
from core import mousehook  # noqa: E402
from core.popup import PopupController  # noqa: E402

OUT = ROOT / "docs" / "images"
BASE = "http://127.0.0.1:8899"


def shot(ctrl, name: str) -> None:
    ctrl.root.update()
    left, top, right, bottom = ctrl.bounds
    pad = 20
    img = ImageGrab.grab(
        bbox=(max(0, left - pad), max(0, top - pad), right + pad, bottom + pad),
        all_screens=True,
    )
    img.save(OUT / f"{name}.png")
    print(f"  {name}.png {img.size}")


def main() -> None:
    _enable_dpi()
    root = tk.Tk()
    root.withdraw()
    ctrl = PopupController(root, BASE)

    # 1) 钩子能否装上
    watcher = mousehook.MouseWatcher(
        on_select=lambda x, y: None, on_press=ctrl.handle_press
    )
    watcher.start()
    watcher.ready.wait(2)
    print("hook installed:", bool(watcher._hook), watcher.failed)

    # 2) 弹窗 + 首屏
    root.after(200, lambda: ctrl.submit("ubiquitous", 420, 300))
    root.after(1400, lambda: shot(ctrl, "08-popup"))

    # 3) 点「翻译」
    root.after(1800, ctrl._act_translate)
    root.after(3600, lambda: shot(ctrl, "09-popup-translate"))

    # 4) 关掉重开，点「长难句」
    def second() -> None:
        ctrl.close()
        ctrl.submit(
            "The committee, having reviewed the proposal at length, concluded that "
            "the measures, however well-intentioned, were unlikely to yield results.",
            420, 240,
        )

    root.after(4000, second)
    root.after(5600, ctrl._act_structure)
    root.after(7400, lambda: shot(ctrl, "10-popup-structure"))
    root.after(7800, lambda: (watcher.stop(), root.quit()))

    root.mainloop()
    print("done")


if __name__ == "__main__":
    main()
