### Benchmark at a false-alarm budget of 0.05 per astronaut-week (bench split, scenario sizes × 0.5 and × 1.0)

| Rank | Method | Persistence | FA / astronaut-week | Early detection (≤21 d) | Detected | Mean of median delays (d) |
|---|---|---|---|---|---|---|
| – | B1 fixed clinical thresholds | rule | 0.106 | 44% | 62% | 16.2 |
| 1 | Classical Mahalanobis, 14-day mean (drift) | 3 | 0.049 | 65% | 89% | 18.3 |
| 2 | Combined: Mahalanobis 7-day mean + AE ensemble | 3 | 0.049 | 64% | 87% | 17.0 |
| 3 | Classical Mahalanobis, 14-day mean (drift) | 2 | 0.047 | 64% | 89% | 18.2 |
| 4 | Classical Mahalanobis, 7-day mean (drift) | 3 | 0.049 | 62% | 86% | 17.4 |
| 5 | Classical Mahalanobis, 7-day mean, 3-day smoothed | 2 | 0.049 | 62% | 86% | 17.7 |
| 6 | Classical Mahalanobis, 7-day mean, 3-day smoothed | 3 | 0.046 | 61% | 87% | 18.3 |
| 7 | Combined: Mahalanobis 7-day mean + AE ensemble | 2 | 0.049 | 60% | 84% | 17.7 |
| 8 | AE ensemble x5, 300 train, 3-day smoothed | 2 | 0.049 | 59% | 86% | 17.6 |
| 9 | AE ensemble x5, 300 train | 3 | 0.049 | 58% | 84% | 17.8 |
| 10 | Classical Mahalanobis, 7-day mean (drift) | 2 | 0.049 | 58% | 84% | 19.2 |
| 11 | AE w7 b8, 300 train, latent only | 2 | 0.049 | 57% | 85% | 18.7 |
| 12 | AE v2 (current: w7 b8, 60 train) | 2 | 0.049 | 57% | 80% | 17.2 |
| 13 | AE ensemble x5, 300 train | 2 | 0.049 | 57% | 83% | 17.2 |
| 14 | AE w7 b8, 300 train, latent only | 3 | 0.048 | 57% | 84% | 18.8 |
| 15 | AE ensemble x5, 300 train, 3-day smoothed | 3 | 0.048 | 57% | 85% | 18.4 |
| 16 | AE w7 b8, 300 train, 5-day smoothed | 2 | 0.049 | 57% | 84% | 18.8 |
| 17 | AE v2 (current: w7 b8, 60 train) | 3 | 0.049 | 56% | 82% | 17.0 |
| 18 | AE w7 b8, 300 train + personal fine-tuning | 3 | 0.048 | 56% | 81% | 18.3 |
| 19 | AE w7 b8, 300 train, 3-day smoothed | 3 | 0.049 | 56% | 84% | 18.9 |
| 20 | AE w7 b8, 300 train, 3-day smoothed | 2 | 0.048 | 56% | 83% | 19.1 |
| 21 | AE w7 b8, 300 train | 2 | 0.047 | 55% | 80% | 18.0 |
| 22 | AE w7 b8, 300 train | 3 | 0.049 | 55% | 81% | 18.2 |
| 23 | AE w7 b8, 300 train + personal fine-tuning | 2 | 0.049 | 55% | 80% | 18.2 |
| 24 | AE w14 b8, 300 train | 3 | 0.049 | 54% | 86% | 19.5 |
| 25 | AE w14 b8, 300 train | 2 | 0.048 | 54% | 85% | 19.1 |
| 26 | AE w7 b8, 300 train, 5-day smoothed | 3 | 0.048 | 53% | 84% | 19.6 |
| 27 | Hybrid: max(AE, B2) percentile | 3 | 0.049 | 52% | 81% | 19.0 |
| 28 | AE w7 b4, 300 train | 2 | 0.048 | 51% | 81% | 19.5 |
| 29 | Hybrid: max(AE 3-day smoothed, B2) percentile | 2 | 0.049 | 51% | 80% | 19.5 |
| 30 | Hybrid: max(AE, B2) percentile | 2 | 0.049 | 50% | 80% | 19.7 |
| 31 | Hybrid: max(AE 3-day smoothed, B2) percentile | 3 | 0.048 | 50% | 82% | 19.8 |
| 32 | AE w7 b16, 300 train | 3 | 0.049 | 49% | 78% | 19.8 |
| 33 | AE w7 b4, 300 train | 3 | 0.048 | 49% | 81% | 20.4 |
| 34 | AE w7 b16, 300 train | 2 | 0.049 | 46% | 81% | 21.0 |
| 35 | B2 personal single-indicator, 3-day smoothed | 3 | 0.049 | 43% | 74% | 21.6 |
| 36 | Classical Mahalanobis, 7-day window | 3 | 0.049 | 42% | 70% | 19.6 |
| 37 | Classical Mahalanobis, 7-day window | 2 | 0.049 | 40% | 67% | 19.6 |
| 38 | B2 personal single-indicator, 3-day smoothed | 2 | 0.047 | 37% | 67% | 20.7 |
| 39 | B2 personal single-indicator (max |z|) | 2 | 0.049 | 36% | 66% | 21.7 |
| 40 | B2 personal single-indicator (max |z|) | 3 | 0.049 | 34% | 63% | 21.5 |
| 41 | AE w7 b8, 300 train, reconstruction only | 2 | 0.049 | 25% | 50% | 22.7 |
| 42 | AE w7 b8, 300 train, reconstruction only | 3 | 0.049 | 24% | 50% | 24.4 |
