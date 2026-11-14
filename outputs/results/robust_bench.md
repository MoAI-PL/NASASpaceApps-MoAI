### Robustness benchmark — keep synthetic detection, stay quiet on real data

58 variants. Synthetic: early detection on `bench` (S1–S3, sizes × 0.5 and × 1.0, alarm within 21 days) with each variant's threshold set to 0.05 false alarms per astronaut-week. Real: PMData selection half (p01, p03, p05, p07, p09, p11, p13, p15). Rule fixed in advance: lowest real alarm rate among variants at most 5 points below the current model's early detection. Variant groups were added in rounds after diagnosing the previous round (adaptive normal → missing-aware distance → autocorrelation-aware normal → alarm logic and inputs); every round used the selection half only.

| Variant | Early detection (bench) | Detected at all | Real alarms per person-week (selection half) | Real days in alarm |
|---|---|---|---|---|
| Robust EWMA, floor ×1.0, without exercise | 69% | 87% | 0.000 | 0% |
| Robust EWMA, floor ×1.0, without exercise, ends after 7 quiet days **(chosen)** | 71% | 89% | 0.000 | 0% |
| Robust EWMA, floor ×1.0, without exercise, persistence 5, ends after 7 quiet days | 68% | 90% | 0.000 | 0% |
| Autocorrelation-aware, robust EWMA, floor ×1.0, without exercise, ends after 7 quiet days | 66% | 87% | 0.000 | 0% |
| Robust EWMA, floor ×1.0, without exercise, persistence 5 | 67% | 89% | 0.000 | 0% |
| Robust EWMA, floor ×1.0, without exercise, persistence 5, ends after 3 quiet days | 67% | 89% | 0.000 | 0% |
| Robust EWMA, floor ×1.0, without exercise, persistence 4 | 68% | 88% | 0.000 | 0% |
| Autocorrelation-aware, robust EWMA, floor ×1.0, without exercise, persistence 5 | 59% | 86% | 0.000 | 0% |
| Autocorrelation-aware, robust EWMA, floor ×1.0, without exercise, persistence 5, ends after 7 quiet days | 64% | 88% | 0.000 | 0% |
| Robust EWMA (gap 21, ~39 d), floor ×1.0, without exercise, persistence 5 | 67% | 92% | 0.000 | 0% |
| Fixed normal, without exercise, ends after 7 quiet days | 68% | 92% | 0.007 | 1% |
| Robust EWMA, floor ×1.0, persistence 5 | 71% | 90% | 0.028 | 2% |
| Robust EWMA, floor ×1.0, persistence 5, ends after 7 quiet days | 71% | 91% | 0.028 | 5% |
| Rolling normal, gap 21 d, window 56 d | 68% | 88% | 0.035 | 2% |
| Robust EWMA normal (±2 sd), gap 14 d, half-life ~39 d | 69% | 86% | 0.035 | 2% |
| EWMA normal, gap 21 d, half-life ~19 d | 67% | 85% | 0.035 | 2% |
| Rolling (gap 21, 28 d), sd floor ×1.0 | 66% | 90% | 0.035 | 2% |
| Fixed normal, sd floor ×1.0 | 66% | 94% | 0.043 | 2% |
| Rolling normal, gap 21 d, window 28 d | 65% | 87% | 0.043 | 4% |
| Rolling normal, gap 28 d, window 28 d | 71% | 92% | 0.043 | 4% |
| Rolling normal, gap 28 d, window 56 d | 69% | 89% | 0.043 | 3% |
| EWMA normal, gap 14 d, half-life ~19 d | 69% | 84% | 0.043 | 2% |
| EWMA normal, gap 14 d, half-life ~39 d | 68% | 84% | 0.043 | 2% |
| EWMA normal, gap 21 d, half-life ~39 d | 71% | 88% | 0.043 | 2% |
| Robust EWMA normal (±2 sd), gap 21 d, half-life ~39 d | 70% | 87% | 0.043 | 2% |
| Fixed normal, trained with slow drift (0.05) | 66% | 89% | 0.043 | 2% |
| Fixed normal, trained with slow drift (0.1) | 62% | 89% | 0.043 | 2% |
| Autocorrelation-aware (fixed normal) | 58% | 88% | 0.043 | 2% |
| Autocorrelation-aware, robust EWMA (gap 14, ~19 d) | 66% | 84% | 0.043 | 2% |
| Autocorrelation-aware, robust EWMA (gap 14, ~19 d), floor ×1.0 | 65% | 85% | 0.043 | 2% |
| Current model (fixed 21-day normal) (version 1) | 66% | 89% | 0.050 | 2% |
| Rolling normal, gap 14 d, window 28 d | 68% | 85% | 0.050 | 4% |
| Rolling normal, gap 14 d, window 56 d | 66% | 85% | 0.050 | 2% |
| Robust EWMA normal (±2 sd), gap 14 d, half-life ~19 d | 68% | 83% | 0.050 | 2% |
| EWMA normal, gap 21 d, half-life ~10 d | 67% | 85% | 0.050 | 3% |
| Robust EWMA normal (±2 sd), gap 21 d, half-life ~10 d | 67% | 86% | 0.050 | 2% |
| Robust EWMA normal (±2 sd), gap 21 d, half-life ~19 d | 69% | 87% | 0.050 | 2% |
| Robust EWMA (gap 14, ~19 d), trained with slow drift (0.05) | 69% | 84% | 0.050 | 2% |
| Robust EWMA (gap 14, ~19 d), trained with slow drift (0.1) | 68% | 86% | 0.050 | 2% |
| Robust EWMA (gap 14, ~19 d), sd floor ×1.0 | 68% | 88% | 0.050 | 2% |
| Personal score scale, robust EWMA (gap 14, ~19 d), floor ×1.0 | 69% | 86% | 0.050 | 2% |
| Autocorrelation-aware + personal score scale | 59% | 86% | 0.050 | 2% |
| Autocorrelation-aware + personal score scale, robust EWMA, floor ×1.0 | 66% | 84% | 0.050 | 2% |
| Robust EWMA, floor ×1.0, alarm ends after 7 quiet days | 71% | 89% | 0.050 | 7% |
| EWMA normal, gap 14 d, half-life ~10 d | 68% | 84% | 0.057 | 2% |
| Robust EWMA normal (±2 sd), gap 14 d, half-life ~10 d | 67% | 82% | 0.057 | 2% |
| Fixed normal, ends after 7 quiet days | 70% | 92% | 0.057 | 8% |
| Autocorrelation-aware, sd floor ×1.0 | 61% | 92% | 0.064 | 2% |
| Personal score scale (fixed normal) | 67% | 89% | 0.064 | 2% |
| Missing-aware, robust EWMA (gap 14, ~19 d), floor ×1.0, shrinkage 0.6 | 70% | 89% | 0.149 | 12% |
| Missing-aware, robust EWMA (gap 14, ~19 d) | 68% | 86% | 0.163 | 14% |
| Missing-aware, robust EWMA (gap 14, ~19 d), floor ×1.0, shrinkage 0.3 | 71% | 88% | 0.163 | 13% |
| Missing-aware, robust EWMA (gap 14, ~19 d), sd floor ×1.0 | 69% | 88% | 0.177 | 14% |
| Missing-aware, covariance shrinkage 0.6 | 67% | 89% | 0.177 | 16% |
| Missing-aware, sd floor ×1.0 | 68% | 94% | 0.199 | 18% |
| Missing-aware distance (fixed normal) | 67% | 91% | 0.206 | 17% |
| Missing-aware, robust EWMA (gap 21, ~39 d), sd floor ×1.0 | 67% | 89% | 0.206 | 16% |
| Missing-aware, covariance shrinkage 0.3 | 68% | 91% | 0.206 | 17% |

