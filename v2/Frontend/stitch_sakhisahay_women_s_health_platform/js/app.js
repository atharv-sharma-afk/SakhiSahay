/* ==========================================================================
   App core: state, i18n helper, routing, toasts, modals, boot sequence.
   Feature modules (tracker, dashboard, onboarding, lock, chat, pages) attach
   themselves to window.Sakhi* and are orchestrated from boot() below.
   ========================================================================== */
(function () {
  const D = window.SakhiDates;
  const api = window.SakhiApi;

  const ROUTES = ["overview", "ai-health-assistant", "period-symptom-tracker", "health-insights", "doctor-connect", "health-history-privacy", "settings"];
  const LANG_KEY = "sakhisahay_lang";

  const AppState = {
    lang: localStorage.getItem(LANG_KEY) || "en",
    currentRoute: "overview",
    locked: false,
    booted: false,
    data: { profile: null, periods: [], symptoms: [], catalogue: [], insights: null, lockStatus: null },
  };
  window.AppState = AppState;

  // ---- i18n ---------------------------------------------------------------
  function t(key, vars) {
    const dict = (window.I18N_DICTIONARY && window.I18N_DICTIONARY[AppState.lang]) || {};
    const en = (window.I18N_DICTIONARY && window.I18N_DICTIONARY.en) || {};
    let s = dict[key] != null ? dict[key] : en[key] != null ? en[key] : key;
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  }
  window.t = t;

  function applyLanguage(lang, { persistRemote = true, announce = false } = {}) {
    if (!["en", "hi", "hinglish"].includes(lang)) lang = "en";
    AppState.lang = lang;
    localStorage.setItem(LANG_KEY, lang);
    if (typeof window.applyLanguageToUI === "function") window.applyLanguageToUI(lang);
    document.querySelectorAll("[data-lang-select]").forEach((el) => { el.value = lang; });
    document.querySelectorAll("[data-lang-pill]").forEach((el) => el.classList.toggle("is-on", el.getAttribute("data-lang-pill") === lang));
    document.dispatchEvent(new CustomEvent("sakhi:lang", { detail: { lang } }));
    renderHeader();
    if (announce) showToast(t("toast.language_switched", { lang: t(`lang.${lang}`) }), "info");
    if (persistRemote && AppState.data.profile && AppState.data.profile.preferred_language !== lang && !AppState.locked) {
      api.profile.update({ preferred_language: lang }).then((p) => { AppState.data.profile = p; }).catch(() => {});
    }
  }
  window.applyLanguage = applyLanguage;

  // ---- toasts -----------------------------------------------------------------
  function showToast(message, kind = "success", ms = 3200) {
    const stack = document.getElementById("toast-stack");
    if (!stack) return;
    const icons = { success: "check_circle", error: "error", info: "info" };
    const el = document.createElement("div");
    el.className = `toast toast-${kind}`;
    el.setAttribute("role", kind === "error" ? "alert" : "status");
    el.innerHTML = `<span class="material-symbols-outlined" aria-hidden="true">${icons[kind] || "info"}</span><span></span>`;
    el.lastElementChild.textContent = message;
    stack.appendChild(el);
    while (stack.children.length > 3) stack.firstElementChild.remove();
    setTimeout(() => { el.classList.add("is-leaving"); setTimeout(() => el.remove(), 220); }, ms);
  }
  window.showToast = showToast;

  // ---- modals -----------------------------------------------------------------
  function openModal(id) {
    const m = document.getElementById(id);
    if (!m) return;
    m.hidden = false;
    document.body.style.overflow = "hidden";
    const focusable = m.querySelector("[autofocus], input, select, textarea, button");
    if (focusable) setTimeout(() => focusable.focus(), 30);
  }
  function closeModal(id) {
    const m = document.getElementById(id);
    if (!m) return;
    m.hidden = true;
    if (!document.querySelector(".modal-backdrop:not([hidden])")) document.body.style.overflow = "";
  }
  window.openModal = openModal;
  window.closeModal = closeModal;
  document.addEventListener("click", (e) => {
    const closer = e.target.closest("[data-close-modal]");
    if (closer) { closeModal(closer.getAttribute("data-close-modal")); return; }
    if (e.target.classList && e.target.classList.contains("modal-backdrop") && e.target.dataset.dismissible !== "false") {
      closeModal(e.target.id);
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      const open = document.querySelector(".modal-backdrop:not([hidden])");
      if (open && open.dataset.dismissible !== "false") closeModal(open.id);
    }
  });

  /** Promise-based confirm dialog. */
  function confirmDialog({ title, message, confirmLabel, danger = false }) {
    return new Promise((resolve) => {
      const m = document.getElementById("confirm-modal");
      m.querySelector("[data-confirm-title]").textContent = title;
      m.querySelector("[data-confirm-message]").textContent = message;
      const ok = m.querySelector("[data-confirm-ok]");
      const cancel = m.querySelector("[data-confirm-cancel]");
      ok.textContent = confirmLabel || t("common.confirm");
      ok.className = `btn ${danger ? "btn-danger" : "btn-primary"}`;
      const done = (v) => { ok.onclick = null; cancel.onclick = null; closeModal("confirm-modal"); resolve(v); };
      ok.onclick = () => done(true);
      cancel.onclick = () => done(false);
      openModal("confirm-modal");
    });
  }
  window.confirmDialog = confirmDialog;

  // ---- routing ----------------------------------------------------------------
  function switchRoute(routeName, { replace = false } = {}) {
    if (AppState.locked) return; // no navigation while locked
    if (!ROUTES.includes(routeName)) routeName = "overview";
    const changed = AppState.currentRoute !== routeName;
    AppState.currentRoute = routeName;
    if (window.location.hash.replace("#", "") !== routeName) {
      if (replace) history.replaceState(null, "", `#${routeName}`);
      else window.location.hash = routeName;
    }
    document.querySelectorAll(".view-container").forEach((v) => v.classList.toggle("active", v.id === `view-${routeName}`));
    document.querySelectorAll("[data-path]").forEach((item) => item.classList.toggle("is-active", item.getAttribute("data-path") === routeName));
    if (changed) window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
    document.dispatchEvent(new CustomEvent("sakhi:route", { detail: { route: routeName } }));
  }
  window.switchRoute = switchRoute;
  window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace("#", "") || "overview";
    if (AppState.locked) { history.replaceState(null, "", `#${AppState.currentRoute}`); return; }
    switchRoute(hash, { replace: true });
  });
  document.addEventListener("click", (e) => {
    const link = e.target.closest("[data-route]");
    if (link) { e.preventDefault(); switchRoute(link.getAttribute("data-route")); }
  });

  // ---- header -----------------------------------------------------------------
  function greetingKey() {
    const h = new Date().getHours();
    if (h < 12) return "greeting.morning";
    if (h < 17) return "greeting.afternoon";
    return "greeting.evening";
  }
  function renderHeader() {
    const name = (AppState.data.profile && AppState.data.profile.display_name) || "";
    const greet = `${t(greetingKey())}${name ? `, ${name}` : ""}`;
    document.querySelectorAll("[data-greeting]").forEach((el) => { el.textContent = greet; });
    const today = new Date();
    document.querySelectorAll("[data-today-long]").forEach((el) => {
      el.textContent = today.toLocaleDateString(D.localeFor(AppState.lang), { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    });
    const initials = name ? name.split(/\s+/).map((p) => p[0]).join("").slice(0, 2).toUpperCase() : "S";
    document.querySelectorAll("[data-initials]").forEach((el) => { el.textContent = initials; });
    document.querySelectorAll("[data-display-name]").forEach((el) => { el.textContent = name || t("profile.friend"); });
  }
  window.renderHeader = renderHeader;

  // Keep the date fresh if the tab stays open past midnight.
  let lastDay = D.todayISO();
  setInterval(() => {
    const now = D.todayISO();
    if (now !== lastDay) { lastDay = now; renderHeader(); document.dispatchEvent(new CustomEvent("sakhi:data")); }
  }, 60 * 1000);

  // ---- data -------------------------------------------------------------------
  async function loadRecords() {
    const [periods, symptoms] = await Promise.all([api.tracker.periods(), api.tracker.symptoms()]);
    AppState.data.periods = periods || [];
    AppState.data.symptoms = symptoms || [];
    document.dispatchEvent(new CustomEvent("sakhi:data"));
  }
  async function loadInsights() {
    try {
      AppState.data.insights = await api.insights();
    } catch (err) {
      AppState.data.insights = null;
      if (!(err instanceof api.ApiError) || err.code !== "locked") console.warn("insights unavailable:", err.message);
    }
    document.dispatchEvent(new CustomEvent("sakhi:insights"));
  }
  /** Refresh everything derived from records after a save. */
  async function refreshAll() {
    await loadRecords();
    loadInsights();
  }
  window.SakhiData = { loadRecords, loadInsights, refreshAll };

  // ---- connectivity banner --------------------------------------------------------
  function setOfflineBanner(offline) {
    const banner = document.getElementById("offline-banner");
    if (banner) banner.hidden = !offline;
  }
  api.onAvailabilityChange((available) => setOfflineBanner(!available));

  // ---- boot -------------------------------------------------------------------
  async function boot() {
    applyLanguage(AppState.lang, { persistRemote: false });
    renderHeader();
    document.getElementById("app-loading").hidden = false;

    const base = await api.resolveBase();
    if (api.isAvailable() === false) {
      document.getElementById("app-loading").hidden = true;
      setOfflineBanner(true);
      switchRoute(window.location.hash.replace("#", "") || "overview", { replace: true });
      document.dispatchEvent(new CustomEvent("sakhi:data"));
      return;
    }
    void base;

    // 1. App lock: must be satisfied before any health data is requested.
    try {
      AppState.data.lockStatus = await api.lock.status();
    } catch (err) {
      console.warn("lock status unavailable:", err.message);
    }
    if (AppState.data.lockStatus && AppState.data.lockStatus.enabled && window.SakhiLock) {
      document.getElementById("app-loading").hidden = true;
      await window.SakhiLock.requireUnlock(); // resolves only after a verified unlock
      document.getElementById("app-loading").hidden = false;
    }

    // 2. Profile -> onboarding if needed.
    try {
      AppState.data.profile = await api.profile.get();
    } catch (err) {
      showToast(err.message, "error", 6000);
    }
    if (AppState.data.profile && AppState.data.profile.preferred_language && !localStorage.getItem(LANG_KEY)) {
      applyLanguage(AppState.data.profile.preferred_language, { persistRemote: false });
    }
    renderHeader();
    if (AppState.data.profile && !AppState.data.profile.onboarding_completed_at && window.SakhiOnboarding) {
      document.getElementById("app-loading").hidden = true;
      AppState.data.profile = await window.SakhiOnboarding.run(AppState.data.profile);
      renderHeader();
      document.getElementById("app-loading").hidden = false;
    }

    // 3. Records + reference data.
    try {
      AppState.data.catalogue = await api.tracker.catalogue();
    } catch (err) {
      console.warn("catalogue unavailable:", err.message);
    }
    try {
      await loadRecords();
    } catch (err) {
      showToast(err.message, "error", 6000);
      document.dispatchEvent(new CustomEvent("sakhi:data"));
    }
    loadInsights();

    document.getElementById("app-loading").hidden = true;
    AppState.booted = true;
    if (window.SakhiLock) window.SakhiLock.armLifecycle();
    switchRoute(window.location.hash.replace("#", "") || "overview", { replace: true });
    document.dispatchEvent(new CustomEvent("sakhi:booted"));
  }

  document.addEventListener("DOMContentLoaded", () => {
    // language controls
    document.querySelectorAll("[data-lang-select]").forEach((sel) => sel.addEventListener("change", (e) => applyLanguage(e.target.value, { announce: true })));
    document.querySelectorAll("[data-lang-pill]").forEach((pill) => pill.addEventListener("click", () => applyLanguage(pill.getAttribute("data-lang-pill"), { announce: true })));
    document.getElementById("offline-retry")?.addEventListener("click", async () => {
      const btn = document.getElementById("offline-retry");
      btn.classList.add("is-loading");
      await api.resolveBase(true);
      btn.classList.remove("is-loading");
      if (api.isAvailable()) { setOfflineBanner(false); if (!AppState.booted) boot(); else refreshAll().catch(() => {}); }
      else showToast(t("offline.still"), "error");
    });
    boot();
  });
})();
