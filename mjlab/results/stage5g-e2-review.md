# Review round 10: E1 killed; E2 specified (2026-10-20)

Five members answered independently. The brief covered E1's kill and the reward diagnosis.

## Consensus

1. **E1 counts as a kill** (5 of 5). A run that misses its pre-registered early check is a kill whatever the cause; only a broken measurement or a crashed tool is exempt.
   - The error is shared. Round 9 specified dropping the dense paddle term, and the 0.3 s swing lead was in the spec.
   - Also, at the parent's 0.32 m median miss, the contact reward's position factor was about exp(-10) too (RL).
   - E1's falls (1.0 %) are reported as a pass: the root and falls terms work.

   Stage 5G: 1 kill, 1 of 6 runs. **An E2 kill returns the decision to the user.**
2. **E2's one change: a redesign of the paddle reward** (counted as one change; 4-5 of 5):
   - restore reach-06's `paddle_track` to p* (std 0.15, weight 2) while the goal is open (5 of 5; motion would open it only for tau > 0.3 s);
   - delete `swing_guide` (4 of 5; experiment design would cap its lead at 0.25 m);
   - `timed_contact`'s velocity factor becomes linear: 0.5 + 0.5 * clamp(1 - |dv| / |v*|, 0, 1). It pays from a parked paddle (RL; the coach's "position pays half" shape; architecture and motion also proposed linear factors).

   **No speed curriculum, no change to lambda, no change to the bank.**
3. **Two implementation bugs fixed** before E2 (architecture; these are fixes, not experimental changes):
   - **(a) Reset:** the first goal of each episode was sampled before the episode clock and pose reset (stale t_contact, p* and root target). The fix resamples after the reset.
   - **(b) Timing grid:** t* is snapped to the 20 ms control grid, and the one-shot fires at clock >= t_contact - step_dt / 2. Unsnapped, a perfect 7 m/s swing measured about 7 cm off on average. This corrects the measurement; the gate is unchanged.
4. **Parent:** reach-06/model_34700, widened again (5 of 5). A killed run is never a parent. Bank, gate, early kill and seeds 4216101 / 4216110 are unchanged.
5. **Offline check before launch** (5 of 5; not a run, not selection on the gate): the parent zero-shot on the fixed E2 task, 256 envs, 10 s, spare seed 4216012.
   - **Pass rules, fixed now:**
     - every reward term pays;
     - `timed_contact` > 0.01 on at least 20 % of goals, with a velocity factor that varies across envs;
     - the first goal after a reset has the same p*-to-pelvis distance as later goals.
   - **Also reported:**
     - the split of v* into its normal part u (the part that sets the outgoing ball) and its tangential part (`paddle_for` copies the ball's tangential velocity; motion and architecture);
     - the parent's peak paddle speeds.
   - **If the commanded speed is infeasible for latent-07 at lambda 1** (lambda-1 ball executors topped out at 4.4-4.7 m/s; motion), that is a premise question for the panel, never tuned away. A lambda change would be its own later run.
