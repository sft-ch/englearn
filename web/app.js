/* Englearn 前端逻辑：无框架，原生 DOM。 */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const state = {
  health: null,
  config: null,
  tab: "words",
  words: [],
  sentences: [],
  history: [],
  day: null,
  dayDate: new Date().toISOString().slice(0, 10),
  expanded: null,
  current: null,
  query: "",
  wordKind: "",
  kindCounts: { all: 0, word: 0, phrase: 0, sentence: 0 },
  busy: false,
};

const ESC_MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ESC_MAP[c]);

const KIND_LABEL = { word: "单词", phrase: "短语", sentence: "句子" };
const UNIT_LABEL = { word: "单词", phrase: "短语", sentence: "短句" };
const STATUS_LABEL = { new: "新词", learning: "学习中", known: "已掌握" };
const STATUS_NEXT = { new: "learning", learning: "known", known: "new" };

let toastTimer = null;

function toast(msg, kind = "") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = `toast ${kind}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 3600);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let data;
  try {
    data = await res.json();
  } catch {
    throw new Error(`服务返回异常（HTTP ${res.status}）`);
  }
  if (!res.ok || data.ok === false) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

/* ---------------- 状态栏 ---------------- */
async function refreshHealth() {
  const h = await api("/api/health");
  state.health = h;
  const pill = $("#status-pill");
  if (h.mock) {
    pill.textContent = "MOCK 演示模式";
    pill.className = "pill warn";
  } else if (h.has_key) {
    pill.textContent = `已连接 · ${h.model || "模型"}`;
    pill.className = "pill ok";
  } else {
    pill.textContent = "未配置 API Key";
    pill.className = "pill bad";
  }
  const hotkey = (h.hotkey || "alt+d").split("+").map((s) => s.toUpperCase()).join("+");
  const kbd = $("#kbd-hotkey");
  if (kbd) kbd.textContent = hotkey;
}

/* ---------------- 分析 ---------------- */
function setBusy(busy) {
  state.busy = busy;
  const btn = $("#btn-analyze");
  btn.disabled = busy;
  btn.innerHTML = busy ? "分析中…" : "分析 <kbd>Ctrl</kbd>+<kbd>Enter</kbd>";
}

async function analyze(text) {
  const value = (text ?? $("#input").value).trim();
  if (!value) return toast("先输入或取词一段英文");
  if (state.busy) return;
  setBusy(true);
  try {
    const r = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ text: value, mode: $("#mode").value }),
    });
    renderResult(r);
    await Promise.all([loadWords(), loadHistory()]);
  } catch (e) {
    renderError(e.message);
    toast(e.message, "error");
  } finally {
    setBusy(false);
  }
}

async function captureSelection() {
  try {
    const r = await api("/api/capture", { method: "POST", body: "{}" });
    $("#input").value = r.text;
    updateCounter();
    await analyze(r.text);
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ---------------- 结果渲染 ---------------- */
function renderError(message) {
  $("#result").innerHTML = `<div class="error-box"><b>分析失败</b><br>${esc(message)}</div>`;
}

function renderResult(payload, opts = {}) {
  const data = payload.data || payload;
  const kind = data.type || "sentence";
  state.current = payload;

  const badges = [`<span class="badge">${KIND_LABEL[kind] || kind}</span>`];
  if (kind === "sentence") badges.push('<span class="badge gray">长难句</span>');
  if (data.mock) badges.push('<span class="badge mock">MOCK</span>');

  let html = `<div class="res-head">
      <div>${badges.join(" ")}</div>
      <span class="muted">${payload.elapsed ? payload.elapsed + " 秒" : ""}</span>
    </div>`;

  const marks = payload.sentenceId ? payload.marks || [] : [];
  if (kind === "sentence") {
    html += `<div class="en-block">${renderMarked(data.text, marks)}</div>`;
    if (data.translation) html += `<div class="zh-block">${esc(data.translation)}</div>`;
    if (payload.sentenceId) html += renderMarkTools(marks);
    html += renderStructure(data.structure || {});
  } else {
    html += renderWordCard(data);
  }

  const canSave = payload.record && payload.record.id;
  html += `<div class="res-actions">
      ${canSave ? `<button class="btn primary" id="btn-save">${kind === "sentence" ? "收藏句子" : "加入生词本"}</button>` : ""}
      <button class="btn ghost" id="btn-copy">复制译文</button>
    </div>`;

  const box = $("#result");
  box.innerHTML = html;
  box.scrollTop = 0;

  if ($("#btn-save")) $("#btn-save").onclick = () => saveCurrent(kind);
  $("#btn-copy").onclick = async () => {
    try {
      await navigator.clipboard.writeText(data.translation || data.text);
      toast("已复制");
    } catch {
      toast("复制失败，请手动选择文本", "error");
    }
  };
  $$(".chip", box).forEach((chip) => {
    chip.onclick = () => {
      $("#input").value = chip.dataset.word;
      updateCounter();
      analyze(chip.dataset.word);
    };
  });

  if ($("#btn-mark")) $("#btn-mark").onclick = addMark;
  $$(".mark-chip", box).forEach((chip) => {
    chip.onclick = () => removeMark(Number(chip.dataset.idx));
  });
  $$("mark.vocab-mark", box).forEach((markEl) => {
    markEl.onclick = () => lookupWord(markEl.dataset.word);
  });

  if (opts.detail) enterDetail(opts.title || "详情");
  else exitDetail();
}

/* ---------------- 词汇卡片 ---------------- */
function renderWordCard(data) {
  const uk = data.phonetic_uk || (typeof data.phonetic === "string" ? data.phonetic : "");
  const us = data.phonetic_us || "";
  const none = `<div class="muted small">暂无</div>`;
  const sec = (title, body) =>
    `<div class="card-sec"><div class="card-sec-title">${title}</div>${body}</div>`;

  let html = `<div class="res-title"><h2>${esc(data.text)}</h2></div>
    <div class="phonetics">
      ${uk ? `<span class="ph-item">英 <b>${esc(uk)}</b></span>` : ""}
      ${us ? `<span class="ph-item">美 <b>${esc(us)}</b></span>` : ""}
      ${data.pos ? `<span class="ph-item">${esc(data.pos)}</span>` : ""}
    </div>`;

  html += sec("释义", data.senses?.length
    ? `<ul class="senses">${data.senses
        .map((s) => `<li><span class="pos-tag">${esc(s.pos || "")}</span>${esc(s.meaning)}</li>`)
        .join("")}</ul>`
    : (data.translation ? `<div class="zh-block">${esc(data.translation)}</div>` : none));

  html += sec("熟词生义", data.familiar?.length
    ? data.familiar
        .map((f) => `<div class="card-row">
          <div><b>${esc(f.sense)}</b>${f.pos ? ` <span class="pos-tag">${esc(f.pos)}</span>` : ""}</div>
          ${f.note ? `<div class="muted small">${esc(f.note)}</div>` : ""}
          ${f.example ? `<div class="ex-en">${esc(f.example)}</div>` : ""}
        </div>`)
        .join("")
    : `<div class="muted small">无常见熟词生义</div>`);

  html += sec("短语搭配", data.phrases?.length
    ? data.phrases
        .map((p) => `<div class="card-row"><b>${esc(p.en)}</b>
          <span class="muted">${esc(p.zh)}</span></div>`)
        .join("")
    : none);

  html += sec("例句", data.examples?.length
    ? `<div class="examples">${data.examples
        .map((e) => `<div class="ex"><div class="en">${esc(e.en)}</div>
          <div class="zh">${esc(e.zh)}</div></div>`)
        .join("")}</div>`
    : none);

  html += sec("派生词", data.derivatives?.length
    ? data.derivatives
        .map((d) => `<div class="card-row"><b>${esc(d.word)}</b>
          ${d.pos ? `<span class="pos-tag">${esc(d.pos)}</span>` : ""}
          <span>${esc(d.meaning)}</span></div>`)
        .join("")
    : none);

  html += sec("类似词", data.similar?.length
    ? data.similar
        .map((s) => `<div class="card-row"><b>${esc(s.word)}</b>
          ${s.relation ? `<span class="badge gray">${esc(s.relation)}</span>` : ""}
          ${s.note ? `<div class="muted small">${esc(s.note)}</div>` : ""}</div>`)
        .join("")
    : none);

  return html;
}

/* ---------------- 句子里的自定义标记 ---------------- */
function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function renderMarked(text, marks) {
  const words = (marks || []).map((m) => m.word).filter(Boolean);
  if (!words.length) return esc(text);
  const sorted = [...words].sort((a, b) => b.length - a.length);
  const pattern = sorted
    .map((w) => {
      const lead = /^\w/.test(w) ? "\\b" : "";
      const tail = /\w$/.test(w) ? "\\b" : "";
      return lead + escapeRe(w) + tail;
    })
    .join("|");
  const parts = text.split(new RegExp(`(${pattern})`, "gi"));
  return parts
    .map((part, i) => {
      if (i % 2 === 1) {
        const idx = marks.findIndex(
          (m) => String(m.word).toLowerCase() === part.toLowerCase()
        );
        return `<mark class="vocab-mark" data-word="${esc(part)}" title="点击生成词汇卡片">${esc(part)}</mark>`;
      }
      return esc(part);
    })
    .join("");
}

function renderMarkTools(marks) {
  const chips = marks.length
    ? `<div class="marks">${marks
        .map(
          (m, i) => `<span class="mark-chip" data-idx="${i}" title="点击取消标记">
            ${esc(m.word)}<i>×</i></span>`
        )
        .join("")}</div>`
    : `<div class="marks muted">还没有标记：选中句中的词，再点左边按钮</div>`;
  return `<div class="mark-tools">
      <button class="btn ghost tiny" id="btn-mark">标记陌生词</button>
      <span class="muted">先在上面的句子里选中一个词或短语</span>
    </div>${chips}`;
}

async function addMark() {
  const payload = state.current;
  if (!payload?.sentenceId) return;
  const sel = window.getSelection();
  const text = (sel?.toString() || "").replace(/\s+/g, " ").trim();
  if (!text) return toast("先在句子里选中一个词");
  if (text.length > 60) return toast("标记太长，选一个词或短语就好");
  const node = sel.anchorNode;
  const el = node && node.nodeType === 3 ? node.parentElement : node;
  if (!el?.closest?.(".en-block")) return toast("请选中句子里面的词");

  const marks = [...(payload.marks || [])];
  if (marks.some((m) => String(m.word).toLowerCase() === text.toLowerCase())) {
    return toast("这个词已经标记过了");
  }
  marks.push({ word: text, note: "" });
  try {
    const r = await api(`/api/sentences/${payload.sentenceId}`, {
      method: "PATCH",
      body: JSON.stringify({ marks }),
    });
    payload.marks = r.sentence.marks || marks;
    renderResult(payload, { detail: true, title: "长难句详情" });
    await loadSentences();
    toast(`已标记：${text}`);
  } catch (e) {
    toast(e.message, "error");
  }
}

async function removeMark(idx) {
  const payload = state.current;
  if (!payload?.sentenceId || Number.isNaN(idx)) return;
  const marks = [...(payload.marks || [])];
  const [removed] = marks.splice(idx, 1);
  try {
    const r = await api(`/api/sentences/${payload.sentenceId}`, {
      method: "PATCH",
      body: JSON.stringify({ marks }),
    });
    payload.marks = r.sentence.marks || marks;
    renderResult(payload, { detail: true, title: "长难句详情" });
    await loadSentences();
    if (removed) toast(`已取消标记：${removed.word}`);
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ---------------- 详情模式：左栏整页显示 ---------------- */
function enterDetail(title) {
  $(".col-left").classList.add("detail");
  $("#detail-bar").classList.remove("hidden");
  $("#detail-title").textContent = title || "详情";
}

function exitDetail() {
  state.backTo = null;
  $(".col-left").classList.remove("detail");
  $("#detail-bar").classList.add("hidden");
}

/** 标记词 → 生成词汇卡片；返回时回到原来的长难句 */
async function lookupWord(word) {
  const w = String(word || "").trim();
  if (!w) return;
  state.backTo = state.current || null;
  try {
    const r = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ text: w, mode: "word", source: "标记词" }),
    });
    renderResult(r, { detail: true, title: "词汇卡片" });
    await loadHistory();
  } catch (e) {
    toast(e.message, "error");
  }
}

function goBack() {
  if (state.backTo) {
    const prev = state.backTo;
    state.backTo = null;
    renderResult(prev, { detail: true, title: "长难句详情" });
    return;
  }
  exitDetail();
}

function renderStructure(st) {
  const hasAny = st.main || st.clauses?.length || st.modifiers?.length || st.hard_words?.length;
  if (!hasAny) return "";
  let html = `<div class="section-title">句子结构</div>`;
  if (st.main) html += `<div class="struct-main"><b>主干</b>　${esc(st.main)}</div>`;
  for (const c of st.clauses || []) {
    html += `<div class="clause" style="margin-top:8px">
        <span class="tag">${esc(c.type || "从句")}</span><span class="text">${esc(c.text)}</span>
        <div class="explain">${esc(c.explain)}</div>
      </div>`;
  }
  for (const m of st.modifiers || []) {
    html += `<div class="modifier">
        <span class="tag">修饰</span><span class="text">${esc(m.text)}</span>
        <div class="explain">${esc(m.explain)}</div>
      </div>`;
  }
  if (st.hard_words?.length) {
    html += `<div class="section-title">难点词汇</div><div class="hard-words">${st.hard_words
      .map((h) => `<span class="chip" data-word="${esc(h.word)}" data-meaning="${esc(h.meaning)}">
          <b>${esc(h.word)}</b><span>${esc(h.meaning)}</span></span>`)
      .join("")}</div>`;
  }
  if (st.difficulty) html += `<div class="difficulty">难点：${esc(st.difficulty)}</div>`;
  return html;
}

async function saveCurrent(kind) {
  if (!state.current?.record?.id) return toast("没有可保存的记录", "error");
  try {
    if (kind === "sentence") {
      const r = await api("/api/sentences", {
        method: "POST",
        body: JSON.stringify({ record_id: state.current.record.id }),
      });
      toast("句子已收藏");
      if (r.sentence) await loadHistory();
    } else {
      const r = await api("/api/words", {
        method: "POST",
        body: JSON.stringify({ record_id: state.current.record.id }),
      });
      toast(`已加入生词本：${r.word.lemma}`);
      await loadWords();
    }
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ---------------- 列表 ---------------- */
async function loadWords() {
  const data = await api("/api/words");
  state.words = data.words || [];
  state.kindCounts = data.kinds || state.kindCounts;
  renderList();
}

async function loadHistory() {
  const data = await api("/api/history?limit=80");
  state.history = data.records || [];
  $("#cnt-history").textContent = state.history.length;
  renderList();
}

async function loadSentences() {
  const data = await api("/api/sentences");
  state.sentences = data.sentences || [];
  if ($("#cnt-sentences")) $("#cnt-sentences").textContent = state.sentences.length;
  renderList();
}

async function loadDay(date) {
  const target = date || state.dayDate;
  const data = await api(`/api/day?date=${encodeURIComponent(target)}`);
  state.day = data;
  state.dayDate = data.date;
  if (state.tab === "day") renderList();
}

function renderWordItem(w) {
  const kind = w.kind || "word";
  return `<div class="item" data-word-id="${w.id}" title="点击查看详情">
      <div class="row1">
        <span class="status-dot ${esc(w.status)}"></span>
        <span class="kind-tag ${esc(kind)}">${UNIT_LABEL[kind] || "单词"}</span>
        <span class="lemma">${esc(w.lemma)}</span>
        <span class="ts" style="margin-left:auto">×${w.cnt}</span>
      </div>
      <div class="meaning">${esc(w.meaning || "—")}</div>
    </div>`;
}

function renderKindFilter() {
  const c = state.kindCounts || {};
  const item = (key, label) => {
    const n = key === "" ? c.all || 0 : c[key] || 0;
    return `<button class="chip-btn ${state.wordKind === key ? "on" : ""}"
       data-kind="${key}">${label} ${n}</button>`;
  };
  return `<div class="kind-filter">
      ${item("", "全部")}${item("word", "单词")}${item("phrase", "短语")}${item("sentence", "短句")}
    </div>`;
}

function renderWordPage(w) {
  state.current = null;
  state.backTo = null;
  const statusBtn = ["new", "learning", "known"]
    .map(
      (s) => `<button class="chip-btn ${w.status === s ? "on" : ""}"
        data-status="${s}" data-wid="${w.id}">${STATUS_LABEL[s]}</button>`
    )
    .join("");
  $("#result").innerHTML = `
    <div class="res-head">
      <div><span class="badge">${UNIT_LABEL[w.kind] || "单词"}</span>
        <span class="badge gray">${STATUS_LABEL[w.status] || w.status}</span></div>
      <span class="muted">出现 ${w.cnt} 次</span>
    </div>
    <div class="res-title"><h2>${esc(w.lemma)}</h2>
      ${w.phonetic ? `<span class="phonetic">${esc(w.phonetic)}</span>` : ""}</div>
    <div class="zh-block">${esc(w.meaning || "—")}</div>
    ${w.example ? `<div class="section-title">例句</div>
      <div class="examples"><div class="ex"><div class="en">${esc(w.example)}</div></div></div>` : ""}
    <div class="section-title">备注</div>
    <input class="note-input wide" data-note="${w.id}" value="${esc(w.note || "")}"
           placeholder="写下记忆点，回车保存">
    <div class="meta-grid">
      <div><span class="d-k">来源</span>${esc(w.source || "—")}</div>
      <div><span class="d-k">首次</span>${esc(w.first_seen)}</div>
      <div><span class="d-k">最近</span>${esc(w.last_seen)}</div>
    </div>
    <div class="res-actions">${statusBtn}
      <button class="chip-btn" data-card-word="${w.id}">生成词汇卡片</button>
      <button class="chip-btn danger" data-del-word="${w.id}">删除</button>
    </div>`;
  $("#result").scrollTop = 0;
  enterDetail("生词详情");
  bindWordActions();
}

function bindWordActions() {
  $$("[data-status]").forEach((btn) => {
    btn.onclick = async () => {
      try {
        await api(`/api/words/${btn.dataset.wid}`, {
          method: "PATCH",
          body: JSON.stringify({ status: btn.dataset.status }),
        });
        toast("状态已更新");
        await loadWords();
        await refreshDayIfOpen();
        const w = state.words.find((x) => String(x.id) === String(btn.dataset.wid));
        if (w) renderWordPage(w);
      } catch (e) {
        toast(e.message, "error");
      }
    };
  });

  $$("[data-note]").forEach((input) => {
    input.onkeydown = async (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      try {
        await api(`/api/words/${input.dataset.note}`, {
          method: "PATCH",
          body: JSON.stringify({ note: input.value }),
        });
        toast("备注已保存");
        input.blur();
        await loadWords();
      } catch (e) {
        toast(e.message, "error");
      }
    };
  });

  $$("[data-del-word]").forEach((el) => {
    el.onclick = async () => {
      if (!confirm("删除这个生词？")) return;
      try {
        await api(`/api/words/${el.dataset.delWord}`, { method: "DELETE" });
        await loadWords();
        await refreshDayIfOpen();
        exitDetail();
        $("#result").innerHTML = `<div class="empty-hint">已删除，从右侧继续选择</div>`;
      } catch (e) {
        toast(e.message, "error");
      }
    };
  });

  $$("[data-card-word]").forEach((btn) => {
    btn.onclick = () => {
      const w = state.words.find((x) => String(x.id) === String(btn.dataset.cardWord));
      if (w) lookupWord(w.lemma);
    };
  });
}

function renderSentenceItem(s) {
  const markCount = (s.marks || []).length;
  return `<div class="item" data-sid="${s.id}">
      <div class="row1">
        <span class="badge gray">长难句</span>
        ${markCount ? `<span class="badge mark-badge">${markCount} 处标记</span>` : ""}
        <span class="ts">${esc((s.created_at || "").slice(0, 10))}</span>
        <span class="del" data-del-sent="${s.id}" style="margin-left:auto">删除</span>
      </div>
      <div class="meaning">${esc((s.text || "").slice(0, 90))}</div>
    </div>`;
}

function renderDay(q) {
  const d = state.day || {};
  const day = d.date || state.dayDate;
  const words = (d.words || []).filter(
    (w) => !q || `${w.lemma}${w.meaning}`.toLowerCase().includes(q)
  );
  const sents = (d.sentences || []).filter(
    (s) => !q || (s.text || "").toLowerCase().includes(q)
  );
  const head = `<div class="daybar">
      <button class="day-nav" data-shift="-1">‹</button>
      <input type="date" id="day-date" value="${esc(day)}">
      <button class="day-nav" data-shift="1">›</button>
      <button class="day-today">今天</button>
    </div>
    <div class="day-stats">生词 ${words.length} · 长难句 ${sents.length} ·
      分析记录 ${(d.records || []).length}</div>`;
  const wHtml = words.length
    ? words.map(renderWordItem).join("")
    : `<div class="empty-hint">这天没有新增生词</div>`;
  const sHtml = sents.length
    ? sents.map(renderSentenceItem).join("")
    : `<div class="empty-hint">这天没有收藏的句子</div>`;
  return `${head}
    <div class="day-title">当天新增生词</div>${wHtml}
    <div class="day-title">当天收藏的句子</div>${sHtml}`;
}

function renderList() {
  const list = $("#list");
  const q = state.query.toLowerCase();
  $("#cnt-words").textContent = state.words.length;
  if ($("#cnt-sentences")) $("#cnt-sentences").textContent = state.sentences.length;

  if (state.tab === "words") {
    const byKind = state.words.filter((w) => !state.wordKind || (w.kind || "word") === state.wordKind);
    const rows = byKind.filter(
      (w) => !q || `${w.lemma} ${w.meaning} ${w.note}`.toLowerCase().includes(q)
    );
    const head = renderKindFilter();
    if (!rows.length) {
      list.innerHTML = head + `<div class="empty-hint">${
        q ? "没有匹配的条目" : "这一类还没有条目"
      }</div>`;
      bindListEvents();
      return;
    }
    list.innerHTML = head + rows.map(renderWordItem).join("");
  } else if (state.tab === "sentences") {
    const rows = state.sentences.filter(
      (s) => !q || `${s.text} ${s.translation}`.toLowerCase().includes(q)
    );
    if (!rows.length) {
      list.innerHTML = `<div class="empty-hint">${q ? "没有匹配的长难句" : "还没有收藏的长难句<br>分析句子后点「收藏句子」"}</div>`;
      return;
    }
    list.innerHTML = rows.map(renderSentenceItem).join("");
  } else if (state.tab === "day") {
    list.innerHTML = renderDay(q);
  } else {
    const rows = state.history.filter((r) => !q || (r.text || "").toLowerCase().includes(q));
    if (!rows.length) {
      list.innerHTML = `<div class="empty-hint">${q ? "没有匹配的记录" : "暂无历史记录"}</div>`;
      return;
    }
    list.innerHTML = rows
      .map(
        (r) => `<div class="item" data-rec-id="${r.id}">
          <div class="row1">
            <span class="badge gray">${esc(KIND_LABEL[r.kind] || r.kind)}</span>
            <span class="ts">${esc(r.ts)}</span>
            <span class="del" data-del-rec="${r.id}" style="margin-left:auto">删除</span>
          </div>
          <div class="meaning">${esc((r.text || "").slice(0, 90))}</div>
        </div>`
      )
      .join("");
  }
  bindListEvents();
}

function bindListEvents() {
  // 分类筛选：全部 / 单词 / 短语 / 短句
  $$("[data-kind]", $("#list")).forEach((btn) => {
    btn.onclick = () => {
      state.wordKind = btn.dataset.kind || "";
      renderList();
    };
  });

  // 生词：点击后在左侧整页展示详情
  $$("[data-word-id]", $("#list")).forEach((el) => {
    el.onclick = () => {
      const id = String(el.dataset.wordId);
      const w =
        state.words.find((x) => String(x.id) === id) ||
        (state.day?.words || []).find((x) => String(x.id) === id);
      if (w) renderWordPage(w);
    };
  });

  // 收藏的长难句：点击回看完整解析
  $$("[data-sid]").forEach((el) => {
    el.onclick = (ev) => {
      if (ev.target.dataset.delSent) return;
      const sid = String(el.dataset.sid);
      const sent =
        state.sentences.find((s) => String(s.id) === sid) ||
        (state.day?.sentences || []).find((s) => String(s.id) === sid);
      if (!sent) return;
      const analysis = sent.analysis && Object.keys(sent.analysis).length
        ? sent.analysis
        : { type: "sentence", text: sent.text, translation: sent.translation, structure: {} };
      renderResult(
        { data: analysis, record: { id: null, text: sent.text },
          sentenceId: sent.id, marks: sent.marks || [] },
        { detail: true, title: "长难句详情" }
      );
      state.backTo = null;
      toast("已打开这条长难句");
    };
  });

  $$("[data-del-sent]").forEach((el) => {
    el.onclick = async (ev) => {
      ev.stopPropagation();
      if (!confirm("取消收藏这条句子？")) return;
      try {
        await api(`/api/sentences/${el.dataset.delSent}`, { method: "DELETE" });
        await loadSentences();
        await refreshDayIfOpen();
      } catch (e) {
        toast(e.message, "error");
      }
    };
  });

  $$("[data-rec-id]").forEach((el) => {
    el.onclick = (ev) => {
      if (ev.target.dataset.delRec) return;
      const rec = state.history.find((r) => String(r.id) === el.dataset.recId);
      if (!rec) return;
      try {
        const data = JSON.parse(rec.payload || "{}");
        renderResult({ data, record: rec }, { detail: true, title: "记录详情" });
      } catch {
        toast("这条记录的数据已损坏", "error");
      }
    };
  });

  $$("[data-del-rec]").forEach((el) => {
    el.onclick = async (ev) => {
      ev.stopPropagation();
      try {
        await api(`/api/history/${el.dataset.delRec}`, { method: "DELETE" });
        await loadHistory();
      } catch (e) {
        toast(e.message, "error");
      }
    };
  });

  // 日期导航
  $$(".day-nav").forEach((btn) => {
    btn.onclick = () => shiftDay(Number(btn.dataset.shift));
  });
  const dateInput = $("#day-date");
  if (dateInput) dateInput.onchange = (ev) => loadDay(ev.target.value);
  const todayBtn = $(".day-today");
  if (todayBtn) todayBtn.onclick = () => loadDay(todayStr());
}

function todayStr() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate()
  ).padStart(2, "0")}`;
}

