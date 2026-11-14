# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Hold-out discipline (CLAUDE.md rule 7), checked without ever touching the S5 data.

Only the guard and the recorded result are tested: no test loads the test split or runs the
evaluation, so running the suite can never become a second hold-out run.
"""

import pytest

from src.common import CONFIG_DIR, config_hash, load_yaml, read_json
from src.evaluate import FINAL_PATH, holdout_guard


def test_test_split_needs_final_flag(tmp_path):
    assert "--final" in holdout_guard("test", final=False, tune=False, final_path=tmp_path / "none.json")


def test_test_split_refuses_a_second_run(tmp_path):
    done = tmp_path / "final_test.json"
    done.write_text("{}", encoding="utf-8")
    assert "must not be re-run" in holdout_guard("test", final=True, tune=False, final_path=done)


def test_the_recorded_hold_out_blocks_any_rerun():
    """The real result file exists, so `--split test --final` is refused in this repository."""
    assert FINAL_PATH.exists()
    assert "must not be re-run" in holdout_guard("test", final=True, tune=False, final_path=FINAL_PATH)


@pytest.mark.parametrize("split", ["test", "dev_s4"])
def test_no_tuning_outside_the_selection_splits(split, tmp_path):
    assert "selection splits" in holdout_guard(split, final=True, tune=True, final_path=tmp_path / "none.json")


@pytest.mark.parametrize("split", ["bench", "dev"])
def test_selection_splits_are_allowed(split, tmp_path):
    assert holdout_guard(split, final=False, tune=True, final_path=FINAL_PATH) is None


def test_frozen_configs_still_match_the_hold_out_record():
    """The configs that produced final_test.json are unchanged: same hashes as recorded then.

    If a number in config/*.yaml changes, the recorded hold-out result no longer belongs to the
    code; this test fails instead of letting that happen silently.
    """
    recorded = read_json(FINAL_PATH)["config_hashes"]
    current = {name: config_hash(load_yaml(CONFIG_DIR / f"{file}.yaml"))
               for name, file in [("model", "model"), ("sim", "simulation"), ("rules", "rules")]}
    assert current == recorded
