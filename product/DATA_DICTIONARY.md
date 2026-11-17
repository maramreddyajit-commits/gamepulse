# Telemetry contract
All shipped records are generated, fictional data. Seed 20261117. Observation window: 2026-07-20 00:00 UTC through 2026-11-17 00:00 UTC, exclusive. Calendar-day rather than rolling-24-hour retention.

| Column | Type / rule |
|---|---|
| event_id | Nonempty globally unique string; duplicate ingestion is rejected |
| player_id | Synthetic pseudonymous string; consistent dimensions per player |
| event_name | install, session_start, tutorial_complete, match_complete, social_use, shop_view, session_end |
| game_id | Nonempty string, demo_arena in fixtures |
| session_id | Required except install; one player, one start, at most one end |
| timestamp | ISO-8601 explicit UTC Z or +00:00; valid time, at/after actual install timestamp and session start |
| platform | mobile / desktop / console |
| channel | organic / friend / paid / unknown; unknown is explicit missing attribution |
| cohort | YYYY-MM-DD UTC install date; exactly one matching install per player |
| properties | JSON object; optional mode on match_complete, synthetic on install |

Strict whole-file rejection preserves previous database on validation failure. Inputs must include the complete install history for every supplied player; partial/incremental ingestion is not implemented. Events after session end and sessions spanning multiple game IDs are rejected. Multi-game player identity requires upstream namespacing. No free-text player data, chat, age, location, device IDs or private contacts are generated. Profile CSV is an export; analytics derive installs from the validated event table.

## Simulation assumptions
Each player has a latent Beta(2.5,2) engagement propensity. It affects activity, tutorial completion and permanent daily churn risk. Installs span 120 days, with right-censored cohorts. Sessions have clipped lognormal durations; ~1.5% of end events are deliberately omitted. Three percent expected acquisition channels are unknown. These assumptions create learnable patterns; they are not fitted to Roblox data. Seeded reproducibility is scoped to pinned dependency versions.

## Model contract
Features: counts of sessions, active days, matches, social uses, tutorial completions on calendar ages 0–6. Label: no session starts on ages 7–20. Only players observed through age 20 are eligible. Train on installs at ages 0–39 relative to dataset start; test on installs at ages 70–98. The intervening gap ensures every training label is available before the earliest holdout install. User IDs are disjoint; cohort, future events, duration endpoints and latent simulator variables are not features. Standardization fits training rows only. Fixed L2 logistic regression and threshold 0.5; no test-set tuning. AP is average precision, not trapezoidal PR area. No serialized executable model file is loaded by the server.
