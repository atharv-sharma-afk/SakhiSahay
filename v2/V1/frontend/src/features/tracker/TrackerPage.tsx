import { useState } from "react";
import { CalendarHeart, Droplets, ShieldCheck, Trash2 } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Skeleton } from "@/components/ui/EmptyState";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/cn";
import { fmtDate } from "@/lib/dates";
import type { PeriodRecord, SymptomRecord } from "@/lib/types";
import { CycleCalendar } from "./CycleCalendar";
import { PeriodHistory, SymptomHistory } from "./HistoryLists";
import { InsightsPanel } from "./InsightCards";
import { PeriodForm } from "./PeriodForm";
import { SymptomForm } from "./SymptomForm";
import { useTrackerData, useTrackerMutations } from "./hooks";

type Tab = "period" | "symptom";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl bg-ivory-50 px-4 py-3">
      <p className="text-[0.7rem] font-semibold uppercase tracking-wider text-ink-400">{label}</p>
      <p className="mt-0.5 font-display text-2xl font-semibold text-plum-800">{value}</p>
      {hint && <p className="text-xs text-ink-500">{hint}</p>}
    </div>
  );
}

export function TrackerPage() {
  const toast = useToast();
  const { periods, symptoms, catalogue, insights } = useTrackerData();
  const m = useTrackerMutations();
  const [tab, setTab] = useState<Tab>("period");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [editingPeriod, setEditingPeriod] = useState<PeriodRecord | null>(null);
  const [editingSymptom, setEditingSymptom] = useState<SymptomRecord | null>(null);
  const [confirm, setConfirm] = useState<{ kind: "period" | "symptom" | "all"; id?: string; label: string } | null>(null);

  const loading = periods.isLoading || symptoms.isLoading || catalogue.isLoading;
  const stats = insights.data?.stats;

  async function handleDelete() {
    if (!confirm) return;
    try {
      if (confirm.kind === "period" && confirm.id) await m.deletePeriod.mutateAsync(confirm.id);
      if (confirm.kind === "symptom" && confirm.id) await m.deleteSymptom.mutateAsync(confirm.id);
      if (confirm.kind === "all") await m.deleteAll.mutateAsync();
      toast(confirm.kind === "all" ? "All your tracker data was deleted." : "Entry deleted.", "info");
    } catch {
      toast("Could not delete. Please try again.", "error");
    } finally {
      setConfirm(null);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Track · Analyze"
        title="Cycle & symptom tracker"
        description="Log what you notice. Everything stays in your own records and insights are described plainly, never as a diagnosis."
        action={
          periods.data && periods.data.length + (symptoms.data?.length ?? 0) > 0 ? (
            <Button variant="danger" size="sm" onClick={() => setConfirm({ kind: "all", label: "all of your tracker data" })}>
              <Trash2 className="size-4" aria-hidden /> Delete all my data
            </Button>
          ) : null
        }
      />

      {loading ? (
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-6">
            <Card>
              <CardHeader eyebrow="Calendar" title="Your recorded months" description="Select a day to pre-fill the log form." />
              <CycleCalendar periods={periods.data ?? []} symptoms={symptoms.data ?? []} selected={selectedDate} onSelect={setSelectedDate} />
            </Card>

            {stats && (
              <Card>
                <CardHeader eyebrow="Overview" title="Cycle statistics" description="Calculated only from the dates you logged." />
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <Stat label="Periods logged" value={String(stats.logged_periods)} />
                  <Stat label="Median cycle" value={stats.median_cycle_length ? `${stats.median_cycle_length}d` : "-"} hint={stats.completed_cycles ? `${stats.completed_cycles} completed cycles` : "needs 3 periods"} />
                  <Stat label="Cycle range" value={stats.shortest_cycle ? `${stats.shortest_cycle}-${stats.longest_cycle}d` : "-"} />
                  <Stat label="Avg period length" value={stats.average_period_duration ? `${stats.average_period_duration}d` : "-"} hint={stats.periods_with_duration ? `${stats.periods_with_duration} with end dates` : "needs end dates"} />
                </div>
                {stats.days_since_last_period_start !== null && (
                  <p className="mt-3 text-sm text-ink-500">
                    Day <span className="font-semibold text-plum-800">{stats.days_since_last_period_start + 1}</span> since your last recorded period start ({fmtDate(stats.last_period_start)}).
                  </p>
                )}
              </Card>
            )}

            <Card>
              <CardHeader eyebrow="Insights" title="What your records show" description="Each insight explains how it was computed." />
              {insights.data ? <InsightsPanel data={insights.data} /> : <Skeleton className="h-24" />}
            </Card>
          </div>

          <div className="space-y-6">
            <Card>
              <div className="mb-4 flex rounded-xl bg-ivory-100 p-1" role="tablist" aria-label="What to log">
                {(["period", "symptom"] as Tab[]).map((t) => (
                  <button
                    key={t}
                    role="tab"
                    aria-selected={tab === t}
                    onClick={() => setTab(t)}
                    className={cn("flex flex-1 items-center justify-center gap-2 rounded-lg py-2 text-sm font-medium transition-colors", tab === t ? "bg-white text-plum-800 shadow-soft" : "text-ink-500 hover:text-ink-900")}
                  >
                    {t === "period" ? <Droplets className="size-4" aria-hidden /> : <CalendarHeart className="size-4" aria-hidden />}
                    {t === "period" ? "Log a period" : "Log a symptom"}
                  </button>
                ))}
              </div>
              {selectedDate && (
                <p className="mb-3 text-xs text-ink-500">
                  Pre-filled with <span className="font-medium text-plum-800">{fmtDate(selectedDate)}</span>.{" "}
                  <button type="button" className="underline" onClick={() => setSelectedDate(null)}>
                    Clear
                  </button>
                </p>
              )}
              {tab === "period" ? (
                <PeriodForm
                  key={selectedDate ?? "new-period"}
                  defaultStart={selectedDate}
                  submitting={m.createPeriod.isPending}
                  onSubmit={async (data) => {
                    await m.createPeriod.mutateAsync(data);
                    toast("Period saved.");
                  }}
                />
              ) : (
                <SymptomForm
                  key={selectedDate ?? "new-symptom"}
                  catalogue={catalogue.data ?? []}
                  defaultDate={selectedDate}
                  submitting={m.createSymptom.isPending}
                  onSubmit={async (data) => {
                    await m.createSymptom.mutateAsync(data);
                    toast("Symptom saved.");
                  }}
                />
              )}
            </Card>

            <Card>
              <CardHeader eyebrow="History" title="Periods" description={periods.data?.length ? `${periods.data.length} logged` : undefined} />
              <PeriodHistory periods={periods.data ?? []} onEdit={setEditingPeriod} onDelete={(p) => setConfirm({ kind: "period", id: p.id, label: `the period starting ${fmtDate(p.start_date)}` })} />
            </Card>

            <Card>
              <CardHeader eyebrow="History" title="Symptoms" description={symptoms.data?.length ? `${symptoms.data.length} entries` : undefined} />
              <SymptomHistory
                symptoms={symptoms.data ?? []}
                catalogue={catalogue.data ?? []}
                onEdit={setEditingSymptom}
                onDelete={(s) => setConfirm({ kind: "symptom", id: s.id, label: `this symptom entry on ${fmtDate(s.record_date)}` })}
              />
            </Card>

            <div className="flex items-start gap-3 rounded-2xl border border-sage-200 bg-sage-100/50 px-4 py-3 text-xs leading-relaxed text-sage-700">
              <ShieldCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
              <p>Your records are stored locally in this prototype's database and are never added to the assistant's knowledge base. You can edit or delete any entry at any time.</p>
            </div>
          </div>
        </div>
      )}

      <Dialog open={!!editingPeriod} onClose={() => setEditingPeriod(null)} title="Edit period">
        {editingPeriod && (
          <PeriodForm
            initial={editingPeriod}
            submitting={m.updatePeriod.isPending}
            onCancel={() => setEditingPeriod(null)}
            onSubmit={async (data) => {
              await m.updatePeriod.mutateAsync({ id: editingPeriod.id, data });
              toast("Period updated.");
              setEditingPeriod(null);
            }}
          />
        )}
      </Dialog>

      <Dialog open={!!editingSymptom} onClose={() => setEditingSymptom(null)} title="Edit symptom">
        {editingSymptom && (
          <SymptomForm
            catalogue={catalogue.data ?? []}
            initial={editingSymptom}
            submitting={m.updateSymptom.isPending}
            onCancel={() => setEditingSymptom(null)}
            onSubmit={async (data) => {
              await m.updateSymptom.mutateAsync({ id: editingSymptom.id, data });
              toast("Symptom updated.");
              setEditingSymptom(null);
            }}
          />
        )}
      </Dialog>

      <Dialog
        open={!!confirm}
        onClose={() => setConfirm(null)}
        title={confirm?.kind === "all" ? "Delete all tracker data?" : "Delete this entry?"}
        description={`This will permanently remove ${confirm?.label ?? ""}. This cannot be undone.`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirm(null)}>
              Keep it
            </Button>
            <Button variant="danger" onClick={handleDelete} loading={m.deletePeriod.isPending || m.deleteSymptom.isPending || m.deleteAll.isPending}>
              Delete
            </Button>
          </>
        }
      />
    </div>
  );
}
