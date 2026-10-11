import { Pencil, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { durationDays, fmtDate, fmtRange } from "@/lib/dates";
import type { PeriodRecord, SymptomCatalogueItem, SymptomRecord } from "@/lib/types";

const SEVERITY_LABEL: Record<number, string> = { 1: "mild", 2: "moderate", 3: "severe" };

export function PeriodHistory({ periods, onEdit, onDelete }: { periods: PeriodRecord[]; onEdit: (p: PeriodRecord) => void; onDelete: (p: PeriodRecord) => void }) {
  if (periods.length === 0) {
    return <EmptyState title="No periods logged yet" description="Your first entry starts your history. Add a start date, and the end date whenever you know it." />;
  }
  return (
    <ul className="divide-y divide-ivory-200">
      {periods.map((p) => {
        const days = durationDays(p.start_date, p.end_date);
        return (
          <li key={p.id} className="flex items-center gap-3 py-3">
            <span className="flex size-10 shrink-0 flex-col items-center justify-center rounded-xl bg-plum-100 text-plum-800">
              <span className="text-[0.6rem] font-semibold uppercase leading-none">{fmtDate(p.start_date, "MMM")}</span>
              <span className="text-base font-semibold leading-tight">{fmtDate(p.start_date, "d")}</span>
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-ink-900">{fmtRange(p.start_date, p.end_date)}</p>
              <p className="flex flex-wrap items-center gap-1.5 text-xs text-ink-500">
                {days ? <span>{days} day{days === 1 ? "" : "s"}</span> : <Badge tone="rose">ongoing</Badge>}
                {p.flow && <Badge tone="neutral">{p.flow}</Badge>}
                {p.notes && <span className="truncate">· {p.notes}</span>}
              </p>
            </div>
            <div className="flex shrink-0 gap-1">
              <Button variant="ghost" size="sm" onClick={() => onEdit(p)} aria-label={`Edit period starting ${fmtDate(p.start_date)}`} className="px-2">
                <Pencil className="size-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={() => onDelete(p)} aria-label={`Delete period starting ${fmtDate(p.start_date)}`} className="px-2 text-danger-600 hover:bg-danger-100">
                <Trash2 className="size-4" />
              </Button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function SymptomHistory({
  symptoms,
  catalogue,
  onEdit,
  onDelete,
}: {
  symptoms: SymptomRecord[];
  catalogue: SymptomCatalogueItem[];
  onEdit: (s: SymptomRecord) => void;
  onDelete: (s: SymptomRecord) => void;
}) {
  const label = (key: string) => catalogue.find((c) => c.key === key)?.label ?? key;
  if (symptoms.length === 0) {
    return <EmptyState title="No symptoms logged yet" description="Tracking a few symptoms over time is what makes patterns visible later." />;
  }
  const byDate = symptoms.reduce<Record<string, SymptomRecord[]>>((acc, s) => {
    (acc[s.record_date] ??= []).push(s);
    return acc;
  }, {});
  return (
    <div className="space-y-4">
      {Object.entries(byDate).map(([date, items]) => (
        <div key={date}>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-400">{fmtDate(date, "EEEE, d MMM yyyy")}</p>
          <ul className="space-y-1.5">
            {items.map((s) => (
              <li key={s.id} className="flex items-center gap-3 rounded-xl border border-ivory-200 bg-white px-3 py-2">
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-1.5 text-sm text-ink-900">
                    <span className="font-medium">{label(s.symptom)}</span>
                    {s.severity && <Badge tone={s.severity === 3 ? "rose" : s.severity === 2 ? "lavender" : "neutral"}>{SEVERITY_LABEL[s.severity]}</Badge>}
                  </p>
                  {s.notes && <p className="truncate text-xs text-ink-500">{s.notes}</p>}
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button variant="ghost" size="sm" onClick={() => onEdit(s)} aria-label={`Edit ${label(s.symptom)} on ${fmtDate(s.record_date)}`} className="px-2">
                    <Pencil className="size-4" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => onDelete(s)} aria-label={`Delete ${label(s.symptom)} on ${fmtDate(s.record_date)}`} className="px-2 text-danger-600 hover:bg-danger-100">
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
