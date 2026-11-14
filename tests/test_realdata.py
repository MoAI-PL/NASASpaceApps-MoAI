# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Tests for the real-data check (PMData reader, cleaning and alarm counting)."""

import json

import numpy as np
import pandas as pd

from src.realdata import clean, participant_daily, summarise


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_participant_daily_reads_pmdata_layout(tmp_path):
    p = tmp_path / "p01"
    _write(p / "fitbit" / "resting_heart_rate.json", [
        {"dateTime": "2019-11-01 00:00:00", "value": {"value": 55.2}},
        {"dateTime": "2019-11-03 00:00:00", "value": {"value": 0}},          # 0 = no estimate
    ])
    _write(p / "fitbit" / "sleep.json", [
        {"dateOfSleep": "2019-11-01", "minutesAsleep": 420, "mainSleep": True},
        {"dateOfSleep": "2019-11-01", "minutesAsleep": 30, "mainSleep": False},   # nap ignored
    ])
    _write(p / "fitbit" / "very_active_minutes.json", [{"dateTime": "2019-11-01 00:00:00", "value": "20"},
                                                        {"dateTime": "2019-11-03 00:00:00", "value": "0"}])
    _write(p / "fitbit" / "moderately_active_minutes.json", [{"dateTime": "2019-11-01 00:00:00", "value": "10"}])
    (p / "pmsys").mkdir(parents=True)
    (p / "pmsys" / "wellness.csv").write_text(
        "effective_time_frame,mood\n2019-11-02T08:00:00.000Z,4\n2019-11-03T08:00:00.000Z,0\n", encoding="utf-8")

    daily = participant_daily(p)
    # Day 3 has no valid value left (HR 0, mood 0, band not worn → exercise missing), so it is dropped.
    assert list(daily["day"]) == [1, 2]
    assert daily.loc[0, "hr"] == 55.2
    assert daily.loc[0, "sleep_h"] == 7.0
    assert daily.loc[0, "exercise_min"] == 30
    assert daily.loc[1, "mood"] == 4


def test_clean_drops_sleep_artefacts_and_unworn_exercise():
    frame = pd.DataFrame({"hr": [60.0, 60.0, np.nan], "sleep_h": [24.0, 7.0, np.nan],
                          "mood": [3.0, 3.0, 3.0], "exercise_min": [10.0, 10.0, 0.0]})
    out = clean(frame)
    assert np.isnan(out.loc[0, "sleep_h"]) and out.loc[1, "sleep_h"] == 7.0
    assert np.isnan(out.loc[2, "exercise_min"])    # no HR and no sleep record: band not worn


def test_summarise_counts_episodes_after_calibration():
    days = np.arange(1, 36)
    model = np.zeros(35, dtype=bool)
    model[[4, 5]] = True            # during calibration: ignored
    model[[24, 25, 26]] = True      # one episode after calibration
    flags = {"days": days, "Model": model, "B1": np.zeros(35, bool), "B2": np.zeros(35, bool)}
    out = summarise([flags], calib_days=21)
    assert out["person_weeks"] == 2.0
    assert out["alarms_per_person_week"]["Model"] == 0.5
    assert out["share_of_people_with_any_alarm"]["Model"] == 1.0
