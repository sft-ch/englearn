"""截取「生词分类」界面：全部 / 短句筛选。"""

from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from shoot import CDP, SHOTS, launch_chrome, page_ws_url  # noqa: E402

BASE = "http://127.0.0.1:8765"


def main() -> None:
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
        cdp.wait_js("!!document.querySelector('.kind-filter')")
        time.sleep(1.2)

        def shot(name: str) -> None:
            data = base64.b64decode(cdp.call("Page.captureScreenshot", {"format": "png"})["data"])
            (SHOTS / f"{name}.png").write_bytes(data)
            print(f"  {name}.png  {len(data)//1024} KB")

        shot("24-kind-all")

        cdp.js("""document.querySelector('[data-kind="sentence"]').click()""")
        cdp.wait_js("""document.querySelector('[data-kind="sentence"]').classList.contains('on')""")
        time.sleep(0.6)
        shot("25-kind-sentence")
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
