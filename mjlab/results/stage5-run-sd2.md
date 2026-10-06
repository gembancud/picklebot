# Stage 5 Drill 2 run S-D2 (`student-swing-d2`): shadow swing on the student

Date: 2026-10-07.
- **Task:** `Picklebot-Student-Swing-G1`: 25 % move-to-spot, 50 % ghost-ball shadow swing over all 14 families, 25 % real hitting on the hitting teacher's families.
- **Network and algorithm:** the 1024-512-256 student with RegPPO:
  - pull-back toward the frozen `student-big-03/model_1500`, coefficient 10 → 1 over 1,500 updates;
  - 100-iteration critic warm-up;
  - learning rate 1e-4, desired KL 0.005.
- **Train seed 1.**

## The run
- **Unfreezing at iteration 100:** pull-back 83, falls spiked to about 8 per log window, then recovered within about 50 iterations (pull-back 0.007 by iteration 150).
- **From about iteration 500:** training falls and action std rose steadily (std 0.50 → 0.79, falls 1.2 → 4.7) and the mean reward turned negative, while deterministic diagnostics at iterations 200, 500 and 700 kept walking at 100 % and hitting at about 99 %.
- **Simulation blow-ups:** single iterations with value loss 644 (it. 658) and 3.4e9 (it. 734), from a robot reaching impossible base speeds (body_ang_vel −1,830, foot_slip −117 in one window).
- **Crash at iteration 953:** a blow-up produced a NaN that a metrics histogram turned into a negative index (CUDA scatter assert).
  - **Fixed in `107c049`:** NaN-safe histograms, plus a `blew_up` termination for later tasks.
  - **Endpoint:** the last saved checkpoint, **`model_900`**.

## Evaluation (`model_900`; swings dev seed 4,200,200, move 4,200,201, hit 4,200,202; reference `student-big-03/model_1500` on the same seeds)
**Shadow swing** (swing episodes only; d_min = closest paddle–ball distance in the window):

| Family | Swings | Median d_min | Within 0.15 m | Paddle v_x | Feet set |
|---|---:|---:|---:|---:|---:|
| easy / wide / backhand | 591 / 600 / 583 | 6 / 6 / 6 cm | 96 / 98 / 70 % | 5.9–6.1 m/s | 74 / 43 / 63 % |
| deep / short / high | 581 / 570 / 599 | 4 / 4 / 6 cm | 97 / 96 / 94 % | 5.9–7.4 | 61 / 80 / 79 % |
| low / fast / topspin / backspin | 569 / 628 / 584 / 600 | 9 / 9 / 4 / 6 cm | 93 / 90 / 99 / 97 % | 5.4–6.2 | 43 / 19 / 44 / 73 % |
| reach_forehand | 586 | 4 cm | 96 % | 7.3 | 17 % |
| **reach_backhand** | 549 | **39 cm** | 22 % | 5.8 | 0.4 % |
| **reach_short** | 647 | **81 cm** | 2 % | 1.4 | 0.2 % |
| **reach_deep** | 556 | **94 cm** | 7 % | 0.5 | 10 % |

- **Falls in swing episodes:** 697 of 4,133 (16.9 %).
- **Recovery error:** median 1.53 m.
- **Walking:** 99.95 % arrival (reference 99.86 %).
- **Hitting:** legal and contact within 0.3 points of the reference on every family; A/B gain +0.846 vs +0.838; 0 falls.

## Multi-task check (D-044)
**No interference:** walking and hitting are unchanged against the distilled student on the same seeds, so separate critic heads are not needed.

## Drill 2 gate: NOT MET
| Criterion | Result | Verdict |
|---|---|---|
| Median contact error ≤ 0.15 m on every family geometry | 11 of 14 pass (4–9 cm); reach backhand / short / deep 0.39 / 0.81 / 0.94 m | **fail** |
| Feet set ≥ 70 % | below 70 % on 9 of 14 families | **fail** |
| Median recovery error ≤ 0.5 m | 1.53 m | **fail** |
| Falls ≤ 1 % | 16.9 % in swing episodes | **fail** |
| Walking and hitting within 5 points | pass | pass |

Timing is not measured separately: an early or late swing shows as a larger d_min. Rising action std suggests the entropy bonus is too strong for a fine-tune, which shows up in training falls.

## Diagnosis
- **The student swings accurately wherever it already reaches the ball.** This includes reach_forehand.
- **Reach backhand, short and deep fail on footwork, not swing.** Nothing tells the policy where to go: during the window its spot input points at the recovery spot, and its ball input alone has not led it to the interception point.
- **Falls and the missing set feet come from lunging at balls while still moving.**

## Follow-up S-D2b (loop rule 8, 1 of 2), decided before launch
**One change: the footwork hint.** In swing episodes, the existing spot input shows the predicted interception stance until the window closes (`swing_hint`), then the true recovery spot. The prediction uses per-family constants measured from the analytic ball; median error 3–23 cm (`tests/test_swing_hint.py`).
- **Not counted as a variable:** the bug fixes, i.e. NaN-safe histograms and the `blew_up` termination for simulation blow-ups.
- **Setup:** warm-started from `student-swing-d2/model_900`, the same pull-back reference `student-big-03/model_1500`, and otherwise identical settings (`Picklebot-Student-Swing-Hint-G1`).
- **Planned S-D2c if needed:** lower entropy bonus (0.01 → 0.002) to stop std drift.

Files: `stage5-sd2-swing.json`, `stage5-sd2-w-move.json`, `stage5-sd2-wref-move.json`, `stage5-sd2-h-*.json`, `stage5-sd2-href-*.json`.
