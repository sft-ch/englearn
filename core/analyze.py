"""文本分类、提示词构造、结果归一化与离线 mock。"""

from __future__ import annotations

import json
import re

from . import llm

SENTENCE_MIN_WORDS = 12

SYSTEM_PROMPT = """你是 Englearn 的英语精读助手，服务于中文母语的英语学习者。
输出要求：
1. 只输出一个 JSON 对象，不要 Markdown 代码块，不要任何解释性文字。
2. 所有讲解用简体中文，英文原文原样保留。
3. 不确定的字段留空字符串或空数组，但字段本身不能省略。
"""

USER_TEMPLATE = """待分析文本：
<<<{text}>>>

识别类型：{kind}（word=单词，phrase=短语，sentence=句子或段落）

按以下结构输出 JSON：
{{
  "type": "{kind}",
  "text": "原文",
  "translation": "对应中文译文",
  "phonetic": "音标，仅单词或短语需要",
  "pos": "主要词性，如 n. / v. / adj.",
  "senses": [{{"pos": "n.", "meaning": "常用释义，按词性分组"}}],
  "examples": [{{"en": "英文例句", "zh": "例句翻译"}}],
  "structure": {{
    "main": "句子主干：主语 + 谓语 + 宾语",
    "clauses": [{{"type": "定语从句/状语从句/宾语从句等", "text": "从句原文", "explain": "它修饰什么、起什么作用"}}],
    "modifiers": [{{"text": "修饰成分原文", "explain": "作用说明"}}],
    "difficulty": "一句话概括这句话难在哪",
    "hard_words": [{{"word": "生词", "meaning": "在句中的含义"}}]
  }}
}}

要求：
{extra}"""

EXTRA = {
    "word": "senses 至少给 2 条常用义项；examples 给 2 条贴近日常的例句；structure 各字段留空即可。",
    "phrase": "给出短语整体含义与 1-2 个用法例句；若含固定搭配请点明。",
    "sentence": "structure 必须填写：main 写出主干；clauses 按从外到内逐层拆解每个从句；"
                "modifiers 列出后置定语、插入语、分词结构等；hard_words 挑出 3-6 个生词。",
}

WORD_SYSTEM = """你是英语词汇解析专家，面向中文母语的英语学习者。
要求：
1. 只输出一个 JSON 对象，不要 Markdown 代码块，不要任何解释性文字。
2. 所有解释、辨析用简体中文，英文原词原样保留。
3. 音标准确，英式与美式分别给出；释义按使用频率从高到低排序。
4. 没有对应内容的字段输出空数组，不得编造。
"""

WORD_USER = """待解析词汇：{text}

严格按下面结构输出 JSON（字段不可省略）：
{{
  "type": "{kind}",
  "text": "{text}",
  "phonetic": {{"uk": "/英式音标/", "us": "/美式音标/"}},
  "pos": "主要词性",
  "senses": [{{"pos": "n.", "meaning": "中文释义", "freq": 1}}],
  "familiar": [{{"pos": "", "sense": "熟词生义：常见词的不常见义项", "note": "使用场景与辨析要点", "example": "英文例句"}}],
  "phrases": [{{"en": "高频短语或固定搭配", "zh": "中文释义"}}],
  "examples": [{{"en": "地道例句", "zh": "中文翻译"}}],
  "derivatives": [{{"word": "同根派生词", "pos": "词性", "meaning": "中文释义"}}],
  "similar": [{{"word": "近义/反义/形近/易混词", "relation": "近义|反义|形近|易混", "note": "辨析要点"}}]
}}

要求：
- senses：按常用度排序，通常 2-4 条，每条标明词性
- familiar：仅当该词确有「熟词生义」时填写，否则 []
- phrases：2-4 条高频搭配
- examples：2-3 条，体现真实语境
- derivatives：2-4 条，含词性转换
- similar：2-4 条，说明与目标词的差别
"""


def classify(text: str) -> str:
    t = (text or "").strip()
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", t)
    if not words:
        return "sentence"
    ends_sentence = t.endswith((".", "!", "?", '"', "”", "）"))
    if len(words) == 1:
        return "word"
    if len(words) <= 3 and not ends_sentence:
        return "phrase"
    if len(words) >= SENTENCE_MIN_WORDS or ends_sentence:
        return "sentence"
    return "phrase"


