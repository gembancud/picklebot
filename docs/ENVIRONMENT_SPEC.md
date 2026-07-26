# Picklebot environment specification

Specification version: **env-v0-draft**

Scope: **Phase 0 simulation contract**

Normative terms such as **must**, **must not**, **should**, and **may** describe
requirements for declaring Phase 0 complete. This document becomes `env-v0`
when every Phase 0 exit criterion is satisfied. Incompatible contract changes
after that point require a new environment version.

## 1. Design goals

The Phase 0 environment must:

- produce stable, testable ball, paddle, court, and net interactions;
- reset every episode without state leakage;
- generate scenarios from explicit seeds;
- expose simulation facts without depending on a learning framework;
- support scripted control, replay, automated tests, and future trainers through
  the same step contract;
- make every episode termination classifiable.

The Phase 0 environment is not required to implement a policy, a trainer,
humanoid locomotion, full match scoring, camera observations, or every official
pickleball rule.

## 2. Units, axes, and time

All core state uses SI units:

- distance: metres;
- time: seconds;
- mass: kilograms;
- linear velocity: metres per second;
- angular velocity: radians per second;
- rotation: unit quaternion.

World coordinates follow Unity's axis convention:

- `+X`: across the court toward the controlled player's right;
- `+Y`: upward;
- `+Z`: from the controlled near side toward the far side;
- origin: court-floor centre directly below the net.

Canonical Phase 0 timing:

| Setting | Value |
|---|---:|
| Physics fixed step | `1 / 120 s` |
| Default action interval | `2 physics ticks` |
| Default control frequency | `60 Hz` |
| Maximum episode duration | scenario-defined, no more than `20 s` |
| Unity time scale | must not change simulated results |

Actions are held constant for the complete action interval. Tests may step one
physics tick at a time. A timing change is contract-affecting and requires a
decision record because it can change contacts and learned behavior.

## 3. Canonical geometry

Phase 0 uses a regulation-sized playing rectangle with simplified colliders:

| Element | Canonical value |
|---|---:|
| Court length | `13.4112 m` |
| Court width | `6.0960 m` |
| Half length | `6.7056 m` |
| Half width | `3.0480 m` |
| Non-volley-zone depth per side | `2.1336 m` |
| Net height at sidelines | `0.9144 m` |
| Net height at centre | `0.8636 m` |
| Ball nominal mass | `0.024 kg` |
| Ball nominal diameter | `0.074 m` |

Court and non-volley-zone lines are part of the region they bound. The initial
net may use a simplified static collider, but its visual mesh and collision
surface must agree closely enough that debug inspection is not misleading.

Ball drag, angular drag, restitution, friction, paddle dimensions, paddle mass,
and contact material values must live in a versioned simulation configuration
asset. They are calibration parameters, not untracked prefab defaults.

## 4. Simulation ownership and dependency boundary

The core simulation assembly owns:

- authoritative physics state;
- episode lifecycle;
- seeded scenario generation;
- event detection;
- zone and rule classification;
- observations;
- named reward features;
- termination reason;
- metrics.

It must not reference ML-Agents, a Python bridge, a specific neural-network
runtime, or trainer-owned types.

Adapters may:

- normalize or stack observations;
- map trainer actions into the canonical action command;
- weight named reward features;
- batch environments;
- serialize step results;
- expose the contract to a trainer.

Adapters must not alter court rules, silently clamp authoritative state, invent
terminal reasons, or bypass the reset lifecycle.

## 5. Episode lifecycle

Every environment follows this state machine:

```text
Uninitialized -> Resetting -> Ready -> Running -> Terminal
                     ^                      |
                     +----------------------+
```

### Reset

`Reset(request)` must:

1. stop simulation advancement;
2. clear queued actions, contacts, events, metrics, and reward features;
3. restore all rigidbody transforms, velocities, angular velocities, sleep
   states, and controller integrators;
4. restore scenario-owned score or rule state;
5. initialize independent random streams from the request seed;
6. generate and record the scenario parameters;
7. synchronize transforms before the next physics step;
8. return the initial observation in `Ready`.

No object from the prior episode may influence the next episode.

### Start and step

The first accepted action moves `Ready` to `Running`. `Step(action)` advances
exactly one action interval and returns one `StepResult`. Calls after `Terminal`
must fail visibly until reset; they must not advance hidden physics.

### Terminal

Exactly one primary terminal reason is recorded. Secondary events from the final
step remain available for diagnosis. Terminal state is immutable until reset.

## 6. Seed and reproducibility contract

