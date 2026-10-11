import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { ChevronDown, ExternalLink, Sparkles, SearchX, ScrollText, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Notice } from "@/components/ui/Notice";
import { cn } from "@/lib/cn";
import type { ChatResponse, SourceRef } from "@/lib/types";

const PUBLISHER_TONE: Record<string, "plum" | "lavender" | "sage" | "rose" | "neutral"> = {
  "World Health Organization": "plum",
  "NHS (UK)": "lavender",
  "US CDC": "sage",
};

function publisherTone(publisher: string) {
  return PUBLISHER_TONE[publisher] ?? (publisher.includes("India") ? "rose" : "neutral");
}

function ModeBadge({ response }: { response: ChatResponse }) {
  if (response.mode === "llm") {
    return (
      <Badge tone="sage" icon={<Sparkles className="size-3" aria-hidden />}>
        Live answer · {response.model}
      </Badge>
    );
  }
  if (response.mode === "retrieval_only") {
    return (
      <Badge tone="amber" icon={<ScrollText className="size-3" aria-hidden />}>
        Retrieved passages only (no model)
      </Badge>
    );
  }
  return (
    <Badge tone="neutral" icon={<SearchX className="size-3" aria-hidden />}>
      Not covered by sources
    </Badge>
  );
}

const STRENGTH_LABEL = { strong: "Strong evidence match", moderate: "Moderate evidence match", weak: "Weak evidence match", none: "No matching evidence" } as const;
const STRENGTH_TONE = { strong: "sage", moderate: "lavender", weak: "amber", none: "neutral" } as const;

function SourceItem({ source, highlighted }: { source: SourceRef; highlighted: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <li id={`src-${source.source_id}-${source.ref}`} className={cn("rounded-xl border bg-white transition-colors", highlighted ? "border-plum-300 bg-plum-50/40" : "border-ivory-300")}>
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="flex w-full items-start gap-3 px-3.5 py-3 text-left">
        <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-plum-700 text-[0.7rem] font-semibold text-white">{source.ref}</span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Badge tone={publisherTone(source.publisher)}>{source.publisher}</Badge>
            {source.cited ? <Badge tone="sage">cited</Badge> : <Badge tone="neutral">retrieved</Badge>}
          </span>
          <span className="mt-1 block text-sm font-medium text-ink-900">{source.title}</span>
          {source.section && <span className="block text-xs text-ink-500">Section: {source.section}</span>}
        </span>
        <ChevronDown className={cn("mt-1 size-4 shrink-0 text-ink-400 transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      {open && (
        <div className="border-t border-ivory-200 px-3.5 py-3 text-sm">
          <p className="italic leading-relaxed text-ink-700">"{source.excerpt}"</p>
          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-ink-500">
            <dt>Document type</dt>
            <dd className="text-ink-700">{source.doc_type.replace("_", " ")}</dd>
            <dt>Similarity score</dt>
            <dd className="text-ink-700">{source.score.toFixed(3)}</dd>
            {source.updated_date && (
              <>
                <dt>Page date</dt>
                <dd className="text-ink-700">{source.updated_date}</dd>
              </>
            )}
            <dt>Accessed</dt>
            <dd className="text-ink-700">{source.accessed_date ?? "-"}</dd>
          </dl>
          <a href={source.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-plum-700 underline decoration-plum-300 underline-offset-2">
            Open original source <ExternalLink className="size-3.5" aria-hidden />
          </a>
        </div>
      )}
    </li>
  );
}

export function AnswerCard({ response, lang }: { response: ChatResponse; lang: string }) {
  const [highlight, setHighlight] = useState<number | null>(null);
  const [showSources, setShowSources] = useState(response.mode !== "llm");

  const markdown = useMemo(() => response.answer.replace(/\[S(\d{1,2})\]/g, (_m, n) => `[${n}](#cite-${n})`), [response.answer]);
  const urgent = response.safety.notices.filter((n) => n.level === "urgent");
  const advisory = response.safety.notices.filter((n) => n.level === "advisory");

  return (
    <div className="space-y-3">
      {urgent.map((n) => (
        <Notice key={n.title} tone="urgent" title={n.title}>
          {n.message}
          {n.source_url && (
            <>
              {" "}
              <a className="underline underline-offset-2" href={n.source_url} target="_blank" rel="noreferrer">
                {n.source_label ?? "Source"}
              </a>
            </>
          )}
        </Notice>
      ))}

      <div className="card overflow-hidden">
        <div className="flex flex-wrap items-center gap-2 border-b border-ivory-200 bg-ivory-50/70 px-5 py-3">
          <ModeBadge response={response} />
          <Badge tone={STRENGTH_TONE[response.evidence_strength]}>{STRENGTH_LABEL[response.evidence_strength]}</Badge>
          {response.tracker_context_used && (
            <Badge tone="rose" icon={<ShieldCheck className="size-3" aria-hidden />}>
              Used your tracker summary
            </Badge>
          )}
          <span className="ml-auto text-xs text-ink-400">{(response.latency_ms / 1000).toFixed(1)} s</span>
        </div>

        <div className="px-5 py-4" lang={lang}>
          <div className="prose-answer">
            <ReactMarkdown
              components={{
                a: ({ href, children }) => {
                  if (href?.startsWith("#cite-")) {
                    const n = Number(href.replace("#cite-", ""));
                    return (
                      <button
                        type="button"
                        onClick={() => {
                          setShowSources(true);
                          setHighlight(n);
                        }}
                        className="mx-0.5 inline-flex size-5 -translate-y-1 items-center justify-center rounded-full bg-plum-100 align-middle text-[0.68rem] font-semibold text-plum-800 hover:bg-plum-200"
                        aria-label={`Show source ${n}`}
                      >
                        {children}
                      </button>
                    );
                  }
                  return (
                    <a href={href} target="_blank" rel="noreferrer">
                      {children}
                    </a>
                  );
                },
              }}
            >
              {markdown}
            </ReactMarkdown>
          </div>
          {response.fallback_reason && <p className="mt-3 text-xs text-ink-400">{response.fallback_reason}</p>}
        </div>

        {advisory.length > 0 && (
          <div className="space-y-2 px-5 pb-4">
            {advisory.map((n) => (
              <Notice key={n.title} tone="advisory" title={n.title}>
                {n.message}
              </Notice>
            ))}
          </div>
        )}

        {response.sources.length > 0 && (
          <div className="border-t border-ivory-200">
            <button
              type="button"
              onClick={() => setShowSources((s) => !s)}
              aria-expanded={showSources}
              className="flex w-full items-center justify-between px-5 py-3 text-sm font-medium text-plum-800 hover:bg-plum-50/60"
            >
              <span>
                {response.mode === "insufficient_evidence" ? "Possibly related reading" : "Sources"} ({response.sources.length})
              </span>
              <ChevronDown className={cn("size-4 transition-transform", showSources && "rotate-180")} aria-hidden />
            </button>
            {showSources && (
              <ul className="space-y-2 px-5 pb-5">
                {response.sources.map((s) => (
                  <SourceItem key={`${s.source_id}-${s.ref}`} source={s} highlighted={highlight === s.ref} />
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
