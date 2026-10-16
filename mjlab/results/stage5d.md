# Stage 5D: rally training (D-091)

Gate: P(rally >= 10) >= 20 %; court falls <= 1 %; style <= 3.86; move-to-spot arrival >= 90 % every direction; court main metric >= 76.8 % (run 22 final 78.8 % minus 2). Budget 15 runs.

Start point: Stage 5C candidate run 22 (`s5c-22-res-rally/model_900`): rally P(>= 10) 1.6 % (90 s, seed 4200860), court-anchored legal 61.8 %, court falls 3.3 %, style 4.017, arrival 99.4-99.95 %, court main metric 78.8 %.

## Runs
| # | Run | Change (written before launch) | From | Endpoint | P(rally >= 10) | Court main | Falls | Style |
|---|---|---|---|---|---|---|---|---|
| 1 | s5d-01-rally | PPO continuation of run 22 on the rally drill (D-092) | s5c-22/model_900 | iteration 1,900 or last before the cap | | | | |
