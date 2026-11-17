import pandas as pd
import pytest

from portfolio.gamepulse import (
    FEATURES,
    feature_table,
    funnel,
    generate,
    ingest,
    load,
    retention,
    train_model,
    validate_events,
)


def tiny():
    rows = []

    def add(pid, event, day, minute=0):
        cohort = "2026-07-20" if pid == "a" else "2026-08-19"
        ts = pd.Timestamp(cohort, tz="UTC") + pd.Timedelta(days=day, minutes=minute)
        rows.append(
            {
                "player_id": pid,
                "event_name": event,
                "cohort": cohort,
                "time": ts,
                "day": ts.floor("D"),
                "age": day,
                "install": pd.Timestamp(cohort, tz="UTC"),
            }
        )

    add("a", "install", 0)
    add("a", "session_start", 1)
    add("a", "session_start", 7)
    add("a", "match_complete", 0, 1)
    add("a", "tutorial_complete", 0, 2)
    add("a", "match_complete", 0, 3)
    add("b", "install", 0)
    return pd.DataFrame(rows)


def test_retention_excludes_immature():
    rows = retention(tiny(), pd.Timestamp("2026-08-20", tz="UTC"))
    assert rows[0]["d1"] == 1 and rows[0]["d7"] == 1 and rows[0]["d30"] == 0
    assert rows[1]["d1"] is None and rows[1]["d30"] is None


def test_retention_exact_boundary():
    rows = retention(tiny(), pd.Timestamp("2026-07-21", tz="UTC"))
    assert rows[0]["d1"] is None


def test_funnel_order_and_dedup():
    f = tiny()
    assert [x["players"] for x in funnel(f)] == [2, 1, 1]
    f = f[~((f.event_name == "match_complete") & (f.time.dt.minute == 3))]
    assert funnel(f)[-1]["players"] == 0


def test_future_events_do_not_change_features():
    f = tiny()
    before = feature_table(f)
    changed = f.copy()
    changed.loc[len(changed)] = {
        **f.iloc[1].to_dict(),
        "age": 10,
        "event_name": "social_use",
    }
    pd.testing.assert_frame_equal(before[FEATURES], feature_table(changed)[FEATURES])


def test_generation_reproducible(tmp_path):
    generate(tmp_path / "a", 30)
    generate(tmp_path / "b", 30)
    assert (tmp_path / "a/events.csv").read_bytes() == (tmp_path / "b/events.csv").read_bytes()


@pytest.fixture
def valid(tmp_path):
    generate(tmp_path, 10)
    return pd.read_csv(tmp_path / "events.csv", keep_default_na=False)


@pytest.mark.parametrize(
    "mutation", ["duplicate", "utc", "name", "session", "cohort", "properties"]
)
def test_invalid_ingestion(valid, mutation):
    if mutation == "duplicate":
        valid = pd.concat([valid, valid.iloc[:1]])
    elif mutation == "utc":
        valid.loc[0, "timestamp"] = "2026-07-20T00:00:00"
    elif mutation == "name":
        valid.loc[0, "event_name"] = "bogus"
    elif mutation == "session":
        valid.loc[1, "session_id"] = ""
    elif mutation == "cohort":
        valid.loc[0, "cohort"] = "2030-01-01"
    else:
        valid.loc[0, "properties"] = "[]"
    with pytest.raises((ValueError, TypeError)):
        validate_events(valid)


def test_ingestion_roundtrip(valid, tmp_path):
    p = tmp_path / "input.csv"
    valid.to_csv(p, index=False)
    ingest(p, tmp_path / "t.db")
    assert len(load(tmp_path / "t.db")) == len(valid)


def test_model_has_temporal_gap(tmp_path):
    generate(tmp_path, 600)
    ingest(tmp_path / "events.csv", tmp_path / "t.db")
    m = train_model(load(tmp_path / "t.db"))
    assert m["user_overlap"] == 0
    assert m["last_train_label_end_exclusive"] < m["first_test_install"]
    assert 0 <= m["roc_auc"] <= 1
    assert sum(map(sum, m["confusion_matrix_actual_rows_predicted_columns"])) == m["test_players"]


def test_session_duration_excludes_missing_ends(tmp_path):
    generate(tmp_path, 20)
    ingest(tmp_path / "events.csv", tmp_path / "test.sqlite")
    frame = load(tmp_path / "test.sqlite")
    from portfolio.gamepulse import analytics

    report = analytics(frame)
    starts = frame[frame.event_name == "session_start"].set_index("session_id")
    ends = frame[frame.event_name == "session_end"].set_index("session_id")
    manual = [
        (ends.loc[s, "time"] - starts.loc[s, "time"]).total_seconds() / 60 for s in ends.index
    ]
    assert abs(report["session_minutes_mean"] - sum(manual) / len(manual)) < 1e-8
    assert report["missing_session_ends"] == len(starts) - len(ends)


def test_invalid_input_preserves_previous_database(valid, tmp_path):
    path = tmp_path / "input.csv"
    database = tmp_path / "test.sqlite"
    valid.to_csv(path, index=False)
    ingest(path, database)
    expected = database.read_bytes()
    valid.loc[0, "event_name"] = "invalid"
    valid.to_csv(path, index=False)
    with pytest.raises(ValueError):
        ingest(path, database)
    assert database.read_bytes() == expected
