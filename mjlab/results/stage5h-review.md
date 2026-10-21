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

# Round 18: run 1 at its endpoint; run 2 (2026-10-21)

Brief: run 1 is not a kill.
- R1 is met: drill v2 0.846, and every stage rule passes.
- R2 (development seeds) is 10.0 % [9.5, 10.4], and R4 P(4+) is 0.0004.
- The keep-alive box share went 7.3 % -> 10.7 %, with ball speed still 11.2 m/s.

## Correction check (5 of 5: the implementation is right)

- **The keep-alive term is too weak:** about 0.15 x 2.0 = 0.3 per legal landing, against 5.0 for a legal return (coach, motion, architecture). It is also sparse (RL, experiment design). A dense version adds nothing (architecture).
- **Read errors:**
  - the 7.3 -> 10.7 % box share mixes protocols (court early check against the R2 recording; RL), and the early pass sat within overlapping intervals (experiment design);
  - run 4's R2 was read on readiness seeds and run 1's on development seeds, so they are not a clean comparison (experiment design);
  - `stage5h-01-r2-returns.pt` came from an R2 evaluation seed and must never be used for training (RL, experiment design, architecture).
- **The loss is mostly reception** (RL). On own balls, contact is 25.4 %; hits convert at about 39 %.

## Decisions

1. **Run 2 = (b)** (5 of 5). 40 % of feeds are run 1's own legal returns, mirrored; court feeds are 0.4 of the rest (architecture), so about 40 / 24 / 36 % replay / court / drill v2.
   - **Parent:** run 1's endpoint, model_2599.
   - **The weight change (a) is rejected:** it trains the hitter, while the gap is on the receiving side; above the legal weight it risks legal returns.
   - **Falls (c)** wait until legal returns pass about 30 % (motion).
2. **Code (D-130):** `replay_prob` with its own generator. Per env:
   - a replay draw first;
   - rally-phase flags (`return_stand.py` had made every feed rally-phase whenever a replay file was set);
   - no planner spot;
   - its own outcome tally, kept out of the per-family and drill v2 counters.

   The replay set is recorded from model_2599 on development seed 4217040, never an R2 evaluation file.
   **Tests:**
   - `test_d130_replay_prob_zero_reproduces_the_task`: one environment, every generator and state restored, because separate environments differ by their reset poses;
   - `test_d130_replay_mix_shares_and_flags`;
   - `test_d130_task_changes_only_the_replay_mix`.
3. **Kill at model_2900** (300 of 800 iterations), with the parent read on the same seeds:
   - drill v2 or court main more than 5 points below the parent;
   - arrival below 90 %;
   - court falls above 7.4 % per episode;
   - **progress:** own-ball legal on the R2 protocol (512 envs) not above 10.4 %, the upper bound of run 1's R2. Point estimate: 3 of 5 (coach, motion, architecture); RL and experiment design wanted its Wilson lower bound.
4. **Credibility** (5 of 5): 4 runs are not credible on the trend. 10 % -> 56 % needs about 15 points per run; Stage 5 has given about 2.
   - **Stop rule** (4 of 5): if R2 at run 2's endpoint is below 20 %, Stage 5H ends, and the user gets the interim video with the gap stated plainly. Experiment design proposed 16.4 %, and 20 % is stricter.
   - Also stop if the stage ends with P(4+) under 1 %.

# Round 19: run 2 killed by court main while own-ball legal rose (2026-10-21)

**Correction check** (5 of 5):
- **The kill is sound and counts.** Court main fell -6.0 points against the 5-point line. Its interval is [71.0, 74.8] against the 73.9 line, so the kill is real but marginal (motion, RL, experiment design).
- **Round 18's mix rule was a design error** (5 of 5). The code was right; the arithmetic went unchecked: 0.6 x 0.4 = 24 % court. Run 2 therefore changed two things, adding replays and cutting court rehearsal from 40 % to 24 %, so the court kill is confounded.
- **From now on,** every plan lists the realised feed shares, and they are checked in a smoke test before launch (experiment design, architecture).
- **The D-130 stop rule does not fire:** a killed run has no endpoint. It carries over unchanged to run 3's endpoint, as does round 17's "doubled by run 2" rule. The 37 % read (16.6 %) is not taken as an endpoint.

