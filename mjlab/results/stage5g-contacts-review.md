# Review round 16: two pre-launch fails on the feed side; measure the shots first (2026-10-20)

Brief: E6 on the robot's own mirrored returns failed its pre-launch check. On E3 zero-shot, 52 % of goals were above 1.5 m/s, falls were 7.1 % per feed and legal returns 5.6 %. Before that, the walkable contact had also failed. The robot's shots land short (3.4-3.5 m against the 4.7-5.7 m box) and wide (|y| 1.3-1.4 m against <= 1).

## Correction check (5 of 5)

- **The fail is sound,** and the own-ball setup is right:
  - `mirror_ball_states` is a proper 180-degree rotation, with spin as an axial vector;
  - replayed feeds are in the rally phase;
  - the start box is the parent's own.
- **Caveats** (none changes the verdict):
  - the 404 feeds with no planned goal inflate falls per feed (RL, coach, architecture), so falls should be reported on planned feeds only;
  - the partner starts in the start box rather than near its last contact (motion, experiment design);
  - some of those goals may be cut off at the 1.8 s horizon (architecture: raise it to about 2.3 s and report the found rate; recorded, not changed here);
  - the "speed error 4-10 %" item measures magnitude only; paddle-velocity direction has never been measured (architecture).
- **D-126's order was wrong** (RL, experiment design, coach, motion). The own balls are short and wide *because* the robot's aim is off, so training the receiver on them treats a symptom of the hitter. Fixing the shots fixes both sides of the rally; that is the keep-alive box's design intent.

## Decisions

1. **(a) first, evaluation only, no run used** (5 of 5). E3 on court feeds (E5 task), development seed 4216507. Each first contact's landing error splits into:
   - **the planner gap:** the commanded paddle state (n*, v*) put through the simulator's own impact model, with the real incoming ball, its spin and the paddle friction, then flown with spin, against the target;
   - **the controller gap:** the realized shot against that commanded-state shot.

   Also reported: the face-normal error, the paddle-velocity error (size and direction), the contact offset from the face centre, and the incoming- and outgoing-spin parts.
   - Code: `picklebot_mj/contact_check.py`, `stage2_eval.py --record-contacts`, `scripts/h5g_contacts.sh`.
   - Zero-point test (architecture): from exact inputs, the impact model reproduces the planned ball and lands on the target within 2 cm (`test_contact_decomposition_reproduces_the_plan_from_exact_inputs`).
2. **Pre-registered rule:** the larger of the mean landing-x gaps picks the fix.
   - **Planner larger:** (c), an impact-model fix or calibration, read zero-shot (no run). It passes if more landings fall in the box than in (a)'s read, legal returns are >= 15.24 % and falls per feed <= 2.5 %. Then the own returns are re-recorded and the D-126 check rerun unchanged (experiment design, coach).
   - **Controller larger:** E6 = (b), the face factor tightened (the 0.5 floor removed, mirroring D-121's linear0; motion), on court feeds (E5 task), parent E3, entropy 0.001.
     - **Pre-launch:** a reward-ranking test (an aligned face > a misaligned face > a miss > a fall).
     - **Kill at about 30 %:**
       - legal returns <= 15.24 %;
       - falls per feed > 2.5 %;
       - bank paddle p90 > 0.20 m or speed error > 20 %;
       - median face error not below E3's (motion, coach).
   - **Both under 0.3 m:** a landing reward.
3. **No new stage now** (5 of 5). Stage 5G's last run goes on the chosen fix. The D-entry for a new stage of at most 4 runs comes after that run's panel round.
