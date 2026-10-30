# Evaluation 2026-10-30T15:10:55.177708+00:00

- model: `deepseek-v4.1-flash`, prompt `facts-v7`, rules v1, metrics v2
- cases: 19, runs per case: 1, workers: 1
- tag: `facts-v7-inline-both`

| metric | baseline | pipeline | denominator |
| --- | --- | --- | --- |
| calls | 19 | 19 | all attempts |
| parsed answers | 18 | 19 | all attempts |
| parse rate | 95% | 100% | all attempts |
| transport failures | 1 | 0 | all attempts |
| content failures | 0 | 0 | all attempts |
| avg latency (ms) | 4337 | 4340 | parsed |
| p95 latency (ms) | 6015 | 7040 | parsed |
| prompt tokens | 5775 | 8523 | parsed |
| completion tokens | 4181 | 4534 | parsed |
| wrong price | 0 | n/a | parsed (baseline) |
| claims rules reject | 2 | n/a | parsed (baseline) |
| unknown add-ons | 0 | n/a | parsed (baseline) |
| unsafe releases | 2 | 0 | parsed |
| original request satisfied | n/a | 6 | all attempts |
| narrowed option available | n/a | 6 | all attempts |
| honest "no solution" | n/a | 7 | all attempts |

Pipeline `unsafe releases` counts option rows whose displayed price or verdict disagrees with a fresh recomputation from the rules; it is measured every run, not assumed to be zero. Unparseable answers count as failures in every rate whose denominator is "all attempts".

## Per case

| case | rules say | baseline (first run) | pipeline (first run) |
| --- | --- | --- | --- |
| case-01-missing-both | no 500 USD | 500.0 USD (claimed feasible: True) | 1 option(s), 0 deliverable |
| case-02-missing-budget | no 500 USD | unparseable | 1 option(s), 0 deliverable |
| case-03-missing-deadline | no 500 USD | 500.0 USD (claimed feasible: True) | 1 option(s), 0 deliverable |
| case-04-budget-gap | no 700 USD | 700.0 USD (claimed feasible: False) | 2 option(s), 1 deliverable |
| case-05-exact-budget | feasible 700 USD | 700.0 USD (claimed feasible: True) | 1 option(s), 1 deliverable |
| case-06-unsupported-ordering | no 500 USD | 500.0 USD (claimed feasible: False) | 2 option(s), 1 deliverable |
| case-07-unsupported-multilanguage | no 500 USD | 500.0 USD (claimed feasible: True) | 2 option(s), 1 deliverable |
| case-08-deadline-conflict-no-assets | no 500 USD | 500.0 USD (claimed feasible: False) | 1 option(s), 0 deliverable |
| case-09-deadline-exact | feasible 500 USD | 500.0 USD (claimed feasible: True) | 1 option(s), 1 deliverable |
| case-10-deadline-one-day-short | no 500 USD | 500.0 USD (claimed feasible: False) | 1 option(s), 0 deliverable |
| case-11-copywriting-over-budget | no 650 USD | 650.0 USD (claimed feasible: False) | 2 option(s), 1 deliverable |
| case-12-revision-addon-fits | feasible 550 USD | 550.0 USD (claimed feasible: True) | 1 option(s), 1 deliverable |
| case-13-external-link-free | feasible 500 USD | 500.0 USD (claimed feasible: True) | 1 option(s), 1 deliverable |
| case-14-zero-pages | no 0 USD | 0.0 USD (claimed feasible: False) | 2 option(s), 0 deliverable |
| case-15-unknown-addon | no 500 USD | 500.0 USD (claimed feasible: False) | 2 option(s), 1 deliverable |
| case-16-large-page-count | feasible 1000 USD | 1000.0 USD (claimed feasible: True) | 1 option(s), 1 deliverable |
| case-17-unsupported-and-over-budget | no 700 USD | 700.0 USD (claimed feasible: False) | 2 option(s), 1 deliverable |
| case-18-three-problems-at-once | no 700 USD | 700.0 USD (claimed feasible: False) | 2 option(s), 0 deliverable |
| case-19-single-page-tight-deadline | feasible 500 USD | 500.0 USD (claimed feasible: True) | 1 option(s), 1 deliverable |

_calls in denominator: 19 per arm._
