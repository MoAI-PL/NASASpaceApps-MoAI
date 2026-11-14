### Benchmark at a false-alarm budget of 0.05 per astronaut-week (bench split, scenario sizes × 0.5 and × 1.0)

| Rank | Method | Persistence | FA / astronaut-week | Early detection (≤21 d) | Detected | Mean of median delays (d) |
|---|---|---|---|---|---|---|
| – | B1 fixed clinical thresholds | rule | 0.084 | 39% | 58% | 17.7 |
| 1 | Classical Mahalanobis, 7-day mean (drift) | 3 | 0.048 | 82% | 96% | 15.3 |
| 2 | Classical Mahalanobis, 7-day mean, 3-day smoothed | 3 | 0.049 | 82% | 96% | 15.7 |
| 3 | Classical Mahalanobis, 14-day mean (drift) | 2 | 0.048 | 81% | 96% | 15.2 |
| 4 | Combined: Mahalanobis 7-day mean + AE ensemble | 3 | 0.048 | 81% | 93% | 15.2 |
| 5 | Classical Mahalanobis, 14-day mean (drift) | 3 | 0.048 | 81% | 95% | 15.2 |
| 6 | Combined: Mahalanobis 7-day mean + AE ensemble | 2 | 0.049 | 79% | 93% | 14.8 |
| 7 | Classical Mahalanobis, 7-day mean, 3-day smoothed | 2 | 0.045 | 79% | 94% | 15.6 |
| 8 | Classical Mahalanobis, 7-day mean (drift) | 2 | 0.049 | 78% | 95% | 15.1 |
| 9 | AE ensemble x5, 300 train, 3-day smoothed | 3 | 0.049 | 68% | 89% | 17.0 |
| 10 | AE ensemble x5, 300 train | 2 | 0.049 | 67% | 86% | 16.9 |
| 11 | AE w14 b8, 300 train | 2 | 0.049 | 67% | 91% | 17.4 |
| 12 | AE w7 b16, 300 train | 3 | 0.049 | 66% | 84% | 16.2 |
| 13 | AE ensemble x5, 300 train, 3-day smoothed | 2 | 0.049 | 66% | 86% | 18.2 |
| 14 | AE ensemble x5, 300 train | 3 | 0.049 | 66% | 87% | 17.0 |
| 15 | AE w14 b8, 300 train | 3 | 0.049 | 65% | 91% | 18.2 |
| 16 | B2 personal single-indicator, 3-day smoothed | 3 | 0.049 | 64% | 88% | 19.1 |
| 17 | AE w7 b4, 300 train | 2 | 0.049 | 63% | 90% | 19.6 |
| 18 | B2 personal single-indicator (max |z|) | 3 | 0.049 | 61% | 87% | 16.9 |
| 19 | B2 personal single-indicator, 3-day smoothed | 2 | 0.048 | 61% | 86% | 18.5 |
| 20 | Classical Mahalanobis, 7-day window | 3 | 0.049 | 60% | 80% | 17.7 |
| 21 | AE w7 b4, 300 train | 3 | 0.048 | 60% | 87% | 20.4 |
| 22 | AE w7 b16, 300 train | 2 | 0.047 | 58% | 81% | 19.2 |
| 23 | Classical Mahalanobis, 7-day window | 2 | 0.047 | 56% | 76% | 17.7 |
| 24 | B2 personal single-indicator (max |z|) | 2 | 0.049 | 55% | 82% | 18.7 |
| 25 | Hybrid: max(AE 3-day smoothed, B2) percentile | 2 | 0.048 | 54% | 80% | 19.0 |
| 26 | AE v2 (current: w7 b8, 60 train) | 2 | 0.049 | 53% | 79% | 18.9 |
| 27 | AE v2 (current: w7 b8, 60 train) | 3 | 0.048 | 53% | 81% | 19.2 |
| 28 | Hybrid: max(AE, B2) percentile | 3 | 0.049 | 52% | 77% | 20.2 |
| 29 | AE w7 b8, 300 train, 5-day smoothed | 3 | 0.049 | 52% | 78% | 19.0 |
| 30 | Hybrid: max(AE, B2) percentile | 2 | 0.046 | 52% | 78% | 21.0 |
| 31 | Hybrid: max(AE 3-day smoothed, B2) percentile | 3 | 0.048 | 51% | 76% | 19.6 |
| 32 | AE w7 b8, 300 train, 3-day smoothed | 3 | 0.049 | 49% | 76% | 19.8 |
| 33 | AE w7 b8, 300 train, 5-day smoothed | 2 | 0.047 | 49% | 77% | 20.0 |
| 34 | AE w7 b8, 300 train | 3 | 0.049 | 48% | 73% | 19.8 |
| 35 | AE w7 b8, 300 train + personal fine-tuning | 3 | 0.048 | 48% | 74% | 19.8 |
| 36 | AE w7 b8, 300 train, 3-day smoothed | 2 | 0.048 | 47% | 73% | 20.8 |
| 37 | AE w7 b8, 300 train | 2 | 0.049 | 47% | 73% | 21.6 |
| 38 | AE w7 b8, 300 train + personal fine-tuning | 2 | 0.049 | 45% | 71% | 22.8 |
| 39 | AE w7 b8, 300 train, reconstruction only | 3 | 0.049 | 44% | 66% | 18.1 |
| 40 | AE w7 b8, 300 train, reconstruction only | 2 | 0.049 | 44% | 68% | 18.4 |
| 41 | AE w7 b8, 300 train, latent only | 2 | 0.049 | 43% | 74% | 23.8 |
| 42 | AE w7 b8, 300 train, latent only | 3 | 0.049 | 42% | 72% | 22.4 |
