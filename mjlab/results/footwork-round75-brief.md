# Panel round 75 brief: D-210 reads RECIPE pass, LEVER-FAIL, 2026-11-04

Read first:
- D-210 and its result in docs/DECISIONS.md;
- round 74 in mjlab/results/footwork-review.md;
- mjlab/results/lev74-summary.txt (and .json);
- d1_rule.gain2 / mechanism / drift_verdict;
- the frozen target, mjlab/results/rally-target.md.

## Result

Both runs on training seed 206 (LR 3e-5, ScheduledPPO, no anchor, 1,200 iterations from d1s3 model_31399, endpoint model_32598). Training clean.
- +360 for C: falls 1.29 per 1,000 env-s, legal_return 0.853.
- +360 for L: falls 1.69 per 1,000 env-s, legal_return 0.796.

**RECIPE: PASS.** C = rally-d1s3lr3 (d1s3lr's recipe) against the parent, pooled over D-204's 4 + 4 seeds.
- P(5+) 0.4115 vs 0.3812.
- GAIN2 +3.03 points; per seed +2.40 / +3.12 / +3.49 / +3.09; lower bound +1.72.
- Ready stance 0.291 (bar 0.25); falls per 1,000 hits 0.89 (bar 1.3); WRONG_SIDE 0.224; recovery 0.275 m.

**LEVER: FAIL.** L = rally-d1s3bh = C + backhand / reach-backhand / cross-backhand feeder weights 2.0, against C.
- GAIN2: -0.46 points; per seed -0.84 / -0.49 / -1.57 / +1.08; lower bound -1.81.
- Guard breach against the pooled parent: cross_forehand 0.722 vs 0.756 (-3.4; kill below -3).
- Backhand-family contact, L vs C:

  | family | L | C |
  |---|---|---|
  | backhand | 0.625 | 0.606 |
  | reach_backhand | 0.613 | 0.614 |
  | cross_backhand | 0.485 | 0.425 |

- Falls per 1,000 hits 1.13 vs C 0.89; ready stance 0.326.
- No CONFIRM ran; dev 4220341-4220348 are still unread.

**Reported only:** the 3-training-seed estimate (d1s3lr, d1s3lr2, C) is +2.20 points, 95 % CI +0.22 to +4.17.

**Post hoc (no verdict):**
- C against the pooled parent has no guard breach. Worst family fast -4.6; wide_forehand -3.1; backhand -3.3; low -3.5; cross_forehand -0.2; left + back +0.1.
- C's mean family shift is -0.93; feeder 0.638 vs 0.635. drift_verdict would read FIXED.
- L's family shifts against the parent run from cross_backhand +7.8 and reach_deep +3.0 down to cross_forehand -3.4. Mean -0.18.

**Distance to the target:** P(5+) 0.41 (C) against 0.80; feeder 0.64 against M1's 85 %. Under the earlier hazards, most of the loss is still at the feeder ball and k = 1.

**Note:** C is a finished, read seed-206 run. Any next lever trained on seed 206 from the same parent and settings has C as a matched control at no extra training cost.

The GPU is idle. Training seeds 206 are used; next is 207. Dev 4220341-4220348 are reserved but unread; next free 4220349 (4220340 held).

## Questions

1. **Correction check.**
   - Are RECIPE and LEVER-FAIL valid as pre-registered?
   - Is GAIN2's per-seed SE (0.23 here) a sound guard when the eval seeds share one training seed?
   - Anything misstated?
2. **What the backhand result tells us.** Doubling the weights moved cross_backhand contact up 6 points but cost cross_forehand and the P(5+) gain. Is family reweighting a dead lever, or just this dose?
3. **Next step.** Vote, with coded lines and seeds:
   - **(i) Promote C** (rally-d1s3lr3 model_32598) as the new parent, after a pre-registered CONFIRM: parent and C re-read pooled on fresh dev 4220341-4220348. Later levers start from C.
   - **(ii) Continue the recipe:** a further 1,200 iterations of C at LR 3e-5 (seed 207), read against C. Does the gain compound?
   - **(iii) A lever on seed 206 against C,** no promotion. Candidates: lever (a) IdleRec, recovery pay while parked (coded since D-205); the falls lever; an agility item (Fast4 floor, d1 + --recover).
   - **(iv) Other.**
