# Stage 5 Drill 1: D1, D1b and D1c compared (informational under D-042)

Date: 2026-10-06. All three runs share one policy between move-to-spot episodes and hitting rehearsal (D-041). Each is evaluated at its fixed endpoint on its own fresh dev seed. Movement is scored on move episodes only (uniform sectors, 2048 envs × 24 s). Retention is scored on the Stage 4 families from the fixed start, hitting only, target A, versus `footwork-f02/model_12000` on the same feeds.

| | D1 | D1b | D1c |
|---|---|---|---|
| Change | — | right sectors ×2 | hitting rehearsal 25 → 40 % |
| Parent | `footwork-f02/model_12000` | D1 `model_13900` | D1 `model_13900` |
| Endpoint | `drill-move-d01/model_13900` | `drill-move-d01b/model_15900` | `drill-move-d01c/model_15900` |
| Dev seed | 4,200,100 | 4,200,110 | 4,200,120 |
| **Arrival, all** | **91.0 %** | 69.0 % | 85.6 % |
| forward / fwd-left / left | 97.7 / 98.6 / 97.4 % | 43.8 / 38.7 / 80.0 % | 98.9 / 99.8 / 96.4 % |
| back-left / back | 99.6 / 94.5 % | 97.9 / 94.9 % | 98.5 / 95.7 % |
| back-right / right / fwd-right | 63.0 / 82.6 / 88.0 % | 92.3 / 77.7 / 56.1 % | 56.9 / 55.8 / 75.2 % |
| Median final error | 0.175–0.225 m | 0.175–0.275 m | 0.175–0.225 m |
| Ready stance at arrival | 99.9 % | 88.9 % | 99.4 % |
| Falls per robot episode | 0 | 0.03 % | 0 |
| Retention, overall | **−2.0** | −6.7 | −5.3 |
| Retention, worst families | low −6.7, fast −7.0, backspin −7.6 | fast −16.6, backspin −15.7, low −12.6, backhand −12.1 | low −15.3, fast −14.9, wide −7.9, easy −7.6 |

**Against the Drill 1 thresholds** (arrival ≥ 90 % per sector, error ≤ 0.25 m, ready ≥ 80 %, falls ≤ 1 %, retention within 5 points per family): **none of the three passes.** D1 fails three right-side sectors and three families; D1b and D1c fail more.

## Reading
1. **Both follow-ups traded one skill for another.**
   - More right-side practice (D1b) broke forward movement.
   - More hitting practice (D1c) neither held hitting nor kept the right side. The higher hitting reward in training did not carry over to the fixed-start retention test, and the right side fell further.

   This is the shared-policy trade-off D-042 replaces with specialist teachers and distillation.
2. **The right (paddle) side is the persistent weak direction** in all three runs. The walking teacher, with no hitting to compete with, tests whether this is interference or a body/stance limit.
3. **High balls improve in every run** (+7 to +11 points). Moving seems to help with high balls.

## Walking-teacher parent (D-042)
**`drill-move-d01/model_13900` (D1):** the highest overall arrival rate (91.0 %), with the best right side of the three and the best retention. This is a choice between completed fixed endpoints on dev seeds, as recorded in D-042.

Files: `stage5-run-d1.md`, `stage5-run-d1b.md`, this file, and `stage5-d1c-{move,retention-A,retention-parent-A}.json`.
