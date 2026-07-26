# Picklebot roadmap

Status: **Accepted**

This roadmap defines the order in which Picklebot capabilities are built. It is
deliberately gated: a later phase may be explored in a branch, but it does not
become the project focus until the previous phase's exit criteria are recorded
as passing.

## North-star outcome

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

### Scope

- Use the Phase 0 simplified paddle and numeric observations.
- Train continuous paddle motion against seeded launch curricula.
- Start with a large contact region and low launch variance, then narrow the
  region and expand speed, spin, and placement.
- Add an ML-Agents adapter or a custom Python adapter; core simulation remains
  unchanged.
- Establish scripted and heuristic baselines before comparing learned policies.

### Evaluation set

Use a held-out, versioned seed set. Report at minimum:

- contact rate;
- legal-return rate;
- target-zone accuracy;
- net and out rate;
- mean landing error;
- action smoothness and peak paddle speed;
- performance by launch-speed, spin, and placement bucket.

### Exit criteria

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
- higher-fidelity aerodynamics and paddle/ball materials;
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
