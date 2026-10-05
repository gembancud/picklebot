# Stage 5 review videos: F2 endpoint `footwork-f02/model_12000`

Date: 2026-10-06. Task `Picklebot-Footwork-G1`, dev seed 4,200,091, target A, 8 s per clip, env 0 of 2. Six families, behind and side views. Clips in `mjlab/artifacts/videos/stage5/f2-<family>-<view>.mp4` (local, sent to the user), stills every 25 frames alongside.

| Family | F2 legal (eval) | What the clips show |
|---|---:|---|
| easy_forehand | 82 % | Contact from about the start spot: lean and reach with small foot adjustments. |
| backhand | 81 % | Same, on the left side of the body. |
| reach_forehand | 74 % | Steps out to the right, crouched, paddle extended low to the right as the ball arrives. This is the one movement it learned. |
| reach_backhand | 0 % | **Stands upright at the start spot, paddle tucked on its right, while the ball bounces 1–2.5 m to its left and goes past.** No step toward it. |
| reach_short | 0 % | The short ball bounces twice in front of it; no forward movement. |
| reach_deep | 0 % | The lob bounces behind and is lost; no backward movement. |

**Consistent with the diagnosis in `stage5-run-f2.md`:** a single learned lean-and-step-right, and no movement in other directions. This motivated the movement drills (D-041). The clips are the before-drills reference for Drill 1's videos.
