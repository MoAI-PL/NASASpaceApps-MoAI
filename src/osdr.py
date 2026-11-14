# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""Plausibility check of the simulator against real astronaut blood tests (NASA OSDR, Inspiration4).

Data: NASA Open Science Data Repository study OSD-575, "SpaceX Inspiration4 Blood Serum Metabolic
Panel" — the comprehensive metabolic panel (CMP) of the four Inspiration4 crew members at three
pre-flight (L-92, L-44, L-3) and four post-flight draws (Overbey et al. 2024, Nature,
doi:10.1038/s41586-024-07639-y). Of our nine daily inputs only glucose is in this panel.

This is a comparison only: nothing is fitted, the simulator is NOT calibrated on it, and
config/simulation.yaml stays frozen (the hold-out result depends on it). The pre-flight draws
are compared with the simulator's healthy glucose parameters (population mean and spread,
day-to-day spread). Post-flight draws are reported but not compared: they are not a healthy
baseline, and the R+45 values below 50 mg/dL (three of the four crew) are flagged as implausible
for healthy people (cause unknown, possibly sample handling; we do not correct them).

Usage:
    python -m src.osdr --download   # fetch the CMP table into data/raw/ (needs internet once)
    python -m src.osdr              # run the check on the cached table
"""

# ===== Imports =====
from __future__ import annotations

import argparse
import datetime as dt
import sys

import numpy as np
import pandas as pd

from src.common import CONFIG_DIR, RAW_DIR, RESULTS_DIR, load_yaml, write_json

# ===== Constants =====
STUDY = "OSD-575"
STUDY_URL = "https://osdr.nasa.gov/bio/repo/data/studies/OSD-575"
FILE_NAME = "LSDS-8_Comprehensive_Metabolic_Panel_CMP.upload_SUBMITTED.csv"
DOWNLOAD_URL = f"https://osdr.nasa.gov/geode-py/ws/studies/{STUDY}/download?source=datamanager&file={FILE_NAME}"
CITATION = ("Overbey E.G. et al. (2024) The Space Omics and Medical Atlas (SOMA) and international "
            "astronaut biobank. Nature. doi:10.1038/s41586-024-07639-y")
CACHE_CSV = RAW_DIR / "osdr_osd575_cmp.csv"
CACHE_META = RAW_DIR / "osdr_osd575_cmp.meta.json"
IMPLAUSIBLE_BELOW = 50.0   # mg/dL: below this a healthy adult's glucose reading is flagged, not used


# ===== Download =====
def download(timeout: float = 60.0) -> None:
    """Fetch the CMP table from NASA OSDR into data/raw/ (requires network access)."""
    import requests  # imported here so offline modules never need it

    response = requests.get(DOWNLOAD_URL, timeout=timeout)
    response.raise_for_status()
    CACHE_CSV.write_bytes(response.content)
    write_json(CACHE_META, {"study": STUDY, "study_url": STUDY_URL, "file": FILE_NAME, "url": DOWNLOAD_URL,
                            "citation": CITATION,
                            "retrieved": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})


# ===== Analysis =====
def glucose_table(cmp: pd.DataFrame) -> pd.DataFrame:
    """Glucose rows only: subject, timepoint, value (mg/dL), and whether the draw is pre-flight."""
    g = cmp[cmp["ANALYTE"].str.strip().str.upper() == "GLUCOSE"].copy()
    units = set(g["UNITS"].str.strip())
    if units != {"mg/dL"}:
        raise ValueError(f"Unexpected glucose units: {units}")
    g["value"] = pd.to_numeric(g["VALUE"], errors="coerce")
    g["preflight"] = g["timepoint"].str.startswith("L-")
    return g.rename(columns={"SUBJECT_ID": "subject"})[["subject", "timepoint", "value", "preflight"]]


def summarise(g: pd.DataFrame, glucose_cfg: dict) -> dict:
    """Pre-flight glucose statistics next to the simulator's healthy parameters."""
    pre = g[g["preflight"] & g["value"].notna()]
    per_subject = pre.groupby("subject")["value"]
    sim_mean, sim_pop_sd, sim_day_sd = (float(glucose_cfg[k]) for k in ("pop_mean", "pop_sd", "day_sd"))
    real_mean = float(pre["value"].mean())
    within_sd = float(np.sqrt(per_subject.var(ddof=1).mean()))            # pooled within-person sd
    between_sd = float(per_subject.mean().std(ddof=1))                     # sd of the person means
    flagged = g[g["value"] < IMPLAUSIBLE_BELOW]
    return {
        "study": STUDY, "study_url": STUDY_URL, "citation": CITATION,
        "crew": int(pre["subject"].nunique()), "preflight_draws": int(len(pre)),
        "real_preflight": {"mean": round(real_mean, 1), "min": float(pre["value"].min()),
                           "max": float(pre["value"].max()), "within_person_sd": round(within_sd, 1),
                           "between_person_sd": round(between_sd, 1)},
        "simulator": {"pop_mean": sim_mean, "pop_sd": sim_pop_sd, "day_sd": sim_day_sd},
        "checks": {
            "real_mean_inside_simulated_population_2sd": bool(abs(real_mean - sim_mean) <= 2 * sim_pop_sd),
            "real_mean_minus_simulated_mean": round(real_mean - sim_mean, 1),
            "within_person_sd_ratio_real_to_sim": round(within_sd / sim_day_sd, 2),
        },
        "postflight_flagged_below_50": flagged[["subject", "timepoint", "value"]].to_dict("records"),
        "note": ("Comparison only; the simulator was not calibrated on these data. n = 4 crew, 3 pre-flight "
                 "draws each; fasting state of the draws is not stated in the table."),
    }


