# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""JPL Horizons Earth–Mars delay: parsing and the committed cache, without network access."""

import datetime as dt
import socket

import pytest

from src import horizons

# Four rows of a real Horizons response (CSV, quantities 20 and 23), trimmed.
SAMPLE = """ Date__(UT)__HR:MN, , ,            delta,     deldot,     S-O-T,/r,
$$SOE
 2024-May-01 00:00, , , 1.97660254853535, -6.5131033,   40.8580,/L,
 2024-May-02 00:00, , , 1.97284087735422, -6.5139153,   41.0580,/L,
$$EOE
"""


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", refuse)


def test_one_au_is_about_499_light_seconds():
    assert horizons.light_time_s(1.0) == pytest.approx(499.005, abs=0.001)


def test_parse_gives_mission_day_distance_delay_and_sun_angle():
    rows = horizons.parse_ephemeris(SAMPLE, dt.date(2024, 5, 1))
    assert [r["day"] for r in rows] == [1, 2]
    assert rows[0]["date"] == "2024-05-01"
    assert rows[0]["distance_au"] == pytest.approx(1.976603)
    assert rows[0]["one_way_s"] == pytest.approx(986.3, abs=0.1)     # about 16.4 minutes
    assert rows[1]["sun_angle_deg"] == pytest.approx(41.058)


def test_a_response_without_ephemeris_is_rejected():
    with pytest.raises(ValueError):
        horizons.parse_ephemeris("API error: no data", dt.date(2024, 5, 1))


def test_committed_cache_covers_every_mission_day():
    delay = horizons.delay_by_day(120)
    assert delay is not None and len(delay["one_way_s"]) == 120
    assert all(600 < s < 1320 for s in delay["one_way_s"])           # inside NASA's 0–22 min range
    assert min(delay["sun_angle_deg"]) > 10                           # no solar conjunction in this window


def test_missing_cache_means_no_real_delay(tmp_path, monkeypatch):
    monkeypatch.setattr(horizons, "CACHE_PATH", tmp_path / "absent.json")
    assert horizons.delay_by_day(120) is None
