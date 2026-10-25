"""导出：Markdown / JSON / CSV / Anki TXT / HTML。"""

from __future__ import annotations

import csv
import html
import io
import json
from datetime import datetime
from pathlib import Path

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports"

STATUS_LABEL = {"new": "新词", "learning": "学习中", "known": "已掌握"}
EXT = {"md": "md", "json": "json", "csv": "csv", "anki": "txt", "html": "html"}


def _cell(text) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


def _payload(row: dict) -> dict:
    raw = row.get("payload")
    if raw is None:
        raw = row.get("analysis")
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except ValueError:
        return {}


def build_markdown(store) -> str:
    words = store.words(limit=1000)
    sentences = store.sentences(limit=1000)
    records = store.records(limit=300)
    stats = store.stats()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Englearn 学习导出",
        "",
        f"> 导出时间：{now}　｜　生词 {stats['words']} 个（已掌握 {stats['known']}）"
        f"　｜　长难句 {stats['sentences']} 句　｜　记录 {stats['records']} 条",
        "",
    ]

    lines += ["## 一、生词本", ""]
    if words:
        lines += ["| 单词 | 音标 | 词性 | 释义 | 次数 | 状态 | 最近出现 |",
                  "| --- | --- | --- | --- | --- | --- | --- |"]
        for w in words:
            lines.append(
                f"| {_cell(w['lemma'])} | {_cell(w['phonetic'])} | {_cell(w['pos'])} | "
                f"{_cell(w['meaning'])} | {w['cnt']} | "
                f"{STATUS_LABEL.get(w['status'], w['status'])} | {_cell(w['last_seen'])} |"
            )
        lines += ["", "### 生词详情", ""]
        for idx, w in enumerate(words, 1):
            head = f"**{idx}. {w['lemma']}**"
            if w["phonetic"]:
                head += f"　{w['phonetic']}"
            if w["pos"]:
                head += f"　{w['pos']}"
            lines.append(head)
            lines.append("")
            lines.append(f"- 释义：{w['meaning'] or '—'}")
            if w["example"]:
                lines.append(f"- 例句：{w['example']}")
            if w["note"]:
                lines.append(f"- 备注：{w['note']}")
            if w["source"]:
                lines.append(f"- 来源：{w['source']}")
            lines.append(f"- 出现 {w['cnt']} 次，首次 {w['first_seen']}，最近 {w['last_seen']}")
            lines.append("")
    else:
        lines += ["_暂无生词_", ""]

    lines += ["## 二、长难句精析", ""]
    if sentences:
        for idx, s in enumerate(sentences, 1):
            data = _payload(s)
            struct = data.get("structure") or {}
            lines.append(f"### {idx}. {s['text']}")
            lines.append("")
            if s["translation"]:
                lines.append(f"- 参考译文：{s['translation']}")
            try:
                marks = json.loads(s.get("marks") or "[]")
            except ValueError:
                marks = []
            if marks:
                lines.append("- 陌生词标记：" + "、".join(
                    f"**{m.get('word', '')}**" for m in marks if m.get("word")
                ))
            if struct.get("main"):
                lines.append(f"- 句子主干：{struct['main']}")
            clauses = struct.get("clauses") or []
            if clauses:
                lines.append("- 从句拆解：")
                for c in clauses:
                    label = c.get("type") or "从句"
                    lines.append(f"  - **[{label}]** {c.get('text', '')} —— {c.get('explain', '')}")
            mods = struct.get("modifiers") or []
            if mods:
                lines.append("- 修饰成分：")
                for m in mods:
                    lines.append(f"  - {m.get('text', '')} —— {m.get('explain', '')}")
            hards = struct.get("hard_words") or []
            if hards:
                joined = "；".join(f"{h.get('word', '')}（{h.get('meaning', '')}）" for h in hards)
                lines.append(f"- 难点词汇：{joined}")
            if struct.get("difficulty"):
                lines.append(f"- 难点说明：{struct['difficulty']}")
            if s["source"]:
                lines.append(f"- 来源：{s['source']}")
            lines.append(f"- 记录时间：{s['created_at']}")
            lines.append("")
    else:
        lines += ["_暂无长难句_", ""]

    lines += ["## 三、学习记录", ""]
    if records:
        lines += ["| 时间 | 类型 | 原文 |", "| --- | --- | --- |"]
        for r in records:
            lines.append(f"| {_cell(r['ts'])} | {_cell(r['kind'])} | {_cell(r['text'][:120])} |")
        lines.append("")
    else:
        lines += ["_暂无记录_", ""]

    return "\n".join(lines)


