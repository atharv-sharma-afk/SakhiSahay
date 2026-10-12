import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Field";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { todayIso } from "@/lib/dates";
import type { SymptomCatalogueItem, SymptomInput, SymptomRecord } from "@/lib/types";

const GROUP_LABEL: Record<string, string> = { pain: "Pain", body: "Body", bleeding: "Bleeding", mood: "Mood & sleep" };
const SEVERITY = [
  { value: 1, label: "Mild" },
  { value: 2, label: "Moderate" },
  { value: 3, label: "Severe" },
];

export function SymptomForm({
  catalogue,
  initial,
  defaultDate,
  onSubmit,
  onCancel,
  submitting,
}: {
  catalogue: SymptomCatalogueItem[];
  initial?: SymptomRecord | null;
  defaultDate?: string | null;
  onSubmit: (data: SymptomInput) => Promise<unknown>;
  onCancel?: () => void;
  submitting: boolean;
}) {
  const [date, setDate] = useState(initial?.record_date ?? defaultDate ?? todayIso());
  const [symptom, setSymptom] = useState(initial?.symptom ?? "");
  const [severity, setSeverity] = useState<number | null>(initial?.severity ?? null);
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!initial && defaultDate) setDate(defaultDate);
  }, [defaultDate, initial]);

  const groups = catalogue.reduce<Record<string, SymptomCatalogueItem[]>>((acc, item) => {
    (acc[item.group] ??= []).push(item);
    return acc;
  }, {});

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!symptom) local.symptom = "Pick a symptom.";
    if (!date) local.record_date = "Pick a date.";
    setErrors(local);
    if (Object.keys(local).length) return;
    try {
      await onSubmit({ record_date: date, symptom, severity, notes: notes.trim() || null });
      if (!initial) {
        setSymptom("");
        setSeverity(null);
        setNotes("");
      }
    } catch (err) {
      if (err instanceof ApiError) setErrors(Object.keys(err.fieldErrors).length ? err.fieldErrors : { _: err.message });
      else setErrors({ _: "Could not save. Please try again." });
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <Input label="Date" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} error={errors.record_date} required />

      <fieldset>
        <legend className="mb-2 text-sm font-medium text-ink-700">Symptom</legend>
        <div className="space-y-3">
          {Object.entries(groups).map(([group, items]) => (
            <div key={group}>
              <p className="mb-1.5 text-[0.7rem] font-semibold uppercase tracking-wider text-ink-400">{GROUP_LABEL[group] ?? group}</p>
              <div className="flex flex-wrap gap-2">
                {items.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    aria-pressed={symptom === item.key}
                    onClick={() => setSymptom(item.key)}
                    className={cn(
                      "min-h-9 rounded-full border px-3.5 text-sm transition-colors",
                      symptom === item.key ? "border-plum-700 bg-plum-700 text-white" : "border-ivory-300 bg-white text-ink-700 hover:border-plum-300",
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
        {errors.symptom && (
          <p className="mt-2 text-xs text-danger-600" role="alert">
            {errors.symptom}
          </p>
        )}
      </fieldset>

      <fieldset>
        <legend className="mb-2 flex items-baseline justify-between text-sm font-medium text-ink-700">
          <span>How strong was it?</span>
          <span className="text-xs font-normal text-ink-400">optional</span>
        </legend>
        <div className="grid grid-cols-3 gap-2">
          {SEVERITY.map((s) => (
            <button
              key={s.value}
              type="button"
              aria-pressed={severity === s.value}
              onClick={() => setSeverity(severity === s.value ? null : s.value)}
              className={cn(
                "flex min-h-11 flex-col items-center justify-center rounded-xl border text-sm transition-colors",
                severity === s.value ? "border-plum-700 bg-plum-50 text-plum-800" : "border-ivory-300 bg-white text-ink-700 hover:border-plum-300",
              )}
            >
              <span className="flex gap-0.5" aria-hidden>
                {[1, 2, 3].map((dot) => (
                  <span key={dot} className={cn("size-1.5 rounded-full", dot <= s.value ? "bg-plum-600" : "bg-ivory-300")} />
                ))}
              </span>
              <span className="mt-1">{s.label}</span>
            </button>
          ))}
        </div>
      </fieldset>

      <Textarea label="Notes" value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} optional placeholder="e.g. worse in the evening" error={errors.notes} />

      {errors._ && (
        <p className="rounded-xl bg-danger-100 px-3 py-2 text-sm text-danger-800" role="alert">
          {errors._}
        </p>
      )}
      <div className="flex flex-wrap justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" loading={submitting}>
          {initial ? "Save changes" : "Save symptom"}
        </Button>
      </div>
    </form>
  );
}
