# Stage 5D: rally training (D-091)

Gate: P(rally >= 10) >= 20 %; court falls <= 1 %; style <= 3.86; move-to-spot arrival >= 90 % every direction; court main metric >= 76.8 % (run 22 final 78.8 % minus 2). Budget 15 runs.

Start point: Stage 5C candidate run 22 (`s5c-22-res-rally/model_900`): rally P(>= 10) 1.6 % (90 s, seed 4200860), court-anchored legal 61.8 %, court falls 3.3 %, style 4.017, arrival 99.4-99.95 %, court main metric 78.8 %.

## Runs
| # | Run | Change (written before launch) | From | Endpoint | P(rally >= 10) | Court main | Falls | Style |
|---|---|---|---|---|---|---|---|---|
| 1 | s5d-01-rally | PPO continuation of run 22 on the rally drill (D-092) | s5c-22/model_900 | model_1800 (cap) | **9.67 %** [9.05, 10.34] | 77.9 % | court 6.1 %, move 0.15 % | **4.199 (kill rule)** |
| 2 | s5d-02-rally-style | run 1's recipe + style anchor: prior penalty on the composite latent, 0.05 (D-093) | s5c-22/model_900 | iteration 1,900 or last before the cap | | | | |

## Notes
- **Run 1** (dev seeds 4200930-935): rally P(>= 10) 1.6 -> **9.67 %**, mean ended rally 2.68.
  - Arrival 99.5-100 %, recovery 1.175 m, court 77.9 %.
  - Court falls rose to 6.1 %, and style 4.199 triggers the kill rule (> 4.17), so run 1 is not built on.
  - Style drifts because the residual tasks dropped the prior penalty on the composite latent (D-093).

