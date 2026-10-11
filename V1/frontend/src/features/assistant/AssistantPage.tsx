import { useEffect, useRef, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { ArrowUp, Info, RotateCcw, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Notice } from "@/components/ui/Notice";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { ChatResponse, LanguageChoice } from "@/lib/types";
import { AnswerCard } from "./AnswerCard";

interface Turn {
  id: number;
  question: string;
  language: LanguageChoice;
  includeTracker: boolean;
  response?: ChatResponse;
  error?: string;
  pending: boolean;
}

const LANGS: { value: LanguageChoice; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "en", label: "English" },
  { value: "hi", label: "हिन्दी" },
  { value: "hinglish", label: "Hinglish" },
];

const SUGGESTIONS: Record<LanguageChoice, string[]> = {
  auto: [
    "What is a normal menstrual cycle length?",
    "PCOS ke symptoms kya hote hain?",
    "माहवारी में दर्द क्यों होता है?",
    "When should heavy periods be checked by a doctor?",
  ],
  en: [
    "What is a normal menstrual cycle length?",
    "What are common symptoms of PMS?",
    "What is endometriosis?",
    "Is bleeding during pregnancy always serious?",
  ],
  hi: ["सामान्य मासिक धर्म चक्र कितने दिनों का होता है?", "PCOS क्या है?", "रजोनिवृत्ति के दौरान क्या बदलाव आते हैं?", "गर्भावस्था में खून आना कितना गंभीर है?"],
  hinglish: ["Periods mein itna dard kyun hota hai?", "Heavy bleeding kab doctor ko dikhani chahiye?", "Irregular periods ki wajah kya ho sakti hai?", "PMS mein mood swings normal hain kya?"],
};

const LANG_ATTR: Record<string, string> = { en: "en", hi: "hi", hinglish: "en" };

