/* ==========================================================================
   Date utilities.

   Two kinds of values flow through the app and must never be mixed:
   - Calendar dates ("2026-10-12"): what the user means by "today", a period
     start, a symptom day. Represented as plain YYYY-MM-DD strings, built from
     the device's *local* clock. Never passed through Date.toISOString(),
     which would convert to UTC and shift the day near midnight.
   - Instants (created_at "2026-10-12T11:45:00Z"): when something happened.
     Parsed with new Date(iso) and displayed in local time.
   ========================================================================== */
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.SakhiDates = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  const ISO_RE = /^(\d{4})-(\d{2})-(\d{2})$/;
  const pad2 = (n) => String(n).padStart(2, "0");

  /** Local calendar date of a Date object -> "YYYY-MM-DD". */
  function toISODate(d) {
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  }

  /** "YYYY-MM-DD" -> Date at local midnight. Returns null for invalid input. */
  function parseISODate(iso) {
    if (typeof iso !== "string") return null;
    const m = ISO_RE.exec(iso.trim());
    if (!m) return null;
    const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
    const date = new Date(y, mo - 1, d);
    // Reject impossible dates such as 2026-02-30 (which Date would roll over).
    if (date.getFullYear() !== y || date.getMonth() !== mo - 1 || date.getDate() !== d) return null;
    return date;
  }

  function isValidISODate(iso) {
    return parseISODate(iso) !== null;
  }

  function todayISO(now) {
    return toISODate(now || new Date());
  }

  function addDays(iso, n) {
    const d = parseISODate(iso);
    if (!d) return null;
    d.setDate(d.getDate() + n);
    return toISODate(d);
  }

  /** Whole calendar days from a to b (b - a). DST-safe via UTC day numbers. */
  function diffDays(a, b) {
    const da = parseISODate(a), db = parseISODate(b);
    if (!da || !db) return NaN;
    const ua = Date.UTC(da.getFullYear(), da.getMonth(), da.getDate());
    const ub = Date.UTC(db.getFullYear(), db.getMonth(), db.getDate());
    return Math.round((ub - ua) / 86400000);
  }

  function compareISO(a, b) {
    return a < b ? -1 : a > b ? 1 : 0;
  }

  function isBetween(iso, startIso, endIso) {
    return iso >= startIso && iso <= endIso;
  }

  function daysInMonth(year, month0) {
    return new Date(year, month0 + 1, 0).getDate();
  }

  /** Weekday index of the 1st of the month with Monday = 0 ... Sunday = 6. */
  function firstWeekdayMon0(year, month0) {
    return (new Date(year, month0, 1).getDay() + 6) % 7;
  }

  function isLeapYear(year) {
    return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  }

  /** Build the cells of a Monday-first month grid (always full weeks). */
  function monthGrid(year, month0) {
    const lead = firstWeekdayMon0(year, month0);
    const count = daysInMonth(year, month0);
    const cells = [];
    const prevY = month0 === 0 ? year - 1 : year;
    const prevM = month0 === 0 ? 11 : month0 - 1;
    const prevCount = daysInMonth(prevY, prevM);
    for (let i = lead - 1; i >= 0; i--) {
      cells.push({ iso: `${prevY}-${pad2(prevM + 1)}-${pad2(prevCount - i)}`, day: prevCount - i, outside: true });
    }
    for (let d = 1; d <= count; d++) {
      cells.push({ iso: `${year}-${pad2(month0 + 1)}-${pad2(d)}`, day: d, outside: false });
    }
    const nextY = month0 === 11 ? year + 1 : year;
    const nextM = month0 === 11 ? 0 : month0 + 1;
    let trail = (7 - (cells.length % 7)) % 7;
    for (let d = 1; d <= trail; d++) {
      cells.push({ iso: `${nextY}-${pad2(nextM + 1)}-${pad2(d)}`, day: d, outside: true });
    }
    return cells;
  }

  function shiftMonth(year, month0, delta) {
    const total = year * 12 + month0 + delta;
    return { year: Math.floor(total / 12), month0: ((total % 12) + 12) % 12 };
  }

  const LOCALES = { en: "en-IN", hi: "hi-IN", hinglish: "en-IN" };
  function localeFor(lang) {
    return LOCALES[lang] || "en-IN";
  }

  /** Format a calendar date for display, e.g. "Mon, 12 Oct". */
  function formatISODate(iso, lang, options) {
    const d = parseISODate(iso);
    if (!d) return "";
    return d.toLocaleDateString(localeFor(lang), options || { day: "numeric", month: "short", year: "numeric" });
  }

  function formatMonthYear(year, month0, lang) {
    return new Date(year, month0, 1).toLocaleDateString(localeFor(lang), { month: "long", year: "numeric" });
  }

  function weekdayLabels(lang, style) {
    // Monday-first, matching monthGrid.
    const base = new Date(2024, 0, 1); // a Monday
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(base);
      d.setDate(base.getDate() + i);
      return d.toLocaleDateString(localeFor(lang), { weekday: style || "short" });
    });
  }

  /** Format an instant (ISO timestamp with offset) as local time, e.g. "5:12 pm". */
  function formatTime(instant, lang) {
    const d = instant instanceof Date ? instant : new Date(instant);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleTimeString(localeFor(lang), { hour: "numeric", minute: "2-digit" });
  }

  function formatDateTime(instant, lang) {
    const d = instant instanceof Date ? instant : new Date(instant);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleString(localeFor(lang), { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
  }

  /** Human-friendly relative day label for calendar dates. */
  function relativeDayLabel(iso, todayIso, lang) {
    const diff = diffDays(todayIso, iso);
    if (diff === 0) return { key: "date.today" };
    if (diff === -1) return { key: "date.yesterday" };
    if (diff === 1) return { key: "date.tomorrow" };
    return { text: formatISODate(iso, lang, { weekday: "short", day: "numeric", month: "short" }) };
  }

  return {
    toISODate, parseISODate, isValidISODate, todayISO, addDays, diffDays, compareISO, isBetween,
    daysInMonth, firstWeekdayMon0, isLeapYear, monthGrid, shiftMonth, localeFor,
    formatISODate, formatMonthYear, weekdayLabels, formatTime, formatDateTime, relativeDayLabel,
  };
});
