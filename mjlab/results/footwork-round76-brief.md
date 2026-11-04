# Panel round 76 brief: D-211 CONFIRMED, rally-d1s3lr3 is the new parent, 2026-11-04

Read first:
- D-211 and its result, and the D-191 result (Fast4), in docs/DECISIONS.md;
- round 75 in mjlab/results/footwork-review.md;
- mjlab/results/conf75-summary.txt;
- the frozen target, mjlab/results/rally-target.md.

## Result

16 fresh reads on dev 4220341-4220348: parent d1s3 model_31399 and C = rally-d1s3lr3 model_32598.
- **GAIN2:** +2.99 points; per seed +2.00 / +2.86 / +2.85 / +4.29; lower bound +1.68. P(5+) 0.4117 vs 0.3818.
- **Guards:** no breach. Worst family fast -4.4; cross_forehand -1.2; left + back +0.7.
- **Mechanism:**

  | measure | C | parent |
  |---|---|---|
  | ready stance | 0.295 | 0.154 |
  | falls per 1,000 hits | 0.84 | 1.86 |
  | WRONG_SIDE share | 0.231 | 0.255 |
  | recovery | 0.275 m | 0.375 m |

- **Reported:** feeder legal 0.639 vs 0.634; drift_verdict FIXED.
- **Calibration:** no shrinkage. Parent 0.3818 here vs 0.3812 on D-204 seeds; C 0.4117 vs 0.4115.

**CONFIRMED: C is the parent.** Its references are lev74-C (D-204 seeds) and conf75-C (fresh seeds). Family guards stay referenced to the original parent's pooled D-204 reads, which is stricter.

## Where we stand

- P(5+) is 0.41 against the target of 0.80 (Wilson low 0.78 over at least 1,000 rallies). Feeder legal is 0.64 against M1's 85 %. Court falls (target at most 4 %) have not been re-read on C. They were 5-6 % on older parents, and C falls about half as often per hit as its parent.
- Earlier hazard reads (on older parents): most losses are at the feeder ball (0.38) and k = 1 (0.29). Later shots are about 0.003 each.
- Round 75 (motion): C's gain comes from steadier positioning and fewer falls. Speed is unchanged or slightly lower (feeder peak p99 2.71 vs 2.77 m/s), and the loading dip is lost (0.139 vs 0.321). The user wants agility toward 3-4 m/s.
- The LR 3e-5 recipe gave +1.45 to +3.0 points per 1,200 iterations on three training seeds. Nobody has tested whether it compounds from C.
- **Queued and coded:**
  - lever (a) IdleRec (recovery pay while parked): it SMOKE-FAILed at LR 1e-4 on the old parent (D-205); a falls transient in iterations 0-9.
  - the Fast4 floor test: reads only, dev 4220248, on fw-fast4-01 model_18099 (D-191: +0.22 m/s, falls 0.155). It is the gate before Fast4 could be a d1b footwork teacher, which means a base rebuild.
- **Queued, not coded:** the falls lever; d1 + --recover.

The GPU is idle. Training seed next 207; dev next free 4220349 (4220340 held; 4220248 reserved for the Fast4 floor test).

## Questions

1. **Correction check.** Is CONFIRMED valid as pre-registered? Is anything misstated? Is anything missing for promotion (for example new reference reads)?
2. **Next step.** Vote with coded lines, kill checks and seeds:
   - **(i) Compound:** C2 = C + 1,200 iterations at LR 3e-5, seed 207, read against C (GAIN2, guards against the original parent, mechanism bars).
   - **(ii) Pair on seed 207:** C2 as in (i), plus C + one lever (lever (a) IdleRec with a smoke, or another named lever), the lever read against C2.
   - **(iii) Agility first:** the Fast4 floor test (reads only) now, then the d1b route if it passes.
   - **(iv) Other.**
3. **The target.** At about +2-3 points per accepted step, 0.80 is far off. Is there a larger lever the panel should plan toward (for example the opening-exchange hazard, or footwork speed)? Name the simplest version.
