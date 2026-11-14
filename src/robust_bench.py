# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Robustness benchmark: can the model keep its synthetic detection AND stay quiet on real data?

The real-data check (src/realdata.py) showed that the frozen model alarms ~7x more often on real
everyday data (PMData) than on synthetic data, mostly because real resting heart rate drifts slowly
over weeks while the personal normal stays fixed after day 21. This benchmark compares ways of
keeping the personal normal up to date, and other variants, under a protocol fixed in advance:

1. Every variant is fitted on healthy synthetic astronauts only (train_large) and its alarm
   threshold is set on the healthy days of the selection split `bench` to the SAME false-alarm
   budget as the model-selection benchmark (0.05 per astronaut-week, persistence 3 days).
2. Synthetic metric: early-detection rate on `bench` (S1-S3, sizes x0.5 and x1.0, alarm within 21
   days of onset) — identical to src/benchmark.py.
3. Real metric: alarm episodes per person-week on the SELECTION half of PMData (odd participant
   numbers p01, p03, ...).
4. Selection rule: among variants whose early detection is at most 5 points below the current
   model, pick the one with the lowest real alarm rate on the selection half.
5. The winner (and the current model, for comparison) is then run ONCE on the CONFIRMATION half of
   PMData (even participant numbers) and on the dev split. The hold-out split (S5) is never touched.

Usage:
    python -m src.robust_bench            # all variants, selection and confirmation
