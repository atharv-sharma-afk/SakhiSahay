/* ==========================================================================
   Period & symptom tracker.
   - Calendar is rendered from the records in AppState.data (periods, symptoms)
     plus estimates from SakhiCycle. Nothing is hardcoded to a month.
   - The day panel edits the selected date: flow -> period records, symptoms ->
     symptom records. Saves are explicit, awaited, and only reported as
     successful after the API confirms.
   ========================================================================== */
(function () {
  const D = window.SakhiDates;
  const C = window.SakhiCycle;
  const api = window.SakhiApi;

  const FLOWS = ["none", "spotting", "light", "medium", "heavy"];
  const GROUP_ORDER = ["pain", "body", "bleeding", "mood"];
  const GROUP_TONE = { pain: "", body: "chip-peach", bleeding: "", mood: "chip-lavender" };

  const T = {
    year: null,
    month0: null,
    selected: null,
    view: "month",
    form: { flow: "none", symptoms: new Set(), severity: 2, notes: "" },
    formDate: null, // date the form currently holds
    dirty: false,
    saving: false,
    periodModal: { id: null },
  };

  // ---- indexes ----------------------------------------------------------------------------
  function indexes() {
    const today = D.todayISO();
    const periodByDay = new Map();
    for (const p of AppState.data.periods) {
      const end = p.end_date || (p.start_date <= today ? today : p.start_date);
      for (let iso = p.start_date; iso <= end; iso = D.addDays(iso, 1)) {
        periodByDay.set(iso, { period: p, isStart: iso === p.start_date, isEnd: iso === end, open: !p.end_date });
      }
    }
    const symptomsByDay = new Map();
    for (const s of AppState.data.symptoms) {
      if (!symptomsByDay.has(s.record_date)) symptomsByDay.set(s.record_date, []);
      symptomsByDay.get(s.record_date).push(s);
    }
    const { marks, status } = C.estimateMarkers(AppState.data.periods, AppState.data.profile, today, 3);
    return { today, periodByDay, symptomsByDay, marks, status };
  }

  function catalogue() {
    const list = AppState.data.catalogue && AppState.data.catalogue.length ? AppState.data.catalogue : [];
    const groups = new Map();
    for (const item of list) {
      if (!groups.has(item.group)) groups.set(item.group, []);
      groups.get(item.group).push(item);
    }
    return GROUP_ORDER.filter((g) => groups.has(g)).map((g) => ({ group: g, items: groups.get(g) }));
  }
  function symptomLabel(key) {
    const k = `sym.${key}`;
    const tr = t(k);
    if (tr !== k) return tr;
    const item = (AppState.data.catalogue || []).find((c) => c.key === key);
    return item ? item.label : key;
  }

  // ---- calendar --------------------------------------------------------------------------------
  function ensureMonth() {
    if (T.year == null) {
      const d = D.parseISODate(T.selected || D.todayISO());
      T.year = d.getFullYear(); T.month0 = d.getMonth();
    }
    if (!T.selected) T.selected = D.todayISO();
  }

  function cellClass(iso, idx) {
    const cls = ["cal-cell"];
    const p = idx.periodByDay.get(iso);
    if (p) { cls.push("is-period"); if (p.isStart) cls.push("is-period-start"); if (p.isEnd) cls.push("is-period-end"); }
    else {
      const m = idx.marks.get(iso);
      if (m === "predicted") cls.push("is-predicted");
      else if (m === "fertile") cls.push("is-fertile");
      else if (m === "ovulation") cls.push("is-ovulation");
    }
    if (idx.symptomsByDay.has(iso)) cls.push("has-symptoms");
    if (iso === idx.today) cls.push("is-today");
    if (iso === T.selected) cls.push("is-selected");
    if (iso > idx.today) cls.push("is-future");
    return cls.join(" ");
  }

  function cellAria(iso, idx) {
    const parts = [D.formatISODate(iso, AppState.lang, { weekday: "long", day: "numeric", month: "long", year: "numeric" })];
    if (idx.periodByDay.has(iso)) parts.push(t("cal.aria_period"));
    const m = idx.marks.get(iso);
    if (m === "predicted") parts.push(t("cal.aria_predicted"));
    if (m === "fertile" || m === "ovulation") parts.push(t(`cal.aria_${m}`));
    if (idx.symptomsByDay.has(iso)) parts.push(t("cal.aria_symptoms", { n: idx.symptomsByDay.get(iso).length }));
    if (iso === idx.today) parts.push(t("date.today"));
    return parts.join(", ");
  }

  function renderCalendar(idx) {
    ensureMonth();
    const title = document.getElementById("calendar-current-month");
    if (title) title.textContent = D.formatMonthYear(T.year, T.month0, AppState.lang);
    const weekdaysEl = document.getElementById("calendar-weekdays");
    if (weekdaysEl) weekdaysEl.innerHTML = D.weekdayLabels(AppState.lang, "short").map((w) => `<div class="cal-weekday">${w.slice(0, 3)}</div>`).join("");
    const grid = document.getElementById("calendar-days-grid");
    if (!grid) return;
    const cells = D.monthGrid(T.year, T.month0);
    grid.innerHTML = cells.map((c) => `
      <button type="button" class="${cellClass(c.iso, idx)}${c.outside ? " is-outside" : ""}" data-cal-date="${c.iso}" aria-label="${cellAria(c.iso, idx)}" aria-pressed="${c.iso === T.selected}">
        <span class="cal-num">${c.day}</span><span class="cal-dot" aria-hidden="true"></span>
      </button>`).join("");
    const todayBtn = document.getElementById("btn-today-month");
    if (todayBtn) {
      const td = D.parseISODate(idx.today);
      todayBtn.disabled = td.getFullYear() === T.year && td.getMonth() === T.month0 && T.selected === idx.today;
    }
    document.getElementById("calendar-month-view")?.toggleAttribute("hidden", T.view !== "month");
    document.getElementById("calendar-year-view")?.toggleAttribute("hidden", T.view !== "year");
    document.querySelectorAll("[data-cal-view]").forEach((b) => b.classList.toggle("is-on", b.getAttribute("data-cal-view") === T.view));
    if (T.view === "year") renderYear(idx);
  }

  function renderYear(idx) {
    const host = document.getElementById("calendar-year-view");
    if (!host) return;
    const months = Array.from({ length: 12 }, (_, m) => m);
    host.innerHTML = `<div class="row-between mb-3">
        <button type="button" class="btn btn-ghost btn-icon" data-year-shift="-1" aria-label="${t("cal.prev_year")}"><span class="material-symbols-outlined">chevron_left</span></button>
        <div class="font-semibold">${T.year}</div>
        <button type="button" class="btn btn-ghost btn-icon" data-year-shift="1" aria-label="${t("cal.next_year")}"><span class="material-symbols-outlined">chevron_right</span></button>
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      ${months.map((m) => {
        const cells = D.monthGrid(T.year, m);
        return `<button type="button" class="card p-3 text-left hover:shadow-md transition-shadow" data-year-month="${m}">
          <div class="caption font-semibold mb-2 text-[var(--ink)]">${new Date(T.year, m, 1).toLocaleDateString(D.localeFor(AppState.lang), { month: "short" })}</div>
          <div class="grid grid-cols-7 gap-[3px]">
            ${cells.map((c) => {
              if (c.outside) return `<span class="block aspect-square rounded-[3px]"></span>`;
              let bg = "var(--surface-2)";
              if (idx.periodByDay.has(c.iso)) bg = "var(--rose)";
              else if (idx.marks.get(c.iso) === "predicted") bg = "var(--blush)";
              else if (idx.marks.get(c.iso) === "fertile" || idx.marks.get(c.iso) === "ovulation") bg = "var(--sage)";
              const ring = c.iso === idx.today ? "box-shadow:0 0 0 1.5px var(--rose-deep);" : "";
              return `<span class="block aspect-square rounded-[3px]" style="background:${bg};${ring}"></span>`;
            }).join("")}
          </div>
        </button>`;
      }).join("")}</div>`;
    host.querySelectorAll("[data-year-shift]").forEach((b) => b.addEventListener("click", () => { T.year += Number(b.getAttribute("data-year-shift")); renderAll(); }));
    host.querySelectorAll("[data-year-month]").forEach((b) => b.addEventListener("click", () => { T.month0 = Number(b.getAttribute("data-year-month")); T.view = "month"; renderAll(); }));
  }

  // ---- summary cards ---------------------------------------------------------------------------
  function renderSummary(idx) {
    const s = idx.status;
    const host = document.getElementById("tracker-summary");
    if (!host) return;
    if (!s.hasData) {
      host.innerHTML = `<div class="card card-pad sm:col-span-2 xl:col-span-4">
        <div class="empty-state">
          <span class="icon-bubble icon-bubble-lg bubble-blush"><span class="material-symbols-outlined">water_drop</span></span>
          <h4>${t("trk.empty_title")}</h4><p>${t("trk.empty_body")}</p>
          <button type="button" class="btn btn-primary btn-sm mt-2" data-open-period-modal>${t("trk.log_period")}</button>
        </div></div>`;
      return;
    }
    const phaseTone = { menstrual: "badge-blush", follicular: "badge-peach", fertile: "badge-sage", ovulation: "badge-sage", luteal: "badge-lavender", late: "badge-danger" }[s.phase] || "badge-neutral";
    const nextText = s.daysToNextPeriod > 0 ? t("trk.next_in", { n: s.daysToNextPeriod }) : s.daysToNextPeriod === 0 ? t("trk.next_today") : t("trk.late_by", { n: s.lateByDays });
    const last = s.lastPeriod;
    const lastRange = last.end_date ? `${D.formatISODate(last.start_date, AppState.lang, { day: "numeric", month: "short" })} – ${D.formatISODate(last.end_date, AppState.lang, { day: "numeric", month: "short" })}` : t("trk.started_on", { date: D.formatISODate(last.start_date, AppState.lang, { day: "numeric", month: "short" }) });
    const lastDur = last.end_date ? t("common.n_days", { n: D.diffDays(last.start_date, last.end_date) + 1 }) : t("trk.ongoing");
    host.innerHTML = `
      <div class="card card-pad flex flex-col gap-2">
        <div class="row-between"><span class="caption font-semibold">${t("trk.card_cycle_day")}</span><span class="badge ${phaseTone}">${t(`phase.${s.phase}`)}</span></div>
        <div class="stat-value">${t("cycle.day_n", { n: s.cycleDay })}</div>
        <div class="w-full h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden"><div class="h-full rounded-full bg-[var(--rose)]" style="width:${Math.round(s.progress * 100)}%"></div></div>
        <p class="caption">${t(`phase.${s.phase}_short`)}</p>
      </div>
      <div class="card card-pad flex flex-col gap-2">
        <span class="caption font-semibold">${t("trk.card_next")}</span>
        <div class="stat-value text-[var(--rose-deep)]">${D.formatISODate(s.nextPeriodStart, AppState.lang, { day: "numeric", month: "short" })}</div>
        <p class="caption">${nextText}</p>
      </div>
      <div class="card card-pad flex flex-col gap-2">
        <span class="caption font-semibold">${t("trk.card_cycle_len")}</span>
        <div class="stat-value">${t("common.n_days", { n: s.cycleLength })}</div>
        <p class="caption">${s.cycleSource === "logged" ? t("trk.based_on_cycles", { n: s.loggedCycles }) : t("trk.baseline_note")}</p>
      </div>
      <div class="card card-pad flex flex-col gap-2">
        <span class="caption font-semibold">${t("trk.card_last")}</span>
        <div class="stat-value">${lastDur}</div>
        <p class="caption">${lastRange}${last.flow ? ` · ${t(`flow.${last.flow}`)}` : ""}</p>
      </div>`;
  }

  // ---- legend --------------------------------------------------------------------------------------
  function renderLegend() {
    const host = document.getElementById("calendar-legend");
    if (!host) return;
    host.innerHTML = `
      <span><i class="swatch swatch-period"></i>${t("cal.leg_period")}</span>
      <span><i class="swatch swatch-predicted"></i>${t("cal.leg_predicted")}</span>
      <span><i class="swatch swatch-fertile"></i>${t("cal.leg_fertile")}</span>
      <span><i class="swatch swatch-ovulation"></i>${t("cal.leg_ovulation")}</span>
      <span><i class="swatch swatch-symptom"></i>${t("cal.leg_symptoms")}</span>
      <span><i class="swatch swatch-today"></i>${t("date.today")}</span>`;
  }

  // ---- day panel -------------------------------------------------------------------------------------
  function loadFormFromRecords(iso, idx) {
    const p = idx.periodByDay.get(iso);
    const symptoms = idx.symptomsByDay.get(iso) || [];
    T.form = {
      flow: p && p.period.flow ? p.period.flow : p ? "light" : "none",
      flowFromRecord: !!p,
      symptoms: new Set(symptoms.map((s) => s.symptom)),
      severity: symptoms.reduce((m, s) => Math.max(m, s.severity || 0), 0) || 2,
      notes: (symptoms.find((s) => s.notes) || {}).notes || "",
    };
    T.formDate = iso;
    T.dirty = false;
  }

  function latestSavedAt(iso, idx) {
    const symptoms = idx.symptomsByDay.get(iso) || [];
    const p = idx.periodByDay.get(iso);
    const stamps = symptoms.map((s) => s.updated_at).concat(p ? [p.period.updated_at] : []).filter(Boolean);
    if (!stamps.length) return null;
    return stamps.sort().pop();
  }

  function renderDayPanel(idx) {
    const host = document.getElementById("day-panel");
    if (!host) return;
    const iso = T.selected;
    if (T.formDate !== iso || !T.dirty) loadFormFromRecords(iso, idx);
    const future = iso > idx.today;
    const rel = D.relativeDayLabel(iso, idx.today, AppState.lang);
    const relText = rel.key ? t(rel.key) : rel.text;
    const fullDate = D.formatISODate(iso, AppState.lang, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    const cycleDay = C.cycleDayFor(AppState.data.periods, iso);
    const p = idx.periodByDay.get(iso);
    const mark = idx.marks.get(iso);
    const badges = [];
    if (cycleDay) badges.push(`<span class="badge badge-neutral">${t("cycle.day_n", { n: cycleDay })}</span>`);
    if (p) badges.push(`<span class="badge badge-rose"><span class="material-symbols-outlined">water_drop</span>${t("cal.leg_period")}${p.open ? ` · ${t("trk.ongoing")}` : ""}</span>`);
    else if (mark === "predicted") badges.push(`<span class="badge badge-blush">${t("cal.leg_predicted")}</span>`);
    else if (mark === "fertile" || mark === "ovulation") badges.push(`<span class="badge badge-sage">${t(`cal.leg_${mark}`)}</span>`);
    const savedAt = latestSavedAt(iso, idx);
    const hasRecords = !!p || (idx.symptomsByDay.get(iso) || []).length > 0;

    const groups = catalogue();
    const sevOn = T.form.symptoms.size > 0;
    host.innerHTML = `
      <div class="flex items-start justify-between gap-3 mb-4">
        <div>
          <div class="eyebrow">${relText}</div>
          <h2 class="h2 mt-1">${fullDate}</h2>
          <div class="flex flex-wrap gap-1.5 mt-2">${badges.join("")}</div>
        </div>
        ${p ? `<button type="button" class="btn btn-ghost btn-sm" data-edit-period="${p.period.id}"><span class="material-symbols-outlined">edit_calendar</span>${t("trk.edit_period")}</button>` : ""}
      </div>
      ${future ? `<div class="notice notice-neutral"><span class="material-symbols-outlined">schedule</span><span>${t("trk.future_hint")}</span></div>` : `
      <div class="grid gap-5" id="day-form">
        <div class="field">
          <div class="row-between"><span class="field-label">${t("trk.flow_title")}</span><span class="field-hint">${t("trk.flow_hint")}</span></div>
          <div class="seg" role="radiogroup" aria-label="${t("trk.flow_title")}">
            ${FLOWS.map((f) => `<button type="button" class="seg-btn ${T.form.flow === f ? "is-on" : ""}" role="radio" aria-checked="${T.form.flow === f}" data-flow="${f}">${t(`flow.${f}`)}</button>`).join("")}
          </div>
        </div>
        ${groups.map((g) => `
        <div class="field">
          <div class="row-between"><span class="field-label">${t(`group.${g.group}`)}</span>${g.group === "pain" ? `<span class="field-hint">${t("trk.tap_all")}</span>` : ""}</div>
          <div class="chip-group" role="group">
            ${g.items.map((item) => `<button type="button" class="chip ${GROUP_TONE[g.group]} ${T.form.symptoms.has(item.key) ? "is-on" : ""}" data-symptom="${item.key}" aria-pressed="${T.form.symptoms.has(item.key)}"><span class="material-symbols-outlined chip-check">check</span>${symptomLabel(item.key)}</button>`).join("")}
          </div>
        </div>`).join("")}
        <div class="field ${sevOn ? "" : "opacity-50"}">
          <div class="row-between"><span class="field-label">${t("trk.severity_title")}</span><span class="field-hint">${t("trk.severity_hint")}</span></div>
          <div class="seg" role="radiogroup">
            ${[1, 2, 3].map((n) => `<button type="button" class="seg-btn ${T.form.severity === n ? "is-on" : ""}" role="radio" aria-checked="${T.form.severity === n}" data-severity="${n}" ${sevOn ? "" : "disabled"}>${t(`severity.${n}`)}</button>`).join("")}
          </div>
        </div>
        <div class="field" id="day-notes-field">
          <div class="row-between"><label class="field-label" for="day-notes">${t("trk.notes_title")}</label><span class="field-hint" id="day-notes-count">${T.form.notes.length}/500</span></div>
          <textarea class="textarea" id="day-notes" maxlength="500" rows="3" placeholder="${t("trk.notes_placeholder")}">${escapeHtml(T.form.notes)}</textarea>
          <span class="field-error" id="day-notes-error"></span>
        </div>
        <div class="notice notice-error" id="day-error" hidden><span class="material-symbols-outlined">error</span><span></span></div>
        <div class="flex flex-wrap items-center gap-3">
          <button type="button" class="btn btn-primary" id="btn-save-day"><span class="material-symbols-outlined">check</span>${t("trk.btn_save")}</button>
          ${hasRecords ? `<button type="button" class="btn btn-ghost" id="btn-delete-day"><span class="material-symbols-outlined">delete</span>${t("trk.btn_delete_day")}</button>` : `<button type="button" class="btn btn-ghost" id="btn-clear-day">${t("trk.btn_clear")}</button>`}
          <span class="caption ml-auto" id="day-saved-at">${savedAt ? t("trk.saved_at", { time: D.formatDateTime(savedAt, AppState.lang) }) : t("trk.nothing_logged")}</span>
        </div>
      </div>`}`;
    bindDayPanel(host, idx);
  }

  function bindDayPanel(host, idx) {
    host.querySelectorAll("[data-flow]").forEach((b) => b.addEventListener("click", () => {
      T.form.flow = b.getAttribute("data-flow"); T.dirty = true;
      host.querySelectorAll("[data-flow]").forEach((x) => { const on = x === b; x.classList.toggle("is-on", on); x.setAttribute("aria-checked", String(on)); });
    }));
    host.querySelectorAll("[data-symptom]").forEach((b) => b.addEventListener("click", () => {
      const key = b.getAttribute("data-symptom");
      T.form.symptoms.has(key) ? T.form.symptoms.delete(key) : T.form.symptoms.add(key);
      T.dirty = true;
      b.classList.toggle("is-on", T.form.symptoms.has(key));
      b.setAttribute("aria-pressed", String(T.form.symptoms.has(key)));
      const on = T.form.symptoms.size > 0;
      host.querySelectorAll("[data-severity]").forEach((x) => { x.disabled = !on; });
      host.querySelector("[data-severity]")?.closest(".field").classList.toggle("opacity-50", !on);
    }));
    host.querySelectorAll("[data-severity]").forEach((b) => b.addEventListener("click", () => {
      T.form.severity = Number(b.getAttribute("data-severity")); T.dirty = true;
      host.querySelectorAll("[data-severity]").forEach((x) => { const on = x === b; x.classList.toggle("is-on", on); x.setAttribute("aria-checked", String(on)); });
    }));
    const notes = host.querySelector("#day-notes");
    notes?.addEventListener("input", () => { T.form.notes = notes.value; T.dirty = true; host.querySelector("#day-notes-count").textContent = `${notes.value.length}/500`; });
    host.querySelector("#btn-save-day")?.addEventListener("click", () => saveDay(idx));
    host.querySelector("#btn-delete-day")?.addEventListener("click", () => deleteDay(idx));
    host.querySelector("#btn-clear-day")?.addEventListener("click", () => { loadFormFromRecords(T.selected, idx); renderDayPanel(idx); });
    host.querySelector("[data-edit-period]")?.addEventListener("click", (e) => openPeriodModal(e.currentTarget.getAttribute("data-edit-period")));
  }

  function showDayError(message) {
    const box = document.getElementById("day-error");
    if (!box) return;
    box.hidden = !message;
    box.lastElementChild.textContent = message || "";
  }

  // ---- saving --------------------------------------------------------------------------------------------
  function pick(p) { return { start_date: p.start_date, end_date: p.end_date, flow: p.flow, notes: p.notes }; }

  /** Translate a flow choice for one day into period-record operations. */
  async function applyFlow(iso, flow) {
    const today = D.todayISO();
    const periods = AppState.data.periods;
    const covering = C.periodCovering(periods, iso, today);
    if (flow === "none") {
      if (!covering) return;
      const end = covering.end_date || today;
      if (covering.start_date === iso && end === iso) return api.tracker.deletePeriod(covering.id);
      if (covering.start_date === iso) return api.tracker.updatePeriod(covering.id, { ...pick(covering), start_date: D.addDays(iso, 1) });
      if (end === iso) return api.tracker.updatePeriod(covering.id, { ...pick(covering), end_date: D.addDays(iso, -1) });
      // Removing a middle day splits the record in two.
      await api.tracker.updatePeriod(covering.id, { ...pick(covering), end_date: D.addDays(iso, -1) });
      return api.tracker.createPeriod({ start_date: D.addDays(iso, 1), end_date: covering.end_date, flow: covering.flow, notes: null });
    }
    if (covering) {
      if (covering.flow !== flow) return api.tracker.updatePeriod(covering.id, { ...pick(covering), flow });
      return;
    }
    const prev = periods.find((p) => (p.end_date || p.start_date) === D.addDays(iso, -1));
    if (prev) return api.tracker.updatePeriod(prev.id, { ...pick(prev), end_date: iso, flow: prev.flow || flow });
    const next = periods.find((p) => p.start_date === D.addDays(iso, 1));
    if (next) return api.tracker.updatePeriod(next.id, { ...pick(next), start_date: iso, flow: next.flow || flow });
    return api.tracker.createPeriod({ start_date: iso, end_date: iso, flow, notes: null });
  }

  async function applySymptoms(iso, idx) {
    const existing = idx.symptomsByDay.get(iso) || [];
    const selected = T.form.symptoms;
    const severity = T.form.severity;
    const notes = T.form.notes.trim() || null;
    const ops = [];
    for (const e of existing) {
      if (!selected.has(e.symptom)) ops.push(api.tracker.deleteSymptom(e.id));
      else if (e.severity !== severity || (e.notes || null) !== notes) ops.push(api.tracker.updateSymptom(e.id, { record_date: iso, symptom: e.symptom, severity, notes }));
    }
    const existingKeys = new Set(existing.map((e) => e.symptom));
    for (const key of selected) if (!existingKeys.has(key)) ops.push(api.tracker.createSymptom({ record_date: iso, symptom: key, severity, notes }));
    await Promise.all(ops);
    return ops.length;
  }

  async function saveDay(idx) {
    if (T.saving) return;
    const iso = T.selected;
    showDayError("");
    const notes = T.form.notes.trim();
    const nothingChosen = T.form.flow === "none" && T.form.symptoms.size === 0;
    const hadRecords = idx.periodByDay.has(iso) || (idx.symptomsByDay.get(iso) || []).length > 0;
    if (nothingChosen && !hadRecords) { showDayError(notes ? t("trk.err_note_needs_symptom") : t("trk.err_nothing")); return; }
    if (notes && T.form.symptoms.size === 0) { showDayError(t("trk.err_note_needs_symptom")); return; }
    if (notes.length > 500) { showDayError(t("trk.err_notes_long")); return; }

    const btn = document.getElementById("btn-save-day");
    T.saving = true;
    btn.classList.add("is-loading"); btn.insertAdjacentHTML("beforeend", '<span class="spinner"></span>');
    try {
      await applyFlow(iso, T.form.flow);
      await applySymptoms(iso, idx);
      T.dirty = false;
      await window.SakhiData.refreshAll();
      showToast(t("trk.toast_saved", { date: D.formatISODate(iso, AppState.lang, { day: "numeric", month: "short" }), time: D.formatTime(new Date(), AppState.lang) }), "success");
    } catch (err) {
      // Keep the user's input; show exactly what went wrong.
      showDayError(err.message || t("trk.err_generic"));
      if (err && err.code === "network") showToast(err.message, "error", 5000);
      try { await window.SakhiData.loadRecords(); } catch { /* keep going */ }
    } finally {
      T.saving = false;
      const b = document.getElementById("btn-save-day");
      if (b) { b.classList.remove("is-loading"); b.querySelector(".spinner")?.remove(); }
    }
  }

  async function deleteDay(idx) {
    const iso = T.selected;
    const ok = await confirmDialog({ title: t("trk.delete_day_title"), message: t("trk.delete_day_msg", { date: D.formatISODate(iso, AppState.lang, { weekday: "long", day: "numeric", month: "long" }) }), confirmLabel: t("common.delete"), danger: true });
    if (!ok) return;
    try {
      const symptoms = idx.symptomsByDay.get(iso) || [];
      await Promise.all(symptoms.map((s) => api.tracker.deleteSymptom(s.id)));
      await applyFlow(iso, "none");
      T.dirty = false;
      await window.SakhiData.refreshAll();
      showToast(t("trk.toast_deleted"), "info");
    } catch (err) {
      showDayError(err.message);
    }
  }

  // ---- period modal (explicit start/end editing) ----------------------------------------------------
  function openPeriodModal(periodId) {
    const p = periodId ? AppState.data.periods.find((x) => x.id === periodId) : null;
    T.periodModal.id = p ? p.id : null;
    const today = D.todayISO();
    const start = document.getElementById("pm-start");
    const end = document.getElementById("pm-end");
    start.max = today; end.max = today;
    start.value = p ? p.start_date : (T.selected && T.selected <= today ? T.selected : today);
    end.value = p && p.end_date ? p.end_date : "";
    document.getElementById("pm-notes").value = p && p.notes ? p.notes : "";
    const flow = p && p.flow ? p.flow : "medium";
    document.querySelectorAll("#pm-flow [data-pm-flow]").forEach((b) => { const on = b.getAttribute("data-pm-flow") === flow; b.classList.toggle("is-on", on); b.setAttribute("aria-checked", String(on)); });
    document.getElementById("pm-title").textContent = p ? t("pm.title_edit") : t("pm.title_new");
    document.getElementById("pm-delete").hidden = !p;
    document.getElementById("pm-error").hidden = true;
    document.querySelectorAll("#period-modal .field").forEach((f) => f.classList.remove("has-error"));
    openModal("period-modal");
  }

  function pmFlow() {
    const on = document.querySelector("#pm-flow [data-pm-flow].is-on");
    return on ? on.getAttribute("data-pm-flow") : null;
  }

  async function savePeriodModal() {
    const start = document.getElementById("pm-start").value;
    const endRaw = document.getElementById("pm-end").value;
    const notes = document.getElementById("pm-notes").value.trim();
    const today = D.todayISO();
    const errBox = document.getElementById("pm-error");
    errBox.hidden = true;
    const startField = document.getElementById("pm-start-field");
    const endField = document.getElementById("pm-end-field");
    startField.classList.remove("has-error"); endField.classList.remove("has-error");
    if (!D.isValidISODate(start)) { startField.classList.add("has-error"); startField.querySelector(".field-error").textContent = t("pm.err_start"); return; }
    if (start > today) { startField.classList.add("has-error"); startField.querySelector(".field-error").textContent = t("pm.err_future"); return; }
    if (endRaw) {
      if (!D.isValidISODate(endRaw)) { endField.classList.add("has-error"); endField.querySelector(".field-error").textContent = t("pm.err_end"); return; }
      if (endRaw < start) { endField.classList.add("has-error"); endField.querySelector(".field-error").textContent = t("pm.err_end_before"); return; }
      if (endRaw > today) { endField.classList.add("has-error"); endField.querySelector(".field-error").textContent = t("pm.err_future"); return; }
      if (D.diffDays(start, endRaw) > 30) { endField.classList.add("has-error"); endField.querySelector(".field-error").textContent = t("pm.err_too_long"); return; }
    }
    const body = { start_date: start, end_date: endRaw || null, flow: pmFlow(), notes: notes || null };
    const btn = document.getElementById("pm-save");
    btn.classList.add("is-loading"); btn.insertAdjacentHTML("beforeend", '<span class="spinner"></span>');
    try {
      if (T.periodModal.id) await api.tracker.updatePeriod(T.periodModal.id, body);
      else await api.tracker.createPeriod(body);
      closeModal("period-modal");
      T.selected = start; T.dirty = false;
      const d = D.parseISODate(start); T.year = d.getFullYear(); T.month0 = d.getMonth();
      await window.SakhiData.refreshAll();
      showToast(T.periodModal.id ? t("pm.toast_updated") : t("pm.toast_created"), "success");
    } catch (err) {
      errBox.hidden = false;
      errBox.lastElementChild.textContent = err.message;
    } finally {
      btn.classList.remove("is-loading"); btn.querySelector(".spinner")?.remove();
    }
  }

  async function deletePeriodFromModal() {
    if (!T.periodModal.id) return;
    const ok = await confirmDialog({ title: t("pm.delete_title"), message: t("pm.delete_msg"), confirmLabel: t("common.delete"), danger: true });
    if (!ok) return;
    try {
      await api.tracker.deletePeriod(T.periodModal.id);
      closeModal("period-modal");
      await window.SakhiData.refreshAll();
      showToast(t("pm.toast_deleted"), "info");
    } catch (err) {
      const errBox = document.getElementById("pm-error");
      errBox.hidden = false; errBox.lastElementChild.textContent = err.message;
    }
  }

  // ---- history list -------------------------------------------------------------------------------------
  function renderHistory() {
    const host = document.getElementById("period-history");
    if (!host) return;
    const periods = C.sortPeriods(AppState.data.periods).reverse();
    if (!periods.length) {
      host.innerHTML = `<p class="caption">${t("trk.history_empty")}</p>`;
      return;
    }
    const lengths = C.cycleLengths(AppState.data.periods);
    host.innerHTML = periods.slice(0, 12).map((p, i) => {
      const dur = p.end_date ? t("common.n_days", { n: D.diffDays(p.start_date, p.end_date) + 1 }) : t("trk.ongoing");
      const range = p.end_date ? `${D.formatISODate(p.start_date, AppState.lang, { day: "numeric", month: "short" })} – ${D.formatISODate(p.end_date, AppState.lang, { day: "numeric", month: "short", year: "numeric" })}` : D.formatISODate(p.start_date, AppState.lang, { day: "numeric", month: "short", year: "numeric" });
      const cycleLen = i < periods.length - 1 ? D.diffDays(periods[i + 1].start_date, p.start_date) : null;
      void lengths;
      return `<div class="list-item">
        <div class="flex items-center gap-3 min-w-0">
          <span class="icon-bubble bubble-blush"><span class="material-symbols-outlined">water_drop</span></span>
          <div class="min-w-0">
            <div class="font-semibold text-sm truncate">${range}</div>
            <div class="caption">${dur}${p.flow ? ` · ${t(`flow.${p.flow}`)}` : ""}${cycleLen ? ` · ${t("trk.cycle_len_n", { n: cycleLen })}` : ""}</div>
          </div>
        </div>
        <button type="button" class="btn btn-ghost btn-xs" data-edit-period="${p.id}"><span class="material-symbols-outlined">edit</span>${t("common.edit")}</button>
      </div>`;
    }).join("");
    host.querySelectorAll("[data-edit-period]").forEach((b) => b.addEventListener("click", () => openPeriodModal(b.getAttribute("data-edit-period"))));
  }

  // ---- orchestration -------------------------------------------------------------------------------
  function renderAll() {
    const idx = indexes();
    renderSummary(idx);
    renderLegend();
    renderCalendar(idx);
    renderDayPanel(idx);
    renderHistory();
  }

  function selectDate(iso, { scrollToPanel = false } = {}) {
    if (T.dirty && iso !== T.selected) {
      // keep unsaved input unless the user confirms switching
      const ok = window.confirm(t("trk.unsaved_confirm"));
      if (!ok) return;
    }
    T.selected = iso;
    T.dirty = false;
    const d = D.parseISODate(iso);
    T.year = d.getFullYear(); T.month0 = d.getMonth();
    T.view = "month";
    renderAll();
    if (scrollToPanel) setTimeout(() => document.getElementById("day-panel")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  }

  function goToToday({ focusPanel = false } = {}) {
    switchRoute("period-symptom-tracker");
    selectDate(D.todayISO(), { scrollToPanel: focusPanel });
  }

  function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

  document.addEventListener("DOMContentLoaded", () => {
    T.selected = D.todayISO();
    ensureMonth();
    document.getElementById("calendar-days-grid")?.addEventListener("click", (e) => {
      const cell = e.target.closest("[data-cal-date]");
      if (cell) selectDate(cell.getAttribute("data-cal-date"));
    });
    document.getElementById("btn-prev-month")?.addEventListener("click", () => { const m = D.shiftMonth(T.year, T.month0, -1); T.year = m.year; T.month0 = m.month0; renderAll(); });
    document.getElementById("btn-next-month")?.addEventListener("click", () => { const m = D.shiftMonth(T.year, T.month0, 1); T.year = m.year; T.month0 = m.month0; renderAll(); });
    document.getElementById("btn-today-month")?.addEventListener("click", () => selectDate(D.todayISO()));
    document.querySelectorAll("[data-cal-view]").forEach((b) => b.addEventListener("click", () => { T.view = b.getAttribute("data-cal-view"); renderAll(); }));
    document.addEventListener("click", (e) => {
      if (e.target.closest("[data-open-period-modal]")) openPeriodModal(null);
      if (e.target.closest("[data-log-today]")) goToToday({ focusPanel: true });
    });
    document.getElementById("pm-save")?.addEventListener("click", savePeriodModal);
    document.getElementById("pm-delete")?.addEventListener("click", deletePeriodFromModal);
    document.querySelectorAll("#pm-flow [data-pm-flow]").forEach((b) => b.addEventListener("click", () => {
      document.querySelectorAll("#pm-flow [data-pm-flow]").forEach((x) => { const on = x === b; x.classList.toggle("is-on", on); x.setAttribute("aria-checked", String(on)); });
    }));
  });
  document.addEventListener("sakhi:data", () => renderAll());
  document.addEventListener("sakhi:lang", () => renderAll());

  window.SakhiTracker = { renderAll, selectDate, goToToday, openPeriodModal, indexes };
})();
