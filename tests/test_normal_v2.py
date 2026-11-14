# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Tests for the version-2 personal normal and the alarm hold."""

import numpy as np

from src.features import calibration_autocorr, robust_ewma_normal, window_variance_factor
from src.scoring import ae_alarm, hold


def test_normal_never_uses_recent_days():
    days = np.arange(1, 61)
    raw = np.zeros((60, 1))
    raw[45:, 0] = 100.0                          # a jump on day 46
    means = robust_ewma_normal(raw, days, np.zeros(1), np.ones(1), calib_days=21, gap=14, alpha=0.5, winsor=2.0)
    assert np.all(means[:59, 0] == 0.0)          # days 46..59 are < 14 days old until day 60
    assert means[59, 0] > 0.0                    # day 60 may use day 46


def test_normal_moves_at_most_winsor_sd_per_update():
    days = np.arange(1, 41)
    raw = np.full((40, 1), 50.0)
    means = robust_ewma_normal(raw, days, np.zeros(1), np.ones(1), calib_days=21, gap=14, alpha=1.0, winsor=2.0)
    assert means[35, 0] == 2.0                   # first update (day 36 uses day 22): clipped to 0 + 2 sd


def test_autocorrelation_factor():
    w = np.arange(1, 8, dtype=float)
    w = w / w.sum()
    assert abs(window_variance_factor(0.0, w) - 1.0) < 1e-12
    assert window_variance_factor(0.86, w) > 3.0  # a smoothed signal's weekly mean varies far more
    rng = np.random.default_rng(1)
    x = np.cumsum(rng.normal(size=(21, 1)), axis=0)
    assert calibration_autocorr(x, np.arange(1, 22), 21)[0] > 0.5


def test_hold_keeps_alarm_until_quiet_days():
    hit = np.array([1, 1, 1, 0, 1, 0, 0, 0, 0], dtype=bool)
    flags = np.array([0, 0, 1, 0, 0, 0, 0, 0, 0], dtype=bool)
    out = hold(flags, hit, release=3)
    assert list(out.astype(int)) == [0, 0, 1, 1, 1, 1, 1, 0, 0]


def test_ae_alarm_persistence_and_release():
    sai = np.array([95, 95, 95, 95, 95, 10, 10, 95, 10, 10, 10], dtype=float)
    assert ae_alarm(sai, 90, 5).sum() == 1                       # starts after 5 days, ends at once
    assert ae_alarm(sai, 90, 5, release=3).astype(int).tolist() == [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0]
