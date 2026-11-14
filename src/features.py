# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Personal normalisation and 7-day windows.

Each astronaut is normalised against their OWN normal: the model sees deviations from that person's
normal, not absolute values. Two kinds of personal z-scores are kept:

- `z` (fixed normal): calibration days 1-21 only. Used by the single-indicator baseline B2, the sensor
  check and the normal bands shown in the app — unchanged since version 1.
- `x` (model windows): built from the model's personal normal, set in config/model.yaml → normal.
  Version 2 (chosen by src/robust_bench.py on real PMData + synthetic data): the normal follows slow
  changes with a robust exponentially weighted mean that only uses days at least 14 days old (a
  developing illness cannot be absorbed within two weeks), each input is scaled by its personal
  day-to-day autocorrelation (smoothed wearable signals vary more week to week), and inputs listed in
  `exclude` (exercise: context, not health) are left out of the score.
"""

# ===== Imports =====
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.common import AE_FEATURES, val

MIN_CALIBRATION_VALUES = 7   # an input needs at least 7 values in days 1-21 to get a personal normal


# ===== Data structures =====
@dataclass
class AstronautWindows:
    """Normalised data and 7-day windows for one astronaut."""

    astronaut: str
    days: np.ndarray          # mission day of every row (1..n)
    z: np.ndarray             # (n, 9) personal z-scores, 0 where missing
    mask: np.ndarray          # (n, 9) 1 = observed, 0 = missing
    window_days: np.ndarray   # mission day that ends each window (7..n)
    x: np.ndarray             # (n - w + 1, w * 9) flattened windows
    m: np.ndarray             # (n - w + 1, w * 9) flattened masks
    stats: dict               # feature -> (mean, sd) over the calibration period
    z_model: np.ndarray | None = None   # (n, 9) z-scores under the model's normal (= z for the fixed normal)


# ===== Normalisation =====
def calibration_stats(frame: pd.DataFrame, sim_cfg: dict) -> dict[str, tuple[float, float]]:
    """Mean and sd of every AE feature over the calibration days.

    The sd is floored at half the configured within-person sd so that a very flat calibration
    period (e.g. identical mood scores) cannot produce exploding z-scores.
    """
    calib_days = int(val(sim_cfg["mission"]["calibration_days"]))
    calib = frame[frame["day"] <= calib_days]
    stats = {}
    for f in AE_FEATURES:
        series = calib[f].dropna()
        # Without enough calibration values there is no personal normal yet: the input is not scored
        # (NaN mean → z-score 0) rather than compared with a population average.
        mean = float(series.mean()) if len(series) >= MIN_CALIBRATION_VALUES else float("nan")
        sd = float(series.std(ddof=1)) if len(series) > 1 else 0.0
        floor = 0.5 * float(sim_cfg["features"][f]["day_sd"])
        stats[f] = (mean, max(sd, floor))
    return stats


def zscore_matrix(frame: pd.DataFrame, stats: dict[str, tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    """Personal z-scores (missing → 0) and the observation mask, ordered by day."""
    raw = frame[AE_FEATURES].to_numpy(dtype=float)
    mask = (~np.isnan(raw)).astype(np.float32)
    means = np.array([stats[f][0] for f in AE_FEATURES])
    sds = np.array([stats[f][1] for f in AE_FEATURES])
    z = np.nan_to_num((raw - means) / sds, nan=0.0).astype(np.float32)
    return z, mask


# ===== Model normal (version 2) =====
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


def robust_ewma_normal(raw: np.ndarray, days: np.ndarray, start: np.ndarray, sd: np.ndarray, calib_days: int,
                       gap: int, alpha: float, winsor: float) -> np.ndarray:
    """Personal normal per day: an EWMA updated with the value from `gap` days earlier, clipped to
    normal ± winsor·sd so that a sudden change moves the normal only slowly. Uses no day after t - gap."""
    means = np.empty_like(raw)
    m = start.copy()
    row_of = {int(d): i for i, d in enumerate(days)}
    for t in range(len(raw)):
        src = row_of.get(int(days[t]) - gap)
        if src is not None and days[src] > calib_days:
            x = raw[src]
            ok = ~np.isnan(x)
            upd = np.clip(x, m - winsor * sd, m + winsor * sd)
            m[ok] = (1 - alpha) * m[ok] + alpha * upd[ok]
        means[t] = m
    return means


def model_zscores(frame: pd.DataFrame, sim_cfg: dict, normal: dict, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Z-scores and mask under the version-2 normal (see module docstring)."""
    calib_days = int(val(sim_cfg["mission"]["calibration_days"]))
    raw = frame[AE_FEATURES].to_numpy(dtype=float)
    days = frame["day"].to_numpy()
    calib = frame[frame["day"] <= calib_days]
    means, sds = [], []
    for f in AE_FEATURES:
        series = calib[f].dropna()
        means.append(float(series.mean()) if len(series) >= MIN_CALIBRATION_VALUES else float("nan"))
        sd = float(series.std(ddof=1)) if len(series) > 1 else 0.0
        sds.append(max(sd, float(normal["sd_floor_scale"]) * float(sim_cfg["features"][f]["day_sd"])))
    start, sd = np.array(means), np.array(sds)
    if normal["baseline"] == "robust_ewma":
        centre = robust_ewma_normal(raw, days, start, sd, calib_days, int(normal["gap_days"]),
                                    float(normal["alpha"]), float(normal["winsor_sd"]))
    else:
        centre = np.tile(start, (len(raw), 1))
    mask = (~np.isnan(raw)).astype(np.float32)
    z = np.nan_to_num((raw - centre) / sd, nan=0.0)
    if normal.get("autocorrelation_aware"):
        w = weights / weights.sum()
        rho = calibration_autocorr(raw, days, calib_days)
        z = z * np.array([1 / np.sqrt(window_variance_factor(r, w)) for r in rho])
    for f in normal.get("exclude", []):
        j = AE_FEATURES.index(f)
        z[:, j] = 0.0
        mask[:, j] = 0.0
    return z.astype(np.float32), mask


