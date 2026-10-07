# Stage 5 Drill 3 review videos (`student-drill3-d3b/model_6500`, provisional student, D-046)

Date: 2026-10-07. Settings:
- real balls, no stance hint (deployment-like), move/ghost episodes off;
- dev seed 4,200,250, 10 s per clip, env 0 of 2, side and behind views.

Clips: `mjlab/artifacts/videos/stage5/sd3b-{easy_forehand,reach_forehand,reach_backhand,reach_short,reach_deep}-{side,behind}.mp4` (local; all ten sent to the user). Contact sheets (`sheet-sd3b-*.png`) show one still every 0.5 s.

| Family | What the robot does | Matches the gate numbers? |
|---|---|---|
| easy_forehand (success) | Compact forehand from a ready stance, small adjustment steps, returns to its spot. | Yes (96 % legal) |
| reach_forehand (success, move → swing) | Shuffle steps to the right, plants and swings beside the body, then steps back toward the spot. It does move first and then swing. | Yes (96 % legal) |
| reach_backhand (miss) | Barely travels left. It turns and reaches across the body with the right-hand paddle, late, and often brushes or misses the ball. No crossover step. | Yes (22 % legal, 36 % contact) |
| reach_short (miss) | Stays near its start depth. It swings while the ball bounces short in front, with no forward run. | Yes (2 % legal) |
| reach_deep (miss) | **New compared with S-D2c:** it backs up to and past the baseline. It still swings forward while the ball is already level with or behind it, so contact is rare. | Yes (2 % legal) |

## What changed since the S-D2c review
- **Moving back for deep balls:** the robot now retreats with the ball (the v2 hint and the extended spot box), but its timing on high-bouncing balls is wrong.
- **Stance and contact on the Stage 4 families are clean.**
- **Unchanged:** no forward run for short balls, no crossover to the backhand side, upright and stiff balance. This is the movement-quality gap Stage 5B (human motion priors) targets.

## Before/after reference for Stage 5B
These clips are the "before" for Stage 5B's side-by-side style comparison: same families, views and seed settings.
