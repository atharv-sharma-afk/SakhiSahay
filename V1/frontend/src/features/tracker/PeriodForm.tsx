import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Input, Select, Textarea } from "@/components/ui/Field";
import { ApiError } from "@/lib/api";
import { todayIso } from "@/lib/dates";
import type { FlowLevel, PeriodInput, PeriodRecord } from "@/lib/types";

const FLOWS: { value: FlowLevel | ""; label: string }[] = [
  { value: "", label: "Prefer not to record" },
  { value: "spotting", label: "Spotting" },
  { value: "light", label: "Light" },
  { value: "medium", label: "Medium" },
  { value: "heavy", label: "Heavy" },
];

export function PeriodForm({
  initial,
  defaultStart,
  onSubmit,
  onCancel,
  submitting,
}: {
  initial?: PeriodRecord | null;
  defaultStart?: string | null;
  onSubmit: (data: PeriodInput) => Promise<unknown>;
  onCancel?: () => void;
  submitting: boolean;
}) {
  const [start, setStart] = useState(initial?.start_date ?? defaultStart ?? todayIso());
  const [end, setEnd] = useState(initial?.end_date ?? "");
  const [flow, setFlow] = useState<FlowLevel | "">(initial?.flow ?? "");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!initial && defaultStart) setStart(defaultStart);
  }, [defaultStart, initial]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (!start) local.start_date = "Choose the first day of bleeding.";
    if (end && end < start) local.end_date = "End date must be on or after the start date.";
    if (start > todayIso()) local.start_date = "Start date cannot be in the future.";
    setErrors(local);
    if (Object.keys(local).length) return;
    try {
      await onSubmit({ start_date: start, end_date: end || null, flow: flow || null, notes: notes.trim() || null });
      if (!initial) {
        setEnd("");
        setFlow("");
        setNotes("");
      }
    } catch (err) {
      if (err instanceof ApiError) setErrors(Object.keys(err.fieldErrors).length ? err.fieldErrors : { _: err.message });
      else setErrors({ _: "Could not save. Please try again." });
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Period started" type="date" value={start} max={todayIso()} onChange={(e) => setStart(e.target.value)} error={errors.start_date} required />
        <Input label="Period ended" type="date" value={end} min={start} max={todayIso()} onChange={(e) => setEnd(e.target.value)} error={errors.end_date} optional hint="Leave empty if it is still ongoing." />
      </div>
      <Select label="Flow" value={flow} onChange={(e) => setFlow(e.target.value as FlowLevel | "")} optional error={errors.flow}>
        {FLOWS.map((f) => (
          <option key={f.value} value={f.value}>
            {f.label}
          </option>
        ))}
      </Select>
      <Textarea label="Notes" value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} optional placeholder="Anything you want to remember about this period" error={errors.notes} />
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
          {initial ? "Save changes" : "Save period"}
        </Button>
      </div>
    </form>
  );
}
