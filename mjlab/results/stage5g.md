# Stage 5G: the timed goal-conditioned controller (the exit stage, D-117 / D-118)

Design: `exit-stage-review.md` (panel round 9). The readiness milestone (`selfplay-readiness.md`) is unchanged and re-registered. Budget: 6 runs.

## Step 0 (no training)

- **Planner** (`planner.py`, tests in `tests/test_stage5f.py`):
  - **Contact:** `predict_contact` (point, ball velocity and time) at a 2.5 ms step is within 2.7 cm and 10 ms of the full simulation. A 12.5 ms step gave 14 cm and 63 ms.
  - **Keep-it-alive aim:** `aim_outgoing` lands within 10 cm of a target in the box (landing x +4.7 to +5.7, |y| <= 1, flight time 1.3-1.5 s).
  - **Paddle state:** `paddle_for`, the closed-form inverse of the impact model, reproduces the commanded outgoing ball within 5 % through `sphere_impulse`.
- **Goal bank** `bank-s5g-01.pt` (sha256 d011fb34...; `scripts/build_goal_bank.py`, seed 4216004): 36,530 goals.
  - Sources: drill v2 16,022; court 11,890; own-ball 8,618.
  - The own-ball source is the robot's returns re-recorded from run 4's endpoint on seed 4216003 (sha256 85853fa3...), never the readiness recordings.
  - **Goal shape (10th / 50th / 90th percentile):**

    | Quantity | Value |
    |---|---|
    | t* | 1.05 / 1.33 / 1.61 s |
    | Commanded paddle speed | 6.6 / 7.3 / 7.9 m/s |
    | Contact height | 0.50 / 0.75 / 1.10 m |
    | Root target distance | 0.32 / 1.61 / 2.31 m |

- **Parent baseline:** reach-06/model_34700, widened 111 -> 117 inputs with zero weights, zero-shot on the timed task (seed 4216010, 1,024 envs, 20 s):

  | Measure | Value |
  |---|---|
  | Paddle error at t*, median / p90 | 0.32 / >= 1.0 m |
  | Speed error, median | 90 % |
  | Timing within 50 ms | 13 % |
  | Root within 0.25 m | 25 % |
  | Falls per episode | **15.2 %** |

- **Diagnostic** (spare seed 4216011, goals with root targets within 1 m only):

  | Measure | Value |
  |---|---|
  | Paddle error, median / p90 | **0.02** / 0.22 m |
  | Speed error | 96 % |
  | Timing within 50 ms | 20 % |
  | Root within 0.25 m | 67 % |
  | Falls per episode | 2.1 % |

  **Reading:**
  - The parent already places the paddle. It does not swing: it parks the paddle and holds it.
  - Its falls come from the long walks (median 1.6 m in under 1.4 s).
  - The bank is kept as built. Court feeds need those walks, and easing the bank after seeing the baseline would ease the gate.

## Runs (budget 6; the panel's stop rules in D-118)

| # | Run | Change (written before launch) | From | Endpoint | Result |
|---|---|---|---|---|---|
| E1 | s5g-e1-timed | Timed command and rewards (`Picklebot-Latent-TimedReach-G1`): swing guide, plus a one-shot contact reward at t* (weight 5 per goal); 4,096 envs; training seed 74 | reach-06/model_34700, widened | iteration 39,700 (5,000 more), or the last checkpoint before the 7,000 s cap | **Killed at the early check (model_36200):** median paddle error 0.53 m (> 0.25), falls 1.0 % (pass). Cause: the reward design (see below). |
| E2 | s5g-e2-timed-v2 | One paddle-reward redesign (D-119): reach-06 paddle_track to p* while the goal is open, no swing guide, linear contact velocity factor; plus the two timed_reach fixes (reset, timing grid) | reach-06/model_34700, widened | iteration 39,700, or the last checkpoint before the 7,000 s cap | **Killed at the early check (model_36200): falls 5.12 % (40 / 781 episodes; line 5 %).** Median paddle error **0.01 m**, p90 0.08 m (pass); speed error 96 %; timing within 50 ms 21.7 %; root within 0.25 m 59 %. |
| E3 | s5g-e3-timed-v3 | The contact reward's speed floor removed: fv = clamp(1 - |dv|/|v*|, 0, 1) (D-121); nothing else | reach-06/model_34700, widened | iteration 39,700, or the last checkpoint before the 7,000 s cap | **Gate: 3 of 6 met** (endpoint model_39699, seed 4216110). Paddle error median 0.03 m (<= 0.08) and p90 0.10 m (<= 0.20); speed error median **4 %** (<= 20 %); timing within 50 ms 44.5 % (needs 80 %); falls 2.48 % (needs 2 %); root within 0.25 m 64.9 % (needs 90 %). Not a kill (early check passed). |
| E4 | s5g-e4-root16 | D-118's one extension (D-122): root_progress max_speed 1.0 -> 1.6 m/s; nothing else | E3 endpoint (model_39699) | iteration 44,699, or the last checkpoint before the 7,000 s cap | **Gate: 3 of 6 met** (endpoint model_44698, seed 4216310). Paddle 0.02 / 0.06 m; speed error 0.04; timing 71.5 % (needs 80 %); falls 3.07 % (needs 2 %); root within 0.25 m 69.3 % (needs 90 %). Not a kill. **D-118's one extension is used, so the decision goes to the user.** |

