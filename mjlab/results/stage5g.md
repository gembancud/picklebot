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
| E1 | s5g-e1-timed | Timed command and rewards (`Picklebot-Latent-TimedReach-G1`): swing guide, plus a one-shot contact reward at t* (weight 5 per goal); 4,096 envs; training seed 74 | reach-06/model_34700, widened | iteration 39,700 (5,000 more), or the last checkpoint before the 7,000 s cap | |

- **E1 early kill (D-118)** at model_36200 (seed 4216101, 256 envs): falls above 5 %, or a median paddle error above 0.25 m.
  - **The parent fails both today** (15.2 %, 0.32 m), so E1 must improve on both by 30 % of the run.
- **E1 gate (D-118):**
  - median paddle error <= 0.08 m, p90 <= 0.20 m;
  - timing within 50 ms >= 80 %;
  - median speed error <= 20 %;
  - falls <= 2 %;
  - root within 0.25 m >= 90 %.

  Endpoint seed 4216110.
