# Strategy and execution

Work branch: `feat/hierarchical-control`. Baseline: `f17dca1`.

The intended system has two shared actor policies. Each player independently uses a strategy actor to choose goals and an execution actor to control its body. Training critics do not add deployed actors.

## First implemented stage

The existing drill runner can now accept `PlayerExecutionDrillsV1`, an opt-in companion component. It changes the learner's behavior to `PicklebotExecutionV1` and appends 12 goal features to the existing 124 observations. The 16 continuous motor controls and masked binary release branch are unchanged. Fixed-ball serving remains the training convention.

| Goal features | Meaning |
|---|---|
| Four intention bits | Play ball, recover, cover, yield |
| Movement enabled, relative X/Z, radius | Desired body destination and tolerance |
| Shot enabled, absolute X/Z, radius | Desired landing area |

Targets use canonical court meters: both teams attack toward positive Z. Movement offsets use the current player's position and the existing 8.4/16.2 meter scales; shot coordinates use court half-width/half-length. Radii are scaled by 3 meters. Disabled target fields are zero. Goal ownership and issue tick are checked against each private observation. Each arena regenerates its goal set on reset.

Goals do not move the body, assign a stroke, predict a contact point or choose a swing time. Movement and swinging can overlap. The movement destination and recover/cover/yield intentions are exposed in the contract but **are not yet trained** by the first shot-placement experiment.

## Goal practice

Current practice assigns `PlayBall` plus a seeded shot target. The goal sampler has its own RNG and does not change ball-feed randomness. Serve targets lie within the receiving service box. Existing solo serve/return/volley/movement mixtures remain available.

A target bonus is paid once, after the existing drill reports a legal outcome and an accepted post-contact opponent-court bounce exists. Maximum bonus is 0.25; it decreases linearly to zero at the target radius. Existing legal-hit rewards remain. Misses, illegal hits and illegal serves receive no placement bonus. Target circles near boundaries are effectively clipped by court legality.

Metrics: `PicklebotExecution/LegalLanding`, `TargetHitPerAttempt`, `TargetHitGivenLegal`, and `LandingDistanceGivenLegal`. Read both success-per-attempt and conditional accuracy: better conditional aim alone can conceal more misses. Exact targets and outcomes are recorded in `execution-goals.jsonl`.

Worker manifests explicitly opt into `execution-v1-136obs-16continuous-release`. Legacy workers remain on the old contract. This first execution stage rejects paired workers, background models and legacy optimizer diagnostics rather than silently mixing incompatible contracts.

## Preserving learned control

`tools/mlagents-training/initialize_execution_v1.py` expands the saved actor and critic input layers. Old weights and normalization statistics are copied exactly; new goal weights start at zero. Goal normalization starts with a zero-mean, unit-variance prior at the inherited count. A fresh optimizer and zero experience counter make this a weight initialization, **not a resumed run**.

The initializer checks installed-framework actor/critic outputs, deterministic actions and a nonzero gradient path into the new goal columns, then exports a new ONNX model. The previous checkpoints and ONNX files are retained. The ordinary pinned ML-Agents trainer is unchanged; the earlier isolated critic-key correction is not part of this migration.

From the repository root, using the training Pixi environment:

```powershell
pixi run --manifest-path tools/mlagents-training/pixi.toml python tools/mlagents-training/initialize_execution_v1.py --parent training/snapshots/swing-recovery-parent-01.pt --output artifacts/hierarchy-v1/execution-init-01
```

Use a fresh output directory when repeating initialization. `config/mlagents/execution-v1-smoke.yaml` defines a 32,768-experience integration run, not a competency benchmark. It requires a newly built worker with the execution contract; old headless builds cannot consume it.

## Sequence and acceptance

1. Verify observation/action contracts, reset isolation and exported-policy parity in Unity.
2. Verify actual PPO training consumes the new contract and changes goal weights. Keep the familiar skills in the mixture.
3. Evaluate placement on held-out targets while checking serves, bounced returns, volleys and movement returns separately. No promotion based only on training reward.
4. Train movement destinations and continuous contact/recovery transitions. Distinguish positioning from shot accuracy; test both.
5. Add paired take/yield/cover practice with private observations and team outcomes.
6. Train a slower strategy actor against a stable executor, then evaluate full 2v2. Its cadence and reward design remain to be measured.

An initialized goal-conditioned executor is not a trained strategy system, and a short integration run does not establish goal-following competence. Jointly changing both policies is deferred until executor behavior is sufficiently reliable to evaluate tactical decisions.

[First integration results](research/execution-v1-integration.md): contract, warm-start parity, actual PPO learning and a small exported-model screen.
