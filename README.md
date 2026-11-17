# GamePulse

[Working public demo](https://maramreddyajit-commits.github.io/gamepulse/) · [Product requirements](product/PRD.md)

Player retention cohorts, funnel diagnostics and a chronological churn baseline.

All records are fictional/synthetic. No real adoption, revenue or user impact is claimed.

## Run and reproduce

Use Python 3.14.7 (the audited version):

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m scripts.build_gamepulse
python -m pytest -q
python -m scripts.build_demo
python -m http.server 8000 --directory docs
```

Open http://localhost:8000/. The public demo is served from `docs/` by GitHub Pages. Python source and seed 20261117 reproduce the underlying dataset/evaluation.

## Deployment architecture

The browser loads four precomputed analytics views produced by the original Python/SQLite pipeline. Platform filters work; model evaluation remains global. Raw CSV ingestion and model fitting run locally with Python, not on GitHub Pages.

## Evaluation and limits

335,355 events from 10,000 simulated players over 120 days. 3,405 training and 2,404 later, disjoint test players. First-week features predict no sessions at ages 7–20. ROC-AUC 0.826958; not accuracy or demonstrated real-world performance. Generator assumptions create learnable signal.

See product documentation for KPI definitions, prioritization assumptions and proposed experiments. Proposed research has not been conducted. Implementation was built with AI coding assistance; evidence and limitations are documented explicitly.
