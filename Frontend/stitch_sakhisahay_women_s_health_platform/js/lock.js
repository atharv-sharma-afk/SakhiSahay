/* ==========================================================================
   App lock (Touch ID / Face ID / Windows Hello) via WebAuthn.

   What this does and does not do, honestly:
   - A web page cannot call Touch ID directly. It can ask the browser for a
     *platform authenticator* credential; the OS then shows its own Face ID /
     Touch ID prompt and returns a signature. The server verifies that
     signature and only then hands out an unlock token (see backend).
   - Locked state is enforced server-side: without the token every health
     route answers 423. The blur + overlay here is presentation, not security.
   - Requires a secure context (https:// or localhost) and a device with an
     enrolled biometric / screen lock. Otherwise the toggle reports
     "unavailable" instead of pretending.
   ========================================================================== */
(function () {
  const api = window.SakhiApi;

  const LockState = {
    status: null, // from /api/auth/biometric/status
    hiddenAt: null,
    pendingUnlock: null, // Promise while the lock screen is up
    resolveUnlock: null,
    armed: false,
  };

  // ---- base64url <-> ArrayBuffer -------------------------------------------------
  function b64urlToBuf(s) {
    const pad = "=".repeat((4 - (s.length % 4)) % 4);
    const bin = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    return buf.buffer;
  }
  function bufToB64url(buf) {
    const bytes = new Uint8Array(buf);
    let bin = "";
    for (const b of bytes) bin += String.fromCharCode(b);
    return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
  function creationOptionsFromJSON(json) {
    if (window.PublicKeyCredential && typeof PublicKeyCredential.parseCreationOptionsFromJSON === "function") {
      return PublicKeyCredential.parseCreationOptionsFromJSON(json);
    }
    return {
      ...json,
      challenge: b64urlToBuf(json.challenge),
      user: { ...json.user, id: b64urlToBuf(json.user.id) },
      excludeCredentials: (json.excludeCredentials || []).map((c) => ({ ...c, id: b64urlToBuf(c.id) })),
    };
  }
  function requestOptionsFromJSON(json) {
    if (window.PublicKeyCredential && typeof PublicKeyCredential.parseRequestOptionsFromJSON === "function") {
      return PublicKeyCredential.parseRequestOptionsFromJSON(json);
    }
    return {
      ...json,
      challenge: b64urlToBuf(json.challenge),
      allowCredentials: (json.allowCredentials || []).map((c) => ({ ...c, id: b64urlToBuf(c.id) })),
    };
  }
  function credentialToJSON(cred) {
    if (typeof cred.toJSON === "function") return cred.toJSON();
    const r = cred.response;
    const out = {
      id: cred.id,
      rawId: bufToB64url(cred.rawId),
      type: cred.type,
      authenticatorAttachment: cred.authenticatorAttachment || null,
      clientExtensionResults: cred.getClientExtensionResults ? cred.getClientExtensionResults() : {},
      response: { clientDataJSON: bufToB64url(r.clientDataJSON) },
    };
    if (r.attestationObject) {
      out.response.attestationObject = bufToB64url(r.attestationObject);
      if (typeof r.getTransports === "function") out.response.transports = r.getTransports();
    }
    if (r.authenticatorData) {
      out.response.authenticatorData = bufToB64url(r.authenticatorData);
      out.response.signature = bufToB64url(r.signature);
      out.response.userHandle = r.userHandle ? bufToB64url(r.userHandle) : null;
    }
    return out;
  }

  // ---- capability ---------------------------------------------------------------------
  async function capability() {
    if (!window.isSecureContext) return { ok: false, reason: "insecure" };
    if (!window.PublicKeyCredential) return { ok: false, reason: "unsupported" };
    try {
      const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
      return available ? { ok: true } : { ok: false, reason: "no_authenticator" };
    } catch {
      return { ok: false, reason: "unsupported" };
    }
  }

  function explainWebAuthnError(err) {
    const name = err && err.name;
    if (name === "NotAllowedError") return t("lock.err_cancelled");
    if (name === "InvalidStateError") return t("lock.err_already");
    if (name === "SecurityError") return t("lock.err_security");
    if (name === "NotSupportedError") return t("lock.err_unsupported");
    if (name === "AbortError") return t("lock.err_cancelled");
    if (err instanceof api.ApiError) return err.message;
    return (err && err.message) || t("lock.err_generic");
  }

  // ---- server round trips -----------------------------------------------------------------
  async function authenticateOnce() {
    const options = await api.lock.authOptions();
    const cred = await navigator.credentials.get({ publicKey: requestOptionsFromJSON(options) });
    const result = await api.lock.authVerify(credentialToJSON(cred));
    api.setUnlockToken(result.unlock_token);
    return result;
  }

  async function registerOnce() {
    const options = await api.lock.registerOptions();
    const cred = await navigator.credentials.create({ publicKey: creationOptionsFromJSON(options) });
    const label = `${navigator.platform || "device"} · ${new Date().toLocaleDateString()}`;
    const result = await api.lock.registerVerify(credentialToJSON(cred), label);
    api.setUnlockToken(result.unlock_token);
    return result;
  }

  async function refreshStatus() {
    try {
      LockState.status = await api.lock.status();
    } catch (err) {
      LockState.status = null;
    }
    AppState.data.lockStatus = LockState.status;
    renderPrivacyCard();
    return LockState.status;
  }

  // ---- lock screen ---------------------------------------------------------------------------
  function setLockedUI(locked) {
    AppState.locked = locked;
    const root = document.getElementById("app-root");
    const screen = document.getElementById("lock-screen");
    if (root) {
      root.classList.toggle("is-locked", locked);
      if (locked) root.setAttribute("inert", ""); else root.removeAttribute("inert");
      root.setAttribute("aria-hidden", locked ? "true" : "false");
    }
    if (screen) screen.hidden = !locked;
    document.querySelectorAll(".modal-backdrop").forEach((m) => { if (locked) m.hidden = true; });
    if (locked) document.title = "SakhiSahay"; // no health info in the tab title while locked
  }

  function setLockMessage(msg, kind) {
    const el = document.getElementById("lock-message");
    if (!el) return;
    el.textContent = msg || "";
    el.className = `body-sm ${kind === "error" ? "text-[var(--danger)]" : "muted"}`;
  }

  /**
   * Show the lock screen and resolve only after a verified unlock.
   * Multiple callers share one pending promise.
   */
  function requireUnlock() {
    if (LockState.pendingUnlock) return LockState.pendingUnlock;
    setLockedUI(true);
    LockState.pendingUnlock = new Promise((resolve) => { LockState.resolveUnlock = resolve; });
    attemptUnlock();
    return LockState.pendingUnlock;
  }

  async function attemptUnlock() {
    const btn = document.getElementById("lock-unlock-btn");
    const cap = await capability();
    if (!cap.ok) {
      setLockMessage(t(`lock.cap_${cap.reason}`), "error");
      if (btn) btn.disabled = false;
      return;
    }
    if (btn) { btn.disabled = true; btn.classList.add("is-loading"); }
    setLockMessage(t("lock.prompting"));
    try {
      await authenticateOnce();
      setLockMessage("");
      finishUnlock();
    } catch (err) {
      setLockMessage(explainWebAuthnError(err), "error");
    } finally {
      if (btn) { btn.disabled = false; btn.classList.remove("is-loading"); }
    }
  }

  function finishUnlock() {
    setLockedUI(false);
    const resolve = LockState.resolveUnlock;
    LockState.pendingUnlock = null;
    LockState.resolveUnlock = null;
    if (resolve) resolve(true);
    document.dispatchEvent(new CustomEvent("sakhi:unlocked"));
  }

  /** Lock now: drop the token locally and server-side, then demand re-auth. */
  async function lock({ silent = false } = {}) {
    if (!LockState.status || !LockState.status.enabled) return;
    if (AppState.locked) return;
    api.lock.lockNow().catch(() => {});
    api.setUnlockToken(null);
    if (!silent) showToast(t("lock.locked_toast"), "info", 1800);
    await requireUnlock();
    // Data may have changed on another device while locked; refresh quietly.
    if (window.SakhiData && AppState.booted) window.SakhiData.refreshAll().catch(() => {});
  }

  // ---- lifecycle policy ----------------------------------------------------------------------
  function armLifecycle() {
    if (LockState.armed) return;
    LockState.armed = true;
    document.addEventListener("visibilitychange", () => {
      if (!LockState.status || !LockState.status.enabled) return;
      if (document.visibilityState === "hidden") {
        LockState.hiddenAt = Date.now();
      } else if (LockState.hiddenAt) {
        const elapsed = (Date.now() - LockState.hiddenAt) / 1000;
        LockState.hiddenAt = null;
        if (elapsed >= (LockState.status.lock_timeout_seconds || 0)) lock({ silent: true });
      }
    });
    // Leaving the page: the in-memory token dies with it, so a reload re-locks.
    window.addEventListener("pagehide", () => { if (LockState.status && LockState.status.enabled) api.setUnlockToken(null); });
    api.onLocked(() => lock({ silent: true }));
  }

  // ---- Privacy Safeguards card ----------------------------------------------------------------
  const TIMEOUTS = [0, 60, 300, 900];

  async function renderPrivacyCard() {
    const host = document.getElementById("privacy-lock-card");
    if (!host) return;
    const s = LockState.status || AppState.data.lockStatus;
    const cap = await capability();
    const enabled = !!(s && s.enabled);
    const available = cap.ok;
    const busy = host.dataset.busy === "1";

    let stateText;
    if (enabled) stateText = t("lock.state_on", { n: s.credential_count });
    else if (available) stateText = t("lock.state_off");
    else stateText = t(`lock.cap_${cap.reason}`);

    host.innerHTML = `
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-start gap-3 min-w-0">
          <span class="icon-bubble ${enabled ? "bubble-rose" : "bubble-blush"}"><span class="material-symbols-outlined">fingerprint</span></span>
          <div class="min-w-0">
            <div class="font-semibold">${t("lock.title")}</div>
            <p class="body-sm muted mt-0.5">${t("lock.desc")}</p>
            <p class="caption mt-2 ${enabled ? "text-[var(--sage-deep)]" : available ? "" : "text-[var(--warning)]"}" id="lock-state-text">${stateText}</p>
          </div>
        </div>
        <button type="button" class="toggle ${busy ? "is-busy" : ""}" id="lock-toggle" role="switch" aria-checked="${enabled}" aria-label="${t("lock.title")}" ${!available && !enabled ? "disabled" : ""} ${busy ? "disabled" : ""}></button>
      </div>
      <div class="mt-4 grid gap-3 ${enabled ? "" : "opacity-60"}">
        <label class="card-row">
          <span class="body-sm font-medium">${t("lock.timeout_label")}</span>
          <select class="select input-sm w-auto min-w-[11rem]" id="lock-timeout" ${enabled ? "" : "disabled"}>
            ${TIMEOUTS.map((sec) => `<option value="${sec}" ${s && s.lock_timeout_seconds === sec ? "selected" : ""}>${t(`lock.timeout_${sec}`)}</option>`).join("")}
          </select>
        </label>
        ${enabled ? `<button type="button" class="btn btn-soft btn-sm self-start" id="lock-now-btn"><span class="material-symbols-outlined">lock</span>${t("lock.lock_now")}</button>` : ""}
      </div>
      <p class="caption mt-3" id="lock-error" role="alert"></p>
      <details class="mt-2">
        <summary class="caption cursor-pointer select-none">${t("lock.how_summary")}</summary>
        <ul class="caption mt-2 list-disc pl-4 space-y-1">
          <li>${t("lock.how_1")}</li><li>${t("lock.how_2")}</li><li>${t("lock.how_3")}</li><li>${t("lock.how_4")}</li>
        </ul>
      </details>`;

    host.querySelector("#lock-toggle")?.addEventListener("click", () => (enabled ? disable() : enable()));
    host.querySelector("#lock-timeout")?.addEventListener("change", async (e) => {
      const value = Number(e.target.value);
      try {
        const p = await api.profile.update({ lock_timeout_seconds: value });
        AppState.data.profile = p;
        if (LockState.status) LockState.status.lock_timeout_seconds = value;
        showToast(t("lock.timeout_saved"), "success");
      } catch (err) {
        showToast(err.message, "error");
      }
    });
    host.querySelector("#lock-now-btn")?.addEventListener("click", () => lock());
  }

  function setCardBusy(busy, message) {
    const host = document.getElementById("privacy-lock-card");
    if (!host) return;
    host.dataset.busy = busy ? "1" : "0";
    const toggle = host.querySelector("#lock-toggle");
    if (toggle) { toggle.disabled = busy; toggle.classList.toggle("is-busy", busy); }
    const state = host.querySelector("#lock-state-text");
    if (state && message) state.textContent = message;
    const err = host.querySelector("#lock-error");
    if (err && busy) err.textContent = "";
  }
  function setCardError(message) {
    const err = document.querySelector("#privacy-lock-card #lock-error");
    if (err) { err.textContent = message; err.className = "caption mt-3 text-[var(--danger)]"; }
  }

  async function enable() {
    const cap = await capability();
    if (!cap.ok) { setCardError(t(`lock.cap_${cap.reason}`)); return; }
    setCardBusy(true, t("lock.prompting"));
    try {
      await registerOnce();
      await refreshStatus();
      showToast(t("lock.enabled_toast"), "success");
    } catch (err) {
      setCardBusy(false);
      await renderPrivacyCard();
      setCardError(explainWebAuthnError(err));
    }
  }

  async function disable() {
    const ok = await confirmDialog({ title: t("lock.disable_title"), message: t("lock.disable_msg"), confirmLabel: t("lock.disable_confirm"), danger: true });
    if (!ok) return;
    setCardBusy(true, t("lock.prompting"));
    try {
      // Turning the lock off requires a fresh device verification, every time.
      await authenticateOnce();
      await api.lock.disable();
      api.setUnlockToken(null);
      await refreshStatus();
      showToast(t("lock.disabled_toast"), "info");
    } catch (err) {
      setCardBusy(false);
      await renderPrivacyCard();
      setCardError(explainWebAuthnError(err));
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("lock-unlock-btn")?.addEventListener("click", attemptUnlock);
  });
  document.addEventListener("sakhi:route", (e) => { if (e.detail.route === "health-history-privacy") refreshStatus(); });
  document.addEventListener("sakhi:lang", () => renderPrivacyCard());
  document.addEventListener("sakhi:booted", () => { LockState.status = AppState.data.lockStatus; renderPrivacyCard(); });

  window.SakhiLock = { requireUnlock, lock, armLifecycle, capability, refreshStatus, renderPrivacyCard };
})();
