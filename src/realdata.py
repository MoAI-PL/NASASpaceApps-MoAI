# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Real-data check: how often do the frozen model and the baselines alarm on REAL everyday data?

Data: PMData (Thambawita et al., 2020, CC BY 4.0) — 16 people logging Fitbit and wellness data
for up to 5 months (Nov 2019 – Mar 2020). Four of our nine daily inputs exist there:
resting heart rate (Fitbit), sleep hours (Fitbit main sleep), mood (1–5 self-rating, PMSys; higher
= better) and exercise minutes (Fitbit very + moderately active). Blood pressure, temperature,
glucose and reaction time are missing and enter the model as "missing" (personal z-score 0).

Nothing is fitted or tuned here: the production detector, P_yellow, persistence and the baseline
rules are used exactly as frozen. The people are not labelled healthy (winter months, flu season),
so the result is an alarm rate on real everyday life, reported next to a synthetic control with the
SAME four inputs (healthy astronauts of the bench and dev selection splits; never the hold-out).

Usage:
    python -m src.realdata --pmdata-dir PATH/TO/pmdata   # rebuild data/real/pmdata_daily.csv from raw PMData
    python -m src.realdata                               # run the check on the committed daily table
"""

# ===== Imports =====
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.baselines import b1_alarm, b2_alarm
from src.common import AE_FEATURES, CONFIG_DIR, DATA_DIR, DISCLAIMER, RESULTS_DIR, load_yaml, val, write_json
from src.evaluate import onsets
from src.features import astronaut_windows
from src.scoring import ae_alarm, contribution_shares, load_scorer, score_astronaut
from src.simulate import build_split

# ===== Constants =====
REAL_FEATURES = ["hr", "sleep_h", "mood", "exercise_min"]   # the four inputs PMData provides
DAILY_CSV = DATA_DIR / "real" / "pmdata_daily.csv"
CONTROL_SPLITS = ["bench", "dev"]                            # selection splits only, never "test"
MIN_DAYS_AFTER_CALIBRATION = 28
SLEEP_ARTEFACT_H = (1.0, 16.0)   # Fitbit nights outside this range are recording artefacts → missing
METHODS = ["Model", "B1", "B2"]
SOURCE = ("PMData: Thambawita V. et al. (2020), PMData: a sports logging dataset, Proc. ACM MMSys'20, "
          "doi:10.1145/3339825.3394926, CC BY 4.0, https://datasets.simula.no/pmdata")


# ===== Reading raw PMData =====
def _daily_json(path: Path, value) -> pd.Series:
    """Date-indexed series from a Fitbit daily JSON list ([{dateTime, value}, ...])."""
    if not path.exists():
        return pd.Series(dtype=float)
    rows = json.loads(path.read_text(encoding="utf-8"))
    out = {pd.Timestamp(r["dateTime"][:10]): value(r["value"]) for r in rows}
    return pd.Series(out, dtype=float)


def _resting_hr(v) -> float:
    """Fitbit reports 0 when it could not estimate a resting heart rate: treat that as missing."""
    hr = float(v.get("value", 0) or 0)
    return hr if hr > 0 else np.nan


def _sleep_hours(path: Path) -> pd.Series:
    """Hours asleep per night: main-sleep records only, summed per date of sleep."""
    if not path.exists():
        return pd.Series(dtype=float)
    rows = [r for r in json.loads(path.read_text(encoding="utf-8")) if r.get("mainSleep", True)]
    frame = pd.DataFrame({"date": [pd.Timestamp(r["dateOfSleep"]) for r in rows],
                          "minutes": [float(r["minutesAsleep"]) for r in rows]})
    return frame.groupby("date")["minutes"].sum() / 60.0 if len(frame) else pd.Series(dtype=float)


def _mood(path: Path) -> pd.Series:
    """Mood self-rating 1–5 (PMSys wellness); 0 is not a valid answer. Last answer of a day wins."""
    if not path.exists():
        return pd.Series(dtype=float)
    frame = pd.read_csv(path)
    frame["date"] = pd.to_datetime(frame["effective_time_frame"].str[:10])
    frame = frame[frame["mood"].between(1, 5)]
    return frame.groupby("date")["mood"].last().astype(float)


def clean(frame: pd.DataFrame) -> pd.DataFrame:
    """Sensor-logic cleaning, decided before scoring and applied to every person alike.

    - Fitbit writes 0 active minutes on days the band was not worn: exercise counts as missing on
      days with no wear evidence (neither a resting heart rate nor a sleep record).
    - Sleep records outside SLEEP_ARTEFACT_H hours are recording artefacts and count as missing.
    """
    frame = frame.copy()
    no_wear = frame["hr"].isna() & frame["sleep_h"].isna()
    frame.loc[no_wear, "exercise_min"] = np.nan
    lo, hi = SLEEP_ARTEFACT_H
    frame.loc[(frame["sleep_h"] < lo) | (frame["sleep_h"] > hi), "sleep_h"] = np.nan
    return frame


def participant_daily(folder: Path) -> pd.DataFrame:
    """One row per calendar day for one participant, from the first to the last day with any value."""
    fitbit, pmsys = folder / "fitbit", folder / "pmsys"
    very = _daily_json(fitbit / "very_active_minutes.json", float)
    moderate = _daily_json(fitbit / "moderately_active_minutes.json", float)
    cols = {
        "hr": _daily_json(fitbit / "resting_heart_rate.json", _resting_hr),
        "sleep_h": _sleep_hours(fitbit / "sleep.json"),
        "mood": _mood(pmsys / "wellness.csv"),
        "exercise_min": very.add(moderate, fill_value=0) if len(very) or len(moderate) else pd.Series(dtype=float),
    }
    frame = pd.DataFrame(cols).sort_index()
    frame = clean(frame)
    frame = frame.dropna(how="all")
    if frame.empty:
        return frame
    full = pd.date_range(frame.index.min(), frame.index.max(), freq="D")
    frame = frame.reindex(full)
    frame.insert(0, "date", frame.index.strftime("%Y-%m-%d"))
    frame.insert(0, "day", np.arange(1, len(frame) + 1))
    frame.insert(0, "participant", folder.name)
    return frame.reset_index(drop=True)


def build_daily_table(pmdata_dir: Path) -> pd.DataFrame:
    """Daily table for every participant folder (p01 … p16) found in the PMData directory."""
    frames = [participant_daily(p) for p in sorted(pmdata_dir.glob("p[0-9][0-9]")) if p.is_dir()]
    frames = [f for f in frames if not f.empty]
    table = pd.concat(frames, ignore_index=True)
    return table.round({"hr": 1, "sleep_h": 2, "exercise_min": 0})


# ===== Signals =====
def as_crew_frame(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    """Shape a daily table like a simulated astronaut: all nine inputs, missing ones as NaN."""
    out = pd.DataFrame({"astronaut": name, "day": frame["day"].to_numpy()})
    for f in AE_FEATURES:
        out[f] = frame[f].to_numpy(dtype=float) if f in frame else np.nan
    return out


def alarm_flags(frame: pd.DataFrame, cfgs: dict, scorer) -> dict[str, np.ndarray]:
    """Yellow-or-worse model alarm and the two baseline alarms, per day, with frozen settings."""
    window = int(cfgs["model"]["window_days"])
    aw = astronaut_windows(frame, cfgs["sim"], window, cfgs["model"].get("normal"), cfgs["model"]["scoring"]["day_weights"])
    sai = score_astronaut(scorer, aw)["sai"]
    p_yellow = float(cfgs["model"]["scoring"]["p_yellow"])
    k = int(cfgs["model"]["scoring"]["persistence_days"])
    release = int(cfgs["model"]["scoring"].get("release_days", 0))
    scored = score_astronaut(scorer, aw)
    top = [None if np.isnan(row).any() or row.sum() <= 0 else AE_FEATURES[int(np.argmax(row))]
           for row in scored["deviation"]]
    return {"days": aw.days, "top": top, "Model": ae_alarm(sai, p_yellow, k, release),
            "B1": b1_alarm(frame, cfgs["rules"]), "B2": b2_alarm(aw.z, aw.mask, cfgs["rules"])}


def summarise(flag_sets: list[dict], calib_days: int) -> dict:
    """Alarm episodes per person-week, share of days in alarm and share of people with any alarm."""
    days_total, episodes, alarm_days, anyone = 0, dict.fromkeys(METHODS, 0), dict.fromkeys(METHODS, 0), dict.fromkeys(METHODS, 0)
    for s in flag_sets:
        keep = s["days"] > calib_days
        days_total += int(keep.sum())
        for m in METHODS:
            episodes[m] += onsets(s[m], keep)
            alarm_days[m] += int((s[m] & keep).sum())
            anyone[m] += int((s[m] & keep).any())
    weeks = days_total / 7.0
    return {
        "people": len(flag_sets),
        "person_weeks": round(weeks, 1),
        "alarms_per_person_week": {m: round(episodes[m] / weeks, 3) for m in METHODS},
        "share_of_days_in_alarm": {m: round(alarm_days[m] / days_total, 3) for m in METHODS},
        "share_of_people_with_any_alarm": {m: round(anyone[m] / len(flag_sets), 3) for m in METHODS},
    }


def alarm_drivers(flag_sets: list[dict], calib_days: int) -> dict[str, float]:
    """Share of the model's alarm days on which each input holds the largest part of the deviation."""
    counts: dict[str, int] = {}
    for s in flag_sets:
        for day, flag, top in zip(s["days"], s["Model"], s["top"]):
            if flag and day > calib_days and top:
                counts[top] = counts.get(top, 0) + 1
    total = sum(counts.values()) or 1
    return {f: round(c / total, 3) for f, c in sorted(counts.items(), key=lambda kv: -kv[1])}


