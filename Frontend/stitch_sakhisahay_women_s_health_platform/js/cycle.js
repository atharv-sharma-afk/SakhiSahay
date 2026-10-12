/* ==========================================================================
   Cycle maths - pure functions over the user's own records.

   Everything here is an *estimate* derived from logged period start dates and
   the baseline the user gave during onboarding. Nothing is a diagnosis. The
   ovulation / fertile-window rule is the common textbook approximation
   (ovulation ~14 days before the next period; fertile window = 5 days before
   ovulation through 1 day after) and is labelled as an estimate in the UI.
   ========================================================================== */
(function (root, factory) {
  const deps = typeof module !== "undefined" && module.exports ? require("./dates.js") : root.SakhiDates;
  const api = factory(deps);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.SakhiCycle = api;
})(typeof window !== "undefined" ? window : globalThis, function (D) {
  const LUTEAL_DAYS = 14;
  const MIN_PLAUSIBLE_CYCLE = 15;
  const MAX_PLAUSIBLE_CYCLE = 60;

  function median(nums) {
    if (!nums.length) return null;
    const s = [...nums].sort((a, b) => a - b);
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  }

  /** Sort periods oldest -> newest by start_date. */
  function sortPeriods(periods) {
    return [...(periods || [])].sort((a, b) => D.compareISO(a.start_date, b.start_date));
  }

  /** Days between consecutive logged starts, ignoring implausible gaps. */
  function cycleLengths(periods) {
    const sorted = sortPeriods(periods);
    const out = [];
    for (let i = 1; i < sorted.length; i++) {
      const len = D.diffDays(sorted[i - 1].start_date, sorted[i].start_date);
      if (len >= MIN_PLAUSIBLE_CYCLE && len <= MAX_PLAUSIBLE_CYCLE) out.push(len);
    }
    return out;
  }

  function periodDurations(periods) {
    return (periods || [])
      .filter((p) => p.end_date)
      .map((p) => D.diffDays(p.start_date, p.end_date) + 1)
      .filter((n) => n >= 1 && n <= 31);
  }

  /**
   * Choose the cycle/period lengths to use for estimates.
   * With >= 2 completed cycles the user's own median wins; otherwise the
   * onboarding baseline. `source` tells the UI which one is in use.
   */
  function effectiveLengths(periods, profile) {
    const lens = cycleLengths(periods);
    const durs = periodDurations(periods);
    const baselineCycle = (profile && profile.cycle_length_days) || 28;
    const baselinePeriod = (profile && profile.period_length_days) || 5;
    const cycle = lens.length >= 2 ? Math.round(median(lens)) : baselineCycle;
    const period = durs.length >= 2 ? Math.round(median(durs)) : baselinePeriod;
    return {
      cycleLength: cycle,
      periodLength: period,
      cycleSource: lens.length >= 2 ? "logged" : "baseline",
      periodSource: durs.length >= 2 ? "logged" : "baseline",
      loggedCycles: lens.length,
      cycleLengths: lens,
      periodDurations: durs,
    };
  }

  /** The most recent period that started on/before `today`. */
  function lastPeriodOnOrBefore(periods, todayIso) {
    const sorted = sortPeriods(periods).filter((p) => p.start_date <= todayIso);
    return sorted.length ? sorted[sorted.length - 1] : null;
  }

  /** Find the logged period covering a date (open periods cover start day only... plus ongoing until today). */
  function periodCovering(periods, iso, todayIso) {
    for (const p of periods || []) {
      const end = p.end_date || (p.start_date <= todayIso ? todayIso : p.start_date);
      if (iso >= p.start_date && iso <= end) return p;
    }
    return null;
  }

  /**
   * Windows for one estimated cycle starting at `startIso`.
   * Returns ISO ranges for period, fertile window and ovulation day.
   */
  function cycleWindows(startIso, cycleLength, periodLength) {
    const nextStart = D.addDays(startIso, cycleLength);
    const ovulation = D.addDays(nextStart, -LUTEAL_DAYS);
    return {
      start: startIso,
      nextStart,
      periodEnd: D.addDays(startIso, Math.max(periodLength, 1) - 1),
      fertileStart: D.addDays(ovulation, -5),
      fertileEnd: D.addDays(ovulation, 1),
      ovulation,
    };
  }

  /**
   * Phase for a given cycle day. Returns a key the UI translates.
   * menstrual | follicular | fertile | ovulation | luteal | late
   */
  function phaseForDay(cycleDay, cycleLength, periodLength) {
    if (cycleDay == null) return null;
    const ovDay = cycleLength - LUTEAL_DAYS; // 1-indexed day of ovulation
    if (cycleDay > cycleLength) return "late";
    if (cycleDay <= periodLength) return "menstrual";
    if (cycleDay === ovDay) return "ovulation";
    if (cycleDay >= ovDay - 5 && cycleDay <= ovDay + 1) return "fertile";
    if (cycleDay < ovDay) return "follicular";
    return "luteal";
  }

  /**
   * Everything the dashboard/tracker need about "now".
   */
  function currentStatus(periods, profile, todayIso) {
    const lengths = effectiveLengths(periods, profile);
    const last = lastPeriodOnOrBefore(periods, todayIso);
    if (!last) {
      return { hasData: false, ...lengths };
    }
    const cycleDay = D.diffDays(last.start_date, todayIso) + 1;
    const covering = periodCovering(periods, todayIso, todayIso);
    const windows = cycleWindows(last.start_date, lengths.cycleLength, lengths.periodLength);
    let phase = phaseForDay(cycleDay, lengths.cycleLength, lengths.periodLength);
    if (covering) phase = "menstrual"; // a logged flow day is always menstrual, whatever the maths says
    const daysToNext = D.diffDays(todayIso, windows.nextStart);
    return {
      hasData: true,
      ...lengths,
      lastPeriod: last,
      lastStart: last.start_date,
      cycleDay,
      phase,
      onPeriod: !!covering,
      nextPeriodStart: windows.nextStart,
      daysToNextPeriod: daysToNext,
      lateByDays: daysToNext < 0 ? -daysToNext : 0,
      fertileStart: windows.fertileStart,
      fertileEnd: windows.fertileEnd,
      ovulation: windows.ovulation,
      progress: Math.min(cycleDay / lengths.cycleLength, 1),
    };
  }

  /**
   * Build a lookup of estimated markers for calendar rendering.
   * Only future days get "predicted period" marks; the fertile window is shown
   * for the current cycle and the next `cyclesAhead` cycles.
   */
  function estimateMarkers(periods, profile, todayIso, cyclesAhead) {
    const marks = new Map(); // iso -> "predicted" | "fertile" | "ovulation"
    const status = currentStatus(periods, profile, todayIso);
    if (!status.hasData) return { marks, status };
    const ahead = cyclesAhead == null ? 3 : cyclesAhead;
    let start = status.lastStart;
    for (let c = 0; c <= ahead; c++) {
      const w = cycleWindows(start, status.cycleLength, status.periodLength);
      // fertile window
      for (let iso = w.fertileStart; iso <= w.fertileEnd; iso = D.addDays(iso, 1)) {
        marks.set(iso, iso === w.ovulation ? "ovulation" : "fertile");
      }
      // next predicted period (only days after today)
      const pw = cycleWindows(w.nextStart, status.cycleLength, status.periodLength);
      for (let iso = w.nextStart; iso <= pw.periodEnd; iso = D.addDays(iso, 1)) {
        if (iso > todayIso) marks.set(iso, "predicted");
      }
      start = w.nextStart;
    }
    return { marks, status };
  }

  /** Cycle day for an arbitrary date given the logged periods. */
  function cycleDayFor(periods, iso) {
    const last = lastPeriodOnOrBefore(periods, iso);
    if (!last) return null;
    return D.diffDays(last.start_date, iso) + 1;
  }

  return {
    LUTEAL_DAYS, median, sortPeriods, cycleLengths, periodDurations, effectiveLengths,
    lastPeriodOnOrBefore, periodCovering, cycleWindows, phaseForDay, currentStatus, estimateMarkers, cycleDayFor,
  };
});
