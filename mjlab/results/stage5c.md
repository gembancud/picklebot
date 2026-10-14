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
