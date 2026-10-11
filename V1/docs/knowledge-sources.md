# Knowledge sources, research notes and verification status

## 1. Curated corpus (19 sources, all URLs fetched successfully on 2026-10-11)

Canonical manifest: [`backend/data/knowledge/sources.yaml`](../backend/data/knowledge/sources.yaml).
Per-source extraction reports: `backend/data/knowledge/cache/<id>.meta.json` (method, page date hint, char count,
warnings). The API exposes the same registry at `/api/knowledge/sources` and the UI shows it on the Sources page.

| Publisher | Documents | Type | Status |
|-----------|-----------|------|--------|
| World Health Organization | Menstrual health; Endometriosis; PCOS; Menopause; Adolescent pregnancy; Comprehensive sexuality education; Maternal mortality; Family planning/contraception; Infertility (fact sheets) | fact_sheet | indexed |
| NHS (UK) | Periods overview; Period problems; Heavy periods; Period pain; Irregular periods; PMS; Vaginal bleeding in pregnancy; Ectopic pregnancy | patient_education | indexed |
| US CDC | About STIs and Pregnancy | patient_education | indexed |
| NHM / MoHFW (India) | Menstrual Hygiene Policy for School-Going Girls (Nov 2024, PDF) | policy_document | indexed from a text snapshot (see note) |

Note on the NHM PDF: `nhm.gov.in` timed out from the build machine, so the ingestion run recorded the source as
`failed` (the failure path works). The PDF text was then captured through an external fetch and registered as a
snapshot with that fact written into its `.meta.json`. Running
`python -m app.knowledge.ingest --refresh --only nhm-menstrual-hygiene-policy-2024` from a machine that can reach
the site replaces it with a direct PyMuPDF extraction.

### Verified vs. requiring further investigation

Verified in this iteration (fetched, extracted, reviewed by eye):
- All 18 HTML pages above; NHS pages include "Page last reviewed" dates in the snapshot.
- WHO copyright policy: WHO publications are CC BY-NC-SA 3.0 IGO; WHO permits linking to pages; the WHO emblem may
  not be used; links must not imply endorsement. SakhiSahay links to full pages and shows attribution.
- Gemini API: model id `gemini-3.8-flash` (stable), keys via `GEMINI_API_KEY`, SDK `google-genai`, 429/5xx retry
  guidance.
- Embedding models: `intfloat/multilingual-e5-small` (MIT, 384-d, needs `query:`/`passage:` prefixes);
  `paraphrase-multilingual-MiniLM-L12-v2` (Apache-2.0, 384-d, 128-token window - shorter, which matters for chunks).

Requires further investigation before the final submission:
- Exact NHS reuse terms for website content (most NHS content is under the Open Government Licence v3.0 but the NHS
  website also offers a syndication route) - confirm and record in the manifest.
- Government of India copyright/reuse terms for NHM PDFs (typically permitted with attribution; confirm).
- ACOG patient FAQs (Painful Periods, Heavy Menstrual Bleeding, PCOS, Endometriosis, The Menopause Years) are
  excellent but copyrighted; include only if ACOG permission or a quoting policy is established. Currently **not
  ingested**.
- ICMR Standard Treatment Workflow "Heavy Menstrual Bleeding" is clinician-facing with drug dosing; **excluded** from
  the patient-facing assistant on purpose. Could support a future clinician-mode behind role-based access.
- WHO guidelines (e.g. "WHO recommendations on maternal health, 2nd ed., 2025", 198 pages) are policy/programme
  documents; consider selected chapters with careful chunking in Phase 3.
- WHO Global Health Observatory indicators (statistical datasets) are **not** suitable as personal guidance; a
  possible later use is a transparent "context" panel (e.g. national indicators), never as an answer source.

## 2. Ingestion metadata recorded per chunk

`source_id, title, publisher, url, doc_type, topic, section, language, published_date, updated_date (page date
hint when the publisher exposes it), accessed_date, license_note, chunk_id, text`. Extraction failures and documents
below a minimum length are recorded as `failed` with a reason in `knowledge_sources.status_detail` - nothing is
silently skipped.

## 3. Tracker research (Module B)

### Competitor feature comparison

| Feature | Flo (verified: product tour, help centre, privacy policy) | Clue (verified: help article, privacy policy) | SakhiSahay MVP | SakhiSahay later |
|---------|------|------|------|------|
| Period logging + calendar | Yes | Yes | Yes (recorded dates only) | + estimates, clearly labelled |
| Cycle predictions | Yes (period, ovulation, fertile days; asks for >= 3 cycles) | Yes (advanced 12-month predictions in Clue Plus) | **No** (deliberately) | Phase 4, after evaluation, with uncertainty |
| Symptom tracking | 70-80+ symptoms and events | 200+ experiences, unlimited custom tags (Plus) | 15-item configurable catalogue + severity | custom tags, more categories |
| Flow / pain / mood | Yes | Yes | flow optional; cramps/pain, mood in catalogue | richer scales |
| Insights / content | daily insights co-created with experts; health assistant chat | cycle statistics, analysis tab, content tab | descriptive insights with basis shown; RAG assistant with citations | longitudinal charts, exports |
| Privacy | Anonymous Mode; says it does not sell personal data; may share non-health technical data with partners with consent | health data processed only when tracked; EU storage; no health data shared with Google or wearable partners | local single-user DB; no third parties; per-request consent for personalisation; delete-all | auth, consent records, export, retention policy |
| Doctor access | self-assessment to share with a doctor | history "helpful for conversations" | preview only | Phase 5 |

Observed usability patterns worth adopting: ask for a few cycles before showing statistics; mark predictions
distinctly from records; one-tap daily logging; symptom grouping. Patterns deliberately not copied: proprietary
visuals, branding, content library.

### Medical reference rules used by the tracker (general information, cited in the UI)

- NHS: cycles usually every 21-35 days, average 28; periods last 2-7 days, average 5; irregular if gap < 21 or > 35
  days; see a GP if periods last more than 7 days, are heavy enough to affect life, or if there is bleeding between
  periods or after sex.
- NHS: heavy periods include changing a pad/tampon every 1-2 hours, clots larger than about 2.5 cm, bleeding through
  clothes; urgent help if feeling faint or very short of breath.
- NHS: urgent GP/111 if period pain is severe or worse than usual and painkillers have not helped.
- WHO menstrual health fact sheet: unpredictable, very painful, heavy bleeding or disruptive mood changes "could
  suggest an underlying condition" and "deserve to be heard and evaluated by health and care workers".

What the tracker does **not** assume: a 28-day cycle, day-14 ovulation, or that any logged pattern indicates a
condition. Guidance notes are shown only when the user's own recorded numbers leave the published ranges, and always
with the words "general information, not an assessment of you".

## 4. Multilingual approach

No translation API. The user's language choice (or detection) steers (a) the per-language relevance gate and
(b) the response-language instruction in the prompt. The multilingual embedding model retrieves English passages for
Hindi/Hinglish queries (6/6 and 7/7 top-6 hits on the dev set). Known limits: Hinglish detection is a marker-word
heuristic; Devanagari answers depend on the LLM; medical terms may be inconsistent across answers.
