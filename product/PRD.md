# GamePulse product requirements and decision record

## User problem and audience
A small game studio can see daily activity without knowing whether new players return, which onboarding step loses them, or whether a churn score was trained on future information. Target users are a creator/PM and an analyst at an early-stage game team. These are proposed personas; no interviews were conducted.

## Goal and delivered scope
Provide an auditable local retention workflow before recommending an experiment. Delivered: seeded telemetry, whole-file CSV validation, transactional SQLite ingestion, mature D1/D7/D30 cohorts, ordered first-week funnel, platform filter, session-end quality reporting, acquisition/feature summaries, temporal logistic baseline, and scenario comparison labeled as an assumption. Custom ingestion is CLI-based; dashboard configuration remains tailored to the demo window. Production incremental ingestion is outside this release.

## Acceptance criteria
- Duplicate IDs, invalid UTC timestamps, inconsistent player dimensions, missing session starts, cross-player/game session IDs, events before install or after session end reject the input before database replacement.
- Retention excludes cohorts lacking a complete target UTC calendar day; aggregation sums players, not unweighted cohort percentages.
- Funnel counts each player once per ordered step. Missing ends never become zero-minute sessions.
- Feature days 0–6 are separated from label days 7–20; player groups are disjoint; training labels finish before the first test install; preprocessing fits only training rows.
- Platform selection changes analytics; UI explicitly says the model is global.

## Prioritization
Planning score = impact × confidence / effort. Impact 1–3; confidence is subjective; effort is relative engineering units, not measured hours.

| Feature | Impact | Confidence | Effort | Score | Status |
|---|---:|---:|---:|---:|---|
| Correct mature retention | 3 | .95 | 2 | 1.425 | Delivered |
| Validation + session quality | 3 | .9 | 2 | 1.35 | Delivered |
| Temporal interpretable baseline | 2 | .8 | 3 | .533 | Delivered |
| Custom-data dashboard setup | 2 | .6 | 3 | .4 | Deferred |
| Live developer-authorized telemetry | 3 | .4 | 6 | .2 | Unstarted |

## KPIs and measurement
Technical release gates: invalid fixture rejection / invalid fixtures; correct hand-checked calculations / reference cases; zero user overlap; exact independent feature parity. Model ROC-AUC and AP are holdout discrimination measures, not retention improvement. Product KPI for a future real trial: mature D7 returned installs / eligible installs. Secondary KPI: ordered first-match converters / fully observed installs. Guardrails: crash sessions / all sessions, invitation opt-out rate, help requests and consented satisfaction ratings. Define observation cutoff before querying.

## Proposed experiment
Test a shorter tutorial against the current version in one developer-controlled game after authorization. Assign a stable user-level treatment at installation; analyze intention-to-treat. Primary metric: mature D7 retention. Guardrails: first-match comprehension, crash rate, excessive session pressure. Pre-register duration, exclusion rules and sample size using a real baseline and a business-meaningful minimum effect; no sample size or uplift is claimed now. Account for repeated testing and concurrent game updates.

## Recommendation and next decision
Prioritize tutorial comprehension and telemetry quality before sending churn interventions. A high synthetic AUC does not justify targeting real players. Approve a real trial only after consent, schema stability and an out-of-time real-data baseline. The dashboard's +3-point scenario is purely hypothetical. See DATA_DICTIONARY.md and DECISION_BRIEF.md.

## Planned usability tasks
Find a cohort too young for D30; explain its blank value; trace one funnel; identify missing session-end handling; explain one false positive. Record task completion and comprehension with consenting participants. None of these human sessions has been run.
