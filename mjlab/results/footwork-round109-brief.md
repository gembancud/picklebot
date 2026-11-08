# Panel round 109 brief: D-249 (the pro-move drill) NO-CANDIDATE, 2026-11-09

Read first: D-243 to D-249 with results at the end of docs/DECISIONS.md; rounds 105-108 in mjlab/results/footwork-review.md; results/lc110-summary.txt, results/lc110-kill.txt; results/rally-target.md; docs/PANEL.md; mjlab/picklebot_mj/tasks/pro_move.py.

## Result

D-249 = rally-d1s3pro1: Q + move-episode spots drawn from 167 pro moves (one PPA singles match), unscaled, MoveDrill's 4 x 5.6 m box (flip / shrink), untimed limit. Smoke 9/9 ok (flipped 0.320, clipped 0.488 of issued spots; arrived 0.924). Kill at +240 all CONTINUE (OPEN-DEV 0.7898 vs Q 0.8018, inside the -0.02 line; left contact 0.372 vs Q 0.350 on 4220440).

| gate line (pooled 4220385-88 / dir 4220307, 34-36) | child model_37392 | reference | result |
|---|---|---|---|
| GAIN2 vs C | +18.92, lower bound +17.32 | | pass |
| left + back guard | 0.4178 vs parent 0.4557 (-3.8) | kill below -5 | pass |
| H0 / FEEDER / K3-KEPT / R3 | 0.128 / 0.8737 / 0.0213 / 0.0260 | | pass |
| **OPEN vs Q** | **0.7956 vs 0.8172 (-0.0216)** | **>= +0.02** | **FAIL** |
| M / N-KEPT | P(5+) 0.7537 | | pass |
| **P / Q / D244-KEPT** | **0.7537 vs 0.7817 / 0.7759 / 0.7880** | **>= -0.02** | **FAIL** |

Hazards h0-h4 0.128 / 0.088 / 0.039 / 0.012 / 0.002 (Q 0.117 / 0.075 / 0.036 / 0.012 / 0.003). Direction contact forward 0.884, left 0.332, back 0.647, right 0.770 (M 0.914 / 0.346 / 0.568 / 0.783).

## Where the climb stands

Since D-243 (Q, CONFIRMED, P(5+) 0.776) seven children read 0.754-0.788: cap 5 (K3 fail), feed dose x2 (killed on a mix-biased line; re-run OPEN +0.009), pro-move drill (OPEN -0.022). The target needs h0 about 0.089 at Q's h1-h4 (Q 0.117; best child 0.101). Left feeder contact sits at 0.33-0.37 in every run. The user (D-228) wants fast, humanlike movement and does not care about motor limits; footwork phase (D-226) asked for a set start or a body / controller change.

## Resources

GPU free. Training seeds from 261; dev 4220443+ free; the target-read block 4220425-4220433 unread.

## Questions

1. **Correction check** on D-249 (lines, the box distortion, anything mis-read).
2. **Next.** Vote one, naming the simpler option if you choose a bigger one:
   - **(a)** pro-move drill again with the spot box extended (deeper behind the baseline, wider), so the pro moves land unclipped; parent Q;
   - **(b)** back to the D-248 feed dose with one change aimed at h1;
   - **(c)** a body / controller change toward speed (the user's 3-4 m/s; motor limits are not a constraint), say which and how it is tested;
   - **(d)** other, or a STOP vote (under D-169 a STOP moves the loop to the next phase; name it).
   Give the form: parent, the one change, lines, seeds.
3. **Target estimate**, and what the video route has shown so far.

Under 250 words.
