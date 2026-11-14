# Astrobalance — personal-baseline health monitoring for deep-space crews

**NASA Space Apps Challenge 2026 · Challenge: _Create Health Monitoring Software for Astronauts on Space Missions_ (author: Brazilian Space Agency)**

**▶ Live app (works offline after the first visit, no login): https://moai-pl.github.io/NASASpaceApps-MoAI/**

> **Prototype — not medical advice.** Model results come from synthetic data calibrated on published sources, plus one alarm-rate check on real everyday data (PMData) — proof of concept, not clinical validation. Not a medical device.

---

## 1. Overview

Halfway to Mars, “your fellow crew mate feels a sharp pain in the chest and collapses” — the scenario set by the challenge author, the Brazilian Space Agency, in the [challenge video](https://www.youtube.com/watch?v=RERG3gEmdC8) (0:43). Our addition: there is no doctor on board, and a message to Earth takes up to ~22 minutes one way.

Astrobalance lets astronauts assess their own health on long missions along two paths:

- **Prevent** — an unsupervised model of the **personal normal** (a multivariate personal-drift model, chosen in a benchmark against autoencoder variants) turns each day's self-measurements into a single **Systemic Anomaly Index (SAI, 0–100)**, with an explanation of which indicators moved and a prompt for the next measurement. The personal normal follows slow, healthy change; on real everyday data (PMData) the model raised no alarm in 280 person-weeks (7.4).
- **Respond** — fixed critical thresholds and an emergency mode that work **independently of the model**, with an escalation ladder that accounts for the communication delay to Earth.

Every NASA Human Research Program hazard is visible in the product:

| NASA HRP hazard | How Astrobalance covers it | Data |
|---|---|---|
| Space radiation | daily and cumulative absorbed dose, alerts on solar particle events | real NASA DONKI SEP events + assumed dose model |
| Isolation & confinement | mind & sleep system (sleep, mood, reaction time); the model detects joint drift | synthetic |
| Distance from Earth | escalation ladder and Earth-report queue use the one-way communication delay; reports to Earth in SBAR form; comms-blackout mode for Mars solar conjunction | config per environment |
| Gravity fields | heart & circulation system (blood pressure, heart rate, exercise) | synthetic |
| Hostile & closed environment | cabin CO₂ against the NASA limit; infection onset via temperature and heart rate | synthetic |

Bone loss cannot be tracked with daily self-measurements and is out of scope (see Limitations).

## 2. Quick start

```bash
conda env create -f environment.yml && conda activate spaceapps
python -m src.donki --start 2024-05-01 --days 120   # needs internet once: caches real NASA DONKI SEP events
python -m src.run_all                               # simulate → fit → tune on bench → confirm on dev → export → figures
python -m src.run_all --benchmark                   # same, plus the model-selection benchmark (~5 min on CPU)
python -m src.robust_bench --window 14              # robustness benchmark: synthetic detection vs real-data alarms (7.5)
pytest -q
```

The production detector fits in seconds on a laptop CPU; the benchmark trains nine autoencoders (about 30 s each on CPU, `--device cuda` in `src.train` for the alternative detector).

Live app: https://moai-pl.github.io/NASASpaceApps-MoAI/ — rebuilt and published by `.github/workflows/pages.yml` on every push to `main`. Locally: `cd ui/app && npm install && npm run dev`, or `npm run build` for a self-contained static site in `ui/app/dist/`. The built app is installable and works fully offline after the first visit (own service worker `ui/app/public/sw.js`, no extra library); check it with `npm run preview`, then stop the server and reload. UI concept: open `ui/concept/index.html` in a browser (works offline). See `ui/README.md`.

The one-time hold-out test is **not** part of `run_all`: `python -m src.evaluate --split test --final` (run once, after freezing `config/model.yaml` and `config/rules.yaml`).

## 3. How it works

1. **Daily check-in** — blood pressure, resting heart rate, fasting glucose, temperature, sleep, mood (1–5), reaction time; exercise minutes as context. The six indicators named in the challenge statement are all included. Image-based indicators (camera, ultrasound), which the challenge also allows, are out of scope: Astrobalance uses daily self-measurements only.
2. **Personal normalisation** — each indicator is converted to a z-score against that astronaut's own normal, so the model sees *deviation from this person's normal*, not absolute values. The normal is learned on mission days 1–21 and then **follows slow change**: a robust exponentially weighted mean that only uses days at least 14 days old (a developing illness cannot be absorbed within two weeks) and moves by at most 2 personal standard deviations per update. An indicator with fewer than 7 values in days 1–21 has no normal yet and is not scored. Exercise minutes are shown as context but not scored (chosen in 7.5).
3. **Drift summary** — for each day, the last 14 days are summarised as a weighted mean of the personal z-scores (latest day heaviest), one value per feature.
4. **Personal-drift model (unsupervised)** — a Gaussian model of that 9-dimensional summary is learned from 300 healthy simulated astronauts, with no illness labels. The anomaly score is the squared Mahalanobis distance of today's summary from the healthy model (a Hotelling T²-type statistic): it rises when several indicators drift together, even if each one alone still looks normal.
5. **SAI** — the percentile of the score among healthy validation days (0–100).
6. **Alert levels** — yellow (Watch) when SAI ≥ 94 on 3 consecutive days, orange (Act) when SAI ≥ 99 on 3 consecutive days; a level ends after 7 days in a row below its threshold. P_yellow was tuned **on the selection split only**, as the most sensitive value with ≤ 0.05 false alarms per astronaut-week. Red comes only from critical thresholds.
7. **Explanation** — the score decomposes exactly into one term per indicator (T² = Σ d_f·(Σ⁻¹d)_f); the positive terms give "what moved", mapped to body systems and to the hazard strip; prompts ask for a targeted re-measurement.
8. **Escalation** — monitor → self-care → crew medical officer (orange, or yellow for 5 days, or 2+ systems) → flight surgeons (red; on Mars transit the onboard protocol comes first and the report is queued for downlink).

Reference methods the model is compared against:
- **B1 — fixed clinical thresholds** (e.g. AHA stage 2 hypertension, ADA hypoglycaemia), 2–3 days persistence.
- **B2 — personal single-indicator thresholds**: any indicator beyond 3 personal standard deviations on 2 consecutive days.

## 4. Architecture

```mermaid
flowchart LR
  A[Daily check-in<br/>manual input / wearables] --> B[Personal normalisation<br/>learned days 1–21, then follows slow change]
  R[Space weather<br/>NASA DONKI SEP] --> H
  C[Cabin CO₂] --> H
  B --> D[14-day drift summary]
  D --> E[Personal-drift model<br/>Mahalanobis vs healthy]
  E --> F[SAI 0–100 + levels]
  A --> G[Critical thresholds<br/>independent of the model]
  F --> H[Local JSON store<br/>offline-first]
  G --> H
  H --> I[Crew UI: SAI, body map,<br/>hazards, prompts, emergency]
  H --> J[Earth report queue<br/>delayed downlink]
```

## 5. Why unsupervised

There is no labelled dataset of astronaut illnesses: crews are tiny, serious events are rare and individual health records are private. A supervised classifier has nothing to learn from. A model of **each person's normal** needs no labels — it only needs healthy days, which every mission produces.

**Why not a deep model?** We benchmarked it (section 7). On daily data with 9 features, a well-specified statistical model of the healthy state beat every autoencoder variant, including ensembles and per-astronaut fine-tuning. It is also tiny (a 9 × 9 matrix), exactly explainable and trivial to run offline on any flight computer. The autoencoder remains in the code (`detector: autoencoder`) for richer, higher-frequency data in future work.

## 6. Data & sources

- **Real data:** NASA DONKI solar energetic particle events for the mission window (`python -m src.donki`). If the cache is missing, no SEP events are simulated and `meta.json` reports `space_weather.status = "missing"`.
- **Real everyday data:** PMData (Thambawita et al. 2020, CC BY 4.0) — Fitbit resting heart rate, sleep and active minutes plus a daily mood rating from 16 people. The odd-numbered half calibrates the simulator's noise and drift and selects the personal-normal variant (7.5); the even-numbered half is used only to confirm; the model itself is never fitted on it.
- **Synthetic crews (simulator 2):** individual astronaut records are privacy-protected, so every astronaut is simulated from `config/simulation.yaml`. Day-to-day variation is correlated through two latent factors (fatigue, training load); each input's own noise is autocorrelated and every healthy baseline drifts slowly, with both effects estimated from real everyday data (PMData, selection half only: resting heart rate autocorrelation 0.75, drift 0.13 personal sd per √day) and flagged as assumptions where PMData does not measure the input. Scenario sizes were fixed **before** any evaluation.

| Scenario | What changes (in personal standard deviations) | Role |
|---|---|---|
| S1 Cardiovascular deconditioning | heart rate +2.5, systolic +2.0, diastolic +1.5, reaction time +0.5; exercise −40 %; 21-day ramp | development |
| S2 Isolation & stress | sleep −2.0, mood −2.0, reaction time +2.0, heart rate +1.0; 14-day ramp | development |
| S3 Metabolic disturbance | glucose +2.5, sleep −1.0, mood −1.0; 14-day ramp | development |
| S4 Sensor fault | one indicator +6 for 5 days | development (sensor-fault flag) |
| S5 Infection onset | temperature +2.5, heart rate +2.0, sleep −1.5, mood −1.5, reaction time +1.0; 5-day ramp | **hold-out test only** |

Every configuration value is either sourced or flagged as an assumption: full list in [`outputs/results/config_sources.md`](outputs/results/config_sources.md) (generated by `python -m src.report_sources`). Sourced values: ISS sleep duration (Barger et al. 2014), CO₂ limit (NASA OCHMO / NASA-STD-3001), blood-pressure categories (AHA), hypoglycaemia levels (ADA), Earth–Mars communication delay (NASA ASCEND).

## 7. Results

*Synthetic data calibrated on published sources — proof of concept, not clinical validation.*

### Results at a glance

Every number says what data it comes from and how it was tested.

| Result | Number | Data | How it was tested |
|---|---|---|---|
| Unseen illness type detected | **10 of 10** (clinical limits: 9 of 10; single-value limits: 10 of 10) | synthetic, hold-out scenario S5 (infection onset) | S5 never looked at during development; evaluated **once** on the frozen model (commit `0fc28fe`) |
| Earlier than clinical limits | **+5 days** (median; 9 detected by both, 1 more only by the model) | same | same |
| False alarms on the same test | **0.055** per astronaut-week (clinical limits 0.121, single-value limits 0.241) | same | same; single-value limits alarm 3.5 days earlier (median) but with 4.4× the false alarms |
| Changes caught within 21 days at an equal false-alarm budget | **71%** (fixed personal normal 66%; autoencoders ≤ 59 %; personal single-value limits ≤ 43 %; clinical limits 44 % at their own, higher false-alarm rate) | synthetic, selection split (130 astronauts) | every method set to 0.05 false alarms per astronaut-week |
| Alarms on real everyday data | **0.000** per person-week — none in 280 person-weeks (fixed normal 0.029; clinical limits 0.021; single-value limits 0.068) | **real**: PMData, 16 people, 4 of 9 inputs | no labels: an alarm rate, not accuracy (7.4) |

Testing on new people from the same data generator shows that a method generalises to new people. Our hold-out also tests a **new type of health change**, and the real-data check tests **real people**.

**Protocol.** (1) Model selection on a dedicated selection split (`bench`, new seeds: 30 astronauts per scenario S1–S3 + 40 healthy, scenario sizes × 0.5 and × 1.0), every method tuned to the **same false-alarm budget** (≤ 0.05 per astronaut-week). (2) Confirmation on the original development split with all thresholds frozen. (3) One run on the hold-out scenario S5 (infection onset), never seen during development; configuration frozen in git commit `0fc28fe` before the run.

### 7.1 Model-selection benchmark

![Benchmark](outputs/figures/benchmark.png)

| Method family (best variant) | Scenarios detected within 21 days | Detected at all |
|---|---|---|
| **Multivariate personal-drift model, 14-day mean (chosen)** | **65 %** | **89 %** |
| Drift model + autoencoder ensemble | 64 % | 87 % |
| Autoencoder ensemble ×5 (300 training astronauts) | 59 % | 86 % |
| Autoencoder, single model (latent distance) | 57 % | 85 % |
| Autoencoder + per-astronaut fine-tuning | 56 % | 81 % |
| Personal single-indicator thresholds (B2, smoothed) | 43 % | 74 % |
| Fixed clinical thresholds (B1, own false-alarm rate 0.106) | 44 % | 62 % |

42 configurations at the 0.05 budget (architecture, training-set size, score components, smoothing, persistence, ensembles, fine-tuning, hybrids): [`outputs/results/benchmark.md`](outputs/results/benchmark.md). The second stage (7.5) then chose how the personal normal is kept up to date; with it the chosen model reaches 71%.

### 7.2 Confirmation split (thresholds frozen)

| Scenario | Detected: model / B1 / B2 | Median delay after onset (days): model / B1 / B2 | Model lead vs B1 (median) | Model lead vs B2 (median) |
|---|---|---|---|---|
| S1 Cardiovascular | 100 % / 50 % / 100 % | 12 / 24 / 10 | +14 d; 5 found only by the model | -2 d |
| S2 Isolation & stress | 100 % / 90 % / 100 % | 13.5 / 12 / 9.5 | +0 d; 1 found only by the model | -5 d |
| S3 Metabolic | 100 % / 80 % / 100 % | 8 / 18 / 11 | +4 d; 2 found only by the model | +6.5 d |

False alarms per astronaut-week: model 0.065, B1 0.121, B2 0.183. Single-value limits react a few days earlier on S1 and S2, but at about three times the false-alarm rate; at an equal false-alarm budget they catch far fewer changes early (7.1). Small isolation changes (S2 at half size) are the weak spot: 50 % detected (B2 80 %). Full tables: [`outputs/results/dev_metrics.md`](outputs/results/dev_metrics.md).

### 7.3 Hold-out test — infection onset (S5), evaluated once

| | Model | Fixed clinical thresholds (B1) | Personal single-indicator thresholds (B2) |
|---|---|---|---|
| Detected | **100 %** | 90 % | 100 % |
| Median delay after onset | **9 days** | 13 days | 4.5 days |
| Model lead (median) | – | **+5 days** (9 detected by both); 1 case found only by the model | -3.5 days (all 10) |
| False alarms per astronaut-week | **0.055** | 0.121 | 0.241 |

![Hold-out](outputs/figures/lead_time_test.png)

S5 was never seen during development and was evaluated once (`outputs/results/final_test.json`, with timestamp and commit hash). The recorded commit `0fc28fe` is from the project's first repository (MoAI-PL/NASASpaceApps-Health); the frozen content has git tree `843e3d1`.

**What this shows — and what it does not:**
- Against fixed clinical thresholds the hypothesis holds on this synthetic data: earlier detection, including on a scenario type the model never saw, with half the false alarms.
- Against personal single-indicator thresholds it does not: they alarm about 3.5 days earlier on the infection scenario, but raise 4.4× as many false alarms; on real everyday data they alarm 0.068 times per person-week, the model never (7.4). The trade-off is speed versus a crew that keeps trusting its alerts.
- The simulator is linear-Gaussian with gradual mean shifts, which favours a Gaussian drift model; on real crew data the ranking could change.

### 7.4 Real-data check — alarm rate on real everyday data (PMData)

The model was built on synthetic astronauts. To see how it behaves on real human data, we ran it on PMData: 16 people logging Fitbit and wellness data for up to five months (Nov 2019 – Mar 2020; CC BY 4.0). Four of our nine daily inputs exist there — resting heart rate, sleep hours, mood (1–5) and exercise minutes; the others are missing and enter the model as "at your normal". Nothing is fitted on PMData.

![Real-data check](outputs/figures/real_data_check.png)

| Method | Alarms per person-week | Days in alarm |
|---|---|---|
| **Astrobalance (adaptive personal normal)** | **0.000** | 0% |
| Same detector with a normal fixed after day 21 | 0.029 | 1% |
| Fixed clinical limits | 0.021 | 0% |
| Personal single-value limits | 0.068 | 2% |

**What it shows:** the model raised no alarm in 280 person-weeks of real everyday life, where single-value limits alarmed 0.068 times per person-week. The PMData people are not labelled and include winter months, so this is an alarm rate, not accuracy: the model may also have missed real events, and with only 4 of 9 inputs it sees less than it would on a crew.

Data cleaning, fixed before scoring and applied to everyone alike: exercise minutes count as missing on days with no wear evidence (no resting heart rate and no sleep record); sleep records under 1 h or over 16 h are artefacts. Daily table: [`data/real/pmdata_daily.csv`](data/real/pmdata_daily.csv) (derived from PMData, CC BY 4.0); output: [`outputs/results/real_data_check.json`](outputs/results/real_data_check.json); rerun with `python -m src.realdata`.

### 7.5 Robustness benchmark — how the personal normal is kept up to date

Real wearable resting heart rate is smoothed (day-to-day autocorrelation ~0.75) and drifts by a few bpm over weeks; a normal fixed after day 21 reads that as deviation. 58 variants of the personal normal and the alarm logic (fixed, rolling, EWMA, robust EWMA, autocorrelation-aware, missing-aware distance, personal score scale, persistence, alarm hold, inputs left out) were compared on the 14-day detector under a rule fixed in advance: each variant's threshold is set on the synthetic selection split to 0.05 false alarms per astronaut-week; among variants whose early detection is at most 5 points below the fixed normal, pick the one with the fewest alarms on **half** of the PMData people (p01, p03, …); then run it **once** on the other half and on the dev split.

| Model | Early detection, synthetic (bench) | Real alarms per person-week: selection half → confirmation half | Dev false alarms per astronaut-week |
|---|---|---|---|
| Fixed 21-day normal | 66% | 0.050 → 0.007 | 0.045 |
| **Robust EWMA normal, exercise not scored, alarm held 7 days (chosen)** | **71%** | **0.000 → 0.000** | 0.069 |

The chosen normal catches more changes early and raises fewer real alarms, at a somewhat higher synthetic false-alarm rate on dev. Full table and protocol notes (including a missing-data fix made after the first confirmation, and the rounds in which the grid was built): [`outputs/results/robust_bench.md`](outputs/results/robust_bench.md) (`python -m src.robust_bench --window 14`).

Figures (1600 × 900, slide-ready): `benchmark.png`, `lead_time_test.png`, `lead_time_dev.png`, `timeline_demo.png` (Crew Member Bravo: one false alarm on day 37, model alarm on day 65 after the change starts on day 50, fixed clinical thresholds on day 72), `real_data_check.png`, `healthy_check.png`.

## 8. Earth spin-off

The same offline, personal-baseline monitoring fits isolated crews on Earth: Antarctic research stations wintering without evacuation, remote communities with limited access to care, and long maritime deployments. A personal normal travels with the person; no labelled patient data or constant connectivity is needed. The challenge author names exactly this use — remote communities and places with limited access to health services — in the [challenge video](https://www.youtube.com/watch?v=RERG3gEmdC8).

## 9. Limitations

- All astronaut data are synthetic; results show the method works on plausible data, not that it works on real crews. The real-data check (PMData) uses 4 of 9 inputs, is not astronauts and has no labels, so it measures alarm rates, not accuracy.
- Most simulation parameters are assumptions (listed in `config_sources.md`); noise and drift are taken from healthy everyday adults, not from spaceflight, and spaceflight adaptation (e.g. fluid shifts) is not modelled.
- Personal single-indicator thresholds react faster on some scenarios (S1, S2, the S5 hold-out) at several times the false-alarm rate; small isolation changes (S2 at half size) are the model's weakest case.
- An alarm stays on until 7 quiet days have passed, so a false alarm also lasts longer (9 % of healthy synthetic days in Watch).
- Daily granularity; no continuous wearable streams (HRV, SpO₂, respiratory rate) — possible future work.
- Bone loss is not covered (not measurable with daily self-measurements).
- The emergency-mode steps and the measurement guidance in the app are first-aid and self-measurement guidance paraphrased from the public sources listed in References; they are not a validated medical protocol and do not replace crew medical training or onboard procedures.
- Model selection used synthetic scenarios designed by the team; the winning model's advantage may partly reflect the linear-Gaussian simulator (see 7.3).
- Radiation dose values are illustrative; SEP event dates are real only after `src.donki` has been run with internet access.

## 10. Use of AI (Super Intelligence, SI)

Generative AI was used in this project, as required to be disclosed by the NASA Space Apps rules:
- **Claude (Anthropic)**, including via Claude Code, drafted the Python code, tests, configuration files, the concept UI, the figures and this README, and helped search for and verify sources. Every source file carries the header "AI-assisted: drafted with Claude (Anthropic), reviewed by the team".
- The team defined the concept, made the design decisions, reviewed and ran all code, and checked every cited source.
- No AI-generated images are used. No NASA logos or branding are used anywhere.

## 11. References

Data and scientific sources
- Brazilian Space Agency (AEB) — challenge introduction video, NASA Space Apps Challenge 2026 (source of the scenario quote and the Earth-application idea): https://www.youtube.com/watch?v=RERG3gEmdC8
- NASA Human Research Program — 5 Hazards of Human Spaceflight: https://www.nasa.gov/hrp/hazards/
- NASA Human Research Program — Risks of Human Spaceflight: https://www.nasa.gov/hrp/risks/
- NASA Human Research Program — Ongoing HRP Research in Space: https://www.nasa.gov/hrp/ongoing-hrp-research/
- Thambawita V., Hicks S.A., Borgli H., Stensland H.K., Jha D., Svensen M.K., Pettersen S.A., Johansen D., Johansen H.D., Pettersen S.D., Nordvang S., Pedersen S., Gjerdrum A., Grønli T.-M., Fredriksen P.M., Eg R., Hansen K., Fagernes S., Claudi C., Biørn-Hansen A., Nguyen D.T.D., Kupka T., Hammer H.L., Jain R., Riegler M.A., Halvorsen P. (2020), PMData: a sports logging dataset, Proc. 11th ACM Multimedia Systems Conference (MMSys'20), doi:10.1145/3339825.3394926 — dataset under CC BY 4.0: https://datasets.simula.no/pmdata (daily files read from the public mirror https://github.com/itsalamhere/sports-logs, which states PMData as its source)
- NASA CCMC DONKI — Solar Energetic Particle events API: https://ccmc.gsfc.nasa.gov/tools/DONKI/
- NASA OCHMO Technical Brief OCHMO-TB-004, Carbon Dioxide: https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-004-carbon-dioxide.pdf
- NASA ASCEND paper, Communication Delays, Disruptions, and Blackouts for Crewed Mars Missions: https://ntrs.nasa.gov/api/citations/20220013418/downloads/ASCEND-Communication%20Delays%2C%20Disruptions%2C%20and%20Blackouts%20for%20Crewed%20Mars%20Missions.pdf
- Canadian Space Agency — Monitoring Radiation for Astronaut Health: https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp
- Barger L.K. et al., sleep deficiency in astronauts, The Lancet Neurology (2014); press release: https://www.eurekalert.org/news-releases/595450
- American Heart Association — Understanding Blood Pressure Readings: https://heart.org/bplevels
- American Diabetes Association — Hypoglycemia (HCP): https://professional.diabetes.org/sites/dpro/files/2025-05/hypoglycemia-hcp-5-27-25.pdf

Crew-facing guidance in the UI app (`ui/app/src/content/texts.js`; paraphrased and linked, no text copied; checked 2026-11-14)
- NASA HRP risk pages: Cardiovascular Adaptations, Altered Immune System Responses, Inadequate Sleep and Irregular Schedules, Behavioral Changes and Psychiatric Disorders, Inadequate Food and Nutrition — https://www.nasa.gov/hrp/risks/
- NASA HRP hazard pages: Gravity Fields, Isolation and Confinement, Hostile/Closed Environments, Distance from Earth — https://www.nasa.gov/hrp/hazards/
- NASA, Space Radiation Won't Stop NASA's Human Exploration (shelter during solar particle events): https://www.nasa.gov/humans-in-space/space-radiation-wont-stop-nasas-human-exploration/
- NASA Human Research Roadmap, Psychomotor Vigilance Test (Reaction Self-Test) on ISS: https://humanresearchroadmap.nasa.gov/Tasks/task.aspx?i=1651
- Hinkelbein J. et al. (2020), Cardiopulmonary resuscitation (CPR) during spaceflight — a guideline for CPR in microgravity (DGLRM / ESAM-SMG), Scand J Trauma Resusc Emerg Med 28:108, CC BY 4.0: https://link.springer.com/article/10.1186/s13049-020-00793-y
- Tobin B.W. et al. (2002), Insulin secretion and sensitivity in space flight: diabetogenic effects, Nutrition 18(10):842–8: https://pubmed.ncbi.nlm.nih.gov/12361776/
- Van Dongen H.P.A., Maislin G., Mullington J.M., Dinges D.F. (2003), The cumulative cost of additional wakefulness, Sleep 26(2):117–26 (basis of the "Feels fine ≠ is fine" readiness check in the UI): https://pubmed.ncbi.nlm.nih.gov/12683469/
- NASA, What's Mars Solar Conjunction, and Why Does It Matter? (basis of the comms-blackout mode in the Earth link): https://www.nasa.gov/solar-system/whats-mars-solar-conjunction-and-why-does-it-matter/
- AHRQ TeamSTEPPS, Tool: SBAR — Situation, Background, Assessment, Recommendation (structure of the report to Earth): https://www.ahrq.gov/teamstepps-program/curriculum/communication/tools/sbar.html
- American Heart Association: Home Blood Pressure Monitoring; Target Heart Rates; Warning Signs of a Heart Attack — https://www.heart.org/
- MedlinePlus (U.S. National Library of Medicine): CPR — adult (000013); Unconsciousness — first aid (000022); Breathing difficulties — first aid (000007); Chest pain (003079); Body temperature norms (001982); Blood sugar test (003482) — https://medlineplus.gov/ency/

Software (open-source licenses)
- Methods: Mahalanobis distance / Hotelling T² statistic (classical multivariate statistics); autoencoders for anomaly detection (benchmarked alternative).
- Python packages: NumPy (BSD-3-Clause), pandas (BSD-3-Clause), PyTorch (BSD-3-Clause), Matplotlib (Matplotlib license, PSF-based), PyYAML (MIT), Requests (Apache-2.0), jsonschema (MIT), pytest (MIT).
- Concept UI: React and ReactDOM 18 (MIT, bundled in `ui/concept/vendor/`), Tailwind CSS 3 (MIT, build time), Babel (MIT, build time).
- UI app (`ui/app/`): React and ReactDOM 18 (MIT, bundled into the build), Vite 6 (MIT, build time), @vitejs/plugin-react (MIT, build time), Tailwind CSS 4 and @tailwindcss/vite (MIT, build time). No web fonts, icons or images from third parties: system fonts and our own SVG.

## 12. License and disclaimer

Code and documentation: **Apache License 2.0** (`LICENSE`).
This is a research prototype built during a 48-hour hackathon on synthetic data. It is **not a medical device**, has **not** been clinically validated and must not be used for medical decisions.