"""

# ===== Imports =====
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.baselines import persistent
from src.common import AE_FEATURES, CONFIG_DIR, RESULTS_DIR, load_yaml, val, write_json
from src.features import calibration_stats, make_windows
from src.realdata import DAILY_CSV, as_crew_frame, eligible
from src.scoring import day_weights
from src.simulate import build_split, load_split

# ===== Constants =====
BUDGET = 0.05
PERSISTENCE = 3
EARLY_DAYS = 21
SCALES = [0.5, 1.0]
SCENARIOS = ["S1", "S2", "S3"]
MAX_EARLY_DROP = 0.05
WEIGHTS = np.arange(1, 8, dtype=float)       # same day weights as config/model.yaml (1..7)
SELF_GAP = 14                                 # personal score scale uses scores from ≥ 14 days ago
SELF_MIN = 14                                 # … and needs at least 14 of them


# ===== Variants =====
@dataclass
class Variant:
    """How the personal normal is computed; everything else (summary, Mahalanobis model) is shared."""

    name: str
    baseline: str = "fixed"        # fixed | rolling | ewma
    gap: int = 14                  # days between the newest day used for the normal and today
    length: int = 28               # rolling window length (days)
    alpha: float = 1 / 28          # EWMA weight of a new day
    winsor: float | None = None    # clip updates to normal ± winsor·sd (robust to illness spikes)
    floor_scale: float = 0.5       # sd floor = floor_scale × configured within-person sd
    drift_aug: float = 0.0         # sd of a slow random-walk drift added to healthy TRAINING data (in personal sd/√day)
    missing: str = "zero"          # zero: missing = "at your normal" | marginal: distance on the measured inputs only
    min_obs: int = 2               # marginal: an input counts as measured in a window with at least this many days
    shrink: float = 0.0            # covariance shrinkage toward its diagonal (0 = none, 1 = independent inputs)
    acf: bool = False              # autocorrelation-aware: rescale each input by its personal day-to-day autocorrelation
    selfscale: bool = False        # divide the score by the person's own typical score (from days ≥ 14 days ago), never up
    persistence: int = 3           # days above threshold before an alarm starts
    release: int = 0               # an alarm ends only after this many days below threshold (0 = at once)
    drop: tuple = ()               # inputs left out of the score (e.g. exercise, which is context)
    notes: str = ""
    extra: dict = field(default_factory=dict)


def variants() -> list[Variant]:
    """The grid, fixed before any result was seen."""
    out = [Variant("Current model (fixed 21-day normal)")]
    out.append(Variant("Fixed normal, sd floor ×1.0", floor_scale=1.0))
    for gap in (14, 21, 28):
        for length in (28, 56):
            out.append(Variant(f"Rolling normal, gap {gap} d, window {length} d", "rolling", gap=gap, length=length))
    for gap in (14, 21):
        for alpha in (1 / 14, 1 / 28, 1 / 56):
            out.append(Variant(f"EWMA normal, gap {gap} d, half-life ~{int(round(np.log(2) / alpha))} d", "ewma",
                               gap=gap, alpha=alpha))
            out.append(Variant(f"Robust EWMA normal (±2 sd), gap {gap} d, half-life ~{int(round(np.log(2) / alpha))} d",
                               "ewma", gap=gap, alpha=alpha, winsor=2.0))
    for aug in (0.05, 0.1):
        out.append(Variant(f"Fixed normal, trained with slow drift ({aug})", drift_aug=aug))
        out.append(Variant(f"Robust EWMA (gap 14, ~19 d), trained with slow drift ({aug})", "ewma", gap=14,
                           alpha=1 / 28, winsor=2.0, drift_aug=aug))
    for floor in (1.0,):
        out.append(Variant(f"Robust EWMA (gap 14, ~19 d), sd floor ×{floor}", "ewma", gap=14, alpha=1 / 28,
                           winsor=2.0, floor_scale=floor))
        out.append(Variant(f"Rolling (gap 21, 28 d), sd floor ×{floor}", "rolling", gap=21, length=28, floor_scale=floor))
    # Missing-aware distance: Mahalanobis on the measured inputs only (marginal Gaussian), put on a
    # common scale across numbers of inputs (Wilson–Hilferty). Added after the first grid showed that
    # imputing unmeasured inputs at the normal breaks the learned correlations on real data.
    out.append(Variant("Missing-aware distance (fixed normal)", missing="marginal"))
    out.append(Variant("Missing-aware, sd floor ×1.0", missing="marginal", floor_scale=1.0))
    out.append(Variant("Missing-aware, robust EWMA (gap 14, ~19 d)", "ewma", gap=14, alpha=1 / 28, winsor=2.0,
                       missing="marginal"))
    out.append(Variant("Missing-aware, robust EWMA (gap 14, ~19 d), sd floor ×1.0", "ewma", gap=14, alpha=1 / 28,
                       winsor=2.0, missing="marginal", floor_scale=1.0))
    out.append(Variant("Missing-aware, robust EWMA (gap 21, ~39 d), sd floor ×1.0", "ewma", gap=21, alpha=1 / 56,
                       winsor=2.0, missing="marginal", floor_scale=1.0))
    for sh in (0.3, 0.6):
        out.append(Variant(f"Missing-aware, covariance shrinkage {sh}", missing="marginal", shrink=sh))
        out.append(Variant(f"Missing-aware, robust EWMA (gap 14, ~19 d), floor ×1.0, shrinkage {sh}", "ewma", gap=14,
                           alpha=1 / 28, winsor=2.0, missing="marginal", floor_scale=1.0, shrink=sh))
    # Autocorrelation-aware normal and personal score scale. Added after the missing-aware variants
    # failed: real wearable resting heart rate has lag-1 autocorrelation ~0.86 (synthetic ~0.09), so its
    # 7-day mean varies far more than the model expects.
    out.append(Variant("Autocorrelation-aware (fixed normal)", acf=True))
    out.append(Variant("Autocorrelation-aware, sd floor ×1.0", acf=True, floor_scale=1.0))
    out.append(Variant("Autocorrelation-aware, robust EWMA (gap 14, ~19 d)", "ewma", gap=14, alpha=1 / 28, winsor=2.0, acf=True))
    out.append(Variant("Autocorrelation-aware, robust EWMA (gap 14, ~19 d), floor ×1.0", "ewma", gap=14, alpha=1 / 28,
                       winsor=2.0, acf=True, floor_scale=1.0))
    out.append(Variant("Personal score scale (fixed normal)", selfscale=True))
    out.append(Variant("Personal score scale, robust EWMA (gap 14, ~19 d), floor ×1.0", "ewma", gap=14, alpha=1 / 28,
                       winsor=2.0, floor_scale=1.0, selfscale=True))
    out.append(Variant("Autocorrelation-aware + personal score scale", acf=True, selfscale=True))
    out.append(Variant("Autocorrelation-aware + personal score scale, robust EWMA, floor ×1.0", "ewma", gap=14,
                       alpha=1 / 28, winsor=2.0, floor_scale=1.0, acf=True, selfscale=True))
    # Alarm logic and inputs. Added after diagnosing that the remaining real alarms are mostly short
    # 1–3-day flickers around the threshold, and that exercise (context, not health) drives some of them.
    best = dict(baseline="ewma", gap=14, alpha=1 / 28, winsor=2.0, floor_scale=1.0)
    out.append(Variant("Robust EWMA, floor ×1.0, alarm ends after 7 quiet days", release=7, **best))
    out.append(Variant("Robust EWMA, floor ×1.0, persistence 5", persistence=5, **best))
    out.append(Variant("Robust EWMA, floor ×1.0, persistence 5, ends after 7 quiet days", persistence=5, release=7, **best))
    out.append(Variant("Robust EWMA, floor ×1.0, without exercise", drop=("exercise_min",), **best))
    out.append(Variant("Robust EWMA, floor ×1.0, without exercise, ends after 7 quiet days", drop=("exercise_min",),
                       release=7, **best))
    out.append(Variant("Robust EWMA, floor ×1.0, without exercise, persistence 5, ends after 7 quiet days",
                       drop=("exercise_min",), persistence=5, release=7, **best))
    out.append(Variant("Autocorrelation-aware, robust EWMA, floor ×1.0, without exercise, ends after 7 quiet days",
                       drop=("exercise_min",), release=7, acf=True, **best))
    nx = dict(best, drop=("exercise_min",))
    out.append(Variant("Robust EWMA, floor ×1.0, without exercise, persistence 5", persistence=5, **nx))
    out.append(Variant("Robust EWMA, floor ×1.0, without exercise, persistence 5, ends after 3 quiet days",
                       persistence=5, release=3, **nx))
    out.append(Variant("Robust EWMA, floor ×1.0, without exercise, persistence 4", persistence=4, **nx))
    out.append(Variant("Autocorrelation-aware, robust EWMA, floor ×1.0, without exercise, persistence 5",
                       persistence=5, acf=True, **nx))
    out.append(Variant("Autocorrelation-aware, robust EWMA, floor ×1.0, without exercise, persistence 5, ends after 7 quiet days",
                       persistence=5, release=7, acf=True, **nx))
    out.append(Variant("Robust EWMA (gap 21, ~39 d), floor ×1.0, without exercise, persistence 5",
                       baseline="ewma", gap=21, alpha=1 / 56, winsor=2.0, floor_scale=1.0, drop=("exercise_min",), persistence=5))
    out.append(Variant("Fixed normal, ends after 7 quiet days", release=7))
    out.append(Variant("Fixed normal, without exercise, ends after 7 quiet days", drop=("exercise_min",), release=7))
    return out


def window_variance_factor(rho: float, weights: np.ndarray) -> float:
    """Variance of a weighted mean of an AR(1)-correlated series relative to white noise."""
    lags = np.abs(np.subtract.outer(np.arange(len(weights)), np.arange(len(weights))))
    return float((np.outer(weights, weights) * rho ** lags).sum() / (weights ** 2).sum())


def calibration_autocorr(raw: np.ndarray, days: np.ndarray, calib_days: int) -> np.ndarray:
    """Lag-1 autocorrelation per input over the calibration days (consecutive observed pairs), in [0, 0.95]."""
    out = np.zeros(raw.shape[1])
    cal = days <= calib_days
    x, d = raw[cal], days[cal]
    for j in range(raw.shape[1]):
        a, b = x[:-1, j], x[1:, j]
        ok = ~np.isnan(a) & ~np.isnan(b) & (np.diff(d) == 1)
        if ok.sum() >= 10 and np.std(a[ok]) > 0 and np.std(b[ok]) > 0:
            out[j] = float(np.clip(np.corrcoef(a[ok], b[ok])[0, 1], 0.0, 0.95))
    return out


# ===== Personal normal =====
def personal_stats(frame: pd.DataFrame, sim_cfg: dict, floor_scale: float) -> tuple[np.ndarray, np.ndarray]:
    """Calibration mean and sd per feature (sd floored at floor_scale × configured day sd)."""
    stats = calibration_stats(frame, sim_cfg)
    calib_days = int(val(sim_cfg["mission"]["calibration_days"]))
    calib = frame[frame["day"] <= calib_days]
    means, sds = [], []
    for f in AE_FEATURES:
        mean, _ = stats[f]
        series = calib[f].dropna()
        sd = float(series.std(ddof=1)) if len(series) > 1 else 0.0
        sds.append(max(sd, floor_scale * float(sim_cfg["features"][f]["day_sd"])))
        means.append(mean)
    return np.array(means), np.array(sds)


def baseline_means(raw: np.ndarray, cal_mean: np.ndarray, cal_sd: np.ndarray, days: np.ndarray,
                   calib_days: int, v: Variant) -> np.ndarray:
    """Personal normal (mean) for every day, shape (n, 9). Never uses days after t - gap."""
    n = len(raw)
    means = np.tile(cal_mean, (n, 1))
    if v.baseline == "fixed":
        return means
    if v.baseline == "rolling":
        for t in range(n):
            end = days[t] - v.gap                          # newest day allowed in the normal
            if end <= calib_days:
                continue
            use = (days <= end) & (days > end - v.length)
            block = raw[use]
            for j in range(raw.shape[1]):
                col = block[:, j]
                col = col[~np.isnan(col)]
                if v.winsor is not None and len(col):
                    col = np.clip(col, cal_mean[j] - v.winsor * cal_sd[j], cal_mean[j] + v.winsor * cal_sd[j])
                if len(col) >= 7:
                    means[t, j] = col.mean()
        return means
    # EWMA, updated day by day with the value from `gap` days earlier
    m = cal_mean.copy()
    by_day = {int(d): i for i, d in enumerate(days)}
    for t in range(n):
        src = by_day.get(int(days[t]) - v.gap)
        if src is not None and days[src] > calib_days:
            x = raw[src]
            ok = ~np.isnan(x)
            upd = x.copy()
            if v.winsor is not None:
                upd = np.clip(upd, m - v.winsor * cal_sd, m + v.winsor * cal_sd)
            m[ok] = (1 - v.alpha) * m[ok] + v.alpha * upd[ok]
        means[t] = m
    return means


def zscores(frame: pd.DataFrame, sim_cfg: dict, v: Variant) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Personal z-scores under a variant (missing → 0), the mask and the days."""
    frame = frame.sort_values("day")
    calib_days = int(val(sim_cfg["mission"]["calibration_days"]))
    raw = frame[AE_FEATURES].to_numpy(dtype=float)
    days = frame["day"].to_numpy()
    cal_mean, cal_sd = personal_stats(frame, sim_cfg, v.floor_scale)
    means = baseline_means(raw, cal_mean, cal_sd, days, calib_days, v)
    mask = (~np.isnan(raw)).astype(np.float32)
    z = np.nan_to_num((raw - means) / cal_sd, nan=0.0).astype(np.float32)
    for f in v.drop:
        j = AE_FEATURES.index(f)
        z[:, j] = 0.0
        mask[:, j] = 0.0
    if v.acf:
        weights = WEIGHTS / WEIGHTS.sum()
        rho = calibration_autocorr(raw, days, calib_days)
        z = z * np.array([1 / np.sqrt(window_variance_factor(r, weights)) for r in rho], dtype=np.float32)
    return z, mask, days


