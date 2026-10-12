/* ==========================================================================
   Secondary pages: Health Insights (+ data export), Doctor Connect (demo
   directory from the API, clearly labelled), Privacy data controls, Settings.
   ========================================================================== */
(function () {
  const D = window.SakhiDates;
  const C = window.SakhiCycle;
  const api = window.SakhiApi;

  function escapeHtml(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

  // ---- Insights ------------------------------------------------------------------------------------
  function renderInsights() {
    const stats = document.getElementById("ins-stats");
    const list = document.getElementById("ins-list");
    if (!stats || !list) return;
    const data = AppState.data.insights;
    if (!data) {
      stats.innerHTML = Array.from({ length: 4 }, () => `<div class="card card-pad"><div class="skeleton h-3 w-24 mb-3"></div><div class="skeleton h-7 w-16"></div></div>`).join("");
      list.innerHTML = "";
      return;
    }
    const s = data.stats;
    const fmt = (v, unit) => (v == null ? "—" : `${Number.isInteger(v) ? v : v.toFixed(1)}${unit ? ` ${unit}` : ""}`);
    stats.innerHTML = `
      <div class="card card-pad"><div class="caption font-semibold mb-1">${t("ins.stat_periods")}</div><div class="stat-value">${s.logged_periods}</div><div class="caption mt-1">${t("ins.stat_cycles_n", { n: s.completed_cycles })}</div></div>
      <div class="card card-pad"><div class="caption font-semibold mb-1">${t("ins.stat_avg_cycle")}</div><div class="stat-value">${fmt(s.average_cycle_length, t("common.days"))}</div><div class="caption mt-1">${s.shortest_cycle != null ? t("ins.range", { a: s.shortest_cycle, b: s.longest_cycle }) : t("ins.needs_more")}</div></div>
      <div class="card card-pad"><div class="caption font-semibold mb-1">${t("ins.stat_avg_period")}</div><div class="stat-value">${fmt(s.average_period_duration, t("common.days"))}</div><div class="caption mt-1">${t("ins.with_end_dates", { n: s.periods_with_duration })}</div></div>
      <div class="card card-pad"><div class="caption font-semibold mb-1">${t("ins.stat_since_last")}</div><div class="stat-value">${s.days_since_last_period_start == null ? "—" : t("common.n_days", { n: s.days_since_last_period_start })}</div><div class="caption mt-1">${s.last_period_start ? D.formatISODate(s.last_period_start, AppState.lang) : t("ins.no_period_yet")}</div></div>`;

    const kindTone = { cycle_length: "bubble-blush", period_duration: "bubble-peach", symptom_frequency: "bubble-lavender", symptom_days: "bubble-lavender", guidance: "bubble-sage" };
    const kindIcon = { cycle_length: "repeat", period_duration: "calendar_view_week", symptom_frequency: "monitor_heart", symptom_days: "event_note", guidance: "menu_book" };
    const insights = data.insights.map((i) => `
      <article class="card card-pad">
        <div class="flex items-start gap-3">
          <span class="icon-bubble ${kindTone[i.kind] || "bubble-blush"}"><span class="material-symbols-outlined">${kindIcon[i.kind] || "insights"}</span></span>
          <div class="min-w-0 flex-1">
            <h3 class="h3">${escapeHtml(i.title)}</h3>
            <p class="body mt-1">${escapeHtml(i.statement)}</p>
            <details class="mt-2"><summary class="caption cursor-pointer select-none">${t("ins.how_calculated")}</summary><p class="caption mt-1">${escapeHtml(i.basis)} ${t("ins.records_used", { n: i.records_used })}</p></details>
            ${i.source_url ? `<a class="caption inline-flex items-center gap-1 mt-2 text-[var(--rose-deep)] font-semibold" href="${escapeHtml(i.source_url)}" target="_blank" rel="noopener">${escapeHtml(i.source_label || i.source_url)} <span class="material-symbols-outlined text-xs">open_in_new</span></a>` : ""}
          </div>
        </div>
      </article>`);
    const reqs = data.requirements.map((r) => `
      <div class="notice notice-info"><span class="material-symbols-outlined">lightbulb</span><span>${escapeHtml(r.message)}</span></div>`);
    list.innerHTML = `${insights.join("")}${reqs.length ? `<div class="grid gap-2">${reqs.join("")}</div>` : ""}
      ${!insights.length && !reqs.length ? `<div class="empty-state"><h4>${t("ins.none")}</h4></div>` : ""}
      <p class="caption">${escapeHtml(data.generated_from)}</p>`;

    // Cycle length chart (simple bars from the user's own data)
    const chart = document.getElementById("ins-chart");
    if (chart) {
      const lens = s.cycle_lengths_days || [];
      if (lens.length < 2) { chart.innerHTML = `<p class="caption">${t("ins.chart_needs", { n: 3 })}</p>`; }
      else {
        const max = Math.max(...lens, 35), min = Math.min(...lens, 21);
        const periods = C.sortPeriods(AppState.data.periods);
        chart.innerHTML = `<div class="flex items-end gap-2 h-36">${lens.map((n, i) => {
          const h = 20 + ((n - min) / Math.max(max - min, 1)) * 80;
          const label = periods[i + 1] ? D.formatISODate(periods[i + 1].start_date, AppState.lang, { month: "short" }) : "";
          const tone = n < 21 || n > 35 ? "var(--peach-deep)" : "var(--rose)";
          return `<div class="flex-1 flex flex-col items-center gap-1 min-w-0"><span class="caption font-semibold">${n}</span><div class="w-full rounded-t-lg" style="height:${h}%;background:${tone}"></div><span class="caption truncate">${label}</span></div>`;
        }).join("")}</div><p class="caption mt-2">${t("ins.chart_caption")}</p>`;
      }
    }
  }

  // ---- Export ------------------------------------------------------------------------------------------
  function csvCell(v) { const s = String(v == null ? "" : v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }
  function exportCSV() {
    const periods = C.sortPeriods(AppState.data.periods);
    const symptoms = [...AppState.data.symptoms].sort((a, b) => D.compareISO(a.record_date, b.record_date));
    if (!periods.length && !symptoms.length) { showToast(t("export.nothing"), "info"); return; }
    const lines = ["type,date,end_date,flow,symptom,severity,notes,created_at"];
    for (const p of periods) lines.push(["period", p.start_date, p.end_date || "", p.flow || "", "", "", p.notes || "", p.created_at].map(csvCell).join(","));
    for (const s of symptoms) lines.push(["symptom", s.record_date, "", "", s.symptom, s.severity ?? "", s.notes || "", s.created_at].map(csvCell).join(","));
    const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `sakhisahay-records-${D.todayISO()}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    showToast(t("export.done", { n: periods.length + symptoms.length }), "success");
  }

  async function deleteAllData() {
    const ok = await confirmDialog({ title: t("priv.delete_all_title"), message: t("priv.delete_all_msg"), confirmLabel: t("priv.delete_all_confirm"), danger: true });
    if (!ok) return;
    try {
      const res = await api.tracker.deleteAll();
      await window.SakhiData.refreshAll();
      showToast(t("priv.delete_all_done", { p: res.periods_deleted, s: res.symptoms_deleted }), "info", 5000);
    } catch (err) {
      showToast(err.message, "error", 5000);
    }
  }

  // ---- Doctor Connect (demo directory, from the API) -------------------------------------------------------
  let doctorsLoaded = false;
  async function renderDoctors() {
    const host = document.getElementById("doctors-list");
    const notice = document.getElementById("doctors-notice");
    if (!host || doctorsLoaded) return;
    host.innerHTML = Array.from({ length: 3 }, () => `<div class="card card-pad"><div class="skeleton h-12 w-12 rounded-full mb-3"></div><div class="skeleton h-4 w-32 mb-2"></div><div class="skeleton h-3 w-48"></div></div>`).join("");
    try {
      const data = await api.doctors();
      doctorsLoaded = true;
      if (notice) notice.textContent = data.notice;
      const tones = ["bubble-blush", "bubble-lavender", "bubble-sage"];
      host.innerHTML = data.doctors.map((d, i) => `
        <article class="card card-pad flex flex-col gap-3">
          <div class="flex items-center gap-3">
            <span class="icon-bubble icon-bubble-lg ${tones[i % 3]}"><span class="material-symbols-outlined">person</span></span>
            <div><h3 class="h3">${escapeHtml(d.display_name)}</h3><div class="caption">${escapeHtml(d.specialty)} · ${escapeHtml(d.city)}</div></div>
            ${d.is_demo ? `<span class="badge badge-neutral ml-auto">${t("doc.demo_badge")}</span>` : ""}
          </div>
          <div class="flex flex-wrap gap-1.5">${d.focus_areas.map((f) => `<span class="badge badge-blush">${escapeHtml(f)}</span>`).join("")}</div>
          <div class="caption"><strong>${t("doc.languages")}:</strong> ${d.languages.map(escapeHtml).join(", ")}<br/><strong>${t("doc.consult_types")}:</strong> ${d.consultation_types.map(escapeHtml).join(", ")}</div>
          <button type="button" class="btn btn-soft btn-sm self-start" disabled title="${t("doc.booking_soon")}"><span class="material-symbols-outlined">event</span>${t("doc.booking_soon")}</button>
        </article>`).join("");
    } catch (err) {
      host.innerHTML = `<div class="notice notice-error sm:col-span-3"><span class="material-symbols-outlined">error</span><span>${escapeHtml(err.message)}</span></div>`;
    }
  }

  // ---- Settings ----------------------------------------------------------------------------------------------
  function fillSettings() {
    const p = AppState.data.profile;
    if (!p) return;
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v == null ? "" : v; };
    set("setting-name", p.display_name);
    set("setting-age", p.age);
    set("setting-cycle", p.cycle_length_days);
    set("setting-period", p.period_length_days);
    document.getElementById("setting-cycle-val").textContent = t("common.n_days", { n: p.cycle_length_days });
    document.getElementById("setting-period-val").textContent = t("common.n_days", { n: p.period_length_days });
    document.querySelectorAll("[data-lang-select]").forEach((el) => { el.value = AppState.lang; });
  }

  async function saveSettings() {
    const name = document.getElementById("setting-name").value.replace(/\s+/g, " ").trim();
    const ageRaw = document.getElementById("setting-age").value.trim();
    const cycle = Number(document.getElementById("setting-cycle").value);
    const period = Number(document.getElementById("setting-period").value);
    const err = document.getElementById("settings-error");
    err.hidden = true;
    if (name.length < 1) { err.hidden = false; err.lastElementChild.textContent = t("ob.name_error"); return; }
    if (ageRaw && (!Number.isInteger(Number(ageRaw)) || Number(ageRaw) < 10 || Number(ageRaw) > 80)) { err.hidden = false; err.lastElementChild.textContent = t("ob.age_error"); return; }
    const btn = document.getElementById("btn-save-settings");
    btn.classList.add("is-loading"); btn.insertAdjacentHTML("beforeend", '<span class="spinner"></span>');
    try {
      const p = await api.profile.update({ display_name: name, age: ageRaw ? Number(ageRaw) : null, cycle_length_days: cycle, period_length_days: period, preferred_language: AppState.lang });
      AppState.data.profile = p;
      renderHeader();
      document.dispatchEvent(new CustomEvent("sakhi:data"));
      showToast(t("set.saved"), "success");
    } catch (e) {
      err.hidden = false; err.lastElementChild.textContent = e.message;
    } finally {
      btn.classList.remove("is-loading"); btn.querySelector(".spinner")?.remove();
    }
  }

  async function redoOnboarding() {
    const ok = await confirmDialog({ title: t("set.redo_title"), message: t("set.redo_msg"), confirmLabel: t("set.redo_confirm") });
    if (!ok) return;
    try {
      await api.profile.update({ onboarding_completed: false });
      localStorage.removeItem("sakhisahay_onboarding_draft");
      location.hash = "overview";
      location.reload();
    } catch (e) { showToast(e.message, "error"); }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-export-csv]").forEach((b) => b.addEventListener("click", exportCSV));
    document.getElementById("btn-delete-all")?.addEventListener("click", deleteAllData);
    document.getElementById("btn-save-settings")?.addEventListener("click", saveSettings);
    document.getElementById("btn-redo-onboarding")?.addEventListener("click", redoOnboarding);
    document.getElementById("setting-cycle")?.addEventListener("input", (e) => { document.getElementById("setting-cycle-val").textContent = t("common.n_days", { n: e.target.value }); });
    document.getElementById("setting-period")?.addEventListener("input", (e) => { document.getElementById("setting-period-val").textContent = t("common.n_days", { n: e.target.value }); });
    document.getElementById("btn-open-article")?.addEventListener("click", () => openModal("article-modal"));
  });
  document.addEventListener("sakhi:insights", renderInsights);
  document.addEventListener("sakhi:data", () => { fillSettings(); });
  document.addEventListener("sakhi:lang", () => { renderInsights(); fillSettings(); doctorsLoaded = false; if (AppState.currentRoute === "doctor-connect") renderDoctors(); });
  document.addEventListener("sakhi:route", (e) => {
    if (e.detail.route === "doctor-connect") renderDoctors();
    if (e.detail.route === "settings") fillSettings();
    if (e.detail.route === "health-insights") renderInsights();
  });

  window.SakhiPages = { renderInsights, renderDoctors, exportCSV, fillSettings };
})();