**Decisions:**
1. **Run 3 = (a)** (5 of 5). Run 2's task with `court_feed_prob` 2/3 of the non-replay feeds: **40 % replay / 40 % court / 20 % drill v2.**
   - Task `...-KeepAlive-Own-Court40-G1`: config only; the run 2 task is kept unchanged.
   - Parent: run 1's endpoint (model_2599); a killed run is never a parent. Same replay set (seed 4217040).
   - **Smoke check:** `test_d131_realised_shares_are_40_40_20` passes (within 2 points).
   - **The cost, pre-registered:** the drill v2 share falls from 60 % to 20 %, so drill v2 is the line most at risk.
2. **Kill at model_2900** (parent read on the same new seeds 4217200-4217204), every line reported with its interval:
   - drill v2 or court main more than 5 points below the parent;
   - arrival below 90 %;
   - court falls above 7.4 % per episode;
   - own-ball legal not above 10.4 %.

   Run 2's 16.6 % is a reference only.
3. **At the endpoint** (iteration 3399; run 3 of 4):
   - R2 below 20 % ends Stage 5H, and the user gets the interim video with the gap stated;
   - P(4+) under 1 % at the stage's end also ends it.
   - Experiment design's extra rule, "a second court-main kill ends Stage 5H", got 1 of 5 and is recorded.

# Round 20: run 3 at its endpoint; the last Stage 5H run (2026-10-21)

**Brief:** run 3 tripled R2 to 29.8 %, cut falls on own balls to 0.8 % per shot, and raised R4 P(4+) to 0.33 %. Court main is 75.1 %, under the 76.8 % stage line. Own-ball legal in pairs is only about 12 %.

## Correction check

- **The stage-rule kill is applied correctly and counts** (5 of 5). It is Stage 5H's second kill in a row. Run 3 is never a parent, and court main's interval belongs in the report (coach, RL, experiment design).
- **The brief was wrong in one place** (experiment design, motion, RL). `_refeed` never moves the robot back to the start spot: replays fire 0.5 s after the robot's own ball lands, from wherever it has recovered to.
- **The pairs-vs-replay gap (12 % vs 30 %) is partly a protocol artifact** (RL, motion, architecture). `pairs.py` hands the ball over at the **net crossing**. The receiver first sees it mid-flight, about 0.55-0.9 s before contact against about 1.1-1.4 s on replays, and the ball history jumps at that moment. A real opponent's ball is visible from the paddle.
- **Diagnostic** (motion's, no new code; seed 4217305): R2 on run 3's endpoint with **no refeed delay** is **29.9 % [29.3, 30.6]**, the same as 29.8 % with 0.5 s. So recovery time is not the cause; the late, jumping sight of the ball in pairs is the likely one.
  - This is recorded, not changed. Moving the hand-off to the partner's contact would change the frozen R4 protocol, so it needs a D-entry; it goes to the user (motion) or a later round (architecture's 2-line fix, RL's check).

## Decisions

1. **Run 4 = (a), pair-mode training** (4 of 5; coach preferred a hit-and-recover feeder).
   - **The task:** run 1's task with `pair_mode` and no replay file (3 of 5). It is the loop's self-play setup: one shared policy on both envs of a pair, and a feeder ball starts each rally.
   - **The court share is kept at about 40 % of all feeds** (motion, architecture, experiment design: the round-19 lesson). Hand-offs were 41 % of feeds in run 1's pair read, so the feeder's court_feed_prob is 0.678.
   - **Parent:** s5h-01-keepalive/model_2599.
   - **Smoke:** 3 PPO iterations in pair mode run cleanly; `test_d132_pairs_task_changes_only_pair_mode_and_the_court_share` passes.
2. **Kill at model_2900,** with the parent read on the same seeds (4217300-4217303):
   - drill v2 or court main more than 5 points below the parent;
   - arrival below 90 %;
   - falls above 7.4 % per episode;
   - **progress:** own-ball legal per shot in pairs (R4 protocol, 1,024 envs) not above 6.5 %, run 1's (RL, motion, architecture). Experiment design proposed run 3's 11.8 %.
3. **After run 4, back to the user whatever the result** (5 of 5). Stage 5H's 4 runs are used, and D-129 (P(4+) under 1 %) almost certainly fires; even 30 % per shot gives only about 0.8 %.
   - **Interim video,** labelled interim, from the best policy that passes the stage rules:
     - random pair rallies on a fixed development seed;
     - the longest rally, labelled as hand-picked;
     - the failure mode;
     - on screen: legal per shot against the 56 % bar, and P(4+).
   - **Questions for the user:**
     - a pair-mode stage with runs over 2 h;
     - the hand-off fix (a change to the R4 protocol);
     - R3 falls.