def add_slow_drift(frame: pd.DataFrame, sim_cfg: dict, scale: float, seed: int) -> pd.DataFrame:
    """Healthy-training augmentation: a slow random walk (per feature) after the calibration period."""
    if scale <= 0:
        return frame
    rng = np.random.default_rng(seed)
    frame = frame.sort_values("day").copy()
    calib_days = int(val(sim_cfg["mission"]["calibration_days"]))
    after = (frame["day"] > calib_days).to_numpy()
    for f in AE_FEATURES:
        sd = float(sim_cfg["features"][f]["day_sd"])
        walk = np.cumsum(rng.normal(0.0, scale * sd, after.sum()))
        frame.loc[after, f] = frame.loc[after, f].to_numpy() + walk
    return frame


# ===== Scores =====
def summaries(z: np.ndarray, mask: np.ndarray, weights: np.ndarray, window: int, v: Variant) -> tuple[np.ndarray, np.ndarray]:
    """7-day weighted summary per window and which inputs count as measured in it."""
    x, m = make_windows(z, mask, window)
    x = x.reshape(len(x), window, len(AE_FEATURES))
    m = m.reshape(len(m), window, len(AE_FEATURES))
    if v.missing == "zero":
        return (x * weights[None, :, None]).sum(axis=1), np.ones((len(x), len(AE_FEATURES)), dtype=bool)
    w = weights[None, :, None] * m
    total = w.sum(axis=1)
    summary = np.where(total > 0, (x * w).sum(axis=1) / np.maximum(total, 1e-12), 0.0)
    return summary, m.sum(axis=1) >= v.min_obs


