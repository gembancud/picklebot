# Review round 9: planning the exit stage, the timed goal-conditioned controller (2026-10-20)

**Trigger.**
- Run 4 was killed (court main 75.9 %), the third kill in a row. The pre-registered exit was taken (D-117).
- Readiness was measured:
  - **R2 (own-ball):** 6-8 % legal; the robot touches only 17-22 % of its own shots.
  - **R4 (two robots):** P(4+ shots) 0.000 / 0.0002 over about 41,000 rallies.

Five members answered independently.

## Consensus

1. **Correction check:**
   - **The exit is legitimate, but under D-116's three-kill rule, not under D-108's "plateau below p 0.80"** (run 4 reached 0.843). The binding failures are R2 (returnability) and court retention, so the exit stage is designed against R2 (5 of 5).
   - Round 8's correction (d), that the pace reward makes "winner-only" balls, was known and not acted on. That was the real error (RL).
   - The readiness budget ("by run 9") is void now that the exit is taken. **R1-R4 are re-registered with a new budget; the bars are unchanged** (experiment design, RL).
   - **The readiness recordings (seeds 4215000+) must never shape training goals or targets.** The goal bank is re-recorded on a fresh development block. The smoke recordings (4213001-003) are cited for design (motion, experiment design; the charter's readiness-seed rule settles it against the two members who proposed using them).
   - **R4's symmetry measure is defined before the next read:** each side's legal rate on own-ball shots only, the feeder ball excluded. R2 also reports an env-clustered bootstrap lower bound, and both lower bounds must clear 0.65. This tightens only (experiment design).
   - **The readiness scripts hard-code the court task and `--no-hint`.** New versions take the task as an argument; the scoring is unchanged and the hashes are recorded before use.
   - **Every R1-R4 measurement of the new system runs the noisy spin-blind planner.** The planner must fire on replayed and paired balls; this needs a test (architecture).
2. **Controller (5 of 5):** extend the Stage 5B H3 latent-reach controller (`latent_reach.py`, `ReachCommand`, frozen latent-07 prior and decoder). Make it timed: paddle position p*, paddle velocity v* and face normal n* at a contact time t*, plus the root target.
   - PPO, ball-free, on a goal bank.
   - Warm start from reach-06/model_34700 (2 members; architecture proposed agility-L3), widened with zero-initialised inputs.
   - One-shot reward at t*: exp(-(dp/0.10)²) · exp(-(dv/1.0)²) · (0.5 + 0.5 n·n*). Root progress, the prior penalty and the falls term are kept.
   - **Not built** (5 of 5): MaskedMimic or new teachers, re-distilling H0 or H1, more residual layers, a learned planner, a spin estimator, spin commands, volley or dink modes, a strategy layer, a multi-agent wrapper, opponent pools.
3. **Planner (5 of 5):** extend `planner.py`.
   - `predict_top` returns the contact point, t* and the ball's velocity there.
   - Choose the outgoing ball with a short search over the spin-blind rollout, landing in a target box.
   - Get the paddle state in closed form from the impact model: n ∥ (v_out − v_in), u = (v_out·n + e·v_in·n)/(1 + e).
   - Batched and compiled in `_plan_step`, within 5 % of an environment step.
4. **The binding gap (5 of 5):** the planner owns the outgoing ball. Its **keep-it-alive target is the feeder's own ball** (coach's numbers):
   - landing x +4.7 to +5.7 m;
   - |y| <= 1 m;
   - flight time 1.3-1.5 s;
   - spin not commanded.

   A robot that hits feeder-like balls meets its strongest skill (0.84 on feeder balls) when it receives them. **Own-ball replay as a training family is a later, single, fallback change** (5 of 5).

   **New reported metric** (coach): the *partner window*, the share of legal returns whose mirrored flight arrives at <= 4.5 m/s with a bounce apex of 0.6-1.1 m. Outgoing pace, depth and margin are reported (the collusion check).
5. **Plan:**
   - **Step 0, no training:**
     - tests: planner contact against the simulator, impulse inversion, outgoing landing, a one-shot reward, planner firing in replay and pair mode, observation widening;
     - a goal bank on a fresh block;
     - reach-06 zero-shot on the new command (the baseline);
     - a spin-error diagnostic;
     - versioned readiness scripts;
     - the evaluation adapter reproducing Stage 5D run 1's run 0 within its intervals.
   - **E1:** timed reach, ball-free (4 of 5).
   - **E2:** E1 plus the planner, zero-shot in the ball environment (4 of 5): the clean battery, R2 and R4.
   - **E3 onward, one change each:** PPO fine-tune with the ball (the goal reward plus legal return replaces return_quality's pace term), with 40 % court rehearsal; then own-ball replay if needed.
   - **Budget: 6 runs** (median of the proposals 3, 6, 6, 8, 8).
6. **Back to the user when any of these happens:**
   - readiness is met;
   - E1 misses its gate after one extension (a MaskedMimic-class controller would need the user's compute decision);
   - R2 does not improve after the zero-shot run plus one fine-tune (thresholds in D-118);
   - 2 kills in a row;
   - 6 runs are used.

## Settled by majority or the tie rule

- **E1 gate:** experiment design's numbers (tie rule):
  - median paddle error at t* <= 0.08 m, p90 <= 0.20 m;
  - timing within 50 ms on >= 80 % of goals;
  - paddle speed error <= 20 %;
  - falls <= 2 % per episode;
  - arrival >= 90 %.
- **E1 early kill:** falls > 5 % (3 of 5), or a median paddle error at t* > 0.25 m (experiment design).
- **Kill rules for the new controller** (experiment design, with a named premise): D-113's rules assumed fine-tuning the start point, where a drop means forgetting; a fresh controller has nothing to forget.
  - Per-run kills are measured against the stage's own parent.
  - A fixed check by E4: some endpoint has drill v2 >= 0.723 and court main >= 76.8 %.
  - R1 keeps every absolute number.
- **Stop on 2 kills in a row** (3 of 5).
