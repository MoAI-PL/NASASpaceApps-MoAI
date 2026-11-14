### Confirmation split (dev, thresholds frozen)

P_yellow = 94.0, persistence = 3 days, hold = 7 days. Synthetic data calibrated on published sources — proof of concept, not clinical validation.

| Scenario | n | Detected Model / B1 / B2 | Median delay (days) Model / B1 / B2 | Lead vs B1: median (both detected) · only Model | Lead vs B2: median (both detected) · only Model |
|---|---|---|---|---|---|
| S1 | 10 | 100% / 50% / 100% | 12 / 24 / 10 | +14 d (n=5) · 5 | -2 d (n=10) · 0 |
| S2 | 10 | 100% / 90% / 100% | 13.5 / 12 / 9.5 | +0 d (n=9) · 1 | -5 d (n=10) · 0 |
| S3 | 10 | 100% / 80% / 100% | 8 / 18 / 11 | +4 d (n=8) · 2 | +6.5 d (n=10) · 0 |

False alarms per astronaut-week (healthy days after calibration): Model 0.065, B1 0.121, B2 0.183.

### Sensitivity to scenario size (detection rate Model / B1 / B2)

| Scale | S1 | S2 | S3 |
|---|---|---|---|
| × 0.5 | 100% / 50% / 100% | 50% / 60% / 80% | 80% / 40% / 80% |
| × 1.0 | 100% / 50% / 100% | 100% / 90% / 100% | 100% / 80% / 100% |
| × 1.5 | 100% / 60% / 100% | 100% / 90% / 100% | 100% / 100% / 100% |

### False-alarm-matched comparison with B2 (model at P_yellow = 90, Model 0.124 vs B2 0.183 false alarms per astronaut-week)

| Scale | S1: detected Model / B2 | S2: detected Model / B2 | S3: detected Model / B2 |
|---|---|---|---|
| × 0.5 | 100% / 100% | 60% / 80% | 90% / 80% |
| × 1.0 | 100% / 100% | 100% / 100% | 100% / 100% |
| × 1.5 | 100% / 100% | 100% / 100% | 100% / 100% |
