# Stage 5F: numeric triggers, sub-step gates and early-kill rules (D-111, frozen before step 0)

Written before any Stage 5F measurement exists. Changing any number here needs a new decision entry.

## Notation

- **Command delay:** a fixed lag in physics steps (5 ms each). So 0 / 10 / 20 ms = 0 / 2 / 4 steps.
- **Ball delay:** a fixed lag in control steps (20 ms each). So 0 / 20 / 40 ms = 0 / 1 / 2 steps.
- **Grid cell:** written "ball / command", e.g. "40 / 20". In every grid cell the ball-state noise is on, as in the frozen D-101 drill v2 evaluation.
- **The "clean" condition:** no delay and no noise. It is the condition of the D-101 Stage 5C retention battery.
- **Tracking success:** `tracking_eval.py --per-stroke`, which counts tennis stroke segments and 4 s windows of the other sources. Each controller is measured with 2 repeats, on the same seeds as its comparison.
- **"Points":** percentage points of a rate, comparing paired measurements on the same seeds.

## Step 0 triggers (each decides whether a controller sub-step runs)

| Sub-step | Runs if |
|---|---|
| H0 delay fine-tune | H0 tracking success at command 20 ms is more than 2 points below H0 at 0 ms, for any source (tennis, LAFAN1, mirrored LAFAN1, footwork) or for any tennis stroke type. |
| H1 decoder re-distillation | **Either** (a) latent-07 tracking (encoder mode) at command 20 ms is more than 2 points below 0 ms for any source, **or** (b) the executor-driven move drill (Stage 5D run 1 on latent-07, command 20 ms) has arrival below 90 % in any direction, or move-drill falls above 1 %. |
| Walking-teacher delay fine-tune | The flat walking teacher (`teacher-move-01/model_15900`) has arrival below 90 % in any direction at command 20 ms, **and** a later sub-step uses it (as a kickstart or DAgger target). If nothing uses it, it is reported only. |

## Sub-step gates (frozen now; each sub-step has at most 3 runs, and the controller has at most 6 in total)

**H0 gate,** at command 0, 10 and 20 ms, per source and per tennis stroke type:
- tracking success >= the old H0's success at 0 ms minus 2 points;
- the new H0 at 0 ms is also >= the old H0 at 0 ms minus 2 points.

**H1 gate (the new decoder),** with the encoder, prior and normaliser frozen:
1. **Tracking:** in encoder-tracking mode, per source, at 0 / 10 / 20 ms, >= latent-07's success at 0 ms minus 2 points. 100STYLE windows stay at 57/57.
2. **Zero-shot executor transfer:** Stage 5D run 1, on the new H1 with no retraining.
   - **Clean:**
     - court main >= 76.8 % and within 3 points of its latent-07 value;
     - arrival in every direction within 2 points of its latent-07 value;
     - move-drill falls <= 1 %;
     - Stage 5D rally P(rally >= 10) within 2 points of its latent-07 value.
   - **Command delay 20 ms (ball delay 0):** arrival >= 90 % in every direction; move-drill falls <= 1 %.
   - **Grid cell 40 / 20:** court main no more than 3 points below its latent-07 value in the same cell.
3. **Style:** the new H1 under Stage 5D run 1 scores style on the new reference <= latent-07's + 0.03.

Failing the H1 gate after its 3 runs fires the pre-registered exit (D-109 item 8).

## Early-kill rules (kill only; never extend or promote a run)

**At about 30 % of each run's iterations,** checked on the nearest saved checkpoint:
- **Executor runs:**
  - Drill v2, cell 40 / 20 (noisy spot), 256 envs, 30 s, one seed from the run's block. Kill if per-shot p is more than 5 points below the run's parent on the same protocol and seed.
  - Move drill, clean, 256 envs, 20 s. Kill if arrival is below 90 % in any direction.
- **Controller runs (H0, H1):** tracking success, clean, one repeat. Kill if it is more than 3 points below the parent for any source.

## Stage kill rules (fixed from run 0; per run, at its endpoint)

Fixed from run 0's values before run 1. The tolerances are written now:

| Measure | A run is killed if |
|---|---|
| Drill v2 per-shot p (frozen D-101 condition) | below the start point's run-0 value minus 3 points |
| Court main, clean | below 76.8 % |
| Court main, cell 40 / 20 | below the start point's run-0 value minus 3 points |
| Arrival, clean | below 90 % in any direction |
| Arrival, command 20 ms | below the start point's run-0 value minus 2 points, until the H1 sub-step has passed; below 90 % after it |
| Court falls, clean | above the start point's run-0 value plus 1 point |
| Court falls, cell 40 / 20 | above the start point's run-0 value plus 1 point |
| Style, new reference | above the start point's run-0 value plus 0.15 |

## Shot-item metrics (each run is judged on its stage metrics; these show whether the item did what it was meant to)

| Item | Metric |
|---|---|
| Ready position and split step | the share of feeds with stance width >= 0.35 m and both feet down at feed launch, and a pelvis dip >= 3 cm within ±0.25 s of the feed launch |
| Turn-and-go footwork | arrival and falls in the back, back-left and back-right directions (clean and at command 20 ms), plus the share of backward moves over 1 m with torso yaw >= 30° within 0.5 s |
| Stance spot plus time-to-contact | the median pelvis distance to the planner's stance spot at the first contact |
| Failure-weighted feeds | per-family p of the five weakest families in run 0 |
| Backspin teacher | backspin p, clean and in cell 40 / 20 |
| 100STYLE style reward | style on the new reference |

## Reporting (descriptive, not gating)

- **Every battery item** is also reported on the full grid (ball 0 / 20 / 40 × command 0 / 10 / 20) plus the extrapolation cell 60 / 30.
- **Breakdowns:** arrival and falls by direction; falls per 100 shots.
