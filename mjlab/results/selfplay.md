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

## Run 3: run 2 continued unchanged (D-139)

`scripts/rally_run03.sh`. Parent rally-02-coop/model_6400 with its optimizer, the same task, training seed 81, no critic warm-up, 6 h cap. Early kill at model_7300 (`rally_check.py early-continuation`). Endpoint: M1 on 4218332, read once.

**Pre-launch diagnostic** (model_6400, pairs, contact; reported): with a 2 s refeed delay (4218305) against 0.2 s (4218304):

| Refeed delay | Partner-ball legal | Feeder-ball legal | P(5+) |
|---|---|---|---|
| 0.2 s | 53.0 % | 75.1 % | 6.7 % |
| 2 s | 55.6 % | 75.5 % | 8.1 % |

Recovery time does not explain the feeder-ball gap.

**The early check passed** (model_7300; the parent re-read on 4218301-4218304), but the run is flat:

| Measure | Parent | Run 3 | Kill line |
|---|---|---|---|
| Partner-ball legal | 53.0 % (low 51.8 %) | 51.7 % (low 50.6 %) | 49.8 % |
| Feeder-ball legal | 75.1 % | 75.7 % (low 74.6 %) | 72.1 % |
| P(5+) | 6.7 % | 6.3 % | reported |
| Court main | 75.6 % | 74.5 % | -5 points |
| Drill v2 | 79.3 % | 78.9 % | -5 points |
| Lowest move arrival | 61.5 % | 61.1 % | -5 points |
| Court falls per episode | | 2.0 % | met |

**Plainly:** after 900 more iterations nothing moved, with no gain and no loss. As pre-registered, the run continues to its fixed endpoint (no early stop for futility). The panel plans run 4 at the endpoint.

**Endpoint: model_9200** (the 6 h cap). M1 read on 4218332, read once (`rally-03-target.json`, 24,350 rallies):

| M1 item | Value | Bar | |
|---|---|---|---|
| Partner-ball legal | **55.9 %** (bootstrap low 55.4 %) | >= 50 % | met |
| Feeder-ball legal | **77.9 %** (low 77.4 %; D-138 counting) | >= 85 % | **not met** |
| Sides | 63.9 / 64.0 % (gap 0.1) | within 3 points | met |
| Court falls per episode | 2.3 % | <= 4 % | met |

**M1 is not met.**

| Reported | Value |
|---|---|
| **P(5+)** | **8.9 %** [8.5, 9.2] (run 2: 7.9 %) |
| P(3+) | 21.2 % |
| P(4+) | 13.7 % |
| Mean rally length | 1.71 |
| Rallies of 10, 11, 12, 13 good shots | 65, 38, 36, 16 |
| Falls per shot | 0.4 / 0.5 % |
| Crossing read (4218333) | P(5+) 4.1 %, own-ball 42.5 % |

**The endpoint battery:**
- drill v2 86.3 %, court main 75.7 %;
- move arrival recovered part of run 2's loss: fwd 81 %, fwd-left 72 %, left 88 %, fwd-right 88 %; the others 93-99 %.

**Feeder-ball legal by family** (feeder balls only, D-139; contact / legal):

| Weakest families | Contact / legal |
|---|---|
| **reach_deep** | **38 % / 30 %** |
| **cross_backhand** | **56 % / 50 %** |
| fast | 70 % / 60 % |
| reach_backhand | 73 % / 70 % |
| low | 79 % / 73 % |

- Every other family is 78-94 % legal.
- The 17 families are fed evenly. Lifting reach_deep and cross_backhand to 85 % alone would add about 5 points.

**Against the panel trigger** (a feeder-ball gain of at least 3 points): +0.9 to +2.1 points over run 2's endpoint (75.8-77.0 %), so the trigger fires. The continuation gave little: partner-ball +1.6, P(5+) +1.0.

## Interim video: rally run 2's endpoint (panel round 25, 4/5; M1 not met)

`scripts/rally_videos02.sh`, development seed 4218240, contact hand-off, 4 courts, 90 s. Clips chosen before rendering:
- `docs/media/g1-rally-run2-interim-first.mp4`: court 0, every rally in order, not picked;
- `docs/media/g1-rally-run2-interim-longest.mp4`: the longest rally of the 4 courts, **13 good shots**, picked and labelled so; GIF preview `docs/media/g1-rally-run2-interim.gif`.

No gate statistic is taken from this read (64 rallies).

**A cost to note:** the render took 2 h 33 min of wall time (CPU-bound). Run 3 waited for it, so nothing else used the GPU while it trained. Future videos should be shorter (30-45 s).

**A suspected training-side bug, found while run 3 trains (to verify after its endpoint, then panel):**
- In pair mode, move-drill episodes (`move_prob` 0.35: walk to a spot, no ball; `move_drill.py`) are not respected.
- `PairCourts` hands partner returns and feeder balls to any parked env, and `_refeed` does not check `drill.move_ep`. So a robot in a move episode is fed balls while it is told to walk to a spot. Its ball-approach shaping is also switched off in move episodes (`return_stand.py` ~line 1165).
- Outside pair mode this cannot happen: a move episode is tallied, so it never refeeds.
- **If confirmed,** it would explain two problems since Stage 5H run 4:
  - the forward move-arrival forgetting (the move drill is no longer clean practice);
  - part of the partner-ball loss (balls handed to a robot that is walking away).

