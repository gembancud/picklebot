# Picklebot roadmap

Status: **Accepted**

This roadmap defines the order in which Picklebot capabilities are built. It is
deliberately gated: a later phase may be explored in a branch, but it does not
become the project focus until the previous phase's exit criteria are recorded
as passing.

D-025 adds a user-directed exception: the current focus is a separate playable
3D ping-pong rally prototype. Its learned paddle actions, simplified physics,
and verification are documented in [AI_RALLY.md](AI_RALLY.md). Completion of
that prototype does not close the pickleball calibration or Phase 1C gates.

D-026 changes this prototype from cooperative returns to competitive points.
The current work uses smaller paddles, energy loss, limited paddle speed, and
point-winning shot selection. See [COMPETITIVE_MATCH.md](COMPETITIVE_MATCH.md).
The earlier cooperative benchmark remains historical evidence, not a score for
the new physics or model.

## North-star outcome

D-029 added a five-stage doubles goal: match rules, articulated bodies,
bounded contact, trained contact and shot choice, then validated 2v2 games.
The base prototype passed its checks on 2026-09-06.
See [DOUBLES_PROGRESS.md](DOUBLES_PROGRESS.md) for the acceptance evidence. This
work uses provisional physics and does not close the empirical calibration gate.

D-028 permits a provisional full-size competitive training experiment at the
user's request. Its first stage learns shot choice with explicit scripted
contact assistance. This exception does not close the empirical calibration
gate or claim learned paddle contact. See [PICKLEBALL_MATCH.md](PICKLEBALL_MATCH.md).

D-027 returns the current focus to full-size pickleball inspection before
further training. The selected reference is an outdoor 40-hole ball on an
acrylic court. The inspection scene adds manual six-axis paddle control,
bounded player markers, free-running contact presets, and rally-rule checks.
See [PICKLEBALL_INSPECTION.md](PICKLEBALL_INSPECTION.md).

The next gates are measured court rebounds, angled contacts, flight decay,
and paddle strokes. Fit and validate those parameters before freezing the new
training environment. A plausible animation or a passing simulated drop test
does not close the empirical calibration gate. Do not reuse the table-scale
model as evidence for this full-size environment.

Train a physics-based 3D agent that can acquire increasingly complete
pickleball behavior while keeping each source of progress measurable:

1. paddle control;
2. court positioning and locomotion;
3. coordinated whole-body strokes;
4. rally strategy against varied opponents;
5. adaptation through self-play.

The project is a learning and research system first. Photorealism, exhaustive
rules coverage, camera-only play, and deployment to a physical robot are not
early roadmap requirements.

## Rules that apply to every phase

- Unity owns simulation and presentation.
- Core simulation code does not depend on a trainer SDK.
- Measurements and regression tests are added with each capability.
- Numeric state observations are the default until the numeric policy is a
  stable baseline.
- New complexity must beat or meaningfully extend the preceding baseline.
- Reward changes are versioned with evaluation results; they are not silently
  tuned in place.
- A phase is complete only when its exit criteria pass from a clean,
  reproducible run.

## Phase 0 — Deterministic simulation foundation

### Purpose

Build a trusted environment before introducing a learning algorithm.

### Deliverables

- A Unity project pinned to one editor version and committed physics settings.
- Court, net, ball, and simplified paddle prefabs using SI units.
- Project-owned random-number streams and seeded scenario generation.
- Fixed-step simulation, reset lifecycle, event classification, and episode
  termination.
- The trainer-independent contract in
  [ENVIRONMENT_SPEC.md](ENVIRONMENT_SPEC.md).
- Scripted and recorded action sources that exercise the same contract a
  trainer will use.
- EditMode and PlayMode tests plus a headless regression command.
- Debug overlays for trajectories, contacts, zones, state, seed, and terminal
  reason.

### Exit criteria

- The committed Phase 0 verification suite passes.
- Identical seeds produce identical generated launch parameters.
- Supported-environment replay produces the same event sequence and terminal
  reason, with numeric state inside the tolerances in the environment spec.
- Boundary, net, reset, contact, timeout, and invalid-state tests pass.
- At least 10,000 seeded headless episodes complete without NaN, infinity,
  leaked state, or an unclassified termination.
- A clean checkout can run the tests using documented commands.
- The contract is tagged `env-v0`.

