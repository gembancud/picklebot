# Review round 17: Stage 5G used up; re-plan the route to the rally video (2026-10-21)

Brief: Stage 5G has used 6 of 6 runs.
- Every timed controller returns about 15 % of court feeds legally.
- E5 and E6 were killed in a row; both ball-PPO runs broke the ball-free goal skill.
- The D-127 decomposition puts the loss in the controller.
- The Stage 5F executor (run 4: drill v2 0.843, court main 75.9 %) hits the wrong ball for a rally: 11.5 m/s, low, heavy backspin. R2 8.2 %, R4 P(4+) 0.0002.

## Correction check (5 of 5)

- **E5 and E6 were read correctly,** and both kills count.
- **The bank guard stays as it is** (5 of 5). It measures the commanded-paddle skill the planner relies on (RL, motion, architecture). It decided neither kill alone: E5 also failed its legal line, and E6's legal pass (15.26 % against 15.24 %, about +-1.3 points) is noise. It is a proxy (experiment design, coach), and replacing it needs a D-entry naming D-124's premise.
- **Two premises are named:**
  - legal returns went flat after about 160 iterations, before any forgetting, so 15 % is a structural ceiling of the timed controller with the latent-07 prior (motion, architecture: even the planned keep-alive ball needs about 11 m/s, and E3 delivers 8.0);
  - no 5G reward ever paid for where the ball lands (coach).
- **D-124's "no rehearsal" tie-break was an error** (RL, experiment design). Stage 5F had already shown the forgetting and fixed it with rehearsal.
- **From now on, kill lines are reported with their intervals.** A line at the parent's point estimate cannot show progress (experiment design, architecture).
- **The 5F and 5G legal numbers are not directly comparable** (experiment design): 5F's is a cell-averaged court metric, 5G's is pooled per feed through the planner.

## Decisions

1. **The route: Stage 5H, at most 4 runs, back to the Stage 5F executor** (5 of 5; option b).
   - **The gap, stated plainly:** about 56 % legal per shot is needed. Today R2 is 8.2 %, R4 is about 0.36 per side, P(4+) 0.0002.
   - **Why not (a), the 5G timed controller with rehearsal:** rehearsal guards the bank, not the 15 % ceiling. It would also be 100-150 lines inside the CUDA-graphed goal setter (architecture).
   - **Experiment design's fair cross-lineage read** (pairs plus a 2x2 own-ball cross-replay) got 1 of 5. It is recorded, not adopted.
2. **Run 1's one change:** run 4's recipe exactly (court mix 0.4, seed 73, 12,288 envs, 800 iterations). The pace term `return_shaping` is replaced, at the same weight (100) and place, by `keep_alive_landing`.
   - **The score:** the real simulated legal landing (drag, spin, the net) scored by `planner.keep_alive_score`. It is 1 in the box (x 4.7-5.7, |y| <= 1) with a flight of 1.3-1.5 s, and falls linearly to 0 at 1 m outside the box and 0.5 s outside the window (the tails fixed before any data was read).
   - **Unchanged:** net clearance, placement, the rally bonus and legal_return.
   - **Parent:** s5d-01-rally/model_1800 (4 of 5; run 4 was killed and is never a parent). So run 4 is the clean A/B comparator.
   - **Code:** about 35 lines plus tests.
3. **Pre-launch checks, all passing:**
   - `test_d129_keep_alive_score_and_ranking`: a box legal return > the parent's typical fast legal return > not legal > a fall;
   - `test_d129_task_changes_only_the_pace_term`;
   - **on the parent's recorded legal returns** (`selfplay-r2-s5d01-returns.pt`, 26,113): 56.9 % score above 0 (bar >= 5 %; RL, architecture), mean 0.12. Flight 0.85 / 1.00 / 1.19 s and landing x 3.2 / 4.3 / 5.3 m (10th / 50th / 90th percentiles); median |y| 1.43 m (`results/s5h-keepalive-precheck.json`).
4. **Kill at model_2100** (run 4's point), with the parent read on the same development seeds:
   - drill v2 or court main more than 5 points below the parent (5 of 5);
   - move arrival below 90 %;
   - court falls above 7.4 % per episode (RL, architecture);
   - **the progress line:** the keep-alive box share of legal landings not above the parent's.

   The progress line was a tie: box share (RL, architecture) against own-ball legal (motion, experiment design). The tie went to the least code; the box share needs no record-and-replay. Speed is reported.
5. **Endpoint:** the D-113 stage rules (h5f_clean_eval), plus R2 and R4 on development seeds. **Pair-mode P(4+) is the primary readout.** R3 falls stay open, so any video is labelled interim.
6. **Back to the user when any of these happens:**
   - a qualifying video exists;
   - the route needs runs over 2 h, a bigger controller or a new prior;
   - Stage 5H ends without a credible route: own-ball legal not doubled by run 2 (experiment design), or P(4+) under 1 % at the end (RL, motion, architecture).
