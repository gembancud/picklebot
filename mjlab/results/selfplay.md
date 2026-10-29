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

## Run 5: practise the weak feeder families (D-141)

`scripts/rally_run05.sh`.
- **Task:** Coop-Moves-Weak (COURT_MIX_WEAK), from rally-04 model_12100 with its optimizer.
- **Training:** training seed 83, no critic warm-up, 6 h cap.
- **Early kill at model_13000** (`rally_check.py early-weak`; the pair read at 2,048 envs, 120 s).
- **Endpoint:** M1 on 4218532, read once.

The realised family shares are in round 27.

**The early check passed** (model_13000; the parent re-read on 4218501-4218504, the pair read at 2,048 envs, 120 s):

| Measure | Parent (run 4 endpoint) | Run 5 | Kill line |
|---|---|---|---|
| Partner-ball legal | 53.9 % | 52.5 % (low 51.8 %) | 50.9 % |
| Feeder-ball legal (even mix) | 80.1 % | 80.3 % (low 79.8 %) | 78.1 % |
| P(5+) | 8.0 % | 7.6 % | reported |
| Court main | 77.2 % | 76.6 % | -5 points |
| Drill v2 | 83.0 % | 83.3 % | -5 points |
| Lowest move arrival | 96.5 % | 94.4 % | -5 points |
| Court falls per episode | | 3.8 % (Wilson low 2.6 %) | met |

**Weighted families** (parent to run 5):

| Family | Parent | Run 5 |
|---|---|---|
| backhand | 78.3 % | 80.5 % |
| cross_backhand | 54.7 % | 57.4 % |
| fast | 64.3 % | 65.4 % |
| reach_deep | 41.9 % | 45.3 % |
| drop | 72.4 % | 73.8 % |
| low | 74.3 % | 74.9 % |
| **reach_backhand** | 74.7 % | **71.9 %** |

**Down-weighted families (guard):** short 95.2 to 94.0 %, high 93.1 to 92.6 %, reach_forehand 92.5 to 92.9 %. All are within 5 points.

**Plainly:** after a third of the run, the weak families moved a little and feeder-ball legal did not. The run continues to its fixed endpoint.

**Endpoint: model_15000** (the 6 h cap). M1 read on 4218532, read once (`rally-05-target.json`, 24,078 rallies):

| M1 item | Value | Bar | |
|---|---|---|---|
| Partner-ball legal | **55.2 %** (bootstrap low 54.6 %) | >= 50 % | met |
| Feeder-ball legal | **81.9 %** (low 81.4 %) | >= 85 % | **not met** |
| Sides | 64.8 / 64.5 % (gap 0.3) | within 3 points | met |
| Court falls per episode | 3.1 % | <= 4 % | met |

**M1 is not met** (+1.7 points; the panel trigger fires).

| Reported | Value |
|---|---|
| P(5+) | 8.7 % |
| P(3+) | 19.7 % |
| Lowest move arrival | 97.3 % |
| Drill v2 | 88.8 % |
| Court main | 76.9 % |

**Feeder families, run 4 to run 5:**

| Family | Run 4 | Run 5 |
|---|---|---|
| backhand | 77.2 % | 81.7 % |
| reach_backhand | 73.1 % | 76.8 % |
| cross_backhand | 55.8 % | 60.5 % |
| fast | 65.5 % | 69.7 % |
| drop | 75.0 % | 77.3 % |
| reach_deep | 44.8 % | 45.2 % |
| low | 75.3 % | 75.7 % |

The down-weighted families held: short 94.6 %, high 92.1 %, reach_forehand 94.4 %.

**Plainly:** the drilled backhand-side families gained 4-5 points each, and feeder-ball legal rose another 1.7 points. reach_deep did not move.

## Run 6: the stale footwork reward off (D-142)

`scripts/rally_run06.sh`.
- **Task:** Coop-Moves-Weak-NoStance (stance_progress weight 0), from rally-05 model_15000 with its optimizer.
- **Training:** training seed 84, no critic warm-up, 6 h cap.
- **Checks:** early kill at model_15900 on D-141's lines. Endpoint: M1 on 4218632, read once.
- **Benchmark:** 84.1 % +- 1 feeder-ball (the linear trend).
- **Then back to the user.**

**The early check passed** (model_15900; the parent re-read on 4218601-4218604):

| Measure | Parent (run 5 endpoint) | Run 6 | Kill line |
|---|---|---|---|
| Partner-ball legal | 55.4 % | 55.1 % (low 54.5 %) | 52.4 % |
| Feeder-ball legal | 81.3 % | 80.7 % (low 80.2 %) | 79.3 % |
| P(5+) | 8.8 % | 8.7 % | reported |
| Court main | 78.3 % | 78.3 % | -5 points |
| Drill v2 | 85.1 % | 84.1 % | -5 points |
| Lowest move arrival | 96.1 % | 97.5 % | -5 points |
| Court falls per episode | | **4.0 %** (Wilson low 2.8 %) | met |

- **Motion's reported tripwire (3.5 %) is exceeded.** The kill line is not.
- The feeder families moved by -2.6 to +1.3 points; none of the guards fired.
- **Plainly:** with the stale stance reward off, nothing has moved after a third of the run. The run continues to its fixed endpoint.

**Endpoint: model_17900** (the 6 h cap). M1 read on 4218632, read once (`rally-06-target.json`, 25,096 rallies):

| M1 item | Value | Bar | |
|---|---|---|---|
| Partner-ball legal | **52.1 %** (bootstrap low 51.5 %) | >= 50 % | met |
| Feeder-ball legal | **81.3 %** (low 80.7 %) | >= 85 % | **not met** |
| Sides | 62.9 / 62.9 % (gap 0.0) | within 3 points | met |
| Court falls per episode | 3.5 % | <= 4 % | met |

**M1 is not met.** Against the benchmark (84.1 % +- 1), feeder-ball came in 2.8 points low and 0.6 points below run 5.

| Reported | Value |
|---|---|
| P(5+) | 7.7 % |
| P(3+) | 17.2 % |
| Lowest move arrival | 98.7 % |
| Drill v2 | 88.7 % |
| Court main | 77.6 % |

**Next-shot rate by position** (the chance a rally of length k continues): 78.5 % for the feeder return, then 41.7, 52.6, 65.1, 69.0, 67.3, 67.2 %.

**Plainly:** turning off the stale stance reward did not help. Feeder-ball was flat, and partner-ball fell 3 points. **Run 5's model_15000 remains the best rally policy.** Per D-142, the loop goes back to the user.

## Where the loop stands (2026-10-23, after 6 runs and about 37 GPU-hours)

| Run | Change | Partner-ball | Feeder-ball | P(5+) | P(3+) |
|---|---|---|---|---|---|
| base | Stage 5H run 4 (contact read) | 19.2 % | 64.7 % | 0.4 % | |
| 1 | contact hand-off in training | killed early | | | |
| 2 | cooperative credit | 54.3 % | 75.8-77.0 % | 7.9 % | 18.8 % |
| 3 | run 2 continued | 55.9 % | 77.9 % | 8.9 % | 21.2 % |
| 4 | drill-episode fix | 53.9 % | 80.2 % | 8.1 % | 18.6 % |
| 5 | weak-family mix | **55.2 %** | **81.9 %** | **8.7 %** | 19.7 % |
| 6 | stale stance reward off | 52.1 % | 81.3 % | 7.7 % | 17.2 % |

- **M1** (feeder-ball >= 85 %): not met; the best is 81.9 %.
- **The final target** (80 % of rallies reach 5 good shots): about 9 %.

## Run 7: softer shots, keep_alive x2 (D-144)

`scripts/rally_run07.sh`.
- **Task:** Coop-Moves-Weak-KA2 (keep_alive 100 -> 200), from rally-05 model_15000 with its optimizer.
- **Training:** training seed 85, no critic warm-up, 6 h cap.
- **Checks:** early kill at model_15900 (`rally_check.py early-pace`). Endpoint: M1 on 4218742, read once.
- **Success:** partner-ball >= 58.2 % (bootstrap low > 55.2 %).

**Premise read** (`ready-contact-split.json`): partner balls reached 74-76 % of the time when slow or medium (<= 11.0 m/s), and 44 % when fast (mean 11.7 m/s). Readiness at the launch made no difference.

**Killed at the early check** (model_15900; the parent re-read on 4218711-4218714):

| Measure | Parent | Run 7 | Kill line |
|---|---|---|---|
| **Partner-ball legal** | 55.3 % | **47.8 %** (low 47.1 %) | 52.3 % (failed) |
| Feeder-ball legal | 81.6 % | 80.9 % | 79.6 % |
| P(5+) | 8.7 % | 6.0 % | reported |
| Keep-alive-box share | 22.5 % | 28.4 % | engaged |
| Flight | 1.23 s | 1.26 s | |
| **Ball out** | 10.54 m/s | **10.81 m/s** | |
| Court landing x | 4.69 m | 4.91 m | |
| Court legal given contact | 91.5 % | 90.7 % | |
| Drill v2 | 84.0 % | 82.2 % | |
| Lowest move arrival | 94.9 % | 96.9 % | |
| Court falls per episode | | 3.5 % | |

