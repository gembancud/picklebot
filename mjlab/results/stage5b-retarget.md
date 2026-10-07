# Stage 5B: Tennis-MoCap retargeted to the paddle G1 (2026-10-07)

Downloads approved in D-046:
- **Tennis-MoCap:** 100 BVH files, 276 MB on disk.
- **GMR:** 1.5 GB on disk, not the ~276 MB the GitHub API reported (robot meshes and media). It is installed in its own venv, `~/envs/gmr` (5.9 GB, because SMPL-X pulls in PyTorch), so mjlab's MuJoCo 3.3 environment is untouched. `pytest` was added there for the tests.

Everything sits under the git-ignored `mjlab/artifacts/motion/`.

**LAFAN1 G1 CSVs were not downloaded.** Unitree's Hugging Face dataset now returns 401 without a login, and only a third-party mirror is public. Signing in is the user's step, and the mirror needs the user's say-so.

## Pipeline (`scripts/motion/`)
### `tennis_retarget.py` (GMR venv)
GMR has no mapping for the OptiTrack Arena skeleton (18 joints, no toes or fingers), so the IK config is built from the two rest poses:
- **Rotation offsets** = `Q0⁻¹·H·R_tpose`. They map the human T-pose (all BVH rotations zero) onto an explicit G1 T-pose: shoulders rolled out 90° and elbows +90°. The G1's zero pose has the forearm pointing forward. A first version aligned bone directions instead; it left the forearm twist ambiguous and bent the elbows by 72°.
- **Positions go to the links at the joints:** `hip_roll_link`, `shoulder_roll_link`, `elbow_link` and `wrist_roll_link`.
  - Rotations go to the thigh and upper-arm yaw links through `~rot` aliases (GMR allows one task per human bone).
  - The pelvis target is raised 13 cm above the hip centre.
  - Mapping the hips and shoulders to the yaw links had given constant 27 cm and 14 cm errors.
- **Per-bone scales** = robot / human distance from the hip centre, in T-pose. GMR's LAFAN1 factors shrank the arms well short of the G1's reach.
- **Hands are position-only.** The Arena hand rest orientation points down rather than along the forearm, which pinned the wrist joints at their limits 90 % of the time. Wrist angles are therefore not retargeted; the paddle face will come from the task reward.
- **Warm start:** the pelvis is placed at the human's pose and heading, the arms in T-pose, and the IK settles for 50 iterations on frame 0. Starting from the G1 zero pose facing +x trapped 44 of 93 clips in a local minimum: a shoulder pinned at its limits for the whole clip, 15–20 cm median error.
- **Fixes to the tools:**
  - **mink 1.3 shim.** GMR passes its limits list in the slot mink 1.3 now uses for `safety_break`, so float round-off at a joint limit crashed clips.
  - **BVH input.** Space-padded frame lines are normalised. Frame lines beyond the `Frames:` header are dropped (2 files have them).
- **Output:** 100 Hz → 50 Hz, with the feet grounded (lowest ankle = standing ankle height). Each clip produces:
  - a CSV in mjlab's `csv_to_npz` layout (base xyz, quat xyzw, 29 joints);
  - a check JSON;
  - the scaled human joints, for overlays.

### Other scripts
- `rest_check.py`: the T-pose sanity check. The G1 lands on its T-pose within 1° (wrists within 5°).
- `retarget_summary.py`: per-stroke table and `accepted.json`.
  - **Acceptance:** median position error ≤ 8 cm and 95th percentile ≤ 20 cm over the position-tracked bodies.
- `render_retarget.py` and `render_strokes.sh`: kinematic playback on the paddle G1, with the human joints as red dots.
- **Tests:** `tests/test_tennis_retarget.py` covers the loader, rest pose → T-pose, the CSV layout, grounding and hand-only position tracking. 3 pass in the GMR venv; the file skips in the main venv.

## Results (`artifacts/motion/retargeted-v3`, 99 labelled clips)
| Stroke | Clips | Accepted | Accepted minutes | Median pos. error | Joints most often at a limit (accepted) |
|---|---:|---:|---:|---:|---|
| serve | 16 | 11 | 5.4 | 3.4 cm | right shoulder yaw 16 %, waist pitch 13 %, right ankle roll 11 % |
| smash | 16 | 15 | 7.2 | 2.8 cm | right ankle roll 20 %, shoulder yaw 15 % |
| forehand | 18 | 18 | 7.4 | 2.6 cm | left ankle roll 26 %, right shoulder yaw 15 % |
| forehand volley | 16 | 16 | 7.9 | 2.5 cm | ankle roll 12–16 % |
| backhand | 18 | 18 | 7.7 | 2.7 cm | left ankle roll 25 %, right shoulder yaw 13 % |
| backhand volley | 15 | 14 | 7.0 | 2.4 cm | ankle roll 15–20 % |
| **total** | **99** | **92** | **42.7** | | |

`jangel_VReves` has no row in `labels.csv` and is left out.

- **Handedness:** every forehand, serve and smash is right-handed, matching the paddle hand.
- **Backhands:** 14 of 18 have the faster left hand, i.e. two-handed backhands. The G1 holds the paddle in one hand, so these teach two-handed body mechanics.
- **Feet:** grounded. Median foot-skate while planted is 5–7 cm/s.
- **Paddle path:** the right hand reaches 3.2–6.6 m/s (99th percentile) on the strokes.

### Known limits (robot range, not mapping errors)
- **G1 ankle roll is ±15°.** It is at a limit in 12–26 % of frames in wide or lunging stances.
- **Right shoulder yaw is at a limit in 13–16 % of frames,** in the take-back and serve.
- **Wrist orientation is not retargeted** (see above).
- **Kinematic only.** Dynamic feasibility is the tracking teacher's job.

## Clips for the user
`artifacts/videos/stage5b/retarget-{forehand,backhand,forehand_volley,backhand_volley,serve,smash}-side.mp4`. High-level player `jgacosta`, 4 s around the fastest swing, side view, human joints as red dots beside the robot.

## Next
**Tracking teacher.** Convert the accepted CSVs to mjlab npz (`csv_to_npz.py`), then train `Mjlab-Tracking-Flat-Unitree-G1`-style tracking on the paddle G1, chained ≤ 2 h runs (rule 9).
