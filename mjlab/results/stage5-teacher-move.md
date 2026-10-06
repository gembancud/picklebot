# Stage 5 walking teacher (`teacher-move-01`): gate passed on the first chained run

Date: 2026-10-06. Task `Picklebot-Teacher-Move-G1`: move-to-spot episodes only, uniform sectors, same rewards and inputs as Drill 1, no hitting. Parent: `drill-move-d01/model_13900` (D1; see `stage5-drill1.md`). 4096 envs, train seed 1, 7,000 s cap: iterations 13,900 → 15,905. **Fixed endpoint `model_15900`.** Chain run 1 of at most 4 (loop rule 9); chaining stops because the gate is met.

## Training
- **Arrival reward:** about 0.13 per episode at the start (D1's level adjusted for its 75 % move share), then 0.27 at 14,000, 0.51 at 14,500 and 0.61–0.65 from 14,750 on.
- **Health:** falls 0–0.04, value loss 0.017–0.06, action std 0.53 → 0.33.

## Evaluation (dev seed 4,200,130; 2048 envs × 24 s; 17,791 finished spots)
| Direction | Arrival | Mean time | Median final error | Ready stance at arrival | D1 arrival |
|---|---:|---:|---:|---:|---:|
| forward | 100 % | 2.52 s | 0.175 m | 100 % | 97.7 % |
| forward-left | 100 % | 2.43 s | 0.175 m | 99.96 % | 98.6 % |
| left | 100 % | 2.31 s | 0.175 m | 99.95 % | 97.4 % |
| back-left | 98.95 % | 2.07 s | 0.175 m | 99.8 % | 99.6 % |
| back | 99.5 % | 2.02 s | 0.175 m | 100 % | 94.5 % |
| back-right | **100 %** | 2.09 s | 0.175 m | 100 % | 63.0 % |
| right | **99.96 %** | 2.32 s | 0.175 m | 100 % | 82.6 % |
| forward-right | **100 %** | 2.49 s | 0.175 m | 100 % | 88.0 % |
| **all** | **99.84 %** | — | 0.175 m | 99.97 % | 91.0 % |

**Falls:** 0 in 6,144 robot episodes.

## Gate (≥ 95 % arrival in every sector, median error ≤ 0.25 m, ready stance ≥ 90 %, falls ≤ 1 %): **PASS**
Every sector is at 98.95 % or above.

## What this shows
**The right-side weakness of D1, D1b and D1c was interference from sharing the policy with hitting, not a body or stance limit.** With walking as its only skill, the same network from the same parent reaches 99.96–100 % on the right side within one 2-hour run. This is direct evidence for D-042.