def _clean_json(raw: str) -> str:
    s = (raw or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end > start:
        return s[start:end + 1]
    return s


def _empty_structure() -> dict:
    return {"main": "", "clauses": [], "modifiers": [], "difficulty": "", "hard_words": []}


def normalize(data: dict, text: str, kind: str) -> dict:
    out = data if isinstance(data, dict) else {}
    struct = out.get("structure") if isinstance(out.get("structure"), dict) else {}
    norm_struct = {
        "main": str(struct.get("main") or ""),
        "clauses": [],
        "modifiers": [],
        "difficulty": str(struct.get("difficulty") or ""),
        "hard_words": [],
    }
    for c in struct.get("clauses") or []:
        if isinstance(c, dict):
            norm_struct["clauses"].append({
                "type": str(c.get("type") or ""),
                "text": str(c.get("text") or ""),
                "explain": str(c.get("explain") or ""),
            })
    for m in struct.get("modifiers") or []:
        if isinstance(m, dict):
            norm_struct["modifiers"].append({
                "text": str(m.get("text") or ""),
                "explain": str(m.get("explain") or ""),
            })
    for h in struct.get("hard_words") or []:
        if isinstance(h, dict):
            norm_struct["hard_words"].append({
                "word": str(h.get("word") or ""),
                "meaning": str(h.get("meaning") or ""),
            })

    senses = []
    for s in out.get("senses") or []:
        if isinstance(s, dict):
            senses.append({"pos": str(s.get("pos") or ""), "meaning": str(s.get("meaning") or "")})
        elif isinstance(s, str):
            senses.append({"pos": "", "meaning": s})

    examples = []
    for e in out.get("examples") or []:
        if isinstance(e, dict):
            examples.append({"en": str(e.get("en") or ""), "zh": str(e.get("zh") or "")})
        elif isinstance(e, str):
            examples.append({"en": e, "zh": ""})

    ph = out.get("phonetic")
    if isinstance(ph, dict):
        phonetic_uk = str(ph.get("uk") or "").strip()
        phonetic_us = str(ph.get("us") or "").strip()
        phonetic = phonetic_uk or phonetic_us
    else:
        phonetic = str(ph or "").strip()
        phonetic_uk, phonetic_us = phonetic, ""

    familiar = []
    for f in out.get("familiar") or []:
        if isinstance(f, dict):
            familiar.append({
                "pos": str(f.get("pos") or ""),
                "sense": str(f.get("sense") or ""),
                "note": str(f.get("note") or ""),
                "example": str(f.get("example") or ""),
            })

    phrases = []
    for p in out.get("phrases") or []:
        if isinstance(p, dict):
            phrases.append({"en": str(p.get("en") or ""), "zh": str(p.get("zh") or "")})
        elif isinstance(p, str):
            phrases.append({"en": p, "zh": ""})

    derivatives = []
    for d in out.get("derivatives") or []:
        if isinstance(d, dict):
            derivatives.append({
                "word": str(d.get("word") or ""),
                "pos": str(d.get("pos") or ""),
                "meaning": str(d.get("meaning") or ""),
            })

    similar = []
    for s2 in out.get("similar") or []:
        if isinstance(s2, dict):
            similar.append({
                "word": str(s2.get("word") or ""),
                "relation": str(s2.get("relation") or ""),
                "note": str(s2.get("note") or ""),
            })

    return {
        "type": out.get("type") if out.get("type") in ("word", "phrase", "sentence") else kind,
        "text": str(out.get("text") or text).strip(),
        "translation": str(out.get("translation") or ""),
        "phonetic": phonetic,
        "phonetic_uk": phonetic_uk,
        "phonetic_us": phonetic_us,
        "pos": str(out.get("pos") or ""),
        "senses": senses,
        "familiar": familiar,
        "phrases": phrases,
        "examples": examples,
        "derivatives": derivatives,
        "similar": similar,
        "structure": norm_struct,
        "mock": bool(out.get("mock")),
    }


def mock(text: str, kind: str) -> dict:
    """离线演示数据，用于没有 API Key 时跑通链路。"""
    if kind in ("word", "phrase"):
        return {
            "type": kind,
            "text": text,
            "translation": f"【示例】{text} 的中文释义",
            "phonetic": "/ˈmɒk/",
            "phonetic_uk": "/ˈmɒk/",
            "phonetic_us": "/ˈmɑːk/",
            "pos": "n.",
            "senses": [
                {"pos": "n.", "meaning": "【示例】名词释义"},
                {"pos": "v.", "meaning": "【示例】动词释义"},
            ],
            "familiar": [
                {"pos": "", "sense": "【示例】熟词生义", "note": "【示例】使用场景说明", "example": "This is a familiar-sense example."},
            ],
            "phrases": [{"en": "mock up", "zh": "【示例】短语释义"}],
            "examples": [
                {"en": "This is a mock example sentence.", "zh": "这是一个示例例句。"},
                {"en": "Englearn runs fully offline in mock mode.", "zh": "Englearn 在 mock 模式下可完全离线运行。"},
            ],
            "derivatives": [{"word": "mockery", "pos": "n.", "meaning": "【示例】派生词释义"}],
            "similar": [{"word": "fake", "relation": "近义", "note": "【示例】辨析说明"}],
            "structure": _empty_structure(),
            "mock": True,
        }
    return {
        "type": "sentence",
        "text": text,
        "translation": "【示例译文】这里会显示整句的中文翻译。",
        "phonetic": "",
        "pos": "",
        "senses": [],
        "examples": [],
        "structure": {
            "main": "【示例】主语 + 谓语 + 宾语",
            "clauses": [
                {"type": "定语从句", "text": "which ...", "explain": "【示例】修饰前面的名词"},
                {"type": "状语从句", "text": "although ...", "explain": "【示例】表示让步"},
            ],
            "modifiers": [
                {"text": "分词短语", "explain": "【示例】作后置定语"},
            ],
            "difficulty": "【示例】从句嵌套较深，需要先找主干再看修饰。",
            "hard_words": [
                {"word": "example", "meaning": "例子"},
                {"word": "mock", "meaning": "模拟的"},
            ],
        },
        "mock": True,
    }


def analyze(cfg: dict, text: str, mode: str = "auto") -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("文本为空")
    kind = mode if mode in ("word", "phrase", "sentence") else classify(text)
    if cfg.get("mock"):
        return mock(text, kind)

    if kind in ("word", "phrase"):
        raw = llm.chat(cfg, WORD_SYSTEM, WORD_USER.format(text=text, kind=kind))
    else:
        user = USER_TEMPLATE.format(text=text, kind=kind, extra=EXTRA.get(kind, ""))
        raw = llm.chat(cfg, SYSTEM_PROMPT, user)
    try:
        data = json.loads(_clean_json(raw))
    except ValueError:
        # 解析失败时降级：保留原始输出便于排查
        broken = normalize({}, text, kind)
        broken["translation"] = raw.strip()[:2000]
        broken["raw"] = raw[:2000]
        return broken
    return normalize(data, text, kind)
