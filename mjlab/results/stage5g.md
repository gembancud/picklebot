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
| E3 | s5g-e3-timed-v3 | The contact reward's speed floor removed: fv = clamp(1 - |dv|/|v*|, 0, 1) (D-121); nothing else | reach-06/model_34700, widened | iteration 39,700, or the last checkpoint before the 7,000 s cap | |

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
