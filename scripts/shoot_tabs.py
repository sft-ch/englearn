"""给新增的「生词详情 / 长难句 / 日历」三个界面截图。"""

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

        # 生词详情展开
        cdp.js("document.querySelector('[data-word-id]').click()")
        cdp.wait_js("!!document.querySelector('.detail')")
        time.sleep(0.5)
        shot("11-word-detail")

        # 长难句回看
        cdp.js("""document.querySelector('[data-tab="sentences"]').click()""")
        cdp.wait_js("!!document.querySelector('[data-sid]')")
        time.sleep(0.5)
        shot("12-sentences")

        # 日历
        cdp.js("""document.querySelector('[data-tab="day"]').click()""")
        cdp.wait_js("!!document.querySelector('.daybar')")
        time.sleep(0.7)
        shot("13-day")

        # 点开一条收藏的长难句，右侧应渲染完整解析
        cdp.js("""document.querySelector('[data-tab="sentences"]').click()""")
        cdp.wait_js("!!document.querySelector('[data-sid]')")
        time.sleep(0.3)
        cdp.js("document.querySelector('[data-sid]').click()")
        cdp.wait_js("!!document.querySelector('#result .struct-main')")
        time.sleep(0.5)
        shot("14-sentence-view")
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
