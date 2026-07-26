# Picklebot Phase 1A specification

Status: **Frozen by D-019**

Version: `phase1a-protocol-v0`

Protocol hash: `4ae0928d344f1c3c`

Environment dependency: `env-v0`

Direction note (2026-07-26): D-020 inserted pickleball physics calibration as
Phase 1B. Historical references below to Phase 1B training record the plan at
the time of this freeze; D-020 supersedes their scheduling and future-use
requirements. Phase 1C must receive a new `env-v1`-dependent protocol. This
note does not change the frozen values, evidence, or protocol hash below.

Phase 1A freezes the measurement and training-readiness foundation for learned
paddle returns. It does not claim that a neural policy has been trained.
Phase 1B must use this protocol, or accept a new decision and protocol version,
so later results cannot be projected onto a different benchmark.

## 1. Scope and completion boundary

Phase 1A provides:

- disjoint training, validation, and held-out evaluation seeds;
- a four-stage launch curriculum;
- one frozen numeric observation encoding and the existing `PaddleActionV0`;
- one versioned scalar reward mapping over `env-v0` reward features;
- zero-action and intercept-heuristic baselines;
- required evaluation metrics and bucket breakdowns;
- a real-environment throughput and managed-allocation readiness gate;
- a trainer selection without adding a trainer dependency to the simulator.

Phase 1A excludes package installation, Python environment creation, PPO
configuration, substantive training, model checkpoints, and learned-policy
claims. Those begin in Phase 1B.

## 2. Assembly boundary

`Picklebot.Evaluation` references `Picklebot.Core` only. It must not reference
`Picklebot.Simulation`, ML-Agents, MCP for Unity, or another trainer SDK.

A future adapter assembly may reference `Picklebot.Core`,
`Picklebot.Evaluation`, and its trainer SDK. Dependencies may not point back
from the core, simulation, or evaluation assemblies to that adapter.

## 3. Seed partitions

All ranges are inclusive and are part of the protocol identity.

| Use | Range | Count |
|---|---:|---:|
| Training | `2000000`–`2049999` | 50,000 |
| Validation and curriculum promotion | `3000000`–`3000999` | 1,000 |
| Held-out final evaluation | `4000000`–`4000999` | 1,000 |

Training code must never request a held-out seed. Selection, tuning, early
stopping, and curriculum promotion use training and validation partitions only.
The held-out partition is for committed comparisons.

## 4. Curriculum

`TrainingRequest` and `ValidationRequest` construct the same stage manifest from
their assigned seed partition. The vertical launch override is explicit in the
episode manifest.

| Order | Stage | Scenario | Difficulty | Vertical velocity | Promotion metric |
|---:|---|---|---|---:|---:|
| 1 | `p1a/contact-easy` | `contact/front-on` | easy | `0.0 m/s` | contact rate >= `0.90` |
| 2 | `p1a/return-easy` | `launch/rally` | easy | `3.0 m/s` | legal-return rate >= `0.70` |
| 3 | `p1a/place-default` | `launch/rally` | default | `2.0 m/s` | target-hit rate among legal returns >= `0.55` |
| 4 | `p1a/robust-hard` | `launch/rally` | hard | `1.6 m/s` | legal-return rate >= `0.45` |

Promotion is evaluated on validation seeds. A trainer may mix earlier stages
after promotion, but may not skip recording the stage mixture.

The held-out suite cycles `easy`, `default`, and `hard` over all 1,000 seeds and
uses the corresponding `3.0`, `2.0`, and `1.6 m/s` vertical overrides. These
overrides create reachable inbound arcs while preserving every other
`env-v0`-generated launch parameter.

## 5. Observation contract

Encoding version: `phase1a-observation-v0`

Shape: 37 finite scalar values in `[-1, 1]`, written into a caller-owned buffer.

| Indices | Values | Scaling |
|---|---|---|
| 0–2 | ball world position XYZ | court half-width + 2 m, 8 m, court half-length + 2 m |
| 3–5 | ball world linear velocity XYZ | 25 m/s |
| 6–8 | ball world angular velocity XYZ | 50 rad/s |
| 9–11 | paddle world position XYZ | same position scales as ball |
| 12–15 | canonical paddle quaternion XYZW | component clamp |
| 16–18 | paddle world linear velocity XYZ | 8 m/s |
| 19–21 | paddle world angular velocity XYZ | 18 rad/s |
| 22–24 | ball position from paddle XYZ | half-width + 2 m, 8 m, court length + 4 m |
| 25–27 | ball velocity from paddle XYZ | 33 m/s |
| 28 | elapsed episode time | 6 s, clamped to `[0, 1]` |
| 29–34 | last-touch state | six-value one-hot |
| 35 | controlled-paddle contact count | count / 4, clamped to `[0, 1]` |
| 36 | ball-floor contact count | count / 4, clamped to `[0, 1]` |

