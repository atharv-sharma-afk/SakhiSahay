# Roadmap: from the mid-semester MVP to the final project

Phase 1 (the MVP in this repository) is done. Each later feature lists purpose, dependencies, data, implementation,
evaluation, risks and complexity (S / M / L = roughly a few files / a subsystem / cross-cutting work).

## Phase 2 - Stabilisation and trust

| Feature | Purpose | Depends on | Data | Implementation | Evaluation | Risks | Size |
|---|---|---|---|---|---|---|---|
| JWT authentication | real multi-user isolation | - | users table (+ password hash) | `auth` router, bcrypt/argon2, `get_current_user` swap (route handlers unchanged) | pytest: cross-user 403/404; token expiry | scope creep into OAuth; keep email+password | M |
| PostgreSQL + Alembic | durable store, migrations | auth | same schema | `DATABASE_URL`, Alembic baseline, CI job with Postgres service | migration up/down in CI | SQLite-specific assumptions | M |
| Held-out evaluation set | unbiased retrieval numbers | - | 40+ new questions, second annotator | extend `eval_questions.yaml` with `split: test` | Hit@k, MRR on test split; inter-annotator agreement | annotator time | S |
| Generation evaluation | grounding and language quality | Gemini key | `answers-*.json` | rubric (grounded / partially / not), 2 raters, per language | % grounded, citation precision (cited chunk supports sentence) | subjectivity | M |
| Frontend tests | regression safety | - | - | Vitest + Testing Library for forms, calendar, AnswerCard citation rendering | CI green | - | S |
| CI | automated checks | tests | - | GitHub Actions: pytest, eval smoke on committed snapshots, typecheck, build | pass/fail | runner time for torch download (cache it) | S |
| Structured logging + error taxonomy | debuggability without leaking PHI | - | - | request ids, JSON logs, redaction tests | log review | - | S |
| Accessibility pass | WCAG AA | - | - | axe run, keyboard walkthrough, Hindi screen-reader check | zero critical axe issues | - | S |

## Phase 3 - Knowledge base and multilingual quality

| Feature | Purpose | Depends on | Data | Implementation | Evaluation | Risks | Size |
|---|---|---|---|---|---|---|---|
| Corpus expansion to ~60 sources | coverage of pregnancy, maternal care, contraception detail, adolescent health, India-specific guidance | licensing review | WHO fact sheets/Q&As, selected WHO guideline chapters, NHM/MoHFW patient material, CDC pages; ACOG only with permission | manifest entries, `doc_type` taxonomy, chapter-level extraction for long PDFs | Hit@k on expanded test split; manual relevance spot checks | boilerplate in long PDFs; drift between editions | M |
| Hindi-language sources | native Hindi passages for Hindi users | corpus | NHM Hindi booklets (e.g. maternal-health guidance in Hindi) | language-tagged chunks; retrieval filter or boost by language | Hindi Hit@k with and without native passages | OCR-quality PDFs | M |
| Embedding model comparison | choose the best model with evidence | eval set | - | run eval with `multilingual-e5-base`, `MiniLM-L12-v2`; record size/latency | table in docs | e5-base memory on laptops | S |
| Hybrid retrieval (BM25 + dense) | exact-term recall (drug names, acronyms) | corpus | - | Qdrant sparse vectors or `rank_bm25` fusion | Hit@k delta | complexity; only keep if it helps | M |
| Reranker | only if hybrid shows ranking errors | hybrid | - | small cross-encoder | MRR delta vs latency | latency on CPU | M |
| Answer self-check | detect unsupported sentences | generation eval | - | second cheap LLM pass: sentence -> supporting chunk id or "none"; flag unsupported | groundedness score | cost/latency; false positives | M |
| Query normalisation for Hinglish | better retrieval of romanised Hindi | - | small transliteration lexicon | optional LLM rewrite to English before embedding, cached | Hinglish Hit@k delta | extra call | S |

## Phase 4 - Personalisation and analytics

| Feature | Purpose | Depends on | Data | Implementation | Evaluation | Risks | Size |
|---|---|---|---|---|---|---|---|
| Consent management | lawful, revocable personalisation | auth | `consents` table (scope, granted_at, revoked_at) | settings page; API checks scope; audit entries | tests for revoked consent | over-collection | M |
| Personal context in answers | answers that reference the user's own patterns | consent | tracker summary (numbers), recent symptoms | extend prompt with structured summary; model instructed to describe, not diagnose | rubric: never diagnostic; useful | leakage into logs | M |
| Longitudinal charts | see trends | tracker | periods, symptoms | cycle-length line, symptom heat-map by cycle day; only with >= 3 cycles | usability test | misreading charts as diagnosis | M |
| Optional cycle estimate | user convenience, clearly uncertain | >= 6 cycles, evaluation | historical starts | median +/- MAD window; label "estimate"; show range not a day | backtest on logged histories: coverage of range | overconfidence; never show as fact | M |
| Export and account deletion | data rights | auth | all user tables | JSON + printable PDF summary; hard delete with cascade | tests | PDF generation deps | S |
| Reminders | adherence | auth | - | opt-in email/push; no health detail in notification text | opt-in rate | spam | S |

## Phase 5 - Doctor Connect

| Feature | Purpose | Depends on | Data | Implementation | Evaluation | Risks | Size |
|---|---|---|---|---|---|---|---|
| Clinician profiles + verification | real professionals only | auth, roles | `doctors` (registration no., specialty, languages, verification_status, documents) | admin review workflow; unverified never listed | admin test cases | fake credentials; legal review of what "verified" means | L |
| Discovery | find a suitable clinician | profiles | city, specialty, language | filters + search; no ratings until a fair policy exists | task completion in usability test | bias | M |
| Appointment requests | path to care | discovery | `appointments` (status machine: requested, proposed, confirmed, declined, cancelled) | request form, clinician inbox, notifications | state-machine tests | double booking; expectations of real-time | L |
| Optional tracker-summary share | better consultations | consent | summary snapshot with expiry | one-time share token, viewable by that clinician only | access tests | over-sharing | M |
| Secure messaging | follow-up questions | appointments | messages | per-appointment thread, server-side encryption at rest | security review | moderation, liability | L |
| Teleconsultation | remote care | messaging, legal review | - | third-party video SDK; only if compliance and support are feasible | pilot | regulatory, cost | L |

## Phase 6 - Production readiness and final submission

| Deliverable | Notes |
|---|---|
| Deployment | containerised backend + static frontend; managed PostgreSQL; Qdrant server or managed instance; HTTPS; secrets manager |
| Security review | OWASP ASVS level 1 checklist, dependency audit, rate limiting on `/api/chat`, abuse controls |
| Performance | p95 latency targets for chat (< 6 s with LLM) and tracker (< 200 ms); load test |
| Monitoring | uptime, error rate, LLM failure rate, retrieval below-gate rate; no PHI in telemetry |
| Final evaluation | held-out retrieval metrics, groundedness rubric results, safety-probe outcomes, usability study with 8-10 participants, accessibility audit |
| Documentation | SRS, architecture and DFDs, DB schema, API reference (OpenAPI export), RAG explanation, source manifest, evaluation methodology and results, security/privacy section, user guide, deployment guide, limitations, future work |
| Presentation | live demo + recorded fallback, architecture walkthrough, honest results |

## Explicit non-goals

Training or fine-tuning an LLM; diagnosing conditions from tracker data; predicting ovulation for contraception
purposes; a payments marketplace; microservices, Kafka, Kubernetes, Redis.
