"""离线冒烟测试：拉起一个 mock 服务，验证核心接口、数据写入与导出。

用法：
    python scripts/selftest.py

全部通过时退出码为 0，可直接用于 CI 或贡献者自查。
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Windows 控制台默认 cp1252/cp936，直接 print 中文会 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass



def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def call(url: str, payload: dict | None = None, method: str | None = None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method=method or ("POST" if data else "GET"),
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="englearn-selftest-"))
    port = free_port()
    env = dict(
        os.environ,
        ENGL_DATA_DIR=str(tmp / "data"),
        ENGL_CONFIG=str(tmp / "config.json"),
        PYTHONIOENCODING="utf-8",
    )
    proc = subprocess.Popen(
        [sys.executable, "app.py", "--mock", "--no-open", "--no-hotkey",
         "--no-popup", "--port", str(port)],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    checks: list[tuple[str, bool]] = []

    try:
        health = None
        for _ in range(80):
            try:
                health = call(base + "/api/health")
                break
            except Exception:  # noqa: BLE001
                if proc.poll() is not None:
                    out = proc.stdout.read().decode("utf-8", "replace") if proc.stdout else ""
                    print(out)
                    return 1
                time.sleep(0.25)
        if not health:
            print("FAIL: 服务 20 秒内未就绪")
            return 1
        checks.append(("health", health.get("ok") is True and health.get("mock") is True))

        with urllib.request.urlopen(base + "/", timeout=10) as resp:
            page = resp.read().decode("utf-8", "replace")
        checks.append(("index page", "Englearn" in page and resp.status == 200))

        word = call(base + "/api/analyze", {"text": "ubiquitous", "mode": "word"})
        fields = ("senses", "familiar", "phrases", "examples",
                  "derivatives", "similar", "phonetic_uk", "phonetic_us")
        checks.append(("word card fields", all(k in word["data"] for k in fields)))

        sent_text = ("The committee, having reviewed the proposal at length, "
                     "concluded that the measures were unlikely to yield results.")
        sent = call(base + "/api/analyze", {"text": sent_text, "mode": "sentence"})
        checks.append(("sentence structure", bool(sent["data"]["structure"]["main"])))

        saved = call(base + "/api/words", {"record_id": word["record"]["id"]})
        checks.append(("save word", saved["word"]["lemma"] == "ubiquitous"))
        checks.append(("word kind", saved["word"].get("kind") == "word"))

        # 生词分类：短语 / 短句 各自归位
        phrase = call(base + "/api/analyze", {"text": "copy to clipboard", "mode": "phrase"})
        per = call(base + "/api/words", {"record_id": phrase["record"]["id"]})
        short = call(base + "/api/analyze",
                     {"text": "but it is also incredibly error prone", "mode": "sentence"})
        ser = call(base + "/api/words", {"record_id": short["record"]["id"]})
        kinds = call(base + "/api/words?kind=phrase")["kinds"]
        checks.append(("classify phrase", per["word"].get("kind") == "phrase"))
        checks.append(("classify sentence", ser["word"].get("kind") == "sentence"))
        checks.append(("kind counts", kinds["word"] == 1 and kinds["phrase"] == 1
                       and kinds["sentence"] == 1 and kinds["all"] == 3))

        sentence = call(base + "/api/sentences", {"record_id": sent["record"]["id"]})
        sid = sentence["sentence"]["id"]
        patched = call(
            base + f"/api/sentences/{sid}",
            {"marks": [{"word": "committee"}, {"word": "proposal"}]},
            method="PATCH",
        )
        checks.append(("sentence marks", len(patched["sentence"]["marks"]) == 2))

        listing = call(base + "/api/sentences")
        checks.append(("list sentences", any(s["id"] == sid for s in listing["sentences"])))

        today = time.strftime("%Y-%m-%d")
        day = call(base + f"/api/day?date={today}")
        checks.append(("day view", day.get("date") == today and len(day["words"]) >= 1))

        exported = call(base + "/api/export", {"format": "md"})
        checks.append(("export markdown", exported["content"].startswith("# Englearn")))
        checks.append(("export includes marks", "陌生词标记" in exported["content"]))

        for fmt in ("json", "csv", "anki", "html"):
            call(base + "/api/export", {"format": fmt})
        checks.append(("export other formats", True))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    width = max(len(name) for name, _ in checks)
    failed = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name.ljust(width)}")
        failed += 0 if ok else 1

    print(f"\n{len(checks) - failed}/{len(checks)} 项通过")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
