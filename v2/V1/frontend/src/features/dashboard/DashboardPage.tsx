import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpenText, CalendarHeart, Droplets, MessageCircleHeart, Sparkles, Stethoscope } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState, Skeleton } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import { fmtDate, fmtRange, greeting } from "@/lib/dates";
import { CycleCalendar } from "../tracker/CycleCalendar";
import { InsightCard } from "../tracker/InsightCards";

const QUICK_QUESTIONS = ["What is a normal cycle length?", "PCOS ke symptoms kya hote hain?", "माहवारी में दर्द क्यों होता है?"];

function QuickAction({ to, icon: Icon, title, text }: { to: string; icon: typeof Droplets; title: string; text: string }) {
  return (
    <Link to={to} className="group flex items-center gap-4 rounded-2xl border border-ivory-300 bg-white p-4 shadow-soft transition-colors hover:border-plum-300">
      <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-plum-100 text-plum-700 transition-colors group-hover:bg-plum-700 group-hover:text-white">
        <Icon className="size-5" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-ink-900">{title}</span>
        <span className="block text-xs text-ink-500">{text}</span>
      </span>
      <ArrowRight className="size-4 text-ink-300 transition-transform group-hover:translate-x-0.5 group-hover:text-plum-700" aria-hidden />
    </Link>
  );
}