- **E1 early kill (D-118)** at model_36200 (seed 4216101, 256 envs): falls above 5 %, or a median paddle error above 0.25 m.
  - **The parent fails both today** (15.2 %, 0.32 m), so E1 must improve on both by 30 % of the run.
- **E1 gate (D-118):**
  - median paddle error <= 0.08 m, p90 <= 0.20 m;
  - timing within 50 ms >= 80 %;
  - median speed error <= 20 %;
  - falls <= 2 %;
  - root within 0.25 m >= 90 %.

  Endpoint seed 4216110.

### E1 kill diagnosis (training log; agent's implementation error)

- **The rewards gave no paddle signal.** `timed_contact` paid 0.000 per episode throughout, and `swing_guide` 0.003-0.010.
  - **The swing guide's lead target, p* - v* min(tau, 0.3 s), lay about 2.1 m behind the contact point** at the bank's median commanded paddle speed of 7.3 m/s. That is out of reach.
  - The contact reward's velocity kernel (std 1 m/s) is about exp(-49), roughly 0, for a parent that parks the paddle (|dv| about 7 m/s).
  - The dense paddle reward of reach-06 had been removed.
- **What the policy learned instead:** it kept root and falls and abandoned the paddle.
  - Falls fell from 15.2 % to 1.0 %; mean paddle distance drifted from about 1.0 m to 1.13 m.
  - Early check: median paddle error 0.53 m, speed error 84 %, timing within 50 ms 4.8 %, root within 0.25 m 52 %.
- **Counters:** Stage 5G kills 1, runs 1 of 6. The panel (round 10) specifies the fix.

### E2 pre-launch check (D-119; parent zero-shot on the E2 task, 256 envs, 10 s, seed 4216012): **pass**

- **Reward sums per env:**

  | Term | Sum |
  |---|---|
  | paddle | 113 |
  | timed_contact | 211 |
  | root | 206 |
  | root progress | 161 |
  | alive | 250 |
  | fall | -5.9 |
  | latent L2 | -158 |
  | action rate | -27 |

- **Contact reward:** > 0.01 on 47 % of 1,293 scored goals (q10 / 50 / 90 = 0.000 / 0.001 / 0.454).
- **Factors:**
  - speed: 0.50 / 0.50 / 0.54, std 0.021 (varies);
  - position: 0.00 / 0.002 / 0.98;
  - align: 0.61 / 0.84 / 0.97.
- **The reset fix holds:** the first goal after a reset sits 1.80 m from the pelvis (median, 259 goals), later goals 1.68 m.
- **Commanded paddle speed** (bank): along n* 7.10 m/s median (6.43-7.70), tangential 1.77 m/s. The swing really is fast; the tangential copy is small.
- **The parent's peak paddle speed** in 10 s: 3.9 / 4.8 / 6.1 m/s (q10 / 50 / 90). Not shown infeasible, so there is no premise stop. Watch whether the speed error falls in E2.

### E2 at its early check: killed on falls by one episode; 2 kills in a row