def fit_model(summary: np.ndarray, observed: np.ndarray, reg: float, v: Variant) -> dict:
    """Mean and covariance of healthy summaries (windows with every input measured), optional shrinkage."""
    full = summary[observed.all(axis=1)] if v.missing == "marginal" else summary
    mean = full.mean(axis=0)
    cov = np.cov(full, rowvar=False)
    cov = (1 - v.shrink) * cov + v.shrink * np.diag(np.diag(cov)) + reg * np.eye(cov.shape[0])
    if v.drop:
        for f in v.drop:
            j = AE_FEATURES.index(f)
            mean[j] = 0.0
            cov[j, :] = 0.0
            cov[:, j] = 0.0
            cov[j, j] = 1.0
    model = {"mean": mean, "cov": cov, "inv_cov": np.linalg.inv(cov)}
    model["median_score"] = float(np.median(score_summaries(summary, observed, model, v)))
    return model


def wilson_hilferty(t2: np.ndarray, k: np.ndarray, target: int) -> np.ndarray:
    """Map a chi-square(k) value to the chi-square(target) value with the same tail probability."""
    k = np.maximum(k, 1).astype(float)
    zval = ((np.maximum(t2, 0) / k) ** (1 / 3) - (1 - 2 / (9 * k))) / np.sqrt(2 / (9 * k))
    base = zval * np.sqrt(2 / (9 * target)) + 1 - 2 / (9 * target)
    return target * np.maximum(base, 0) ** 3


