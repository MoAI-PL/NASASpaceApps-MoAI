# Real everyday data (check only)

`pmdata_daily.csv` is a daily table derived from **PMData** (Thambawita V. et al. 2020,
*PMData: a sports logging dataset*, Proc. ACM MMSys'20, doi:10.1145/3339825.3394926),
licensed under **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/). Dataset page:
https://datasets.simula.no/pmdata. The raw daily files were read from the public mirror
https://github.com/itsalamhere/sports-logs, which states PMData as its source.

Changes made by the Astrobalance team (`python -m src.realdata --pmdata-dir <raw folder>`):
- one row per participant and calendar day; `day` counts from the first day with any value;
- `hr` = Fitbit resting heart rate (0 → missing); `sleep_h` = hours asleep in main-sleep records;
  `mood` = PMSys wellness mood 1–5 (0 → missing); `exercise_min` = Fitbit very + moderately active minutes;
- cleaning: exercise missing on days with no resting heart rate and no sleep record; sleep under 1 h
  or over 16 h missing.

Used only to measure alarm rates of the frozen model (README section 7.4). Nothing is trained or tuned on it.
