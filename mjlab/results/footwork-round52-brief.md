# Panel round 52 brief (footwork phase step 1), 2026-10-31

Read first: D-179 to D-181 in docs/DECISIONS.md, and mjlab/results/footwork-review.md (round 51).

## What ran since round 51

**fw1c** (scripts/diag/footwork_fw1c.sh):
- **B0:** fw1b-S model_16600 re-read on the fixed instrument. Picklebot-Footwork-Measure60-G1, 60-s episodes, learning rate 0, 300 iterations, stochastic actions, seed 170. Results in results/fw1c-summary.txt and results/fw1c-B0.jsonl.
  - Sustained speed 1.84-2.09 m/s in every sector; censored 0.084.
  - Untimed arrival 0.31-0.38; settled-in-time 0.15-0.22.
  - Settle time 2.2-2.6 s after first entry. Mean largest distance after entry was 0.25 m, the radius itself, so there is no run-through: the robot hovers.
  - Falls 3.49 per 1,000 env-s.
  - The pre-registered rule prints **MIXED**: only BODY-OK (d), untimed arrival >= 90 %, fails.
- **Arm A:** pay "settled", from model_16600, adaptive PPO.
  - Killed by the coded watcher on KILL-no-settle at iteration 320 (results/fw1c-A-kill.json): untimed arrival 0.437 over iterations 220-320, min(L, B, R) speed 1.53 m/s, falls 1.37.
  - Its training untimed arrival rose only from 0.33-0.44 to 0.33-0.46. Action std stayed at 0.51 throughout.
  - Last checkpoint 2026-10-31_02-38-52_fw1c-A/model_16900.
  - The scripted read of A was skipped by a naming bug in the driver: the measure tag "A" collided with the training counter file. A killed arm's read is diagnostic only.

## New diagnostic (after the kill, before this round)

**Deterministic (mean-action) reads** through scripts/stage2_eval.py (scripts/diag/footwork_eval.py, fw1c_det_reads.sh):
- same Measure60 task;
- 1,024 envs, 120 s;
- development seeds 4220210 (B0, model_16600) and 4220211 (A, model_16900);
- results in results/fw1c-det-{B0,A}.json.

| sector | B0 sustained | B0 untimed | B0 settled-in-time | A sustained | A untimed | A settled-in-time |
|---|---|---|---|---|---|---|
| forward | 1.94 | 0.997 | 0.546 | 1.95 | 1.000 | 0.489 |
| forward-left | 1.95 | 0.998 | 0.570 | 1.94 | 0.999 | 0.502 |
| left | 1.99 | 0.992 | 0.615 | 1.99 | 0.999 | 0.576 |
| back-left | 2.02 | 0.989 | 0.640 | 1.99 | 0.992 | 0.524 |
| back | 2.11 | 0.989 | 0.635 | 2.04 | 1.000 | 0.534 |
| back-right | 2.03 | 0.995 | 0.648 | 1.96 | 0.999 | 0.520 |
| right | 1.92 | 0.990 | 0.590 | 1.95 | 1.000 | 0.549 |
| forward-right | 1.88 | 0.994 | 0.519 | 1.93 | 0.999 | 0.505 |

- **B0:** censored 0.077; 36 falls over about 123,000 env-s, about 0.3 per 1,000 env-s; settle time 0.8-1.0 s after entry.
- **A:** censored 0.076; 55 falls (38 of them back-left).

With mean actions, both checkpoints meet every BODY-OK line of bodyspeed_rule:
- forward >= 1.8 m/s;
- left, back and right >= 1.8 m/s;
- untimed arrival >= 90 % in every sector;
- falls <= 4.157;
- censored <= 10 %.

The pre-registered reads (D-179 to D-181) are stochastic, as in training, so this has not been relabelled. Downstream, the specialist is used with mean actions:
- motion's step-2 clip recording ("record clips with mean actions only");
- kickstart / DAgger targets, which are action means;
- every rally and executor evaluation in this project (stage2_eval.py is deterministic).

## The question for round 52

1. **Correction check** on D-181 and its implementation.
2. **Is step 1 answered?** The body can sustain about 1.9-2.1 m/s in every direction and settle, under mean actions.
   - If so, how should it be confirmed honestly? For example, a confirmatory deterministic read on fresh development seeds under a rule frozen before the read: bodyspeed_rule unchanged, mean actions. A D-entry would name the premise that changed: the stochastic read was the wrong instrument for a teacher used with mean actions.
   - Or does that count as a post-hoc instrument change that must not be accepted?
3. **Which checkpoint becomes the step-1 teacher:** model_16600 (B0) or model_16900 (A)?
   - footwork_rule.select would compare min(L, B, R): B0 1.92, A 1.95, within 0.1, and there is no style arm.
   - B0 settles in time more often; A has more back-left falls.
4. **The next step.** Options:
   - (a) Go to step 2's premise checks (round 51, motion): a mean-action video of the four cardinal sectors; clips recorded with mean actions through amass_g1_import's frozen acceptance checks; back-sector heading at mid-move (turn-and-run vs backpedal).
   - (b) First lower the policy noise (RL's fallback, entropy_coef 0.01 -> 0.001), so the stochastic read also passes.
   - (c) Coach's heading limit (at most 90 degrees from the net), queued before step 2.
   - (d) Other.

Rules: never loosen a threshold; one change per run; dev seeds only (next free in block 3 after 4220211; training seeds from 171).
