# Panel round 99 brief: D-238 KILL-NO-HIT on a restart-biased line, 2026-11-06

Read first:
- D-236, D-237 and D-238 with their results at the end of docs/DECISIONS.md;
- rounds 96-98 in mjlab/results/footwork-review.md;
- results/lc100-kill.txt and results/lc100-summary.txt;
- results/rally-target.md;
- docs/PANEL.md.

## Result

N = rally-d1s3drl5 is M (rally-d1s3drl3 model_34996, unpromoted) with the move drill weighted x3 on left / back. It was killed at +180. Kill lines over +61-180:

| line | value | needed | result |
|---|---|---|---|
| KILL-NO-HIT: pair-court rally length | 11.714 vs M's last 120 iterations 14.584 (0.80x) | >= 0.9x | KILL |
| KILL-UNSTABLE: exact falls off the launcher courts | 0.448 | <= 3.14 | pass |
| KILL-LOST-OPEN | 0.6618 -> 0.6656 | | pass |
| KILL-NO-FALLS (dev 4220402) | 0.0257 | <= 0.04 | pass |
| **KILL-DIR: left + back contact** (dev 4220402) | **0.4469 vs M 0.4191 (+2.8 points)** | | pass |
| Right contact (reported) | 0.7744 vs 0.7726 | | |

Checkpoints exist up to model_35160 (+164).

**Restart dip (found after the kill).** Pair-court mean rally length by window after each run's (re)start:

| run | +1-60 | +61-180 | +181-300 | later |
|---|---|---|---|---|
| L (from R) | 3.7 | 12.05 | 14.90 | 14.30 (+241-360) |
| M (resumed from 34160) | 2.6 | 12.21 | 14.29 | 14.72 (end) |
| R (from C) | 3.0 | 10.96 | 13.09 | 13.86 (end) |
| N (from M) | 3.4 | **11.71** | - | - |

N's 11.71 is 0.96x M's own +61-180 post-restart window. The coded line compared a post-restart window with the parent's settled end window. It came from round 97's form, and the agent did not check the transient.

**Target:** P(5+) >= 0.80 with Wilson low >= 0.78. M is at 0.745; the opening (h0, h1) is the binding lever.

**Resources:**
- The GPU is free. The GVHMR pickleball pilots are running in the gap: three user-approved singles videos plus one 50+ clip.
- Training seeds from 241. Dev seeds from 4220404 (4220403, 4220399 and 4220349-4220356 unread).

## Questions

1. **Correction check.** Is the KILL right as coded, and is the restart-dip diagnosis honest?
2. **Next.** Vote, with parent, lines and seeds:
   - **(i) Continue N** from model_35160 to the fixed endpoint model_35595, with KILL-NO-HIT re-read on a paired window (N's +181-300 against M's own +181-300 post-restart window, >= 0.9x).
   - **(ii) Rerun from M** with that corrected line, on a fresh seed.
   - **(iii) Other.**
3. **Target estimate**, briefly.

Under 250 words.