The reset request contains:

```text
seed: unsigned 64-bit integer
scenario_id: stable string
difficulty: optional stable string
overrides: explicit test-only parameter map
```

Project-owned pseudo-random streams must be used instead of global
`UnityEngine.Random` state. Stream names are stable and independently derived
from the episode seed, for example:

- `launcher`;
- `ball_physics`;
- `paddle_start`;
- `domain_randomization`;
- `opponent` (reserved).

Adding a random draw to one stream must not shift values in another stream.
Every generated parameter is captured in the episode manifest.

Reproducibility has two levels:

1. **Generation determinism:** the same environment version, scenario, and seed
   must produce bit-identical generated parameters.
2. **Simulation reproducibility:** on the pinned Unity version, target platform,
   scripting backend, physics settings, and hardware class, a replay must
   produce the same ordered discrete events and terminal reason. Sampled
   positions and velocities must remain within the committed regression
   tolerances.

Phase 0 does not claim bit-identical PhysX trajectories across arbitrary
platforms or Unity versions.

## 7. Canonical action command

Phase 0 exposes one continuous simplified-paddle command:

```text
PaddleActionV0
  linear_velocity_local: float[3]   # each component in [-1, 1]
  angular_velocity_local: float[3]  # each component in [-1, 1]
```

The normalized components are scaled by versioned maximum linear and angular
speeds from the simulation configuration. The paddle uses a kinematic rigidbody
and physics-aware movement during fixed steps; gameplay code must not teleport
its transform during a running episode.

Action values must be finite. Out-of-range finite values are clamped and emit an
`ActionClamped` diagnostic event. NaN or infinite values terminate with
`InvalidAction`.

Scripted controllers, replay, tests, and trainer adapters all submit this same
command. If a later phase needs a different action space, it receives a new
version instead of silently changing `PaddleActionV0`.

## 8. Canonical observation snapshot

Core simulation emits raw, unnormalized SI state. Normalization belongs to an
adapter and must be versioned with the policy.

```text
ObservationV0
  environment_version: string
  episode_id: unsigned 64-bit integer
  seed: unsigned 64-bit integer
  scenario_id: stable string
  physics_tick: unsigned 64-bit integer
  elapsed_time: float

  ball:
    position_world: float[3]
    rotation_world: float[4]
    linear_velocity_world: float[3]
    angular_velocity_world: float[3]

  paddle:
    position_world: float[3]
    rotation_world: float[4]
    linear_velocity_world: float[3]
    angular_velocity_world: float[3]

  relative:
    ball_position_from_paddle: float[3]
    ball_velocity_from_paddle: float[3]

  episode:
    state: enum
    last_touch: enum { None, Launcher, ControlledPaddle, Net, Floor, Other }
    controlled_paddle_contacts: integer
    ball_floor_contacts: integer
```

Every numeric field must be finite. Quaternion sign normalization must be
consistent so replay comparisons do not alternate between equivalent `q` and
`-q` representations.

Fields may be appended compatibly while the spec is a draft. Removing,
reinterpreting, reordering a positional encoding, or changing units after
`env-v0` requires a new observation version.

## 9. Events

Events are immutable facts emitted in deterministic order. Each contains
`physics_tick`, a per-tick sequence number, and relevant entity identifiers and
contact data.

Phase 0 event kinds:

- `EpisodeStarted`;
- `BallLaunched`;
- `BallPaddleContact`;
- `BallNetContact`;
- `BallFloorContact`;
- `BallEnteredZone`;
- `BallExitedPlayableVolume`;
- `ActionClamped`;
- `EpisodeTerminated`;
- `InvalidNumericState`.

Multiple low-level collision callbacks for one continuous contact manifold must
not be counted as multiple logical hits. Contact de-duplication rules and the
minimum separation needed to register another hit belong in the versioned
simulation configuration and require tests.

Event ordering within one physics tick is:

1. invalid-state detection;
2. physical contacts, ordered by stable entity identifier;
3. derived zone transitions;
4. termination.

## 10. Landing and zone classification

The first logical ball-floor contact produces a projected contact position and
classifies it against closed region boundaries with a documented epsilon.

Minimum classifications:

- `NearCourtIn`;
- `FarCourtIn`;
- `NearNonVolleyZone`;
- `FarNonVolleyZone`;
- `Out`;
- `Unknown` only when numeric state is invalid.

A boundary line is in. Classification code is shared by gameplay and tests; it
must not be duplicated in scene scripts.