def markdown(result: dict) -> str:
    """Short table for the README and outputs/results/osdr_check.md."""
    r, s, c = result["real_preflight"], result["simulator"], result["checks"]
    return "\n".join([
        f"### Plausibility check: glucose vs real astronaut blood tests ({result['study']}, Inspiration4)",
        "",
        "| | Real pre-flight draws (n = {} crew, {} draws) | Simulator (healthy) |".format(result["crew"], result["preflight_draws"]),
        "|---|---|---|",
        f"| Mean (mg/dL) | {r['mean']} (range {r['min']:g}–{r['max']:g}) | {s['pop_mean']:g} |",
        f"| Spread between people (sd) | {r['between_person_sd']} | {s['pop_sd']:g} |",
        f"| Spread within a person (sd) | {r['within_person_sd']} | {s['day_sd']:g} (day to day) |",
        "",
        f"Real mean inside the simulated population (±2 sd): **{'yes' if c['real_mean_inside_simulated_population_2sd'] else 'no'}**"
        f" (difference {c['real_mean_minus_simulated_mean']:+g} mg/dL). Within-person spread real / simulated: "
        f"{c['within_person_sd_ratio_real_to_sim']}. {result['note']}",
    ])


# ===== Main =====
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare simulated glucose with Inspiration4 blood tests (NASA OSDR).")
    parser.add_argument("--download", action="store_true", help="Fetch the CMP table from NASA OSDR first.")
    args = parser.parse_args()

    if args.download:
        try:
            download()
        except Exception as error:  # network problems are expected offline
            print(f"OSDR download failed ({error}).")
            if not CACHE_CSV.exists():
                sys.exit(1)
    if not CACHE_CSV.exists():
        sys.exit(f"{CACHE_CSV} is missing: run `python -m src.osdr --download` once.")

    glucose_cfg = load_yaml(CONFIG_DIR / "simulation.yaml")["features"]["glucose"]
    result = summarise(glucose_table(pd.read_csv(CACHE_CSV)), glucose_cfg)
    write_json(RESULTS_DIR / "osdr_check.json", result)
    (RESULTS_DIR / "osdr_check.md").write_text(markdown(result) + "\n", encoding="utf-8")
    print(markdown(result))
