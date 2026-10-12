import { useMemo, useState } from "react";
import { addMonths, eachDayOfInterval, endOfMonth, endOfWeek, format, isSameDay, isSameMonth, isToday, isWithinInterval, parseISO, startOfMonth, startOfWeek, subMonths } from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/cn";
import type { PeriodRecord, SymptomRecord } from "@/lib/types";

const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

export function CycleCalendar({
  periods,
  symptoms,
  selected,
  onSelect,
  compact = false,
}: {
  periods: PeriodRecord[];
  symptoms: SymptomRecord[];
  selected?: string | null;
  onSelect?: (iso: string) => void;
  compact?: boolean;
}) {
  const [month, setMonth] = useState(() => startOfMonth(new Date()));

  const days = useMemo(
    () => eachDayOfInterval({ start: startOfWeek(startOfMonth(month), { weekStartsOn: 1 }), end: endOfWeek(endOfMonth(month), { weekStartsOn: 1 }) }),
    [month],
  );

  const symptomDays = useMemo(() => new Set(symptoms.map((s) => s.record_date)), [symptoms]);
  const intervals = useMemo(
    () => periods.map((p) => ({ start: parseISO(p.start_date), end: p.end_date ? parseISO(p.end_date) : parseISO(p.start_date), open: !p.end_date, startIso: p.start_date })),
    [periods],
  );

  function dayState(day: Date) {
    const inPeriod = intervals.find((i) => isWithinInterval(day, { start: i.start, end: i.end }));
    return {
      period: !!inPeriod,
      periodStart: !!inPeriod && isSameDay(day, inPeriod.start),
      ongoing: !!inPeriod?.open,
      symptom: symptomDays.has(format(day, "yyyy-MM-dd")),
    };
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-sans text-base font-semibold text-ink-900">{format(month, "MMMM yyyy")}</h3>
        <div className="flex gap-1">
          <button type="button" onClick={() => setMonth((m) => subMonths(m, 1))} aria-label="Previous month" className="rounded-lg p-1.5 text-ink-500 hover:bg-plum-50 hover:text-plum-800">
            <ChevronLeft className="size-4" />
          </button>
          <button type="button" onClick={() => setMonth(startOfMonth(new Date()))} className="rounded-lg px-2 text-xs font-medium text-ink-500 hover:bg-plum-50 hover:text-plum-800">
            Today
          </button>
          <button type="button" onClick={() => setMonth((m) => addMonths(m, 1))} aria-label="Next month" className="rounded-lg p-1.5 text-ink-500 hover:bg-plum-50 hover:text-plum-800">
            <ChevronRight className="size-4" />
          </button>
        </div>
      </div>
      <div className="grid grid-cols-7 gap-y-1 text-center">
        {WEEKDAYS.map((d) => (
          <div key={d} className="pb-1 text-[0.68rem] font-semibold uppercase tracking-wide text-ink-400">
            {d}
          </div>
        ))}
        {days.map((day) => {
          const iso = format(day, "yyyy-MM-dd");
          const s = dayState(day);
          const outside = !isSameMonth(day, month);
          const isSelected = selected === iso;
          const future = day > new Date();
          const label = [format(day, "d MMMM yyyy"), s.periodStart ? "period start" : s.period ? "period day" : "", s.symptom ? "symptoms logged" : ""].filter(Boolean).join(", ");
          return (
            <button
              key={iso}
              type="button"
              disabled={!onSelect || future}
              onClick={() => onSelect?.(iso)}
              aria-label={label}
              aria-pressed={isSelected}
              className={cn(
                "relative mx-auto flex flex-col items-center justify-center rounded-xl text-sm transition-colors",
                compact ? "size-8" : "size-10 sm:size-11",
                outside && "text-ink-300",
                !outside && !s.period && "text-ink-700",
                s.period && !outside && "bg-plum-700 text-white",
                s.period && outside && "bg-plum-200 text-white",
                s.ongoing && "ring-2 ring-rose-300 ring-offset-1",
                isSelected && !s.period && "bg-lavender-200 text-lavender-700",
                isToday(day) && !s.period && "font-bold text-plum-800",
                onSelect && !future && "hover:bg-plum-100",
                future && "cursor-default opacity-50",
              )}
            >
              <span>{format(day, "d")}</span>
              {s.symptom && <span className={cn("absolute bottom-1 size-1.5 rounded-full", s.period ? "bg-rose-200" : "bg-rose-500")} aria-hidden />}
              {isToday(day) && <span className="absolute -top-0.5 right-0.5 size-1.5 rounded-full bg-sage-500" aria-hidden />}
            </button>
          );
        })}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[0.7rem] text-ink-500">
        <li className="flex items-center gap-1.5"><span className="size-3 rounded-md bg-plum-700" aria-hidden /> Recorded period day</li>
        <li className="flex items-center gap-1.5"><span className="size-3 rounded-md ring-2 ring-rose-300" aria-hidden /> Ongoing (no end date yet)</li>
        <li className="flex items-center gap-1.5"><span className="size-1.5 rounded-full bg-rose-500" aria-hidden /> Symptom logged</li>
        <li className="flex items-center gap-1.5"><span className="size-1.5 rounded-full bg-sage-500" aria-hidden /> Today</li>
      </ul>
      <p className="mt-1 text-[0.7rem] text-ink-400">Only recorded dates are shown. SakhiSahay does not predict future periods yet.</p>
    </div>
  );
}
