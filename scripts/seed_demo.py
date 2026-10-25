"""向 data/app.db 写入一套演示数据，供教程截图使用。

用法：python scripts/seed_demo.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.store import Store  # noqa: E402

DATA = Path(os.environ.get("ENGL_DATA_DIR") or (ROOT / "data")) / "app.db"


def word_payload(text, phonetic, pos, senses, examples, translation=""):
    return {
        "type": "word",
        "text": text,
        "translation": translation,
        "phonetic": phonetic,
        "pos": pos,
        "senses": [{"pos": p, "meaning": m} for p, m in senses],
        "examples": [{"en": e, "zh": z} for e, z in examples],
        "structure": {"main": "", "clauses": [], "modifiers": [], "difficulty": "", "hard_words": []},
        "mock": False,
    }


def sentence_payload(text, translation, structure):
    return {
        "type": "sentence",
        "text": text,
        "translation": translation,
        "phonetic": "",
        "pos": "",
        "senses": [],
        "examples": [],
        "structure": structure,
        "mock": False,
    }


WORDS = [
    word_payload(
        "ubiquitous", "/juːˈbɪkwɪtəs/", "adj.",
        [("adj.", "无处不在的；普遍存在的"),
         ("adj.", "（指人）到处可见的")],
        [("Smartphones have become ubiquitous in modern life.",
          "智能手机在现代生活中已经无处不在。"),
         ("The company's logo is ubiquitous on billboards across the city.",
          "这家公司的标志在城市各处的广告牌上随处可见。")],
        translation="无处不在的；普遍存在的",
    ),
    word_payload(
        "mitigate", "/ˈmɪtɪɡeɪt/", "v.",
        [("v.", "减轻；缓和（痛苦、损失等）"),
         ("v.", "使（罪行）减轻")],
        [("Planting trees can mitigate the effects of urban heat.",
          "植树可以缓解城市热岛效应。"),
         ("The government introduced subsidies to mitigate the impact of rising fuel costs.",
          "政府推出补贴以减轻燃油价格上涨带来的影响。")],
        translation="减轻；缓和",
    ),
    word_payload(
        "contentious", "/kənˈtenʃəs/", "adj.",
        [("adj.", "有争议的；引起争论的"),
         ("adj.", "爱争论的")],
        [("The proposal remains highly contentious among researchers.",
          "该提案在研究人员中仍极具争议。")],
        translation="有争议的",
    ),
]

SENTENCE_1 = (
    "The committee, having reviewed the proposal at length, concluded that the "
    "measures, however well-intentioned, were unlikely to yield results."
)
SENTENCE_2 = (
    "What makes the finding remarkable is not merely that the effect persisted "
    "for a decade, but that it appeared across every demographic group studied."
)

SENTENCES = [
    sentence_payload(
        SENTENCE_1,
        "委员会在详尽审议该提案后得出结论：这些措施无论初衷多么良好，都不太可能取得成效。",
        {
            "main": "The committee concluded that the measures were unlikely to yield results.",
            "clauses": [
                {"type": "宾语从句", "text": "that the measures ... were unlikely to yield results",
                 "explain": "作 concluded 的宾语，说明结论内容"},
                {"type": "让步状语", "text": "however well-intentioned",
                 "explain": "插入语，省略了 they were，表示“无论初衷多好”"},
            ],
            "modifiers": [
                {"text": "having reviewed the proposal at length",
                 "explain": "现在分词完成式作时间状语，先于主句动作发生"},
            ],
            "difficulty": "主句被一个长分词状语和一个插入语隔开，容易找不到谓语 concluded。",
            "hard_words": [
                {"word": "at length", "meaning": "详尽地"},
                {"word": "well-intentioned", "meaning": "善意的"},
                {"word": "yield", "meaning": "产生（结果）"},
            ],
        },
    ),
    sentence_payload(
        SENTENCE_2,
        "这项发现之所以引人注目，不仅在于该效应持续了十年，更在于它出现在所研究的每一个群体中。",
        {
            "main": "What makes the finding remarkable is ... that it appeared across every demographic group.",
            "clauses": [
                {"type": "主语从句", "text": "What makes the finding remarkable", "explain": "作整句主语"},
                {"type": "表语从句", "text": "that the effect persisted for a decade", "explain": "not merely that… 的第一层表语"},
                {"type": "表语从句", "text": "that it appeared across every demographic group studied", "explain": "but that… 的第二层表语，与前者并列"},
            ],
            "modifiers": [
                {"text": "studied", "explain": "过去分词作后置定语，修饰 group"},
            ],
            "difficulty": "not merely that… but that… 的并列结构跨度过长，容易漏掉第二个 that。",
            "hard_words": [
                {"word": "demographic", "meaning": "人群的；人口统计的"},
                {"word": "persist", "meaning": "持续"},
            ],
        },
    ),
]


def main() -> None:
    if DATA.exists():
        DATA.unlink()
    st = Store(DATA)

    for w in WORDS:
        st.save_word(w, source=w["text"])

    for s in SENTENCES:
        st.save_sentence(s["text"], s["translation"], s, source="演示数据")

    # 记录（历史列表）
    st.add_record("word", "ubiquitous", "chrome.exe", WORDS[0])
    st.add_record("sentence", SENTENCE_1, "chrome.exe", SENTENCES[0])
    st.add_record("word", "mitigate", "chrome.exe", WORDS[1])
    st.add_record("sentence", SENTENCE_2, "chrome.exe", SENTENCES[1])

    print("seeded:", st.stats())


if __name__ == "__main__":
    main()
