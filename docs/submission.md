# Project page texts — NASA Space Apps 2026 submission

Copy each block into the matching field of the project page (Space Apps → My Team → Project → Edit).
Everything is in English, as the submission guide requires. Numbers come from `outputs/results/` and match the README.

---

## Project Name

Astrobalance

## High-Level Project Summary

Astrobalance is offline health-monitoring software that lets astronauts check their own health on long missions, where there is no doctor on board and a message to Earth takes up to about 22 minutes one way. After a two-minute daily check-in (blood pressure, heart rate, temperature, glucose, sleep, mood and a reaction test), an unsupervised model learns each astronaut's personal normal and turns the last two weeks into one Systemic Anomaly Index from 0 to 100, with a clear status (Watch or Act), the values that moved and the next step. Fixed critical limits and a step-by-step emergency guide work independently of the model from day 1. In a one-time test on an illness type the model never saw (infection onset), it caught 10 of 10 cases, a median of 5 days earlier than fixed clinical limits, with 4.4 times fewer false alarms than single-value limits; on real everyday data from 16 people it raised no alarm in 280 person-weeks. Every NASA Human Research Program hazard is visible in the app, and the same approach can serve isolated crews on Earth, such as Antarctic stations and remote communities. Proof of concept on synthetic data calibrated on published sources; not a medical device.

## Link to Project Demo

https://github.com/MoAI-PL/NASASpaceApps-MoAI/blob/main/docs/demo/Astrobalance-demo-slides.pdf
(7 slides including the title slide; public, no login)

## Link to Final Project

