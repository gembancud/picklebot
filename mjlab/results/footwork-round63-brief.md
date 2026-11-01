# Panel round 63 brief: d1s3 reads SPEED-KEPT; next step toward the rally target, 2026-11-01

Read first:
- D-195, D-196 and D-197 in docs/DECISIONS.md;
- mjlab/results/d1s3-summary.txt;
- results/ballidx52-summary.txt (22b's ball-index split, training seeds);
- results/idlerec53-summary.txt (D-177: idle recovery, no measurable dose);
- results/p5-bound.txt (D-189);
- mjlab/results/rally-target.md.

## Where we are

**d1s3** (22b re-climbed on the d1 base with the move-episode speed reward, model_31399):
- Agility kept: R_LB 0.825; L/B 1.61 / 1.78 m/s; first step L 1.41 s; Measure60 falls 3.13 against 22b's 6.87.
- Rally unchanged against 22b, on the same seeds:
  - P(5+) open 0.380 vs 0.381;
  - feeder 0.635 vs 0.652;
  - left + back contact 0.496 vs 0.457 (22b model_30600: 0.484);
  - h5f court falls 0.062 vs 0.056. Z (untrained d1 composite): 0.046.
- **Verdict: SPEED-KEPT.** The agility the user asked for (D-191) is now carried by a rally player that is no worse at rallies.

**Rally target:** P(5+) >= 0.80 with Wilson low >= 0.78; sides within 3; **falls <= 4 %**; M1 feeder 85 %.
- Every player we have misses falls and feeder.
- The D-189 bound puts footwork alone at about 0.5.

**Where rallies end** (22b, ballidx52, training seeds):
- k = 1 (first robot-to-robot ball) legal 0.689; k = 2 0.825; k >= 3 0.933.
- k = 1 failures concentrate on the receiver's state at the hand-off, at matched interception distance:

| receiver state at hand-off | worst tercile fails | best tercile fails |
|---|---|---|
| pelvis speed | 0.271 | 0.086 |
| distance from the recovery spot | 0.232 | 0.108 |
| short idle time | 0.211 | — |

- Deep bounces (fail 0.232) and heavy spin also hurt.
- The D-177 idle-recovery reward (spot_progress while parked) had no measurable effect (idlerec53: k = 1 +0.8 pt, within noise).
- So the first ball fails mostly because the receiver is **not yet set** when it arrives, and partly on hard first shots.

**Feeder balls** (first ball of a rally, from the feeder): legal about 0.64-0.66 for every player. M1 needs 0.85.

## Options (vote, with coded lines and seeds)

- **(e1) Diagnostic first:** a ball-index split read on dev seeds (logging only, LR 0) of the d1s3 child against 22b. Does the faster, steadier base reduce the k = 1 state failures? About 1-2 GPU-h; needs a dev-seed variant of ballidx52.sh.
- **(e2) Recovery to ready in the base:** d1 + `--recover`. The kickstart copies the fast teacher after the hit too.
  - Architecture's precedent: s5c-16-recover collapsed hitting (74.5 % -> 47.3 %), because the robot was still walking when the next feed came.
  - Then the d1s3 recipe on top.
- **(e3) Recovery in the rally task:** a reward for being set (low pelvis speed, near the recovery spot) at the moment a handed ball arrives, on the d1s3 child. One change.
- **(e4) Feeder-ball lever:** the feeder ball is the other half of M1, at about 0.65 against 0.85. What limits it?
- **(e5) Falls lever:** court falls of 5-6 % against the 4 % target line.
- **(f) Other.**

Also rule on:
- which player is the parent from now on: the d1s3 child, or 22b;
- whether any line in the d1s2-gate verdict table needs a new D-entry. The court-falls line comes from the rally target and is not loosened.

Seeds:
- dev next free 4220303 (spares 4220227-4220229, 4220235-4220240, 4220243, 4220263-4220265; 4220248 reserved for the Fast4 floor test);
- training next free 191 (188 reserved for d1b, 180 for H1'').