def eligible(frame: pd.DataFrame, calib_days: int) -> bool:
    """Enough follow-up after calibration, and heart rate or sleep observed during calibration."""
    calib = frame[frame["day"] <= calib_days]
    has_wearable = calib[["hr", "sleep_h"]].notna().any(axis=None)
    return int((frame["day"] > calib_days).sum()) >= MIN_DAYS_AFTER_CALIBRATION and bool(has_wearable)


def synthetic_control(cfgs: dict, scorer, calib_days: int) -> tuple[dict, dict]:
    """Healthy astronauts of the selection splits, scored with all nine and with only the four inputs."""
    full, four = [], []
    for split in CONTROL_SPLITS:
        crew, _ = build_split(cfgs["sim"], split)
        for name, frame in crew.groupby("astronaut", sort=False):
            if str(frame["scenario"].iloc[0]) != "none":
                continue
            frame = frame.sort_values("day")
            full.append(alarm_flags(frame, cfgs, scorer))
            reduced = frame.copy()
            reduced[[f for f in AE_FEATURES if f not in REAL_FEATURES]] = np.nan
            four.append(alarm_flags(reduced, cfgs, scorer))
    return summarise(full, calib_days), summarise(four, calib_days)


# ===== Report =====
def markdown(result: dict) -> str:
    """Results table for README / outputs/results/real_data_check.md."""
    rows = [("Real people (PMData), 4 inputs", result["real"]),
            ("Synthetic healthy astronauts, same 4 inputs", result["synthetic_same_inputs"]),
            ("Synthetic healthy astronauts, all 9 inputs", result["synthetic_all_inputs"])]
    lines = ["### Real-data check (PMData, frozen model — nothing fitted or tuned)", "",
             "| Data | People | Person-weeks | Alarms per person-week Model / B1 / B2 | Days in alarm Model / B1 / B2 |",
             "|---|---|---|---|---|"]
    for label, r in rows:
        a, d = r["alarms_per_person_week"], r["share_of_days_in_alarm"]
        lines.append(f"| {label} | {r['people']} | {r['person_weeks']} | "
                     f"{a['Model']:.3f} / {a['B1']:.3f} / {a['B2']:.3f} | "
                     f"{d['Model']:.0%} / {d['B1']:.0%} / {d['B2']:.0%} |")
    lines += ["", result["note"], "", f"Source: {SOURCE}."]
    return "\n".join(lines) + "\n"


