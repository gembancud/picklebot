# Panel round 73 brief: rally-d1s3anc03 (anchor coef 0.3) reads HELD-NO-GAIN, 2026-11-03

Read first:
- D-208 in docs/DECISIONS.md;
- round 72 in mjlab/results/footwork-review.md;
- mjlab/results/anchor72-summary.txt (and .json);
- picklebot_mj/rl/sched_ppo.py (AnchoredScheduledPPO);
- picklebot_mj/rl/reg_ppo.py (_RefRegulariser).

## Result

rally-d1s3anc03 = model_31399, d1s3's task, LR 3e-5, AnchoredScheduledPPO coef 0.3, training seed 204, no smoke. Training clean.
- +360: falls 1.66, legal_return 0.759 (the +241-260 window read 0.888).
- **Pull-back:** 0.004 at update 1, 0.026 at update 10, 0.033 at update 100, 0.035 at +360 and at the end. It settled by about update 100, at 3.2x the coef-1.0 plateau (0.011), not the roughly 11x predicted from 1/coef^2.

**Pooled 4-seed read:**
- drift FIXED: no guard breach, left + back +0.3, mean family shift -0.39, backhand 0.618 vs 0.639;
- feeder 0.632 vs 0.635;
- **GAIN fails:** pooled P(5+) +0.20 points; per seed -0.53, -0.36, +0.48, +1.16; lower 95 % CI -1.06.
- **Route HELD-NO-GAIN.**

**Mechanism read** (pooled pairs, reported):

| arm | ready stance | falls per 1,000 hits | WRONG_SIDE share | recovery median |
|---|---|---|---|---|
| parent | 0.153 | 1.68 | 0.259 | 0.375 m |
| d1s3lr (no anchor) | **0.318** | **0.94** | **0.220** | **0.325 m** |
| anchor 1.0 | 0.151 | 1.74 | 0.253 | 0.375 m |
| anchor 0.3 | 0.150 | 1.58 | 0.248 | 0.375 m |

So at 0.3, as at 1.0, the anchor holds the posture at the parent's values. d1s3lr's P(5+) gain came with a whole-body posture change: a wider ready base, about half the falls, better recovery. Its drift was in the contact families (backhand, reach).

The GPU is idle. Training seed 204 is used; next is 205. Dev 4220341-4220348 were not used (no confirmation ran).

## Queued in D-208

- **Motion:** an anchor on the arms (stroke outputs) only, leaving the legs free. This is new code: an output mask on the KL.
- **RL:** coef 0.1.

## Questions

1. **Correction check.**
   - Is HELD-NO-GAIN valid as pre-registered?
   - Does the pull-back plateau (3.2x, not 11x) change the coefficient model?
   - Anything misstated?
2. **Next step.** Vote, with coded lines and seeds:
   - **(i) An arms-only anchor.** Which outputs are arms versus legs in the actor's action layout (the residual over the latent decoder)? Is a per-output mask well defined? Give the code and tests.
   - **(ii) coef 0.1.**
   - **(iii) No anchor, LR 3e-5, plus a stroke-specific guard lever.** Accept d1s3lr's recipe and attack the backhand drift another way.
   - **(iv) Other.**
3. **Lines.** Keep D-208's lines (drift_verdict + GAIN + routes + pooled confirmation), or change them?

Seeds: dev from 4220341; training from 205.
