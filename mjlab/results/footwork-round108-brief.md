# Panel round 108 brief: the user's direction, train with the pro footwork videos; D-248 NO-CANDIDATE, 2026-11-08

Read first: D-243 to D-248 with results at the end of docs/DECISIONS.md; rounds 104-107 in mjlab/results/footwork-review.md; results/lc109-summary.txt; results/rally-target.md; docs/PANEL.md; the move drill code (mjlab/picklebot_mj/tasks/move_drill.py, deadline_drill.py, agility.py FastMoveDrill).

## The user's direction (2026-11-08)

"lets see if the pickleball videos help with training shall we?" The direction is set by the user; this round sets its form (parent, the one change, lines, seeds).

## D-248 result

NO-CANDIDATE on OPEN alone: (1-h0)(1-h1) 0.8258 vs Q 0.8172 (+0.0086, needed +0.02). Every other line passed (K3 0.0206, left + back -4.1, R3 0.0231, P(5+) 0.7852). h0 fell 0.117 -> 0.101, h1 rose 0.075 -> 0.081. Since D-243 (Q, CONFIRMED, 0.776) every child has read P(5+) 0.776-0.788.

## The video data (CPU, artifacts git-ignored under mjlab/artifacts/motion/pb-pilot/)

- 63 user-marked rallies from one pro singles match (PPA, fixed broadcast camera behind the near baseline); 58 passed the near-player tracking check; GVHMR SMPL body tracks for all 58 (out_ppa/cNN/hmr4d_results.pt), ViTPose 2-D keypoints (preprocess/vitpose.pt).
- Court-line homography from 6 court points (reprojection error 1-3 px; verified on 5 clips across the match): the near player's feet in metric court coordinates.
- **208 single moves** (ppa_moves.json; a move = from one settled spot to the next on the 0.5 s-smoothed foot track, >= 0.5 m): per move the start spot, displacement (dx across, dy toward the net), duration, mean speed. Medians: left 63 moves 2.24 m in 1.57 s; right 73 moves 1.87 m in 1.10 s; forward 41 moves 4.69 m in 2.93 s; back 31 moves 2.36 m in 2.60 s (18 backpedals >= 2 m). 124 moves cover >= 2 m. Peak speeds from the foot track are inflated by keypoint jumps (some > 10 m/s) and are not trustworthy; mean speeds are about 1.2-1.6 m/s.
- Reference: the robot's body tops out near 2 m/s; human court-foot speed p90 about 2.9 m/s, p99 about 4.4 m/s (ppa_court_stats_smooth15.csv).
- No retargeting to the G1 exists yet.

## Options to weigh (name the simpler option if you choose a bigger one)

- **(a) A pro-move drill:** the existing move-to-spot drill draws its spot and deadline from the 208 pro moves (displacement and time, scaled or not to the robot) instead of its own sampler. Reuses the drill; small code.
- **(b) Full-body imitation:** retarget the GVHMR bodies to the G1 and add a tracking or style reward, or rebuild the motion prior. Large.
- **(c) Other.**

## Questions

1. **Correction check** on D-248.
2. **The form:** parent (Q or D-248's child), the one change, how the human moves map to the robot (distances, deadlines, scaling), smoke / kill / gate / CONFIRM lines and seeds (training from 258; dev 4220439+ free; the target-read block 4220425-4220433 unread).
3. **Target estimate**, and what this route can and cannot show.

Under 250 words.
