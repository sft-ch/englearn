"""验证词汇卡片：输入单词分析 + 点标记词生成卡片 + 返回。"""

from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from shoot import BASE, SHOTS, CDP, launch_chrome, page_ws_url  # noqa: E402


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
        cdp.wait_js("!!document.querySelector('#list')")
        time.sleep(1.5)

        def shot(name: str) -> None:
            data = base64.b64decode(cdp.call("Page.captureScreenshot", {"format": "png"})["data"])
            (SHOTS / f"{name}.png").write_bytes(data)
            print(f"  {name}.png  {len(data)//1024} KB")

        # 1) 输入单词 → 词汇卡片
        cdp.js("""(() => {
            const inp = document.querySelector('#input');
            inp.value = 'ubiquitous';
            inp.dispatchEvent(new Event('input'));
            document.querySelector('#btn-analyze').click();
        })()""")
        cdp.wait_js("!!document.querySelector('.card-sec')", timeout=15)
        time.sleep(0.6)
        shot("21-word-card")

        # 2) 长难句里的标记词 → 卡片
        cdp.js("""document.querySelector('[data-tab="sentences"]').click()""")
        cdp.wait_js("!!document.querySelector('[data-sid]')")
        time.sleep(0.3)
        cdp.js("""(() => {
            const el = [...document.querySelectorAll('[data-sid]')]
                .find(e => e.textContent.includes('The committee'));
            el.click();
        })()""")
        cdp.wait_js("!!document.querySelector('mark.vocab-mark')")
        time.sleep(0.3)
        cdp.js("document.querySelector('mark.vocab-mark').click()")
        cdp.wait_js("document.querySelector('#detail-title').textContent === '词汇卡片'", timeout=15)
        time.sleep(0.6)
        shot("22-mark-card")

        # 3) 返回应回到长难句
        cdp.js("document.querySelector('#btn-back').click()")
        cdp.wait_js("document.querySelector('#detail-title').textContent === '长难句详情'")
        time.sleep(0.4)
        shot("23-back-to-sentence")
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
