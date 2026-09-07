# Picklebot Phase 1C0 provisional learning probe specification

Status: **Normative diagnostic contract**

Version: `phase1c0-learning-probe-v0`

Environment dependency: current `env-v1` implementation, explicitly
`provisional-unfitted`

Protocol dependency: `phase1c-protocol-v0`

Decision authority: D-023

## 1. Purpose and non-claims

Phase 1C0 proves that the complete learning path works: Unity environment,
numeric observation, continuous action, reward, Python trainer, checkpoint
export, native Unity inference, metrics, and visible replay.

It does not:

- close any Phase 1B empirical gate;
- freeze or tag the simulator as calibrated `env-v1`;
- complete Phase 1C's three-training-seed benchmark;
- establish final pickleball realism;
- authorize humanoid control, rallies, scoring, opponents, or self-play.

Every run, checkpoint, model, trajectory, and metric must be labelled
`provisional` and is invalidated by a configuration-hash change.

## 2. Fixed integration contract

The adapter consumes the project-owned environment boundary and may depend on
`Picklebot.Core`, `Picklebot.Simulation`, `Picklebot.Evaluation`, and Unity
ML-Agents. Those three project assemblies may not reference the adapter or any
trainer SDK.

The first adapter uses:

- Unity Editor `6000.5.5f1`;
- Unity package `com.unity.ml-agents@4.0.3`, communicator `1.5.0`;
- Python `3.10.12`;
- PyPI Python package `mlagents==1.1.0`;
- PyTorch `2.1.2`;
- ONNX `1.15.0` and protobuf `3.20.3`;
- native Conda `grpcio==1.48.2` on Apple Silicon;
- observation `phase1c-observation-v0`, exactly 37 floats;
- action `paddle-action-v0`, six continuous values in `[-1, 1]`;
- control frequency `60 Hz`, with two `120 Hz` physics ticks per action;
- reward `phase1c-reward-v0`;
- curriculum stages from `Phase1CProtocolV0`.

The six action values map in order to local paddle linear velocity `x/y/z` and
local angular velocity `x/y/z`. `ActionProcessorV0` remains the authoritative
clamp and physical scaling path.

## 3. Seed hygiene

Only these request builders are legal:

- training: `Phase1CProtocolV0.TrainingRequest`;
- model selection and demonstration: `Phase1CProtocolV0.ValidationRequest`.

`Phase1CProtocolV0.FinalEvaluationSeeds` is metadata only. Phase 1C0 code must
not add a builder, enumerate that range, reset an environment with a seed from
it, or include it in a trainer configuration. Automated tests must fail if a
training or validation request overlaps it.

An unseen validation launch means its seed was not used for gradient updates,
curriculum promotion, trainer-side normalization fitting, or replay-buffer
sampling. It may be used for checkpoint comparison and the final visible
Phase 1C0 demonstration.

## 4. Curriculum and reward

Training advances through the committed stages in order:

1. `p1c/contact-easy`;
2. `p1c/return-easy`;
3. `p1c/place-default`;
4. `p1c/robust-hard`.

The first bounded run may stop after it demonstrates legal returns on varied
validation launches; reaching that diagnostic milestone does not waive the
remaining stages for Phase 1C.

The adapter converts only named project reward inputs into scalar reward. The
versioned mapping includes:

- controlled-paddle contact;
- far-court legal landing;
- near-court and out landing;
- net contact;
- target distance at a legal landing;
- action clamping;
- invalid state;
- elapsed time;
- a bounded pre-contact interception-progress term;
- a bounded action-change term.

No reward may inspect a final-evaluation seed, hidden future trajectory, or
scripted solution. Any weight or term change requires a new accepted decision
or a new reward version; a completed run records the reward hash.

## 5. Generated artifacts and storage

Committed reproducibility inputs live under:

```text
config/phase1c0/environment.yml
config/phase1c0/picklebot_ppo.yaml
```

Generated, ignored artifacts live under:

```text
artifacts/phase1c0/<run-id>/
  trainer/<run-id>/
    configuration.yaml
    PicklebotReturn/
      checkpoint.pt
      PicklebotReturn.onnx
      PicklebotReturn-<step>.pt
      PicklebotReturn-<step>.onnx
  runtime/<policy-source>/<session-id>/<training-or-validation>/
    manifest.json
    summary.json
    episodes.jsonl
    trajectory-<seed>.json
```

The imported replay model lives under
`Assets/Picklebot/Models/Phase1C0/` and must have an adjacent manifest naming
its source checkpoint and SHA-256.

PyTorch must remain on an exporter-compatible line. ML-Agents `1.1.0` pins
ONNX `1.15.0` and protobuf below `3.21`; a PyTorch release whose default ONNX
path requires `onnxscript` and a newer ONNX/protobuf chain is incompatible.
`scripts/phase1c0-train.sh` must fail its exporter preflight before opening a
trainer socket if this invariant is broken.

Before training, record free disk space. Retained Phase 1C0 generated artifacts
must remain below `5 GiB`, and training must stop before free space falls below
`15 GiB`. Do not duplicate the upstream ML-Agents repository merely to install
the published trainer.

## 6. Required verification sequence

1. Unity package resolves and all existing project assemblies compile.
2. The isolated Conda environment reports the exact Python and ML-Agents
   versions.
3. EditMode tests prove observation order/size, action mapping, reward
   arithmetic/bounds, seed separation, and dependency direction.
4. PlayMode tests prove reset, decision, step, terminal, metric, and no-scripted-
   override paths against the real environment.
5. A Unity-Python handshake reports one behavior with a 37-float vector
   observation and six continuous actions.
6. A bounded training smoke produces a loadable checkpoint.
7. A retained learned checkpoint visibly runs in Unity using native inference.
8. Replay uses validation requests only and records contact, legal-return,
   target-hit, net, out, landing-error, smoothness, and peak-speed metrics plus
   seed-level trajectories.

After any C# edit or package change, wait for compilation and inspect the Unity
console before using new types. Final replay evidence requires a clean console.

## 7. Diagnostic acceptance

Phase 1C0 is achieved only when all of the following are directly evidenced:

- the active action source is a loaded neural model, not `Heuristic`, a
  scripted policy, or a hidden corrective controller;
- Unity visibly shows the paddle tracking and striking incoming balls;
- the replay set contains at least 20 unseen validation seeds spanning at
  least two placement buckets and two launch-speed or curriculum buckets;
- at least one replay episode is a legal far-court return after controlled
  paddle contact;
- the learned replay exceeds zero action on both contact rate and legal-return
  rate over the same validation requests;
- the checkpoint, imported model, manifests, exact configuration, metrics, and
  trajectories are retained and mutually hash-linked;
- all outputs state that the simulator and policy are provisional.

These criteria prove a learned-return demonstration. Phase 1C still requires
material improvement over the committed scripted baseline, three training
seeds, the approved randomization envelope, and the untouched final evaluation
after Phase 1B closes.