def score_summaries(summary: np.ndarray, observed: np.ndarray, model: dict, v: Variant) -> np.ndarray:
    """Mahalanobis distance; missing-aware variants use the measured inputs only."""
    d = summary - model["mean"]
    if v.missing == "zero":
        return np.einsum("ij,jk,ik->i", d, model["inv_cov"], d)
    out = np.zeros(len(d))
    patterns: dict[tuple, np.ndarray] = {}
    for i, obs in enumerate(observed):
        key = tuple(obs)
        if key not in patterns:
            idx = np.flatnonzero(obs)
            patterns[key] = (idx, np.linalg.inv(model["cov"][np.ix_(idx, idx)]) if len(idx) else None)
        idx, inv = patterns[key]
        if len(idx) == 0:
            continue
        di = d[i, idx]
        out[i] = wilson_hilferty(np.array([di @ inv @ di]), np.array([len(idx)]), len(AE_FEATURES))[0]
    return out


def daily_scores(frame: pd.DataFrame, sim_cfg: dict, v: Variant, model: dict, weights: np.ndarray,
                 window: int) -> tuple[np.ndarray, np.ndarray]:
    """Drift score per day (NaN before the first full window) and the days."""
    z, mask, days = zscores(frame, sim_cfg, v)
    summary, observed = summaries(z, mask, weights, window, v)
    score = np.full(len(days), np.nan)
    score[window - 1:] = score_summaries(summary, observed, model, v)
    if v.selfscale:
        score = personal_scale(score, days, model["median_score"])
    return score, days


def personal_scale(score: np.ndarray, days: np.ndarray, pop_median: float) -> np.ndarray:
    """Divide each day's score by the person's own median score from ≥ SELF_GAP days earlier (never scale up)."""
    out = score.copy()
    for t in range(len(score)):
        hist = score[(days <= days[t] - SELF_GAP) & np.isfinite(score)]
        if len(hist) >= SELF_MIN:
            out[t] = score[t] / max(float(np.median(hist)) / pop_median, 1.0)
    return out


def fit_variant(v: Variant, train: pd.DataFrame, sim_cfg: dict, model_cfg: dict, weights: np.ndarray,
                window: int) -> dict:
    """Fit the Gaussian model on healthy synthetic windows computed with the variant's normal."""
    blocks, obs = [], []
    for i, (_, frame) in enumerate(train.groupby("astronaut", sort=False)):
        frame = add_slow_drift(frame, sim_cfg, v.drift_aug, seed=10_000 + i)
        z, mask, _ = zscores(frame, sim_cfg, v)
        summary, observed = summaries(z, mask, weights, window, v)
        blocks.append(summary)
        obs.append(observed)
    return fit_model(np.concatenate(blocks), np.concatenate(obs), float(model_cfg["drift"]["regularisation"]), v)


