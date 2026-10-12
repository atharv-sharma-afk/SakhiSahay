/* ==========================================================================
   Ask Sakhi - RAG assistant UI. Talks to /api/chat; falls back to the small
   built-in knowledge base (translations.js) when the backend is unreachable
   and says so in the reply.
   ========================================================================== */
(function () {
  const api = window.SakhiApi;
  const D = window.SakhiDates;

  function escapeHtml(str) {
    return String(str == null ? "" : str).replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));
  }

  function renderMarkdown(rawText, sources) {
    if (!rawText) return "";
    let text = escapeHtml(rawText);
    text = text.replace(/\[S(\d+)\]/g, (m, num) => {
      const idx = parseInt(num, 10);
      const tip = sources && sources[idx - 1] && sources[idx - 1].name ? sources[idx - 1].name : `Source ${num}`;
      return `<span class="cite-pill" title="${escapeHtml(tip)}">${num}</span>`;
    });
    const lines = text.split("\n");
    const out = [];
    let list = null; // "ul" | "ol"
    const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
    for (let line of lines) {
      line = line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/__(.+?)__/g, "<strong>$1</strong>");
      line = line.replace(/(^|[^*])\*(?!\*)([^*]+?)\*(?!\*)/g, "$1<em>$2</em>");
      const h = line.match(/^(#{1,3})\s+(.+)$/);
      if (h) { closeList(); out.push(`<h4 class="font-bold text-[var(--rose-deep)] mt-3 mb-1">${h[2]}</h4>`); continue; }
      const bullet = line.match(/^\s*[*\-•]\s+(.+)$/);
      if (bullet) { if (list !== "ul") { closeList(); out.push('<ul class="space-y-1.5 my-2 pl-1">'); list = "ul"; } out.push(`<li class="flex gap-2"><span class="w-1.5 h-1.5 rounded-full bg-[var(--rose-deep)] shrink-0 mt-2"></span><span class="flex-1">${bullet[1]}</span></li>`); continue; }
      const num = line.match(/^\s*(\d+)\.\s+(.+)$/);
      if (num) { if (list !== "ol") { closeList(); out.push('<ol class="space-y-1.5 my-2 pl-1">'); list = "ol"; } out.push(`<li class="flex gap-2"><span class="font-bold text-[var(--rose-deep)] text-xs mt-0.5">${num[1]}.</span><span class="flex-1">${num[2]}</span></li>`); continue; }
      closeList();
      if (line.trim() === "") out.push('<div class="h-2"></div>');
      else out.push(`<p class="mb-2">${line}</p>`);
    }
    closeList();
    return out.join("");
  }

  async function generateResponse(question) {
    const lang = AppState.lang || "en";
    try {
      const data = await api.chat(question, lang);
      const sources = (data.sources || []).map((s) => ({
        name: s.publisher ? `${s.publisher} — ${s.title}` : s.title,
        doc: s.topic ? s.topic.replace(/_/g, " ") : s.doc_type || "",
        url: s.url || null,
        excerpt: s.excerpt || null,
        cited: s.cited,
      }));
      const cited = sources.filter((s) => s.cited);
      return { text: data.answer, sources: cited.length ? cited : sources.slice(0, 3), mode: data.mode, disclaimer: data.disclaimer, notices: data.notices || [] };
    } catch (err) {
      if (err instanceof api.ApiError && !err.isNetwork && err.code !== "server") {
        // e.g. 503 "index not built" or 422: surface the real message
        return { text: err.message, sources: [], mode: "error" };
      }
      console.warn("Chat backend unavailable, using static fallback:", err.message);
    }
    const KB = window.SAKHI_KNOWLEDGE_BASE || {};
    const q = question.toLowerCase();
    let match = KB.default;
    if (/cramp|pain|dard|मरोड़|दर्द/.test(q)) match = KB.cramps;
    else if (/phase|cycle|follicular|luteal|चरण|चक्र/.test(q)) match = KB.phases;
    else if (/bloat|pms|pet phool|water|ब्लोटिंग/.test(q)) match = KB.bloating;
    else if (/twinge|mittelschmerz|खिंचाव/.test(q)) match = KB.twinges;
    if (!match) return { text: t("ai.offline_generic"), sources: [], mode: "offline" };
    const text = match[lang] || match.en;
    return { text: `${text}\n\n_${t("ai.offline_note")}_`, sources: match.sources || [], mode: "offline" };
  }

  function appendUser(text) {
    const c = document.getElementById("chat-messages-container");
    const wrap = document.createElement("div");
    wrap.className = "flex justify-end animate-fade-in";
    wrap.innerHTML = `<div class="bubble-user"><div class="flex items-center justify-between gap-4 mb-1"><span class="text-xs font-bold opacity-90">${t("ai.you")}</span><span class="text-[11px] opacity-70">${D.formatTime(new Date(), AppState.lang)}</span></div><p class="text-sm leading-relaxed">${escapeHtml(text)}</p></div>`;
    c.appendChild(wrap);
    c.scrollTop = c.scrollHeight;
  }

  function appendSakhi(resp) {
    const c = document.getElementById("chat-messages-container");
    const id = `src-${Math.random().toString(36).slice(2, 9)}`;
    let sourcesHtml = "";
    if (resp.sources && resp.sources.length) {
      sourcesHtml = `<div class="mt-3 pt-3 border-t border-[var(--line)]">
        <button type="button" class="flex items-center justify-between w-full text-xs text-[var(--rose-deep)] font-bold py-1" data-toggle-sources="${id}" aria-expanded="false">
          <span class="flex items-center gap-1"><span class="material-symbols-outlined text-sm">menu_book</span>${t("ai.sources_n", { n: resp.sources.length })}</span>
          <span class="material-symbols-outlined text-sm transition-transform">expand_more</span>
        </button>
        <div id="${id}" hidden class="space-y-2 mt-2 text-xs muted bg-white p-3 rounded-[12px] border border-[var(--line)]">
          ${resp.sources.map((s, i) => `<div class="flex items-start gap-2"><span class="cite-pill">${i + 1}</span><div>${s.url ? `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener" class="text-[var(--rose-deep)] font-semibold hover:underline">${escapeHtml(s.name)}</a>` : `<strong>${escapeHtml(s.name)}</strong>`}${s.doc ? ` — <em>${escapeHtml(s.doc)}</em>` : ""}${s.excerpt ? `<p class="mt-0.5 italic opacity-80">"${escapeHtml(s.excerpt)}"</p>` : ""}</div></div>`).join("")}
        </div></div>`;
    }
    const modeBadge = resp.mode === "retrieval_only" ? `<span class="badge badge-lavender">${t("ai.mode_retrieval")}</span>` : resp.mode === "offline" ? `<span class="badge badge-peach">${t("ai.mode_offline")}</span>` : "";
    const notices = (resp.notices || []).map((n) => `<div class="notice ${n.level === "urgent" ? "notice-error" : "notice-warn"} mt-3"><span class="material-symbols-outlined">${n.level === "urgent" ? "emergency" : "info"}</span><span>${escapeHtml(n.message || n.text || "")}</span></div>`).join("");
    const wrap = document.createElement("div");
    wrap.className = "flex items-start gap-3 animate-fade-in";
    wrap.innerHTML = `
      <span class="icon-bubble bubble-rose shrink-0 mt-1"><span class="material-symbols-outlined" style="font-variation-settings:'FILL' 1">spa</span></span>
      <div class="bubble-sakhi flex-1 min-w-0">
        <div class="flex items-center justify-between gap-3 mb-1"><span class="text-xs font-bold text-[var(--rose-deep)]">${t("ai.companion_name")}</span><div class="flex items-center gap-2">${modeBadge}<span class="caption">${D.formatTime(new Date(), AppState.lang)}</span></div></div>
        <div class="body">${renderMarkdown(resp.text, resp.sources)}</div>
        ${notices}
        ${sourcesHtml}
        ${resp.disclaimer ? `<p class="caption mt-3 flex items-start gap-1.5"><span class="material-symbols-outlined text-sm text-[var(--sage-deep)]">verified_user</span><span>${escapeHtml(resp.disclaimer)}</span></p>` : ""}
      </div>`;
    c.appendChild(wrap);
    c.scrollTop = c.scrollHeight;
    wrap.querySelector("[data-toggle-sources]")?.addEventListener("click", (e) => {
      const btn = e.currentTarget;
      const panel = document.getElementById(btn.getAttribute("data-toggle-sources"));
      const open = panel.hidden;
      panel.hidden = !open;
      btn.setAttribute("aria-expanded", String(open));
      btn.lastElementChild.style.transform = open ? "rotate(180deg)" : "";
    });
  }

  let busy = false;
  async function submit(question) {
    if (busy) return;
    const q = (question || "").trim();
    if (q.length < 3) { showToast(t("ai.too_short"), "info"); return; }
    busy = true;
    appendUser(q);
    const input = document.getElementById("messageInput");
    input.value = "";
    const send = document.getElementById("sendBtn");
    send.disabled = true;
    const c = document.getElementById("chat-messages-container");
    const typing = document.createElement("div");
    typing.className = "flex items-center gap-2 px-4 py-3 rounded-full bg-[var(--surface-2)] w-fit text-xs font-semibold text-[var(--rose-deep)]";
    typing.innerHTML = `<span class="spinner" style="width:14px;height:14px"></span><span>${t("ai.thinking")}</span>`;
    c.appendChild(typing);
    c.scrollTop = c.scrollHeight;
    try {
      const resp = await generateResponse(q);
      typing.remove();
      appendSakhi(resp);
    } catch (err) {
      typing.remove();
      appendSakhi({ text: t("ai.error_generic"), sources: [], mode: "error" });
    } finally {
      busy = false;
      send.disabled = false;
      input.focus();
    }
  }

  // ---- voice input (Web Speech API; no simulation) ---------------------------------------------------
  let recognition = null;
  function toggleVoice() {
    const indicator = document.getElementById("voice-indicator");
    const btn = document.getElementById("voiceBtn");
    if (recognition) { try { recognition.stop(); } catch { /* noop */ } return; }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { showToast(t("ai.voice_unsupported"), "info"); return; }
    recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = AppState.lang === "hi" ? "hi-IN" : "en-IN";
    indicator.hidden = false; btn.classList.add("text-[var(--rose-deep)]");
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      const input = document.getElementById("messageInput");
      input.value = transcript; input.focus();
    };
    recognition.onerror = (e) => { if (e.error !== "aborted") showToast(t("ai.voice_error"), "error"); };
    recognition.onend = () => { recognition = null; indicator.hidden = true; btn.classList.remove("text-[var(--rose-deep)]"); };
    try { recognition.start(); } catch { recognition = null; indicator.hidden = true; }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("chatForm");
    const input = document.getElementById("messageInput");
    form?.addEventListener("submit", (e) => { e.preventDefault(); submit(input.value); });
    document.querySelectorAll(".prompt-chip").forEach((chip) => chip.addEventListener("click", () => { input.value = chip.textContent.trim(); input.focus(); }));
    document.getElementById("voiceBtn")?.addEventListener("click", toggleVoice);
    document.getElementById("voice-cancel")?.addEventListener("click", toggleVoice);
    // Backend capability line
    api.health().then((h) => {
      const el = document.getElementById("ai-capability");
      if (!el) return;
      if (h.llm && h.llm.configured) el.textContent = t("ai.cap_llm", { model: h.llm.model });
      else el.textContent = t("ai.cap_retrieval");
    }).catch(() => {});
  });

  window.SakhiChat = { submit };
})();
