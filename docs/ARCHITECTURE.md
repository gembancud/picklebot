# Picklebot architecture

## Full-body doubles prototype

D-029 adds `Picklebot.Doubles`, with dependencies on Core and Simulation.
It does not change the earlier rally, inspection or singles assemblies.

- `DoublesWorld` owns one local 240 Hz physics scene, a dynamic ball, four
  kinematic paddles, body colliders, a level apron and net contact checks.
- `DoublesRules` owns service order, side-out scoring and rally faults. It
  retains volley momentum obligations until the player regains control.
- `PlayerBody` constrains the paddle grip to arm reach. Analytic two-bone IK
  places the arms and legs. A procedural step controller supplies foot state.
- `StrokeController` supplies scripted interception and inverse flight planning.
  It moves the paddle. It does not assign ball velocity or spin.
- `ContactModel` supplies fitted pitch, timing, speed and brush corrections
  for three shot styles. These are learned parameters, not a joint-torque network.
- Two `TeamPolicy` objects select targets and contact styles from ball state
  and teammate/opponent positions. Terminal rewards are opposing win/loss values.
- `DoublesTraining` runs bounded Editor jobs. Reports preserve source, model,
  configuration and seed evidence. Test samples and interactive play use
  separate seed ranges.

The ball uses the existing provisional V1 contact and aerodynamic models.
The four-body environment has its own versioned source evidence. It does not
close measured physics calibration. See [PICKLEBALL_DOUBLES.md](PICKLEBALL_DOUBLES.md).

## Full-size inspection environment

D-027 adds `Picklebot.Inspection`. It depends on Core and Simulation, but not
on a trainer. It reuses the existing V1 geometry factory, configuration,
aerodynamic model, and provisional paddle spin-transfer model. It replaces
the training episode lifecycle with a local physics scene at 240 Hz.
Collisions and rule faults do not stop that scene. A 20-second inspection
limit bounds each run.

Two bounded kinematic paddle motors accept independent XYZ translation and
three-axis rotation. Player ground markers supply a limited kitchen-rule
proxy. The ball remains a dynamic rigid body. The contact model does not
select a landing target. Optional fixed strokes demonstrate contact without
an AI model. Recorded trajectories and contacts support later measurements.
See [PICKLEBALL_INSPECTION.md](PICKLEBALL_INSPECTION.md) for the provisional
contract and its limits. This addition does not replace the frozen Phase 0
contract or close Phase 1B.

## Separate AI rally prototype

D-028 adds `Picklebot.Match` above Inspection. It reuses the same local physics
world and bounded motors. `ScriptedStrokeMotor` provides explicit contact
assistance. Two independent `ShotPolicy` objects learn shot choice from
terminal zero-sum rewards. The editor runs bounded training and validation
jobs, while `MatchDemo` displays independent points. The model asset records
source and configuration hashes. There is no dependency from Inspection back
to Match. See [PICKLEBALL_MATCH.md](PICKLEBALL_MATCH.md).

D-025 introduces `Picklebot.Rally` as an independent prototype assembly. It
contains its own local Unity physics scene, bounce/point state, trained dense
neural policy, and demo controls. It has no dependency on the existing Core,
Simulation, Evaluation, or Training assemblies. An Editor-only assembly creates
the scene and records validation results. `scripts/rally-train.py` generates
offline imitation examples and exports model weights; no teacher code runs in
the game. See [AI_RALLY.md](AI_RALLY.md) for the provisional physics contract.

D-026 adds `Picklebot.Competition`. It reuses the rally rule state and model
serialization types. It has its own physics scene, smaller paddle geometry,
materials, bounded motor, and demo. A frozen goal-conditioned neural stroke
model controls contact. A second neural policy chooses one of five landing
targets from ball state and both paddle positions. Python trains that policy
with PPO and actual Unity point results. Each side acts in its own coordinate
frame. The two sides share weights, but receive opposite point rewards.
The old cooperative scene and evidence remain separate. See
[COMPETITIVE_MATCH.md](COMPETITIVE_MATCH.md) for the current contract.

Status: **Accepted overview**

This document is the short architectural map. The normative detail lives in:

- [ROADMAP.md](ROADMAP.md) for capability order and phase gates;
- [ENVIRONMENT_SPEC.md](ENVIRONMENT_SPEC.md) for the versioned simulation
  contract;