### Explicitly deferred

ML-Agents, Python trainers, neural policies, humanoid locomotion, self-play,
camera observations, photorealistic assets, and full match scoring.

## Phase 1 — Learned paddle returns

### Purpose

Prove that a policy can learn ball contact and target placement without
locomotion or whole-body control obscuring the result.

### Phase 1A — Evaluation and training readiness

Before installing a trainer or producing a checkpoint:

- freeze disjoint training, validation, and held-out seed partitions;
- freeze the numeric observation, action, reward, curriculum, and metric
  protocol;
- establish zero-action and deterministic intercept baselines;
- prove the real environment step path meets provisional throughput and managed
  allocation limits;
- select a trainer adapter target while keeping trainer dependencies outside
  the simulator;
- record clean-checkout evidence without claiming learned behavior.

The normative details and close gate are in
[PHASE1A_SPEC.md](PHASE1A_SPEC.md).

### Phase 1B — Pickleball physics calibration

Before installing a trainer or optimizing a policy:

- calibrate an outdoor 40-hole reference ball against measured drop and flight
  traces;
- replace generic damping with versioned quadratic drag and spin-lift behavior;
- calibrate court rebound and a project PBCoR surrogate for paddle contact;
- use a bounded, versioned residual-slip surrogate so kinematic paddle brushes
  create observable ball spin before trainer integration;
- correct the representative paddle and regulation post-span net collision
  geometry;
- prove deterministic replay, stability, and readiness remain inside committed
  limits;
- freeze the calibrated simulator as `env-v1`;
- prepare a replacement Phase 1C evaluation protocol with new untouched final
  seeds.

The normative fixtures, measurements, thresholds, evidence, and close gate are
in
[PHASE1B_PHYSICS_CALIBRATION_SPEC.md](PHASE1B_PHYSICS_CALIBRATION_SPEC.md).
Phase 1B remains open until that specification's empirical close gate passes.
D-023 permits only the separately versioned Phase 1C0 diagnostic probe below;
it does not freeze `env-v1`, close Phase 1B, or authorize a final Phase 1C
claim.

### Physics Museum — interactive feel-check interlude

Before Phase 1C trainer integration, inspect the frozen `env-v1` behavior in the
interactive Physics Museum. Its six stations expose ball drop/rebound, spin
flight, court bounce, paddle brush/spin transfer, net clearance/contact, and a
free-hit regulation court through the same environment contract the agent will
use.

This is a human-sensemaking and regression aid, not a substitute for Phase 1B's
numeric calibration evidence. Museum controls, camera work, telemetry, and
trajectory rendering remain outside the authoritative simulator assemblies.
See [PHYSICS_MUSEUM.md](PHYSICS_MUSEUM.md).

### Phase 1C0 — Provisional learned-return probe

Phase 1C0 deliberately trains against the current `provisional-unfitted`
simulator so learned behavior can expose exploits and feel problems before the
remaining empirical calibration work is available. Its normative contract is
[PHASE1C0_LEARNING_PROBE_SPEC.md](PHASE1C0_LEARNING_PROBE_SPEC.md).

This probe must:

- use only the new Phase 1C training and validation seed partitions;
- keep the final-evaluation partition inaccessible;
- use a trainer adapter outside the core and simulation assemblies;
- record the exact simulator/configuration hash, protocol hash, package pair,
  Python environment, trainer configuration, training seed, checkpoint, and
  per-episode metrics;
- visibly replay a neural policy in Unity with no heuristic or scripted action
  override;
- label every model, metric, and trajectory provisional and disposable if the
  physics configuration changes.

Phase 1C0 is successful when one bounded local run produces a checkpoint that
visibly tracks and strikes varied incoming balls and records legal returns on
unseen validation launches. This is a learning-system integration and
diagnostic milestone, not completion of Phase 1C and not evidence that Phase 1B
is calibrated.

### Phase 1C — First learned return

#### Scope

- Use the `env-v1` calibrated kinematic paddle and numeric observations.
- Train continuous paddle motion against seeded launch curricula.
- Start with a large contact region and low launch variance, then narrow the
  region and expand speed, spin, and placement.
- Add an ML-Agents adapter or a custom Python adapter; core simulation remains
  unchanged.
- Establish scripted and heuristic baselines before comparing learned policies.

