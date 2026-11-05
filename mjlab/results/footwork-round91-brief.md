# Panel round 91 brief: the user's answers (D-228) - set start like a drill, agile reference motion, no realistic motor limits, 2026-11-06

Read first:
- D-226, D-227 (and its stage A result) and D-228 in docs/DECISIONS.md;
- results/rally-target.md;
- results/ph90-summary.txt;
- the G1 actuator constants (mjlab asset_zoo/robots/unitree_g1/g1_constants.py) and picklebot_mj/g1_paddle.py;
- mjlab/results/stage5b-video-pilot-survey.md (the CalTennis -> GVHMR -> GMR -> G1 route).

## The user's answers (D-228, verbatim)

1. "lets follow the proper spot if its going to be like in a drill. i guess it has to adjust either way"
2. "i would say if you could get a more agile reference like in tennis that should help. but we need to make it scale on to the proper scale right? i would say our target right now is purely digital. i dont have a fucking bot so even if its not possible with the current motor limits which i think its able to anyways, i want the robot to move the fastest it can to learn. i dont give a fuck about limiting the motors for realistic motors, i want fast humanlike movement"

## Facts

**The set-start hold, reported only (D-227 stage A):** C reads P(5+) 0.607 under a 3-s hold, against 0.412 on the standard read. The hazards are h0 0.214, h1 0.163, h2 0.058, h3 0.018, h4 0.003. But only about 5 % of feeder balls found both robots set (within 0.3 m and below 0.3 m/s); about 95 % were released by the timeout. C does not settle on its spot.

**Actuators (mjlab G1, BuiltinPositionActuatorCfg):**

| motor | effort limit |
|---|---|
| 5020 | 25 Nm |
| 7520_14 | 88 Nm (hips) |
| 7520_22 | 139 Nm (knees) |
| 4010 | 5 Nm |
| waist / ankle (5020 x2) | 50 Nm |

- Stiffness is armature x natural_freq^2, and the damping ratio is 2.0.
- Every policy so far was trained under these limits.

**fw-scratch-01 (D-227 B) is running to its +1,800 kill.** At +914 it stood still: 0 arrivals and 0 falls.

**Reference motion:**
- **On disk:** Tennis-MoCap (strokes in place, about 10-15 repeated strokes per take), LAFAN1, the D-178 AMASS-G1 subset (551 clips, little fast lateral motion), footwork-fast, one CalTennis pilot session (three camera mp4s, 244 MB), and GVHMR and GMR installed.
- **Missing:** the SMPL / SMPL-X body models. They need a personal registration at smpl-x.is.tue.mpg.de, which only the user can do.
- **CalTennis on Hugging Face** (demalenk/caltennis, CC BY-NC 4.0, about 121 GB in all, 20 sessions, about 80-100 MB per camera clip) has match-play footwork. GMR does the scaling to the G1 ("make it scale on to the proper scale").
- **No ready-made tennis-to-G1 motion set was found online.** The full AMASS-G1 is 6.95 GB, which we have partly; GINGA is soccer.

**Resources:**
- The GPU is in use by fw-scratch-01 until its kill read (about 01:20) or about 05:30 at its endpoint.
- Training seeds: next free 226.
- Dev seeds: next free 4220383 (4220340 held; 4220349-4220356 CONFIRM only).

## Questions

1. **Correction check on D-227 A and D-228.** Is anything misstated?
2. **The set-start read (the new frozen read, by the user's authority).** Define it exactly, so it can be coded, tested and frozen before any score:
   - the mechanism: place both robots on their spots before each feeder ball, as a drill reset, or hold the feeder ball until both are set, with or without a timeout;
   - what "set" means;
   - what happens between rallies;
   - what the R3 falls read becomes.
   
   "It has to adjust either way": the robots still move to the ball after the feed. The bars are unchanged. Should C be read on it now as the new baseline?
3. **The actuation change.** Which limits change (effort, velocity, stiffness / natural frequency, armature) and by how much? How is it tested first, as one change? For example: re-read fw1b-S and C zero-shot under the raised limits; or warm-start Q2's task under them with the same kill and gate. "Fast humanlike movement" keeps the style requirement.
4. **The reference route.** Name what the user should be asked for:
   - the SMPL-X registration;
   - which CalTennis sessions and cameras, at what size;
   - or something else.
   
   Say how the clips enter: tracking teacher, prior, or style reward.
5. **Order.** What runs first once the GPU is free, and is fw-scratch-01 still worth its kill read?