**Confirmation (run once):** PMData confirmation half (p02, p04, p06, p08, p10, p12, p14, p16) and the dev split.

| Model | Real alarms per person-week, confirmation half | All 16 people | Days in alarm (all) | Dev false alarms per astronaut-week | Dev early detection S1 / S2 / S3 |
|---|---|---|---|---|---|
| Current model (fixed 21-day normal) | 0.007 | 0.029 | 1% | 0.045 | 90% / 90% / 90% |
| Robust EWMA, floor ×1.0, without exercise, ends after 7 quiet days | 0.000 | 0.000 | 0% | 0.069 | 100% / 90% / 100% |

Notes on discipline: (1) the variant grid was built in rounds on simulator-1 data, and the script then printed the confirmation-half result of three interim winners; (2) on simulator-2 data the detector benchmark chose the 14-day window, so this benchmark was run with `--window 14` (a 7-day run is kept in robust_bench_w7.json); (3) after the first confirmation a missing-data bug was found (an input with no values in days 1-21, e.g. a heart rate first recorded on day 61, was compared with the synthetic population mean); it was fixed for every person alike and selection and confirmation were rerun once; the winner did not change. The hold-out split (S5) was not used.

Real data: PMData (Thambawita et al. 2020, CC BY 4.0), 4 of 9 inputs. Synthetic data calibrated on published sources — proof of concept, not clinical validation.
