# Review round 15: the walkable contact failed its check; E6 trains on the robot's own returns (2026-10-20)

Brief: E6's pre-launch check failed. On E3 zero-shot, the walkable contact (D-125) left 29 % of live goals above 1.5 m/s (the line is 21 %), with legal returns at 15.0 %. No E6 was run.

## Correction check (5 of 5)

- **The fail is sound,** and so is `predict_contact_walkable`:
  - the first interception is always a candidate;
  - later points come only after the capture and inside [0.50, 1.1] m;
  - a qualifying choice is latched;
  - otherwise the point needing the least walking.
- **Caveats** (none changes the verdict):
  - required speed ignores starting from rest and reaction delay, so the cap is lenient (motion, experiment design, architecture);
  - the 1.8 s horizon leaves deep feeds little window (architecture);
  - later points are low on the descent, and falls per goal doubled in the 1.0-1.5 m/s bin (motion).
- **The premise was wrong, not the code:** the fast court families have no walkable point in the bank's heights, and a planner change cannot fix physics.
- **Stage 5G is still at 5 of 6 runs,** with 1 kill in a row.

## Decisions

1. **E6 re-plans onto the rally's ball distribution** (option c: 4 of 5 for the direction; coach, motion, RL, experiment design, with architecture also choosing c). Reasons:
   - a two-robot rally never sends reach, cross, fast or deep feeds;
   - those families dilute every update and cause most falls;
   - the video bar needs about 56 % legal per shot.
2. **How:** no majority, so the least new code wins. Every feed is one of **E3's own legal returns, mirrored**, through the ball term's existing `replay_file` (motion, RL).
   - **Recording:** on a fresh development seed (4216504; the readiness seeds are never used).
   - **Why these balls:** they are the short (about 3.4 m), wide (about 1.3 m) balls a partner sends today (the coach's reason for a widened rally family).
   - **Other options:** keep-alive-box synthetic feeds (architecture; experiment design's fallback) and training in pair mode (experiment design) are recorded. Architecture's caution that the file goes stale as aim improves is noted. RL: refresh the file from newer checkpoints only after two runs show drift.
   - **The rest:** task `Picklebot-Latent-TimedBall-Own-G1`, E5's planner, and the D-125 entropy correction (0.001). The test `test_e6_own_changes_only_the_feeds_and_the_entropy_correction` checks that nothing else changes.
3. **Parent: E3's endpoint, model_39699.**
   - **Pre-launch check:** E3 zero-shot on the E6 task (seed 4216505). It passes only with >= 1,000 feeds, live goals above 1.5 m/s <= 21 % (3 of 5) and falls per feed <= 2.5 % (5 of 5). Its legal-return rate is the kill line (4 of 5).
   - **Kill lines at about 30 %:**
     - legal returns <= that rate;
     - falls per feed > 2.5 %;
     - on the bank: paddle p90 > 0.20 m or speed error > 20 %.
4. **The endpoint report:**
   - legal returns per shot on own balls, with the Wilson interval;
   - the court battery (retention of the hard families, against E3's 15.0-15.2 %);
   - an R4 pair-mode smoke test with P(4+) on development seeds;
   - action std, the speed bins and the landing rates.
5. **After E6:** a panel round, then a D-entry for a new stage of at most 4 runs. It states the gap plainly:
   - about 56 % legal per shot is needed, against about 15 % on court feeds and 6-8 % on own balls (R2, Stage 5F);
   - pair-mode P(4+) becomes the stage's primary readout (architecture, experiment design).

   The stage after that is shot quality, the face factor and the landing target (coach, motion, RL), on this distribution.
