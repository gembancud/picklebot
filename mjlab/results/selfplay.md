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

**Killed at the early check (model_3700, 302 of 900 iterations).** Reads on the same seeds (4218100-4218103), `rally-01-{parent-early,early}-*.json`:

| Measure | Parent | Run 1 | Kill line |
|---|---|---|---|
| Own-ball legal in pairs (contact) | 18.3 % [17.4, 19.2] | **14.2 %** [13.4, 15.1] | above 19.2 % (failed) |
| P(5+) | 0.34 % | 0.11 % [0.06, 0.21] | reported |
| P(4+) | 0.88 % | 0.50 % | reported |
| Feeder-ball legal | 64.4 % | 63.7 % | not below -5 (met) |
| Court main | 75.4 % | 73.3 % | not below -5 (met) |
| Drill v2 | 76.6 % | 73.7 % | not below -5 (met) |
| Move arrival, lowest direction | 86.1 % | **74.3 %** | not below -5 (failed) |
| Court falls per episode | | 2.0 % (Wilson low 1.2 %) | low <= 4 %, point <= 7.4 % (met) |

- **Plainly:** training with the ball handed over at the partner's contact made the robot worse at returning the partner's shots, and it forgot part of its side-stepping. The endpoint battery was skipped.
- **A check for a training-side bug:** the rewards have no miss penalty, so a partner's faulted shot gives the receiver nothing (no wrong punishment).
- Panel round 23 decides what comes next.

## Run 2: cooperative credit (D-137)

`scripts/rally_run02.sh`.
- **Task:** `Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-G1`: placement weight 0, partner_return 150, court share 0.80.
- **Training:** parent s5h-04-pairs/model_3398, 3,200 iterations, 6 h cap, training seed 80, 12,288 envs.
- **Checks:** early kill at model_4400. Endpoint: M1 (`rally-milestones.md`) and the target, read once on 4218232.

**The court-share dry read** (rally run 1's task and the parent, training conditions, 4218200, `rally-02-share.json`):
- hand-offs were 49.97 % of feeds started (9,568 of 19,148), so run 1 trained on about 34 % court feeds;
- partner-ball legal 15.0 % (bootstrap low 14.1 %), feeder-ball legal 78.2 % (low 77.2 %).

(pending)
