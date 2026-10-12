# Mid-semester demonstration script

Target length: 10-12 minutes. Everything below runs on one laptop with two terminals.

## Before the day (checklist)

1. `cp .env.example backend/.env` and set `GEMINI_API_KEY`. Test with one question; confirm the Assistant status pill
   reads "Assistant live · gemini-3.8-flash".
2. `python -m app.knowledge.ingest --offline` (index from committed snapshots; no network needed).
3. `python -m evaluation.run_retrieval_eval --with-answers` - read every answer in `docs/evaluation/answers-*.json`,
   fill in the safety checklist in `docs/evaluation/README.md`, and keep the file open for the viva.
4. Log realistic records for the demo account (3-5 periods with end dates, a handful of symptoms) **or** start empty
   and log live - decide one; empty-first is more convincing if time allows.
5. Pre-open: dashboard, `/docs` (OpenAPI), the eval markdown, and the screenshots folder as the offline fallback.
6. Turn off laptop sleep; set the browser to 110% zoom for projectors.

## Sequence

| # | Step | Say |
|---|------|-----|
| 1 | Dashboard | "SakhiSahay: ask, understand, track, analyse, escalate, consult - in one calm product. Status pill shows the live model and 19 cited sources." |
| 2 | Sources page | "The assistant can cite only these documents. Each shows access date, licence note and passage count. This is the whole universe of claims." |
| 3 | Assistant, English | Ask "What counts as a heavy period?" Point at: live badge, evidence-strength chip, citation chips, open a source, click "Open original source". |
| 4 | Assistant, Hinglish | Ask "PCOS ke symptoms kya hote hain?" Show detected language and Hinglish answer. |
| 5 | Assistant, Hindi | Ask "माहवारी में दर्द क्यों होता है?" Show Devanagari rendering. |
| 6 | Safety | Ask "I am soaking a pad every hour and feel faint" - red urgent notice with NHS link appears regardless of the model. |
| 7 | Refusal | Ask "How do I fix a flat tyre on my scooter?" - "Not covered by sources", no fabrication. |
| 8 | Tracker | Log a period (start + end), log "cramps, moderate" today. Refresh: records persist; calendar fills; history lists them with edit/delete. |
| 9 | Insights | Show the cycle-length insight, open "How this was calculated". Show the "What unlocks more" list - no fake insights. |
| 10 | Consent toggle | Back in Assistant, tick "Use my tracker summary", ask "Is my cycle length normal?" - badge "Used your tracker summary"; explain only numbers are shared. |
| 11 | Doctor Connect | Open preview; click "Preview appointment request"; stress the demonstration labels and the Phase 5 plan. |
| 12 | Architecture | One slide from `docs/architecture.md` (flowchart + sequence). Mention tests (25 passing) and the retrieval table (Hit@6 33/33 on the dev set, with its caveat). |
| 13 | Limitations | No auth yet, keyword safety, dev-set-calibrated gates, small corpus, no prediction. Then the roadmap. |

## Fallbacks

| Failure | What happens automatically | What you do |
|---------|---------------------------|-------------|
| Gemini key rejected / quota / network down | Response switches to **"Retrieved passages only (no model)"** with the reason shown; citations still real | Say so plainly; show that the passages are verbatim source text; continue with tracker |
| Projector cannot reach backend | - | `docs/screenshots/` has every screen; `answers-*.json` has real transcripts |
| Embedding model cache missing | API returns 503 for chat with a clear message | Re-run ingest (downloads once); keep the model cache folder on the laptop |
| Qdrant lock error | - | Make sure the eval script is not running while the API runs |

Never present a retrieval-only or screenshot fallback as a live model answer; the badge in the UI makes the mode
explicit and the examiners will respect that.

## Likely viva questions and short answers

- *Why RAG instead of fine-tuning?* Verifiability and freshness: every claim maps to a retrievable, dated source; fine-tuning hides provenance and needs data we do not have.
- *How do you stop hallucinated citations?* The model can only emit `[S#]` markers for passages it was shown; markers outside that range and unknown URLs are stripped server-side; the source list comes from the retriever, not the model.
- *Why per-language thresholds?* Cosine scores from e5 are compressed and cross-lingual pairs score ~0.05 lower; a single gate either rejects Hindi questions or admits off-topic English ones. Calibrated on the dev set - stated as a limitation.
- *Is this diagnosing?* No: the prompt forbids it, the safety layer labels diagnosis requests, and insights are descriptive statistics with their basis shown.
- *Where is personal data?* Relational DB only, per user, never in the vector store; shared with the model only as numbers, only when the user ticks the box for that question.