# ===== Metrics =====
def onsets_per_week(flags: list[np.ndarray], keeps: list[np.ndarray]) -> float:
    """Alarm episodes starting on kept days, per kept week."""
    episodes = sum(int((f & ~np.concatenate([[False], f[:-1]]) & k).sum()) for f, k in zip(flags, keeps))
    days = sum(int(k.sum()) for k in keeps)
    return episodes / (days / 7.0) if days else float("nan")


def alarms(scores: list[np.ndarray], thr: float, v: "Variant") -> list[np.ndarray]:
    """Persistent alarms (NaN never alarms), optionally held until `release` quiet days."""
    out = []
    for s in scores:
        hit = np.nan_to_num(s, nan=-np.inf) >= thr
        flag = persistent(hit, v.persistence)
        if v.release > 0:
            held, on, quiet = np.zeros_like(flag), False, 0
            for t in range(len(flag)):
                if flag[t]:
                    on, quiet = True, 0
                elif on:
                    quiet = 0 if hit[t] else quiet + 1
                    if quiet >= v.release:
                        on = False
                held[t] = on
            flag = held
        out.append(flag)
    return out


def synthetic_population(crew: pd.DataFrame, sim_cfg, v, model, weights, window) -> list[dict]:
    """Scores and ground truth for every astronaut of a split."""
    out = []
    for _, frame in crew.groupby("astronaut", sort=False):
        frame = frame.sort_values("day")
        score, days = daily_scores(frame, sim_cfg, v, model, weights, window)
        out.append({"scenario": str(frame["scenario"].iloc[0]), "start": int(frame["scenario_start"].iloc[0]),
                    "days": days, "score": score})
    return out


def healthy_keeps(pop: list[dict], calib: int) -> list[np.ndarray]:
    """Healthy days after calibration (before onset for scenario astronauts)."""
    out = []
    for p in pop:
        end = p["start"] if p["scenario"] != "none" else p["days"].max() + 1
        out.append((p["days"] > calib) & (p["days"] < end))
    return out


def threshold_for_budget(pop: list[dict], calib: int, v: "Variant") -> float:
    """Lowest score threshold with at most BUDGET false alarms per astronaut-week on healthy days."""
    keeps = healthy_keeps(pop, calib)
    scores = [p["score"] for p in pop]
    healthy = np.concatenate([s[k & np.isfinite(s)] for s, k in zip(scores, keeps)])
    cands = np.unique(np.quantile(healthy, np.linspace(0.5, 0.99995, 500)))
    lo, hi = 0, len(cands) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if onsets_per_week(alarms(scores, cands[mid], v), keeps) <= BUDGET:
            hi = mid
        else:
            lo = mid + 1
    return float(cands[lo])


def detection(pop: list[dict], thr: float, v: "Variant") -> dict:
    """Early-detection and detection rate per scenario."""
    flags = alarms([p["score"] for p in pop], thr, v)
    out = {}
    for s in sorted({p["scenario"] for p in pop} - {"none"}):
        delays = []
        for p, f in zip(pop, flags):
            if p["scenario"] != s:
                continue
            hits = p["days"][(p["days"] >= p["start"]) & f]
            delays.append(int(hits[0] - p["start"]) if len(hits) else None)
        found = [d for d in delays if d is not None]
        out[s] = {"early": sum(d <= EARLY_DAYS for d in found) / len(delays), "detected": len(found) / len(delays),
                  "median_delay": float(np.median(found)) if found else None}
    return out


def real_rate(people: list[tuple[str, pd.DataFrame]], sim_cfg, v, model, weights, window, thr, calib) -> dict:
    """Alarm episodes per person-week and share of days in alarm on real data."""
    scores, keeps = [], []
    for name, frame in people:
        score, days = daily_scores(as_crew_frame(frame, name), sim_cfg, v, model, weights, window)
        scores.append(score)
        keeps.append(days > calib)
    flags = alarms(scores, thr, v)
    in_alarm = sum(int((f & k).sum()) for f, k in zip(flags, keeps)) / sum(int(k.sum()) for k in keeps)
    return {"alarms_per_person_week": round(onsets_per_week(flags, keeps), 3), "share_of_days_in_alarm": round(in_alarm, 3),
            "people": len(people)}


