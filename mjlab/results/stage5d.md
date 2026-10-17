# Stage 5D: rally training (D-091)

Gate: P(rally >= 10) >= 20 %; court falls <= 1 %; style <= 3.86; move-to-spot arrival >= 90 % every direction; court main metric >= 76.8 % (run 22 final 78.8 % minus 2). Budget 15 runs.

Start point: Stage 5C candidate run 22 (`s5c-22-res-rally/model_900`): rally P(>= 10) 1.6 % (90 s, seed 4200860), court-anchored legal 61.8 %, court falls 3.3 %, style 4.017, arrival 99.4-99.95 %, court main metric 78.8 %.

## Runs
| # | Run | Change (written before launch) | From | Endpoint | P(rally >= 10) | Court main | Falls | Style |
|---|---|---|---|---|---|---|---|---|
| 1 | s5d-01-rally | PPO continuation of run 22 on the rally drill (D-092) | s5c-22/model_900 | model_1800 (cap) | **9.67 %** [9.05, 10.34] | 77.9 % | court 6.1 %, move 0.15 % | **4.199 (kill rule)** |
| 2 | s5d-02-rally-style | run 1's recipe + style anchor: prior penalty on the composite latent, 0.05 (D-093) | s5c-22/model_900 | model_1800 (cap) | 7.57 / 7.73 % | 77.8 % | court 5.1 %, move 0.08 %; **arrival right 85.8 / 86.6 % (kill rule)** | 4.148 / 4.133 |
| 3 | s5d-03-rally-speed | run 1's recipe + overspeed penalty -0.5 (v - 1.2)^2 (D-094) | s5c-22/model_900 | model_1800 (cap) | 8.44 / 8.96 % | 78.0 % | court 4.7 %, move 0.1 % | **4.210 (kill rule)** |
| 4 | s5d-04-rally-gait | run 1's recipe + gait anchor to the walking teacher while walking (D-095) | s5c-22/model_900 | iteration 1,900 or last before the cap | | | | |

## Notes
- **Run 1** (dev seeds 4200930-935): rally P(>= 10) 1.6 -> **9.67 %**, mean ended rally 2.68.
  - Arrival 99.5-100 %, recovery 1.175 m, court 77.9 %.
  - Court falls rose to 6.1 %, and style 4.199 triggers the kill rule (> 4.17), so run 1 is not built on.
  - Style drifts because the residual tasks dropped the prior penalty on the composite latent (D-093).
- **Run 2:** the style anchor at 0.05 moved style by only about -0.05 and cost rally (7.65 %) and rightward arrival (kill rule).
- **Style breakdown** (D-094): h4-25b scores 3.88 on the court drill.
  - Fast poses (>= 0.8 m/s) sit at about 4.5 for every executor.
  - Rally training raises the fast share (32 % -> 39 %).
  - The style gate (3.86) may be out of reach on this drill. It stays as written.
- **Run 3:** the overspeed penalty barely engaged. Style 4.21 (kill rule) and rally 8.7 % make it plateau strike 2, so run 4 must reach at least 11.67 %.

