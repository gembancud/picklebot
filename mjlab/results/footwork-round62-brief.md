# Panel round 62 brief: d1 stage 2 reads PANEL, 2026-11-01

Read first:
- D-194 and D-195 in docs/DECISIONS.md;
- mjlab/results/d1s2-summary.txt (all lines);
- results/d1s2-*.json;
- results/d1r-summary.txt (the base gate);
- round 61 in mjlab/results/footwork-review.md.

## What happened

- **The d1 base** (s5c-d1-fw1bS model_32854, fw1b-S as the move teacher) passed its gate: agility MIXED (R_LB 0.62 -> 0.80; falls 57 -> 12 on 3-5 m Fast25 spots), and hitting RETAINS.
- **Zero-shot.** 22b model_30200's residual on the d1 base, with no training (dev 4220257):
  - rally unchanged: P(5+) open 0.381 vs 0.379; feeder 0.652 vs 0.662;
  - footwork much faster: Measure60 sustained L / B 1.47 / 1.89 vs 1.16 / 1.45; falls 5.8 vs 6.4.
- **Stage 2.** 22b's task, 1,200 iterations on the d1 base. Training stayed healthy: +360 checks CONTINUE; training-log legal 0.79-0.93 in late windows.
- **Endpoint** (model_31399 against 22b model_30200, paired on the same seeds):
  - P(5+) open 0.369 vs 0.381;
  - feeder 0.622 vs 0.648;
  - left + back feeder contact 0.430 vs 0.482;
  - partner 0.991 vs 0.989;
  - guards broken (six families, the worst cross_backhand -8.3; left + back -5.3);
  - court falls 0.068 from the h5f battery. Earlier composites read 0.06-0.075 there; 22b has no h5f read.
  - 22b model_30600 (+400 on its own base, reported): P(5+) 0.385, feeder 0.628.
- **Agility** (Measure60, against 22b's composite): CAP-HELD.
  - R_LB 0.637 -> 0.688.
  - Sustained L / B 1.39 / 1.43, below the zero-shot's 1.47 / 1.89.
  - Falls 6.9 -> 1.07; worst arrival 0.98.
- **Verdict: PANEL.**

## The question

Training on 22b's rally task seems to have **trained the new speed back out**: zero-shot L / B 1.47 / 1.89, endpoint 1.39 / 1.43. It also cost feeder and left / back contact. Its move reward saturates at about 1 m/s (round 61, motion), and ball-episode footwork is still s5c-17's (D-192: no `--recover`).

Queued options (from D-192 to D-195), or others:
- **(a) Adopt and read the zero-shot composite** (22b on the d1 base, no training) as a candidate. It has the same rally and faster, safer footwork. It needs its own endpoint read (h5f battery, guards against 22b). This adds no training: is it a legitimate candidate?
- **(b) d1 + `--recover`.** Rebuild the base again, with the fast teacher also copied after the hit in ball episodes (D-085's existing flag). One change against d1.
- **(c) d1b.** Kickstart move episodes on 1-5 m spots.
- **(d) Re-climb on the d1 base with the specialist's speed reward** (fw_track_lin_vel, P2's change) in the rally task's move episodes, so rally training stops pulling speed down. One change against stage 2.
- **(e) The first-handed-ball levers.** D-189 bound: footwork alone gives about 0.5; the first handed balls (k = 1 legal 0.64-0.69 vs 0.91-0.93 for k >= 3) are the bigger leak.
- **(f) Other.**

Rule on:
1. A correction check of D-195's reading.
2. Is the "speed trained out" reading right? What evidence separates it from noise or from the rally task simply not needing the speed?
3. Vote with coded lines and seeds.

The rally target (rally-target.md) still governs. The user wants agility toward 3-4 m/s.

Seeds: dev next free 4220283 (spares 4220227-4220229, 4220235-4220240, 4220243, 4220263-4220265; 4220248 reserved for the Fast4 floor test); training next free 189 (188 reserved for d1b, 180 for H1'').