# ===== Main =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alarm rates of the frozen model on real everyday data (PMData).")
    parser.add_argument("--pmdata-dir", type=Path, help="Raw PMData folder with p01 … p16; rebuilds the daily table.")
    args = parser.parse_args()

    if args.pmdata_dir:
        table = build_daily_table(args.pmdata_dir)
        DAILY_CSV.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(DAILY_CSV, index=False)
        print(f"Wrote {DAILY_CSV} ({table['participant'].nunique()} people, {len(table)} days)")

    cfgs = {"model": load_yaml(CONFIG_DIR / "model.yaml"), "sim": load_yaml(CONFIG_DIR / "simulation.yaml"),
            "rules": load_yaml(CONFIG_DIR / "rules.yaml")}
    scorer = load_scorer(cfgs["model"])
    calib_days = int(val(cfgs["sim"]["mission"]["calibration_days"]))

    table = pd.read_csv(DAILY_CSV)
    real_sets, excluded, alarm_days = [], [], {}
    for person, frame in table.groupby("participant", sort=True):
        frame = frame.sort_values("day")
        if not eligible(frame, calib_days):
            excluded.append(person)
            continue
        flags = alarm_flags(as_crew_frame(frame, person), cfgs, scorer)
        real_sets.append(flags)
        alarm_days[person] = [int(d) for d, f in zip(flags["days"], flags["Model"]) if f and d > calib_days]

    synth_all, synth_four = synthetic_control(cfgs, scorer, calib_days)
    real = summarise(real_sets, calib_days)
    coverage = {f: round(float(table[f].notna().mean()), 3) for f in REAL_FEATURES}
    result = {
        "data": SOURCE,
        "inputs_used": REAL_FEATURES,
        "inputs_missing": [f for f in AE_FEATURES if f not in REAL_FEATURES],
        "share_of_days_observed": coverage,
        "excluded_participants": excluded,
        "settings": {"p_yellow": float(cfgs["model"]["scoring"]["p_yellow"]),
                     "persistence_days": int(cfgs["model"]["scoring"]["persistence_days"]),
                     "calibration_days": calib_days},
        "cleaning": {"exercise": "missing on days with no resting heart rate and no sleep record (band not worn)",
                     "sleep_h": f"missing outside {SLEEP_ARTEFACT_H[0]}–{SLEEP_ARTEFACT_H[1]} h (recording artefacts)"},
        "real": real,
        "real_alarm_drivers": alarm_drivers(real_sets, calib_days),
        "real_model_alarm_days": alarm_days,
        "synthetic_same_inputs": synth_four,
        "synthetic_all_inputs": synth_all,
        "note": ("Alarm = yellow or worse (model) or a baseline alarm, counted after the 21-day calibration. "
                 "The PMData people are not labelled healthy (winter, flu season), so their alarms are not all false. "
                 "Missing inputs enter the model as 'at your normal', which makes it quieter. "
                 + DISCLAIMER),
    }
    write_json(RESULTS_DIR / "real_data_check.json", result)
    (RESULTS_DIR / "real_data_check.md").write_text(markdown(result), encoding="utf-8")
    print(markdown(result))
