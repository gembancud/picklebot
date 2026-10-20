# Review round 11: E2 killed; E3 specified (2026-10-20)

**Trigger.**
- E2 was killed at its early check: falls 5.12 % (40 / 781; 95 % CI about 3.6-6.9 %) against the 5 % line.
- Its paddle placement was learned: median error 0.01 m, p90 0.08 m. But it parked the paddle: speed error 96 %, timing within 50 ms 21.7 %.
- 2 kills in a row: the user chose to continue (D-120).

## Consensus

1. **Correction check (5 of 5):**
   - E2 was implemented as specified. **The round-10 design was wrong:** the 0.5 floor on the speed factor paid a parked paddle half the contact bonus.
   - With paddle_track and the 0.10 m position kernel, parking tied with or beat a real swing. At the bank medians, park about 3.1 and a 4.8 m/s swing about 3.1 per goal (RL). A 4.7 m/s swing one 20 ms step late earns 0.37, against 0.5 for parking (architecture).
   - Round 10's pre-launch check showed it (speed factor 0.50 / 0.50 / 0.54), but its rule only asked that the factor "varies".
   - **New standing rule: a reward pre-launch check must compare the behaviours the reward should rank (park vs swing), not only check that terms pay.**
2. **E3's one change (4 of 5): drop the floor.** fv = clamp(1 - |dv| / |v*|, 0, 1) (`speed="linear0"`, `Picklebot-Latent-TimedReach-V3-G1`). Nothing else changes; paddle_track stays at weight 2.
   - Parking now earns about 0.6 per goal, a swing about 2.1.
   - **Coach:** gate paddle_track off for the last 0.3 s instead. Runner-up; the others computed it moves only about 0.3-0.6 per goal and leaves parking ahead.
3. **Not lambda 3 now (5 of 5).** On a lambda-1 checkpoint it triples the latent offset and the exploration noise, and weakens the latent penalty about 9x. D-082 run 13 is the precedent: falls exploded. Falls are already at the line.
   - **Pre-registered next step** (motion, experiment design): if E3 keeps position but its speed error levels off (peak paddle speed <= 5 m/s, or speed error about 30-40 %), E4 is lambda 3 with the action-noise std divided by 3. The named premise is lambda-1 capacity: lambda-1 executors topped out at 4.4-4.7 m/s.
4. **Parent:** reach-06/model_34700, widened again (sha be115822..., the same file as E1 and E2). Bank, gate, early kill, training seed 74 and evaluation seeds 4216101 / 4216110 are unchanged.
5. **Pre-launch check:** experiment design's rules (tie rule):
   - every term pays;
   - `timed_contact` > 0.01 on >= 5 % of goals;
   - Spearman(paddle speed along v*, contact reward) >= 0.5 on goals with a position factor > 0.5;
   - fall and paddle sums within 10 % of E2's check.

   Plus a unit test (`test_e3_contact_reward_prefers_a_swing_over_parking`, passing): parked < half speed < perfect; per goal a perfect swing beats parking by >= 2, and a 4.8 m/s swing with a 5 cm miss by >= 1. E2's floored factor tied them.
