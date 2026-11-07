# Panel round 101 brief: D-240 CONFIRM-FAIL on the left + back guard, 2026-11-07

Read first:
- D-236 to D-240 with their results at the end of docs/DECISIONS.md;
- rounds 98-100 in mjlab/results/footwork-review.md;
- results/lc102-summary.txt (gate and CONFIRM) and results/lc102-kill.txt;
- results/rally-target.md;
- docs/PANEL.md.

## Result

N = rally-d1s3cap8 model_35595 (M + the training-only pair_rally_cap 8 on the launcher-court task).

**Gate (dev 4220385-4220388 / 4220307, 4220334-4220336): CANDIDATE.** Every line passed: GAIN2 +20.15; left + back guard -3.5; K3 +0.0041 (line +0.005); M-KEPT 0.7660 vs 0.7454; OPEN 0.8117 vs M 0.7883 (+0.0234); R3 0.0274.

**CONFIRM (fresh dev 4220349-4220356, C re-read on the same seeds): CONFIRM-FAIL.**

| line | N | C (fresh) | result |
|---|---|---|---|
| GAIN2 | P(5+) 0.7687 vs 0.5854 (+18.33, lower bound +16.72) | | pass |
| worst family | +1.6 | kill below -5 | pass |
| **left + back contact** | **0.4320 (n 2907) vs 0.4843 (n 2771): -5.2** | **kill below -5** | **FAIL** |
| R3, dev 4220399 | 0.0237 | <= 0.04 | pass |

Reported: binomial SE of the guard difference about 1.3 points. Direction contact N vs C: forward 0.899 / 0.922, left 0.368 / 0.434, back 0.617 / 0.623, right 0.783 / 0.750. K3 (reported only in CONFIRM) 0.0287 vs 0.0199. C read 0.4557 on left + back on the gate seeds and 0.4843 on the fresh ones.

**History of this guard:** M failed it at the gate (-5.1). N passed at the gate (-3.5) and failed at CONFIRM (-5.2). Left contact has sat at 0.34-0.37 since D-236 in every child, against C's 0.41-0.43.

**Target:** P(5+) >= 0.80, Wilson low >= 0.78. N is at 0.766-0.769 on two seed sets. The guard is not loosened.

**Resources:**
- The GPU is free.
- Training seeds from 244; dev seeds from 4220406. No unread CONFIRM block remains: a new one must be allocated from the 4220406+ range.
- The human-footwork clips: 63 user-marked rallies from one pro singles match, near-player boxes done (5 clips with large tracking gaps). The 3-D body pass has not run.

## Questions

1. **Correction check.** Was D-240, or its implementation, wrong? Is the CONFIRM fail real (n, SE), and what does it say about left?
2. **Next.** Vote, with the parent, the one change, lines and seeds:
   - **(i)** One change from N aimed at left contact (name it), keeping the cap.
   - **(ii)** The queued damping / action-scale premise read first (reads only), then decide.
   - **(iii)** Other, with the simpler option named.
3. **Target estimate**, briefly.

Under 250 words.
