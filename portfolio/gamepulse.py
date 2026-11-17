"""Seeded telemetry, strict ingestion, mature-cohort analytics, temporal churn baseline."""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20261117
START = datetime(2026, 7, 20, tzinfo=UTC)
DAYS = 120
CUTOFF = START + timedelta(days=DAYS)  # exclusive
EVENTS = {
    "install",
    "session_start",
    "tutorial_complete",
    "match_complete",
    "social_use",
    "shop_view",
    "session_end",
}
COLUMNS = [
    "event_id",
    "player_id",
    "event_name",
    "game_id",
    "session_id",
    "timestamp",
    "platform",
    "channel",
    "cohort",
    "properties",
]


def generate(folder: Path, players: int = 10000, seed: int = SEED) -> dict:
    """Model heterogeneous engagement and permanent churn; all identities fictional."""
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    profiles: list[list] = []
    rows: list[list] = []

    def emit(pid, name, sid, ts, platform, channel, cohort, props):
        rows.append(
            [
                f"e{len(rows):08}",
                pid,
                name,
                "demo_arena",
                sid,
                ts.isoformat(),
                platform,
                channel,
                cohort,
                json.dumps(props, sort_keys=True),
            ]
        )

    for i in range(players):
        pid = f"p{i:05}"
        install_day = int(rng.integers(0, DAYS))
        cohort = (START + timedelta(days=install_day)).date().isoformat()
        platform = str(rng.choice(["mobile", "desktop", "console"], p=[0.58, 0.32, 0.10]))
        channel = str(
            rng.choice(["organic", "friend", "paid", "unknown"], p=[0.46, 0.27, 0.24, 0.03])
        )
        engagement = float(rng.beta(2.5, 2))
        tutorial = bool(rng.random() < (0.56 + 0.34 * engagement))
        profiles.append([pid, cohort, platform, channel])
        emit(
            pid,
            "install",
            "",
            START + timedelta(days=install_day),
            platform,
            channel,
            cohort,
            {"synthetic": True},
        )
        alive = True
        for age in range(DAYS - install_day):
            if age and rng.random() < (
                0.018 + 0.105 * (1 - engagement) + (0.025 if not tutorial else 0)
            ):
                alive = False
            if not alive:
                break
            if age and rng.random() > (0.16 + 0.65 * engagement):
                continue
            for visit in range(1 + int(rng.random() < 0.14)):
                sid = f"{pid}-{age}-{visit}"
                ts = START + timedelta(
                    days=install_day + age,
                    hours=9 + visit * 5,
                    minutes=int(rng.integers(0, 120)),
                )
                minutes = float(np.clip(rng.lognormal(2.0 + engagement, 0.65), 1, 90))
                emit(pid, "session_start", sid, ts, platform, channel, cohort, {})
                if age == 0 and visit == 0 and tutorial:
                    emit(
                        pid,
                        "tutorial_complete",
                        sid,
                        ts + timedelta(seconds=30),
                        platform,
                        channel,
                        cohort,
                        {},
                    )
                if (age > 0 or tutorial) and rng.random() < 0.83:
                    emit(
                        pid,
                        "match_complete",
                        sid,
                        ts + timedelta(seconds=50),
                        platform,
                        channel,
                        cohort,
                        {"mode": str(rng.choice(["solo", "duo", "squad"]))},
                    )
                if rng.random() < 0.1 + 0.35 * engagement:
                    emit(
                        pid,
                        "social_use",
                        sid,
                        ts + timedelta(seconds=55),
                        platform,
                        channel,
                        cohort,
                        {},
                    )
                if rng.random() < 0.18:
                    emit(
                        pid,
                        "shop_view",
                        sid,
                        ts + timedelta(seconds=58),
                        platform,
                        channel,
                        cohort,
                        {},
                    )
                # Missing session-end telemetry is a deliberate edge case, never imputed as zero length.
                if rng.random() > 0.015:
                    emit(
                        pid,
                        "session_end",
                        sid,
                        ts + timedelta(minutes=minutes),
                        platform,
                        channel,
                        cohort,
                        {},
                    )
    with (folder / "players.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["player_id", "cohort", "platform", "channel"])
        w.writerows(profiles)
    with (folder / "events.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    manifest = {
        "seed": seed,
        "synthetic": True,
        "players": players,
        "events": len(rows),
        "simulated_days": DAYS,
        "start": START.isoformat(),
        "cutoff_exclusive": CUTOFF.isoformat(),
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def validate_events(frame: pd.DataFrame) -> pd.DataFrame:
    if set(COLUMNS) - set(frame.columns):
        raise ValueError("Missing telemetry columns")
    frame = frame.copy().fillna("")
    if frame.empty:
        raise ValueError("No events")
    if frame.event_id.duplicated().any():
        raise ValueError("Duplicate event_id")
    for col in ["event_id", "player_id", "game_id", "platform", "channel", "cohort"]:
        if (frame[col].astype(str).str.len() == 0).any():
            raise ValueError(f"Missing {col}")
    if not frame.event_name.isin(EVENTS).all():
        raise ValueError("Unknown event name")
    if not frame.platform.isin(["mobile", "desktop", "console"]).all():
        raise ValueError("Unknown platform")
    if not frame.channel.isin(["organic", "friend", "paid", "unknown"]).all():
        raise ValueError("Unknown channel")
    if not frame.timestamp.str.match(r"^\d{4}-\d{2}-\d{2}T.*(?:Z|\+00:00)$").all():
        raise ValueError("Timestamp must be explicit UTC")
    stamps = pd.to_datetime(frame.timestamp, utc=True, format="ISO8601", errors="raise")
    cohorts = pd.to_datetime(frame.cohort, utc=True, format="%Y-%m-%d", errors="raise")
    if (stamps < cohorts).any():
        raise ValueError("Event before install cohort")
    if ((frame.event_name != "install") & (frame.session_id == "")).any():
        raise ValueError("Missing session_id")
    for value in frame.properties:
        if not isinstance(json.loads(value), dict):
            raise ValueError("Properties must be JSON objects")
    consistency = frame.groupby("player_id")[["cohort", "platform", "channel"]].nunique()
    if (consistency > 1).any().any():
        raise ValueError("Inconsistent player dimensions")
    installs = frame[frame.event_name == "install"]
    if installs.player_id.duplicated().any() or set(installs.player_id) != set(frame.player_id):
        raise ValueError("Exactly one install per player required")
    if not (
        pd.to_datetime(installs.timestamp, utc=True, format="ISO8601").dt.strftime("%Y-%m-%d")
        == installs.cohort
    ).all():
        raise ValueError("Install date must match cohort")
    install_times = installs.set_index("player_id").timestamp.map(pd.Timestamp)
    if (stamps < frame.player_id.map(install_times)).any():
        raise ValueError("Event before actual install timestamp")
    if (installs.session_id != "").any():
        raise ValueError("Install must not have a session_id")
    sessions = frame[frame.session_id != ""]
    if (sessions.groupby("session_id").player_id.nunique() > 1).any():
        raise ValueError("Session belongs to multiple players")
    if (sessions.groupby("session_id").game_id.nunique() > 1).any():
        raise ValueError("Session belongs to multiple games")
    starts = sessions[sessions.event_name == "session_start"]
    ends = sessions[sessions.event_name == "session_end"]
    if starts.session_id.duplicated().any() or ends.session_id.duplicated().any():
        raise ValueError("Duplicate session boundary")
    if set(sessions.session_id) - set(starts.session_id):
        raise ValueError("Session event without start")
    start_map = starts.set_index("session_id").timestamp.map(lambda s: pd.Timestamp(s))
    if (
        pd.to_datetime(sessions.timestamp, utc=True, format="ISO8601")
        < sessions.session_id.map(start_map)
    ).any():
        raise ValueError("Session event before start")
    end_map = ends.set_index("session_id").timestamp.map(pd.Timestamp)
    session_ends = sessions.session_id.map(end_map)
    if (pd.to_datetime(sessions.timestamp, utc=True, format="ISO8601") > session_ends).any():
        raise ValueError("Session event after session end")
    return frame[COLUMNS]


def ingest(csv_path: Path, db: Path) -> dict:
    frame = validate_events(pd.read_csv(csv_path, keep_default_na=False))
    with closing(sqlite3.connect(db)) as con, con:
        # Validate first. Replace only in a transaction; invalid uploads preserve the old table.
        con.execute("BEGIN")
        con.execute("DROP TABLE IF EXISTS events")
        con.execute(
            "CREATE TABLE events (event_id TEXT PRIMARY KEY, player_id TEXT NOT NULL, event_name TEXT NOT NULL, game_id TEXT NOT NULL, session_id TEXT NOT NULL, timestamp TEXT NOT NULL, platform TEXT NOT NULL, channel TEXT NOT NULL, cohort TEXT NOT NULL, properties TEXT NOT NULL)"
        )
        con.executemany(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?)",
            frame.itertuples(index=False, name=None),
        )
        con.execute("CREATE INDEX events_player_time ON events(player_id,timestamp)")
        con.execute("CREATE INDEX events_cohort ON events(cohort,event_name)")
    return {"accepted_events": len(frame), "players": frame.player_id.nunique()}


def load(db: Path) -> pd.DataFrame:
    with closing(sqlite3.connect(db)) as con, con:
        frame = pd.read_sql_query("SELECT * FROM events", con)
    frame["time"] = pd.to_datetime(frame.timestamp, utc=True, format="ISO8601")
    frame["day"] = frame.time.dt.floor("D")
    frame["install"] = pd.to_datetime(frame.cohort, utc=True)
    frame["age"] = (frame.day - frame.install).dt.days
    return frame


def retention(frame: pd.DataFrame, cutoff: pd.Timestamp) -> list[dict]:
    profiles = frame[frame.event_name == "install"]
    active = frame[frame.event_name == "session_start"]
    result = []
    for cohort, group in profiles.groupby("cohort"):
        row = {"cohort": cohort, "players": len(group)}
        for n in [1, 7, 30]:
            mature = pd.Timestamp(cohort, tz="UTC") + pd.Timedelta(days=n + 1) <= cutoff
            returned = (
                active[(active.cohort == cohort) & (active.age == n)].player_id.nunique()
                if mature
                else None
            )
            row[f"d{n}"] = returned / len(group) if returned is not None else None
            row[f"d{n}_returned"] = returned
        result.append(row)
    return result


def funnel(frame: pd.DataFrame) -> list[dict]:
    """Strict ordered, per-player onboarding funnel within the first 7 calendar days."""
    eligible = frame[(frame.age < 7) & (frame.age >= 0)]
    steps = ["install", "tutorial_complete", "match_complete"]
    previous: dict[str, pd.Timestamp] = {}
    result = []
    for i, step in enumerate(steps):
        next_seen = {}
        for row in eligible[eligible.event_name == step].sort_values("time").itertuples():
            if row.player_id in next_seen:
                continue
            if i == 0 or (row.player_id in previous and row.time >= previous[row.player_id]):
                next_seen[row.player_id] = row.time
        previous = next_seen
        result.append({"step": step, "players": len(previous)})
    return result


def analytics(frame: pd.DataFrame, cutoff=CUTOFF, platform: str = "all") -> dict:
    frame = frame[frame.time < pd.Timestamp(cutoff)]
    if platform != "all":
        frame = frame[frame.platform == platform]
    cohorts = retention(frame, pd.Timestamp(cutoff))
    rates = {}
    for n in [1, 7, 30]:
        mature = [c for c in cohorts if c[f"d{n}"] is not None]
        den = sum(c["players"] for c in mature)
        num = sum(c[f"d{n}_returned"] for c in mature)
        rates[f"d{n}"] = {
            "rate": num / den if den else None,
            "returned": num,
            "eligible": den,
        }
    starts = frame[frame.event_name == "session_start"]
    ends = frame[frame.event_name == "session_end"]
    paired = starts[["session_id", "time"]].merge(
        ends[["session_id", "time"]], on="session_id", suffixes=("_start", "_end")
    )
    durations = (paired.time_end - paired.time_start).dt.total_seconds() / 60
    profiles = frame[frame.event_name == "install"]
    total = len(profiles)
    frequency = starts.groupby("player_id").day.nunique().reindex(profiles.player_id, fill_value=0)
    # Only mature players enter first-week comparisons.
    mature_ids = profiles[profiles.install + pd.Timedelta(days=7) <= pd.Timestamp(cutoff)].player_id
    mature_frame = frame[frame.player_id.isin(mature_ids)]
    first_week = (
        starts[(starts.age < 7) & starts.player_id.isin(mature_ids)]
        .groupby("player_id")
        .day.nunique()
        .reindex(mature_ids, fill_value=0)
    )
    return {
        "synthetic": True,
        "platform": platform,
        "players": total,
        "events": len(frame),
        "sessions": len(starts),
        "retention": rates,
        "cohorts": cohorts,
        "funnel": funnel(mature_frame),
        "funnel_window": "Days 0–6; only fully observed players",
        "session_minutes_mean": float(durations.mean()) if len(durations) else None,
        "session_minutes_p50": float(durations.median()) if len(durations) else None,
        "missing_session_ends": len(starts) - len(paired),
        "active_days_mean": float(frequency.mean()) if total else 0,
        "first_week_active_days": float(first_week.mean()) if len(first_week) else 0,
        "features": [
            {
                "name": name,
                "players": frame[frame.event_name == name].player_id.nunique(),
                "rate": frame[frame.event_name == name].player_id.nunique() / total if total else 0,
            }
            for name in [
                "tutorial_complete",
                "match_complete",
                "social_use",
                "shop_view",
            ]
        ],
        "segments": [
            {"name": channel, "players": len(g)} for channel, g in profiles.groupby("channel")
        ],
    }


FEATURES = ["active_days", "sessions", "matches", "social_uses", "tutorial"]


def feature_table(frame: pd.DataFrame, cutoff=CUTOFF) -> pd.DataFrame:
    profiles = frame[frame.event_name == "install"][["player_id", "install"]].copy()
    profiles = profiles[profiles.install + pd.Timedelta(days=21) <= pd.Timestamp(cutoff)]
    early = frame[(frame.age >= 0) & (frame.age < 7)]
    future = frame[(frame.age >= 7) & (frame.age < 21) & (frame.event_name == "session_start")]
    table = profiles.set_index("player_id")
    sessions = early[early.event_name == "session_start"]
    table["active_days"] = sessions.groupby("player_id").day.nunique()
    for feature, event in [
        ("sessions", "session_start"),
        ("matches", "match_complete"),
        ("social_uses", "social_use"),
        ("tutorial", "tutorial_complete"),
    ]:
        table[feature] = early[early.event_name == event].groupby("player_id").size()
    table[FEATURES] = table[FEATURES].fillna(0)
    table["churn"] = (~table.index.isin(future.player_id)).astype(int)
    return table


def train_model(frame: pd.DataFrame) -> dict:
    table = feature_table(frame)
    train = table[table.install < START + timedelta(days=40)]
    test = table[
        (table.install >= START + timedelta(days=70)) & (table.install < START + timedelta(days=99))
    ]
    assert set(train.index).isdisjoint(test.index)
    assert train.install.max() + pd.Timedelta(days=21) < test.install.min()
    model = make_pipeline(StandardScaler(), LogisticRegression(random_state=SEED, max_iter=1000))
    model.fit(train[FEATURES], train.churn)
    scores = model.predict_proba(test[FEATURES])[:, 1]
    cm = confusion_matrix(test.churn, scores >= 0.5, labels=[0, 1]).tolist()
    return {
        "algorithm": "StandardScaler + logistic regression (L2, C=1)",
        "features": FEATURES,
        "train_players": len(train),
        "test_players": len(test),
        "train_install_end": train.install.max().isoformat(),
        "last_train_label_end_exclusive": (train.install.max() + pd.Timedelta(days=21)).isoformat(),
        "first_test_install": test.install.min().isoformat(),
        "test_install_end": test.install.max().isoformat(),
        "user_overlap": 0,
        "feature_window": "days 0–6",
        "label": "1 = no sessions on days 7–20",
        "threshold": 0.5,
        "roc_auc": float(roc_auc_score(test.churn, scores)),
        "pr_auc_average_precision": float(average_precision_score(test.churn, scores)),
        "prevalence_baseline_ap": float(test.churn.mean()),
        "confusion_matrix_actual_rows_predicted_columns": cm,
        "standardized_coefficients": dict(zip(FEATURES, model[-1].coef_[0].tolist())),
        "limitation": "Synthetic behavioral rules determine the signal; scores are not evidence of predictive power on real players.",
    }


def build(folder: Path) -> dict:
    manifest = generate(folder)
    ingestion = ingest(folder / "events.csv", folder / "telemetry.sqlite")
    frame = load(folder / "telemetry.sqlite")
    result = {
        "manifest": manifest,
        "ingestion": ingestion,
        "analytics": analytics(frame),
        "model": train_model(frame),
    }
    (folder / "summary.json").write_text(json.dumps(result, indent=2))
    return result
