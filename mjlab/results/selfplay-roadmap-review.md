# Review round 8: the road to self-play (2026-10-20)

**Trigger.** The user handed decisions to a standing panel (D-115, `docs/PANEL.md`) and set the goal: a robot that can improve by self-play. Five members answered independently. The brief included the agent's draft readiness target.

## Consensus

1. **Readiness target**, frozen in `selfplay-readiness.md`:
   - **R1 skill without forgetting:** 5 of 5 keep "every kill rule passes"; 4 of 5 keep drill v2 p >= 0.80.
   - **R2 own-ball returns, by replay of recorded mirrored returns** (5 of 5). All five rejected the draft's fitted feed family: over-built (4), and wrong (1), because a feed family cannot hold correlated position, velocity and spin. Record on one seed block and score on another (3). Bar >= 70 % (5 of 5), with a Wilson lower bound >= 0.65 (experiment design). Spin must be recorded (architecture).
   - **R3 falls,** with units fixed (motion: "court falls" are per robot episode, about 2.8 feeds; the start point is 1.6 % per feed). The per-episode proposals were 3 / 4 / 5 %. The bar is 4.0 % per episode (experiment design's number, the median).
   - **R4 two-robot smoke test:** kept by 4 of 5 as the acceptance test of the self-play environment, not a training target. The bar is 25 % of rallies with 4 or more consecutive legal shots (4 of 5), plus side symmetry within 3 points. Built cheaply as mirrored environment pairs (architecture).
2. **Exit trigger: continue Stage 5F** (5 of 5).
   - Run 2 was a tooling bug. Run 3 was forgetting with a standard fix, not a plateau of shot learning.
   - Recorded in D-116. No counter is reset.
   - **A third kill in a row takes the exit with no new vote.** Readiness must be met by run 9.
3. **Sequence:**
   - Run 4: court-feed rehearsal at 40 % from the start point, 800 iterations, plus a court-main item in the early check (more than 5 points below the parent kills; 3 of 4 who gave a number).
   - Then the own-ball test as evaluation only, on the start point, run 3 and run 4 (4 of 5).
   - Then branches:
     - court fails -> KL pull-back toward the parent (5 of 5);
     - court holds but p < 0.80 -> a smaller court share;
     - both pass but own-ball < 0.70 -> replayed own-ball feeds in training (3 of 5);
     - falls above the bar -> one falls run.
   - **The ready-position reward is off the path to readiness** (3 of 5).
4. **Minimum self-play, after readiness:**
   - one shared learning policy on both sides (5 of 5), on mirrored environment pairs, each robot seeing itself on the near side, so the observations, actions and runner are unchanged;
   - a feeder ball starts each rally;
   - 30-50 % of episodes stay feeder rehearsal;
   - the legal-return reward is unchanged (a cooperative "keep it alive" rally);
   - a fall ends the rally for both.

   **Evaluation anchors** (experiment design):
   - the scripted batteries, whose kill rules still apply;
   - the frozen readiness policy as an opponent;
   - a collusion check (outgoing ball speed, depth and margin; softer balls are not progress);
   - a small cross-play table of about 4 checkpoints, with no Elo.

   **Not yet:** an opponent pool or league (PFSP), Elo, competitive or scoring rewards, serve rules, doubles, a second robot entity or multi-agent wrapper, opponent pose in the observations, a strategy layer, unfreezing the motion prior.
5. **Corrections:**
   - (a) Fix the falls units everywhere.
   - (b) The volley families score 0.0 legal in every court battery, start point included: check whether that is a rules artifact.
   - (c) "P(rally >= 10) vs feeder" is not a rally; relabel it.
   - (d) The robot's returns have never been tested for being returnable. `return_quality` rewards pace (6 m/s reference), which may make low, fast "winner-only" balls.
   - (e) The replay override goes after `_refeed`'s mask restore. Replayed feeds get their own family index.
   - (f) Run 3 must never enter a snapshot pool or serve as a KL target.

## Disagreements, settled by majority or the tie rule

- Drill v2 p >= 0.80 in readiness: kept (4 to 1; the coach would drop it).
- Two-robot test: kept as environment acceptance (4 to 1; RL would replace it with a one-robot closed loop).
- Falls number: 4.0 % per episode, by the median and the tie rule. Proposals: 3 / 4 / 5 % per episode, 1 % or 2 % per shot.
- Budget: readiness by run 9. Proposals: run 7, 8, 9, 9 and a cap of 6 runs.
- Self-play opponent: the shared learner on both sides (3 of 5). RL proposed a ball-space snapshot pool first; motion proposed a frozen snapshot opponent.
