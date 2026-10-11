"""Retrieval evaluation against the curated question set.

    .venv/bin/python -m evaluation.run_retrieval_eval                 # retrieval metrics only
    .venv/bin/python -m evaluation.run_retrieval_eval --with-answers  # also run the full pipeline

Metrics (defined honestly, with their limits):
  * Hit@k  - fraction of questions whose expected source appears in the top-k results
             (k = RETRIEVAL_TOP_K). Judged at source level, not chunk level.
  * MRR    - mean reciprocal rank of the first expected source.
  * Gate   - whether the best score cleared RETRIEVAL_MIN_SCORE (used for
             insufficient-evidence questions, where "below gate" is the correct outcome).
Results are written to docs/evaluation/ so the report quotes real numbers.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.config import BACKEND_DIR, get_settings
from app.rag.language import detect_language
from app.rag.retriever import retrieve

EVAL_DIR = Path(__file__).resolve().parent
DOCS_DIR = BACKEND_DIR.parent / "docs" / "evaluation"


def run(with_answers: bool) -> None:
    settings = get_settings()
    data = yaml.safe_load((EVAL_DIR / "eval_questions.yaml").read_text(encoding="utf-8"))
    questions = data["questions"]
    rows = []
    latencies = []
    for q in questions:
        started = time.perf_counter()
        detected = detect_language(q["question"])
        result = retrieve(q["question"], language=detected)
        latencies.append((time.perf_counter() - started) * 1000)
        ranked_sources: list[str] = []
        for chunk in [*result.chunks, *result.weak]:
            if chunk.payload.source_id not in ranked_sources:
                ranked_sources.append(chunk.payload.source_id)
        expected = set(q.get("expected_sources") or [])
        hit_rank = next((i + 1 for i, s in enumerate(ranked_sources) if s in expected), None)
        above_gate = bool(result.chunks)
        rows.append(
            {
                "id": q["id"],
                "language": q["language"],
                "category": q["category"],
                "question": q["question"],
                "expected": sorted(expected),
                "top_sources": ranked_sources[: settings.retrieval_top_k],
                "best_score": round(result.best_score, 3) if result.best_score is not None else None,
                "detected_language": detected,
                "gate": result.min_score,
                "above_gate": above_gate,
                "hit_rank": hit_rank,
            }
        )

    graded = [r for r in rows if r["expected"]]
    hits = [r for r in graded if r["hit_rank"] is not None]
    mrr = statistics.mean([1 / r["hit_rank"] if r["hit_rank"] else 0 for r in graded]) if graded else 0
    insufficient = [r for r in rows if r["category"] in ("insufficient", "fabrication")]
    correctly_gated = [r for r in insufficient if not r["above_gate"]]

    def by_lang(lang: str) -> str:
        subset = [r for r in graded if r["language"] == lang]
        if not subset:
            return "n/a"
        h = sum(1 for r in subset if r["hit_rank"] is not None)
        return f"{h}/{len(subset)} ({100 * h / len(subset):.0f}%)"

    answers = []
    if with_answers:
        from app.rag.pipeline import answer_question

        for q in questions:
            response = answer_question(q["question"], "auto")
            answers.append(
                {
                    "id": q["id"],
                    "category": q["category"],
                    "question": q["question"],
                    "mode": response.mode,
                    "language_used": response.language_used,
                    "safety_level": response.safety.level,
                    "cited_sources": [s.source_id for s in response.sources if s.cited],
                    "latency_ms": response.latency_ms,
                    "answer": response.answer,
                    "fallback_reason": response.fallback_reason,
                }
            )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    model_slug = settings.embedding_model.split("/")[-1]
    md = [
        f"# Retrieval evaluation - {model_slug}",
        "",
        f"Generated {stamp} by `evaluation/run_retrieval_eval.py`. Embedding model: `{settings.embedding_model}`; "
        f"top_k={settings.retrieval_top_k}; relevance gates en={settings.retrieval_min_score}, "
        f"hi={settings.retrieval_min_score_hi}, hinglish={settings.retrieval_min_score_hinglish} "
        "(calibrated on this very question set, so the gating numbers below are optimistic).",
        "",
        "## Summary",
        "",
        f"- Questions with an expected source: {len(graded)}",
        f"- Hit@{settings.retrieval_top_k} (source level): {len(hits)}/{len(graded)} ({100 * len(hits) / max(len(graded), 1):.0f}%)",
        f"- MRR: {mrr:.3f}",
        f"- English: {by_lang('en')} | Hindi: {by_lang('hi')} | Hinglish: {by_lang('hinglish')}",
        f"- Out-of-scope questions correctly below the gate: {len(correctly_gated)}/{len(insufficient)}",
        f"- Median retrieval latency (embed + search, CPU): {statistics.median(latencies):.0f} ms",
        "",
        "Limits: 37 hand-written questions, one expected-source label per question written by the team, "
        "source-level matching (a chunk from the right page counts even if it is not the ideal paragraph). "
        "These numbers describe this corpus and question set only.",
        "",
        "## Per-question results",
        "",
        "| id | lang | detected | category | best score | gate | passed | hit rank | top sources |",
        "|----|------|----------|----------|-----------:|-----:|:------:|:--------:|-------------|",
    ]
    for r in rows:
        md.append(
            f"| {r['id']} | {r['language']} | {r['detected_language']} | {r['category']} | {r['best_score']} | {r['gate']} | "
            f"{'yes' if r['above_gate'] else 'no'} | {r['hit_rank'] or '-'} | {', '.join(r['top_sources'][:3])} |"
        )
    (DOCS_DIR / f"retrieval-{model_slug}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (DOCS_DIR / f"retrieval-{model_slug}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    if answers:
        (DOCS_DIR / f"answers-{model_slug}.json").write_text(json.dumps(answers, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(md[:12]))
    print(f"\nwritten to {DOCS_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-answers", action="store_true")
    args = parser.parse_args()
    run(args.with_answers)
