# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""NASA DONKI solar particle events are read from the committed cache, with no network access."""

import socket

import pytest

from src import donki
from src.common import write_json


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any attempt to open a network connection fails the test."""
    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", refuse)


def test_committed_cache_gives_the_mission_event_days():
    days, status = donki.sep_event_days("2024-05-01", 120)
    assert status == "cached"
    assert days == [9, 10, 11, 13, 39, 43, 84, 92, 97]


def test_events_carry_their_donki_link():
    events = donki.sep_events("2024-05-01", 120)
    assert events and all(e["link"].startswith("https://ccmc.gsfc.nasa.gov/DONKI/") for e in events)
    assert [e["day"] for e in events] == sorted(e["day"] for e in events)


def test_events_outside_the_window_and_bad_dates_are_skipped(tmp_path, monkeypatch):
    cache = tmp_path / "donki_sep.json"
    write_json(cache, {"events": [
        {"sepID": "a", "eventTime": "2024-05-01T10:00Z", "link": "x"},   # day 1
        {"sepID": "b", "eventTime": "2024-04-30T10:00Z", "link": "x"},   # before the mission
        {"sepID": "c", "eventTime": "2024-08-29T10:00Z", "link": "x"},   # day 121, after it
        {"sepID": "d", "eventTime": "not a date", "link": "x"},
    ]})
    monkeypatch.setattr(donki, "CACHE_PATH", cache)
    assert donki.sep_event_days("2024-05-01", 120) == ([1], "cached")


def test_missing_cache_means_no_events(tmp_path, monkeypatch):
    monkeypatch.setattr(donki, "CACHE_PATH", tmp_path / "absent.json")
    assert donki.sep_event_days("2024-05-01", 120) == ([], "missing")
    assert donki.sep_events("2024-05-01", 120) == []
