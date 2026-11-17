# Decision brief — planned experiments
Audience: a small game team deciding where to invest retention work. The demo diagnoses simulated behavior; it cannot establish the cause of real churn.

| Experiment | Mechanism | Primary success metric | Guardrails | Proposed design |
|---|---|---|---|---|
| Short tutorial with optional practice | Less initial friction, preserve comprehension | D7 exact-day retention on mature installs | First-match completion, crash rate, help requests | User-randomized control / treatment; pre-register minimum detectable effect and sample size after collecting real baseline |
| Opt-in squad invitation after first match | Social connection motivates voluntary return | Mature D7 retention | Invite opt-outs, reports/blocks, latency | Assign users persistently; measure network spillover before interpreting effect |
| Clear next-session goal | Communicate progress without coercive streaks | Mature D30 retention | Session satisfaction survey, excessive play, notification opt-outs | No streak loss or urgency; exposure logging and intention-to-treat analysis |

Priority: tutorial first (lowest implementation risk); goals second; social invitation third because interference complicates inference. The dashboard's +3 percentage point scenario is an explicit planning assumption, not a model estimate or A/B result. Expected benefit is a hypothesis. No tests with real users have been conducted.
