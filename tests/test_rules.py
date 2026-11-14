# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Respond path: the critical (red) thresholds work on their own, without the model."""

import numpy as np
import pandas as pd
import pytest

from src.baselines import b1_alarm, critical_alarm
from src.common import CONFIG_DIR, INDICATORS, load_yaml

RULES = load_yaml(CONFIG_DIR / "rules.yaml")
NORMAL = {"sys": 118, "dia": 76, "hr": 64, "glucose": 92, "temp": 36.7, "sleep_h": 7.0,
          "mood": 4, "reaction_ms": 290, "exercise_min": 60}


def frame(days: int = 5, **overrides_on_day3) -> pd.DataFrame:
    """A short run of normal days; day 3 gets the given values."""
    rows = [{"day": d, **NORMAL} for d in range(1, days + 1)]
    rows[2].update(overrides_on_day3)
    return pd.DataFrame(rows)


def beyond(rule: dict) -> float:
    """A value just past a rule's threshold, in the direction of its operator."""
    step = 0.1 if rule["feature"] == "temp" else 1
    return float(rule["value"]) + (step if rule["op"] in ("gt", "ge") else -step)


@pytest.mark.parametrize("rule", RULES["critical_rules"], ids=lambda r: f"{r['feature']}-{r['op']}-{r['value']}")
def test_each_critical_rule_fires_on_the_same_day(rule):
    alarm, features = critical_alarm(frame(**{rule["feature"]: beyond(rule)}), RULES)
    assert alarm.tolist() == [False, False, True, False, False]   # one day is enough, no persistence
    assert rule["feature"] in features[2]


def test_normal_days_raise_no_critical_alert():
    alarm, _ = critical_alarm(frame(), RULES)
    assert not alarm.any()


def test_missing_values_never_trigger_a_rule():
    alarm, _ = critical_alarm(frame(**{f: np.nan for f in INDICATORS}), RULES)
    assert not alarm.any()


def test_critical_alerts_need_no_model():
    """critical_alarm takes only the measured values and the rules: no scorer, no fitted model."""
    import inspect
    assert list(inspect.signature(critical_alarm).parameters) == ["frame", "rules_cfg"]


def test_clinical_limits_baseline_waits_for_persistence():
    """B1 (fixed clinical limits) is not the safety net: a single bad day is not enough for it."""
    rule = next(r for r in RULES["b1_rules"] if int(r.get("persistence_days", 1)) > 1)
    assert not b1_alarm(frame(**{rule["feature"]: beyond(rule)}), RULES).any()
