/* ==========================================================================
   API client. One place for base-URL discovery, timeouts, JSON handling,
   error normalisation and the app-lock header. Every call either resolves
   with parsed data or rejects with an ApiError - callers never have to guess
   whether a "success" toast is deserved.
   ========================================================================== */
(function () {
  class ApiError extends Error {
    constructor(message, { status = 0, code = "error", errors = [], detail = null } = {}) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.code = code; // network | timeout | locked | validation | conflict | not_found | server | error
      this.errors = errors; // [{field, message}] from 422 responses
      this.detail = detail;
    }
    get isNetwork() { return this.code === "network" || this.code === "timeout"; }
  }

  const state = {
    base: null, // "" (same origin, proxied by server.js) or "http://localhost:8000"
    available: null, // null = unknown, true/false after a probe
    unlockToken: null,
    onLocked: null, // callback when the server answers 423
    onAvailabilityChange: null,
  };

  async function probe(base) {
    try {
      const r = await fetch(`${base}/api/health`, { signal: AbortSignal.timeout(3500), cache: "no-store" });
      return r.ok;
    } catch {
      return false;
    }
  }

  /** Discover the backend once: same-origin proxy first, then direct :8000. */
  async function resolveBase(force) {
    if (!force && state.available === true && state.base !== null) return state.base;
    const candidates = ["", "http://localhost:8000", "http://127.0.0.1:8000"];
    for (const base of candidates) {
      if (await probe(base)) {
        state.base = base;
        setAvailable(true);
        return base;
      }
    }
    state.base = "";
    setAvailable(false);
    return "";
  }

  function setAvailable(value) {
    const changed = state.available !== value;
    state.available = value;
    if (changed && typeof state.onAvailabilityChange === "function") state.onAvailabilityChange(value);
  }

  function setUnlockToken(token) {
    state.unlockToken = token || null;
  }

  function getUnlockToken() {
    return state.unlockToken;
  }

  function friendlyMessage(status, body) {
    if (body && typeof body.detail === "string") return body.detail;
    if (body && body.detail && Array.isArray(body.errors) && body.errors.length) {
      return body.errors.map((e) => (e.field ? `${e.field}: ${e.message}` : e.message)).join(" ");
    }
    if (body && typeof body.error === "string") return body.error;
    if (status === 423) return "SakhiSahay is locked.";
    if (status === 404) return "Not found.";
    if (status === 409) return "This conflicts with an existing record.";
    if (status >= 500) return "The server had a problem. Please try again.";
    return `Request failed (${status}).`;
  }

  function codeFor(status) {
    if (status === 423) return "locked";
    if (status === 422) return "validation";
    if (status === 409) return "conflict";
    if (status === 404) return "not_found";
    if (status === 401) return "unauthorized";
    if (status >= 500) return "server";
    return "error";
  }

  /**
   * request("GET", "/api/tracker/periods") -> data
   * Options: body (object), timeout (ms), headers, raw (return Response)
   */
  async function request(method, path, { body, timeout = 15000, headers = {}, skipLockHandler = false } = {}) {
    if (state.available === null || state.base === null) await resolveBase();
    if (state.available === false) {
      // one more try: the user may have just started the backend
      await resolveBase(true);
      if (state.available === false) {
        throw new ApiError("Cannot reach the SakhiSahay backend. Start it with `python start.py` in the backend folder.", { code: "network" });
      }
    }
    const init = {
      method,
      headers: { Accept: "application/json", ...headers },
      signal: AbortSignal.timeout(timeout),
      cache: "no-store",
    };
    if (state.unlockToken) init.headers["X-Unlock-Token"] = state.unlockToken;
    if (body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(`${state.base}${path}`, init);
    } catch (err) {
      const timedOut = err && (err.name === "TimeoutError" || err.name === "AbortError");
      if (!timedOut) setAvailable(false);
      throw new ApiError(
        timedOut ? "The request took too long. Check your connection and try again." : "Cannot reach the SakhiSahay backend.",
        { code: timedOut ? "timeout" : "network" }
      );
    }
    if (res.status === 204) return null;
    let data = null;
    const text = await res.text();
    if (text) {
      try { data = JSON.parse(text); } catch { data = { detail: text.slice(0, 200) }; }
    }
    if (!res.ok) {
      if (res.status === 423 && !skipLockHandler && typeof state.onLocked === "function") state.onLocked();
      throw new ApiError(friendlyMessage(res.status, data), {
        status: res.status,
        code: codeFor(res.status),
        errors: (data && data.errors) || [],
        detail: data,
      });
    }
    return data;
  }

  const api = {
    ApiError,
    resolveBase,
    isAvailable: () => state.available,
    setUnlockToken,
    getUnlockToken,
    onLocked: (fn) => { state.onLocked = fn; },
    onAvailabilityChange: (fn) => { state.onAvailabilityChange = fn; },
    get: (path, opts) => request("GET", path, opts),
    post: (path, body, opts) => request("POST", path, { ...(opts || {}), body }),
    put: (path, body, opts) => request("PUT", path, { ...(opts || {}), body }),
    del: (path, opts) => request("DELETE", path, opts),

    // ---- typed helpers ---------------------------------------------------
    health: () => request("GET", "/api/health"),
    profile: {
      get: () => request("GET", "/api/profile"),
      update: (patch) => request("PUT", "/api/profile", { body: patch }),
    },
    tracker: {
      summary: () => request("GET", "/api/tracker/summary"),
      catalogue: () => request("GET", "/api/tracker/symptom-catalogue"),
      periods: () => request("GET", "/api/tracker/periods"),
      createPeriod: (data) => request("POST", "/api/tracker/periods", { body: data }),
      updatePeriod: (id, data) => request("PUT", `/api/tracker/periods/${id}`, { body: data }),
      deletePeriod: (id) => request("DELETE", `/api/tracker/periods/${id}`),
      symptoms: (start, end) => {
        const q = new URLSearchParams();
        if (start) q.set("start", start);
        if (end) q.set("end", end);
        const qs = q.toString();
        return request("GET", `/api/tracker/symptoms${qs ? `?${qs}` : ""}`);
      },
      createSymptom: (data) => request("POST", "/api/tracker/symptoms", { body: data }),
      updateSymptom: (id, data) => request("PUT", `/api/tracker/symptoms/${id}`, { body: data }),
      deleteSymptom: (id) => request("DELETE", `/api/tracker/symptoms/${id}`),
      deleteAll: () => request("DELETE", "/api/tracker/all"),
    },
    insights: () => request("GET", "/api/insights"),
    doctors: () => request("GET", "/api/doctors"),
    chat: (question, language) => request("POST", "/api/chat", { body: { question, language }, timeout: 45000 }),
    lock: {
      status: () => request("GET", "/api/auth/biometric/status", { skipLockHandler: true }),
      registerOptions: () => request("POST", "/api/auth/biometric/register/options", { skipLockHandler: true }),
      registerVerify: (credential, label) => request("POST", "/api/auth/biometric/register/verify", { body: { credential, label }, skipLockHandler: true }),
      authOptions: () => request("POST", "/api/auth/biometric/authenticate/options", { skipLockHandler: true }),
      authVerify: (credential) => request("POST", "/api/auth/biometric/authenticate/verify", { body: { credential }, skipLockHandler: true }),
      lockNow: () => request("POST", "/api/auth/biometric/lock", { skipLockHandler: true }),
      disable: () => request("DELETE", "/api/auth/biometric", { skipLockHandler: true }),
    },
  };

  window.SakhiApi = api;
})();
