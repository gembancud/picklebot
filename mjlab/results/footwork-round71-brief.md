# Panel round 71 brief: rally-d1s3lr (LR 3e-5) reads STILL-DRIFT, with a P(5+) gain, 2026-11-03

Read first:
- D-206 in docs/DECISIONS.md;
- round 70 in mjlab/results/footwork-review.md;
- mjlab/results/drift70-summary.txt;
- scripts/diag/drift70.sh;
- picklebot_mj/rl/reg_ppo.py and picklebot_mj/rl/sched_ppo.py.

## Stage A (the drift control's onset)

| checkpoint | guards | mean family shift | pooled feeder | pooled P(5+) | verdict |
|---|---|---|---|---|---|
| +400 (model_31800) | no breach (worst fast -3.6) | -1.48 | 0.619 | 0.378 | LATE |
| +800 (model_32200) | reach_deep breach | -2.38 | 0.600 | 0.370 | |
| +1200 (endpoint) | three breaches | -1.93 | 0.604 | 0.375 | |

The parent reads feeder 0.635 and P(5+) 0.381, pooled over 4 seeds.

## Stage B: rally-d1s3lr, verdict STILL-DRIFT

The parent continued on its own task, LR_PEAK 3e-5 (was 1e-4), 1,200 iterations, seed 201.
- Training clean. +360: falls 1.29, legal_return 0.860.
- Pooled 4-seed guard reads on the same seeds:
  - **breach:** backhand 0.583 vs 0.639 (-5.6, line -5);
  - cross_forehand -1.6, left + back -2.1;
  - mean family shift **-2.21** (also at or below -2.0).
- **Not part of the verdict, but notable:**
  - pooled feeder **0.632** (parent 0.635, control 0.604): kept;
  - pooled P(5+) **0.402** (parent 0.381, control 0.375): **+2.1 points**, n of about 11,000 rallies per arm, roughly 3 SE paired.

D-206's route on STILL-DRIFT: **the anchor next** (RegPPO's frozen-reference pull-back, ported into ScheduledPPO: new code of about 20 lines plus a test).

The GPU is idle. Training seed 201 is used; the next is 202.

## Questions

1. **Correction check.**
   - Is STILL-DRIFT valid as pre-registered?
   - Is the P(5+) gain real? Paired seeds, the pooled CI, per-seed consistency: the per-seed reads are results/drift70-lr-pairs-*.json and results/d1s3ctl-parent-pairs-*.json.
   - Anything misstated?
2. **The anchor run.** Specify it:
   - On which recipe base: LR 1e-4 (the control's, RL's round-70 spec) or LR 3e-5 (this run, which kept feeder and gained P(5+))? One change against which reference?
   - Coefficient, decay, and which reference (the parent's actor; KL or action-MSE).
   - Smoke (new code -> D-170 line), kills, and the DRIFT / FIXED lines against the pooled parent, with the controls reported.
3. **Alternatives.** Vote:
   - **(i)** The anchor per D-206.
   - **(ii)** Accept LR 3e-5 as the new recipe despite the backhand breach. **The threshold is not loosened**: a breach is a breach, and d1s3lr cannot be promoted. So this would mean levers run on the 3e-5 recipe with the guard reported against a 3e-5 control.
   - **(iii)** A lower LR still (1e-5), or a shorter run.
   - **(iv)** Other.

Seeds: dev free from 4220338 (4220338-4220340 held for re-reads); training from 202.
