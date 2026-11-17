# GamePulse
New implementation; no accessible CreatorOS source was copied.

From the portfolio root:
```
python -m scripts.build_gamepulse
python -m pytest tests/test_gamepulse.py -q
python -m portfolio.server
```
Open http://127.0.0.1:8765/gamepulse. Filter platform, inspect cohorts, missing-session quality and the temporal churn baseline.

CSV ingestion: `python -m scripts.ingest_gamepulse INPUT.csv OUTPUT.sqlite` validates a complete telemetry export, including one install per player, before replacing the events table. `portfolio.gamepulse.load` reads this SQLite schema. Dashboard serves the seeded dataset; custom ingestion is a CLI path, not an upload button.

## Product decisions
Read [PRD.md](PRD.md) for user problem, target audience, prioritized requirements, acceptance criteria, KPIs, proposed experiments and recommendations. Research is proposed, not reported as completed.
