# Stage 4 gate: NOT MET (narrowly). Stopped for the user.

Date: 2026-10-03. Candidate: the fixed endpoint of the last Stage 4 run, **`aim-all-c01/model_7600`** (run C, `stage4-run-c.md`). Evaluated on dev seed 4,200,060: 2048 envs × 16 s per condition, paired targets A and B, about 2.7k feeds per family, and the parent `aim-b01/model_5300` on the same feeds. No other checkpoint was considered.

| Criterion | Threshold | Result | Verdict |
|---|---|---|---|
| Legal return, easy_forehand | ≥ 85 % | 85.1 % (A 84.5 [82.5, 86.2], B 85.7 [83.7, 87.5]) | pass (point estimate only) |
| Legal return, wide_forehand | ≥ 85 % | **84.6 %** (A 84.3 [82.3, 86.1], B 84.9 [82.9, 86.7]) | **miss by 0.4 points** |
| Legal return, backhand | ≥ 85 % | **84.4 %** (A 85.4 [83.4, 87.1], B 83.3 [81.2, 85.2]) | **miss by 0.6 points** |
| Legal return, deep / short / low / fast / topspin / backspin | ≥ 70 % | 84.6 / 75.8 / 86.8 / 88.5 / 85.3 / 73.9 % | pass |
| Legal return, high | ≥ 70 % | **69.2 %** (A 69.6 [67.1, 72.0], B 68.8 [66.3, 71.3]) | **miss by 0.8 points** |
| Target A/B gain, 95 % interval above 0 | > 0 | +0.533 [0.528, 0.539]; every family > 0 (lowest backspin +0.096 [0.085, 0.107]) | pass |
| Easy-feed retention | ≤ 5 points loss | +4.4 points vs the parent on the same feeds | pass |
| Falls | — | 0 per robot episode | — |

**Three of the ten family thresholds are missed, each by less than 1 point**, and each of those intervals contains its threshold. Under the rule written before the runs, the gate is not met. There is no automatic extension; the per-family results are recorded and the user decides.

## What limits it
- **Contact**, not landing accuracy. Contact is 86–90 % in every family, and most failed feeds are balls never touched (938 `LOST` vs 223 wrong side with target A). Given contact, about 96 % of lateral touches land legally. Contact has stayed in the 85–92 % band since run A3, while legal-given-contact keeps improving.
- **Context.** Under the all-family mix the lateral families score about 5 points lower than under run B's lateral-only evaluation, for both run C and its parent. The robot's state after a hard feed (e.g. a high ball) makes the next easy feed harder in the feeding machine.

## Options for the user
1. **Run D: a fixed continuation of run C** (same task and recipe, warm-started from `model_7600`, ≤ 2 h), then re-evaluate the gate on a fresh dev seed. Rewards were still rising slowly at the cap. Cheapest option; changes nothing about the setup.
2. **Accept with the documented deviations** (all within the noise of their thresholds) and go to Stage 5. Stage 5 retrains the recipe with two more seeds and re-tests on fresh dev seeds, which tests these margins anyway.
3. **Target contact directly before more training.** Examples: a reward for the paddle reaching the ball's predicted path, a longer refeed delay to recover between feeds, or weighting the mix toward high/lateral. One variable per run.
4. **Revise the thresholds.** Not recommended without a reason other than this result.
