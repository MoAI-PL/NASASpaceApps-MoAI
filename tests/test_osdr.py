# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""NASA OSDR Inspiration4 glucose check: parsing and statistics, from the committed table, offline."""

import socket

import pandas as pd
import pytest

from src import osdr
from src.common import CONFIG_DIR, load_yaml

GLUCOSE_CFG = {"pop_mean": 90, "pop_sd": 8, "day_sd": 6}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", refuse)


def cmp_rows(values: dict[tuple[str, str], float]) -> pd.DataFrame:
    """A CMP table in the OSDR long format; one glucose row per (subject, timepoint), plus noise rows."""
    rows = [{"ANALYTE": "GLUCOSE", "VALUE": v, "UNITS": "mg/dL", "SUBJECT_ID": s, "timepoint": t}
            for (s, t), v in values.items()]
    rows.append({"ANALYTE": "SODIUM", "VALUE": 140, "UNITS": "mmol/L", "SUBJECT_ID": "C001", "timepoint": "L-3"})
    return pd.DataFrame(rows)


def test_only_preflight_draws_are_compared():
    g = osdr.glucose_table(cmp_rows({("C001", "L-3"): 80, ("C001", "L-44"): 90,
                                     ("C002", "L-3"): 70, ("C002", "L-44"): 80, ("C002", "R+45"): 40}))
    result = osdr.summarise(g, GLUCOSE_CFG)
    assert result["preflight_draws"] == 4
    assert result["real_preflight"]["mean"] == 80.0
    assert result["postflight_flagged_below_50"] == [{"subject": "C002", "timepoint": "R+45", "value": 40.0}]


def test_unexpected_units_are_rejected():
    table = cmp_rows({("C001", "L-3"): 4.4})
    table.loc[0, "UNITS"] = "mmol/L"
    with pytest.raises(ValueError):
        osdr.glucose_table(table)


def test_committed_table_gives_the_reported_comparison():
    """The README numbers come from the committed OSDR table and the frozen simulator config."""
    cfg = load_yaml(CONFIG_DIR / "simulation.yaml")["features"]["glucose"]
    result = osdr.summarise(osdr.glucose_table(pd.read_csv(osdr.CACHE_CSV)), cfg)
    assert (result["crew"], result["preflight_draws"]) == (4, 12)
    assert result["real_preflight"]["mean"] == pytest.approx(75.3, abs=0.05)
    assert result["checks"]["real_mean_inside_simulated_population_2sd"] is True
