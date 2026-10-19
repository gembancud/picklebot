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

Move drill (Stage 5D run 1, model_1800; executor drives latent-07). Arrival per direction (8 directions) and robot falls per episode:

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
- **4 vs 8 history steps** (`scripts/diag/history_probe.py`, seed 4210012; rule written before the run): Stage 5D run 1 on the training-latency task, one lag pair per episode. A ridge probe reads the episode's command lag and ball lag from a K-step window of what the actor would see (issued actions, joint positions and velocities, ball estimate), trained on 70 % of the envs and scored on the rest. **Rule:** take the smallest K in {1, 2, 4, 8} within 1 point of K = 8 for both lags; adopt 4 (the D-108 default) unless 4 misses that bar, then 8. Result: not run. Executor history is shelved under D-113, so the probe waits for a later sim-to-real stage.

## Runs

| # | Run | Change (written before launch) | From | Endpoint | Result |
|---|---|---|---|---|---|
| C1 | s5f-c1-h0delay | H0 delay fine-tune (triggered, D-111): per-episode command delay, 30 % clean, otherwise 5-25 ms; the lag shown to the critic only (one trailing critic input, zero-initialised). Same task, motion set and settings as tracking-20-decay (fixed learning rate 1e-5, 4,096 envs, training seed 71). | tracking-20-decay/model_60800 | iteration 63,800 or the last checkpoint before the 7,000 s cap | **Gate not met (D-111); archived (D-113).** Endpoint `s5f-c1b-h0delay/model_63600` (the 4,700 s cap hit at iteration 63,634; last checkpoint before it). See below. |

- **C1 early kill** (D-111): at iteration 61,700, clean tracking with 1 repeat on seed 4210500. The run is killed if any source is more than 3 points below the parent on the same protocol.
- **C1 gate** (D-111): per source and per tennis stroke type, at 0 / 10 / 20 ms, >= the old H0 at 0 ms minus 2 points. Seed 4210501, 2 repeats, paired.
- **C1 tooling fault (D-112):** the early evaluation of `model_61700` crashed (whole-checkpoint load; the delay-trained critic has one more input than the evaluation task), and the watcher read the missing file as a kill, stopping training at about iteration 61,720 after 2,231 s. Fixed (actor-only load); the same early check then **passes**: tennis 94.0 -> 94.8, LAFAN1 89.7 -> 90.8, mirrored LAFAN1 83.3 -> 85.2, footwork 100 -> 100 (parent -> C1, clean, 1 repeat, seed 4210500). Not a kill. C1 continues from `model_61700` to iteration 63,800 as `s5f-c1b-h0delay` with the 4,700 s it had left.

## Re-scope (D-113, 2026-10-19): the clean-simulator instrument

The user has no near-term physical-robot plan. After a fifth review round (round 6, `stage5f-delay-review.md`; 5 of 5 for taking delay out), D-113 moves the Stage 5F drill v2 gate item to grid cell 0/0 (no delay, ball noise on, noisy planner spot). **This loosens that item's instrument** (Stage 5D run 1: 0.306 on the D-101 condition, 0.741 on the new one). Every bar is unchanged. The with-delay bars are suspended for a later sim-to-real stage. The Stage 5E verdict stands. Every run also reports the D-101 figure and the 0/10 and 40/20 cells (never gating).

- **Battery:** `scripts/h5f_clean_eval.sh` (gate: drill v2 at 0/0 plus the clean Stage 5C battery; 8 gate items), summary `scripts/h5f_clean_summary.py`.
- **Budget:** C1 (with its continuation C1b) is run 1 of 15; 14 remain. C1 is gated and archived, not adopted.
- **Order:** run 0 on the new instrument (`scripts/h5f_run0.sh`), then run 2 = plain clean drill v2 PPO from Stage 5D run 1 (`scripts/h5f_run02.sh`), then the coach's order.

### Run C1 result (H0 delay fine-tune; gate D-111; seed 4210501, 2 repeats, paired with the old H0 at 0 ms)

Tracking success, per source:

| Source | Old H0, 0 ms (bar = this - 2) | C1, 0 ms | C1, 10 ms | C1, 20 ms | Old H0, 20 ms (step 0, seed 4210000) |
|---|---|---|---|---|---|
| Tennis | 93.9 | 93.5 | 92.3 | **88.9** | 85.7 |
| LAFAN1 | 89.7 | 89.8 | 89.0 | **85.1** | 80.2 |
| Mirrored LAFAN1 | 83.0 | 83.8 | 82.3 | **79.8** | 74.1 |
| Footwork | 100 | 100 | 100 | 100 | 99.3 |

