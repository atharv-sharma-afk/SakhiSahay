/* ==========================================================================
   Onboarding. A short, focused flow: who you are, your cycle baseline, your
   last period, and four light questions. Answers are drafted to localStorage
   on every change (back navigation and reloads keep them) and persisted to
   the backend profile at the end. Nothing here is decorative state - every
   answer maps to a stored field.
   ========================================================================== */
(function () {
  const D = window.SakhiDates;
  const C = window.SakhiCycle;
  const api = window.SakhiApi;
  const DRAFT_KEY = "sakhisahay_onboarding_draft";

  const GOALS = [
    { key: "track_period", icon: "calendar_month", tone: "blush" },
    { key: "understand_symptoms", icon: "monitor_heart", tone: "lavender" },
    { key: "ask_questions", icon: "forum", tone: "sage" },
    { key: "doctor_visit", icon: "stethoscope", tone: "peach" },
    { key: "healthy_habits", icon: "self_improvement", tone: "sage" },
    { key: "learn_cycle", icon: "menu_book", tone: "lavender" },
  ];
  const FEELINGS = [
    { key: "love_hate", emoji: "😐" },
    { key: "embarrassed", emoji: "😳" },
    { key: "dislike", emoji: "😠" },
    { key: "want_to_understand", emoji: "🤔" },
    { key: "friends", emoji: "😌" },
  ];
  const YNU = ["yes", "no", "unsure"];

  // Step definitions. `optional` steps show Skip; `auto` steps advance on selection.
  const STEPS = [
    { id: "welcome", progress: false },
    { id: "goals", optional: true },
    { id: "name" },
    { id: "last_period", optional: true },
    { id: "cycle" },
    { id: "regular", optional: true, auto: true },
    { id: "feeling", optional: true, auto: true },
    { id: "sleep", optional: true, auto: true },
    { id: "summary" },
    { id: "saving", progress: false },
    { id: "done", progress: false },
  ];
  const QUESTION_STEPS = STEPS.filter((s) => s.progress !== false).length;

  const state = {
    index: 0,
    answers: {},
    profile: null,
    resolve: null,
    calYear: null,
    calMonth: null,
    saving: false,
    saveError: null,
  };

  // ---- draft persistence --------------------------------------------------------------
  function loadDraft() {
    try {
      const raw = localStorage.getItem(DRAFT_KEY);
      if (!raw) return null;
      const d = JSON.parse(raw);
      return d && typeof d === "object" ? d : null;
    } catch { return null; }
  }
  function saveDraft() {
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify({ index: state.index, answers: state.answers })); } catch { /* ignore */ }
  }
  function clearDraft() { localStorage.removeItem(DRAFT_KEY); }

  // ---- illustrations (simple, brand-owned SVG) -------------------------------------------
  const ART = {
    petals: `<svg viewBox="0 0 200 140" fill="none" aria-hidden="true">
      <circle cx="100" cy="76" r="54" fill="#F6DDE5"/>
      <g transform="translate(100 76)">
        <ellipse rx="14" ry="30" fill="#D98FA8" transform="rotate(0)"/>
        <ellipse rx="14" ry="30" fill="#D98FA8" transform="rotate(72)"/>
        <ellipse rx="14" ry="30" fill="#D98FA8" transform="rotate(144)"/>
        <ellipse rx="14" ry="30" fill="#D98FA8" transform="rotate(216)"/>
        <ellipse rx="14" ry="30" fill="#D98FA8" transform="rotate(288)"/>
        <circle r="12" fill="#FFFBF8"/>
      </g>
      <circle cx="38" cy="112" r="6" fill="#E9E2F5"/><circle cx="166" cy="40" r="8" fill="#DDE9DD"/></svg>`,
    calendar: `<svg viewBox="0 0 200 140" fill="none" aria-hidden="true">
      <rect x="44" y="26" width="112" height="96" rx="16" fill="#fff" stroke="#EDE3E7" stroke-width="2"/>
      <rect x="44" y="26" width="112" height="26" rx="16" fill="#F6DDE5"/><rect x="44" y="40" width="112" height="12" fill="#F6DDE5"/>
      <g fill="#E9E2F5"><circle cx="66" cy="72" r="6"/><circle cx="88" cy="72" r="6"/><circle cx="110" cy="72" r="6"/><circle cx="132" cy="72" r="6"/>
      <circle cx="66" cy="96" r="6"/><circle cx="132" cy="96" r="6"/></g>
      <g fill="#D98FA8"><circle cx="88" cy="96" r="6"/><circle cx="110" cy="96" r="6"/></g>
      <circle cx="110" cy="96" r="10" stroke="#B25C79" stroke-width="2"/></svg>`,
    moon: `<svg viewBox="0 0 200 140" fill="none" aria-hidden="true">
      <circle cx="100" cy="70" r="46" fill="#E9E2F5"/>
      <path d="M100 24a46 46 0 1 0 0 92 36 36 0 0 1 0-92z" fill="#FBE8DD"/>
      <circle cx="150" cy="40" r="4" fill="#D98FA8"/><circle cx="46" cy="100" r="5" fill="#DDE9DD"/><circle cx="160" cy="104" r="3" fill="#B7839B"/></svg>`,
    chart: `<svg viewBox="0 0 200 140" fill="none" aria-hidden="true">
      <rect x="30" y="30" width="140" height="84" rx="16" fill="#fff" stroke="#EDE3E7" stroke-width="2"/>
      <path d="M48 92 C70 86, 76 56, 98 60 S126 90, 152 54" stroke="#D98FA8" stroke-width="4" stroke-linecap="round"/>
      <circle cx="98" cy="60" r="6" fill="#fff" stroke="#B25C79" stroke-width="3"/>
      <rect x="48" y="100" width="104" height="4" rx="2" fill="#F6DDE5"/></svg>`,
    heart: `<svg viewBox="0 0 200 140" fill="none" aria-hidden="true">
      <path d="M100 116c-28-18-56-40-56-66a28 28 0 0 1 56-8 28 28 0 0 1 56 8c0 26-28 48-56 66z" fill="#F6DDE5"/>
      <path d="M100 100c-20-13-40-29-40-48a20 20 0 0 1 40-6 20 20 0 0 1 40 6c0 19-20 35-40 48z" fill="#D98FA8"/>
      <circle cx="40" cy="36" r="5" fill="#E9E2F5"/><circle cx="162" cy="100" r="6" fill="#DDE9DD"/></svg>`,
    sleep: `<svg viewBox="0 0 200 140" fill="none" aria-hidden="true">
      <rect x="40" y="76" width="120" height="36" rx="14" fill="#E9E2F5"/>
      <rect x="54" y="62" width="40" height="22" rx="10" fill="#fff"/>
      <path d="M126 36a16 16 0 1 0 14 24 13 13 0 0 1-14-24z" fill="#FBE8DD"/>
      <text x="58" y="48" font-family="Manrope, sans-serif" font-weight="700" font-size="14" fill="#B7839B">z</text>
      <text x="70" y="38" font-family="Manrope, sans-serif" font-weight="700" font-size="18" fill="#D98FA8">z</text></svg>`,
    sparkle: `<svg viewBox="0 0 200 140" fill="none" aria-hidden="true">
      <circle cx="100" cy="70" r="40" fill="#DDE9DD"/>
      <path d="M100 42l6 20 20 6-20 6-6 20-6-20-20-6 20-6z" fill="#43704F"/>
      <path d="M150 30l3 9 9 3-9 3-3 9-3-9-9-3 9-3z" fill="#D98FA8"/>
      <path d="M46 94l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" fill="#B7839B"/></svg>`,
  };
  const STEP_ART = { welcome: "petals", goals: "sparkle", name: "heart", last_period: "calendar", cycle: "moon", regular: "chart", feeling: "heart", sleep: "sleep", summary: "chart", saving: "petals", done: "sparkle" };

  // ---- helpers ---------------------------------------------------------------------
  function el(id) { return document.getElementById(id); }
  function step() { return STEPS[state.index]; }
  function answer(key, value) { state.answers[key] = value; saveDraft(); }

  function todayIso() { return D.todayISO(); }

  function setProgress() {
    const s = step();
    const bar = el("ob-progress-fill");
    const top = el("ob-top");
    if (s.progress === false) { top.style.visibility = "hidden"; return; }
    top.style.visibility = "visible";
    const qIndex = STEPS.slice(0, state.index + 1).filter((x) => x.progress !== false).length;
    bar.style.width = `${Math.round((qIndex / QUESTION_STEPS) * 100)}%`;
    el("ob-back").hidden = state.index === 0 || s.id === "saving";
    el("ob-skip").hidden = !s.optional;
  }

  // ---- step renderers ------------------------------------------------------------------------
  function renderWelcome() {
    return `
      <div class="ob-welcome">
        <div class="ob-brand"><span class="material-symbols-outlined" style="font-variation-settings:'FILL' 1">spa</span> SakhiSahay</div>
        <h1 class="ob-title mt-3">${t("ob.welcome_title")}</h1>
        <p class="ob-sub">${t("ob.welcome_sub")}</p>
        <ul class="ob-feature-list">
          <li><span class="icon-bubble bubble-blush"><span class="material-symbols-outlined">calendar_month</span></span><div><strong>${t("ob.feat_track")}</strong><span>${t("ob.feat_track_sub")}</span></div></li>
          <li><span class="icon-bubble bubble-lavender"><span class="material-symbols-outlined">forum</span></span><div><strong>${t("ob.feat_ask")}</strong><span>${t("ob.feat_ask_sub")}</span></div></li>
          <li><span class="icon-bubble bubble-sage"><span class="material-symbols-outlined">lock</span></span><div><strong>${t("ob.feat_private")}</strong><span>${t("ob.feat_private_sub")}</span></div></li>
        </ul>
        <div class="mt-6">
          <div class="eyebrow mb-2">${t("ob.language")}</div>
          <div class="seg max-w-xs mx-auto" role="radiogroup" aria-label="${t("ob.language")}">
            ${["en", "hi", "hinglish"].map((l) => `<button type="button" class="seg-btn ${AppState.lang === l ? "is-on" : ""}" data-ob-lang="${l}" role="radio" aria-checked="${AppState.lang === l}">${t(`lang.${l}`)}</button>`).join("")}
          </div>
        </div>
      </div>`;
  }

  function renderGoals() {
    const chosen = new Set(state.answers.goals || []);
    return `
      <h1 class="ob-title">${t("ob.goals_title")}</h1>
      <p class="ob-sub">${t("ob.goals_sub")}</p>
      <div class="option-grid" role="group">
        ${GOALS.map((g) => `
          <button type="button" class="option-card ${chosen.has(g.key) ? "is-on" : ""}" data-ob-goal="${g.key}" aria-pressed="${chosen.has(g.key)}">
            <span class="icon-bubble icon-bubble-lg bubble-${g.tone}"><span class="material-symbols-outlined">${g.icon}</span></span>
            <span>${t(`goal.${g.key}`)}</span>
          </button>`).join("")}
      </div>`;
  }

  function renderName() {
    const a = state.answers;
    return `
      <h1 class="ob-title">${t("ob.name_title")}</h1>
      <p class="ob-sub">${t("ob.name_sub")}</p>
      <div class="grid gap-4 max-w-sm mx-auto">
        <div class="field" id="ob-field-name">
          <label class="field-label" for="ob-name">${t("ob.name_label")}</label>
          <input class="input input-lg" id="ob-name" type="text" autocomplete="given-name" maxlength="80" value="${escapeAttr(a.display_name || "")}" placeholder="${t("ob.name_placeholder")}" autofocus />
          <span class="field-error" id="ob-name-error"></span>
        </div>
        <div class="field" id="ob-field-age">
          <label class="field-label" for="ob-age">${t("ob.age_label")} <span class="muted font-normal">(${t("common.optional")})</span></label>
          <input class="input" id="ob-age" type="number" inputmode="numeric" min="10" max="80" value="${a.age != null ? a.age : ""}" placeholder="${t("ob.age_placeholder")}" />
          <span class="field-error" id="ob-age-error"></span>
        </div>
      </div>`;
  }

  function renderLastPeriod() {
    const today = todayIso();
    const sel = state.answers.last_period_start || null;
    if (state.calYear == null) {
      const base = D.parseISODate(sel || today);
      state.calYear = base.getFullYear();
      state.calMonth = base.getMonth();
    }
    const cells = D.monthGrid(state.calYear, state.calMonth);
    const weekdays = D.weekdayLabels(AppState.lang, "short").map((w) => w.slice(0, 2));
    const nextDisabled = state.calYear > Number(today.slice(0, 4)) || (state.calYear === Number(today.slice(0, 4)) && state.calMonth >= Number(today.slice(5, 7)) - 1);
    return `
      <h1 class="ob-title">${t("ob.last_period_title")}</h1>
      <p class="ob-sub">${t("ob.last_period_sub")}</p>
      <div class="card card-pad mini-cal max-w-sm mx-auto">
        <div class="row-between mb-2">
          <button type="button" class="btn btn-ghost btn-icon" data-ob-cal="-1" aria-label="${t("cal.prev_month")}"><span class="material-symbols-outlined">chevron_left</span></button>
          <div class="font-semibold">${D.formatMonthYear(state.calYear, state.calMonth, AppState.lang)}</div>
          <button type="button" class="btn btn-ghost btn-icon" data-ob-cal="1" aria-label="${t("cal.next_month")}" ${nextDisabled ? "disabled" : ""}><span class="material-symbols-outlined">chevron_right</span></button>
        </div>
        <div class="cal-grid">${weekdays.map((w) => `<div class="cal-weekday">${w}</div>`).join("")}</div>
        <div class="cal-grid">
          ${cells.map((c) => {
            const future = c.iso > today;
            const cls = ["cal-cell", c.outside ? "is-outside" : "", future ? "is-future" : "", c.iso === today ? "is-today" : "", c.iso === sel ? "is-period is-selected" : ""].join(" ");
            return `<button type="button" class="${cls}" data-ob-date="${c.iso}" ${future ? "disabled" : ""} aria-label="${D.formatISODate(c.iso, AppState.lang, { weekday: "long", day: "numeric", month: "long" })}" aria-pressed="${c.iso === sel}"><span class="cal-num">${c.day}</span></button>`;
          }).join("")}
        </div>
      </div>
      <p class="caption text-center mt-4" id="ob-date-caption">${sel ? t("ob.last_period_selected", { date: D.formatISODate(sel, AppState.lang, { weekday: "long", day: "numeric", month: "long" }) }) : t("ob.last_period_hint")}</p>`;
  }

  function renderCycle() {
    const a = state.answers;
    const cycle = a.cycle_length_days || (state.profile && state.profile.cycle_length_days) || 28;
    const period = a.period_length_days || (state.profile && state.profile.period_length_days) || 5;
    const unsure = !!a.cycle_unsure;
    return `
      <h1 class="ob-title">${t("ob.cycle_title")}</h1>
      <p class="ob-sub">${t("ob.cycle_sub")}</p>
      <div class="grid gap-5 max-w-sm mx-auto">
        <div class="card card-pad text-center">
          <div class="field-label mb-1">${t("ob.cycle_length")}</div>
          <p class="caption mb-3">${t("ob.cycle_length_hint")}</p>
          <div class="stepper" data-ob-stepper="cycle_length_days" data-min="15" data-max="60">
            <button type="button" data-step="-1" aria-label="-" ${unsure ? "disabled" : ""}><span class="material-symbols-outlined">remove</span></button>
            <output>${cycle} ${t("common.days")}</output>
            <button type="button" data-step="1" aria-label="+" ${unsure ? "disabled" : ""}><span class="material-symbols-outlined">add</span></button>
          </div>
        </div>
        <div class="card card-pad text-center">
          <div class="field-label mb-1">${t("ob.period_length")}</div>
          <p class="caption mb-3">${t("ob.period_length_hint")}</p>
          <div class="stepper" data-ob-stepper="period_length_days" data-min="1" data-max="14">
            <button type="button" data-step="-1" aria-label="-" ${unsure ? "disabled" : ""}><span class="material-symbols-outlined">remove</span></button>
            <output>${period} ${t("common.days")}</output>
            <button type="button" data-step="1" aria-label="+" ${unsure ? "disabled" : ""}><span class="material-symbols-outlined">add</span></button>
          </div>
        </div>
        <button type="button" class="option-row ${unsure ? "is-on" : ""}" data-ob-unsure aria-pressed="${unsure}">
          <span>${t("ob.cycle_unsure")}</span><span class="option-radio"></span>
        </button>
      </div>`;
  }

  function renderSingle(key, options, { emoji = false, notes = false, titleVars } = {}) {
    const current = state.answers[key] || null;
    return `
      <h1 class="ob-title">${t(`ob.${key}_title`, titleVars)}</h1>
      ${t(`ob.${key}_sub`) !== `ob.${key}_sub` ? `<p class="ob-sub">${t(`ob.${key}_sub`)}</p>` : `<div class="mb-4"></div>`}
      <div class="option-list" role="radiogroup">
        ${options.map((o) => {
          const k = typeof o === "string" ? o : o.key;
          const on = current === k;
          const noteKey = `ob.${key}_note_${k}`;
          const hasNote = notes && t(noteKey) !== noteKey;
          return `<button type="button" class="option-row ${on ? "is-on" : ""}" role="radio" aria-checked="${on}" data-ob-single="${key}" data-value="${k}">
            <span><span>${t(`opt.${key}.${k}`)}${emoji && o.emoji ? ` <span class="option-emoji">${o.emoji}</span>` : ""}</span>${hasNote ? `<span class="option-note">${t(noteKey)}</span>` : ""}</span>
          </button>`;
        }).join("")}
      </div>`;
  }

  function summaryModel() {
    const a = state.answers;
    const profile = {
      cycle_length_days: a.cycle_unsure ? 28 : a.cycle_length_days || 28,
      period_length_days: a.cycle_unsure ? 5 : a.period_length_days || 5,
    };
    const periods = [];
    if (a.last_period_start) {
      const today = todayIso();
      const expectedEnd = D.addDays(a.last_period_start, profile.period_length_days - 1);
      // An open period would cover every day through today and mis-label the phase.
      periods.push({
        start_date: a.last_period_start,
        end_date: expectedEnd && expectedEnd < today ? expectedEnd : null,
      });
    }
    return { profile, status: C.currentStatus(periods, profile, todayIso()) };
  }

  function renderSummary() {
    const a = state.answers;
    const { profile, status } = summaryModel();
    const name = a.display_name || "";
    const total = profile.cycle_length_days;
    const pLen = Math.min(profile.period_length_days, total);
    const ov = total - C.LUTEAL_DAYS;
    const fertileStart = Math.max(ov - 5, pLen + 1);
    const fertileEnd = Math.min(ov + 1, total);
    const seg = (n, color) => `<span style="flex:${Math.max(n, 0)};background:${color}"></span>`;
    const bar = `<div class="ob-phase-bar" aria-hidden="true">
        ${seg(pLen, "var(--rose)")}${seg(fertileStart - pLen - 1, "var(--blush)")}${seg(fertileEnd - fertileStart + 1, "var(--sage)")}${seg(total - fertileEnd, "var(--lavender)")}
      </div>
      <div class="ob-phase-labels"><span>${t("phase.menstrual")}</span><span>${t("phase.follicular")}</span><span>${t("phase.fertile")}</span><span>${t("phase.luteal")}</span></div>`;

    let headline, body;
    if (status.hasData && status.phase !== "late") {
      headline = t("ob.summary_phase_title", { name, phase: t(`phase.${status.phase}`) });
      body = t(`phase.${status.phase}_desc`);
    } else if (status.hasData) {
      headline = t("ob.summary_late_title", { name });
      body = t("ob.summary_late_body", { days: status.lateByDays });
    } else {
      headline = t("ob.summary_nodata_title", { name });
      body = t("ob.summary_nodata_body");
    }
    return `
      <h1 class="ob-title">${headline}</h1>
      <p class="ob-sub">${body}</p>
      <div class="card card-pad max-w-md mx-auto">
        ${bar}
        <div class="ob-summary mt-4">
          <div class="row-between"><span class="body-sm muted">${t("ob.sum_cycle")}</span><strong>${profile.cycle_length_days} ${t("common.days")}</strong></div>
          <div class="row-between"><span class="body-sm muted">${t("ob.sum_period")}</span><strong>${profile.period_length_days} ${t("common.days")}</strong></div>
          ${status.hasData ? `
          <div class="row-between"><span class="body-sm muted">${t("ob.sum_cycle_day")}</span><strong>${t("cycle.day_n", { n: status.cycleDay })}</strong></div>
          <div class="row-between"><span class="body-sm muted">${t("ob.sum_next")}</span><strong>${D.formatISODate(status.nextPeriodStart, AppState.lang, { day: "numeric", month: "short" })}</strong></div>` : ""}
        </div>
        <p class="caption mt-4">${t("ob.summary_note")}</p>
      </div>`;
  }

  function renderSaving() {
    if (state.saveError) {
      return `<div class="ob-loading">
        <span class="icon-bubble icon-bubble-lg bubble-peach"><span class="material-symbols-outlined">cloud_off</span></span>
        <h1 class="ob-title">${t("ob.save_failed_title")}</h1>
        <p class="ob-sub">${escapeHtml(state.saveError)}</p>
        <button type="button" class="btn btn-primary" data-ob-retry>${t("common.retry")}</button>
      </div>`;
    }
    return `<div class="ob-loading">
      <span class="spinner spinner-lg"></span>
      <h1 class="ob-title">${t("ob.saving_title")}</h1>
      <p class="ob-sub">${t("ob.saving_sub")}</p>
    </div>`;
  }

  function renderDone() {
    const name = state.answers.display_name || (state.profile && state.profile.display_name) || "";
    return `<div class="ob-welcome">
      <h1 class="ob-title">${t("ob.done_title", { name })}</h1>
      <p class="ob-sub">${t("ob.done_sub")}</p>
      <div class="card card-pad card-tint-sage max-w-md mx-auto text-left">
        <div class="flex items-start gap-3"><span class="material-symbols-outlined text-[var(--sage-deep)]">verified_user</span>
        <p class="body-sm">${t("ob.done_privacy")}</p></div>
      </div>
    </div>`;
  }

  const RENDERERS = {
    welcome: renderWelcome,
    goals: renderGoals,
    name: renderName,
    last_period: renderLastPeriod,
    cycle: renderCycle,
    regular: () => renderSingle("periods_regular", YNU),
    feeling: () => renderSingle("period_feeling", FEELINGS, { emoji: true, titleVars: { name: state.answers.display_name || "" } }),
    sleep: () => renderSingle("cycle_affects_sleep", YNU, { notes: true }),
    summary: renderSummary,
    saving: renderSaving,
    done: renderDone,
  };

  function footerFor(s) {
    const a = state.answers;
    if (s.id === "welcome") return { label: t("ob.get_started"), show: true };
    if (s.id === "summary") return { label: t("ob.looks_good"), show: true };
    if (s.id === "done") return { label: t("ob.lets_begin"), show: true };
    if (s.id === "saving") return { show: false };
    if (s.auto) return { show: false };
    if (s.id === "goals") return { label: (a.goals && a.goals.length) ? t("common.next") : t("common.skip"), show: true };
    return { label: t("common.next"), show: true };
  }

  // ---- render / transitions ----------------------------------------------------------------
  function render(direction) {
    const s = step();
    const host = el("ob-step-host");
    const old = host.firstElementChild;
    const fresh = document.createElement("div");
    fresh.className = "ob-step";
    fresh.innerHTML = `<div class="ob-body-inner">${RENDERERS[s.id]()}</div>`;
    if (old && direction) {
      old.classList.add(direction > 0 ? "is-leaving-left" : "is-leaving-right");
      setTimeout(() => old.remove(), 200);
      fresh.style.animationDelay = "60ms";
    } else if (old) old.remove();
    host.appendChild(fresh);
    el("ob-hero").innerHTML = ART[STEP_ART[s.id]] || "";
    setProgress();
    const f = footerFor(s);
    const btn = el("ob-next");
    btn.hidden = !f.show;
    btn.textContent = f.label || "";
    el("ob-footer-note").textContent = s.id === "summary" ? t("ob.summary_footer") : "";
    el("ob-body").scrollTop = 0;
    bindStep(fresh);
    if (s.id === "saving" && !state.saving && !state.saveError) persist();
  }

  function go(delta) {
    const next = state.index + delta;
    if (next < 0 || next >= STEPS.length) return;
    state.index = next;
    saveDraft();
    render(delta);
  }

  function validateCurrent() {
    const s = step();
    if (s.id === "name") {
      const input = el("ob-name");
      const ageInput = el("ob-age");
      const name = (input.value || "").replace(/\s+/g, " ").trim();
      let ok = true;
      const nameField = el("ob-field-name");
      if (name.length < 2) { nameField.classList.add("has-error"); el("ob-name-error").textContent = t("ob.name_error"); ok = false; }
      else { nameField.classList.remove("has-error"); answer("display_name", name); }
      const ageRaw = ageInput.value.trim();
      const ageField = el("ob-field-age");
      if (ageRaw === "") { ageField.classList.remove("has-error"); answer("age", null); }
      else {
        const age = Number(ageRaw);
        if (!Number.isInteger(age) || age < 10 || age > 80) { ageField.classList.add("has-error"); el("ob-age-error").textContent = t("ob.age_error"); ok = false; }
        else { ageField.classList.remove("has-error"); answer("age", age); }
      }
      if (!ok) (name.length < 2 ? input : ageInput).focus();
      return ok;
    }
    if (s.id === "cycle" && !state.answers.cycle_unsure) {
      if (!state.answers.cycle_length_days) answer("cycle_length_days", 28);
      if (!state.answers.period_length_days) answer("period_length_days", 5);
    }
    return true;
  }

  function bindStep(root) {
    const s = step();
    root.querySelectorAll("[data-ob-lang]").forEach((b) => b.addEventListener("click", () => {
      applyLanguage(b.getAttribute("data-ob-lang"), { persistRemote: false });
      answer("preferred_language", AppState.lang);
      render();
    }));
    root.querySelectorAll("[data-ob-goal]").forEach((b) => b.addEventListener("click", () => {
      const key = b.getAttribute("data-ob-goal");
      const set = new Set(state.answers.goals || []);
      set.has(key) ? set.delete(key) : set.add(key);
      answer("goals", [...set]);
      b.classList.toggle("is-on", set.has(key));
      b.setAttribute("aria-pressed", String(set.has(key)));
      el("ob-next").textContent = set.size ? t("common.next") : t("common.skip");
    }));
    if (s.id === "name") {
      el("ob-name").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); el("ob-age").focus(); } });
      el("ob-age").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); next(); } });
      el("ob-name").addEventListener("input", () => el("ob-field-name").classList.remove("has-error"));
    }
    root.querySelectorAll("[data-ob-cal]").forEach((b) => b.addEventListener("click", () => {
      const m = D.shiftMonth(state.calYear, state.calMonth, Number(b.getAttribute("data-ob-cal")));
      state.calYear = m.year; state.calMonth = m.month0;
      render();
    }));
    root.querySelectorAll("[data-ob-date]").forEach((b) => b.addEventListener("click", () => {
      const iso = b.getAttribute("data-ob-date");
      answer("last_period_start", state.answers.last_period_start === iso ? null : iso);
      render();
    }));
    root.querySelectorAll("[data-ob-stepper]").forEach((wrap) => {
      const key = wrap.getAttribute("data-ob-stepper");
      const min = Number(wrap.dataset.min), max = Number(wrap.dataset.max);
      const out = wrap.querySelector("output");
      wrap.querySelectorAll("[data-step]").forEach((b) => b.addEventListener("click", () => {
        const current = state.answers[key] || (key === "cycle_length_days" ? 28 : 5);
        const value = Math.min(max, Math.max(min, current + Number(b.getAttribute("data-step"))));
        answer(key, value);
        out.textContent = `${value} ${t("common.days")}`;
      }));
    });
    root.querySelector("[data-ob-unsure]")?.addEventListener("click", () => {
      answer("cycle_unsure", !state.answers.cycle_unsure);
      if (state.answers.cycle_unsure) { answer("cycle_length_days", 28); answer("period_length_days", 5); }
      render();
    });
    root.querySelectorAll("[data-ob-single]").forEach((b) => b.addEventListener("click", () => {
      const key = b.getAttribute("data-ob-single");
      answer(key, b.getAttribute("data-value"));
      root.querySelectorAll("[data-ob-single]").forEach((x) => { const on = x === b; x.classList.toggle("is-on", on); x.setAttribute("aria-checked", String(on)); });
      if (step().auto) setTimeout(() => { if (step().id === s.id) go(1); }, 420);
    }));
    root.querySelector("[data-ob-retry]")?.addEventListener("click", () => { state.saveError = null; render(); });
  }

  function next() {
    const s = step();
    if (s.id === "done") { finish(); return; }
    if (!validateCurrent()) return;
    go(1);
  }

  function skip() {
    const s = step();
    if (!s.optional) return;
    if (s.id === "goals") answer("goals", []);
    if (s.id === "last_period") answer("last_period_start", null);
    if (s.id === "regular") answer("periods_regular", null);
    if (s.id === "feeling") answer("period_feeling", null);
    if (s.id === "sleep") answer("cycle_affects_sleep", null);
    go(1);
  }

  // ---- persistence to the backend ---------------------------------------------------------------
  async function persist() {
    state.saving = true;
    const a = state.answers;
    const patch = {
      display_name: a.display_name,
      age: a.age == null ? null : a.age,
      cycle_length_days: a.cycle_unsure ? 28 : a.cycle_length_days || 28,
      period_length_days: a.cycle_unsure ? 5 : a.period_length_days || 5,
      periods_regular: a.periods_regular || null,
      period_feeling: a.period_feeling || null,
      cycle_affects_sleep: a.cycle_affects_sleep || null,
      goals: a.goals || [],
      preferred_language: AppState.lang,
      onboarding_completed: true,
    };
    try {
      if (a.last_period_start) {
        const today = todayIso();
        const expectedEnd = D.addDays(a.last_period_start, patch.period_length_days - 1);
        const body = { start_date: a.last_period_start, end_date: expectedEnd < today ? expectedEnd : null };
        try {
          await api.tracker.createPeriod(body);
        } catch (err) {
          // 409 = a period already covers this date (e.g. a retry); that's fine.
          if (!(err instanceof api.ApiError) || err.code !== "conflict") throw err;
        }
      }
      const profile = await api.profile.update(patch);
      state.profile = profile;
      state.saving = false;
      clearDraft();
      setTimeout(() => { state.index = STEPS.findIndex((x) => x.id === "done"); render(1); }, 500);
    } catch (err) {
      state.saving = false;
      state.saveError = err.message || t("ob.save_failed_generic");
      render();
    }
  }

  function finish() {
    const screen = el("onboarding");
    screen.style.transition = "opacity .3s ease, transform .3s ease";
    screen.style.opacity = "0";
    screen.style.transform = "translateY(10px)";
    setTimeout(() => {
      screen.hidden = true;
      screen.style.opacity = ""; screen.style.transform = ""; screen.style.transition = "";
      document.body.style.overflow = "";
      const resolve = state.resolve; state.resolve = null;
      if (resolve) resolve(state.profile);
    }, 300);
  }

  /** Entry point: resolves with the saved profile when onboarding completes. */
  function run(profile) {
    state.profile = profile;
    const draft = loadDraft();
    state.answers = (draft && draft.answers) || {};
    if (!state.answers.display_name && profile && profile.display_name && profile.display_name !== "Friend") state.answers.display_name = profile.display_name;
    const draftIndex = draft && Number.isInteger(draft.index) ? draft.index : 0;
    state.index = Math.min(Math.max(draftIndex, 0), STEPS.findIndex((x) => x.id === "summary"));
    state.saveError = null; state.saving = false;
    const screen = el("onboarding");
    screen.hidden = false;
    document.body.style.overflow = "hidden";
    render();
    return new Promise((resolve) => { state.resolve = resolve; });
  }

  function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function escapeAttr(s) { return escapeHtml(s); }

  document.addEventListener("DOMContentLoaded", () => {
    el("ob-next").addEventListener("click", next);
    el("ob-skip").addEventListener("click", skip);
    el("ob-back").addEventListener("click", () => go(-1));
  });
  document.addEventListener("sakhi:lang", () => { if (!el("onboarding").hidden) render(); });

  window.SakhiOnboarding = { run };
})();
