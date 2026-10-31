# Panel round 59 brief: design d1 (the base rebuilt with the fast specialist), 2026-10-31

Read first:
- D-189, D-190 and D-191 in docs/DECISIONS.md;
- mjlab/results/footwork-review.md (round 58);
- results/p2speed-summary.txt and results/fw-floor-summary.txt.

## Where we are

**Floor test (D-190).** latent-07's decoder can reproduce fw1b-S's leg actions, state by state:

| | lam 3 | lam 5 |
|---|---|---|
| legs explained | 0.954 | 0.973 |

The frozen route printed **d1**.

**P2 (D-191).** Rally 22b on the specialist's drill with the working speed reward, move-only, 600 iterations. Verdict **CAP-IN-07**:

| | baseline | P2 |
|---|---|---|
| falls per 1,000 env-s | 6.5 | 1.9 |
| arrival | 0.88 | 0.976 |
| settled share (back sectors) | 4-7 % | 11-18 % |
| sustained speed (m/s) | 1.16-1.45 | 1.20-1.51 |
| R_LB | 0.635 | 0.661 |
| residual saturation | 0 | 0 |

Safer and more settled, but barely faster. The frozen RES_BASE (s5c-18-merge17 / model_32874) carries the footwork of the 1-m/s walking teacher.

**User direction (D-191).** Keep raising agility past 2 m/s; beginners are 1-2, intermediates 3-4, professionals 4-6. A body-ceiling test is now running (scripts/diag/fw_fast4.sh, about 2 h): the specialist with the command cap at 4 m/s, read with a new first-step metric.

**P(5+) bound (D-189).** Footwork alone is about 0.5. The first handed balls are the bigger leak.

## How RES_BASE was built (artifacts/train/s5c-1x.launch.json; D-084 / D-085)

1. s5c-12-kickstart, from s5c-02-court model_28400.
2. s5c-13 / s5c-14: PPO at lam 3 (std rescaled).
3. s5c-15-kickstart2, `--lam-self 3.0 --hit-loss latent`.
4. s5c-16-recover.
5. s5c-17: PPO, giving model_31400 (the hitting teacher).
6. **s5c-18-merge17:** scripts/kickstart_h4.py `--init s5c-15/model_31675 --hit-teacher s5c-17/model_31400 --lam-self 3.0 --hit-loss latent --beta-frac 0`, 4,096 envs, 6,900 s.
   - Its footwork teacher is the walking teacher (Picklebot-Teacher-Move-G1 / model_15900).
   - It copies joint targets in move episodes and after the hit.

Architecture's finding (round 58): fw1b-S model_16600 has the walking teacher's interface (118 -> 29). So d1 = the s5c-18 recipe with `--teacher fw1b-S model_16600`, with no new code.

## Open design questions for d1

1. **Teacher:** fw1b-S now, or wait about 2 h for the ceiling test and use the faster specialist if it reads CEILING-RAISED? How much does that delay cost against its benefit?
2. **Recipe:**
   - init from s5c-15 / model_31675 (as s5c-18), or from the current RES_BASE (s5c-18 / model_32874)?
   - same hit teacher (s5c-17 / model_31400)?
   - same lam-self 3, hit-loss latent, beta-frac 0, 6,900 s?
3. **The rally residual on a new base.** P1 showed a residual can collapse when what it sits on changes. Here the decoder stays the same and only a_ref changes. Plan the residual re-adaptation / re-climb with D-188's validity rule and D-189's legal_return kill line. Give coded kill and endpoint lines:
   - agility: first-step time, left / back sustained, settled;
   - rally: P(5+) open, feeder, partner, falls;
   - retention against 22b.
4. **Base gate before the residual:** how to read the new base on its own (move drill with the specialist's drill and agility metrics; hitting retention against model_32874), with coded lines.
5. **Is d1 still the best next step** given P2 and the user's agility goal? Alternatives: d2 (residual-aware kickstart with leg_r 0.3); a rally run with the specialist drill (P2's change) at move share 0.35.

Seeds: dev next free 4220248 (spares 4220227-4220229, 4220235-4220240, 4220243). Training seeds next free 184 (180 reserved).
