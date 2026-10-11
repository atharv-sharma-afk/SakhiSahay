import { differenceInCalendarDays, format, parseISO } from "date-fns";

export const todayIso = () => format(new Date(), "yyyy-MM-dd");

export function fmtDate(iso: string | null | undefined, pattern = "d MMM yyyy"): string {
  if (!iso) return "-";
  return format(parseISO(iso), pattern);
}

export function fmtRange(start: string, end: string | null): string {
  if (!end) return `${fmtDate(start, "d MMM")} - ongoing`;
  const s = parseISO(start);
  const e = parseISO(end);
  const sameMonth = s.getMonth() === e.getMonth() && s.getFullYear() === e.getFullYear();
  return sameMonth ? `${format(s, "d")}-${format(e, "d MMM yyyy")}` : `${format(s, "d MMM")} - ${format(e, "d MMM yyyy")}`;
}

export function durationDays(start: string, end: string | null): number | null {
  if (!end) return null;
  return differenceInCalendarDays(parseISO(end), parseISO(start)) + 1;
}

export function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}
