# Panel round 103 brief: D-242 SMOKE-FAIL on the cap-split line, 2026-11-07

Read first: D-242 at the end of docs/DECISIONS.md; round 102 at the end of mjlab/results/footwork-review.md; results/lc104-summary.txt; results/lc104-smoke-share.jsonl; docs/PANEL.md.

## Result

D-242's smoke (rally-d1s3cap8hr-smoke, seed 247, 160 iterations) passed seven of its eight lines. It failed the cap-split line on one of its three parts:

| part | read | line | result |
|---|---|---|---|
| pair-court feeder share | **0.1555** | prediction 0.124 +/- 25 % (0.093-0.155) | **FAIL, by 0.0005** |
| reset-half longest rally | 8 | <= 8 | pass |
| free-half rallies ending at 9-15 | 63 (18.3 % of 819 free-half rallies went past 8) | > 0 | pass |

So the masked cap works as coded: the reset half never goes past 8, and the free half rallies past it.

**Why the prediction missed (the agent's error):** the agent predicted 0.124 by assuming the free half would average about 12 balls per rally once uncapped. In the smoke it averaged 5.74 (the reset half 5.43). Free-half rallies still end early: hazards h0-h7 are 0.283 / 0.412 / 0.220 / 0.130 / 0.111 / 0.082 / 0.058 / 0.072, because the free half starts from where the robots ended. The share is above the band, so the run gives more opening practice than predicted, not less; and fewer free-half rallies reach the late shots than the panel may have expected.

No training ran. Seeds: training 246 unused; smoke 247 used; dev 4220419 used for P's stage-0 direction read.

## Questions

1. **Correction check.** Is SMOKE-FAIL right as coded? What does the free half's early collapse (h1 0.41) say about the lever?
2. **Next.** Vote, with the parent, the change, lines and seeds:
   - **(a)** Re-run D-242 unchanged with a new smoke seed, the share line re-predicted from this smoke's measured balls per rally and recorded before the re-run.
   - **(b)** A different lever (name it, with the simpler option).
   - **(c)** Other.
3. **Target estimate**, briefly.

Under 200 words.
