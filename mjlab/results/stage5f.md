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

## Runs

| # | Run | Change (written before launch) | From | Endpoint | Result |
|---|---|---|---|---|---|
| C1 | s5f-c1-h0delay | H0 delay fine-tune (triggered, D-111): per-episode command delay, 30 % clean, otherwise 5-25 ms; the lag shown to the critic only (one trailing critic input, zero-initialised). Same task, motion set and settings as tracking-20-decay (fixed learning rate 1e-5, 4,096 envs, training seed 71). | tracking-20-decay/model_60800 | iteration 63,800 or the last checkpoint before the 7,000 s cap | |

- **C1 early kill** (D-111): at iteration 61,700, clean tracking with 1 repeat on seed 4210500. The run is killed if any source is more than 3 points below the parent on the same protocol.
- **C1 gate** (D-111): per source and per tennis stroke type, at 0 / 10 / 20 ms, >= the old H0 at 0 ms minus 2 points. Seed 4210501, 2 repeats, paired.
