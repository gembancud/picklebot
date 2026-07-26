# Picklebot

Picklebot is a learning-focused project for training physics-based 3D agents to
play pickleball. The project starts with a deterministic court and a simplified
paddle controller, then introduces locomotion and whole-body humanoid control
in measurable stages.

## Canonical project direction

Start here before changing simulation, learning, or evaluation behavior:

1. [Architecture](docs/ARCHITECTURE.md) — the system boundary and short
   architectural map.
2. [Roadmap](docs/ROADMAP.md) — the accepted phase order, deliverables, and
   evidence-based exit gates.
3. [Environment specification](docs/ENVIRONMENT_SPEC.md) — the normative Phase
   0 contract, geometry, timing, lifecycle, observations, actions, events,
   termination, and verification requirements.
4. [Decision record](docs/DECISIONS.md) — the accepted rationale and the only
   process for changing established direction.
5. [Development setup](docs/DEVELOPMENT.md) — pinned Unity and editor-tooling
   versions, local project setup, and verification entry points.

Accepted decisions are never silently rewritten. A behavioral change needs a
new decision entry, updated tests, and updates to every affected canonical
document.

## Current milestone: Phase 0 complete

Phase 0 establishes:

- deterministic ball, paddle, court, and net physics;
- regulation-inspired court zones and scoring boundaries;
- scripted launches, episode resets, and seeded randomization;
- automated simulation tests and visible debugging tools;
- a trainer-independent observations/actions/rewards interface.

No reinforcement-learning framework is required for Phase 0.

Phase 0 closed on 2026-07-26 after the committed verification suite and a
10,000-episode seeded headless soak passed from the frozen source snapshot.
The run is recorded in the roadmap milestone and the environment contract is
tagged `env-v0`. Phase 1 training has not started.

## Direction in one paragraph

Unity owns simulation and presentation. Training code communicates through a
small environment contract so the project can evaluate ML-Agents or a modern
custom trainer without rewriting the game. Numeric paddle control comes first,
followed by pretrained locomotion, residual whole-body control, scripted
opponents, and only then self-play. Camera observations and other high-complexity
research branches remain optional until the numeric baseline is proven.