https://moai-pl.github.io/NASASpaceApps-MoAI/
(live app, works on a phone and offline after the first visit; code, results and sources: https://github.com/MoAI-PL/NASASpaceApps-MoAI)

## Detailed Project Description

**What it does.** Halfway to Mars, the challenge author asks us to imagine a crew mate who suddenly collapses with chest pain. Astrobalance works on two paths:

- **Prevent.** A daily self-check-in takes about two minutes. During the first 21 mission days the app learns what is normal for each astronaut, not for an average person; afterwards the personal normal follows slow, healthy change. A personal-drift model watches all indicators together over 14 days and turns them into the Systemic Anomaly Index (0–100). When several small changes add up, the crew sees Watch or Act, the body system that moved, and up to three next steps (for example "re-measure blood pressure and resting heart rate", "tell your crew medical officer today"), often before any single value crosses a limit.
- **Respond.** Fixed critical thresholds raise a red alert without the model. An emergency guide (unresponsive crew mate, CPR, chest pain, breathing difficulty), adapted to weightlessness and to Moon or Mars gravity, is always one tap away. Escalation accounts for the one-way signal delay: the crew medical officer comes first, and a structured SBAR report is queued for Earth; a blackout mode covers Mars solar conjunction.

**How it works.** Each value is converted to a deviation from the astronaut's own normal (a robust, slowly updating personal baseline). The 14-day weighted mean of these deviations is scored with a Mahalanobis (Hotelling T²) distance from a model of healthy days, learned without any illness labels, because a labelled dataset of astronaut illnesses does not exist. The score splits exactly into one share per indicator, which gives the "what moved" explanation. The index is the score's percentile among healthy days; Watch starts after 3 days at 94 or above, Act after 3 days at 99 or above.

**How we tested it.** The model was chosen in a benchmark of 42 configurations, every method held to the same false-alarm budget (at most 0.05 per crew member per week): it caught 71% of simulated health changes within 21 days, against at most 59% for deep-learning autoencoders and 44% for fixed clinical limits. Thresholds were then frozen and confirmed on independent data. Finally, one illness type (infection onset) was kept aside during development and evaluated once: 10 of 10 cases caught (clinical limits 9 of 10), a median of 5 days earlier than clinical limits, 0.055 false alarms per crew member per week (clinical limits 0.121, single-value limits 0.241). Single-value limits alarmed 3.5 days sooner on infections, but with 4.4 times the false alarms; we chose alerts a crew keeps trusting. On real everyday data (PMData: 16 people, Fitbit and mood, 4 of our 9 inputs) the model raised no alarm in 280 person-weeks; this is an alarm rate, not accuracy, because PMData has no illness labels.

**Benefits.** Early, explainable warnings that a crew can act on without waiting for Earth; fewer false alarms, so alerts stay trusted; a safety net that works even when the model cannot. Every state is shown with colour, shape and a word, with large tap targets, so it reads at a glance.

**Earth spin-off.** The same offline monitoring fits Antarctic research stations in winter, remote communities with little access to care (the Earth use named by the challenge author) and long voyages at sea. A personal normal needs no patient database and no constant connection.

**Tools.** Python 3.11 (NumPy, pandas, PyTorch for the benchmarked autoencoders, Matplotlib, PyYAML, Requests, jsonschema, pytest) for simulation, modelling and evaluation; React 18, Vite 6 and Tailwind CSS 4 for the offline web app (installable, works without network); GitHub Pages for hosting. All code is open source under Apache-2.0.

**Honest limits.** Model results come from synthetic astronauts calibrated on published sources, because individual astronaut health records are private; this is a proof of concept, not clinical validation, and not a medical device. Bone loss and image-based indicators are out of scope.

## NASA Data

- **NASA/JPL Horizons** — real Earth–Mars distance for each mission day; the app shows the true one-way delay of that day for a crew on Mars (16 min on day 1 falling to 12 min on day 120): https://ssd.jpl.nasa.gov/horizons/
- **NASA Open Science Data Repository, OSD-575 (Inspiration4 blood metabolic panel)** — real astronaut glucose values used to check the simulator, not to calibrate it: partly consistent (real pre-flight mean 75 mg/dL vs simulated 90): https://osdr.nasa.gov/bio/repo/data/studies/OSD-575
- **NASA DONKI (CCMC) solar energetic particle events** — real events for the mission window are shown on the mission timeline and drive the radiation alerts: https://ccmc.gsfc.nasa.gov/tools/DONKI/
- **NASA Human Research Program — 5 Hazards of Human Spaceflight and Risks** — the product maps every hazard (radiation, isolation and confinement, distance from Earth, gravity fields, hostile and closed environments) to a feature; risk pages inform the crew guidance: https://www.nasa.gov/hrp/hazards/ and https://www.nasa.gov/hrp/risks/
- **NASA OCHMO Technical Brief TB-004, Carbon Dioxide** — cabin CO₂ limit: https://www.nasa.gov/wp-content/uploads/2023/12/ochmo-tb-004-carbon-dioxide.pdf
- **NASA ASCEND paper, Communication Delays, Disruptions, and Blackouts for Crewed Mars Missions** — signal delay used in escalation and the Earth-report queue: https://ntrs.nasa.gov/api/citations/20220013418/downloads/ASCEND-Communication%20Delays%2C%20Disruptions%2C%20and%20Blackouts%20for%20Crewed%20Mars%20Missions.pdf
- **NASA — What's Mars Solar Conjunction** — basis of the communication-blackout mode: https://www.nasa.gov/solar-system/whats-mars-solar-conjunction-and-why-does-it-matter/
- **NASA Human Research Roadmap — Psychomotor Vigilance Test (Reaction Self-Test) on ISS** — basis of the in-app reaction test: https://humanresearchroadmap.nasa.gov/Tasks/task.aspx?i=1651
- **NASA — Space Radiation Won't Stop NASA's Human Exploration** — shelter guidance during solar particle events: https://www.nasa.gov/humans-in-space/space-radiation-wont-stop-nasas-human-exploration/

## Space Agency Partner & Other Data

- **Brazilian Space Agency (AEB)** — challenge video: the chest-pain scenario and the Earth application for remote communities: https://www.youtube.com/watch?v=RERG3gEmdC8
- **Canadian Space Agency** — Monitoring Radiation for Astronaut Health: https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp
- **PMData** (Thambawita et al. 2020, CC BY 4.0) — real Fitbit and wellness data from 16 people; calibrates the simulator's day-to-day noise and drift and tests the model's alarm rate on real people: https://datasets.simula.no/pmdata
- **Barger et al. 2014** (The Lancet Neurology) — sleep of astronauts on the ISS; **American Heart Association** blood-pressure categories and heart-rate guidance; **American Diabetes Association** hypoglycaemia levels; **MedlinePlus** (U.S. National Library of Medicine) first-aid and CPR pages; **Hinkelbein et al. 2020** guideline for CPR in microgravity (CC BY 4.0); **AHRQ TeamSTEPPS SBAR** for the report to Earth. Full list with links: README → References.

## References / Resources

All data, sources and software with licenses are listed in the README: https://github.com/MoAI-PL/NASASpaceApps-MoAI#11-references

- Software: NumPy, pandas, PyTorch (BSD-3-Clause); Matplotlib (Matplotlib license); PyYAML, jsonschema, pytest (MIT); Requests (Apache-2.0); React, Vite, Tailwind CSS (MIT).
- Demo slides: Inter typeface (SIL Open Font License 1.1); screenshots of our own app; QR code generated with python-qrcode (BSD).
- No NASA logos or branding are used. No AI-generated images are used. Every astronaut is synthetic ("Crew Member Alpha, Bravo, Charlie").

## Use of Artificial Intelligence (AI)

Yes. We used Claude (Anthropic), including through Claude Code, as a coding and writing assistant: it drafted Python code, tests, configuration, the web app's code and texts, figures, the README, the demo slides and these texts, and helped us search for and check sources. The team came up with the concept, made the design and modelling decisions, reviewed and ran all code, and checked every cited source. Every source file carries the header "AI-assisted: drafted with Claude (Anthropic), reviewed by the team", and the README has a "Use of AI" section. No AI-generated images, video or audio are used.
