# Stage 5 Drill 1 follow-up D1b (`drill-move-d01b`): right-side oversampling regressed

Date: 2026-10-06. Loop rule 8, follow-up 1. **One change:** training spot sectors back-right, right and forward-right sampled ×2 (`Picklebot-Drill-Move-Right-G1`); evaluation stays uniform. Warm-started from `drill-move-d01/model_13900`. 7,000 s cap: iterations 13,900 → 15,929. **Fixed endpoint `model_15900`.**

## Training
- **Healthy:** falls ~0, value loss 0.05–0.07, action std 0.57.
- **Rewards:** the arrival reward rose from ~0.10 (D1's plateau) to 0.15–0.20, but the training mix had twice as many right-side spots. Hitting rehearsal swung between 0.30 and 0.47.

## Movement evaluation (dev seed 4,200,110; uniform sectors; 14,586 finished spots)
| Direction | D1b arrival | D1 arrival | D1b ready |
|---|---:|---:|---:|
| forward | **43.8 %** | 97.7 % | 100 % |
| forward-left | **38.7 %** | 98.6 % | 99.6 % |
| left | 80.0 % | 97.4 % | 99.2 % |
| back-left | 97.9 % | 99.6 % | 85.6 % |
| back | 94.9 % | 94.5 % | **55.8 %** |
| back-right | 92.3 % | 63.0 % | 78.3 % |
| right | 77.7 % | 82.6 % | 98.8 % |
| forward-right | 56.1 % | 88.0 % | 99.7 % |
| **all** | **69.0 %** | 91.0 % | 88.9 % |

- **Error and falls:** median final error 0.175–0.275 m (forward sectors 0.275 m, over the 0.25 m limit); falls 2 in 6,144 robot episodes.

## Hitting retention (fixed start, target A, vs `model_12000`)
Overall **75.2 % vs 81.9 % (−6.7 points)**. Per family:
- backhand −12.1, low −12.6, fast −16.6, backspin −15.7, deep −5.2;
- the others between −3.9 and +6.9.

## Verdict
**D1b regressed on every Drill 1 gate metric** except back-right arrival. Oversampling the right shifted the gait toward right and back movement at the cost of forward and forward-left; forward-left fell from 98.6 % to 38.7 %. Hitting retention also got worse. The change does not fix the right-side weakness without breaking the rest.

## Follow-up D1c (rule 8, follow-up 2), decided before launch
- **Parent: `drill-move-d01/model_13900` (D1), not D1b.** Hill-climbing keeps the better parent. D1b is a failed branch (worse on arrival, error, ready stance and retention), so building on it would hill-climb downward. This is a choice between two completed fixed endpoints on dev seeds, not peak-picking within a run. D1b stays on record.
- **One change from D1: hitting rehearsal 25 % → 40 % of robot episodes** (`move_prob` 0.75 → 0.60). This targets D1's retention failure (low/fast/backspin −6.7 to −7.6) and was the follow-up planned in `stage5-run-d1.md`.
- Sectors stay uniform. Everything else is as in D1.
- **D1c does not target D1's right-side arrival gap.** If the Drill 1 gate is still missed after D1c, the loop stops for the user (rule 8) with both D1 and D1c analyses.

Files: `stage5-d1b-move.json`, `stage5-d1b-retention-A.json`, `stage5-d1b-retention-parent-A.json`.