**The move-drill bug is confirmed** (`scripts/diag/pair_move_bug.py`; rally-03 model_9200, the Coop task in training conditions, 1,024 envs, 40 s):

| | Feeder balls | Hand-offs | Balls to robots in move episodes | Partner-ball legal, free / move-episode robots |
|---|---|---|---|---|
| As trained (4218340, `rally-03-movebug.json`) | 5,905 | 6,419 | **38.1 %** | 32.8 % / 27.1 % |
| With the fix (4218341, `rally-03-movebug-fixed.json`) | 5,903 | 2,664 | 0 % | 32.7 % / none |

- **The fix** (`PairCourts.step(busy=...)`, cfg `pair_respect_moves`, default off; tests `test_d140_*`):
  - a busy robot gets no ball;
  - a return to a busy partner ends the rally once it lands;
  - the feeder ball goes to the free side;
  - a court with both robots busy waits.
- **The cost:** hand-offs fall by about 60 % per hour of training. The panel decides how to use the fix (round 26).

## Run 4: ball-free drill episodes respected in pair mode (D-140)

`scripts/rally_run04.sh`. Coop-Moves task, from rally-03 model_9200 with its optimizer, training seed 82, no critic warm-up, 6 h cap.
- **Training log:** the move_arrival reward rose from 0.025 (end of run 3) to about 0.21 in the first 350 iterations, so the move drill is being completed again.
- **The partner_return reward** fell from about 0.10 to 0.04, as expected with about 60 % fewer hand-offs.

**The early check passed** (model_10100; the parent re-read on 4218401-4218404):

| Measure | Parent (run 3 endpoint) | Run 4 | Kill line |
|---|---|---|---|
| Partner-ball legal | 54.7 % (low 53.5 %) | 52.6 % (low 51.3 %) | 51.5 % |
| Feeder-ball legal | 76.4 % | 77.0 % (low 75.9 %) | 73.4 % |
| P(5+) | 7.6 % | 6.9 % | reported |
| Court main | 74.7 % | 75.4 % | -5 points |
| Drill v2 | 80.1 % | **82.2 %** | -5 points |
| **Lowest move arrival** | 69.2 % | **92.7 %** | -5 points |
| Court falls per episode | | 2.5 % | met |

- **Plainly:** with the drill episodes clean, the footwork came back. The lowest direction rose 23 points, the largest single gain in this loop.
- Feeder-ball legal has not moved yet. Partner-ball legal fell 2 points (fewer hand-offs to learn from), close to its kill line.
- The run continues to its fixed endpoint.

**Endpoint: model_12100** (the 6 h cap). M1 read on 4218432, read once (`rally-04-target.json`, 24,701 rallies):

| M1 item | Value | Bar | |
|---|---|---|---|
| Partner-ball legal | **53.9 %** (bootstrap low 53.2 %) | >= 50 % | met |
| Feeder-ball legal | **80.2 %** (low 79.7 %) | >= 85 % | **not met** |
| Sides | 63.7 / 63.4 % (gap 0.3) | within 3 points | met |
| Court falls per episode | 2.7 % | <= 4 % | met |

**M1 is not met.** Feeder-ball legal is the closest yet (+2.3 points on run 3), but the panel trigger (+3) fires.

| Reported | Value |
|---|---|
| P(5+) | 8.1 % [7.7, 8.4] (run 3: 8.9 %) |
| P(3+) | 18.6 % |
| P(4+) | 12.1 % |
| Rallies of 12-15 good shots | 35, 28, 16, 8 |
| Crossing read (4218433) | P(5+) 4.2 %, own-ball 39.7 % |

- **Footwork is restored everywhere:** move arrival is 95.7-99.7 % in all 8 directions. The old stage item "arrival >= 90 % every direction" is met for the first time since Stage 5F. Drill v2 87.2 %, court main 75.9 %.
- **Partner-ball legal fell 2 points** with about 60 % fewer hand-offs to practise on.

**Feeder-ball legal by family** (contact / legal), against run 3:

| Family | Run 3 legal | Run 4 contact / legal |
|---|---|---|
| reach_deep | 30 % | 57 / 45 % |
| cross_backhand | 50 % | 63 / 56 % |
| fast | 60 % | 75 / 66 % |
| reach_backhand | | 77 / 73 % |
| low | | 81 / 75 % |
| drop | | 83 / 75 % |
| backhand | | 82 / 77 % |

The rest are 85-94 %.

**Training-free reach check** (`scripts/diag/feeder_reach.py`, seed 4218440, `feeder-reach-check.json`): the least walking speed to a contact stance per feed, from the planner's walkable-contact model.
- The model is conservative: 56 % of feeds need 1.5 m/s or less, yet 80 % are returned.
- reach_deep is the hardest by geometry (median 2.35 m/s).
- At similar speeds, backhand-side families trail their forehand mirrors by 10-30 points (reach 73 / 94 %, cross 56 / 85 %, plain 77 / 88 %). That is a backhand skill gap, not a reach limit.
