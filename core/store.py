"""SQLite 存储：学习记录、生词本、长难句库。"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    kind    TEXT NOT NULL,
    text    TEXT NOT NULL,
    app     TEXT DEFAULT '',
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_records_ts ON records(ts DESC);

CREATE TABLE IF NOT EXISTS words (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lemma      TEXT NOT NULL UNIQUE,
    kind       TEXT DEFAULT '',
    phonetic   TEXT DEFAULT '',
    pos        TEXT DEFAULT '',
    meaning    TEXT DEFAULT '',
    example    TEXT DEFAULT '',
    note       TEXT DEFAULT '',
    status     TEXT DEFAULT 'new',
    tags       TEXT DEFAULT '',
    source     TEXT DEFAULT '',
    cnt        INTEGER DEFAULT 1,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sentences (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    text        TEXT NOT NULL UNIQUE,
    translation TEXT DEFAULT '',
    analysis    TEXT DEFAULT '{}',
    marks       TEXT DEFAULT '[]',
    source      TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);
"""

STATUSES = ("new", "learning", "known")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """老库补列并回填分类。"""
        cols = {row["name"] for row in self._rows("PRAGMA table_info(sentences)")}
        if "marks" not in cols:
            self._exec("ALTER TABLE sentences ADD COLUMN marks TEXT DEFAULT '[]'")

        wcols = {row["name"] for row in self._rows("PRAGMA table_info(words)")}
        if "kind" not in wcols:
            # 用空默认值，让下面的回填把历史条目也归类
            self._exec("ALTER TABLE words ADD COLUMN kind TEXT DEFAULT ''")
        self._backfill_kind()

    def _backfill_kind(self) -> None:
        """把没有分类（或分类为空）的条目按语言单位补上，不覆盖已有分类。"""
        from .units import classify_unit

        rows = self._rows("SELECT id, lemma, kind FROM words")
        for row in rows:
            kind = (row.get("kind") or "").strip()
            if kind in ("word", "phrase", "sentence"):
                continue
            self._exec(
                "UPDATE words SET kind = ? WHERE id = ?",
                (classify_unit(row["lemma"]), row["id"]),
            )

    # ---------- 内部 ----------
    def _rows(self, sql: str, args: tuple = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(sql, args)
            return [dict(r) for r in cur.fetchall()]

    def _one(self, sql: str, args: tuple = ()) -> dict | None:
        rows = self._rows(sql, args)
        return rows[0] if rows else None

    def _exec(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, args)
            self._conn.commit()
            return cur

    # ---------- 记录 ----------
    def add_record(self, kind: str, text: str, app: str, payload: dict) -> dict:
        ts = _now()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO records (ts, kind, text, app, payload) VALUES (?,?,?,?,?)",
                (ts, kind, text, app or "", json.dumps(payload, ensure_ascii=False)),
            )
            self._conn.commit()
            rid = cur.lastrowid
        return {"id": rid, "ts": ts, "kind": kind, "text": text, "app": app or ""}

    def records(self, limit: int = 50, q: str = "") -> list[dict]:
        limit = max(1, min(int(limit or 50), 500))
        if q:
            return self._rows(
                "SELECT * FROM records WHERE text LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{q}%", limit),
            )
        return self._rows("SELECT * FROM records ORDER BY id DESC LIMIT ?", (limit,))

    def record(self, rid: int) -> dict | None:
        return self._one("SELECT * FROM records WHERE id = ?", (rid,))

    def delete_record(self, rid: int) -> None:
        self._exec("DELETE FROM records WHERE id = ?", (rid,))

    # ---------- 生词本 ----------
    def save_word(self, payload: dict, source: str = "") -> dict:
        lemma = (payload.get("text") or payload.get("lemma") or "").strip()
        if not lemma:
            raise ValueError("缺少单词文本")

        senses = payload.get("senses") or []
        meaning = payload.get("meaning") or ""
        pos = payload.get("pos") or ""
        if senses and not meaning:
            parts = []
            for s in senses[:4]:
                p = (s.get("pos") or "").strip()
                m = (s.get("meaning") or "").strip()
                if not m:
                    continue
                parts.append(f"{p} {m}".strip())
            meaning = "；".join(parts)
            pos = pos or (senses[0].get("pos") or "")
        if not meaning and payload.get("translation"):
            meaning = str(payload.get("translation"))[:300]

        example = payload.get("example") or ""
        exs = payload.get("examples") or []
        if not example and exs:
            e = exs[0]
            example = (e.get("en") or "").strip()
            zh = (e.get("zh") or "").strip()
            if example and zh:
                example = f"{example}  —— {zh}"

        phonetic = payload.get("phonetic") or ""
        from .units import classify_unit

        kind = payload.get("type")
        if kind not in ("word", "phrase", "sentence"):
            kind = classify_unit(lemma)
        now = _now()
        existing = self._one("SELECT * FROM words WHERE lemma = ?", (lemma,))
        if existing:
            self._exec(
                "UPDATE words SET cnt = cnt + 1, last_seen = ?, kind = ?, "
                "phonetic = COALESCE(NULLIF(?, ''), phonetic), "
                "pos = COALESCE(NULLIF(?, ''), pos), "
                "meaning = COALESCE(NULLIF(?, ''), meaning), "
                "example = COALESCE(NULLIF(?, ''), example), "
                "source = COALESCE(NULLIF(?, ''), source) "
                "WHERE id = ?",
                (now, kind, phonetic, pos, meaning, example, source, existing["id"]),
            )
            row_id = existing["id"]
        else:
            cur = self._exec(
                "INSERT INTO words (lemma, kind, phonetic, pos, meaning, example, source, "
                "first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?,?)",
                (lemma, kind, phonetic, pos, meaning, example, source, now, now),
            )
            row_id = cur.lastrowid
        return self._one("SELECT * FROM words WHERE id = ?", (row_id,)) or {}

    def words(self, q: str = "", status: str = "", kind: str = "",
              limit: int = 300) -> list[dict]:
        sql = "SELECT * FROM words WHERE 1=1"
        args: list = []
        if status in STATUSES:
            sql += " AND status = ?"
            args.append(status)
        if kind in ("word", "phrase", "sentence"):
            sql += " AND kind = ?"
            args.append(kind)
        if q:
            sql += " AND (lemma LIKE ? OR meaning LIKE ?)"
            args.extend([f"%{q}%", f"%{q}%"])
        sql += " ORDER BY last_seen DESC LIMIT ?"
        args.append(max(1, min(int(limit or 300), 1000)))
        return self._rows(sql, tuple(args))

    def word_kind_counts(self) -> dict:
        rows = self._rows("SELECT kind, COUNT(*) AS n FROM words GROUP BY kind")
        counts = {"word": 0, "phrase": 0, "sentence": 0}
        for row in rows:
            key = row.get("kind") or "word"
            counts[key] = counts.get(key, 0) + row["n"]
        counts["all"] = sum(counts[k] for k in ("word", "phrase", "sentence"))
        return counts

    def update_word(self, wid: int, fields: dict) -> dict | None:
        allowed = {}
        if "status" in fields and fields["status"] in STATUSES:
            allowed["status"] = fields["status"]
        if "note" in fields:
            allowed["note"] = str(fields["note"])[:2000]
        if "tags" in fields:
            allowed["tags"] = str(fields["tags"])[:200]
        if not allowed:
            return self._one("SELECT * FROM words WHERE id = ?", (wid,))
        sets = ", ".join(f"{k} = ?" for k in allowed)
        self._exec(f"UPDATE words SET {sets} WHERE id = ?", (*allowed.values(), wid))
        return self._one("SELECT * FROM words WHERE id = ?", (wid,))

    def delete_word(self, wid: int) -> None:
        self._exec("DELETE FROM words WHERE id = ?", (wid,))

    # ---------- 句子 ----------
    def save_sentence(self, text: str, translation: str, analysis: dict, source: str = "") -> dict:
        text = text.strip()
        if not text:
            raise ValueError("缺少句子文本")
        now = _now()
        existing = self._one("SELECT * FROM sentences WHERE text = ?", (text,))
        payload = json.dumps(analysis or {}, ensure_ascii=False)
        if existing:
            self._exec(
                "UPDATE sentences SET translation = ?, analysis = ?, source = ? WHERE id = ?",
                (translation or existing["translation"], payload, source or existing["source"], existing["id"]),
            )
            sid = existing["id"]
        else:
            cur = self._exec(
                "INSERT INTO sentences (text, translation, analysis, source, created_at) VALUES (?,?,?,?,?)",
                (text, translation or "", payload, source or "", now),
            )
            sid = cur.lastrowid
        return self._one("SELECT * FROM sentences WHERE id = ?", (sid,)) or {}

    def sentences(self, limit: int = 200) -> list[dict]:
        return self._rows("SELECT * FROM sentences ORDER BY id DESC LIMIT ?", (int(limit),))

    def sentence(self, sid: int) -> dict | None:
        return self._one("SELECT * FROM sentences WHERE id = ?", (sid,))

    def sentences_on(self, day: str, limit: int = 200) -> list[dict]:
        return self._rows(
            "SELECT * FROM sentences WHERE created_at LIKE ? ORDER BY id DESC LIMIT ?",
            (f"{day}%", int(limit)),
        )

    def delete_sentence(self, sid: int) -> None:
        self._exec("DELETE FROM sentences WHERE id = ?", (sid,))

    def update_sentence_marks(self, sid: int, marks: list) -> dict | None:
        clean: list[dict] = []
        seen: set[str] = set()
        for item in (marks or [])[:80]:
            if not isinstance(item, dict):
                continue
            word = str(item.get("word") or "").strip()[:60]
            if not word or word.lower() in seen:
                continue
            seen.add(word.lower())
            clean.append({"word": word, "note": str(item.get("note") or "")[:200]})
        self._exec(
            "UPDATE sentences SET marks = ? WHERE id = ?",
            (json.dumps(clean, ensure_ascii=False), sid),
        )
        return self._one("SELECT * FROM sentences WHERE id = ?", (sid,))

    def word(self, wid: int) -> dict | None:
        return self._one("SELECT * FROM words WHERE id = ?", (wid,))

    def words_on(self, day: str, limit: int = 300) -> list[dict]:
        return self._rows(
            "SELECT * FROM words WHERE first_seen LIKE ? ORDER BY id DESC LIMIT ?",
            (f"{day}%", int(limit)),
        )

    def records_on(self, day: str, limit: int = 300) -> list[dict]:
        return self._rows(
            "SELECT * FROM records WHERE ts LIKE ? ORDER BY id DESC LIMIT ?",
            (f"{day}%", int(limit)),
        )

    def days(self, limit: int = 60) -> list[dict]:
        """有学习记录的日期及当天数量，供日历使用。"""
        return self._rows(
            """
            SELECT day,
                   SUM(w) AS words,
                   SUM(s) AS sentences,
                   SUM(r) AS records
            FROM (
                SELECT substr(first_seen, 1, 10) AS day, 1 AS w, 0 AS s, 0 AS r FROM words
                UNION ALL
                SELECT substr(created_at, 1, 10) AS day, 0, 1, 0 FROM sentences
                UNION ALL
                SELECT substr(ts, 1, 10) AS day, 0, 0, 1 FROM records
            )
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            (int(limit),),
        )

    def stats(self) -> dict:
        words = self._one("SELECT COUNT(*) AS n FROM words") or {"n": 0}
        known = self._one("SELECT COUNT(*) AS n FROM words WHERE status = 'known'") or {"n": 0}
        records = self._one("SELECT COUNT(*) AS n FROM records") or {"n": 0}
        sentences = self._one("SELECT COUNT(*) AS n FROM sentences") or {"n": 0}
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = self._one(
            "SELECT COUNT(*) AS n FROM records WHERE ts LIKE ?", (f"{today}%",)
        ) or {"n": 0}
        return {
            "words": words["n"],
            "known": known["n"],
            "records": records["n"],
            "sentences": sentences["n"],
            "today": today_records["n"],
            "kinds": self.word_kind_counts(),
        }