#### Evaluation set

Use a held-out, versioned seed set. Report at minimum:

- contact rate;
- legal-return rate;
- target-zone accuracy;
- net and out rate;
- mean landing error;
- action smoothness and peak paddle speed;
- performance by launch-speed, spin, and placement bucket.

#### Exit criteria

- A trained policy materially exceeds the committed scripted baseline on legal
  returns and target accuracy.
- Results reproduce across at least three training seeds.
- Evaluation never trains on the held-out seed set.
- Reward terms, weights, trainer configuration, environment version, and model
  checkpoint are recorded together.
- Policy performance survives the approved Phase 1 randomization envelope.

## Phase 2 — Court movement with pretrained locomotion

### Purpose

Add positioning while avoiding the cost and ambiguity of learning locomotion
from scratch.

### Scope

- Integrate and benchmark a pretrained humanoid locomotion controller.
- Give the policy high-level movement targets plus the established paddle/stroke
  command.
- Preserve a locomotion-only test scene and metrics so integration regressions
  are visible.
- Expand launches from a reachable local region to regulation-inspired court
  coverage.
- Penalize falls, unstable motion, and unreachable commands through named
  features, not hidden controller logic.

### Exit criteria

- The integrated controller reaches sampled intercept poses within documented
  position, orientation, and timing tolerances.
- The agent improves court-wide legal-return rate over a no-locomotion baseline.
- Falls and controller saturation remain below committed thresholds.
- Phase 1 paddle skill does not regress outside an agreed tolerance on its
  original evaluation set.

## Phase 3 — Residual whole-body strokes

### Purpose

Move from a scaffolded paddle target to coordinated, physically plausible
whole-body stroke control.

### Scope

- Begin with IK, reference motions, or procedural strokes as scaffolding.
- Train bounded residual corrections around the scaffold.
- Unlock control progressively: paddle/wrist, arm, torso, then lower-body
  coordination only when the preceding stage is stable.
- Preserve joint limits, collision constraints, and locomotion stability.

### Exit criteria

- Residual control outperforms the fixed scaffold on placement and robustness.
- Ablations show which unlocked control groups produce the improvement.
- Falls, joint-limit violations, energy use, and motion discontinuity are
  measured and remain inside committed thresholds.
- The agent remains functional when residual output is set to zero.

## Phase 4 — Rally construction against scripted opponents

### Purpose

Learn multi-shot recovery, positioning, and shot selection before introducing a
moving learning target.

### Scope

- Add deterministic scripted opponents with named difficulty profiles.
- Extend episodes from a single exchange to rallies.
- Add serve, double-bounce, non-volley-zone, and scoring rules only to the
  fidelity required for rally learning and evaluation.
- Build curricula across opponent placement, pace, spin, and strategy.

### Exit criteria

- The agent sustains rallies and wins points against every committed scripted
  profile at published rates.
- Metrics separate return execution from recovery and decision quality.
- Earlier single-exchange evaluation sets still run to expose skill regression.
- Rule outcomes have automated tests and no ambiguous terminal states.

## Phase 5 — Population training and self-play

### Purpose

Develop strategies that are not overfit to a finite collection of scripts.

### Scope

- Start from the validated Phase 4 agent and scripted-opponent mixture.
- Train against checkpoint populations rather than only the latest policy.
- Track rating, exploitability indicators, strategy diversity, and catastrophic
  forgetting.
- Keep scripted opponents and frozen checkpoints in every evaluation.

### Exit criteria

- Population-trained agents improve against a held-out opponent suite, not just
  their current training partners.
- Results reproduce across multiple population and training seeds.
- The system can identify and recover from regressions against older
  checkpoints.
- Match evaluation is separated from training and uses a published protocol.

## Phase 6 — Optional research branches

These are intentionally not promised until Phases 0–5 establish a credible
baseline:

- camera or multimodal observations;
- hole-resolved aerodynamics, wind, and deformable ball/paddle/net models;
- motion-capture style priors;
- human demonstrations or offline reinforcement learning;
- sim-to-real transfer;
- cooperative doubles play;
- photorealistic presentation.

Each branch needs its own accepted decision record, baseline, and evaluation
plan before becoming roadmap work.

## Milestone record

When a phase closes, add a dated section here containing:

