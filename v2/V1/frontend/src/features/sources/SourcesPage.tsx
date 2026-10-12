import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";

const STEPS = [
  ["Your question", "Language detected (English / Hindi / Hinglish); urgent phrases screened."],
  ["Semantic search", "The question is embedded with a multilingual model and matched against indexed passages."],
  ["Relevance gate", "If nothing scores above the threshold the assistant says the sources do not cover it."],
  ["Grounded answer", "Gemini writes only from the retrieved passages, in your language, citing [S#]."],
  ["Citation check", "Markers that do not map to a retrieved passage are removed; links are verified."],
];

export function SourcesPage() {
  const { data, isLoading } = useQuery({ queryKey: ["knowledge", "sources"], queryFn: api.knowledgeSources });
  const grouped = (data ?? []).reduce<Record<string, typeof data>>((acc, s) => {
    (acc[s.publisher] ??= []).push(s);
    return acc;
  }, {});

  return (
    <div>
      <PageHeader eyebrow="Transparency" title="Where answers come from" description="The complete list of documents the assistant can cite, with how each was obtained. It cannot cite anything that is not on this page." />

      <Card className="mb-6">
        <CardHeader eyebrow="How an answer is built" title="Retrieval-augmented generation, step by step" />
        <ol className="grid gap-3 md:grid-cols-5">
          {STEPS.map(([title, text], i) => (
            <li key={title} className="rounded-2xl bg-ivory-50 p-4">
              <span className="flex size-7 items-center justify-center rounded-full bg-plum-700 text-xs font-semibold text-white">{i + 1}</span>
              <p className="mt-2 font-sans text-sm font-semibold text-ink-900">{title}</p>
              <p className="mt-1 text-xs leading-relaxed text-ink-500">{text}</p>
            </li>
          ))}
        </ol>
      </Card>

      {isLoading && <Skeleton className="h-64" />}
      {Object.entries(grouped).map(([publisher, sources]) => (
        <section key={publisher} className="mb-8">
          <h2 className="mb-3 text-xl font-semibold text-ink-900">{publisher}</h2>
          <ul className="grid gap-3 md:grid-cols-2">
            {sources!.map((s) => (
              <li key={s.id} className="card p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="plum">{s.doc_type.replace("_", " ")}</Badge>
                  <Badge tone="neutral">{s.topic.replace("_", " ")}</Badge>
                  <Badge tone={s.status === "indexed" ? "sage" : "danger"}>{s.status === "indexed" ? `${s.chunk_count} passages` : s.status}</Badge>
                </div>
                <p className="mt-2 font-sans text-sm font-semibold text-ink-900">{s.title}</p>
                <p className="mt-1 text-xs text-ink-500">
                  {s.updated_date ? `Page date ${s.updated_date} · ` : ""}Accessed {s.accessed_date ?? "-"}
                </p>
                {s.license_note && <p className="mt-2 text-xs leading-relaxed text-ink-500">{s.license_note}</p>}
                <a href={s.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-plum-700 underline decoration-plum-300 underline-offset-2">
                  Open source <ExternalLink className="size-3.5" aria-hidden />
                </a>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