- **Gate not met.**
  - At 20 ms every source except footwork is 3.1-5.0 points below the bar, and every tennis stroke type is 2.7-6.5 points below it.
  - At 10 ms backhand volley (-2.2) and smash (-2.4) fail.
  - At 0 ms forehand (-2.2) fails.
- **What C1 did achieve:** it roughly halved H0's 20 ms loss (tennis 7.8 -> 5.0 points, LAFAN1 8.5 -> 4.6, mirrored 8.9 -> 3.1) and kept clean tracking within 1 point overall.
- **Status (D-113):** archived as a sim-to-real asset. It does not enter the stack. Counted as run 1 of 15.

### Run 0 on the D-113 instrument (`scripts/h5f_run0.sh`)

| Executor | Drill v2 p, 0/0 noisy spot [95 % CI] | Neutral / moderate / extreme (Wilson low) | p, exact spot | p, no spot | P(rally >= 5 / >= 10), drill v2 | Court main | Court falls | Arrival (min) | Style new / old | D-101 figure (reported) | p at 0/10 / 40/20 (reported) | Move drill at 10 ms: arrival min / falls (reported) | Gate items |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Stage 5D run 1 (start; seeds 4210300-315) | **0.753** [0.748, 0.757] | 0.820 / 0.659 / 0.625 (0.815 / 0.649 / 0.611) | 0.750 | 0.766 | 0.240 / 0.070 | 78.6 % | 6.4 % | 99.5 % (back-left) | 4.263 / 4.220 | 0.307 | 0.606 / 0.065 | 98.8 % / 0.7 % | 3/8 |
| run 22 (seeds 4210320-335) | 0.618 [0.613, 0.622] | 0.657 / 0.571 / 0.524 (0.651 / 0.561 / 0.511) | 0.612 | 0.631 | 0.103 / 0.014 | 79.1 % | 3.2 % | 99.4 % (left) | 4.061 / 4.022 | 0.298 | 0.507 / 0.075 | 97.2 % / 0.9 % | 2/8 |
| Stage 5E run 3 (seeds 4210340-355) | 0.462 [0.457, 0.467] | 0.523 / 0.458 / 0.182 (0.517 / 0.448 / 0.171) | 0.463 | 0.480 | 0.029 / 0.001 | 41.1 % | 3.7 % | 69.0 % (back-right) | 3.877 / 3.857 | 0.585 | 0.539 / 0.303 | 55.3 % / 0.6 % | 0/8 |

- **Passing:** extreme floor, court main, arrival.
- **Failing:**
  - per-shot p, by 4.7 points;
  - the neutral floor (0.815 vs 0.92), the largest gap;
  - the moderate floor (0.649 vs 0.80);
  - falls (6.4 % vs 1 %);
  - style (4.263 vs 3.86).
- **The planner's spot does not help this executor.** With no spot, p is 1.3 points higher; the exact spot changes nothing. The Stage 5D executor was trained without a hint and plays from the ball alone.

**Stage kill rules for every run (D-113, from the start point's run 0):**
- drill v2 p (0/0) below **0.723**;
- court main below **76.8 %**;
- arrival below **90 %** in any direction;
- court falls above **7.4 %**;
- style (new reference) above **4.413**.
- **Comparators (descriptive).**
  - **Stage 5E run 3 is worse without delay than with it** (0.462 vs 0.585 on the D-101 condition). It specialised to latency, which confirms the round-6 reading.
  - **On the new instrument the start point leads both comparators by a wide margin:**
    - run 22 by 13.5 points;
    - Stage 5E run 3 by 29 points.
  - **Run 22 falls less than the start point** (3.2 % vs 6.4 %) and has the better style (4.06 vs 4.26).

## Run 2 (launched 2026-10-20 00:5x)

| # | Run | Change (written before launch) | From | Endpoint | Result |
|---|---|---|---|---|---|
| 2 | s5f-02-v2-clean | Plain PPO on drill v2 in the clean simulator (ball noise on, no delay; `Picklebot-Latent-Court-V2-Res-PPO-Clean-G1`), Stage 5E PPO settings (gamma 0.995, 50-update critic warm-up), 12,288 envs, training seed 73 | s5d-01-rally/model_1800 | iteration 2800, or the last checkpoint before the 7,000 s cap | |

- **Early kill at model_2100:**
  - drill v2 at 0/0, 256 envs, 30 s, seed 4211000: killed if more than 5 points below the parent on the same protocol;
  - move drill clean, seed 4211001: killed if arrival is below 90 %.
- **Endpoint:** `h5f_clean_eval.sh`, seeds 4211010-4211025.
