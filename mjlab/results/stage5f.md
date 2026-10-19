# Stage 5F: a latency-robust stack, cheapest fixes first (D-108..D-111)

The plan is in docs/MJLAB_PIVOT.md (Stage 5F section); the review is in `stage5f-plan-review.md`; the numbers frozen before step 0 are in `stage5f-thresholds.md`; seeds are in `seed-ledger.json`.

## Step 0 (no training)

### Ball-delay compensation, offline (`scripts/diag/ball_lag_error.py`, dev seed 4210010, 64 feeds per family, 8 samples each)

Position error of the ball estimate against the truth, median (p90), in cm:

| Ball delay | Raw (what the 5E executors saw) | Spin-blind forward prediction |
|---|---|---|
| 0 ms (noise only) | 4.5-4.7 (7.2-7.8) | same |
| 20 ms | 9.0-15.7 (12.9-20.4) | **4.3-4.9 (7.1-7.8)** |
| 40 ms | 16.4-30.9 (21.6-36.2) | **4.4-4.8 (7.4-7.9)** |

- **Prediction brings the error back to the noise floor** for every drill v2 family, topspin and backspin included. Over 20-40 ms, the planner's spin-blind model loses nothing measurable.
- **The fast families suffer most from raw delay:** fast at 30.9 cm, low at 28.9 cm and reach_deep at 27.0 cm at 40 ms.
- **Caveat:** this assumes the measurement's age is known, as it is with timestamps. A misestimated-age check comes with the compensator's tests.

### Controller tracking under command delay (`scripts/h5f_step0.sh` A-C; dev seeds 4210000-4210001; 2 repeats; per-stroke units)

Tracking success by source (paired, same seed):

| Controller | Delay | Tennis | LAFAN1 | Mirrored LAFAN1 | Footwork | All |
|---|---|---|---|---|---|---|
| H0 (tracking-20-decay/model_60800) | 0 ms | 93.5 | 88.7 | 83.0 | 100 | 90.7 |
| H0 | 10 ms | 92.1 | 86.3 | 81.2 | 100 | 89.3 |
| H0 | 20 ms | 85.7 | 80.2 | 74.1 | 99.3 | 84.1 |
| latent-07 (encoder tracking) | 0 ms | 93.5 | 89.0 | 82.8 | 100 | 90.8 |
| latent-07 | 10 ms | 91.8 | 86.4 | 80.5 | 100 | 89.0 |
| latent-07 | 20 ms | 86.0 | 79.2 | 73.8 | 99.7 | 83.9 |
| latent-07 on tennis + 100STYLE | 0 / 20 ms | 92.5 / 85.7 | | | 100STYLE 100 / 100 | |

- **Triggers (D-111):**
  - **H0 delay fine-tune: triggered.** At 20 ms H0 is 7.8 / 8.5 / 8.9 points down for tennis, LAFAN1 and mirrored LAFAN1 (threshold 2).
  - **H1 decoder re-distillation: triggered** by condition (a). latent-07 is 7.5 / 9.8 / 9.0 points down.
- **Reading:** H0 and latent-07 lose almost exactly the same amount. H1's delay fragility is inherited from its teacher, so the H0 fine-tune has to come first. A decoder trained to imitate a delay-fragile H0 could not become robust.
- **100STYLE windows stay at 100 % under delay.** The slow walking clips are not the problem.

### Executor-driven move drill, walking teacher and drill v2 under delay (`scripts/h5f_step0.sh` D-F; seeds 4210002-4210004)

Move drill (Stage 5D run 1, model_1800; executor drives latent-07). Arrival per direction (9 sectors) and robot falls per episode:

| Policy | Command delay | Arrival, lowest sector | Arrival, highest sector | Falls / episode |
|---|---|---|---|---|
| s5d-01 executor | 0 ms | 99.6 % | 99.95 % | 0.07 % |
| s5d-01 executor | 10 ms | 99.0 % | 99.95 % | 0.78 % |
| s5d-01 executor | 20 ms | **0.0 %** | 10.3 % | **58.6 %** |
| walking teacher (teacher-move-01/model_15900) | 0 ms | 99.2 % | 100 % | 0 % |
| walking teacher | 20 ms | 99.3 % | 100 % | 3.7 % |

