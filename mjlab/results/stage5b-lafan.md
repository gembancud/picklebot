# Stage 5B: LAFAN1 footwork clips retargeted to the paddle G1 (2026-10-08, D-047)

**Source:** `lafan1.zip` from Ubisoft's official GitHub (144 MB, 77 BVH files, 30 fps, CC BY-NC-ND 4.0). It and everything derived from it stay in the git-ignored `artifacts/motion/` (non-commercial, confirmed by the user).

**Used:** the locomotion files, 27 in all: walk1–4, run1–2, sprint1, jumps1, fightAndSports1, multipleActions1. Not used: aiming, dance, falls, ground, fight, obstacles, pushes.

## Pipeline (`scripts/motion/lafan_retarget.py`)
- **Mapping and scaling:** GMR's own LAFAN1 → G1 config and LAFAN1 loader, unchanged.
- **Shared with the tennis pipeline:**
  - IK on GMR's G1 carrying the paddle G1's capsules and paddle;
  - self-collision avoidance;
  - warm start at the human pose;
  - feet grounded;
  - the same checks and acceptance filter (median error ≤ 8 cm, 95th percentile ≤ 20 cm).
- **Error measure:** taken on bodies whose origin is at the human joint they follow: pelvis, knees, ankles, elbows, wrists.
- **Paddle:** no orientation target (the paddle is carried). The clips stay at 30 fps.
- **Test:** `tests/test_lafan_retarget.py` (GMR venv) checks a walk clip for accuracy, grounding, no foot skating (< 5 cm/s) and the CSV layout.

## Results (`artifacts/motion/lafan-g1`)
- **Acceptance:** all 27 clips accepted, 104 min. Median error 4.3–8.0 cm (walk4: 8.0 cm, at the limit); 95th percentile 8–17 cm.
- **Feet:** stay planted. Median skate is 0.6–1.7 cm/s on most clips, up to 17 cm/s on walk4.
- **Joint limits** (robot range, not mapping errors):
  - the G1 waist pitch (±30°) is at its limit in 42 % of frames on average, because people lean the trunk further when moving;
  - ankle roll is at its limit in 18–19 %.

### Tracking-set selection (`tracking_set.json`)
Clips where a waist joint sits at its limit in more than 90 % of frames are left out: walk3 subjects 3 and 5, and walk4 subject 1 (93–98 %). That is a persistent crouched or leaning walking style, not footwork.

**A 50 % cutoff was tried first.** It would also have dropped running, sprinting, jumping and the sport clips (55–74 %), which just lean more than the robot allows. So the cutoff targets the pinned-posture outliers only. Kept: 24 clips, 93 min.

## Clips for the user
`artifacts/videos/stage5b/lafan-{walk1_subject1,run1_subject2,jumps1_subject1,fightAndSports1_subject1}-side.mp4` (8 s each).

## Next
The tracking set becomes 90 tennis clips (42 min) + 24 LAFAN1 clips (93 min).
- **Sampling balance:** the LAFAN1 clips are longer, so balancing sampling between the two sources is a run setting, decided before launch.
- **Timing:** this is a new variable for the tracking teacher. It joins after the current chain (tracking-05) is evaluated, as a rule-8 follow-up or the next run. It is not mixed into a chained run.