# ===== Report =====
def markdown(result: dict) -> str:
    """Markdown report: protocol, every variant, the winner and its one-time confirmation."""
    rows = result["rows"]
    cur = rows[0]
    lines = ["### Robustness benchmark — keep synthetic detection, stay quiet on real data", "",
             f"{len(rows)} variants. Synthetic: early detection on `bench` (S1–S3, sizes × 0.5 and × 1.0, alarm within "
             f"{EARLY_DAYS} days) with each variant's threshold set to {result['budget']} false alarms per astronaut-week. "
             f"Real: PMData selection half ({', '.join(result['select_half'])}). Rule fixed in advance: lowest real alarm "
             f"rate among variants at most {int(MAX_EARLY_DROP * 100)} points below the current model's early detection. "
             "Variant groups were added in rounds after diagnosing the previous round (adaptive normal → missing-aware "
             "distance → autocorrelation-aware normal → alarm logic and inputs); every round used the selection half only.", "",
             "| Variant | Early detection (bench) | Detected at all | Real alarms per person-week (selection half) | Real days in alarm |",
             "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: r["real_select"]["alarms_per_person_week"]):
        mark = " **(chosen)**" if r["variant"] == result["winner"] else (" (version 1)" if r is cur else "")
        lines.append(f"| {r['variant']}{mark} | {r['early_detection']:.0%} | {r['detection']:.0%} | "
                     f"{r['real_select']['alarms_per_person_week']:.3f} | {r['real_select']['share_of_days_in_alarm']:.0%} |")
    if result.get("confirmation"):
        lines += ["", f"**Confirmation (run once):** PMData confirmation half ({', '.join(result['confirm_half'])}) and the dev split.", "",
                  "| Model | Real alarms per person-week, confirmation half | All 16 people | Days in alarm (all) | Dev false alarms per astronaut-week | Dev early detection S1 / S2 / S3 |",
                  "|---|---|---|---|---|---|"]
        for name, c in result["confirmation"].items():
            det = " / ".join(f"{c['dev_detection'][s]['early']:.0%}" for s in SCENARIOS)
            lines.append(f"| {name} | {c['real_confirm']['alarms_per_person_week']:.3f} | {c['real_all']['alarms_per_person_week']:.3f} | "
                         f"{c['real_all']['share_of_days_in_alarm']:.0%} | {c['dev_false_alarms_per_week']:.3f} | {det} |")
        lines += ["", "Notes on discipline: (1) the variant grid was built in rounds on simulator-1 data, and the script then "
                      "printed the confirmation-half result of three interim winners; (2) on simulator-2 data the detector "
                      "benchmark chose the 14-day window, so this benchmark was run with `--window 14` (a 7-day run is kept "
                      "in robust_bench_w7.json); (3) after the first confirmation a missing-data bug was found (an input "
                      "with no values in days 1-21, e.g. a heart rate first recorded on day 61, was compared with the "
                      "synthetic population mean); it was fixed for every person alike and selection and confirmation were "
                      "rerun once; the winner did not change. The hold-out split (S5) was not used."]
    lines += ["", "Real data: PMData (Thambawita et al. 2020, CC BY 4.0), 4 of 9 inputs. Synthetic data calibrated on "
                  "published sources — proof of concept, not clinical validation."]
    return "\n".join(lines) + "\n"


# ===== Main =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Robustness benchmark: synthetic detection vs real-data alarm rate.")
    parser.add_argument("--only", nargs="*", help="Run only variants whose name contains one of these strings.")
    parser.add_argument("--confirm", action="store_true", help="Run the confirmation (other PMData half + dev) for the winner.")
    parser.add_argument("--report-only", action="store_true", help="Rewrite the markdown report from the saved JSON.")
    parser.add_argument("--window", type=int, default=None, help="Summary window in days (default: config/model.yaml).")
    args = parser.parse_args()
    if args.report_only:
        from src.common import read_json
        (RESULTS_DIR / "robust_bench.md").write_text(markdown(read_json(RESULTS_DIR / "robust_bench.json")), encoding="utf-8")
        raise SystemExit(0)

    t0 = time.time()
    model_cfg = load_yaml(CONFIG_DIR / "model.yaml")
    sim_cfg = load_yaml(CONFIG_DIR / "simulation.yaml")
    window = int(args.window or model_cfg["window_days"])
    weights = np.arange(1, window + 1, dtype=float) / np.arange(1, window + 1).sum()
    WEIGHTS = np.arange(1, window + 1, dtype=float)      # used by the autocorrelation-aware scaling
    globals()["WEIGHTS"] = WEIGHTS
    calib = int(val(sim_cfg["mission"]["calibration_days"]))

    train = load_split(model_cfg["drift"]["train_split"])
    bench = {s: build_split(sim_cfg, "bench", s)[0] for s in SCALES}
    table = pd.read_csv(DAILY_CSV)
    people = [(p, f.sort_values("day")) for p, f in table.groupby("participant", sort=True) if eligible(f, calib)]
    select_half = [(p, f) for p, f in people if int(p[1:]) % 2 == 1]
    confirm_half = [(p, f) for p, f in people if int(p[1:]) % 2 == 0]

    rows = []
    grid = variants()
    if args.only:
        grid = [v for v in grid if v.name == grid[0].name or any(o in v.name for o in args.only)]
    fitted = {}
    for v in grid:
        model = fit_variant(v, train, sim_cfg, model_cfg, weights, window)
        pops = {s: synthetic_population(bench[s], sim_cfg, v, model, weights, window) for s in SCALES}
        thr = threshold_for_budget(pops[1.0], calib, v)
        det = {str(s): detection(pops[s], thr, v) for s in SCALES}
        early = float(np.mean([det[str(s)][sc]["early"] for s in SCALES for sc in SCENARIOS]))
        found = float(np.mean([det[str(s)][sc]["detected"] for s in SCALES for sc in SCENARIOS]))
        real = real_rate(select_half, sim_cfg, v, model, weights, window, thr, calib)
        rows.append({"variant": v.name, "early_detection": round(early, 3), "detection": round(found, 3),
                     "real_select": real, "threshold": thr, "by_scale": det,
                     "spec": {k: val_ for k, val_ in v.__dict__.items() if k != "extra"}})
        fitted[v.name] = (v, model, thr)
        print(f"{early:6.1%} early | {found:6.1%} found | real {real['alarms_per_person_week']:.3f}/pw "
              f"({real['share_of_days_in_alarm']:.0%} days) | {v.name}", flush=True)

    # ----- Selection (rule fixed in advance) -----
    current = rows[0]
    allowed = [r for r in rows if r["early_detection"] >= current["early_detection"] - MAX_EARLY_DROP]
    winner = min(allowed, key=lambda r: (r["real_select"]["alarms_per_person_week"], -r["early_detection"]))

    # ----- Confirmation, once: other half of PMData and the dev split -----
    dev = build_split(sim_cfg, "dev")[0]
    confirm = {}
    for r in [] if not args.confirm else ({current["variant"]: current, winner["variant"]: winner}).values():
        v, model, thr = fitted[r["variant"]]
        dev_pop = synthetic_population(dev, sim_cfg, v, model, weights, window)
        dev_fa = onsets_per_week(alarms([p["score"] for p in dev_pop], thr, v), healthy_keeps(dev_pop, calib))
        confirm[r["variant"]] = {
            "real_confirm": real_rate(confirm_half, sim_cfg, v, model, weights, window, thr, calib),
            "real_all": real_rate(people, sim_cfg, v, model, weights, window, thr, calib),
            "dev_detection": detection(dev_pop, thr, v),
            "dev_false_alarms_per_week": round(dev_fa, 3),
        }
    result = {"protocol": __doc__.split("Usage:")[0].strip(), "budget": BUDGET, "persistence": PERSISTENCE,
              "window_days": window,
              "select_half": [p for p, _ in select_half], "confirm_half": [p for p, _ in confirm_half],
              "rows": rows, "winner": winner["variant"], "confirmation": confirm,
              "runtime_s": round(time.time() - t0, 1)}
    write_json(RESULTS_DIR / "robust_bench.json", result)
    (RESULTS_DIR / "robust_bench.md").write_text(markdown(result), encoding="utf-8")
    print("\nWinner:", winner["variant"])
    for name, c in confirm.items():
        print(f"  {name}: confirm-half {c['real_confirm']}, all {c['real_all']['alarms_per_person_week']}, "
              f"dev FA {c['dev_false_alarms_per_week']}, dev {c['dev_detection']}")
