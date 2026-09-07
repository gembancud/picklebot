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
4. [Phase 1A specification](docs/PHASE1A_SPEC.md) — the frozen seed partitions,
   curriculum, observation/reward protocol, baselines, and readiness gates.
5. [Phase 1B physics calibration](docs/PHASE1B_PHYSICS_CALIBRATION_SPEC.md) —
   the measured ball, flight, paddle, court, and net gate required before
   training.
6. [Decision record](docs/DECISIONS.md) — the accepted rationale and the only
   process for changing established direction.
7. [Development setup](docs/DEVELOPMENT.md) — pinned Unity and editor-tooling
   versions, local project setup, and verification entry points.

Accepted decisions are never silently rewritten. A behavioral change needs a
new decision entry, updated tests, and updates to every affected canonical
document.

## Current focus: independent player agents

Four player instances use separate observations and actions, with shared learned
policy parameters. The experimental scene is
`Assets/Picklebot/Scenes/IndependentPlayers.unity`.
Training has not passed final match-strength acceptance. Physics is provisional.

See [Player-agent progress](docs/PLAYER_AGENTS_PROGRESS.md) and
[Move the project and saved weights](docs/PLAYER_AGENTS_TRANSFER.md).
The selected checkpoints are included with the source. Bulk training data is not.

## Preserved full-body doubles baseline

The base doubles goal passed its acceptance checks. It includes four articulated
players, doubles rules, trained contact corrections and competitive team play.
The separate scene is
`Assets/Picklebot/Scenes/PickleballDoubles.unity`.

See [Doubles controls](docs/PICKLEBALL_DOUBLES.md) and
[Doubles acceptance status](docs/DOUBLES_PROGRESS.md). D-029 records the scope.
Physics remains provisional. Earlier demos remain available.

## Previous full-size AI match

Open `Assets/Picklebot/Scenes/PickleballMatch.unity` and press Play to watch
two separate AI shot policies compete on the full-size court. This provisional
experiment trains shot choice with terminal point rewards. Paddle contact uses
an explicitly labelled scripted controller. See
[Full-size AI match](docs/PICKLEBALL_MATCH.md) for training and controls.
D-028 permits this experiment while measured physics calibration remains open.

## Full-size pickleball inspection

Open `Assets/Picklebot/Scenes/PickleballInspection.unity`, press Play, and click
the Game tab. Select a test with buttons 1–7. Space pauses the simulation.
The scene uses a full-size court, a 74 mm ball, and independent paddle
translation and rotation. It uses the provisional outdoor 40-hole ball profile
on an acrylic court. It does not run an AI model.

See [Pickleball inspection](docs/PICKLEBALL_INSPECTION.md) for controls,
measurements, limits, and the calibration steps required before more training.
D-027 records this change of focus. Existing trained demos remain unchanged.

## Previous prototype: competing AI paddles

Open `Assets/Picklebot/Scenes/AIRally.unity`, press Play, and select the Game
tab. Two neural agents compete under simplified ping-pong rules. Each agent
uses a learned stroke model and a learned shot-selection model. Space pauses
the scene; R repeats the current serve. The scene includes
score, rally count, and slow-motion controls.

The paddles are smaller, collisions lose energy, and the training reward is
based on winning points. See [Competitive match](docs/COMPETITIVE_MATCH.md)
for the physics limits, local training, and checks. D-026 extends the separate
prototype. The pickleball calibration work remains open. The previous
cooperative result is retained in [AI rally](docs/AI_RALLY.md).

## Pickleball calibration status

Phase 0 establishes:

- deterministic ball, paddle, court, and net physics;
- regulation-inspired court zones and scoring boundaries;
- scripted launches, episode resets, and seeded randomization;
- automated simulation tests and visible debugging tools;
- a trainer-independent observations/actions/rewards interface.

Phase 0 closed on 2026-07-26 after the committed verification suite and a
10,000-episode seeded headless soak passed from the frozen source snapshot.
The run is recorded in the roadmap milestone and the environment contract is
tagged `env-v0`.

Phase 1A adds the trainer-independent evaluation foundation: disjoint seed
partitions, a staged curriculum, frozen observations and reward mapping,
scripted baselines, metrics, and training-readiness checks. It prepares a
repeatable training experiment, now scheduled as Phase 1C; it does not claim
that reinforcement learning has started or produced a checkpoint. Phase 1A
closed on 2026-07-26 from the source-exact clean-checkout evidence recorded in
the roadmap.

Phase 1B now calibrates real pickleball ball flight, rebound, paddle contact,
court contact, and net geometry before training. Phase 1C owns trainer
installation and the first learning smoke. This inserted gate is recorded by
D-020 so the earlier Phase 1A milestone remains historically accurate.

## Direction in one paragraph

Unity owns simulation and presentation. Training code communicates through a
small environment contract so the project can evaluate ML-Agents or a modern
custom trainer without rewriting the game. Numeric paddle control comes first,
followed by pretrained locomotion, residual whole-body control, scripted
opponents, and only then self-play. Camera observations and other high-complexity
research branches remain optional until the numeric baseline is proven.
