# Stage 5B: self-penetration in the retargeted clips, and the fix (2026-10-07)

**Trigger:** the user saw clipping in the first retarget videos.

**Cause:**
- The retargeting IK had no collision avoidance.
- The human's arms pass closer to the body, and to each other, than the bulkier G1 links allow: the left hand on the grip, hands against the hips, elbows into the torso.
- The paddle has no collision geometry (contype 0; ball contact is analytic, D-039).

## Measurement (`scripts/motion/penetration_check.py`)
- **Method:** kinematic replay on the paddle G1. Contacts come from MuJoCo between the G1's own collision capsules, plus the paddle face made collidable for the check.
- **Pairs ignored:** the model's own exclusions (parent-child, pelvis-hip, elbow-wrist) and the paddle against its holding hand.
- **Threshold:** an overlap counts when it is deeper than 1 cm.
- **Sets:** v3 = 92 accepted clips without avoidance, v4 = 91 accepted clips with it.
- **Raw data:** `stage5b-penetration.json` (v3) and `stage5b-penetration-v4.json`.

| Stroke | Frames with overlap, v3 → v4 | Worst depth, v3 → v4 | Main v3 pairs |
|---|---:|---:|---|
| backhand | 40.8 % → **1.5 %** | 9.3 → 3.8 cm | hand on hand / wrist (two-handed grip), hand into hip |
| backhand volley | 19.0 % → **0.1 %** | 9.5 → 2.9 cm | hand into hip / thigh |
| forehand | 20.0 % → **0.5 %** | 9.5 → 6.8 cm | left hand on the right hand (ready position) |
| forehand volley | 21.5 % → **0.1 %** | 9.5 → 2.3 cm | hand on hand |
| serve | 13.0 % → **1.4 %** | 12.5 → 6.6 cm | arm into torso, hand into hip |
| smash | 20.9 % → **0.9 %** | 9.6 → 5.7 cm | hand on hand, hand into hip |

Paddle against body was never above 1 cm, even in v3.

## Fix (`scripts/motion/tennis_retarget.py`)
- **IK self-collision avoidance** with mink's `CollisionAvoidanceLimit` (10 mm minimum distance, 5 cm detection). It covers:
  - each forearm and hand against the pelvis, torso, hips and thighs;
  - left forearm and hand against right forearm and hand;
  - the paddle against the body and the left arm.
- **Same shapes as the physics.** Collision avoidance on GMR's own mesh collisions barely helped, because the meshes are slimmer than the capsules used in training: hand-on-hand stayed at 7 cm. So GMR's G1 is rebuilt with:
  - its mesh collisions switched off;
  - the paddle G1's capsules and paddle face (`export_collision_geoms.py`; body frames agree to within 0.006 mm);
  - the paddle G1's exclusions.
- **Cost:**
  - Tracking error is unchanged (median 2.4–3.4 cm per stroke).
  - 91 of 99 clips are accepted, against 92 before (one serve fewer).
  - The wrists now take up some avoidance: wrist pitch is at a limit in 11–18 % of frames for backhands and smashes.
- **Remaining:** single frames in the fastest swings (forehand, serve, smash) still reach 5–7 cm, because the per-frame IK cannot keep up there. Physics will settle these in tracking.

## Carried into the tracking teacher
The tracking task must keep the paddle G1's self-collision on: capsules with the same exclusions, plus a collidable paddle face against the body and left arm. Infeasible frames then cost tracking error instead of passing through.

**Tests:** `tests/test_tennis_retarget.py` has 4 tests (GMR venv), including one that the IK model carries the capsules and paddle and that a retargeted clip stays below 2 % of frames with overlap deeper than 2 cm.

**Clips:** `artifacts/videos/stage5b/retarget-v4-*-side.mp4`. Same player and windows as the first set.
