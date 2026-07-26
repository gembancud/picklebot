# Picklebot architecture

Status: **Accepted overview**

This document is the short architectural map. The normative detail lives in:

- [ROADMAP.md](ROADMAP.md) for capability order and phase gates;
- [ENVIRONMENT_SPEC.md](ENVIRONMENT_SPEC.md) for the versioned simulation
  contract;
- [PHASE1A_SPEC.md](PHASE1A_SPEC.md) for the first training and evaluation
  protocol;
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
      +------ future trainer adapter
```

`Picklebot.Evaluation` owns protocol data, observation encoding, reward mapping,
baselines, and reports while referencing only `Picklebot.Core`. The future
trainer adapter may depend on the evaluation and simulation seams plus its SDK;
none of those assemblies may depend back on the adapter.

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
