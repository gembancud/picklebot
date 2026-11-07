# Panel round 102 brief: D-241 NO-CANDIDATE on K3-KEPT alone, 2026-11-07

Read first:
- D-239 to D-241 with their results at the end of docs/DECISIONS.md;
- rounds 99-101 in mjlab/results/footwork-review.md;
- results/lc103-summary.txt, results/lc103-kill.txt, results/lc102-summary.txt;
- results/rally-target.md;
- docs/PANEL.md.

## Result

Child = rally-d1s3cap8h model_36194: N + the set start on half the pair courts, with the training-only pair_rally_cap 8 kept.

| line | child | N (D-240) | reference | result |
|---|---|---|---|---|
| P(5+) (gate seeds) | **0.7817** | 0.7660 | M-KEPT / N-KEPT | pass |
| OPEN (1-h0)(1-h1) | 0.8333 | 0.8117 | M + 0.02 | pass |
| left + back vs parent | -2.7 | -3.5 | kill below -5 | pass |
| **K3 late failure share** | **0.0423** | 0.0310 | C 0.0269 + 0.005 | **FAIL** |
| R3 | 0.0271 | 0.0274 | <= 0.04 | pass |

Every other gate line passed. Hazards h0-h4: child 0.091 / 0.084 / 0.039 / 0.019 / 0.005; N 0.110 / 0.088 / 0.039 / 0.013 / 0.004; C 0.245 / 0.187 / 0.065 / 0.013 / 0.003. Left contact 0.359 (N 0.349, C 0.407).

**The late-rally trend:** K3 read 0.0276 (M, no cap), 0.0394 (D-239 N', no cap, left / back dose), 0.0310 (D-240, cap 8), 0.0423 (D-241, cap 8, second leg). The cap ends every training rally at 8 shots, so shots 8+ are never practised; D-212's cap 5 failed K3 the same way (0.094).

**Arithmetic toward the target:** P(5+) = product of (1 - h_k), k = 0..4. With the child's h0 / h1 and N's h2-h4 it would be about 0.787; with C's late hazards about 0.789. Reaching 0.80 with Wilson low >= 0.78 needs about 0.81, so h0 / h1 must still fall and the late hazards must not rise.

**Resources:**
- The GPU is free.
- Training seeds from 246; dev seeds from 4220418. The D-241 CONFIRM block (4220409-4220417) was not read and may be reused.
- The human-footwork clips are still waiting for the user's check of the near-player boxes.

## Questions

1. **Correction check.** Was D-241, or its implementation, wrong? Is the K3 fail real (n, SE)?
2. **Next.** Vote, with the parent, the one change, lines and seeds. For example:
   - **(i)** Keep the opening practice and restore late-rally practice: the cap on half the pair courts only, or a longer cap.
   - **(ii)** Continue the child with the cap removed.
   - **(iii)** Other, with the simpler option named.
3. **Target estimate**, briefly.

Under 250 words.
