# Panel round 74 brief: rally-d1s3lr2 (the d1s3lr replicate, seed 205) reads NOT-REPLICATED, 2026-11-04

Read first:
- D-209 in docs/DECISIONS.md;
- round 73 in mjlab/results/footwork-review.md;
- mjlab/results/rep73-summary.txt (and .json);
- d1_rule.replicated / gain_line.

## Result

rally-d1s3lr2 = rally-d1s3lr's recipe (model_31399, d1s3's task, LR 3e-5, ScheduledPPO, no anchor, 1,200 iterations) on training seed 205.
- Training clean. +360: falls 1.49, legal_return 0.873.

**Pooled 4-seed read** against the parent:
- **guards: no breach.** Worst family reach_backhand -4.4; cross_forehand -0.8; left + back -0.6; backhand 0.619 vs 0.639 (-2.0).
- **mean family shift -1.40**, so drift_verdict reads **PARTIAL**.
- **feeder 0.624 vs 0.635** (-1.1 points, outside FIXED's 0.01).
- **GAIN fails:** P(5+) 0.3957 vs 0.3812, pooled +1.45 points (>= +1 holds); per seed +0.34, +0.88, +1.38, +3.19; lower 95 % CI -0.52 (needs > 0).
- **Mechanism:**

  | measure | rally-d1s3lr2 | parent | d1s3lr |
  |---|---|---|---|
  | ready stance | **0.259** | 0.153 | 0.318 |
  | falls per 1,000 hits | **0.94** | 1.68 | 0.94 |
  | WRONG_SIDE share | 0.241 | 0.259 | 0.220 |
  | recovery median | 0.325 m | 0.375 m | 0.325 m |

- **REPLICATED** = GAIN and ready >= 0.25 and falls <= 1.3: the mechanism lines pass, GAIN fails. **Verdict NOT-REPLICATED.**
- D-209's route: the d1s3lr gain is read as a seed effect; the anchor line closes; panel.

**Not part of any verdict (post hoc):**
- Across both training seeds, all 8 eval-seed P(5+) differences against the parent are positive: d1s3lr +2.66 / +1.60 / +1.45 / +2.79; d1s3lr2 +0.34 / +0.88 / +1.38 / +3.19. Mean +1.79.
- The posture change replicates closely (ready 0.32 / 0.26, falls 0.94 / 0.94).
- The backhand breach did not replicate (d1s3lr -5.6, d1s3lr2 -2.0).
- The rule was set before the run and is not overturned.

The GPU is idle. Training seed 205 is used; next is 206. Dev 4220341-4220348 are unused (no CONFIRM); next free 4220341.

## Questions

1. **Correction check.**
   - Are NOT-REPLICATED and PARTIAL valid as pre-registered?
   - Was the GAIN CI (t, 3 df, over 4 eval seeds of one training seed) a reasonable test for replication, given that eval-seed spread dominates?
   - Anything misstated?
2. **What we now know.**
   - LR 3e-5 reliably changes posture (2 of 2 training seeds) and lowers falls.
   - Its P(5+) effect is positive in 8 of 8 eval comparisons but noisy.
   - Its family drift is PARTIAL to STILL-DRIFT.
   - The anchor freezes the posture (coef 1.0 and 0.3).
   - Is LR 3e-5 the right recipe base for the next levers, without promoting a checkpoint?
3. **Next step.** Vote, with coded lines and seeds:
   - **(i)** Close the LR-3e-5 line per D-209 and move to another target line: the falls lever, the opening-exchange STATE lever (lever (a), recovery pay while parked, parked since D-205), or the agility queue.
   - **(ii)** Adopt LR 3e-5 as the recipe base, with no promotion. The next lever (for example lever (a) or coach's backhand feeder weights) runs on it, against a matched LR-3e-5 control on the same training seed.
   - **(iii)** A third training seed of d1s3lr, with a pre-registered combined test over all three training seeds.
   - **(iv)** Other.

Seeds: dev from 4220341; training from 206.
