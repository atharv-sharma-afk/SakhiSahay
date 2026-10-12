# Retrieval evaluation - multilingual-e5-small

Generated 2026-10-11 10:28 UTC by `evaluation/run_retrieval_eval.py`. Embedding model: `intfloat/multilingual-e5-small`; top_k=6; relevance gates en=0.83, hi=0.78, hinglish=0.8 (calibrated on this very question set, so the gating numbers below are optimistic).

## Summary

- Questions with an expected source: 33
- Hit@6 (source level): 33/33 (100%)
- MRR: 0.896
- English: 20/20 (100%) | Hindi: 6/6 (100%) | Hinglish: 7/7 (100%)
- Out-of-scope questions correctly below the gate: 2/3
- Median retrieval latency (embed + search, CPU): 9 ms

Limits: 37 hand-written questions, one expected-source label per question written by the team, source-level matching (a chunk from the right page counts even if it is not the ideal paragraph). These numbers describe this corpus and question set only.

## Per-question results

| id | lang | detected | category | best score | gate | passed | hit rank | top sources |
|----|------|----------|----------|-----------:|-----:|:------:|:--------:|-------------|
| en-01 | en | en | educational | 0.889 | 0.83 | yes | 1 | nhs-period-problems, who-menstrual-health, nhs-irregular-periods |
| en-02 | en | en | educational | 0.92 | 0.83 | yes | 1 | nhs-period-problems, nhs-periods-overview, nhs-irregular-periods |
| en-03 | en | en | educational | 0.914 | 0.83 | yes | 1 | nhs-pms, nhs-period-problems, nhs-periods-overview |
| en-04 | en | en | educational | 0.93 | 0.83 | yes | 2 | nhs-period-problems, who-endometriosis, who-menstrual-health |
| en-05 | en | en | educational | 0.918 | 0.83 | yes | 1 | who-pcos, who-menstrual-health, nhs-irregular-periods |
| en-06 | en | en | educational | 0.875 | 0.83 | yes | 1 | nhs-heavy-periods, nhs-period-problems, nhs-periods-overview |
| en-07 | en | en | educational | 0.906 | 0.83 | yes | 1 | nhs-period-pain, nhs-periods-overview, nhs-period-problems |
| en-08 | en | en | educational | 0.892 | 0.83 | yes | 1 | who-menopause, nhs-periods-overview, nhs-period-pain |
| en-09 | en | en | educational | 0.892 | 0.83 | yes | 1 | who-adolescent-pregnancy, who-maternal-mortality, who-comprehensive-sexuality-education |
| en-10 | en | en | educational | 0.888 | 0.83 | yes | 1 | nhs-vaginal-bleeding-pregnancy, who-maternal-mortality, cdc-stis-and-pregnancy |
| en-11 | en | en | educational | 0.92 | 0.83 | yes | 1 | nhs-ectopic-pregnancy, nhs-vaginal-bleeding-pregnancy, who-maternal-mortality |
| en-12 | en | en | educational | 0.915 | 0.83 | yes | 1 | cdc-stis-and-pregnancy, nhs-ectopic-pregnancy, who-menopause |
| en-13 | en | en | educational | 0.917 | 0.83 | yes | 1 | nhs-irregular-periods, who-pcos, nhs-period-problems |
| en-14 | en | en | educational | 0.896 | 0.83 | yes | 1 | who-menstrual-health, who-endometriosis, who-pcos |
| en-15 | en | en | educational | 0.883 | 0.83 | yes | 1 | who-maternal-mortality, who-infertility, who-menstrual-health |
| en-16 | en | en | educational | 0.893 | 0.83 | yes | 1 | who-family-planning-contraception, who-pcos, who-endometriosis |
| en-17 | en | en | educational | 0.904 | 0.83 | yes | 1 | nhm-menstrual-hygiene-policy-2024 |
| hi-01 | hi | hi | educational | 0.842 | 0.78 | yes | 1 | nhs-period-problems, who-menstrual-health, nhs-irregular-periods |
| hi-02 | hi | hi | educational | 0.893 | 0.78 | yes | 1 | who-pcos, nhs-irregular-periods, who-menstrual-health |
| hi-03 | hi | hi | educational | 0.845 | 0.78 | yes | 1 | nhs-period-pain, nhs-period-problems, nhs-heavy-periods |
| hi-04 | hi | hi | educational | 0.822 | 0.78 | yes | 1 | who-endometriosis, nhs-period-problems, who-menstrual-health |
| hi-05 | hi | hi | educational | 0.802 | 0.78 | yes | 1 | who-menopause, who-endometriosis, nhs-periods-overview |
| hi-06 | hi | hi | educational | 0.845 | 0.78 | yes | 1 | nhs-vaginal-bleeding-pregnancy, who-maternal-mortality, nhs-ectopic-pregnancy |
| hing-01 | hinglish | hinglish | educational | 0.837 | 0.8 | yes | 3 | nhs-periods-overview, who-menstrual-health, nhs-period-problems |
| hing-02 | hinglish | hinglish | educational | 0.85 | 0.8 | yes | 2 | who-menstrual-health, nhs-heavy-periods, nhs-period-problems |
| hing-03 | hinglish | hinglish | educational | 0.895 | 0.8 | yes | 1 | who-pcos, nhs-pms, who-menopause |
| hing-04 | hinglish | hinglish | educational | 0.854 | 0.8 | yes | 1 | nhs-irregular-periods, nhs-period-problems, who-pcos |
| hing-05 | hinglish | hinglish | educational | 0.867 | 0.8 | yes | 1 | nhs-pms, nhs-period-problems, who-menopause |
| hing-06 | hinglish | hinglish | educational | 0.858 | 0.8 | yes | 1 | who-menopause, nhs-periods-overview, who-menstrual-health |
| safe-01 | en | en | diagnosis | 0.915 | 0.83 | yes | 1 | who-pcos, nhs-irregular-periods, nhs-periods-overview |
| safe-02 | en | en | severe | 0.87 | 0.83 | yes | 4 | nhs-vaginal-bleeding-pregnancy, nhs-period-problems, nhs-ectopic-pregnancy |
| safe-03 | en | en | medication | 0.868 | 0.83 | yes | 2 | nhs-period-problems, nhs-period-pain, nhs-irregular-periods |
| safe-04 | hinglish | hinglish | severe | 0.822 | 0.8 | yes | 2 | who-menstrual-health, nhs-vaginal-bleeding-pregnancy, nhm-menstrual-hygiene-policy-2024 |
| safe-05 | en | en | fabrication | 0.875 | 0.83 | yes | - | nhm-menstrual-hygiene-policy-2024, who-menstrual-health, who-maternal-mortality |
| safe-06 | en | en | insufficient | 0.824 | 0.83 | no | - | who-menstrual-health, who-infertility |
| safe-07 | en | en | insufficient | 0.796 | 0.83 | no | - | nhs-ectopic-pregnancy, nhs-period-pain |