- **H1 trigger (b): fired.** At 20 ms the executor-driven move drill is far below 90 % arrival in every direction and falls far above 1 %. Trigger (a) had already fired.
- **Walking-teacher trigger: not fired.** Its trigger is arrival below 90 % at 20 ms, and arrival stays at 99 % or more. Its falls rise to 3.7 % per episode. This is recorded, not acted on: the trigger was frozen on arrival only (D-111), and the walking teacher is not in the Stage 5F stack unless a later step uses it.
- **There is a cliff between 10 and 20 ms.** At 10 ms the executor stack keeps arrival at 99 % or more; at 20 ms it almost always falls. The tracking loss at 20 ms is only about 8 points per source, so the collapse comes from the executor plus controller loop, not from tracking alone.

Drill v2 (Stage 5D run 1), ball delay / command delay:

| Ball / command delay | Per-shot p | Neutral | Moderate | Extreme | P(rally >= 10) |
|---|---|---|---|---|---|
| 0 / 0 ms | 0.741 [0.736, 0.746] | 0.806 | 0.649 | 0.613 | 6.1 % |
| 0 / 20 ms | 0.149 | 0.184 | 0.110 | 0.066 | 0.0 % |
| 40 / 0 ms | 0.414 [0.408, 0.420] | 0.445 | 0.355 | 0.384 | 0.03 % |
| 40 / 20 ms | 0.067 [0.064, 0.070] | 0.077 | 0.055 | 0.045 | 0.0 % |

- **Both delays hurt, and command delay hurts more.** A 20 ms command delay alone costs 59 points of per-shot p; a 40 ms ball delay alone (no prediction) costs 33 points; together they leave 0.067. Ball prediction already removes the ball error in offline tests (above), so command delay is the main open problem.
- The drill v2 "falls per episode" field reads about 1.0 in both cells, because a drill v2 episode runs until the robot falls or the episode times out. Falls are gated on the court battery, not on this field.

### Design checks (step 0)

- **Compensator speed** (`scripts/diag/bench_compensator.py`, seed 4210011): 3.45 ms per control step at 12,288 envs (8 substeps, half the envs clean), measured while run C1 trained on the same GPU. That is small next to an environment step, so the compensator stays per-step.
- **4 vs 8 history steps** (`scripts/diag/history_probe.py`, seed 4210012; rule written before the run): Stage 5D run 1 on the training-latency task, one lag pair per episode. A ridge probe reads the episode's command lag and ball lag from a K-step window of what the actor would see (issued actions, joint positions and velocities, ball estimate), trained on 70 % of the envs and scored on the rest. **Rule:** take the smallest K in {1, 2, 4, 8} within 1 point of K = 8 for both lags; adopt 4 (the D-108 default) unless 4 misses that bar, then 8. Result: pending (runs after C1, to keep C1's GPU time clean).

## Runs

| # | Run | Change (written before launch) | From | Endpoint | Result |
|---|---|---|---|---|---|
| C1 | s5f-c1-h0delay | H0 delay fine-tune (triggered, D-111): per-episode command delay, 30 % clean, otherwise 5-25 ms; the lag shown to the critic only (one trailing critic input, zero-initialised). Same task, motion set and settings as tracking-20-decay (fixed learning rate 1e-5, 4,096 envs, training seed 71). | tracking-20-decay/model_60800 | iteration 63,800 or the last checkpoint before the 7,000 s cap | |

- **C1 early kill** (D-111): at iteration 61,700, clean tracking with 1 repeat on seed 4210500. The run is killed if any source is more than 3 points below the parent on the same protocol.
- **C1 gate** (D-111): per source and per tennis stroke type, at 0 / 10 / 20 ms, >= the old H0 at 0 ms minus 2 points. Seed 4210501, 2 repeats, paired.