Phase 0 records net contact as an event. A net touch alone is not necessarily
terminal because a ball may continue over the net. Scenarios determine whether
the eventual floor contact, playable-volume exit, or timeout ends the episode.

## 11. Terminal reasons

`TerminationReasonV0` is exhaustive for Phase 0:

- `FarCourtLanding`;
- `NearCourtLanding`;
- `OutOfBoundsLanding`;
- `PlayableVolumeExit`;
- `Timeout`;
- `InvalidAction`;
- `InvalidNumericState`;
- `ScenarioCompleted`;
- `TestAbort`.

`TestAbort` is forbidden in training or evaluation results. New terminal reasons
require tests and a compatible spec revision; an unclassified terminal state is
a Phase 0 failure.

## 12. Reward-feature boundary

The core environment emits named, unweighted features rather than one canonical
scalar reward. Phase 0 features are:

- `paddle_contact_count`;
- `far_court_landing`;
- `near_court_landing`;
- `out_landing`;
- `net_contact_count`;
- `target_distance_at_landing`;
- `elapsed_time`;
- `action_clamp_count`;
- `invalid_state`.

A trainer adapter converts these features to scalar or vector rewards. The
adapter must record the feature names, weights, transforms, environment version,
and trainer configuration with every run.

This boundary lets reward experiments change without changing physical truth.
If a feature requires new simulation behavior, that behavior still needs core
tests and a spec revision.

## 13. Scenario catalog

Phase 0 ships stable scenario families:

| Scenario ID | Purpose |
|---|---|
| `contact/front-on` | Repeatable ball-paddle collision |
| `launch/serve-like` | Representative high arc and floor landing |
| `launch/rally` | Representative incoming rally ball |
| `boundary/court` | In, line-touching, and out classification |
| `boundary/non-volley-zone` | Kitchen-line classification |
| `net/clear` | Ball clears the net |
| `net/contact-continues` | Net contact followed by continued flight |
| `reset/state-leak` | Reset after non-zero motion and counters |
| `stability/high-speed` | Worst-case supported contact speed |

Scenario defaults are versioned data, not values hidden in test code. Test-only
overrides must appear in the episode manifest.

## 14. Phase 0 verification suite

### Unit and EditMode tests

- geometry and zone boundaries, including every line and corner;
- seed derivation and random-stream independence;
- action validation and scaling;
- event de-duplication and ordering;
- terminal-reason exhaustiveness;
- observation finiteness and quaternion convention;
- configuration serialization and version identity.

### PlayMode tests

- ball-floor, ball-paddle, and ball-net contact;
- high-speed continuous collision detection;
- reset of transforms, velocities, counters, contacts, queued actions, and RNG;
- scenario lifecycle and timeout;
- identical-seed generation;
- recorded-action replay within tolerances.

### Headless soak

At least 10,000 seeded episodes must run with:

- zero invalid numeric states;
- zero unclassified terminations;
- zero state-leak failures;
- a terminal-reason count summing to the episode count;
- output of the environment version, Unity version, platform, physics settings
  hash, configuration hash, seed range, and result summary.

Numeric replay tolerances must be chosen from observed stable runs, committed in
the test configuration, and tight enough to catch a meaningful physics change.
They must never be loosened only to make a failing change pass; the reason and
evidence for a tolerance change belong in a decision record.

## 15. Debugging and run artifacts

The visible debug mode must show:

- seed, scenario, environment version, state, tick, and terminal reason;
- ball trajectory and velocity;
- paddle axes and commanded velocities;
- contact points and normals;
- court and non-volley-zone classification bounds;
- emitted events and reward features.

Every evaluation run must preserve or identify:

- source commit;
- environment and action/observation versions;
- Unity and trainer versions;
- simulation configuration hash;
- scenario set and seeds;
- reward mapping;
- model checkpoint, when applicable;
- aggregate metrics and per-episode manifest.

## 16. Versioning and change control

Changes are classified as:

- **Editorial:** wording only; no behavior or meaning change.
- **Compatible:** additive event, metric, or observation field with unchanged
  existing semantics.
- **Behavioral:** physics, timing, reset, classification, scenario, action,
  observation, reward-feature, or termination behavior changes.
- **Breaking:** an existing consumer would interpret data incorrectly or cannot
  continue.

Behavioral changes require:

1. a decision entry in [DECISIONS.md](DECISIONS.md);
2. updated tests and expected metrics;
3. a documented comparison against the prior environment version.

Breaking changes require a new contract version. Historical run artifacts must
always remain interpretable under the version that produced them.
