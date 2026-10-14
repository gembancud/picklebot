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
