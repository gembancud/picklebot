# Review round 13: after E4; the user hands the next steps to the panel (D-123); the first ball run (2026-10-20)

Brief: the E4 endpoint (3 of 6), E4's zero-shot ball smoke test (legal returns 15.0 %, falls 2.4 % per feed against E3's 15.9 % and 1.1 %), and the user's direction to return only with a rally video the panel approves.

## Correction check

- **E1 gate: missed, not met.** It is not re-scored or relaxed (experiment design). D-122's line "ball fine-tuning waits until the E1 gate is met" was a rule, so moving past it needs its own D-entry that names the premise: **D-124**. The premise is that the ball-free bank is not the binding constraint. E4 gained 4 points of root on the bank and nothing with the ball. The E1 items are still reported at every endpoint.
- **E4's extra falls with the ball are real** (motion, experiment design). The intervals [1.9, 3.0] % and [0.8, 1.5] % per feed do not overlap. At about 2.8 feeds per episode, that is roughly 6.6 % vs 3.1 % per episode against R3's 4 %.
  - The smoke file's `robot_fall_rate_per_episode` of 1.0 is a censoring artifact: in a 30 s run, robot episodes only end by falling. Mark it invalid (motion).
  - Falls also rose late in E4, after the 30 % check, so every run gets a fall check at its endpoint too.
- **Missing pieces:**
  - The ball command never set `req_speed`, so live-ball goals' required speed was never measured (RL; fixed: one line). No reviewer calls root >= 90 % unreachable until it is measured (motion).
  - The ball task has the court task's rewards and cannot train the timed controller as written (RL, architecture).
  - The ball command's per-step `nonzero()` host sync and eager `aim_outgoing` are too slow for training (architecture).
  - The face factor `0.5 + 0.5|n.n*|` pays 0.93 at 30 degrees of face error, the likely cause of the scattered landings (coach). This is recorded, not changed in this run.
  - The 1-in-2,525 five-shot rally must not become the video (coach, experiment design).

## Decisions (majority; ties: least new code)