- the commit and environment version;
- commands used for verification;
- evaluation artifact locations;
- passed thresholds and known limitations;
- the accepted decision that opens the next phase.

Do not rewrite an old milestone to match later understanding. Correct it with a
dated note or a superseding decision so the historical record stays legible.

### 2026-07-26 — Phase 0 closed and env-v0 frozen

- Environment: `env-v0`
- Verified source commit:
  `b84125dbd2742d17fdd706ab79515069e8683f7e`
- Closing decision: [D-016](DECISIONS.md#d-016--freeze-the-passing-phase-0-contract-as-env-v0)
- Release tag: `env-v0`
- Supported verification setup: Unity `6000.5.5f1`, `OSXEditor`, Apple M1 Pro,
  16 GB memory

The source-exact checkout was verified with:

```bash
PICKLEBOT_SOURCE_COMMIT=b84125dbd2742d17fdd706ab79515069e8683f7e \
  ./scripts/phase0-editmode.sh
PICKLEBOT_SOURCE_COMMIT=b84125dbd2742d17fdd706ab79515069e8683f7e \
  ./scripts/phase0-playmode.sh
PICKLEBOT_SOURCE_COMMIT=b84125dbd2742d17fdd706ab79515069e8683f7e \
  ./scripts/phase0-soak.sh
```

Results:

- EditMode: 27 passed, 0 failed, 0 skipped.
- Normal PlayMode: 16 passed, 0 failed, 0 skipped.
- Soak gate: 1 passed test covering exactly 10,000 episodes over seeds
  `1000000`–`1009999`.
- Soak integrity: 10,000 terminals, 0 invalid numeric states, 0 unclassified
  terminations, and 0 state-leak failures.
- Terminal distribution: 5,082 `FarCourtLanding`, 3,331
  `NearCourtLanding`, 476 `OutOfBoundsLanding`, and 1,111
  `PlayableVolumeExit`.
- Configuration identity: `sim-config-v0` /
  `b584437e3d227d89`.
- Physics settings identity: `17155161017eb197`.

Versioned evidence:

- [EditMode NUnit result](evidence/phase0/tests/editmode-results.xml) —
  SHA-256 `d813b45477cd6f0710dc8081df0a9a1d73c993695ea1b436ab18a3e78500710c`
- [PlayMode NUnit result](evidence/phase0/tests/playmode-results.xml) —
  SHA-256 `466b8c73e5b57684886419d37ed4947ba45194389f8266f6814569c66eb6b36a`
- [Soak NUnit result](evidence/phase0/tests/soak-results.xml) —
  SHA-256 `7133848e4ecfa24a48eafbd313b931566b8d87c999edec5347b64981a5e90c23`
- [Soak summary](evidence/phase0/soak/summary.json) —
  SHA-256 `a9ad0127841e5fb940ca56a73cbaae554ab7d6cb54c017b1f5abb44cba734378`
- [10,000 episode manifests](evidence/phase0/soak/episodes.jsonl) —
  SHA-256 `bc588c26c395ebf13811fcf7c410bb73071e0e4bc82972d9a41f66be5e9e390e`
- [Runtime scene](evidence/phase0/phase0-runtime-sloped-net.png)

Known limits:

- Replay is supported as event-equivalent with the numeric tolerances in the
  environment specification; cross-platform bit identity is not claimed.
- The paddle and sloped two-box net are intentionally simplified collision
  models, and the invisible catch floor exists only to classify out landings.
- Phase 0 covers deterministic single-exchange simulation, not a learned
  policy, humanoid locomotion, full match rules/scoring, or a skill benchmark.

Phase 1 may now begin under its accepted scope, but no trainer, policy, or
Phase 1 implementation is included in this milestone.

### 2026-07-26 — Phase 1A evaluation foundation closed

- Environment: `env-v0`
- Protocol: `phase1a-protocol-v0` / `4ae0928d344f1c3c`
- Reward mapping: `d8a9bd0a07a33a23`
- Verified implementation commit:
  `48963c26d761b423e2ca124f11c576cd6880eea0`
- Closing decision:
  [D-019](DECISIONS.md#d-019--close-phase-1a-on-source-exact-baseline-evidence)
- Supported verification setup: Unity `6000.5.5f1`, `OSXEditor`, Apple M1 Pro,
  16 GB memory

The source-exact clean checkout was verified with:

```bash
PICKLEBOT_SOURCE_COMMIT=48963c26d761b423e2ca124f11c576cd6880eea0 \
  ./scripts/phase1a-verify.sh
```

Test results:

- Phase 0 EditMode: 27 passed, 0 failed, 0 skipped.
- Phase 0 normal PlayMode: 16 passed, 0 failed, 0 skipped.
- Phase 1A EditMode: 12 passed, 0 failed, 0 skipped.
- Phase 1A normal PlayMode: 3 passed, 0 failed, 0 skipped.
- Phase 1A exact evidence gate: 1 passed test covering two policies over
  exactly 1,000 held-out episodes each.

Baseline results:

- Zero action: 0% contact, 0% legal return, 0% target hit; all 1,000 episodes
  ended as `NearCourtLanding`.
- Intercept heuristic: 100% contact, 33.4% legal return, 28.8% overall target
  hit, and 86.23% target hit conditioned on a legal return.
- Intercept terminals: 334 `FarCourtLanding` and 666 `PlayableVolumeExit`;
  there were no out landings, invalid states, invalid actions, or unclassified
  terminals.
- Intercept limitations: 0% legal returns in the 333-episode fast bucket and
  50.07% in the 667-episode medium bucket.
- Mean landing error over 334 legal returns: `0.93166 m`.
- Mean action delta: `0.015901`; peak paddle speed: `6.201724 m/s`.

Readiness results:

- 20,000 measured actions and 527 completed validation episodes.
- `4,439.06` actions/second against a minimum of `500`.
- `2,093.23` managed bytes/action against a maximum of `4,096`.
- Unity's `GC Allocated In Frame` counter was available; the readiness gate
  passed.

Versioned evidence:

- [Phase 1A summary](evidence/phase1a/summary.json) —
  SHA-256 `f11cf14dc397be51eedab2511c6bfd3ef549192ce909ac016c071504ecf3e4f4`
- [Phase 1A readiness](evidence/phase1a/readiness.json) —
  SHA-256 `54b67691b274010bb38392cf5f9a403a7dbce3fa0633a06eb469f94de058a0fe`
- [2,000 held-out episode records](evidence/phase1a/episodes.jsonl) —
  SHA-256 `ded856b722306349bf571c4a6e7688b947a7d6f28b13986519fec3ed6285df5b`
- [Phase 1A EditMode NUnit result](evidence/phase1a/tests/editmode-results.xml) —
  SHA-256 `10473abaf4bbec2ceab445a1768def4cbfd15324955202334c097f114f6952b4`
- [Phase 1A PlayMode NUnit result](evidence/phase1a/tests/playmode-results.xml) —
  SHA-256 `6df96fe7946f2b12866b044468459992d8efd03d49d4cc85b808ff4dd65b5855`
- [Phase 1A evidence NUnit result](evidence/phase1a/tests/evidence-results.xml) —
  SHA-256 `ebd919b78a0c7f78c207531113f1bd34cc5c6ede9ca2d0680f4769c092d676aa`

Known limits:

- Phase 1A establishes evaluation and readiness, not a learned policy.
- The selected ML-Agents and Python packages are not installed; their exact
  interoperability remains a Phase 1B smoke gate.
- Allocation and throughput were measured synchronously in the Unity Editor,
  not in a trainer-connected standalone player.
- The heuristic's 66.6% playable-volume-exit rate and complete failure in the
  fast bucket are explicit training opportunities, not hidden successes.

Phase 1B may now install the isolated trainer environment and adapter, then run
a bounded learning smoke on training/validation seeds. The held-out seeds remain
untouched until a checkpoint and experiment configuration are frozen.

### 2026-07-26 — D-020 inserts physics calibration before training

The Phase 1A milestone above is retained verbatim as historical evidence of
what was accepted when it closed. D-020 supersedes only its next-phase
scheduling statement:

- Phase 1B is now the measured pickleball physics calibration gate and produces
  `env-v1`;
- trainer installation, adapter integration, and the first learned return move
  to Phase 1C;
- `env-v0`, `phase1a-protocol-v0`, and their recorded evidence remain
  immutable;
- Phase 1C receives a new `env-v1`-dependent protocol and untouched final
  evaluation seeds before training.
