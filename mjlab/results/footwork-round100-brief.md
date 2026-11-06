# Panel round 100 brief: D-239 NO-CANDIDATE on K3-KEPT, 2026-11-07

Read first:
- D-226 to D-239 with their results at the end of docs/DECISIONS.md (D-226 STOP and its asks; D-228 the user's "fast humanlike movement, does not care about realistic motor limits");
- rounds 95-99 in mjlab/results/footwork-review.md;
- results/lc101-summary.txt (this gate) and results/lc98-summary.txt (M's gate);
- results/rally-target.md;
- docs/PANEL.md.

## Result

N = rally-d1s3drl6 model_35595 (M + launcher courts + left / back move drill x3, continued from rally-d1s3drl5 model_35320). Gate on dev 4220385-4220388 / 4220307, 4220334-4220336:

| line | N | reference | result |
|---|---|---|---|
| GAIN2 vs C | +17.68 points (lower bound +15.67) | | pass |
| left + back guard | 0.4165 vs parent 0.4557 (-3.9) | kill below -5 | pass |
| H0, FEEDER, mechanism | 0.117 hazard, 0.887 legal | | pass |
| **K3-KEPT late failure share** | **0.0394 vs C 0.0269** | **<= +0.005** | **FAIL** (M read 0.0276) |
| M-KEPT P(5+) | 0.7413 vs M 0.7454 | >= -0.02 | pass |
| R3 court, dev 4220403 | 0.0245 (M 0.0306) | <= 0.04 | pass |

Hazards h0-h4: N 0.117 / 0.105 / 0.041 / 0.016 / 0.006; M 0.128 / 0.096 / 0.040 / 0.012 / 0.003.
Direction contact N vs M: forward 0.902 / 0.914, left 0.343 / 0.346, back 0.600 / 0.568, right 0.784 / 0.783.

**Arithmetic toward the target.** P(5+) is the product of (1 - h_k) for k = 0..4. With N's hazards it is 0.741. With h0 = 0.08 and h1 = 0.06 and the rest unchanged it would be about 0.81. Left contact (0.34) is the largest single gap; it has not moved in three runs of left-weighted drilling (D-236 to D-239).

**Target:** P(5+) >= 0.80, Wilson low >= 0.78. Best unpromoted: M 0.7454.

**Resources:**
- The GPU is free.
- Training seeds from 242; dev seeds from 4220404 (4220349-4220356 and 4220399 unread).
- The human-footwork video route is still being built and is not ready to feed training. Its first pass failed (wrong person tracked, camera cuts). The user is now marking clean rally ranges by hand in one 1080p singles match.

## Questions

1. **Correction check.** Was D-239, or its implementation, wrong? Is the K3 fail real or noise (n, SE)?
2. **Next.** Vote, with the parent, lines and seeds:
   - **(i)** Drop the left / back dose and go back to the opening: one change aimed at h0 / h1, with M as the parent.
   - **(ii)** A body / controller change for left footwork, under D-228 (the user does not care about realistic motor limits), with M as the parent.
   - **(iii)** Other, with the simpler option named.
3. **Target estimate**, briefly.

Under 250 words.
