# Panel round 106 brief: D-245 SMOKE-FAIL on the cap-split share, 2026-11-08

Read first: D-243 to D-245 at the end of docs/DECISIONS.md; rounds 103-105 in mjlab/results/footwork-review.md; results/lc107-summary.txt; results/lc107-smoke-share.jsonl and results/lc105-smoke-share.jsonl; docs/PANEL.md.

## Result

D-245's smoke (rally-d1s3q8w2-smoke, seed 253, 160 iterations from Q with feed-mix x2 on reach_deep, cross_backhand, reach_backhand) passed seven of eight lines. The eighth, the cap-split line, has four parts:

| part | read | line | result |
|---|---|---|---|
| pair-court feeder share | **0.1642** | 0.1306 +/- 25 % (top 0.1633) | **FAIL by 0.0009** |
| set-start half longest rally | 8 | <= 8 | pass |
| free-half rallies ending 9-15 | 72 (16.7 % past 8) | > 0 | pass |
| three-family share of feeder balls | 0.302 of 12,031 | 0.261 +/- 25 % (0.196-0.326) | pass |

**Why the share prediction missed (the agent's error, the third time on this line):** the 0.1306 prediction came from Q's own training log (second half, 12,288 envs). A smoke from the same parent reads higher on its own: Q's smoke (D-243, seed 249) read 0.1497 under the same recipe and 1,024 envs. The dose adds to it: harder feeder balls end more rallies early. Smoke training windows over +20-140:

| smoke | reset-half h0 / h1 / (1-h0)(1-h1) | free-half h0 / h1 | feeder share |
|---|---|---|---|
| D-243 (Q's recipe) | 0.145 / 0.187 / 0.695 | 0.338 / 0.388 | 0.1497 |
| D-245 (+ the dose) | 0.172 / 0.214 / 0.652 | 0.339 / 0.437 | 0.1642 |

So the dose works as intended (the three families are 30 % of feeder balls, and the policy misses more of them early in training), and the cap mechanics are unchanged. The share line itself was a check on the cap, which this run does not change.

No training ran. Seeds: training 252 unused; smoke 253 spent; dev 4220435 used for Q's stage-0 direction read.

## Questions

1. **Correction check.** Is SMOKE-FAIL right as coded? What is the right reference for a smoke's share prediction?
2. **Next.** Vote:
   - **(a)** re-run D-245 unchanged on a fresh smoke seed, the share re-predicted (from which basis? recorded before the run), band unchanged;
   - **(b)** something else (name it, with the simpler option).
3. **Target estimate**, briefly.

Under 200 words.
