# Stage 5F plan review (reviewer round 4, 2026-10-19)

Five reviewers each read the next-stage brief independently:
1. RL and sim-to-real;
2. motion prior;
3. pickleball;
4. experiment design;
5. architecture and compute.

The brief set out Option A (rebuild the controller with latency) and Option B (set latency aside), along with the Stage 5E record. The user's decisions are in D-108. This file summarises the reviews; the full texts are in the session transcript.

## Verdicts

All five voted for a **modified Option A**. None voted for Option B.

Reasons given against B:
- **It changes the measuring instrument:** turning sim-to-real off in the evaluation loosens the D-101 gate.
- **It tunes for a condition that will never be deployed.**
- **It confounds the shot work** with a controller that would be replaced later.

## Shared findings and amendments

| # | Finding or amendment | Raised by |
|---|---|---|
| 1 | Ball-observation delay is state estimation: roll the timestamped, delayed measurement forward with the planner's ball model. This is deployable and not a loosening. Command delay needs a controller fix. | RL, pickleball, motion, architecture |
| 2 | No policy has an observation history, so under per-episode latency none can tell which condition it is in. This explains the hedging and specialisation of 5E runs 2-4. Add action, proprioception and ball histories. | RL, architecture, motion |
| 3 | H1's last-action input is `self.dec` (the newest decoder output), not the command applied under delay. Fix it. | RL (from the code) |
| 4 | Localise the damage before rebuilding: measure H0, the latent-07 path and the flat walking teacher on a delay grid. Retrain only what degrades. The walking teacher used for kickstarting may itself be fragile under delay. | motion, RL |
| 5 | Keep latent compatibility: freeze H1's input normalisation, encoder and prior; re-distil the decoder only. Check by zero-shot transfer of existing executors. Use a fresh latent space only as the fallback. | motion, RL, experiment design, architecture |
| 6 | Split the H0 change: delay randomisation and 100STYLE in separate runs. Keep the held-out 100STYLE slice out of all training. | experiment design, motion |
| 7 | Evaluate on a fixed delay grid (ball 0/20/40 ms × command 0/10/20 ms). Every kill and retention check covers every condition the training covers. A test enforces this. | experiment design, RL, motion |
| 8 | Separate plateau strikes from kills; stop and diagnose after 2 kills in a row; early-kill check at about 30 % of a run; a second training seed for the candidate. | experiment design, architecture |
| 9 | New development seed block, opened by a decision before use, plus a seed ledger. | experiment design, architecture |
| 10 | Shot work in the coach's order: ready position and split step; turn-and-go footwork (drop step, turned shuffle); stance spot plus time-to-contact; margin-first shots; backspin reception. | pickleball |
| 11 | Pre-register an exit to a goal-conditioned controller with an interception planner, in case the shot work plateaus below 0.80. | architecture |
| 12 | Realistic cost on the latent-compatible path: about 25-40 GPU-hours, 3-4 days. A fresh latent space would take 60-80 h. | architecture |

## Disagreement

**Retention gate.**
- **Three reviewers:** keep the no-delay court line (76.8 %) and add with-delay lines.
- **Two reviewers:** gate only under the deployment condition (delays on), with a no-delay floor.

The user chose the first: no loosening, plus with-delay lines frozen from the new run 0.

## Concerns noted for later

From the pickleball reviewer:
- The drill v2 recovery depth (x -5.6 to -4.5, 1.1-2.2 m inside the baseline) is no-man's-land.
- The 100STYLE straight-backpedal clips (BW) may reinforce the backward-fall pattern.
- Drill v2 is a baseline drill, not full pickleball (no dinks or volleys).

## Round 5: check of D-108 (2026-10-19)

None of the five reviewers objected to the plan as a whole. Every item drew AGREE or AGREE WITH CAVEAT, with one objection: the pickleball reviewer objected to the straight-backpedal clips entering H0 training without a safeguard.

Main caveats, all adopted in D-109:
- numeric triggers and sub-step gates written before step 0;
- issued-command history for the actor and applied commands for the critic only (deployable);
- the prior also reads the last command, so the compatibility check runs under delay too;
- zero-initialised new inputs;
- a fallback PPO fine-tune of the decoder;
- exit triggers spelled out;
- a mandatory second seed for the candidate;
- comparators named;
- an extrapolation cell beyond the training range.

The user then decided four points:
1. absolute with-delay bars (arrival >= 90 % in every direction, falls <= 1 %);
2. no H0 100STYLE run, and a style reward from the forward and sidestep clips only (no backpedal);
3. 15 runs with the controller capped at 6;
4. the executor history after the controller fix.