1. **The next run is E5: PPO in the ball environment** (5 of 5).
   - **Parent:** E3's endpoint, model_39699 (4 of 5: RL, motion, coach, experiment design; architecture chose E4). E3 has the same legal-return rate as E4 with the ball, half the falls, and better timing.
   - **Rewards:** E3's V3 terms unchanged:
     - paddle_track_open;
     - timed_contact (linear0, 5 per goal);
     - root_track;
     - root_progress capped at 1.0;
     - alive;
     - fall -50;
     - prior, L2 and action rate.

     Plus `legal_return` at 5 per legal return (the court task's 250 / step_dt weight). The court task's pace term (`return_shaping`) and its other legacy court terms are not used (RL; D-118 step 4).
   - **No 40 % rehearsal** (2-2, with experiment design silent; the tie goes to the least code).
     - In the ball environment every feed is already a court feed.
     - `court_feed_prob` feeds get no plan window, so they would silently get no goal (architecture).
     - Forgetting is watched instead through a ball-free bank re-read at the early check.
   - **Critic warm-up:** CriticWarmupHoldLrRunner, because the reward scale changes (RL; D-114).
2. **Early kill at about 30 %** (each line is the majority or the median of the stated lines). Any one of these kills the run:
   - falls per feed > 2.5 %;
   - legal returns <= 15.9 % (E3's zero-shot rate) on a fixed development seed;
   - on the ball-free bank re-read: paddle p90 > 0.20 m or speed error > 20 %.

   The fixed endpoint is also checked for falls per feed.
3. **The rally video for the user** (3 of 5 for two robots; 2 of 3 of those for a 10 % bar).
   - The setup:
     - two copies of one fixed endpoint;
     - the R4 protocol (`h5g_pairs.sh`);
     - at least 1,000 rallies;
     - a new development seed logged before the read.
   - **It qualifies when P(4 or more consecutive legal robot shots) >= 10 %,** with the Wilson interval reported. The feeder ball does not count.
   - **The clips are pre-registered:** the first qualifying rally in seed order, plus the first 3 rallies in seed order whatever happened. The rate, interval and falls per feed are shown on screen.
   - It is labelled **interim** unless R1-R4 are met. The R1-R4 bars are unchanged. Robot-vs-feeder clips stay internal.
4. **Budget: 2 more runs, E5 and E6** (4 of 5).
   - If E5 gains 5 points or more in legal returns, E6 is a routine continuation from it. Otherwise the panel picks E6's one change.
   - **Panel round (not the user)** at either of:
     - a third kill in a row;
     - two runs each gaining less than 2 points (plateau).
   - A panel round also follows E6. More runs need a D-entry.
5. **Tooling first, the minimum** (5 of 5 for throughput):
   - (i) **Planning without host syncs** in the ball command, copying the ball term's `_plan_step` pattern: a persistent due flag, a fixed batch through `topk`, writes by `where`. `aim_outgoing` is compiled at that fixed shape.
   - (ii) **The command summary goes into the smoke JSON:** root hit rate by the speed live goals require, and timing.
   - (iii) **E3's zero-shot smoke test rerun** on a new development seed with the new adapter. This is the equivalence check: legal returns within E3's interval. It also measures live-ball required speeds.
   - (iv) **A throughput probe:** 50 iterations at 4,096 envs. The bar is at most 3.5 s per iteration, about 2,000 iterations in 2 h. If it is slower, profile it before launching, and never go below 2,048 envs.
   - (v) **The pre-launch check:** per goal, the rewards rank a legal return with a good swing above a good swing that is not legal, above a miss, above a fall.

# Round 13b: live-ball goals need faster walking than the bank; E5 unchanged (5 of 5)

**Tooling (iii): E3's zero-shot on the E5 ball task with the sync-free goals** (seed 4216020; `results/s5g-zs-e3-sync-free.json`).
- **The equivalence check passes.**

  | | Old adapter | New adapter |
  |---|---|---|
  | Legal returns | 15.9 % | 15.24 % [13.99, 16.57] |
  | Falls per feed | 1.1 % | 1.74 % [1.33, 2.28] |
  | Contact | 45.9 % | 45.6 % |

- **New fact:** 35 % of live goals need more than 1.5 m/s of walking (the bank: 21 %), and 18 % need more than 2 m/s.
  - Root within 0.25 m is 49.6 % with the ball, against 65 % on the bank.
  - With the ball, paddle error at t* has a median of 0.04 m but a p90 of 1.0 m.

| Required speed (m/s) | Live goals | E3 root within 0.25 m |
|---|---|---|
| 0-0.5 | 687 | 0.956 |
| 0.5-1.0 | 690 | 0.796 |
| 1.0-1.5 | 571 | 0.385 |
| 1.5-2.0 | 524 | 0.122 |
| 2.0-2.5 | 327 | 0.009 |
| 2.5+ | 213 | 0.000 |

**Correction check:** no errors (5 of 5). Motion notes that more than 2 m/s is at or beyond safe G1 walking, so root near 90 % on live goals is probably out of reach under this planner. This is recorded; no gate changes.

**Decisions:**
1. **E5 runs unchanged** (5 of 5).
   - A root_progress cap of 1.6 repeats E4, which doubled falls with the ball. It would also be a second change.
   - The likely lever is a planner that asks for less walking: contact later on the ball's path. It is the pre-registered E6 candidate (5 of 5) if E5's 1.0-2.0 m/s bins do not improve.
2. **No new kill lines** (4 of 5; architecture alone proposed one).
3. **Report only, at the early check and the endpoint,** against the table above:
   - root, legal returns and falls by required speed (5 of 5 for root and legal; falls 2 of 5, added because the counter is shared);
   - paddle p90 of reachable goals (<= 1.5 m/s; 3 of 5);
   - the share of goals swung at from more than 0.5 m (coach);
   - goals per feed (architecture).
4. **Pre-registered expectation** (experiment design): with the cap at 1.0, the bins above 1.5 m/s stay near zero, and any gain comes from the 0.5-1.5 m/s bins.
