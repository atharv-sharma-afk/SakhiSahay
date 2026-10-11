import { useState } from "react";
import { Activity, CalendarRange, ChevronDown, Clock3, ExternalLink, Lightbulb, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import type { Insight, InsightsResponse } from "@/lib/types";

const ICON: Record<Insight["kind"], typeof Activity> = {
  cycle_length: CalendarRange,
  period_duration: Clock3,
  symptom_frequency: Activity,
  symptom_days: Activity,
  guidance: Lightbulb,
};

export function InsightCard({ insight, compact = false }: { insight: Insight; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const Icon = ICON[insight.kind];
  const guidance = insight.kind === "guidance";
  return (
    <div className={cn("rounded-2xl border p-4", guidance ? "border-amber-200 bg-amber-100/50" : "border-ivory-300 bg-white", !compact && "shadow-soft")}>
      <div className="flex items-start gap-3">
        <span className={cn("flex size-9 shrink-0 items-center justify-center rounded-xl", guidance ? "bg-white text-amber-800" : "bg-plum-100 text-plum-700")}>
          <Icon className="size-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-sans text-sm font-semibold text-ink-900">{insight.title}</h3>
            <Badge tone={guidance ? "amber" : "plum"}>{guidance ? "General guidance" : "From your records"}</Badge>
          </div>
          <p className="mt-1 text-sm leading-relaxed text-ink-700">{insight.statement}</p>
          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-plum-700">
            How this was calculated <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} aria-hidden />
          </button>
          {open && (
            <div className="mt-2 rounded-xl bg-ivory-100 px-3 py-2 text-xs leading-relaxed text-ink-700">
              <p>{insight.basis}</p>
              <p className="mt-1 text-ink-500">Records used: {insight.records_used}</p>
              {insight.source_url && (
                <a href={insight.source_url} target="_blank" rel="noreferrer" className="mt-1 inline-flex items-center gap-1 font-medium text-plum-700 underline underline-offset-2">
                  {insight.source_label ?? "Source"} <ExternalLink className="size-3" aria-hidden />
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function InsightsPanel({ data }: { data: InsightsResponse }) {
  return (
    <div className="space-y-3">
      {data.insights.map((i) => (
        <InsightCard key={`${i.kind}-${i.title}`} insight={i} />
      ))}
      {data.insights.length === 0 && (
        <div className="rounded-2xl border border-dashed border-plum-200 bg-plum-50/50 p-5 text-center">
          <Sparkles className="mx-auto mb-2 size-5 text-plum-500" aria-hidden />
          <p className="text-sm font-medium text-ink-900">No insights yet - and that is honest, not broken.</p>
          <p className="mt-1 text-xs text-ink-500">Insights appear only when your own records can support them.</p>
        </div>
      )}
      {data.requirements.length > 0 && (
        <div className="rounded-2xl border border-ivory-300 bg-ivory-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">What unlocks more</p>
          <ul className="mt-2 space-y-1.5 text-sm text-ink-700">
            {data.requirements.map((r) => (
              <li key={r.metric} className="flex gap-2">
                <span className="mt-2 size-1.5 shrink-0 rounded-full bg-plum-400" aria-hidden />
                {r.message}
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="text-[0.7rem] text-ink-400">{data.generated_from}</p>
    </div>
  );
}