export function AssistantPage() {
  const [params] = useSearchParams();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [language, setLanguage] = useState<LanguageChoice>("auto");
  const [includeTracker, setIncludeTracker] = useState(false);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const idRef = useRef(0);

  const { data: health } = useQuery({ queryKey: ["health"], queryFn: api.health, retry: 1 });
  const { data: summary } = useQuery({ queryKey: ["tracker", "summary"], queryFn: api.summary, retry: 1 });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, turns.map((t) => t.pending).join()]);

  // Deep links such as /assistant?q=... (used by dashboard suggestion chips) ask immediately.
  const autoAsked = useRef(false);
  useEffect(() => {
    const q = params.get("q");
    if (q && !autoAsked.current) {
      autoAsked.current = true;
      ask(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(turn: Turn) {
    try {
      const response = await api.chat(turn.question, turn.language, turn.includeTracker);
      setTurns((ts) => ts.map((t) => (t.id === turn.id ? { ...t, response, pending: false, error: undefined } : t)));
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      setTurns((ts) => ts.map((t) => (t.id === turn.id ? { ...t, pending: false, error: message } : t)));
    }
  }

  function ask(question: string) {
    const q = question.trim();
    if (q.length < 3) return;
    const turn: Turn = { id: ++idRef.current, question: q, language, includeTracker, pending: true };
    setTurns((ts) => [...ts, turn]);
    setInput("");
    void run(turn);
  }

  function retry(turn: Turn) {
    setTurns((ts) => ts.map((t) => (t.id === turn.id ? { ...t, pending: true, error: undefined } : t)));
    void run(turn);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    ask(input);
  }

  const busy = turns.some((t) => t.pending);
  const indexMissing = health && !health.knowledge.index_ready;

  return (
    <div className="flex min-h-[calc(100dvh-9rem)] flex-col">
      <PageHeader
        eyebrow="Ask · Understand"
        title="Your health questions, answered from trusted sources"
        description="Every answer is built only from retrieved passages of WHO, NHS, CDC and Government of India material, and shows exactly which passages it used."
      />

      {indexMissing && (
        <Notice tone="advisory" title="Knowledge index not built yet" className="mb-4">
          Run <code className="rounded bg-white px-1">python -m app.knowledge.ingest</code> in the backend folder, then restart the API.
        </Notice>
      )}

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-ivory-300 bg-white px-3 py-2.5 shadow-soft">
        <div role="radiogroup" aria-label="Answer language" className="flex rounded-xl bg-ivory-100 p-1">
          {LANGS.map((l) => (
            <button
              key={l.value}
              type="button"
              role="radio"
              aria-checked={language === l.value}
              onClick={() => setLanguage(l.value)}
              lang={l.value === "hi" ? "hi" : undefined}
              className={cn("rounded-lg px-3 py-1.5 text-sm font-medium transition-colors", language === l.value ? "bg-white text-plum-800 shadow-soft" : "text-ink-500 hover:text-ink-900")}
            >
              {l.label}
            </button>
          ))}
        </div>
        <label className="ml-auto flex cursor-pointer items-center gap-2 text-sm text-ink-700">
          <input
            type="checkbox"
            className="size-4 accent-plum-700"
            checked={includeTracker}
            disabled={!summary || summary.period_count === 0}
            onChange={(e) => setIncludeTracker(e.target.checked)}
          />
          <span>Use my tracker summary</span>
          <span className="group relative inline-flex">
            <Info className="size-4 text-ink-400" aria-hidden />
            <span role="tooltip" className="pointer-events-none absolute right-0 top-6 z-10 hidden w-64 rounded-xl border border-ivory-300 bg-white p-3 text-xs leading-relaxed text-ink-700 shadow-lift group-hover:block group-focus-within:block">
              Optional, per question. Only counts and cycle lengths from your own records are shared with the model - never your notes. Nothing is stored. {summary && summary.period_count === 0 ? "Log a period first to enable this." : ""}
            </span>
          </span>
        </label>
      </div>

      <div className="flex-1 space-y-6 py-6">
        {turns.length === 0 && (
          <div className="animate-rise mx-auto max-w-2xl text-center">
            <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-3xl bg-plum-100 text-plum-700">
              <Sparkles className="size-6" aria-hidden />
            </div>
            <h2 className="text-xl font-semibold text-ink-900">Namaste. What would you like to understand today?</h2>
            <p className="mt-2 text-sm text-ink-500">Ask in English, Hindi or Hinglish. Try one of these:</p>
            <div className="mt-5 grid gap-2 sm:grid-cols-2">
              {SUGGESTIONS[language].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => ask(s)}
                  className="rounded-2xl border border-ivory-300 bg-white px-4 py-3 text-left text-sm text-ink-700 shadow-soft transition-colors hover:border-plum-300 hover:text-plum-800"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((turn) => (
          <article key={turn.id} className="animate-rise space-y-3" aria-busy={turn.pending}>
            <div className="flex justify-end">
              <p className="max-w-[85%] rounded-3xl rounded-br-lg bg-plum-700 px-5 py-3 text-[0.95rem] leading-relaxed text-white shadow-soft sm:max-w-[70%]">{turn.question}</p>
            </div>
            <div className="max-w-full lg:max-w-[88%]">
              {turn.pending && (
                <div className="card inline-flex items-center gap-3 px-5 py-4 text-sm text-ink-500" role="status">
                  <span className="flex gap-1" aria-hidden>
                    <span className="typing-dot size-2 rounded-full bg-plum-400" />
                    <span className="typing-dot size-2 rounded-full bg-plum-400" />
                    <span className="typing-dot size-2 rounded-full bg-plum-400" />
                  </span>
                  Searching sources and composing an answer...
                </div>
              )}
              {turn.error && (
                <Notice tone="advisory" title="Could not get an answer">
                  <p>{turn.error}</p>
                  <Button variant="secondary" size="sm" className="mt-2" onClick={() => retry(turn)}>
                    <RotateCcw className="size-3.5" aria-hidden /> Retry
                  </Button>
                </Notice>
              )}
              {turn.response && <AnswerCard response={turn.response} lang={LANG_ATTR[turn.response.language_used]} />}
            </div>
          </article>
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={onSubmit} className="sticky bottom-20 z-30 lg:bottom-4">
        <div className="flex items-end gap-2 rounded-3xl border border-ivory-300 bg-white p-2 shadow-lift">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                ask(input);
              }
            }}
            rows={1}
            maxLength={1000}
            placeholder="Ask about periods, PCOS, pregnancy, menopause... (Enter to send, Shift+Enter for a new line)"
            aria-label="Your question"
            className="max-h-40 min-h-11 flex-1 resize-none bg-transparent px-3 py-2.5 text-[0.95rem] text-ink-900 placeholder:text-ink-300 focus:outline-none"
          />
          <Button type="submit" size="md" disabled={busy || input.trim().length < 3} aria-label="Send question" className="h-11 w-11 rounded-2xl px-0">
            <ArrowUp className="size-5" aria-hidden />
          </Button>
        </div>
        <p className="mt-2 px-2 text-center text-[0.7rem] leading-relaxed text-ink-400">
          Educational information only, from cited public sources. Not a diagnosis. In an emergency contact local emergency services.
        </p>
      </form>
    </div>
  );
}
