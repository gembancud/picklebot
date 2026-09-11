# Critic-key comparison results

Four independent 500,000-experience runs completed from the same full parent. Only the trainer value-estimates key changed between methods. Both seeds used the same interleaved practice and corrected diagnostics. No model was promoted.

| Test | parent | control-s1 | fixed-s1 | fixed-s2 | control-s2 |
|---|---:|---:|---:|---:|---:|
| legacy/air | 91/128 | 90/128 | 86/128 | 85/128 | 91/128 |
| legacy/bounce | 96/128 | 95/128 | 87/128 | 102/128 | 91/128 |
| focus/air | 120/128 | 123/128 | 124/128 | 125/128 | 128/128 |
| focus/bounce | 128/128 | 128/128 | 128/128 | 128/128 | 123/128 |
| bridge/air | 72/128 | 82/128 | 85/128 | 77/128 | 87/128 |
| bridge/bounce | 99/128 | 108/128 | 93/128 | 99/128 | 87/128 |
| lateral/air | 30/128 | 38/128 | 34/128 | 27/128 | 37/128 |
| lateral/bounce | 46/128 | 42/128 | 39/128 | 42/128 | 30/128 |

| Run | All retention gates | Failed gates |
|---|---|---|
| control-s1 | False | lateral/3/bounce |
| fixed-s1 | False | bridge/3/bounce, lateral/3/bounce |
| fixed-s2 | False | lateral/3/air, lateral/3/bounce |
| control-s2 | False | bridge/3/bounce, bridge/5/bounce, lateral/3/bounce, lateral/5/bounce |

Corrected-minus-control earlier-air gains: seed 1 -3.1 percentage points, seed 2 -4.7 points; mean -3.9 points.
Predeclared promising screen passed: False.

| Run | PPO updates | Mean minibatch fraction where value clipping controls the loss |
|---|---:|---:|
| control-s1 | 60 | 0.00% |
| fixed-s1 | 60 | 0.47% |
| fixed-s2 | 60 | 0.40% |
| control-s2 | 60 | 0.00% |

Serving, opening receive and central rally retention are included in the gates. Repeated basic resets across distributions are not independent samples. The raw verification and direction-mode breakdown retain every denominator.

Two training seeds and one common development cohort. Screening evidence only; not full-game acceptance. Clipping may be unhelpful; retain failed outcomes.

Operational recovery: the first control finished normally, but an overly strict controller check demanded all eight asynchronous workers in every PPO buffer. The corrected validator checks positive, accounted-for worker counts per buffer and all workers across the run. Independent worker completion and per-update drill checks remain. The valid first run and preflight were reused; training, seeds, budgets and evaluation criteria were unchanged.

Evidence: [evaluation](critic-key-evidence/evaluation.json), [review](critic-key-evidence/review.json), [direction breakdown](critic-key-evidence/direction-mode-breakdown.json).
