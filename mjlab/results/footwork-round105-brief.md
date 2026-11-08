# Panel round 105 brief: D-244 NO-CANDIDATE on K3-KEPT and OPEN, 2026-11-08

Read first: D-240 to D-244 with results at the end of docs/DECISIONS.md; rounds 100-104 in mjlab/results/footwork-review.md; results/lc106-summary.txt, results/lc106-kill.txt; results/rally-target.md; docs/PANEL.md.

## Result

Child = rally-d1s3cap5hr model_37392: Q + pair_rally_cap 5 (was 8) on the set-start half only.

| | Q (D-243, CONFIRMED) | child (D-244) | line |
|---|---|---|---|
| P(5+) gate seeds | 0.7759 | **0.7880** (best) | Q-KEPT pass |
| h0 / h1 | 0.117 / 0.075 | 0.106 / 0.068 | |
| h2 / h3 / h4 | 0.036 / 0.012 / 0.003 | 0.042 / 0.010 / 0.003 | |
| OPEN (1-h0)(1-h1) | 0.8172 | 0.8337 (+0.0165) | **>= Q + 0.02: FAIL** |
| K3 late share | 0.0245 | **0.0342** | **<= C 0.0269 + 0.005: FAIL** |
| rally endings 3-4 / 5-7 / 8+ | 63 / 7 / 33 | 56 / 6 / **83** | reported |
| left + back vs parent | -3.1 | -3.1 | pass |
| R3 | 0.0324 | 0.0229 | pass |

The K3 excess is entirely at rallies that already passed 8 shots (83 vs 33; C 33); endings at shots 3-4 fell. P(5+) does not count those endings, but K3-KEPT gates them and is not loosened.

**Pattern across the cap runs:** a stronger set-start cap gives a better opening and worse long rallies (D-240 cap 8 everywhere: K3 0.0310; D-241 cap 8 everywhere + half reset: 0.0423; D-243 cap 8 set-start only: 0.0245; D-244 cap 5 set-start only: 0.0342).

**Target:** P(5+) >= 0.80. The child is 1.2 points short on the gate seeds. With its h1-h4, h0 <= about 0.093 would reach 0.80.

**Resources:** the GPU is free. Training seeds from 252; dev seeds from 4220434 (4220425-4220433, the registered target-read block, was not read and may be re-registered).

## Questions

1. **Correction check.** Anything wrong in D-244 or its lines? Were OPEN's +0.02 and K3's +0.005 the right lines for this lever?
2. **Next.** Vote, with the parent (Q, or the child as warm start?), the one change, lines and seeds. The aim: keep or extend the opening gain without the long-rally cost. Name the simpler option if you propose something bigger.
3. **Target estimate**, briefly.

Under 250 words.
