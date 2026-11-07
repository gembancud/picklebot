# Panel round 104 brief: D-243 CONFIRMED; the next run toward the target, 2026-11-08

Read first: D-240 to D-243 with results at the end of docs/DECISIONS.md; rounds 100-103 in mjlab/results/footwork-review.md; results/lc105-summary.txt; results/rally-target.md; docs/PANEL.md.

## Result

Q = rally-d1s3cap8hr2 model_36793 (the D-241 child + pair_rally_cap 8 on the set-start half only) passed the gate and CONFIRM.

| | C | M | N (D-240) | P (D-241) | **Q (D-243)** |
|---|---|---|---|---|---|
| P(5+) gate seeds | 0.5645 | 0.7454 | 0.7660 | 0.7817 | **0.7759** |
| P(5+) fresh seeds | 0.5854 / 0.5734 | - | 0.7687 | - | **0.7761** |
| h0 / h1 (gate) | 0.245 / 0.187 | 0.128 / 0.096 | 0.110 / 0.088 | 0.091 / 0.084 | **0.117 / 0.075** |
| h2 / h3 / h4 (gate) | 0.065 / 0.013 / 0.003 | 0.040 / 0.012 / 0.003 | 0.039 / 0.013 / 0.004 | 0.039 / 0.019 / 0.005 | **0.036 / 0.012 / 0.003** |
| K3 late share (gate) | 0.0269 | 0.0276 | 0.0310 | 0.0423 | **0.0245** |
| left + back vs parent (gate) | | -5.1 | -3.5 | -2.7 | **-3.1** |
| left contact (gate) | 0.407 | 0.346 | 0.349 | 0.359 | **0.346** |

**Target:** P(5+) >= 0.80 with Wilson low >= 0.78 over >= 1,000 dev rallies. With Q's h1-h4, P(5+) 0.80 needs h0 about 0.085, and the Wilson bar about 0.075. P had h0 0.091; Q gave some of that back when half the courts stopped capping (the free half's opening is 0.42-0.50 in training).

**Resources:**
- The GPU is running the GVHMR body pass on 58 user-marked pro-singles rallies (about 1-2 h). No training until it finishes.
- Training seeds from 250; dev seeds from 4220421. No unread CONFIRM block remains; a new one must be allocated.

## Questions

1. **Correction check.** Anything wrong in D-243 or its reads?
2. **Next.** Vote, with the parent (Q by default), the one change aimed at h0 without giving back K3 or the guard, lines and seeds. Name the simpler option if you propose something bigger. Whether the human-footwork reference (once the body pass is in) should enter now or later is also in scope.
3. **Target estimate**, briefly.

Under 250 words.
