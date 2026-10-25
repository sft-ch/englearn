"""验证长难句里的自定义标记：高亮、标记、取消。"""

from __future__ import annotations

import base64
import json
import sys
import time
import urllib.request
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

        cdp.js("""document.querySelector('[data-tab="sentences"]').click()""")
        cdp.wait_js("!!document.querySelector('[data-sid]')")
        time.sleep(0.3)
        cdp.js("""(() => {
            const el = [...document.querySelectorAll('[data-sid]')]
                .find(e => e.textContent.includes('The committee'));
            el.click();
        })()""")
        cdp.wait_js("document.querySelector('.col-left').classList.contains('detail')")
        cdp.wait_js("!!document.querySelector('.vocab-mark')")
        time.sleep(0.5)
        shot("19-marks")

        # 选中句中的 however well-intentioned，点「标记陌生词」
        cdp.js("""(() => {
            const word = 'however well-intentioned';
            const block = document.querySelector('.en-block');
            const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
            let node, target = null, offset = -1;
            while ((node = walker.nextNode())) {
                const i = node.textContent.indexOf(word);
                if (i >= 0) { target = node; offset = i; break; }
            }
            if (!target) throw new Error('没找到目标文本');
            const range = document.createRange();
            range.setStart(target, offset);
            range.setEnd(target, offset + word.length);
            const sel = getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            document.querySelector('#btn-mark').click();
            return offset;
        })()""")
        cdp.wait_js("document.querySelectorAll('.mark-chip').length >= 3", timeout=10)
        time.sleep(0.6)
        shot("20-mark-added")

        with urllib.request.urlopen(f"{BASE}/api/sentences", timeout=5) as r:
            data = json.loads(r.read().decode())
        for s in data["sentences"]:
            if s["id"] == 1:
                print("stored marks:", [m["word"] for m in s["marks"]])
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