function shiftDay(delta) {
  const base = new Date(`${state.dayDate}T00:00:00`);
  base.setDate(base.getDate() + delta);
  const next = `${base.getFullYear()}-${String(base.getMonth() + 1).padStart(2, "0")}-${String(
    base.getDate()
  ).padStart(2, "0")}`;
  if (next > todayStr()) return toast("已经是最新的一天");
  loadDay(next);
}

async function refreshDayIfOpen() {
  if (state.tab === "day") await loadDay(state.dayDate);
}

/* ---------------- 导出 ---------------- */
async function doExport(format) {
  try {
    const r = await api("/api/export", {
      method: "POST",
      body: JSON.stringify({ format }),
    });
    const blob = new Blob([r.content], { type: "text/plain;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = r.filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    toast(`已导出 ${r.filename}（同时保存在 exports/ 目录）`);
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ---------------- 设置 ---------------- */
async function openSettings() {
  const r = await api("/api/config");
  const c = r.config;
  state.config = c;
  $("#cfg-key").value = "";
  $("#cfg-key").placeholder = c.llm.has_key ? "已保存（留空表示不修改）" : "sk-…";
  $("#cfg-base").value = c.llm.base_url || "";
  $("#cfg-model").value = c.llm.model || "";
  $("#cfg-hotkey").value = c.hotkey || "alt+d";
  $("#cfg-watch").checked = !!c.clipboard_watch;
  $("#cfg-mock").checked = !!c.mock;
  $("#cfg-autostart").checked = !!c.autostart;
  $("#cfg-autostart").disabled = c.autostart_supported === false;
  $("#cfg-hint").textContent = c.llm.has_key ? "已配置 Key" : "尚未配置 Key";
  $("#modal").classList.remove("hidden");
}

async function saveSettings() {
  const body = {
    llm: {
      api_key: $("#cfg-key").value.trim(),
      base_url: $("#cfg-base").value.trim(),
      model: $("#cfg-model").value.trim(),
    },
    hotkey: $("#cfg-hotkey").value.trim(),
    clipboard_watch: $("#cfg-watch").checked,
    mock: $("#cfg-mock").checked,
    autostart: $("#cfg-autostart").checked,
  };
  try {
    const r = await api("/api/config", { method: "POST", body: JSON.stringify(body) });
    $("#modal").classList.add("hidden");
    toast(r.restart_required ? "已保存，热键需重启 Englearn 后生效" : "设置已保存");
    await refreshHealth();
  } catch (e) {
    toast(e.message, "error");
  }
}

/* ---------------- 其它 ---------------- */
function updateCounter() {
  $("#counter").textContent = `${$("#input").value.length} 字符`;
}

function bind() {
  $("#btn-analyze").onclick = () => analyze();
  $("#btn-capture").onclick = captureSelection;
  $("#btn-back").onclick = goBack;
  $("#btn-settings").onclick = openSettings;
  $("#btn-close").onclick = () => $("#modal").classList.add("hidden");
  $("#btn-save").onclick = saveSettings;
  $("#modal").onclick = (ev) => {
    if (ev.target.id === "modal") $("#modal").classList.add("hidden");
  };

  $("#input").addEventListener("input", updateCounter);
  $("#input").addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
      ev.preventDefault();
      analyze();
    }
  });

  $("#search").addEventListener("input", (ev) => {
    state.query = ev.target.value.trim();
    renderList();
  });

  $$(".tab").forEach((tab) => {
    tab.onclick = async () => {
      state.tab = tab.dataset.tab;
      state.expanded = null;
      $$(".tab").forEach((t) => t.classList.toggle("active", t === tab));
      if (state.tab === "sentences" && !state.sentences.length) await loadSentences();
      if (state.tab === "day" && !state.day) await loadDay(state.dayDate);
      renderList();
    };
  });

  $("#btn-export").onclick = (ev) => {
    ev.stopPropagation();
    $("#export-menu").classList.toggle("hidden");
  };
  document.addEventListener("click", (ev) => {
    if (!ev.target.closest(".menu-wrap")) $("#export-menu").classList.add("hidden");
  });
  $$("#export-menu button").forEach((btn) => {
    btn.onclick = () => {
      $("#export-menu").classList.add("hidden");
      doExport(btn.dataset.format);
    };
  });

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") {
      $("#modal").classList.add("hidden");
      exitDetail();
    }
  });
}

function connectSSE() {
  const es = new EventSource("/api/events");
  es.onmessage = (ev) => {
    let msg;
    try {
      msg = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (msg.type === "result") {
      renderResult(msg);
      loadWords();
      loadHistory();
      loadSentences();
      toast("已捕获并分析");
    } else if (msg.type === "error") {
      toast(msg.message, "error");
    }
  };
}

async function init() {
  bind();
  updateCounter();
  try {
    await refreshHealth();
    await Promise.all([loadWords(), loadHistory(), loadSentences()]);
  } catch (e) {
    toast(e.message, "error");
  }
  connectSSE();
}

document.addEventListener("DOMContentLoaded", init);
