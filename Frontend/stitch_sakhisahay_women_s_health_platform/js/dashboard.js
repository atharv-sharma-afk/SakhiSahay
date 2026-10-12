/* ==========================================================================
   Overview / dashboard. Everything shown is computed from the user's records.
   ========================================================================== */
(function () {
  const D = window.SakhiDates;
  const C = window.SakhiCycle;

  const R = 96;
  const CIRC = 2 * Math.PI * R;

  function arc(fromDay, toDay, total, color, width) {
    // days are 1-indexed inclusive; draw [fromDay-1, toDay) of `total`
    const start = Math.max(fromDay - 1, 0) / total;
    const end = Math.min(toDay, total) / total;
    const len = Math.max(end - start, 0) * CIRC;
    if (len <= 0) return "";
    return `<circle cx="120" cy="120" r="${R}" fill="none" stroke="${color}" stroke-width="${width || 16}" stroke-linecap="butt" stroke-dasharray="${len} ${CIRC - len}" stroke-dashoffset="${-start * CIRC}"></circle>`;
  }

  function renderRing(status) {
    const host = document.getElementById("dash-ring");
    if (!host) return;
    if (!status.hasData) {
      host.innerHTML = `<div class="ring-wrap">
        <svg viewBox="0 0 240 240"><circle cx="120" cy="120" r="${R}" fill="none" stroke="var(--surface-2)" stroke-width="16"/></svg>
        <div class="ring-center"><span class="material-symbols-outlined text-3xl text-[var(--rose)]">water_drop</span><span class="font-semibold mt-1">${t("dash.ring_empty")}</span></div>
      </div>`;
      return;
    }
    const total = status.cycleLength;
    const pLen = Math.min(status.periodLength, total);
    const ovDay = total - C.LUTEAL_DAYS;
    const fStart = Math.max(ovDay - 5, pLen + 1);
    const fEnd = Math.min(ovDay + 1, total);
    const day = Math.min(status.cycleDay, total);
    const angle = ((day - 0.5) / total) * 360;
    host.innerHTML = `<div class="ring-wrap">
      <svg viewBox="0 0 240 240" aria-hidden="true">
        <circle cx="120" cy="120" r="${R}" fill="none" stroke="var(--surface-2)" stroke-width="16"/>
        ${arc(1, pLen, total, "var(--rose)")}
        ${arc(pLen + 1, fStart - 1, total, "var(--blush)")}
        ${arc(fStart, fEnd, total, "var(--sage)")}
        ${arc(fEnd + 1, total, total, "var(--lavender)")}
        <g transform="rotate(${angle} 120 120)">
          <circle cx="216" cy="120" r="10" fill="var(--rose-deep)"/>
          <circle cx="216" cy="120" r="4" fill="#fff"/>
        </g>
      </svg>
      <div class="ring-center">
        <span class="eyebrow">${t(`phase.${status.phase}`)}</span>
        <span class="h-display mt-1">${t("cycle.day_n", { n: status.cycleDay })}</span>
        <span class="caption mt-1">${status.phase === "late" ? t("trk.late_by", { n: status.lateByDays }) : status.daysToNextPeriod === 0 ? t("trk.next_today") : t("dash.next_in", { n: status.daysToNextPeriod })}</span>
      </div>
    </div>`;
  }

  function renderStatus(status) {
    const chip = document.getElementById("dash-status-chip");
    if (chip) {
      chip.textContent = status.hasData ? `${t("cycle.day_n", { n: status.cycleDay })} · ${t(`phase.${status.phase}`)}` : t("dash.no_cycle_yet");
    }
    const legend = document.getElementById("dash-ring-legend");
    if (legend) {
      if (!status.hasData) { legend.innerHTML = `<p class="body-sm muted">${t("dash.ring_empty_body")}</p><button type="button" class="btn btn-primary btn-sm mt-3 self-start" data-open-period-modal>${t("trk.log_period")}</button>`; return; }
      const total = status.cycleLength, pLen = status.periodLength, ov = total - C.LUTEAL_DAYS;
      const rows = [
        ["var(--rose)", t("phase.menstrual"), t("dash.days_range", { a: 1, b: pLen })],
        ["var(--blush)", t("phase.follicular"), t("dash.days_range", { a: pLen + 1, b: Math.max(ov - 6, pLen + 1) })],
        ["var(--sage)", t("phase.fertile"), t("dash.days_range", { a: Math.max(ov - 5, pLen + 1), b: Math.min(ov + 1, total) })],
        ["var(--lavender)", t("phase.luteal"), t("dash.days_range", { a: Math.min(ov + 2, total), b: total })],
      ];
      legend.innerHTML = `${rows.map(([c, l, s]) => `<div class="flex items-center gap-2.5"><span class="w-3 h-3 rounded-full shrink-0" style="background:${c}"></span><div><div class="text-sm font-semibold">${l}</div><div class="caption">${s}</div></div></div>`).join("")}
        <div class="divider my-1"></div>
        <div class="flex items-start gap-2.5"><span class="material-symbols-outlined text-[var(--rose-deep)] text-xl">event_upcoming</span><div><div class="text-sm font-semibold">${t("dash.next_period")}</div><div class="caption">${D.formatISODate(status.nextPeriodStart, AppState.lang, { weekday: "short", day: "numeric", month: "short" })} · ${status.cycleSource === "logged" ? t("trk.based_on_cycles", { n: status.loggedCycles }) : t("trk.baseline_note")}</div></div></div>`;
    }
  }

  function renderToday() {
    const host = document.getElementById("dash-today");
    if (!host) return;
    const today = D.todayISO();
    const idx = window.SakhiTracker ? window.SakhiTracker.indexes() : null;
    const symptoms = idx ? idx.symptomsByDay.get(today) || [] : [];
    const period = idx ? idx.periodByDay.get(today) : null;
    const nothing = !symptoms.length && !period;
    const chips = [];
    if (period) chips.push(`<span class="badge badge-rose"><span class="material-symbols-outlined">water_drop</span>${period.period.flow ? t(`flow.${period.period.flow}`) : t("cal.leg_period")}</span>`);
    for (const s of symptoms) chips.push(`<span class="badge ${s.severity === 3 ? "badge-peach" : "badge-neutral"}">${window.SakhiTracker ? symLabel(s.symptom) : s.symptom}</span>`);
    const latest = symptoms.map((s) => s.updated_at).concat(period ? [period.period.updated_at] : []).sort().pop();
    host.innerHTML = `
      <div class="row-between mb-3">
        <div><div class="eyebrow">${t("dash.today_title")}</div><div class="caption mt-0.5">${D.formatISODate(today, AppState.lang, { weekday: "long", day: "numeric", month: "long" })}</div></div>
        <button type="button" class="btn btn-primary btn-sm" data-log-today><span class="material-symbols-outlined">${nothing ? "add" : "edit"}</span>${nothing ? t("dash.log_today") : t("common.edit")}</button>
      </div>
      ${nothing ? `<p class="body-sm muted">${t("dash.today_empty")}</p>` : `<div class="flex flex-wrap gap-1.5">${chips.join("")}</div><p class="caption mt-3">${t("trk.saved_at", { time: D.formatTime(latest, AppState.lang) })}</p>`}`;
  }

  function symLabel(key) {
    const k = `sym.${key}`;
    const tr = t(k);
    if (tr !== k) return tr;
    const item = (AppState.data.catalogue || []).find((c) => c.key === key);
    return item ? item.label : key;
  }

  function renderInsights() {
    const host = document.getElementById("dash-insights");
    if (!host) return;
    const data = AppState.data.insights;
    if (!data) { host.innerHTML = `<p class="body-sm muted">${t("ins.loading")}</p>`; return; }
    const items = data.insights.slice(0, 2);
    const reqs = data.requirements.slice(0, items.length ? 1 : 2);
    host.innerHTML = `
      ${items.map((i) => `<div class="p-4 rounded-[14px] bg-[var(--surface-2)]"><div class="text-sm font-semibold mb-1">${escapeHtml(i.title)}</div><p class="body-sm">${escapeHtml(i.statement)}</p></div>`).join("")}
      ${reqs.map((r) => `<div class="p-4 rounded-[14px] card-tint-lavender flex gap-3"><span class="material-symbols-outlined text-[var(--lavender-deep)]">lightbulb</span><p class="body-sm">${escapeHtml(r.message)}</p></div>`).join("")}
      ${!items.length && !reqs.length ? `<p class="body-sm muted">${t("ins.none")}</p>` : ""}`;
  }

  function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

  function render() {
    const status = C.currentStatus(AppState.data.periods, AppState.data.profile, D.todayISO());
    renderRing(status);
    renderStatus(status);
    renderToday();
    renderInsights();
  }

  document.addEventListener("sakhi:data", render);
  document.addEventListener("sakhi:insights", renderInsights);
  document.addEventListener("sakhi:lang", render);
  window.SakhiDashboard = { render };
})();
