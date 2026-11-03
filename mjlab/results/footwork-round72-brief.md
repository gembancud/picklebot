# Panel round 72 brief: rally-d1s3anc (LR 3e-5 + anchor) reads FIXED pooled, then CONFIRM-FAIL, 2026-11-03

Read first:
- D-207 in docs/DECISIONS.md;
- round 71 in mjlab/results/footwork-review.md;
- mjlab/results/anchor71-summary.txt (and .json);
- scripts/diag/anchor71.sh;
- results/anchor71-train.jsonl (the pull-back per update).

## Result

rally-d1s3anc = model_31399 on d1s3's task, LR 3e-5, with AnchoredScheduledPPO: a pull-back to the parent's frozen actor, coef 1.0 constant. Training seed 202.
- **Smoke** clean: 2.75 falls; the pull-back wired, first update 0.005, nonzero by update 10.
- **+360** CONTINUE: falls 1.68, legal_return 0.813 (rally-d1s3lr had 0.860).
- **Pull-back** 0.011 at both +360 and +1200; KL per update about 0.0027.

**Pooled 4-seed read** (D-204's seeds) against the pooled parent: **FIXED**.

| measure | anchor | parent | rally-d1s3lr | control (1e-4) |
|---|---|---|---|---|
| guards | no breach (worst reach_forehand -2.2; left + back -0.8) | | | |
| mean family shift | **-0.56** | | -2.21 | -1.93 |
| backhand | 0.631 | 0.639 | 0.583 | |
| feeder | 0.630 | 0.635 | 0.632 | 0.604 |
| P(5+) | **0.381** | 0.381 | **0.402** | 0.375 |

- The P(5+) gain of rally-d1s3lr is gone. Per seed, the anchor reads below d1s3lr on all 4 seeds (-1.5 to -3.1).

**Confirmation** (fresh dev 4220338 pairs / 4220339 direction; parent re-read on the same seeds): **CONFIRM-FAIL**.
- backhand 0.531 vs 0.588 (**-5.7**, breach);
- cross_forehand -1.8; left + back +0.7;
- P(5+) 0.3825 vs 0.3869 (below the parent).
- Pre-registered: CONFIRM-FAIL -> panel, no promotion.
- Caveat for the correction check: round 68 found single-seed family reads have a SE of about 5 points, and the parent fails its own fast guard on a re-read. A single-seed confirmation guard is therefore weak. This is recorded, not used to overturn the result.

**Net:** the anchor at coef 1.0 stopped the pooled drift but also stopped learning: P(5+) is back to the parent's level. The fresh-seed read shows a backhand breach and no P(5+) gain. d1s3 model_31399 stays the parent.

The GPU is idle. Training seeds 202-203 are used; next is 204. Dev 4220338-4220339 are used; 4220340 is held; next free 4220341.

## Questions

1. **Correction check.**
   - Are FIXED and CONFIRM-FAIL valid as pre-registered?
   - Is the single-seed confirmation a design weakness to fix in future pre-registrations, for example by pooling confirmation over 4 fresh seeds?
   - Is the confirmation backhand breach likely noise or real? The pooled backhand was 0.631 vs 0.639.
   - Anything misstated?
2. **What the anchor did.** It held the families but erased the P(5+) gain. Is the gain incompatible with staying near the parent, or is coef 1.0 simply too strong (pull-back 0.011 per sample against a KL of about 0.003 per update)?
3. **Next step.** Vote, with coded lines and seeds:
   - **(i)** A weaker anchor (for example coef 0.3), one change against rally-d1s3anc.
   - **(ii)** The anchor at coef 1.0 as the stable base, plus a lever on top: lever (a) recovery pay while parked (parked since D-205), or the falls lever.
   - **(iii)** Accept that d1s3lr's P(5+) gain cannot be had without drift on this task; change the task's ball mix toward rally balls (the backhand fade is rally-only).
   - **(iv)** Other.
