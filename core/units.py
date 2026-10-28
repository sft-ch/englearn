"""按语言单位把一条「生词」归到 单词 / 短语 / 短句。

判定标准（语义优先，长度仅作辅助）：
1. 只含一个英文词 → 单词
2. 以句末/分句标点结尾 → 短句
3. 词数 ≥ 6 → 短句（足以承载主谓结构）
4. 其余 2~5 个词 → 短语
"""

from __future__ import annotations

import re

KINDS = ("word", "phrase", "sentence")
KIND_LABEL = {"word": "单词", "phrase": "短语", "sentence": "短句"}

SENTENCE_MIN_WORDS = 6
SENTENCE_END = (".", "!", "?", ";", "。", "！", "？", "；", "…")

_TOKEN = re.compile(r"[A-Za-z][A-Za-z'’\-]*")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(text or "")


def classify_unit(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "word"
    count = len(tokens(t))
    if count <= 1:
        return "word"
    if t.endswith(SENTENCE_END):
        return "sentence"
    if count >= SENTENCE_MIN_WORDS:
        return "sentence"
    return "phrase"