- **Paddle position is learned:** median error at t* 0.01 m, p90 0.08 m. The position part of the E1 gate is already met at 30 % of the run.
- **No swing:** speed error 96 %. The policy parks the paddle on p* and waits. Timing within 50 ms is 21.7 %: it arrives early and holds.
- **Falls:** 5.12 % per episode (40 of 781 at the early check's 256 envs and 20 s), against the 5 % line. The rule is not loosened; it is a kill.
- **Stage 5G: 2 kills in a row (E1, E2), 2 of 6 runs. Under D-118 / D-119 the decision returns to the user.** The loop stops.
- **Evidence for the next decision:**
  - The motion reviewer's round-10 concern: at lambda 1, executors topped out at 4.4-4.7 m/s paddle speed, and the commanded speed along n* is 7.1 m/s.
  - The parent's peak paddle speed is 4.8 m/s (median).
  - Speed, not position, is the open problem.

### E3 pre-launch check (D-121): three runs

| Run | Seed | Contact > 0.01 | Spearman (kp > 0.5) | fv > 0 (kp > 0.5) | Fall sum | Paddle sum | Root sum |
|---|---|---|---|---|---|---|---|
| E2's check, for reference (E2 reward) | 4216012 | 47 % (floored factor) | | | -5.86 | 113.1 | 206.4 |
| E3, spare seed | 4216013 | 14.8 % | 0.919 (534) | 57.7 % | **-7.62** (old 10 % rule failed) | 114.3 | |
| E3, E2's seed | 4216012 | 15.5 % | 0.914 (531) | 54.8 % | -5.47 | 116.2 | 204.7 |
| E3, E2's seed, repeated | 4216012 | | | | -5.86 | 110.7 | 205.3 |

- **The GPU rollout is not bit-reproducible:** two identical runs differ as much as E3 differs from E2. The rules were replaced, and the standing rule is now the identical-run spread (D-121).
- **Park vs swing** (unit test, passes): per goal, a perfect swing beats parking by >= 2, and a 4.8 m/s swing with a 5 cm miss beats it by >= 1. Under E2's floor they tied.

### E3 early check (model_36200, seed 4216101): **pass**

| Measure | E3 | Kill line |
|---|---|---|
| Falls per episode | 4.0 % | > 5 % |
| Paddle error at t*, median | 0.05 m | > 0.25 m |
| Paddle error, p90 | 0.25 m | |
| Speed error, median | **60 %** (E2: 96 %) | |
| Timing within 50 ms | **38 %** (E2: 22 %) | |
| Root within 0.25 m | 56 % | |

- **The swing has started:** the floor removal moved the policy off parking.
- **Off the GPU while E3 trains:** `TimedBallCommand` and `Picklebot-Latent-TimedBall-G1`. They run the timed controller in the court ball environment with goals from the live ball: the noisy spin-blind planner at the ball term's plan window, a keep-it-alive outgoing ball, and the stance spot. This is the zero-shot evaluation tool. It is not yet run.

### E3 at its endpoint (model_39699; seed 4216110; 1,024 envs, 30 s; 15,581 goals)

| Gate item | E3 | Bar | |
|---|---|---|---|
| Paddle error at t*, median | 0.03 m | <= 0.08 m | met |
| Paddle error at t*, p90 | 0.10 m | <= 0.20 m | met |
| Speed error, median | **0.04** | <= 0.20 | met |
| Timing within 50 ms | 0.445 | >= 0.80 | missed |
| Falls per episode | 0.0248 | <= 0.02 | missed |
| Root within 0.25 m at t* | 0.649 | >= 0.90 | missed |

- **The swing is learned.** Speed error fell 96 % -> 60 % -> 4 % (parent, early check, endpoint) while position held at 3 cm. The paddle now passes p* at the commanded speed.
- **Still open:**
  - timing of the closest approach;
  - the feet (65 % of root targets within 25 cm at t*; the bank's median walk is 1.6 m);
  - falls, 0.5 points over the bar.
- **Not a kill.** The gate is missed, so the panel decides the next run (D-118: one extension of the controller run before the user's call on a bigger controller).

### E3 zero-shot in the ball environment (smoke, not a readiness read; seed 4216014; 256 envs; 30 s; `Picklebot-Latent-TimedBall-G1`)

The timed controller with no ball training. Goals come from the noisy spin-blind planner (keep-it-alive box) on court rally feeds.

| Measure | Value |
|---|---|
| Contact | **45.9 %** of 2,988 feeds |
| Legal returns | **15.9 %** |
| Falls per feed | 1.1 % |
| Paddle speed at contact | 5.5 m/s (sd 1.6) |
| Ball speed out | 7.9 m/s (the keep-it-alive target is about 8) |
| Net clearance | 1.54 m (high) |
| Landing x | 3.2 m (target box 4.7-5.7) |

- **Weakest families:** reach_deep 3 % legal, topspin 7 %, cross_forehand 8 %, fast 9 %.
- **Speed tooling:** the eager contact rollout made in-environment planning CPU-bound (more than 47 min for 30 s of 256 envs). `planner.predict_contact_fast` is a padded, compiled version, equal to the eager one (`test_predict_contact_fast_matches_eager`). The adapter now uses it, and this smoke test took about 10 minutes.

### D-122 timing correction and E3 re-evaluation (seed 4216111; 1,024 envs; 30 s; metric frozen at timed_reach.py sha256 ce144dd2...)

| Policy | Timing within 50 ms, corrected (window [t* - 0.25, t* + 0.10]) | Timing, old whole-window metric | Paddle median / p90 | Speed error | Root within 0.25 m | Falls |
|---|---|---|---|---|---|---|
| E3 (model_39699) | **0.757** (gate 0.80) | 0.438 | 0.03 / 0.10 m | 0.06 | 0.652 | 2.60 % |
| E2 (model_36200, a parker): falsification | **0.309, fails** as it must | 0.226 | 0.01 / 0.08 m | 0.96 | 0.600 | 5.41 % |

**Root within 0.25 m at t*, by the speed the goal requires** (|root_rel| / t*):

| Required speed (m/s) | E3 goals | E3 hit rate | E2 hit rate |
|---|---|---|---|
| 0.0-0.5 | 3,224 | 0.995 | 0.987 |
| 0.5-1.0 | 3,407 | 0.832 | 0.834 |
| 1.0-1.5 | 5,686 | 0.631 | 0.539 |
| 1.5-2.0 | 2,693 | 0.199 | 0.103 |
| 2.0-3.0 | 574 | 0.000 | 0.000 |

- **The old metric under-read E3's timing by 32 points.** On the corrected metric E3 is at 75.7 %, close to the bar. The falsification passes: a parker still fails.
- **Root misses cluster where the goal needs more than 1 m/s,** which is root_progress's cap. By D-122's rule, E4 raises the cap to 1.6 m/s.
- **E4 pre-launch check** (`test_e4_root_speed_cap_ranks_arriving_on_time_first`, passing): over a median goal, walking at the required speed then swinging > a slow walk and a lunge > walking with no swing. The A - B margin grows from cap 1.0 to 1.6.
- **E4 early kill** at model_41200 (seed 4216301): falls > 3 %, paddle p90 > 0.20 m, or speed error > 20 %. Endpoint seed 4216310.

### E4 early check (model_41200, seed 4216301): **pass**

| Measure | E4 | Kill line |
|---|---|---|
| Falls | **1.56 %** | > 3 % |
| Paddle p90 | 0.08 m | > 0.20 m |
| Speed error | 0.04 | > 0.20 |

- **Also:**
  - timing (corrected) 76.8 % (old metric 41.2 %);
  - root within 0.25 m 68.7 % (E3: 65 %).
- **Root by required speed:**

  | Required speed (m/s) | Root within 0.25 m |
  |---|---|
  | 0.0-0.5 | 0.994 |
  | 0.5-1.0 | 0.880 |
  | 1.0-1.5 | 0.680 |
  | 1.5-2.0 | 0.239 |
  | 2.0+ | 0.000 |

- **Possible premise issue, for the panel at E4's end:** about 21 % of bank goals need more than 1.5 m/s of root speed. If those stay near 0-24 %, root >= 90 % may be unreachable with this bank at the walking speeds the motion prior supports.
- **Readiness scripts for the new controller** (D-118: the task as an argument, scoring unchanged): `h5g_ownball.sh` (sha256 0eaf5dec...) and `h5g_pairs.sh` (sha256 3c8e1441...).
  - R4's side symmetry is now read on own-ball shots only, the feeder ball excluded (D-116 tightening; `pairs.py` `sides_own_ball`).
  - `stage2_eval.sh` finds `picklebot_latent` runs.

### E4 at its endpoint (model_44698; seed 4216310; 15,558 goals): gate 3 of 6; one extension used, so back to the user

| Item | E3 (D-122 re-evaluation) | E4 early | E4 endpoint | Bar |
|---|---|---|---|---|
| Paddle median / p90 | 0.03 / 0.10 m | 0.03 / 0.08 m | **0.02 / 0.06 m** | 0.08 / 0.20 |
| Speed error | 0.06 | 0.04 | 0.04 | 0.20 |
| Timing within 50 ms (corrected) | 0.757 | 0.768 | 0.715 | 0.80 |
| Root within 0.25 m | 0.652 | 0.687 | 0.693 | 0.90 |
| Falls per episode | 2.60 % | 1.56 % | **3.07 %** | 2 % |

**Root within 0.25 m by required speed:**

| Required speed (m/s) | E4 hit rate | E3 hit rate |
|---|---|---|
| 0.0-0.5 | 0.993 | 0.995 |
| 0.5-1.0 | 0.874 | 0.832 |
| 1.0-1.5 | 0.698 | 0.631 |
| 1.5-2.0 | 0.278 | 0.199 |
| 2.0-2.5 | 0.008 | 0.000 |

- **The raised cap helped the 1-2 m/s goals by 7-8 points.** It cost about 4 points of timing, and falls rose from 1.6 % (early) to 3.1 % (endpoint).
- **The root item cannot reach 90 %** while about 21 % of bank goals need more than 1.5 m/s and the controller reaches almost none above 2 m/s.
- **Stage 5G after E4:** 4 of 6 runs used. The E1 gate is missed after D-118's one extension, so the decision goes to the user.

### E4 zero-shot in the ball environment (smoke; seed 4216015; 256 envs; 30 s; `results/s5g-zs-e4.json`)

| Measure | E3 (seed 4216014) | E4 |
|---|---|---|
| Contact | 45.9 % | 44.6 % of 2,967 feeds |
| Legal returns | 15.9 % | 15.0 % [13.8, 16.3] |
| Falls per feed | 1.1 % | 2.4 % |
| Paddle speed at contact | 5.5 m/s | 5.8 m/s |
| Ball speed out | 7.9 m/s | 8.3 m/s |
| Net clearance | 1.54 m | 1.78 m |
| Landing x (box 4.7-5.7) | 3.2 m | 3.4 m (sd 1.5) |

- **E4's better feet do not show up with a real ball.** Legal returns are flat (15.0 % vs 15.9 %), and falls per feed doubled.
- **The shots still land short** (3.4 m vs the 4.7-5.7 box) and wide (mean |y| 1.42 m vs |y| <= 1).
- **One rally in 2,525** reached 5 legal returns in a row against the feeder.

### E5 tooling (D-124 round 13 items i-v)

- **(i) Sync-free goals and a compiled aim:**
  - fixed batches of 128 envs through `topk`, with a persistent due flag;
  - no false window-closed edge across a reset;
  - tests `test_ball_goals_planned_in_fixed_batches_without_loss`, `test_ball_goal_no_false_edge_across_reset`, `test_aim_outgoing_fast_matches_eager`.
- **(ii) The command summary is in the smoke JSON:**
  - `req_speed` for live goals;
  - the D-122 timing for live goals;
  - round 13b's report-only items.
- **(iii) Equivalence: pass.** E3's zero-shot on the E5 task (seed 4216020): legal returns 15.24 % [13.99, 16.57] against 15.9 %. Live goals need more than 1.5 m/s 35 % of the time; see round 13b.
- **(iv) Throughput.**
  - **The first probe** (50 iterations at 4,096 envs) ran at **8.1-8.6 s per iteration**, over the 3.5 s bar. So it was profiled before launch, as the rule says (`scripts/diag/ball_env_profile.py`):

    | Configuration | Time per env step |
    |---|---|
    | As built | 354 ms |
    | Without the timed-goal planner | 150 ms |
    | Without both planners | 114 ms |

  - **The cause was kernel launches, not GPU work.** The contact rollout cost 144 ms per call (90 compiled calls), and the aim cost 29 ms.
  - **The fix:** each planner rollout (contact, aim, the ball term's stance rollout) is replayed from one CUDA graph per batch shape. That brought the contact rollout to 18 ms and the aim to 13 ms. The results are identical (`test_graphed_planner_rollouts_match_plain`, plus the eager-equality tests).
  - **After the fix:** **138.5 ms per env step, 3.32 s per 24-step rollout at 4,096 envs.** At 8,192 envs it is 4.0 s.
- **(v) The pre-launch check passes** (`test_e5_rewards_rank_legal_return_first`): a swing with a legal return > a swing without one > a miss > a fall.
- **The E5 ball environment as the battery defines it:** no stance hint, no move or shadow-swing episodes, every family uniform, feeds anchored at the start spot, no curricula.

### E5 launch (D-124): PPO in the ball environment from E3's endpoint

- 4,096 envs, training seed 76, 1,750 iterations (`scripts/h5g_e5.sh`, ITERS=1750). The endpoint is model_41448, or the last checkpoint before the 7,000 s cap.
- **Early kill** at model_40200 (29 %), on seeds 4216401 / 4216402:
  - falls per feed > 2.5 %;
  - legal returns <= 15.9 %;
  - on the bank: paddle p90 > 0.20 m or speed error > 20 %.
- **Endpoint:** the ball battery on seed 4216410 and the bank re-read on seed 4216411.

### E5 early check (model_40200; seeds 4216401 ball / 4216402 bank): **KILL** (2 of 4 lines)

| Item | E5 at 29 % | Reference | Kill line |
|---|---|---|---|
| Ball: falls per feed | **0.58 %** | E3 zero-shot 1.74 % | > 2.5 % (pass) |
| Ball: legal returns | 14.6 % [13.4, 15.9] | E3 zero-shot 15.24 % [14.0, 16.6] | <= 15.9 % (**kill**) |
| Bank: paddle p90 | 0.28 m | E3 0.10 m | > 0.20 m (**kill**) |
| Bank: speed error | 0.10 | E3 0.06 | > 0.20 (pass) |
| Bank: timing within 50 ms | **0.869** | E3 0.757 | report |
| Bank: root within 0.25 m | 0.526 | E3 0.652 | report |
| Bank: falls per episode | 4.7 % | E3 2.6 % | report |

**Report only (round 13b), the ball, by required speed (m/s):**

| | 0-0.5 | 0.5-1.0 | 1.0-1.5 | 1.5-2.0 | 2.0-2.5 | 2.5+ |
|---|---|---|---|---|---|---|
| Root within 0.25 m | 0.987 | 0.830 | 0.384 | 0.064 | 0 | 0 |
| E3 zero-shot root | 0.956 | 0.796 | 0.385 | 0.122 | 0.009 | 0 |
| Legal returns per goal | 0.282 | 0.211 | 0.135 | 0.033 | 0 | 0 |
| Falls per goal | 0.002 | 0.002 | 0.011 | 0.004 | 0.010 | 0.021 |

- **Other report-only items:** paddle p90 of reachable goals 0.07 m; goals swung at from more than 0.5 m: 21.5 %; live timing 0.737; goals set 3,144.
- **The training curve (`artifacts/train/s5g-e5-ball.log`):**
  - The legal_return term rose during the first 160 iterations and was then flat, at 0.13-0.17 per episode.
  - timed_contact rose from 0 to about 0.55 after the critic warm-up (50 iterations).
  - **The policy's action std grew from 1.05 to 1.19.**
- **As pre-registered,** the bins above 1.5 m/s stayed near zero. The 0-1.0 m/s bins gained a little root, but legal returns did not rise.
- **The kill counts** (the standing rule: whatever its cause, the measurement is sound). Stage 5G: 5 of 6 runs used, 1 kill in a row.
