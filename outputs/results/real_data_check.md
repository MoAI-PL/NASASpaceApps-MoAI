### Real-data check (PMData, frozen model — nothing fitted or tuned)

| Data | People | Person-weeks | Alarms per person-week Model / B1 / B2 | Days in alarm Model / B1 / B2 |
|---|---|---|---|---|
| Real people (PMData), 4 inputs | 16 | 280.1 | 0.000 / 0.021 / 0.068 | 0% / 0% / 2% |
| Synthetic healthy astronauts, same 4 inputs | 50 | 707.1 | 0.011 / 0.037 / 0.171 | 2% / 1% / 7% |
| Synthetic healthy astronauts, all 9 inputs | 50 | 707.1 | 0.057 / 0.103 / 0.216 | 9% / 3% / 8% |

Alarm = yellow or worse (model) or a baseline alarm, counted after the 21-day calibration. The PMData people are not labelled healthy (winter, flu season), so their alarms are not all false. Missing inputs enter the model as 'at your normal', which makes it quieter. Synthetic data calibrated on published sources — proof of concept, not clinical validation.

Source: PMData: Thambawita V. et al. (2020), PMData: a sports logging dataset, Proc. ACM MMSys'20, doi:10.1145/3339825.3394926, CC BY 4.0, https://datasets.simula.no/pmdata.
