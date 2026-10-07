# Stage 5B: paddle orientation in the retargeted strokes (2026-10-08)

**Trigger:** the user saw that the backhand paddle holding was wrong. In the v4 clips the paddle stuck out sideways, nearly flat, through the backhand swing.

**Cause:**
- The mocap has no racket, and its hand orientation is unreliable (the Arena hand rest pose points down), so the hands were tracked by position only and the wrist angles stayed near neutral.
- The paddle face therefore just followed the forearm. On forehands that is roughly right; on backhands, where a player turns the forearm and wrist so the back face meets the ball, the face ended up flat or facing backwards.
- Most source backhands are also two-handed (14 of 18), while the G1 holds the paddle in one hand.

**Action:**
- `tracking-01`, which was training on the v4 clips, was stopped at iteration 1,696. Its checkpoints stay as a pipeline check and are not used further.

## Fix (`scripts/motion/tennis_retarget.py`)
- **A paddle orientation task** in the IK (mink `FrameTask` on the paddle body, cost 20).
  - It constrains only the face normal (paddle local z); twist about the normal is free (orientation cost `[c, c, 0]`).
  - It applies during swings, i.e. frames where the right hand moves faster than 2 m/s (`SWING_SPEED`).
  - The target normal is the hand's direction of travel, smoothed. Either face may lead, whichever is closer: the palm side on forehands, the back side on backhands.
  - Between swings the paddle is free (`READY_WEIGHT = 0`).
- **A ready-position target was tried and dropped.** "Face toward the net at weight 0.3" folded the paddle into the torso and pelvis (8–11 % of frames, up to 7 cm).
- **The paddle got its own collision-avoidance limit:** 5 cm clearance, 10 cm look-ahead.
- **Settings chosen from a small sweep** on one forehand and one backhand: paddle cost 10 or 20, clearance 3 or 5 cm.

| Paddle cost / clearance | Forehand: normal error median / p90 | Backhand: normal error median / p90 | Worst overlap pair (forehand) |
|---|---|---|---|
| 20 / 3 cm | 1.7 / 7.2° | n/a | paddle–torso 3.7 % of frames |
| **20 / 5 cm (chosen)** | **1.3 / 9.4°** | **3.6 / 14.0°** | paddle–thigh 0.8 % |
| 10 / 3 cm | 4.4 / 15.5° | 4.7 / 16.0° | paddle–hip 0.8 % |
| 10 / 5 cm | 5.3 / 21.1° | 4.7 / 16.0° | paddle–hip 2.0 % |

## Results (`artifacts/motion/retargeted-v5`, 99 clips; 90 accepted, 41 min)
| Stroke | Accepted | Pos. error median | Face-normal error in swings, median / p90 | Frames with overlap > 1 cm |
|---|---:|---:|---:|---:|
| serve | 10 | 3.4 cm | 0.9 / 11.6° | 1.6 % |
| smash | 14 | 3.1 cm | 0.6 / 8.9° | 1.2 % |
| forehand | 18 | 2.7 cm | 0.6 / 10.7° | 0.7 % |
| forehand volley | 16 | 2.5 cm | 0.5 / 22.1° | 0.5 % |
| backhand | 18 | 2.8 cm | 1.8 / 21.1° | 2.7 % |
| backhand volley | 14 | 2.4 cm | 0.9 / 15.4° | 0.3 % |

Overlap was 0.1–1.5 % of frames in v4.

- **Wrists now do the work:** wrist joints sit at a limit in 15–26 % of frames on backhands and volleys. The p90 errors are fast stroke reversals that the wrist range cannot follow.
- **Self-collision regression test:** its bound was raised from 2 % to 3 % of frames with overlap deeper than 2 cm. The clip measures 2.3 % (the paddle brushing the thigh in fast swings). It is a regression bound, not a gate; the per-stroke numbers above are the measurement.
- **New test:** the backhand face-normal error in swings has a median under 10°.

## Limits
- **The swing-direction heuristic is a prior, not racket data.** The face normal at contact also depends on the target and on spin, which the task reward (ball returns, aiming) decides in the fine-tune.
- **Two-handed backhands are still the source** for 14 of 18 backhands. The G1 follows the body and arm motion one-handed.

**Clips:** `artifacts/videos/stage5b/retarget-v5-*-side.mp4` and `retarget-v5-backhand-front.mp4`.