export function DashboardPage() {
  const periods = useQuery({ queryKey: ["tracker", "periods"], queryFn: api.periods });
  const symptoms = useQuery({ queryKey: ["tracker", "symptoms"], queryFn: api.symptoms });
  const insights = useQuery({ queryKey: ["insights"], queryFn: api.insights });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, retry: 1 });

  const loading = periods.isLoading || insights.isLoading;
  const hasRecords = (periods.data?.length ?? 0) + (symptoms.data?.length ?? 0) > 0;
  const stats = insights.data?.stats;
  const latest = periods.data?.[0];
  const highlight = insights.data?.insights.find((i) => i.kind !== "guidance") ?? insights.data?.insights[0];
  const recent = [
    ...(periods.data ?? []).slice(0, 3).map((p) => ({ id: p.id, date: p.start_date, label: `Period ${fmtRange(p.start_date, p.end_date)}`, kind: "period" as const })),
    ...(symptoms.data ?? []).slice(0, 3).map((s) => ({ id: s.id, date: s.record_date, label: `${s.symptom.replace("_", " ")} logged`, kind: "symptom" as const })),
  ]
    .sort((a, b) => (a.date < b.date ? 1 : -1))
    .slice(0, 4);

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-3xl bg-plum-800 px-6 py-8 text-white shadow-lift sm:px-10 sm:py-10">
        <div className="pointer-events-none absolute -right-16 -top-20 size-72 rounded-full bg-plum-600/60 blur-3xl" aria-hidden />
        <div className="pointer-events-none absolute -bottom-24 right-32 size-64 rounded-full bg-lavender-500/30 blur-3xl" aria-hidden />
        <div className="relative max-w-2xl">
          <p className="text-sm font-medium text-plum-200">{greeting()}, Friend</p>
          <h1 className="mt-1 text-3xl font-semibold leading-tight sm:text-[2.6rem]">
            Your AI-powered women's health companion
          </h1>
          <p className="mt-3 max-w-xl text-[0.95rem] leading-relaxed text-plum-100">
            Ask in English, Hindi or Hinglish and get answers grounded in WHO, NHS, CDC and Government of India sources. Track your cycle privately and see what your own records show.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/assistant" className="inline-flex h-12 items-center gap-2 rounded-2xl bg-white px-6 text-base font-medium text-plum-800 shadow-soft transition-colors hover:bg-plum-50 active:bg-plum-100">
              <MessageCircleHeart className="size-5" aria-hidden /> Ask SakhiSahay
            </Link>
            <Link to="/tracker" className="inline-flex h-12 items-center gap-2 rounded-2xl border border-plum-300/60 px-6 text-base font-medium text-white hover:bg-plum-700">
              <CalendarHeart className="size-5" aria-hidden /> Log today
            </Link>
          </div>
          <div className="mt-5 flex flex-wrap gap-2 text-xs">
            {health.data && (
              <>
                <Badge tone={health.data.llm.configured ? "sage" : "amber"} className="bg-white/15 text-white">
                  {health.data.llm.configured ? `Live model: ${health.data.llm.model}` : "Retrieval-only mode"}
                </Badge>
                <Badge className="bg-white/15 text-white">{health.data.knowledge.indexed_sources} cited sources</Badge>
              </>
            )}
          </div>
        </div>
      </section>

      <section aria-labelledby="quick-actions">
        <h2 id="quick-actions" className="sr-only">
          Quick actions
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <QuickAction to="/tracker" icon={Droplets} title="Log a period" text="Start or end date, flow optional" />
          <QuickAction to="/tracker" icon={CalendarHeart} title="Log a symptom" text="Cramps, fatigue, mood and more" />
          <QuickAction to="/assistant" icon={MessageCircleHeart} title="Ask a question" text="Answers with real citations" />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader eyebrow="Cycle overview" title={hasRecords ? "Where you are" : "Start your history"} action={<Link to="/tracker" className="text-sm font-medium text-plum-700 hover:underline">Open tracker</Link>} />
          {loading ? (
            <Skeleton className="h-40" />
          ) : !hasRecords ? (
            <EmptyState
              icon={<Droplets className="size-5" aria-hidden />}
              title="No records yet"
              description="Log your most recent period to begin. After three logged periods SakhiSahay can describe your cycle lengths - from your own data only."
              action={
                <Link to="/tracker" className="inline-flex h-9 items-center rounded-xl border border-plum-200 bg-white px-3.5 text-sm font-medium text-plum-800 hover:bg-plum-50">
                  Log my first period
                </Link>
              }
            />
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-2xl bg-plum-50 p-3">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-wider text-plum-500">Day of cycle</p>
                  <p className="font-display text-3xl font-semibold text-plum-800">{stats?.days_since_last_period_start !== null && stats ? stats.days_since_last_period_start + 1 : "-"}</p>
                </div>
                <div className="rounded-2xl bg-ivory-100 p-3">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-wider text-ink-400">Last period</p>
                  <p className="text-sm font-semibold text-ink-900">{latest ? fmtDate(latest.start_date, "d MMM") : "-"}</p>
                  <p className="text-xs text-ink-500">{latest?.end_date ? `${fmtDate(latest.end_date, "d MMM")} end` : latest ? "ongoing" : ""}</p>
                </div>
                <div className="rounded-2xl bg-ivory-100 p-3">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-wider text-ink-400">Median cycle</p>
                  <p className="text-sm font-semibold text-ink-900">{stats?.median_cycle_length ? `${stats.median_cycle_length} days` : "needs 3 periods"}</p>
                  <p className="text-xs text-ink-500">{stats?.completed_cycles ? `${stats.completed_cycles} cycles logged` : ""}</p>
                </div>
              </div>
              <CycleCalendar periods={periods.data ?? []} symptoms={symptoms.data ?? []} compact />
            </div>
          )}
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader eyebrow="Insight" title="From your records" />
            {loading ? (
              <Skeleton className="h-24" />
            ) : highlight ? (
              <InsightCard insight={highlight} compact />
            ) : (
              <div className="rounded-2xl border border-dashed border-plum-200 bg-plum-50/40 p-4 text-sm text-ink-500">
                <Sparkles className="mb-2 size-4 text-plum-500" aria-hidden />
                {insights.data?.requirements[0]?.message ?? "Insights appear once your records can support them."}
              </div>
            )}
          </Card>

          <Card>
            <CardHeader eyebrow="Recent" title="Latest entries" />
            {recent.length === 0 ? (
              <p className="text-sm text-ink-500">Nothing logged yet.</p>
            ) : (
              <ul className="divide-y divide-ivory-200 text-sm">
                {recent.map((r) => (
                  <li key={`${r.kind}-${r.id}`} className="flex items-center gap-3 py-2">
                    <span className={`size-2 rounded-full ${r.kind === "period" ? "bg-plum-600" : "bg-rose-500"}`} aria-hidden />
                    <span className="flex-1 capitalize text-ink-900">{r.label}</span>
                    <span className="text-xs text-ink-400">{fmtDate(r.date, "d MMM")}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader eyebrow="Ask · Understand" title="Try the assistant" description="Three suggested questions in three languages." />
          <div className="flex flex-wrap gap-2">
            {QUICK_QUESTIONS.map((q) => (
              <Link key={q} to={`/assistant?q=${encodeURIComponent(q)}`} className="rounded-full border border-ivory-300 bg-white px-4 py-2 text-sm text-ink-700 shadow-soft hover:border-plum-300 hover:text-plum-800">
                {q}
              </Link>
            ))}
          </div>
          <p className="mt-4 flex items-center gap-2 text-xs text-ink-500">
            <BookOpenText className="size-4" aria-hidden /> Every answer lists the exact passages it used.{" "}
            <Link to="/sources" className="font-medium text-plum-700 hover:underline">
              See all sources
            </Link>
          </p>
        </Card>
        <Card className="bg-lavender-100/50">
          <CardHeader eyebrow="Consult" title="Doctor Connect" description="A preview of the path from understanding to professional care." />
          <Badge tone="lavender">Preview · demonstration data</Badge>
          <Link to="/doctors" className="mt-4 flex items-center gap-2 text-sm font-medium text-plum-700 hover:underline">
            <Stethoscope className="size-4" aria-hidden /> Explore the preview
          </Link>
        </Card>
      </div>
    </div>
  );
}
