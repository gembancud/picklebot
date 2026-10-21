# Rally target: run log (D-134 onward)

**Target** (`rally-target.md`, frozen): in two-robot pair play, P(5+ good shots in a row) >= 0.80 (Wilson low >= 0.78, >= 1,000 rallies, development seeds), sides within 3 points, court falls <= 4 % per episode. Every target read uses the contact hand-off (D-135). The old crossing read is reported alongside.

Panel rounds: `selfplay-review.md`. Seeds: `seed-ledger.json` (allocation_rally_target, 4218000-4218999).

## Baseline: Stage 5H run 4's endpoint (s5h-04-pairs/model_3398)

R4 protocol, 2,048 envs (1,024 courts), 120 s. `scripts/rally_baseline.sh`. Results: `rally-baseline-{crossing,contact}.json`.

| Measure | Crossing hand-off (old, 4218000) | Contact hand-off (target read, 4218002) |
|---|---|---|
| Rallies | 34,370 | 35,812 |
| **P(5+)** (the target) | 0.29 % [0.24, 0.35] | **0.38 %** [0.32, 0.45] |
| P(4+) | 0.73 % | 0.98 % |
| Mean rally length | 0.88 | 0.78 |
| Own-ball legal (partner's shots) | 13.1 % [12.7, 13.5] | **19.2 %** [18.8, 19.7] |
| Feeder-ball legal | 76.5 % | **64.7 %** [64.3, 65.2] |
| Sides A / B (all shots) | 46.7 / 46.0 % | 45.3 / 44.2 % |
| Falls per shot A / B | 0.8 / 0.8 % | 3.1 / 3.4 % |

- **A bug, found and fixed:** the first contact read (seed 4218001, kept as `rally-baseline-contact-void-stall.json`) is void. When a return faulted, the receiver's copy was left out of the counts but never marked as ended, so that court never restarted (14,341 rallies instead of about 35,000). `pairs.py` now parks the receiver and only leaves its copy out of the counts. A test checks that the court restarts.
- **What changes with the contact hand-off:** the robot returns more of its partner's shots (it sees them earlier). But it falls about 4 times as often, and returns the feeder ball less often. Run 4 never trained with a ball leaving the far paddle, so this is the run 1 question.
- **The parent bars for run 1's kill lines** are its own early reads on the same seeds (4218100-4218103), not this table.

## Run 1: pair self-play with the contact hand-off (D-135)

`scripts/rally_run01.sh`. Parent s5h-04-pairs/model_3398, 900 iterations, training seed 79, 12,288 envs. Early kill at model_3700 (`scripts/rally_check.py early`).

(pending)
