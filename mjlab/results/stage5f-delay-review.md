# Stage 5F delay review (reviewer round 6, 2026-10-19)

**Trigger.** After step 0 and C1's early check, the user said: "i dont have any close objectives in getting this simulated in the physical world tho. is the delay still going to be important?" They asked for a group view before any frozen decision changes. Brief: the step-0 results, Option A (keep delay as planned), Option B (drop delay), Option C (park delay as a tracked, non-gating line), or a variant.

Five reviewers read the brief independently:
1. RL and sim-to-real;
2. motion prior;
3. pickleball coach;
4. experiment design;
5. architecture and compute.

## Verdicts

| Reviewer | Verdict |
|---|---|
| 1. RL and sim-to-real | C-lite: delay out of the gate and the training; a few fixed delay cells reported as diagnostics |
| 2. Motion prior | B plus an information-only delay line on candidate runs; C2 only if C1 earns it on clean numbers |
| 3. Pickleball coach | B with tracking: two descriptive delay cells (command 10 ms, 40 / 20) on every run |
| 4. Experiment design | B plus C's reporting; a strict decision entry that calls the drill v2 change a loosening of that item |
| 5. Architecture and compute | B+: a tracking line only on the candidate and the final (command 10 ms) |

**Consensus (5 of 5):**
- Take delay out of the Stage 5F gate and out of training.
- Keep ball-state noise.
- Keep every bar unchanged: p >= 0.80; group floors 0.92 / 0.80 / 0.55 on Wilson lower bounds; court >= 76.8 %; falls <= 1 %; arrival >= 90 %; style <= 3.86.
- Spend the budget on the shot work.

No reviewer voted for A.

## Shared findings

| # | Finding | Raised by |
|---|---|---|
| 1 | Round 4's premise (eventual real-robot deployment) is gone. Two of its reasons now point the other way: delay is now the condition that is never deployed, and rebuilding the controller during shot work is now the confound. Its third reason (an instrument change) is answered by a decision entry and dual reporting. | all |
| 2 | Every remaining gap is a clean-simulation gap: p 0.741 vs 0.80, the neutral floor (0.806 vs a 0.92 Wilson lower bound; the hardest item), falls 6.2 % vs 1 %, style 4.26 vs 3.86. | all |
| 3 | Moving drill v2 from the D-101 mixed-latency condition (0.306) to cell 0/0 (0.741) loosens that item's instrument. It is legitimate only because the premise changed outside the results. The decision entry must say so, and say step 0 had been seen. | 4 (1, 3, 5 agree) |
| 4 | Stage 5E's verdict (0/8, not met) stands and is never re-judged. Every run also reports the frozen D-101 figure, so it stays comparable. | 4, 1, 3, 5 |
| 5 | A new run 0 on the new instrument (seeds 4210300-499) before any training run, re-basing the kill rules (for example, p kill = run-0 value minus 3 points). | 4, 1, 5 |
| 6 | The budget, kill and plateau counters carry over; C1 + C1b count as run 1 of 15. | 4, 5 |
| 7 | Keep the delay tooling (delay-grid battery, compensator, history inputs, C2 script) with its tests running, dormant. The with-delay bars are suspended, not deleted; they become the entry gate of any later sim-to-real stage. | all |
| 8 | No light 0-10 ms latency as regularisation by default (a second variable). At most a single pre-registered run later, if falls plateau. | 1, 3, 5 |
| 9 | The pre-registered exit (goal-conditioned controller) still makes sense. Re-cut its triggers: shot plateau, budget out below 0.80, or 2 kills in a row; drop the controller-gate and compatibility triggers. | 5, 3 |
| 10 | One obvious step is untried: PPO of Stage 5D run 1 on drill v2 in clean conditions. Under latency the same step took p from 0.31 to 0.59, falls from 6.2 % to 3.9 % and style to 3.862. | 1 |
| 11 | Falls and style come from how the executor uses the latent space (residual latents off the prior in extreme reaches). They are executor-side, not a controller fault. Probe the latents before falls; check that the motion set covers split step and drop step before the shot runs. | 2 |

## Disagreements (for the user)

- **How much delay reporting:**
  - every run: command 10 ms and 40 / 20 cells, plus the D-101 figure (reviewers 1, 3, 4);
  - the candidate and the final only, command 10 ms (reviewers 2, 5).
- **C1:**
  - finish, gate, archive as a sim-to-real asset; not in the stack (reviewers 1, 3, 4, 5);
  - adopt C1 as H0 if it is clean non-inferior with a real gain somewhere, then one conditional decoder-only C2 (reviewer 2).
- **First executor run:**
  - clean drill v2 PPO from Stage 5D run 1 first (reviewer 1);
  - the coach's order from ready position and split step (reviewer 3);
  - turn-and-go footwork early for falls (reviewer 5).