Invalid observations are rejected rather than silently encoded.

## 6. Action contract

Action version: `paddle-action-v0`

The policy supplies normalized local linear XYZ and angular XYZ commands through
the frozen `env-v0` action type. Simulation applies the existing bounds,
clamping, 60 Hz control cadence, and 120 Hz physics cadence. Phase 1A does not
change action semantics.

## 7. Reward mapping

Mapping version: `phase1a-reward-v0`

Mapping hash: `d8a9bd0a07a33a23`

| Feature | Weight |
|---|---:|
| controlled paddle contact | `+0.25` per contact |
| far-court landing | `+1.00` |
| near-court landing | `-0.25` |
| out landing | `-0.50` |
| net contact | `-0.05` per contact |
| target distance at landing | `-0.05` per metre |
| clamped action | `-0.02` per clamp |
| invalid state | `-1.00` |
| elapsed time | `-0.002` per second |

Elapsed cost uses the difference from the previous step, not absolute elapsed
time. Simulation continues to emit unweighted facts; this mapping belongs to
the evaluation/trainer side of the boundary.

## 8. Baselines

`baseline/zero-v0` emits the canonical zero action. It detects accidental
successes and establishes the no-control floor.

`baseline/intercept-v0` predicts a reachable pre-floor intercept, remains on the
near side of the net, pitches the paddle by 25 degrees, and adds a bounded
forward contact stroke. It is a deterministic comparator, not a target
implementation or a learned policy.

Both baselines run the identical 1,000 held-out manifests. Evaluation must
record the source commit, protocol hash, environment version, Unity version,
platform, and every episode result.

## 9. Metrics

The committed report includes:

- terminal episode count;
- paddle-contact rate;
- legal-return rate, defined as paddle contact followed by `FarCourtLanding`;
- target-hit rate, defined as a legal return landing within 1.0 m of target;
- target-hit rate conditioned on a legal return;
- net-contact, out-landing, and playable-volume-exit rates;
- mean landing error over legal returns;
- mean normalized action delta and peak paddle speed;
- mean mapped episode return;
- contact, legal-return, and target-hit rates by launch-speed, spin, and
  placement bucket.

No failure terminal may be omitted because it is not an out landing.

## 10. Readiness gate

After 256 warm-up actions, the evaluator runs 20,000 real `env-v0` actions on
validation launches using the intercept baseline. The Editor gate requires:

- at least 500 actions per second;
- no more than 4,096 managed bytes per action;
- a valid Unity `GC Allocated In Frame` profiler counter.

Allocation is the counter delta over the synchronous measurement window. This
is an Editor regression guardrail, not a claim about a built player or a
trainer-connected process. Phase 1B must benchmark the actual adapter and
headless player separately.

## 11. Trainer selection

The first adapter targets `com.unity.ml-agents@4.0.3`, the exact package exposed
by the Unity 6 project registry when Phase 1A was frozen. The matching upstream
release line documents ML-Agents Python `1.1.0` and Python `3.10.12`.

The trainer package and Python/PyTorch environment are deliberately not
installed in Phase 1A. Before Phase 1B training, a small compatibility smoke
must prove the exact Unity/Python pair, and storage must be prepared outside the
space-constrained system volume if necessary. A custom low-level adapter remains
an allowed fallback without changing `env-v0`.

## 12. Exit criteria

Phase 1A closes only when:

1. protocol and assembly-boundary EditMode tests pass;
2. normal PlayMode observation, baseline, and readiness tests pass;
3. both baselines complete exactly 1,000 held-out episodes;
4. no episode is unclassified or ends in an invalid action/numeric state;
5. the readiness thresholds pass with the allocation counter available;
6. Phase 0 and Phase 1A suites pass from a source-exact clean checkout;
7. the baseline summary, readiness report, per-episode JSONL, and NUnit results
   are committed with their source commit and limitations.

Changing a seed partition, stage, observation, action, reward weight, metric
definition, threshold, or trainer selection requires a new accepted decision
and protocol version.