def build_json(store) -> str:
    words = store.words(limit=2000)
    sentences = store.sentences(limit=2000)
    records = [dict(r, payload=_payload(r)) for r in store.records(limit=2000)]
    data = {
        "app": "Englearn",
        "version": 1,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": store.stats(),
        "words": words,
        "sentences": [
            dict(s, analysis=_payload(s)) for s in sentences
        ],
        "records": records,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_csv(store) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["单词", "音标", "词性", "释义", "例句", "状态", "备注", "标签",
                     "次数", "首次", "最近"])
    for w in store.words(limit=2000):
        writer.writerow([w["lemma"], w["phonetic"], w["pos"], w["meaning"], w["example"],
                         STATUS_LABEL.get(w["status"], w["status"]), w["note"], w["tags"],
                         w["cnt"], w["first_seen"], w["last_seen"]])
    return buf.getvalue()


def build_anki(store) -> str:
    lines = ["#separator:tab", "#html:true", "#columns:单词\t释义"]
    for w in store.words(limit=2000):
        back = f"<b>{html.escape(w['meaning'] or '')}</b>"
        if w["phonetic"]:
            back = f"{html.escape(w['phonetic'])}<br>{back}"
        if w["example"]:
            back += f"<br><i>{html.escape(w['example'])}</i>"
        lines.append(f"{w['lemma']}\t{back}")
    return "\n".join(lines) + "\n"


def build_html(store) -> str:
    words = store.words(limit=1000)
    sentences = store.sentences(limit=500)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    word_rows = "".join(
        f"<tr><td>{html.escape(w['lemma'])}</td><td>{html.escape(w['phonetic'] or '')}</td>"
        f"<td>{html.escape(w['meaning'] or '')}</td>"
        f"<td>{STATUS_LABEL.get(w['status'], w['status'])}</td><td>{w['cnt']}</td></tr>"
        for w in words
    ) or "<tr><td colspan='5'>暂无生词</td></tr>"

    sent_blocks = []
    for s in sentences:
        data = _payload(s)
        struct = data.get("structure") or {}
        clauses = "".join(
            f"<li><b>{html.escape(c.get('type') or '从句')}</b> {html.escape(c.get('text') or '')}"
            f" —— {html.escape(c.get('explain') or '')}</li>"
            for c in (struct.get("clauses") or [])
        )
        hards = "".join(
            f"<span class='chip'>{html.escape(h.get('word') or '')}"
            f" {html.escape(h.get('meaning') or '')}</span>"
            for h in (struct.get("hard_words") or [])
        )
        sent_blocks.append(
            f"<div class='card'><p class='en'>{html.escape(s['text'])}</p>"
            f"<p class='zh'>{html.escape(s['translation'] or '')}</p>"
            f"<p><b>主干：</b>{html.escape(struct.get('main') or '')}</p>"
            f"<ul>{clauses}</ul><p>{hards}</p>"
            f"<p class='meta'>{html.escape(s['created_at'])}</p></div>"
        )
    sent_html = "".join(sent_blocks) or "<p>暂无长难句</p>"

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>Englearn 学习导出</title>
<style>
body{{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;max-width:900px;margin:40px auto;padding:0 20px;color:#1f2937;background:#f8fafc}}
h1{{font-size:24px}} h2{{margin-top:36px;border-left:4px solid #10b981;padding-left:10px}}
table{{width:100%;border-collapse:collapse;background:#fff}}
th,td{{border:1px solid #e5e7eb;padding:8px 10px;text-align:left;font-size:14px}}
th{{background:#f1f5f9}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:16px;margin:12px 0}}
.en{{font-weight:600}} .zh{{color:#475569}}
.chip{{display:inline-block;background:#ecfdf5;color:#047857;border-radius:999px;padding:2px 10px;margin:2px 6px 2px 0;font-size:13px}}
.meta{{color:#94a3b8;font-size:12px}}
</style></head><body>
<h1>Englearn 学习导出</h1>
<p>导出时间：{now}　｜　生词 {len(words)} 个　｜　长难句 {len(sentences)} 句</p>
<h2>生词本</h2>
<table><thead><tr><th>单词</th><th>音标</th><th>释义</th><th>状态</th><th>次数</th></tr></thead>
<tbody>{word_rows}</tbody></table>
<h2>长难句精析</h2>
{sent_html}
</body></html>"""


BUILDERS = {
    "md": ("markdown", build_markdown, "text/markdown; charset=utf-8"),
    "json": ("json", build_json, "application/json; charset=utf-8"),
    "csv": ("csv", build_csv, "text/csv; charset=utf-8"),
    "anki": ("anki", build_anki, "text/plain; charset=utf-8"),
    "html": ("html", build_html, "text/html; charset=utf-8"),
}


def write_export(store, fmt: str) -> dict:
    fmt = (fmt or "md").lower()
    if fmt not in BUILDERS:
        raise ValueError(f"不支持的格式：{fmt}")
    _, builder, _ = BUILDERS[fmt]
    content = builder(store)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"englearn-{stamp}.{EXT[fmt]}"
    path = EXPORT_DIR / filename
    if fmt == "csv":
        path.write_text("\ufeff" + content, encoding="utf-8")  # Excel 友好
    else:
        path.write_text(content, encoding="utf-8")
    return {"format": fmt, "filename": filename, "path": str(path), "content": content}
