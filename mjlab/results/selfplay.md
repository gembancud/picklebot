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

**The early check passed** (model_4400, 1,002 of 3,200 iterations). Same seeds, 4218201-4218204, `rally-02-{parent-early,early}-*.json`:

| Measure | Parent | Run 2 | Kill line |
|---|---|---|---|
| **Partner-ball legal in pairs** (contact) | 18.5 % [17.5, 19.4] | **32.3 %** [31.3, 33.4] | above 19.4 % (met) |
| P(5+) | 0.37 % | **1.11 %** [0.90, 1.37] | reported |
| P(4+) | 0.93 % | 2.69 % | reported |
| Feeder-ball legal | 64.1 % | **71.1 %** | not below -5 (met, +7.0) |
| Court main | 75.0 % | 74.4 % | not below -5 (met) |
| Drill v2 | 78.4 % | 79.8 % | not below -5 (met) |
| Move arrival, lowest direction | 84.8 % | 80.2 % | not below -5 (met, -4.6: close) |
| Court falls per episode | | 2.5 % (Wilson low 1.6 %) | met |

- **Plainly:** with cooperative credit, the robot returns its partner's shots 14 points more often after a third of the run. Run 1 lost 4 points at the same stage. It also returns more feeder balls.
- **The weak spot:** the side-steps slipped 4.6 points, near the 5-point line.

**Endpoint: model_6400.** The 6 h cap stopped training at iteration 6,400 of 6,598. The pre-registered endpoint is the last checkpoint before the cap.

**M1 read** (contact hand-off, 4218232, read once; `rally-02-target.json`; 25,149 rallies):

| M1 item | Value | Bar | |
|---|---|---|---|
| Partner-ball legal | **54.3 %** (bootstrap low 53.7 %) | >= 50 %, low >= 0.49 | met |
| Feeder-ball legal | **77.0 %** (low 76.4 %); 75.8 % counting the feeds ended by falls | >= 85 %, low >= 0.84 | **not met** |
| Sides A / B (all shots) | 62.7 / 62.3 % (gap 0.4) | within 3 points | met |
| Court falls per episode | 2.2 % | <= 4 % | met |

**M1 is not met** (feeder-ball legal).

| Reported | Value |
|---|---|
| **P(5+)** (the target) | **7.87 %** [7.54, 8.21] (baseline 0.38 %) |
| P(3+) | 18.8 % |
| P(4+) | 12.1 % |
| Mean rally length | 1.61 |
| Longest rallies (by length 9, 10, 11) | 102, 58, 50 |
| Falls per shot | 0.5 / 0.7 % |
| Crossing read (4218233) | P(5+) 4.1 %, own-ball 41.6 % |

**Shots:**
- legal landings at x 4.1 m (sd 1.0), mean |y| 0.73 m;
- keep-alive-box share 17.3 %;
- flight 1.23 s, ball out 10.3 m/s.

**The rest of the endpoint battery** (`stage5f-r02-summary.json`):
- drill v2 86.0 % (rally5 41 %), court main 75.3 %, falls 2.2 %;
- **move arrival fell in the forward directions:** fwd 72 %, fwd-left 65 %, fwd-right 82 % (the others 92-98 %).

**Training curve:** the partner_return reward was still rising at the cap.

| Iteration | partner_return reward |
|---|---|
| 4,400 | 0.054 |
| 5,400 | 0.088 |
| 6,400 | 0.112 |

**A counting slip, found and fixed (D-138):**
- The own-ball and per-court counts left out feeds that ended in a robot fall (only the side counts had them). So the bootstrap's feeder-ball number (77.0 %) is a little high: counting those feeds, it is 75.8 %.
- The partner-ball number changes by at most the fall rate (about 0.6 % of shots).
- Neither changes the verdict. From now on every count treats a fall as a miss (test).
