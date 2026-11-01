# Panel round 65 brief: d1s4 reads NO-DOSE, so choose the next lever for the feeder gate (2026-11-02)

Read first:
- D-198, D-199 (with its two addenda) and D-200 in docs/DECISIONS.md;
- mjlab/results/d1s4-summary.txt;
- results/ballidx63-summary.txt;
- round 64 in mjlab/results/footwork-review.md.

## Facts

**The target.** P(5+) <= feeder legal (rally-target.md). Every player we have returns 0.60-0.65 of feeder balls.

**ballidx63 (FEED-STATE).** At the feeder fire the receiver is still moving (pelvis speed p50 0.28 m/s) and about 0.9 m from its recovery spot. The worst terciles fail 0.37 / 0.35, against 0.09 / 0.05 for the best. With a 3 s refeed, feeder legal rises 0.62 -> 0.74.

**d1s4.** The `ready_at_event` term, paid at feeder fires and at partner contacts (weight 50, v_std 0.3 m/s, d_std 1.0 m).
- The per-event mean rose 0.32 -> 0.375.
- At the feeder fire the state did not change: pelvis speed p50 0.291 vs 0.296; recovery distance p50 1.00 vs 0.87 m (worse).
- Contacts outnumber fires about 4:1, so the gain came from the hand-offs.
- Feeder legal fell 0.629 -> 0.596. Left + back feeder contact fell 0.437 -> 0.378 (back 0.643 -> 0.540).
- At a 3 s refeed the child is also worse: 0.729 vs 0.756.
- Agility kept (R_LB 0.85); k >= 3 kept (0.966); court falls 0.056 vs 0.062.
- **Verdict: NO-DOSE.**

**Why the robot is not set at the feeder fire** (not yet measured):
- The feeder fires 0.2-0.5 s after both robots are parked (refeed_delay 0.5 s), i.e. after the previous rally ends.
- Rallies end with the robot wherever its last shot or miss left it, often moving and away from its spot.
- So "set at the feeder fire" means recovering from a rally's last moment within about 0.5 s.
- The policy may not see the fire coming: there is no countdown in its observation.

**Earlier evidence:**
- D-177: `spot_progress` while parked paid moving toward the spot, and it had no measurable dose.
- D-171 / RL round 63: the feeder share of training balls is about 15 %, and feeder skill is being forgotten. `pair_rally_cap` = 5 (D-161 knob, no new code) was RL's vote.

**The parent stays the d1s3 child.** The d1s4 child is not adopted.

## Options (vote with coded lines)

- **(a) Feeder-only readiness:** pay the term only at feeder fires (one change against d1s4's task). This is not a higher weight. Risk: the same NO-DOSE, if the cause is the 0.5-s window.
- **(b) Parked readiness:** reward low pelvis speed and nearness to the recovery spot during the dead-ball interval, while parked and waiting for the feeder fire. The robot sees itself parked, so it can act on this. Unlike D-177, this pays being set, not moving.
- **(c) `pair_rally_cap` = 5** (RL, round 63): more feeder balls in practice. It also trains the post-rally start state. No new code.
- **(d) Observation:** add a refeed countdown (time to the feeder fire) to the policy's input. This is a network-input change, so it needs a fresh critic / normaliser, and is riskier.
- **(e) Accept the 0.5-s readiness gap** and work on what the feeder ball does to a set robot: left / back reach, reach_deep.
- **(f) Other.**

Seeds: dev next free 4220328; training next free 193.
