# Panel round 84 brief: D-220 (24-s episodes, dose fixed) reads NO-CANDIDATE - the pre-registered STOP fires; name and plan the footwork-base phase, 2026-11-05

Read first:
- D-220 and its result in docs/DECISIONS.md;
- rounds 77-83 in mjlab/results/footwork-review.md;
- results/ep83-summary.txt;
- D-192 (the d1 base rebuild), D-213 (the Fast4 court-scale read) and its result;
- the frozen target (results/rally-target.md);
- D-169 and D-179;
- docs/PANEL.md.

## Result

**The dose arrived:** post-reset share of live feeder fires 0.475, and resets per live env-s 0.0388 (about 4.7x C2). Training was clean.

**At the endpoint, nothing moved:**
- q0 was 0.266 against C's 0.252. The STOP line was C + 0.08.
- GAIN2 was +0.66 points (lower bound -0.70).
- H0 failed (0.3737 vs 0.3725).
- K3-KEPT failed: 5+ rallies ended at 0.028 against 0.012.
- The guards against the original parent fail: fast contact -6.6 and cross_forehand -4.8.
- Far-ball legal (launch > 1.2 m) went from 0.42 to 0.45. Near-ball legal stays at about 0.90.

All five agreed in round 83 that this outcome means STOP. **The episode-length route is closed.** C (rally-d1s3lr3 model_32598) stays the parent, and the target is unchanged.

## What the footwork phase has established (D-179 to D-220)

**The P(5+) gap is the opening.** Within-rally legal is 0.98-0.99. Over the read, the first feeder ball converts q0 0.25 and later feeder balls q1 0.52. With P(5+) ~= 1/(1+(1-q0)/q1), the ceiling at today's q0 is about 0.57. The target needs q0 >= about 0.75-0.87, and q1 has to rise as well.

**The spawn ball is a reach problem:**
- The spawn box is up to 4.1 m off the spot (median 2.1 m; 81 % beyond 1.2 m).
- Ball contact comes 1.6-2.2 s after spawn.
- Legal is about 0.90 within 0.3 m and about 0.42-0.45 beyond 1.2 m.
- Training and the read agree on far balls (0.44 vs 0.42). More practice at the read's weight (D-220) did not move it.

**Speed at court scale is flat everywhere:**
- On 0.5-3 m spots (Measure60-Court, D-213), both teachers, fw1b-S and Fast4, peak at about 1.3-1.5 m/s (p50).
  - They sustain about 1.0-1.1 m/s.
  - Their first-step time is about 1.3-1.4 s in left and back (the d1_rule first-step metric).
- Fast4's 4-6 m gain does not show at court scale.
- The rally policy uses about 2 m/s at most. Misses on left, deep and fast balls peak at 1.6-1.8 m/s.
- The limit is acceleration over the first 1-2 m, not top speed.
- For reference, the user puts beginners at 1-2 m/s and intermediates at 3-4. A human intermediate covers 1.5 m in roughly 0.6-0.8 s.

**The stack:**
- The residual policy (lam_r 2) sits on a **frozen** d1 base: s5c-d1-fw1bS model_32854, the D-192 kickstart with fw1b-S as move teacher, 0.5-3 m move spots, move-prob 0.5, no `--recover`.
- The base runs through the latent-07 decoder.
- latent-07 can express 95 % of the specialist's leg actions (floor test).
- Every residual lever since D-199 has moved q0 by at most about 0.02.

## Options named so far (round 83 and earlier)

- **(a) A court-scale quickness specialist first, then the rebuild** (coach; experiment design and RL in part). Train a footwork specialist on Measure60-Court's 0.5-3 m spots with reward for time to arrival or acceleration, not top speed.
  - Gate: an existing fast4_check-style read against fw1b-S (FIRST-STEP, FASTER, SETTLE, ARRIVE).
  - On a pass, rerun D-192's kickstart with it as the move teacher (d1c).
  - Then the base gate (agility_verdict, retention, base_verdict). Then 22b's residual climbs again on the new base.
- **(b) A spawn-box base retrain** (motion). The base's move drill is drawn from the read's spawn box, with a ball-arrival deadline, so the base learns to reach and hit on the run at about 2 m/s.
- **(c) d1 + `--recover`** (RL, queued since D-192). This is the same kickstart, with the walker also copied after the hit.
- **(d) A distil-then-PPO joint fine-tune** (architecture). Unfreeze the base and train base and residual jointly on the rally task, with a distillation anchor to today's composite. About 80 lines and about 6 GPU h; high risk of forgetting.
- **(e) Other.**

GPU idle. Training seeds next free 220; dev next free 4220373 (4220349-4220356 reserved unread for a CONFIRM).

## Questions

1. **Correction check.** Is NO-CANDIDATE valid, and the STOP correctly triggered? Is anything above misstated?
2. **The phase.** Name the footwork-base phase and its first run. Vote for one of (a)-(e). Give:
   - the one change and its parent;
   - the gate or instrument that shows the change worked *before* the long rally re-climb (readable at smoke, on windows that exist);
   - a kill at about 30 %;
   - seeds.

   If you propose something bigger than the smallest option, name the simpler option and say why it fails.
3. **The speed claim.** Does the evidence support "acceleration over the first 1-2 m is the limit"? If yes, which existing instrument measures it best (first-step time, time to 1.5 m, sustained p50)? Which line should a new base or specialist have to beat?
4. **The target.** Is the frozen target reachable through a better base? If not, what would the panel need to see before recording a STOP to the user? The target itself is unchanged.
