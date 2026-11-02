# Panel round 70 brief: the drift control reads DRIFT; d1s8 reads SMOKE-FAIL, 2026-11-02

Read first:
- D-204 / D-205 in docs/DECISIONS.md;
- round 69 in mjlab/results/footwork-review.md;
- mjlab/results/diag68-summary.txt (the (iii) block), results/d1s3ctl-summary.json;
- mjlab/results/d1s8-summary.txt;
- scripts/diag/d1_stage8.sh.

## (iii) the drift control: DRIFT

rally-d1s3ctlb = the parent d1s3 model_31399 continued 1,200 iterations on its own task, with no change (D-203 settings, training seed 197).
- Training was clean. +360: falls 1.18, legal_return 0.840.
- Guard reads pooled over 4 seeds per checkpoint.

**GUARD-N: not needed.** The parent's single read is within the guards against its own pooled read: worst family -2.8, left + back -1.9.

**DRIFT: the control breaches r19_guards against the pooled parent.**
- reach_backhand 0.538 vs 0.604 (-6.6);
- reach_deep 0.113 vs 0.163 (-5.1);
- cross_forehand 0.717 vs 0.756 (-3.9);
- left + back -3.2 (ok);
- mean family shift -1.93 points (the line is -2.0).

**Reported, on 4220306:**

| checkpoint | P(5+) | feeder | failure by position 0 / 1 / 2 / 3 / 4 |
|---|---|---|---|
| control | 0.371 | 0.601 | 0.409 / 0.287 / 0.094 / 0.023 / 0.006 |
| parent | 0.387 | 0.629 | 0.382 / 0.287 / 0.082 / 0.028 / 0.010 |

So 1,200 more iterations of d1s3's own recipe, with nothing changed, erode contact families and do not improve P(5+) or feeder legal. Earlier children's guard breaches (d1s4, d1s6, d1s7) are at least partly this drift.

## d1s8 (D-205, recovery paid while parked): SMOKE-FAIL

Smoke: training seed 200, 1,024 envs, 40 iterations.
- falls per 1,000 env-s **4.696**, against the line 4.157 (D-170, unchanged);
- half-split (reported): first half **7.56**, second half **2.39**;
- exit 0, no traceback, std 0.1065, config ok.

For comparison, earlier smokes' halves were d1s2 4.15 / 1.69, d1s3 4.40 / 2.26, d1s4 3.66 / 1.67, d1s5 4.16 / 4.64, d1s6 5.26 / 0.92 and d1s7 1.52 / 0.92. d1s8's first half is the largest resume transient so far; its second half is in the parents' range.

Smoke dose log (cumulative, so totals): 85,084 newly paid steps at a mean value of about 0.44, against 259,392 hit_done steps at about 0.72. The newly paid steps are about a quarter of all paid recovery steps.

Nothing was trained. The GPU is idle.

## Rules

- Never loosen a threshold.
- Never re-roll a smoke until it passes (D-170, round 66).
- A gate is overturned only by an instrument defect.

## Questions

1. **Correction check.**
   - Is the DRIFT verdict valid as pre-registered? The control breached r19_guards; the mean shift is -1.93, just inside -2.0.
   - Is d1s8's SMOKE-FAIL valid? Is there an instrument defect, for example in falls_by_length under the changed reward?
   - Anything misstated?
2. **What DRIFT means for the programme.** The base recipe (LR 1e-4 constant, KL 0.05, 1,200 iterations from model_31399 on d1s3's task) erodes contact families and P(5+) on its own. Should later levers change the recipe (shorter runs, lower LR, a fixed reference KL / anchor) before testing any reward? Is d1s3 still the right parent?
3. **Next step.** Vote, with coded lines and seeds:
   - **(i)** Accept d1s8's SMOKE-FAIL and close (a) in this form; move on.
   - **(ii)** (a) again with a pre-registered resume-transient remedy (for example a critic warm-up, PICKLEBOT_CRITIC_WARMUP > 0). Say whether that is a second change and how the smoke line applies.
   - **(iii)** Fix the drift first: a recipe change tested as its own run (shorter / lower LR / anchored) against the control, then levers on top.
   - **(iv)** The falls lever (court falls 6.2-6.5 % vs 4 %).
   - **(v)** Other.

Seeds: dev free from 4220338 (4220338-4220340 held for re-reads); training from 201.