- [PHASE1A_SPEC.md](PHASE1A_SPEC.md) for the first training and evaluation
  protocol;
- [PHASE1B_PHYSICS_CALIBRATION_SPEC.md](PHASE1B_PHYSICS_CALIBRATION_SPEC.md)
  for the measured physics fixtures, thresholds, and `env-v1` close gate;
- [PHASE1C0_LEARNING_PROBE_SPEC.md](PHASE1C0_LEARNING_PROBE_SPEC.md) for the
  provisional trainer, artifact, seed-hygiene, and visible-replay contract;
- [DECISIONS.md](DECISIONS.md) for accepted direction and change history.

When documents appear to conflict, the newest accepted decision explains the
intended change. Update every affected document in the same change rather than
allowing the conflict to persist.

## Locked decisions

- Unity supplies 3D physics, collision handling, scenes, and visualization.
- Phase 0 contains no policy or trainer dependency.
- Numeric state observations come before camera observations.
- Paddle and ball control are learned before custom humanoid locomotion.
- A pretrained locomotion controller is integrated before whole-body fine-tuning.
- IK or reference strokes are scaffolding, not the final controller.
- Residual reinforcement learning progressively unlocks whole-body corrections.
- Scripted opponents precede self-play.
- Core simulation emits named facts and reward features; trainer adapters own
  reward weights.
- Physics runs at 120 Hz and the initial control loop at 60 Hz.
- Phase progression requires recorded verification evidence.

## Simulator boundary

Game code depends on project-owned interfaces rather than a training SDK:

```text
Environment reset and seed
        |
        v
Simulation state -> observation snapshot
        ^                    |
        |                    v
Physics step <- action command
        |
        v
Reward terms and termination reason
```

A trainer adapter may translate this contract to Unity ML-Agents, a custom
Python process, or an offline evaluator. Trainer-specific types must remain
outside the core simulation assembly. Scripted controllers, replay, tests, and
trainers all use the same action/step boundary.

The dependency direction for Phase 1 is:

```text
Picklebot.Core
      ^
      |
Picklebot.Evaluation       Picklebot.Simulation
      ^                         ^
      |                         |
      +------ Phase 1C0 trainer adapter
```

`Picklebot.Evaluation` owns protocol data, observation encoding, reward mapping,
baselines, and reports while referencing only `Picklebot.Core`. The future
trainer adapter may depend on the evaluation and simulation seams plus its SDK;
none of those assemblies may depend back on the adapter.

## Physics calibration boundary

Phase 1B keeps calibration behavior explicit and testable:

- `Picklebot.Core` owns immutable aerodynamic inputs, coefficient/configuration
  records, and pure force calculations that do not depend on Unity scene
  objects;
- `Picklebot.Simulation` converts those calculations to Unity forces and owns
  collision fixtures, while the fitted constants remain project configuration
  rather than hidden material or prefab values;
- calibration datasets, fitting provenance, reports, and closing artifacts live
  outside the runtime assemblies under the documented evidence paths;
- EditMode tests prove the pure model and serialized identity; PlayMode tests
  prove the integrated trajectory and contact behavior.

The calibration assemblies do not introduce a trainer SDK. D-023 permits the
separate Phase 1C0 adapter to consume the provisional `env-v1` contract while
Phase 1B remains open; no dependency points back from Core, Simulation, or
Evaluation to that adapter.

## Verification layers

Phase 0 tests establish:

1. identical seeds generate identical launcher sequences;
2. ball-floor and ball-paddle contacts remain numerically stable;
3. net, in-bounds, and out-of-bounds events are classified correctly;
4. resets restore all relevant state without leaking velocity or score;
5. repeated headless runs complete without invalid physics state.

The full completion gate, including the 10,000-episode soak requirement, is
defined in the roadmap and environment specification.

Phase 1A adds contract tests for the seed, observation, curriculum, reward, and
assembly boundaries; PlayMode checks against the real scene; two held-out
baselines; and a throughput/allocation readiness probe. Its normative gates are
defined in the Phase 1A specification.

Phase 1B adds source-backed geometry, ball-drop, trajectory, court, paddle, and
net calibration fixtures plus a calibrated 10,000-episode stability run. Its
normative thresholds and evidence requirements are defined in the Phase 1B
physics calibration specification.
