# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Sources added after the freeze (config/sources_extra.yaml) must describe the frozen values exactly."""

import pytest

from src.common import CONFIG_DIR, load_yaml
from src.report_sources import extra_sources, table

EXTRA = extra_sources()
VERDICTS = {"confirmed", "close", "partly", "not_verified"}


def frozen_value(entry: dict):
    """The value an entry points to in the frozen config file."""
    node = load_yaml(CONFIG_DIR / entry["file"])
    for part in entry["entry"].split("."):
        node = node[part]
    return node[entry["key"]]


@pytest.mark.parametrize("entry", EXTRA, ids=lambda e: f"{e['entry']}.{e['key']}")
def test_each_entry_matches_the_frozen_config(entry):
    assert entry["verdict"] in VERDICTS
    assert frozen_value(entry) == entry["value"]


@pytest.mark.parametrize("entry", EXTRA, ids=lambda e: f"{e['entry']}.{e['key']}")
def test_a_source_is_claimed_only_when_verified(entry):
    if entry["verdict"] == "not_verified":
        assert entry["source"] is None
    else:
        assert entry["source"] and ("http" in entry["source"] or "doi" in entry["source"])


def test_source_table_lists_the_post_freeze_entries():
    text = table()
    assert "Sources checked after the configs were frozen" in text
    assert text.count("PARTLY SOURCED") == sum(1 for e in EXTRA if e["verdict"] == "confirmed")