def make_windows(z: np.ndarray, mask: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    """Stack consecutive `window`-day blocks into flat vectors (day-major order)."""
    n = z.shape[0]
    idx = np.arange(window)[None, :] + np.arange(n - window + 1)[:, None]
    x = z[idx].reshape(len(idx), -1)
    m = mask[idx].reshape(len(idx), -1)
    return x, m


def astronaut_windows(frame: pd.DataFrame, sim_cfg: dict, window: int, normal: dict | None = None,
                      weights: np.ndarray | None = None) -> AstronautWindows:
    """Full feature pipeline for one astronaut. `normal` = config/model.yaml → normal (None: fixed normal)."""
    frame = frame.sort_values("day")
    stats = calibration_stats(frame, sim_cfg)
    z, mask = zscore_matrix(frame, stats)
    if normal:
        w = np.arange(1, window + 1, dtype=float) if weights is None else np.asarray(weights, dtype=float)
        z_model, m_model = model_zscores(frame, sim_cfg, normal, w)
    else:
        z_model, m_model = z, mask
    x, m = make_windows(z_model, m_model, window)
    days = frame["day"].to_numpy()
    return AstronautWindows(str(frame["astronaut"].iloc[0]), days, z, mask, days[window - 1:], x, m, stats, z_model)


def crew_windows(crew: pd.DataFrame, sim_cfg: dict, window: int, normal: dict | None = None,
                 weights: np.ndarray | None = None) -> list[AstronautWindows]:
    """Feature pipeline for every astronaut of a split (order of first appearance)."""
    return [astronaut_windows(frame, sim_cfg, window, normal, weights) for _, frame in crew.groupby("astronaut", sort=False)]


def normal_bands(stats: dict[str, tuple[float, float]], k: float = 2.0) -> dict[str, list[float]]:
    """Personal normal band (mean ± k sd) per feature, for the UI Trends screen."""
    return {f: ([round(mean - k * sd, 2), round(mean + k * sd, 2)] if np.isfinite(mean) else None)
            for f, (mean, sd) in stats.items()}
