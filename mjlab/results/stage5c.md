# Stage 5C: full-court coverage (D-069, D-075)

Starting executor: `h4-25b-more/model_27700` (the Stage 5B gate). Budget: 30 training runs.

## Footwork: the agility walker
**Task** `Picklebot-Latent-Reach-Agility-G1`: the H3 E2 reach task with root targets 1-3 m away, uniform in angle and distance, one per 2 s (H3: within 1 m), plus paddle targets as before.

**Baseline** (reach-06, `stage5b-h4-reach-direction-diag-1p5m.json`): within 25 cm of a 1.5 m target in 2 s, forward 28 %, right 30 %, left 0 %, back 0 %.

**Criterion** (D-075): if after the walker runs left or back still reach less than 75 % of the mean of right and forward at 1.5 m, retrain the controller with mirrored LAFAN1 locomotion.

**Known quirk:** a reach command resampled at an episode reset reads the robot's pre-reset position, so the first 2 s window of an episode can have an offset target. This has been so since H3; it affects training only, since evaluations clear the tally after the reset.

| # | Run | Change (written before launch) | From | Endpoint | Left / right / forward / back within 25 cm at 1.5 m |
|---|---|---|---|---|---|
| 1 | s5c-01-agility | agility walker task (1-3 m targets) | reach-06/model_34700 | | |

## Court-wide drill (D-076; `Picklebot-Latent-Court-G1`)
- **Zones:** back / mid / front by the pelvis x at feed time. Court-wide start and recovery spots.
- **Six new families:** drop, lob, cross forehand and backhand, volley forehand and backhand. Each is fed only where valid.
- **Offline feed check** (`scripts/tune_court_feeds.py`, `artifacts/eval/court-feeds-v1.json`, 512 feeds per cell):
  - every Stage 4 family is valid from every zone (travel <= 0.5 m);
  - drop asks for 1.3-2.4 m forward (back/mid); lob for 1.1-2.0 m back (mid/front);
  - cross asks for 2.2-3.2 m sideways at up to 1.5 m/s;
  - volleys are 100 % hittable before the bounce;
  - drop and reach short from the front land beyond the net (excluded).
- **Kitchen rules from the feet;** volleys in rally phase; pre-bounce volley hints.
- **Zone-conditioned learning-progress curriculum.**

## Evaluation (`scripts/h5c_eval.sh`, `scripts/h5c_summary.py`)
1. **Court drill:** every family, court-wide starts, random court-wide recovery spots, no hint, 2048 envs x 24 s. Gives per (zone x family) legal, recovery and falls. The pooled legal rate is the **main metric**.
2. **Move-to-spot drill:** arrival per direction (8 sectors).
3. **Regression on the Stage 5B drill**, with exactly its 14 families (`--families drill5b`; "every" now also contains the court families). Compared with h4-25b's paired final evaluation.
4. **Style score.**

## Baseline: h4-25b on the court drill (dev seeds 4200600-603; `stage5c-baseline-h4-25b-*.json`)
- **Main metric 52.0 %.** 15 of 55 (zone x family) cells reach 75 %.
  - Stage 4 families: 73-85 % from the back and mid zones, 44-70 % from the front.
  - Drop 11-32 %, cross 14-40 %, lob 0 %, volleys 0-0.7 %, reach deep 0-45 %.
- **Move-to-spot arrival 0 % in every direction. Recovery 1.53 m. Falls 10.3 %. Style 3.88.**
- **Stage 5B regression check** (h4-25b against itself): within -2.6..+1.0 points, so the check is sound.

## Court-wide executor runs (`Picklebot-Latent-Court-G1`)
| # | Run | Change (written before launch) | From | Endpoint | Main metric (court pooled) | Style |
|---|---|---|---|---|---|---|
| 2 | s5c-02-court | court-wide drill (D-076) with the zone-conditioned curriculum | h4-25b/model_27700 | | | |

## Agility walker result: controller limit (D-077)
- **s5c-01-agility -> model_37300** (dev seed 4200610). Within 25 cm at 1.5 m in 2 s: forward 32 %, right 27 %, **left 0.1 %, back 0 %**.
  - Distance covered in 2 s: about 1.2 / 1.1 / 0.55 / 0.5 m.
  - At 2.5 m: 0 % in every direction.
  - The training curve was flat for the whole run.
- **D-075 criterion met:** retrain the controller.
- **Mirrored LAFAN1** (`scripts/motion/mirror_g1_csv.py`, `tests/test_mirror_g1.py`): 17 clips, 211,996 frames, `lafan-g1-mirror.npz`. Checked through forward kinematics: every left/right body pair mirrors the original within 1e-5 m (`artifacts/eval/check_mirror.py`).
- **Motion set** `tennis-lafan3.npz`: 90 tennis + 17 LAFAN1 + 17 mirrored clips, 549,350 frames. Envs sampled 50.5 / 24.2 / 25.3 % by source (task `Picklebot-Tracking-TennisLafan3-Huge-G1`).
