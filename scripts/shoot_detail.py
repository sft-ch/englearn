"""验证「点击右侧条目 → 左侧整页详情」的新布局。"""

from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from shoot import BASE, SHOTS, CDP, launch_chrome, page_ws_url  # noqa: E402


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
        time.sleep(1.6)

        def shot(name: str) -> None:
            data = base64.b64decode(cdp.call("Page.captureScreenshot", {"format": "png"})["data"])
            (SHOTS / f"{name}.png").write_bytes(data)
            print(f"  {name}.png  {len(data)//1024} KB")

        # 1) 生词 → 整页详情
        cdp.js("document.querySelector('[data-word-id]').click()")
        cdp.wait_js("document.querySelector('.col-left').classList.contains('detail')")
        time.sleep(0.5)
        shot("15-word-page")

        # 2) 返回后恢复输入区
        cdp.js("document.querySelector('#btn-back').click()")
        cdp.wait_js("!document.querySelector('.col-left').classList.contains('detail')")
        time.sleep(0.4)
        shot("16-back")

        # 3) 长难句 → 整页
        cdp.js("""document.querySelector('[data-tab="sentences"]').click()""")
        cdp.wait_js("!!document.querySelector('[data-sid]')")
        time.sleep(0.3)
        cdp.js("document.querySelector('[data-sid]').click()")
        cdp.wait_js("document.querySelector('.col-left').classList.contains('detail')")
        time.sleep(0.5)
        shot("17-sentence-page")

        # 4) 历史 → 整页
        cdp.js("""document.querySelector('[data-tab="history"]').click()""")
        cdp.wait_js("!!document.querySelector('[data-rec-id]')")
        time.sleep(0.3)
        cdp.js("document.querySelector('[data-rec-id]').click()")
        cdp.wait_js("document.querySelector('.col-left').classList.contains('detail')")
        time.sleep(0.5)
        shot("18-history-page")
        print("done")
    finally:
        proc.terminate()
        time.sleep(0.8)
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


if __name__ == "__main__":
    main()
