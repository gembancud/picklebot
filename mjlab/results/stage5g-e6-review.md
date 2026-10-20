# Review round 14: E5 killed; E6 = the walkable contact, with the entropy correction (2026-10-20)

Brief: the E5 kill at model_40200 (legal returns 14.6 %, no gain; bank paddle p90 0.28 m). Also improved: falls per feed 0.58 % and bank timing 0.869. Action std grew from 1.05 to 1.19.

## Correction check

- **The kill is sound and counts** (5 of 5).
  - Experiment design notes that the 15.9 % line came from the old adapter and sat above the parent's own 15.24 % on the E5 task. That made the line slightly strict, but the verdict does not change, since E5 was below the parent too.
  - **From now on, each line comes from the parent's figure on the same task and adapter.**
- **Implementation defect (3 of 5: RL, motion, architecture):** E3 and E5 took the tracking PPO default, entropy_coef 0.005, from `_latent_reach_rl_cfg`.
  - Every ball-PPO run since H4 used 0.001 (D-058: through the tanh-squashed latent, the entropy bonus pays for noise; h4-03 at 0.001 took std from 1.29 to 0.41, and legal returns appeared).
  - E5's entropy loss rose from 50.9 to 55.3 and std from 1.05 to 1.19.
  - Experiment design disagreed: E3 grew std from 0.61 to 1.05 and still improved. Coach flagged it without calling it an error.
  - **It is corrected to 0.001 as a correction, not as an experiment** (D-114 precedent), with a test.
- **Real dilution:** 35 % of live goals need more than 1.5 m/s, give about 0 legal returns, and have the highest falls per goal.
- **Forgetting is real** (bank p90 0.10 -> 0.28 m; falls 2.6 -> 4.7 %). The guard caught it as designed, and the bank line stays (never loosened).
- **Timing of 0.869 is not an E1 gate pass:** a different seed, and the gate needs all six items (experiment design).
- **Coach:** in the 0-0.5 m/s bin, root is 0.987 and paddle p90 is 0.07 m, but only 28 % of goals become legal returns. Once the robot is in place, aim (the face angle, the landing) is the binding gap.
- **Architecture:** `plan_goals`'s stance spot is not clamped to HINT_BOX_V2, unlike `stance_from_intercept`. This is recorded and unchanged here, so E5 and E6 stay comparable.

## Decisions

1. **E6's one change is the pre-registered planner change** (3 of 5: coach, experiment design, RL). Its trigger was met: the fast bins did not improve; the 1.5-2.0 m/s root rate fell from 0.122 to 0.064. Motion and architecture preferred the entropy fix alone first, with the planner as a zero-shot read.
   - **The walkable contact** (`planner.predict_contact_walkable`): the earliest point at or after the first interception whose stance spot needs at most 1.5 m/s of walking, while the ball is inside the bank's contact heights [0.50 m, 1.1 m]. If no point qualifies, the point that needs the least walking.
   - Task `Picklebot-Latent-TimedBall-Walk-G1`. The PPO settings carry the entropy correction (0.001); nothing else changes from E5.
   - Parent: E3's endpoint (model_39699), never a killed checkpoint.
2. **Pre-launch check: E3 zero-shot on the E6 task** (all five want a zero-shot read first; seed 4216503). It passes only if all three hold:
   - live goals needing more than 1.5 m/s <= 21 %, the bank's share (coach, experiment design; RL's 5 % is stricter and is reported);
   - legal returns >= 15.24 % (coach, RL; motion's "above the interval" is reported);
   - falls per feed <= 2.5 %.

   **A fail means no launch,** and the panel meets. Tests: `test_walkable_contact_*` and `test_e6_changes_only_the_planner_and_the_entropy_correction`.
3. **Early kill at about 30 %:** E5's lines, with the legal-return line taken from the parent on this task.
   - falls per feed > 2.5 %;
   - legal returns <= E3's zero-shot rate on the E6 task;
   - on the bank: paddle p90 > 0.20 m or speed error > 20 %.

   **Report only:** action std (RL, architecture), the speed bins and the round 13b items. Falls are also checked at the endpoint.
4. **Budget** (5 of 5): a panel round after E6, whatever happens.
   - A new stage budget needs a D-entry, with at most 4 runs (experiment design, architecture). That D-entry must state the gap plainly (RL, experiment design, coach): the video bar needs about 56 % legal per shot (0.56^4 = 0.10), and today's 15 % gives about 0.05 %.
   - If E6 is killed (2 kills in a row), the next round re-plans the route to the video rather than tuning further (RL, motion). Coach's candidate for the next stage is shot quality: the face factor and the landing target.
