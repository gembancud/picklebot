# Review round 12: E3 met 3 of 6 gate items; the timing metric was wrong; the next run (2026-10-20)

## Consensus

1. **The timing metric is mis-specified** (5 of 5).
   - It took the paddle's closest approach to p* over the whole goal window, from goal set to t* + 0.3-0.8 s. So a wind-up or follow-through pass near p* could win, and a parked paddle's flat distance curve put the minimum anywhere.
   - E3 is 3 cm from p* at t* with a 4 % speed error, so it passes p* within milliseconds of t*. A 44.5 % timing rate contradicts that.
   - The code order is right (architecture: the clock ticks, then rewards, then resets, then command compute); the definition is the defect.
   - **The fix (3 of 5: motion, coach, architecture):** only clocks in [t* - 0.25, t* + 0.10] may update the closest approach. A minimum on a window edge (|dt| = 0.10 or 0.25) still fails the unchanged 50 ms bar.
   - RL and experiment design preferred the plane crossing along v*. Experiment design's concern, that a window could pass a flat (parked) curve by chance, is answered by its own falsification check, adopted:
     - unit tests: an on-time swing passes, a swing 100 ms early fails;
     - **E2's checkpoint (model_36200, a parker) must still fail the corrected timing item;**
     - old and new metrics are reported side by side in a D-entry naming this a measurement correction, not a gate change.
2. **Re-evaluate E3 first** (5 of 5): evaluation only, on a new development seed (4216111), with the root hit rate binned by the speed the goal requires (|root_rel| / t*) (architecture).
3. **Next run: a root/feet fix from E3's endpoint, counting as D-118's one extension** (4 of 5; experiment design: (b) because root was flat at E3's endpoint, at reward 0.58-0.61 over the last 3,000 iterations).
   - The single number is chosen by the re-evaluation (architecture's rule):
     - **if root misses cluster on goals that need more than 1 m/s:** `root_progress` max_speed 1.0 -> 1.6 m/s (motion). The reward stops paying at 1 m/s while the median goal needs about 1.23 m/s on average.
     - **otherwise:** `root_track` std 1.0 -> 0.25 m (RL, coach). At 1.0 it gives 0.94 at 0.25 m, almost no gradient.
   - **Early kill at about 30 %** (motion): falls > 3 % per episode, paddle p90 > 0.20 m, or speed error > 20 %.
   - **Not (d)** (5 of 5): fine-tuning with the ball now would mix up controller misses and planner error. The zero-shot pop-ups (1.54 m clearance, landing at 3.2 m) point at the planner's aim and face angle, which are checked against simulated contacts later.
   - **After this extension, any gate miss goes to the user** (D-118).
4. **Pre-launch check:** score scripted behaviours with the new term:
   - walk to the root target and swing > swing in place (lunge) > walk with no swing;
   - for max_speed: walking at the required speed then swinging beats walking at 1 m/s and arriving late.