**Plainly:** doubling the keep-alive reward made the robots hit deeper and a little faster, not softer. The box is deep and only loosely tied to flight time. The partner's balls got harder, and partner-ball legal fell 7.5 points. Panel round 30 plans run 8.


## Run 8: a ball-out pace ceiling (D-145)

`scripts/rally_run08.sh`.
- **Task:** Coop-Moves-Weak-Pace: -50 x clamp((|ball out| - 9.5) / 2, 0, 1) at the first legal contact, from rally-05 model_15000 with its optimizer.
- **Training:** training seed 86, no critic warm-up, 6 h cap.
- **Smoke** (`scripts/rally_run08_smoke.sh`): 3 iterations ran; the new term logs a negative reward (-0.0049 against paddle_contact +0.0073); the new diagnostic reads 10.33 m/s mean and 25.6 % above 11 m/s on a 64-env pairs read.
- **Checks:** early kill at model_15900 (`rally_check.py early-ceiling`). Endpoint: M1 on 4218842, read once.
- **Success:** partner-ball >= 58.2 % (bootstrap low > 55.2 %). If it stalls: back to the user.

**Killed at the early check** (model_15900; the parent re-read on 4218811-4218814) by the feeder line:

| Measure | Parent | Run 8 | Kill line |
|---|---|---|---|
| Pair ball out | 10.54 m/s | **9.95 m/s** | <= 10.14 (engaged) |
| Share above 11 m/s | 34.7 % | **14.4 %** | <= 26.7 % (engaged) |
| **Partner-ball legal** | 54.2 % | **64.7 %** (low 64.2 %) | 51.2 % (pass) |
| **Feeder-ball legal** | 81.2 % | **78.4 %** (low 77.8 %) | 79.2 % (**failed**) |
| P(5+) | 8.4 % | **13.9 %** | reported |
| Pair contact | 74.5 % | 78.4 % | 71.5 % |
| Court legal given contact | 91.5 % | 92.9 % | 88.5 % |
| Court contact | 84.6 % | 83.3 % | 81.6 % |
| Court main | 77.4 % | 77.4 % | -5 points |
| Drill v2 | 85.4 % | 84.3 % | -5 points |
| Lowest move arrival | 98.2 % | 98.6 % | -5 points |
| Court falls per episode | 3.2 % | 2.7 % | 4 % low / 7.4 % point |

- The feeder-ball drop is mostly missed contacts on hard feeds: reach_deep contact 56 -> 45 %, fast 76 -> 71 %, reach_backhand 80 -> 75 %, low 82 -> 78 %; drop and reach_short improved.

**Plainly:** slowing the shots worked on its target. The partner's balls got slower, partner-ball legal rose 10.5 points (the biggest move in eight runs), and P(5+) rose by two thirds. But feeder balls (the rally's first ball) lost 2.8 points, past the pre-registered line, so the run was killed. Back to the user (D-145); panel round 31 ranks the options.

## Run 9: the pace ceiling on partner-ball returns only (D-148)

`scripts/rally_run09.sh`.
- **Task:** Coop-Moves-Weak-PaceOwn: run 8's ceiling, gated by `pairs.handed`, so feeder-ball returns are exempt. From rally-05 model_15000 with its optimizer.
- **Training:** training seed 87, no critic warm-up, 6 h cap (the panel's choice; D-147 lifted the user's cap).
- **Checks:** early kill at model_15900 (`rally_check.py early-ceiling-own`: D-145's lines plus no feeder family losing more than 5 points of contact). Endpoint: M1 on 4218942, read once.
- **Success:** partner-ball >= 58.2 % (low > 55.2 %) and feeder-ball >= 81.9 %.

**Killed at the early check** (model_15900; the parent re-read on 4218911-4218914). The mechanism did not engage:

| Measure | Parent | Run 9 | Kill line |
|---|---|---|---|
| Pair ball out | 10.56 m/s | **10.56 m/s** | <= 10.16 (**failed**) |
| Share above 11 m/s | 35.4 % | 36.8 % | <= 27.4 % (**failed**) |
| Partner-ball legal | 55.0 % | 52.3 % (low 51.6 %) | 52.0 % (pass) |
| Feeder-ball legal | 81.5 % | 81.1 % (low 80.6 %) | 79.5 % (pass) |
| P(5+) | 8.8 % | 7.7 % | reported |
| Court legal given contact | 92.7 % | 91.0 % | 89.7 % |
| Court main | 77.7 % | 75.2 % | -5 points |
| Worst feeder-family contact | | -4.0 (reach_deep) | -5 points |
| Court falls per episode | | 2.0 % | 4 % |

- In training, the gated penalty averaged -0.009 per episode, against -0.046 for run 8's ungated one (paddle_contact 0.138 in both). Partner-ball returns are a small share of the balls in training, where most feeds are feeder balls and drill episodes, and the policy cannot see which kind of ball it is playing.

**Plainly:** limiting the penalty to partner balls made it about five times weaker, too weak to change anything. Shots stayed as fast as before, and partner-ball legal fell a little. Panel round 32 plans run 10.

## Run 10: run 8's pace ceiling at half the weight (D-149)

`scripts/rally_run10.sh`.
- **Task:** Coop-Moves-Weak-Pace25: -25 x clamp((|ball out| - 9.5) / 2, 0, 1) at the first legal contact, on all returns. From rally-05 model_15000 with its optimizer.
- **Training:** training seed 88, 6,400 iterations (about 13 h).
- **Checks:** early kill at model_16900 (`early-ceiling-own`). Endpoint: model_21400, M1 read on 4219242, read once.
- **Smoke:** the term was 0.22 of paddle_contact (run 9: 0.05; run 8 in training: 0.33).
- **Success:** partner-ball >= 58.2 % (low > 55.2 %) and feeder-ball >= 81.9 %.

**Early check passed** (model_16900; the parent re-read on 4219211-4219214):

| Measure | Parent | Run 10 | Kill line |
|---|---|---|---|
| Pair ball out | 10.55 m/s | 10.23 m/s | <= 10.15 (not met) |
| Share above 11 m/s | 34.8 % | **22.1 %** | <= 26.8 % (engaged) |
| **Partner-ball legal** | 55.5 % | **61.7 %** (low 61.1 %) | 52.5 % |
| **Feeder-ball legal** | 81.1 % | **80.7 %** (low 80.2 %) | 79.1 % |
| P(5+) | 9.0 % | **12.1 %** | reported |
| Court legal given contact | 91.5 % | 92.4 % | 88.5 % |
| Court contact | 84.2 % | 84.5 % | 81.2 % |
| Pair contact | 75.2 % | 77.6 % | 72.2 % |
| Court main | 77.0 % | 78.1 % | -5 points |
| Drill v2 | 85.5 % | 84.4 % | -5 points |
| Lowest move arrival | 97.4 % | 98.0 % | -5 points |
| Worst feeder-family contact | | -4.2 (reach_deep) | -5 points |
| Court falls per episode | | 2.9 % | 4 % |

**Plainly:** half the penalty kept most of run 8's gain (partner-ball legal +6.2 points, P(5+) +3.1) and almost none of its cost (feeder-ball legal -0.4 points). Training continues to the fixed endpoint, model_21400.

**Endpoint** (model_21399, the last checkpoint; the M1 and target read on 4219242, read once):

| Measure | Run 5 (best before) | Run 10 | Bar |
|---|---|---|---|
| **Partner-ball legal** | 55.2 % | **63.1 %** (low 62.6 %) | success >= 58.2 % (met); M1 >= 50 % (met) |
| **Feeder-ball legal** | 81.9 % | **80.1 %** (low 79.5 %) | success >= 81.9 % (**missed**); M1 >= 85 % (missed) |
| P(3+) | 19.7 % | **24.9 %** | M2 >= 50 % |
| **P(5+)** | 8.7 % | **13.3 %** [12.8, 13.8] | target >= 80 % |
| Sides A / B | | 68.3 / 68.7 % | within 3 points (met) |
| Court falls per episode | 3.1 % | 3.5 % | <= 4 % (met) |
| Crossing hand-off P(5+) | | 7.4 % | reported |

- Ball out 10.54 -> 10.14 m/s; share above 11 m/s 19.1 %; landing x 4.25 -> 3.99 m.
- **Feeder-ball misses by family:** reach_deep 761 (legal 45.2 -> 40.7 %), cross_backhand 516 (59.1 %), fast 510 (69.7 -> 63.5 %), low 338, reach_backhand 317. The first three are 38 % of all 4,655 feeder misses. Reaching 85 % would need about 1,150 fewer misses.
- Clean eval battery (h5f): 6/8 Stage 5H gate items (falls <= 1 % and style not met; reported only).

**Plainly:** run 10 has the longest rallies so far: one rally in eight reaches 5 shots, up from one in eleven. The partner balls are now well past their bar. The feeder ball slipped 1.8 points, missing the pre-registered success line, and is further from M1's 85 %. Most feeder misses are on deep reach, cross-court backhand and fast feeds. Panel round 33 picks run 11, aimed at feeder balls (D-149).

## Run 11: a bonus on returns of the weakest feeder balls (D-150)

`scripts/rally_run11.sh`.
- **Task:** Coop-Moves-Weak-Pace25-FeedBonus: run 10's task plus +50 on a legal return of a feeder ball of reach_deep, cross_backhand, fast, reach_backhand or backhand. From rally-10 model_21399 with its optimizer.
- **Training:** training seed 89, 6,400 iterations.
- **Checks:** early kill at model_23300 (`early-feedbonus`). Endpoint: M1 on 4219342, read once.
- **Smoke:** the term was 0.26 of paddle_contact over 40 iterations.
- **Success:** feeder-ball >= 81.9 % (low > 80.1 %) and partner-ball >= 58.2 %.

**Killed at the early check** (model_23300; the parent, rally-10 model_21399, re-read on 4219311-4219314). The bonus did not engage:

| Measure | Parent | Run 11 | Kill line |
|---|---|---|---|
| **Bonus families' feeder-ball legal** | 64.6 % | **64.3 %** | must be up (**failed**) |
| Feeder-ball legal | 80.4 % | 80.1 % (low 79.5 %) | 78.4 % |
| Partner-ball legal | 63.2 % | 64.8 % (low 64.2 %) | 60.2 % |
| P(5+) | 13.4 % | 14.8 % | reported |
| Worst feeder-family contact | | -2.5 (reach_short) | -5 points |
| Court legal given contact | 94.1 % | 92.8 % | 91.1 % |
| Court main | 78.1 % | 75.6 % | -5 points |
| Drill v2 | 85.2 % | 86.1 % | -5 points |
| Lowest move arrival | 99.6 % | 99.1 % | -5 points |
| Court falls per episode | | 3.1 % | 4 % |

**Plainly:** a +50 bonus on returning the five weakest feeder balls did not move them (-0.3 points). This is the second run in a row that ends with feeder-ball legal at or below 81.9 %, so D-149 applies: the controller option or a stop vote. Panel round 34 decides.

## Round 34's controller check (e1, D-151)

`scripts/diag/feeder_speed_envelope.py` on rally-10 model_21399, in the M1 pair read's settings, seed 4219400, `results/feeder-speed-envelope.json`. 8,137 finished feeder balls.

**The pre-registered rule fired (controller limit):** reach_deep and fast feeder-ball misses (464) peak at 1.70 m/s (90th percentile) and still end 0.64 m short (median closest paddle-to-ball distance; the lines were 1.4 m/s and 0.20 m).

**By the direction the robot had to move** (pelvis at the start to the ball at the closest approach):

| Direction | Feeder balls | Legal | Contact | Misses' median closest distance |
|---|---|---|---|---|
| Forward | 3,364 | **91.8 %** | 95.0 % | 0.21 m |
| Right | 2,863 | **87.4 %** | 90.7 % | 0.49 m |
| Back | 608 | **51.8 %** | 65.5 % | 0.37 m |
| Left | 1,302 | **36.2 %** | 46.2 % | 0.84 m |

- **Weakest families:**
  - reach_deep: 38 % legal; its misses go back 54 % and left 35 % of the time.
  - cross_backhand: 61 %; left 83 %.
  - reach_backhand: 76 %; left 90 %.
  - Their misses end 1.8-2.0 m short even at 2.4-2.5 m/s peaks.
- Peak pelvis speed reaches 2.66 m/s (99th percentile), so the planner's 1.5 m/s cap understates speed. The limit is the direction: the robot moves left and back badly. Motion's reading (Stage 5C: the latent controller barely steps left or back) is confirmed.

**Plainly:** the robot runs fast enough, but it cannot get to balls on its left (the backhand side) or behind it. Only 36 % of the feeder balls that need a move to the left come back. By the pre-registered rule, run 12 gives the policy direct control of the legs on top of the frozen controller.

## Run 12: leg-joint residuals on the frozen controller (D-152)

`scripts/rally_run12.sh`.
- **Task:** Coop-Moves-Weak-Pace25-LegRes: run 10's task plus 12 leg-joint residuals (+-0.1 rad, as the right wrist) on the latent controller's output.
- **Parent:** rally-10 model_21399, widened by `scripts/leg_residual_init.py` (12 zero output rows, so it starts as the parent).
- **Training:** training seed 90, 6,400 iterations.
- **Smoke:** 40 training iterations ran; the widened checkpoint loads in the evaluation tasks (`PICKLEBOT_LEG_R=0.1`). Run-to-run GPU noise in a 64-env read is as large as the parent-versus-init difference.
- **Checks:** early kill at model_23300 (`early-legres`: reach_deep + fast feeder contact must be up, plus D-145's and D-148's lines). Endpoint: M1 on 4219442, read once.
- **Success:** feeder-ball >= 81.9 % (low > 80.1 %) and partner-ball >= 58.2 %.

**Killed at the early check** (model_23300; the parent re-read on 4219411-4219414). The leg residual did not engage:

| Measure | Parent | Run 12 | Kill line |
|---|---|---|---|
| **reach_deep + fast feeder contact** | 63.5 % | **63.2 %** | must be up (**failed**) |
| Feeder-ball legal | 80.4 % | 79.9 % (low 79.3 %) | 78.4 % |
| Partner-ball legal | 63.5 % | 64.2 % | 60.5 % |
| P(5+) | 13.9 % | 14.9 % | reported |
| Worst feeder-family contact | | -3.4 (reach_deep) | -5 points |
| Court main | 77.1 % | 78.4 % | -5 points |
| Lowest move arrival | 99.5 % | 96.8 % | -5 points |
| Court falls per episode | | 3.1 % | 4 % |

- **The leg rows are learning slowly:** the mean output-row weight norm went 0.02 (model_21500) -> 0.07 -> 0.11 (model_23300), against 0.28 for the base rows. The leg std held at 0.72.
- With tanh and a +-0.1 rad range, the residual was still a small nudge at the early check.

**Plainly:** the policy has only just started to use its new leg control, and it has not yet changed how the robot gets to deep or fast balls. The kill line was pre-registered, so the run stops here. Panel round 34's next options: fine-tune the controller's decoder (e2 proper), a privileged teacher and distillation (e4), or a stop vote. Panel round 35 decides.

## Run 13: the leg residual at +-0.3 rad (D-153)

`scripts/rally_run13.sh`.
- **Task:** Coop-Moves-Weak-Pace25-LegRes30: run 12's with `leg_r` 0.3. Parent: the same widened rally-10 model_21399.
- **Training:** training seed 91, 6,400 iterations.
- **Smoke:** 40 iterations. fell_over 0.182, against 0.097 for run 12's smoke (1.87x, under the pre-registered 2x line, so the std is kept). The eval path loads.
- **Checks:** early kill at model_23300 (`early-legres30`: run 12's lines plus left + back feeder contact up, from the direction split). Endpoint: M1 on 4219542, read once.
- **Success:** feeder-ball >= 81.9 % (low > 80.1 %) and partner-ball >= 58.2 %.

**Killed at the early check** (model_23300; the parent re-read on 4219511-4219515). It made things worse on almost every line:

| Measure | Parent | Run 13 | Kill line |
|---|---|---|---|
| **Left + back feeder contact** | 52.2 % | **50.4 %** | must be up (**failed**) |
| Left / back feeder legal | 36.6 / 52.9 % | 30.5 / 47.8 % | reported |
| reach_deep + fast feeder contact | 64.0 % | 61.8 % | must be up (**failed**) |
| Feeder-ball legal | 80.4 % | **76.9 %** | 78.4 % (**failed**) |
| Partner-ball legal | 63.1 % | **58.0 %** | 60.1 % (**failed**) |
| P(5+) | 13.3 % | 9.3 % | reported |
| Worst feeder-family contact | | **-11.1** (cross_backhand) | -5 points (**failed**) |
| Lowest move arrival | 99.5 % | **82.6 %** | -5 points (**failed**) |
| Drill v2 | 84.7 % | 80.4 % | -5 points |
| Court falls per episode | | **4.5 %** (low 3.3 %) | point 7.4 %, low 4 % |

**Plainly:** giving the policy a wide range on the leg joints disturbed the controller's walking instead of improving footwork: move arrival fell 17 points and falls rose. Under D-153 the leg-residual route is closed. Panel round 36 chooses between a decoder fine-tune (e2 proper) and a stop.

## Run 14: the residual's latent range doubled (D-154)

`scripts/rally_run14.sh`.
- **Task:** Coop-Moves-Weak-Pace25-LamR2: run 10's with `lam_r` 2 (no leg residual).
- **Parent:** rally-10 model_21399 with latent output rows and std halved (`scripts/lam_r_init.py`).
- **Training:** training seed 92, 6,400 iterations.
- **Smoke:** 40 iterations. fell_over 0.106 (run 11's smoke from the same parent: 0.102); paddle_contact and legal_return are as the parent's; the eval path loads with `PICKLEBOT_LAM_R=2`.
- **Checks:** early kill at model_23300 (`early-lamr2`: left + back feeder contact up by >= 2 points, plus run 12's lines). Endpoint: M1 on 4219642, read once.
- **Success:** feeder-ball >= 81.9 % (low > 80.1 %) and partner-ball >= 58.2 %.

**Early check passed** (model_23300; the parent re-read on 4219611-4219615):

| Measure | Parent | Run 14 | Kill line |
|---|---|---|---|
| **Left + back feeder contact** | 52.9 % | **55.0 %** | up >= 2 points (+2.1, pass) |
| **Left feeder legal** | 36.2 % | **40.8 %** | reported |
| Back feeder legal | 49.6 % | 49.0 % | reported |
| **reach_deep + fast feeder contact** | 62.1 % | **65.7 %** | up (pass) |
| **Partner-ball legal** | 63.4 % | **66.9 %** (low 66.4 %) | 60.4 % |
| **Feeder-ball legal** | 80.5 % | **81.3 %** (low 80.7 %) | 78.5 % |
| P(5+) | 13.4 % | **15.0 %** | reported |
| Pair contact | 78.6 % | 80.6 % | 75.6 % |
| Court main | 78.8 % | 78.5 % | -5 points |
| Drill v2 | 84.5 % | 85.8 % | -5 points |
| Lowest move arrival | 99.5 % | 98.7 % | -5 points |
| Worst feeder-family contact | | -1.4 (cross_forehand) | -5 points |
| Court falls per episode | | 3.3 % | 4 % |

**Plainly:** the wider latent range is the first footwork change in five runs that helped without breaking anything. Balls on the left are returned 4.6 points more often, partner balls 3.5 points more, and feeder balls 0.8 points more. Walking and falls held. Training continues to the endpoint.

**Endpoint** (model_27798, the last checkpoint; the M1 and target read on 4219642, read once): **success line met**, and the new best policy.

| Measure | Run 10 (old best) | Run 14 | Bar |
|---|---|---|---|
| **Partner-ball legal** | 63.1 % | **70.5 %** (low 70.1 %) | success >= 58.2 % (met); M1 >= 50 % (met) |
| **Feeder-ball legal** | 80.1 % | **81.9 %** (low 81.3 %) | success >= 81.9 % with low > 80.1 % (**met**); M1 >= 85 % (not met) |
| P(3+) | 24.9 % | **31.6 %** | M2 >= 50 % |
| **P(5+)** | 13.3 % | **18.7 %** [18.2, 19.3] | target >= 80 % |
| Mean rally length | 2.06 | 2.63 | |
| Sides A / B | 68.3 / 68.7 % | 73.7 / 73.5 % | within 3 points (met) |
| Court falls per episode | 3.5 % | 3.4 % | <= 4 % (met) |
| Crossing hand-off P(5+) | 7.4 % | 10.5 % | reported |
| Style (h5f) | 4.26 | 4.24 | reported |

- **Feeder-ball legal by the direction to move** (direction split, 4219644, against D-151's read of run 10): forward 91.8 -> 93.6 %, right 87.4 -> 88.1 %, **left 36.2 -> 43.7 %**, back 51.8 -> 52.7 %.
- **Feeder families, run 10 -> run 14:** reach_deep 40.7 -> 43.2 %, cross_backhand 59.1 -> 63.8 %, fast 63.5 -> 68.9 %, drop 78.6 -> 83.8 %. reach_backhand (76.3 -> 75.2 %) and backhand (78.9 -> 78.3 %) are flat.
- M1 needs about 700 fewer feeder misses (18.1 % -> 15 %). reach_deep (632), cross_backhand (374) and fast (369) still hold the most.

**Plainly:** widening the policy's control over the motion controller worked. It is the best robot so far: partner balls come back 70 % of the time, one rally in five reaches 5 shots, and balls on the left come back 44 % of the time instead of 36 %. The feeder ball is at 82 % against M1's 85 %. Panel round 37 picks run 15.

## Rally run 15 - lam_r 3 (D-155, panel round 37, 4/5)

- **Change:** the residual's latent range 2 -> 3 prior sigma on run 14's task (`...-Weak-Pace25-LamR3-G1`), the one change.
- **Parent:** rally-14 model_27798 with the latent rows and std scaled by 2/3, with its optimizer; training seed 93; 6,400 iterations; 12,288 envs. Script `scripts/rally_run15.sh`.
- **Smoke:** mean fell_over 0.099 (run 14 smoke 0.106; stop line 0.159); paddle_contact 0.0445 (0.0438).
- **Early kill at model_29700** on run 14's lines (left + back feeder contact up >= 2 points against a parent re-read).
- **Success (pre-registered):** feeder-ball legal >= 83.9 % with low > 81.9 %, partner-ball legal >= 68.5 %, sides within 3 points, falls <= 4 %.

**Early check** (model_29700 against a re-read of run 14's model_27798 on 4219711-4219715): **KILLED** on its engagement line. Left + back feeder-ball contact went **down** 58.4 -> 54.9 % (-3.5; the line was +2.0).

| Measure | Parent (run 14, re-read) | Run 15 model_29700 | Line |
|---|---|---|---|
| **Left + back feeder contact** | 58.4 % | **54.9 %** | up >= 2 points (**failed**) |
| Left feeder legal | 45.5 % | **39.6 %** | reported |
| Back feeder legal | 52.8 % | 49.4 % | reported |
| Forward / right feeder legal | 93.1 / 89.2 % | 93.3 / 87.6 % | reported |
| reach_deep + fast feeder contact | 65.2 % | 64.5 % | up (failed) |
| Partner-ball legal | 69.7 % | 71.8 % | >= 66.7 % (held) |
| Feeder-ball legal | 81.4 % | 82.1 % | >= 79.4 % (held) |
| P(5+) | 17.8 % | 19.2 % | reported |
| Court falls per episode | | 2.6 % | <= 4 % (held) |
| Move arrival (lowest) | 99.5 % | 99.5 % | within -5 (held) |

- Walking, falls and the other lines held. The policy got slightly better on partner balls and P(5+), but worse at the balls that need a step left or back, which is what the wider range was for.
- **Dose response:** lam_r 1 -> 2 raised left feeder legal 36 -> 44 %; 2 -> 3 lowered it 45.5 -> 39.6 %. The useful range is about 2 sigma.

**Plainly:** widening the control range a second time made the robot worse at stepping left and back. Under D-155, lam_r stays at 2; panel round 38 chooses among run 14 continued, the e4 teacher, and a stop.

## Rally run 16 - the e4 privileged-ball teacher (D-156, panel round 38, 3/5)

- **Change:** run 14's task (lam_r 2) plus a trailing 5-dimensional actor input on every live feed: the true-state contact point relative to the pelvis, its height, the time to contact, and an on flag (`...-Weak-Pace25-LamR2-Teacher-G1`).
- **Parent:** rally-14 model_27798 with five zero input columns (exactly the parent at the start), with its optimizer; training seed 94; 6,400 iterations; 12,288 envs. Script `scripts/rally_run16.sh`.
- **Smoke:** fell_over 0.107 (run 14 smoke 0.106); the teacher input is live on 56 % of env-steps and counts down correctly.
- **Headroom read (reported):** run 14 with a clean planner spot turned on: feeder-ball legal 82.0 -> 75.9 %, partner 70.5 -> 68.1 %, P(5+) 18.6 -> 15.8 % (4219801). The policy walks to that spot; it is not a test of the teacher's input.
- **Early kill at model_29700** on run 14's lines (left + back feeder contact up >= 2 points against a parent re-read).
- **Teacher gate (pre-registered):** feeder-ball legal >= 85 % (low >= 84 %), partner-ball legal >= 68.5 %, sides within 3 points, falls <= 4 %. Pass: build the DAgger student; M1 is claimed only from the student.
- **Attempt 1 lost (2026-10-26):** launched about 13:15. The parent re-reads finished, then training stopped about 4.5 minutes in (model_27820, 22 iterations) with no error and no exit file. The whole WSL session ended (WSL was freshly started at 18:48, and Windows rebooted at 17:19). Logs are kept as `artifacts/train/rally-16-teacher-attempt1*.log`. Relaunched unchanged at 18:51 (same commit 86e1191, same seeds; the parent re-reads repeat) from a detached Windows `wsl` process, so the run no longer depends on the Claude app's shell.

**Early check** (attempt 2; model_29700 against a re-read of run 14's model_27798 on 4219811-4219815): **KILLED** on its engagement line. Left + back feeder-ball contact went **down** 58.0 -> 56.3 % (-1.8; the line was +2.0).

| Measure | Parent (run 14, re-read) | Run 16 model_29700 | Line |
|---|---|---|---|
| **Left + back feeder contact** | 58.0 % | **56.3 %** | up >= 2 points (**failed**) |
| Left / back feeder legal | 40.8 / 56.4 % | 41.0 / 52.5 % | reported |
| reach_deep + fast feeder contact | 66.9 % | 65.2 % | up (failed) |
| Partner-ball legal | 70.1 % | 71.3 % | >= 67.1 % (held) |
| Feeder-ball legal | 81.9 % | 81.4 % | >= 79.9 % (held) |
| P(5+) / P(3+) | 18.4 / 31.8 % | 19.7 / 32.3 % | reported |
| Court falls per episode | | 3.4 % | <= 4 % (held) |
| Move arrival (lowest) | 98.3 % | 98.3 % | within -5 (held) |

- **The test was not fair.** The policy hardly used the new input. The first-layer weight on the five teacher columns grew from 0 to only 0.03-0.06 (column norm) by model_29700, against a median of 3.65 for the original input columns: about 1/60 of an ordinary input. The zero-initialized columns, with the learning rate held at 1e-5, learned far too slowly in 1,900 iterations. This is the same pattern as run 12's leg rows.
- So run 16 does not show whether the true contact point and time help. It shows that a zero-start privileged input, with run 14's optimizer settings, is not picked up within 30 % of a run.

**Plainly:** the teacher did not learn to look at its new information, so it played like run 14. Panel round 39 decides what to do.

## Rally run 17 - the e4 teacher with its input x30 (D-157, panel round 39, 5/5 for a fair-start teacher; form by the tie rule)

- **Change:** run 16's teacher input multiplied by 30 (the observation term's scale), the one change against run 16. Under Adam, that is a 30x larger step for those five columns. Run 16's zero-start columns moved only at random-walk size at the 1e-5 learning-rate floor.
- **Parent:** rally-16-teacher-init model_27798 (= run 14 exactly), with its optimizer; training seed 95; 6,400 iterations; 12,288 envs. Script `scripts/rally_run17.sh`, launched from a detached Windows process.
- **Smoke:** fell_over 0.080 (run 14 smoke 0.106); the input is live at gain 30.
- **Early kill at model_29700:** run 14's lines (left + back feeder contact up >= 2 points against a parent re-read), plus the used line: the same checkpoint and seed with the input zeroed must lose >= 3 points of left + back contact.
- **Teacher gate:** D-156's, unchanged. Pre-registered STOP votes (experiment design, architecture, coach) if any line fails.

**Early check** (model_29700 against a re-read of run 14's model_27798 on 4219911-4219915): **KILLED** on both its engagement line and its used line.

| Measure | Parent (run 14, re-read) | Run 17 model_29700 | Line |
|---|---|---|---|
| **Left + back feeder contact** | 55.7 % | **53.0 %** | up >= 2 points (**failed**) |
| **Used line:** the same read with the input zeroed | | 53.3 % (input on: 53.0 %) | zeroed loses >= 3 points (**failed**: -0.3) |
| Left / back feeder legal | 42.3 / 48.7 % | 37.9 / 50.2 % | reported |
| reach_deep + fast feeder contact | 65.1 % | 63.2 % | up (failed) |
| Partner-ball legal | 70.3 % | 69.2 % | >= 67.3 % (held) |
| Feeder-ball legal | 81.6 % | 82.2 % | >= 79.6 % (held) |
| P(5+) / P(3+) | 18.7 / 31.9 % | 18.4 / 31.2 % | reported |
| Court falls per episode | | 3.1 % | <= 4 % (held) |
| Move arrival (lowest) | 98.4 % | 99.5 % | within -5 (held) |

- **Teacher input use.** At model_29700 the raw column norms are 0.03-0.04. With the x30 gain and the normalizer std on those inputs (1.7-3.3; it adapted faster than expected), the effective weight is 0.26-0.75, against a median of 3.65 for the original columns. Zeroing the input changes nothing (-0.3), so the policy still does not use the true contact point and time.
- **Two teacher runs, the same outcome.** With the information available, zero-start and x30-gain columns are not picked up in 1,900 iterations at the 1e-5 learning-rate floor. The policy plays as run 14 does (partner, feeder and P(5+) within noise).

**Plainly:** even with the ball information made 30 times louder, the robot did not start using it, so the teacher played like run 14. Pre-registered: experiment design, architecture and coach vote STOP. Panel round 40 decides.


## KL check after the stop (D-158): why the learning rate sat at its floor (2026-10-27)

The user asked why the learning rate was so low. Three 30-iteration probes from rally run 14 model_27798 on its own task (12,288 envs, its optimizer) recorded each action output's share of the KL (`picklebot_mj/rl/kl_probe.py`, `scripts/diag/kl_probe.sh`, `scripts/diag/kl_probe_summary.py`; results `results/kl-probe-*.jsonl` and `kl-probe-summary.json`; seeds 4219950-4219952, diagnostic only).

| Probe | Learning rate | KL per update (median) | Output 30's share | KL without output 30 |
|---|---|---|---|---|
| a: native schedule | 1e-5 (floor) | 0.0198 | 95.3 % | 0.0011 |
| b: meant 1e-4 (**invalid**, ran at 1e-5: the resume loads the optimizer's rate after the probe set it) | 1e-5 | 0.0170 | 95.0 % | 0.0010 |
| b2: held at 1e-4 | 1e-4 | 0.0508 | 98.6 % | 0.0234 |

- **One output carries the KL.** Output 30 (latent dim 30) has std 0.0020-0.0023; the other 34 sit at 0.15-0.20. Its mean shift counts (1/0.002)^2 = 250,000 times per unit, so it supplies 95-99 % of the KL. rsl_rl sums the KL over outputs and cuts the rate above 2 x desired_kl (0.02).
- **Without it the schedule would have raised the rate.** At 1e-5 the other outputs give 0.0011, under the raise line (0.005). At 1e-4 they give 0.023, at the cut line. The rate would have settled near 1e-4, about 10 times higher than every run since rally run 2.
- **When it started.** Output 30's std fell 0.218 -> 0.0035 during rally run 2 (iterations 3,400-5,600). All stds shrank in that run; output 30 shrank fastest. The rate first hit the floor at iteration 5,200 and stayed there through runs 3-17 (all checkpoints traced). Output 30's mean is ordinary (tanh 0.07-0.35 at the average input), so it is not saturated. Why its noise collapsed is not known yet.
- **What this does not show.** A higher rate is not proof the plateau would move. That needs a run.

**Plainly:** one of the 35 outputs lost almost all its exploration noise in rally run 2. From then on, every tiny change to it looked huge to the schedule, which held the learning rate at its minimum for the whole network for 15 runs. The other 34 outputs would have allowed a rate about 10 times higher.

Literature reviews written for the user: `docs/research/lit-2026-10-27-continued-training.md`, `docs/research/lit-2026-10-27-racket-sports.md`.


## Learning-rate sweep after the KL check (2026-10-28)

The user approved a restart of the optimizer side only ("lets do that then"). Parent: rally run 14 model_27798 with Adam's state emptied and output 30's std raised 0.0022 -> 0.1 (`scripts/fresh_init.py`; the other 34 untouched). Trainer: `picklebot_mj/rl/sched_ppo.py` (ScheduledPPO: std floor 0.1, linear warm-up over 50 updates to a constant peak, KL guard 0.05, no adaptive rule). Run 14's task and reward unchanged. Script `scripts/lr_sweep.sh`; smoke seed 4219953 (fell_over 0.108 vs run 14 smoke 0.106, ok); arms 400 iterations at 12,288 envs, seeds 4219954-4219956; reads on 4219960-4219964 (diagnostic only); `rally_check.py early-lamr2` per arm (`results/lrsweep-<arm>-check.txt`).

Pre-registered choice: among arms holding the guard lines (partner legal >= max(50, parent - 3), feeder legal >= parent - 2, court falls Wilson low <= 4 % and point <= 7.4 %), the largest left + back feeder-contact gain; a full run only if that gain is >= 2 points.

| | Parent (run 14) | 3e-5 | 1e-4 | 3e-4 |
|---|---|---|---|---|
| Left + back feeder contact | 56.4 % | 54.8 % (-1.5) | 53.2 % (-3.2) | 47.3 % (-9.1) |
| Left legal / back legal | 43.4 / 49.7 % | 42.3 / 51.9 % | 38.8 / 46.9 % | 32.6 / 38.7 % |
| Partner-ball legal | 70.4 % | 73.0 % | 75.1 % | 69.7 % |
| Feeder-ball legal (guard >= 79.8 %) | 81.8 % | 81.7 % | 80.6 % | 76.7 % (fails) |
| P(5+) | 18.5 % | 20.4 % | 22.3 % | 17.3 % |
| Court falls per episode (point / low) | | 4.5 / 3.3 % | 5.2 / 3.8 % | 4.0 / 2.8 % |
| Worst feeder-family contact change | | -3.4 (reach_deep) | -3.3 (reach_backhand) | -14.3 (cross_backhand) |
| KL per update (late) / steps taken of 20 | | 0.005 / 20 | 0.012 / 20 | 0.36-0.70 / 1 |
| Output 30's KL share (late) | 95-99 % before | 6-9 % | 6-10 % | 18-44 % |

- **The KL fix worked.** At 3e-5 and 1e-4 every update took all 20 mini-batch steps and no output dominated the KL. 1e-4 sits where the KL check predicted the native schedule would have settled.
- **3e-4 is unstable.** From about update 100 the KL is 0.4-0.7 after one step, so the guard stops every update after its first mini-batch; it lost ground on every measure.
- **More learning moves the policy toward the pair rally, away from left and back.** Partner legal and P(5+) rise with the rate (to 75.1 % and 22.3 % at 1e-4), while left + back contact falls with it. The rally reward already favours the common balls; a higher rate follows it faster.
- **Choice rule:** no arm gains left + back (all negative). By the pre-registered rule there is no full run; the result goes to the user.

**Plainly:** fixing the learning rate made the robot learn again, and at 1e-4 it got better at the partner rally in 400 iterations (P(5+) 18.5 -> 22.3 %). But it did not get better at the left and back balls, which is what we needed it to fix; it got slightly worse. These are 400-iteration diagnostic reads, not endpoints.


## Rally run 18b: the fixed optimizer at 1e-4 (2026-10-28) - killed at the early check

Run 18 (scripts/rally_run18.sh) was stopped during its parent read: the audit found that the first ScheduledPPO's std floor froze any output that reached it (rsl_rl's forward clamp passes zero gradient at the floor). Run 18b (scripts/rally_run18b.sh) is run 18's pre-registered design with the floor clamped after each optimizer step (commit decb45e): run 14's task, parent lrsweep-init/model_27798 (fresh Adam, output 30's std raised to 0.1), 1e-4 constant after a 50-update warm-up, cooldown planned over updates 3,200-4,000, KL guard 0.05; smoke seed 4219991, training seed 4219992, reads 4219967-4219971. Smoke: falls 0.117 (line 0.159), every std output had a gradient. Training: KL 0.011-0.014 per update, all 20 mini-batch steps every update, at most 2 outputs at the floor (they rise off it again).

Early check at model_29000 (rally_check.py early-sched), parent = run 14 model_27798 re-read on the same seeds:

| | Parent | model_29000 | Line |
|---|---|---|---|
| P(5+) (engagement) | 18.44 % | **25.84 %** [25.16, 26.53] (+7.4) | >= +2.0 (held) |
| Partner-ball legal | 69.98 % | **77.36 %** (low 76.91) | >= 66.98 % (held) |
| Feeder-ball legal | 82.26 % | 81.13 % (low 80.47) | >= 80.26 % (held) |
| P(4+) | 23.6 % | 30.4 % | reported |
| Court legal given contact / court contact / pair contact | 94.6 / 83.1 / 82.0 % | 93.0 / 82.0 / 86.4 % | within 3 points (held) |
| Court main / drill v2 / lowest move arrival | 78.6 / 87.3 / 98.2 % | 76.3 / 87.2 / 99.1 % | within 5 points (held) |
| Court falls per episode | | 2.99 % (low 2.0) | low <= 4 %, point <= 7.4 % (held) |
| Left + back feeder-ball contact | 58.8 % | 57.2 % (-1.6) | >= -5 (held) |
| Worst feeder-family contact change | | **-5.3 (cross_forehand)** | >= -5 (**failed**) |

- **Killed on one line.** cross_forehand feeder-ball contact fell 5.3 points (1,089 -> 997 feeds; SE of the difference 1.4 points; its legal return -4.6). That is about 3.8 standard errors, so not read noise: the run traded some cross-forehand balls for the partner rally. Every other line held, most by a wide margin. The kill stands as pre-registered; the endpoint battery was skipped. Checkpoints model_29000-29200 are kept.
- **The optimizer fix works.** In 1,200 iterations at 1e-4 the rally moved more than in rally runs 3-17 together: P(5+) +7.4 points, partner-ball legal +7.4 points, falls lower (3.0 %). Feeder-ball legal is flat (-1.1), so M1 (feeder 85 %) is no nearer.

**Plainly:** with the learning rate fixed, the robot got much better at the two-robot rally in a third of a run (25.8 % of rallies reach 5 shots, up from 18.4 %). It was stopped by the rule that no single ball type may get more than 5 points worse: cross-court forehands got 5.3 points worse. The panel decides what comes next.


## Feed-anchor check (audit F1, 2026-10-28; diagnostic)

Start-anchored feeds aim from ROBOT_START y = 0.35 while the robot recovers to y = 0. Rally run 14 model_27798 read at the task's anchor (y 0.35) and at y 0.0 (`--anchor-y 0.0`), same seeds (pairs 4220000, direction split 4220001), old bookkeeping; `scripts/diag/anchor_check.sh`, results `results/anchor-r14-y{default,0.0}-{pairs,dir}.json`.

| | y 0.35 (as trained and read so far) | y 0.0 |
|---|---|---|
| Partner-ball legal | 69.9 % | 67.8 % |
| Feeder-ball legal | 82.2 % | 82.7 % |
| P(5+) (open rallies counted) | 17.9 % (18.8 %) | 16.2 % (17.0 %) |
| Left: feeds, contact, legal | 1,160, 52.4 %, 42.8 % | 946, 56.0 %, 45.8 % |
| Back: feeds, contact, legal | 532, 66.0 %, 49.4 % | 606, 68.8 %, 53.0 % |
| Right: feeds, legal | 2,589, 87.6 % | 3,729, 86.3 % |
| Feeder families that move most | | backhand 80.7 -> 87.1, reach_backhand 78.3 -> 82.2, deep 87.3 -> 90.7; wide_forehand 88.9 -> 86.2, reach_forehand 92.5 -> 90.5 |

- **The bias is real but small for the totals.** Aiming from the true recovery spot moves about 200 feeds from "needs a left move" to "needs a right move" and lifts the backhand families, but feeder-ball legal changes by only +0.5 points.
- **The left weakness is mostly genuine.** Balls that still need a left move are returned 45.8 % of the time (42.8 % before); fast and low balls do not change.
- **The partner rally reads lower at y 0.0** (P(5+) -1.7), as expected for a policy trained on the 0.35 anchor; a read-time switch would not be fair to it.

**Plainly:** the aiming bug made left balls look a little worse than they are, but fixing it is not the missing piece: balls to the robot's left are still returned less than half the time.


## Rally run 19: run 18b continued from model_29000 (D-160, 2026-10-28) - killed at the early check

scripts/rally_run19.sh: run 14's task, ScheduledPPO at 1e-4 with model_29000's Adam state, no warm-up, training seed 96, smoke seed 97 (falls 0.085, every output with a gradient). Parent model_29000 re-read on 4220002-4220006 (the interface guard verified lam_r 2 against 18b's params): partner 77.35 %, feeder 80.87 %, P(5+) 25.8 % (open rallies counted 27.2 %), reproducing 18b's own read. Training: KL 0.014 per update, all 20 steps every update, at most 2 outputs at the floor.

Early check at model_30200 (rally_check.py early-r19):

| | model_29000 | model_30200 | Line |
|---|---|---|---|
| P(5+), open rallies counted | 27.20 % | **33.19 %** [32.28, 34.11] | >= +1.0 (held, +6.0) |
| Partner-ball legal | 77.35 % | **88.94 %** | >= 75.85 % (held) |
| Feeder-ball legal | 80.87 % | 77.26 % | >= 80.26 % (**failed**) |
| Families below run 14 - 5 points (contact) | | backhand -6.1, deep -5.5, low -6.5, topspin -5.9, reach_deep -12.1 | none (**failed**) |
| cross_forehand contact | 86.75 % | 82.22 % | >= 81.95 % (held) |
| Left + back feeder contact | | 52.5 % (run 14 58.8) | >= run 14 - 5 (**failed**, -6.3) |
| Court contact / court main / drill v2 / move arrival | 83.5 / 77.4 / 86.4 / 99.1 % | 83.0 / 76.9 / 87.3 / 99.1 % | held |
| Court falls per episode | | 3.88 % (low 2.73) | held |
| Share of returns above 11 m/s | 11.9 % | 5.7 % | reported |

- **The rally improved fast; the feeder balls eroded broadly.** Almost every feeder family lost 1-7 points of legal return (fast 71.7 -> 61.9, cross_backhand 65.4 -> 58.6, reach_deep 36.9 -> 30.4). It is not one family: it is the whole feeder ball.
- **The mechanism: the feeder ball's share of play falls as the rally gets longer.** Feeder balls started / all balls started in the pairs reads: run 14 25.9 %, model_29000 21.5 %, model_30200 **13.3 %**. In pair-mode training a feeder ball only starts a rally, so the better the partner rally, the fewer feeder balls the policy sees, and the more it drifts toward partner balls: a self-reinforcing loop. PAIRS_COURT_FEED_PROB (0.678) was set in Stage 5H when hand-offs were 41 % of feeds; nothing holds the feeder share as rallies lengthen.
- The robot now returns softer, easier balls for the partner (share above 11 m/s halved), which helps the rally.

**Plainly:** the robot got much better at rallying with its partner (a third of rallies now reach 5 shots, partner returns 89 %), but because longer rallies mean fewer fresh feeder balls in practice, it is forgetting how to return them. The run was stopped on that, as pre-registered.

**Correction (round 42, experiment design and architecture):** run 14's task chain sets `court_feed_prob` to PAIRS_CONTACT_COURT_FEED_PROB = 0.80 (D-137), not 0.678 as written above. The mechanism is unchanged: the value only splits feeder balls between court and drill-v2 families and does not hold the feeder ball's share of play.


## Rally run 20 not started: the smoke's manipulation check refuted round 42's premise (2026-10-28)

Run 20 (D-161, a training rally cap of 5 shots) stopped at its smoke: the training feeder share of balls started read 0.686, outside the pre-registered 0.20-0.35 (taken from the pairs reads). The run never trained. A diagnostic (`scripts/diag/train_share.sh`; 200 throwaway iterations at 1,024 envs from run 18b model_29000, training seeds 100 / 101, `results/train-share-cap{0,5}.jsonl`) measured the share in real training dynamics:

| Window (env steps after resume) | No cap (run 14's task) | Cap 5 (run 20's task) |
|---|---|---|
| 1st quarter | 0.665 | 0.698 |
| 2nd quarter | 0.669 | 0.687 |
| 3rd quarter | 0.676 | 0.713 |
| 4th quarter | 0.685 | 0.697 |

- **In training, two of every three balls started are feeder balls, with or without the cap.** The training task runs move-to-spot episodes (move_prob 0.35) and ghost-ball swing episodes (swing_prob 0.05); a hand-off to a busy partner ends the rally (D-140), so most training rallies end at the first hand-off. The cap moves the share by about 2-3 points.
- **Round 42's mechanism held for the reads, not for training.** The share that fell 25.9 -> 21.5 -> 13.3 % was measured in the pairs reads (move and swing off, 120 s rallies). Training never practised that distribution; its feeder share is about 0.67 and stable. Run 19's feeder-ball loss therefore needs another explanation; exposure is not it.
- **Also exposed:** the pairs read (the target protocol) plays long uninterrupted rallies that training almost never produces, so the target is measured on a distribution the policy does not train on.

**Plainly:** the fix we voted for would not have changed what the robot practises. In training, feeder balls are already two thirds of all balls, because the partner is often busy with a footwork drill and the rally stops. So the robot did not forget feeder balls for lack of practice; something else (likely the reward) is pulling it toward the partner rally. The panel reconvenes.


## Refeed-delay diagnostic (panel round 43, 2026-10-28; diagnostic only)

Run 19's feeder-ball loss appeared only in the pairs read, where each feeder ball comes 0.5 s after a rally ends. `scripts/diag/refeed_delay.sh` read run 18b model_29000 and run 19 model_30200 in run 19's pairs read with the feeder ball delayed 3.0 s (`--refeed-delay 3.0`), seed 4220053 for both; results `results/refeed3-{29000,30200}-pairs.json`.

| At 3 s | model_29000 | model_30200 | Difference (0.5 s read) |
|---|---|---|---|
| Feeder-ball legal | 83.72 % (low 82.97) | 82.60 % (low 81.69) | **-1.12** (-3.61) |
| Feeder-ball contact | 82.67 % | 79.55 % | -3.1 |
| Feeder-ball falls per ball | 1.17 % | 1.41 % | +0.24 |
| Partner-ball legal | 77.90 % | 90.19 % | +12.3 |
| P(5+), open rallies counted | 28.83 % | **39.16 %** | +10.3 |
| Feeder share of balls started | 0.206 | 0.115 | |

- **About 70 % of run 19's feeder-ball loss is the start state.** Given 3 s to settle, the gap falls from 3.6 to 1.1 points. A real but smaller loss remains, mostly in contact (-3.1).
- **Pre-registered rule (experiment design):** L3 = 1.12, between 1.0 and 2.5, so "mixed: B": the next run removes busy partners from half the pair courts so training produces the read's post-rally feeder balls.
- With time to settle, run 19's model_30200 reaches P(5+) 39.2 % and partner legal 90.2 %.

**Plainly:** most of the feeder-ball "forgetting" was the robot being caught off balance by a feeder ball half a second after a long rally, a situation it almost never trains on. Given three seconds, it returns them nearly as well as before.


## Rally run 21 pre-launch check: STOP on the rally-length line (2026-10-28)

`scripts/diag/train_share_b.sh` (200 throwaway iterations each from run 18b model_29000, training seeds 102 / 103; `results/train-share-b-*.jsonl`, summary `results/train-share-b-summary.txt`) [train-diag]:

| | Run 14's task | Drill-court task (pair_drill_court_frac 0.5) |
|---|---|---|
| Feeder share, all courts | 0.680 | 0.482 |
| Feeder share, pair courts | | **0.376** (2,710 feeder, 4,495 hand-offs) |
| Feeder share, drill courts | | 0.931 (1,584 feeder, 118 hand-offs) |
| Hand-offs per feeder ball | 0.47 (all courts) | **1.66** on pair courts, 0.07 on drill courts |
| Mean training rally (shots per finished rally, all courts) | 0.82 | 1.09 |

- Pre-registered (D-162): pair-court feeder share within 0.15-0.45 (**passed**, 0.376) and mean training rally length >= 2 x run 14's task's (**failed**: 1.09 vs 1.64, measured over all courts).
- The failed line was computed over all courts. The drill courts now play almost no rallies (0.07 hand-offs per feeder ball), which pulls the all-court mean down; on the pair courts the change targets, hand-offs per feeder ball are 3.5 x the baseline's. Round 43's rule says manipulation checks are measured on the population the mechanism names, but reinterpreting a pre-registered line after the result is the panel's call, so run 21 did not start.


## Rally run 21 pre-launch check re-measured on the pair courts: STOP (D-163, 2026-10-28)

`scripts/diag/train_share_b2.sh` (drill-court task, 200 throwaway iterations from run 18b model_29000, training seed 106; per-court-group rally histogram and end reasons, logging only; `results/train-share-b2-drill.jsonl`, `results/train-share-b2-summary.txt`) [train-diag], second half:

| | Pair courts | Drill courts |
|---|---|---|
| Finished rallies / legal shots | 2,899 / 3,449 | 1,468 / 1,015 |
| Shots per finished rally (line >= 1.64) | **1.19** (**failed**) | 0.69 |
| Training P(3+) / P(5+) | 14.4 % / 4.7 % | 0.9 % / 0.3 % |
| Feeder share of balls started (line 0.15-0.45) | 0.394 (passed) | 0.925 |
| Rally ends: not a legal return / busy partner / reset / cap | 2,170 / 0 / 729 / 0 | 322 / 907 / 239 / 0 |

- **Run 21 does not start** (D-163's pre-registered fail branch); the panel reconvenes under option 3. RL predicted about 1.39 and architecture 1.23-1.39: both called the fail.
- **Two training/read gaps the reads never showed:**
  1. **The stochastic training policy returns about 61 % of shots** (3,449 legal shots against 2,170 rally-ending misses on the pair courts), against roughly 80-90 % per shot for the deterministic policy in the reads; training P(5+) is 4.7 % where the read's is 27 %. Exploration noise, not busy partners, keeps training rallies short.
  2. **A quarter of pair-court rallies end on a reset** (729 of 2,899): each robot's 30 s episode clock runs on its own and either robot's reset ends the court's rally, so a court's rally is cut about every 15 s.
- So "make training rallies resemble the read" needs more than freeing the partner: in training the robot rarely gets past shot 2 at all.

**Plainly:** even with no busy partner, practice rallies are short, because during training the robot plays with random noise added to its moves and misses about four shots in ten, and because either robot's practice episode ending stops the rally. The robot that is read (noise off) plays much better than the one that practises.


## Round 45 training screen (D-164, 2026-10-29) [train-diag]

`scripts/diag/screen45.sh`: run 21's drill-court task, 200 iterations at learning rate 0 (rollouts only) from run 18b model_29000, pair courts, second half; `results/screen45-*.jsonl`, `results/screen45-summary.txt`.

| Arm | Shots per rally | Per-ball legal | P(3+) | P(5+) | Feeder share | Ends: not legal / reset |
|---|---|---|---|---|---|---|
| S0 std x1 (calibration) | 1.218 | 0.619 | 15.0 % | 5.1 % | 0.392 | 2,116 / 709 |
| S1 std x 0.001 (about mean actions) | 1.357 | 0.648 | 17.4 % | 6.7 % | 0.374 | 2,016 / 717 |
| S2 std x1, 120 s episodes | 1.681 | 0.648 | 22.6 % | 9.0 % | 0.334 | 2,237 / 211 |

- **Calibration holds:** S0 reproduces run 21's check (1.19 shots per rally, 0.61 per ball).
- **The noise is not the cause** (pre-registered: S1 <= 0.65 rejects C): with near-mean actions the policy still returns only 0.648 per ball on the training task, against about 80-90 % in the pairs read. **The training task itself is harder than the read** (drill-v2 balls, the noisy planner, a 0.2 s refeed and the court mix, per round 45's motion and coach).
- **Longer episodes help but miss the line:** 120 s episodes cut reset ends from 709 to 211 and lift P(3+) to 22.6 %, below M's 30 %.
- **Route (D-164): neither passes -> A, after launch-state logging** (D-165).


## Launch-state measurement (D-165, 2026-10-29): A's premise fails

`scripts/diag/launch_state.sh` (logging only; reads of run 18b model_29000 and run 19 model_30200 on seed 4220079 [read:protocol], and run 14's task in training at learning rate 0, training seed 110 [train-diag]; `results/launch-*`):

| Feeder-ball legal by the previous rally's length | 0-1 shots | 2-4 shots | 5+ shots |
|---|---|---|---|
| model_29000 (n 9,212 / 3,358 / 3,865) | 78.5 % | 85.6 % | 82.3 % |
| model_30200 (n 6,130 / 1,662 / 2,627) | 74.0 % | 84.7 % | 79.5 % |
| Change | -4.6 | -0.9 | -2.8 |

- **Pre-registered rule (D-165): not met.** Feeder balls after a 5+ rally are returned *better* than after a 0-1 rally (79.5 vs 74.0 % at model_30200), and the median launch displacement after a 5+ rally (<= 0.8 m) is no larger than after a 0-1 rally and below training's 90th percentile (> 1.2 m): training launches are already more displaced. So A ("move, then serve") is not supported; the panel reconvenes with the training-vs-read table.
- **Run 19's feeder loss sits mostly after short rallies** (0-1 shots: -4.6 points), i.e. right after the previous feeder ball was missed or returned once.
- **Known flaky test:** `test_court_feed_mix_shares_families_recovery_and_planner` ("two extremes in a row among v2 feeds") fails intermittently on the code from before the D-161..D-165 changes too (2 of 3 runs at commit ba9f6ee in the fix worktree, run with its artifacts linked to the main checkout); not caused by these changes.

**Training vs read configuration [read:protocol]** (training: run 14's task's config; read: `Picklebot-Latent-Court-Res-G1` plus stage2_eval's pairs-read flags):

| Setting | Training | Pairs read |
|---|---|---|
| Actions | sampled (std 0.1-0.2) | mean |
| Observation corruption (ball noise / lag) | on | off (stage2_eval) |
| Feeder balls | 80 % court feeds from COURT_MIX_WEAK (backhand, fast, reach_backhand, cross_backhand x2; low, drop, reach_deep x1.5) + 20 % drill-v2 balls | uniform over all families, no drill-v2 |
| Stance-spot planner | noisy | off |
| Target | random A/B | A |
| Refeed delay | 0.2 s | 0.5 s |
| Episode | 30 s, resets end the court's rally | 121 s |
| Move / swing episodes | 0.35 / 0.05 (busy partners end rallies) | 0 / 0 |
| Recovery spot | random | fixed |
| Rewards | adds keep_alive, partner_return, rally_bonus, ball_out_over | (not used) |

**Plainly:** the robot is not worse after long rallies; it is worse right after a short one, and it already practises from out-of-position starts more than the read shows. Training and the read differ in about ten ways at once, and the same policy returns about 65 % of balls in training against 80-90 % in the read even with the noise off. The next step is to find which of these differences matter.


## Training-side erosion check (D-166, 2026-10-29): no feeder loss in training

`scripts/diag/erosion_check.sh`: run 14's task, 200 iterations at learning rate 0 with sampled actions, second half; `results/erosion-*` [train-diag].

| Arm | Feeder legal (n) | After a 0-1 rally |
|---|---|---|
| T1 run 18b model_29000 (seed 111) | 74.96 % (5,899) | 75.02 % |
| T2 run 19 model_30200 (seed 112) | 75.82 % (5,649) | 75.55 % |
| T3 model_29000 again (seed 113) | 75.13 % (5,797) | 75.41 % |

- **Dtrain = +0.86 points** (SE of a difference about 0.8); replicate |T3 - T1| 0.16. **VERDICT (coded): NO TRAINING LOSS.** Run 19 did not forget feeder balls in the training distribution; its -3.6-point feeder loss exists only in the pairs read. Route (D-166): the training-side leave-one-out screen A-T (D-167).

**Plainly:** in practice conditions the newer robot returns feeder balls as well as before (slightly better). The drop shows up only in the test conditions, so something about how the test differs from practice exposes it.


## Training-side leave-one-out screen A-T (D-167, 2026-10-29) [train-diag]

`scripts/diag/attribution_at.sh`: run 14's task from model_29000 with near-mean actions (std x 0.001), learning rate 0, 200 iterations at 1,024 envs, second half; each arm moves one setting to the pairs read's value; `results/at-*`, `results/at-summary.txt`.

| Arm | Per-ball legal | Delta | Feeder legal |
|---|---|---|---|
| T0 baseline | 72.64 % | | 78.09 % |
| T1 no drill-v2 balls | 70.71 % | -1.93 | 76.88 % |
| T2 uniform family mix | 74.45 % | +1.81 | 80.81 % |
| T3 refeed 0.5 s | 72.91 % | +0.27 | 78.50 % |
| T4 fixed recovery spot | 74.85 % | +2.21 | 79.63 % |
| T5 planner off | 71.40 % | -1.24 | 76.84 % |
| T6 target A | 72.86 % | +0.22 | 77.98 % |
| T7 ball noise off (sim-to-real) | 72.44 % | -0.20 | 77.06 % |
| T8 proprioceptive noise off (sim-to-real) | 75.05 % | +2.41 | 79.48 % |
| **TA all eight** | **81.65 %** | **+9.01** | **85.29 %** |
| model_30200 at T0 (reported) | 75.59 % | | 78.31 % |
| model_30200 at TA (reported) | **85.75 %** | | 85.86 % |

- **Coded verdict: NONE ELIGIBLE** (no T1-T6 Delta >= 3.0). Largest single effects: proprioceptive noise off +2.4 (a sim-to-real commitment, not eligible), fixed recovery spot +2.2, uniform mix +1.8.
- **Calibration passes under both readings** of the line: TA 0.8165 against the pre-registered 0.71 and against the intended "half the gap" value of about 0.748 here. **Flag:** the 0.71 line had been set from the drill-court screen's ~0.65 baseline; on run 14's task T0 is 0.726, so 0.71 would have passed trivially; it did not matter here.
- **The settings interact:** the single Deltas sum to about +3.5, but all eight together give +9.0. The gap to the read is real and is explained by the configuration taken together, not by any one setting.
- **In the read-like training configuration, model_30200 is better than model_29000** (per ball 85.8 vs 81.7 %, feeder 85.9 vs 85.3 %): the newer policy does not lose feeder balls there either.
- The T5 override check printed VOID because YAML writes the value as `'off'` (quoted); the arm's params/env.yaml shows `planner_mode: 'off'`, so T5 is valid (a check bug, not an arm failure).

**Plainly:** no single practice setting explains why the robot plays better in the test than in practice; together they explain all of it (and more). Run 19's robot is the better one in practice conditions made test-like, and it still loses feeder balls only in the test itself.


## Rally run 22 pre-launch check: PASS (D-169, 2026-10-29) [train-diag]

`scripts/diag/prelaunch22.sh`: run 22's exact task and overrides (run 21's drill-court task with 120 s episodes plus A-T's O1-O6: no drill-v2 balls, uniform family mix, refeed 0.5 s, fixed recovery, planner off, target A; sim-to-real noise kept on) at std x1, learning rate 0, 200 iterations from run 18b model_29000, training seed 127; pair courts, second half.

| Pair courts | Run 21's task (round 45 S0) | Run 22's task | Line |
|---|---|---|---|
| Per-ball legal | 0.619 | **0.708** | >= 0.678 (**passed**) |
| Shots per rally | 1.22 | 2.19 | |
| P(3+) / P(5+) | 15.0 / 5.1 % | 28.6 / 14.4 % | |
| Feeder share | 0.392 | 0.288 | 0.15-0.45 (passed) |

Training now produces read-like rallies (P(3+) close to round 45's M line of 30 %, P(5+) about three times higher). Run 22 launched (smoke, parent re-read, then 4,000 iterations).

Phase 2 plan written (`docs/research/footwork-route-2026-10-29.md`): fast left / back stepping (> 1 m/s) has never been trained or measured on the rally stack; the first step is an agility screen (about 2 GPU-h) with a coded route to time-pressured left / back move drills (E) or a faster walking teacher kickstart (C).

## Run 22 smoke stop and run 22b (D-170, 2026-10-29)

Run 22 never started. Its smoke stopped on mean logged fell_over 0.288 against the 0.159 line, while the gradient and config checks passed. That logged value is not a fall rate. It is the mean per-step count of envs that fell, averaged only over steps that had a reset. Episodes of 120 s reset about 4x more rarely than 30 s ones, so the number inflates: every 120 s log reads 0.23-0.29 and every 30 s log reads 0.07-0.12.

Per unit time (scripts/diag/falls_by_length.py, Poisson correction, cross-checked to about 1 episode per env per episode length), smoke falls per 1,000 env-seconds:

| log | episode | logged fell_over | falls / 1,000 env-s |
|---|---|---|---|
| run 14 smoke | 30 s | 0.106 | 2.77 |
| run 18b smoke | 30 s | 0.117 | 2.86 |
| run 19 smoke | 30 s | 0.085 | 2.12 |
| run 20 smoke | 30 s | 0.118 | 3.13 |
| screen45-S0 | 30 s | 0.105 | 2.74 |
| A-T T0 / TA | 30 s | 0.085 / 0.074 | 2.06 / 1.78 |
| screen45-S2 | 120 s | 0.266 | 2.16 |
| prelaunch22 | 120 s | 0.232 | 2.21 |
| **run 22 smoke** | 120 s | 0.288 | **2.12** |

Run 22's smoke falls less often per unit time than run 14's smoke. The new smoke line has the same meaning, 1.5 x run 14's smoke: <= 4.157 falls per 1,000 env-seconds. **Run 22b** (scripts/rally_run22b.sh) is run 22 unchanged apart from that line and its new names. It launched 15:43.
