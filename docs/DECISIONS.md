# Picklebot decision record

Status: **Normative and append-oriented**

This file prevents the project direction from drifting through undocumented
reinterpretation. Accepted decisions remain visible even when superseded.

## How decisions change

- Do not silently rewrite an accepted decision's meaning or rationale.
- Editorial corrections are allowed when they do not change meaning.
- To change direction, add a new decision with a new ID, mark the old decision
  `Superseded by D-xxx`, and describe the evidence, trade-offs, migration, and
  affected roadmap/spec sections.
- Experimental branches may test alternatives without changing the accepted
  direction. They become direction only through an accepted decision.
- Phase gates, physics timing, contract semantics, observation/action spaces,
  reward-feature definitions, and evaluation protocols are behavioral decisions.

## Accepted decisions

### D-001 — Unity owns simulation and presentation

- Date: 2026-07-26
- Status: Accepted; superseded for new work by D-038 (2026-10-02). It still governs the frozen Unity reference.

Unity supplies 3D physics, collision handling, scenes, debugging, and
visualization. Training processes consume a project-owned environment contract;
they do not become the authoritative simulator.

Rationale: one authoritative state avoids duplicated physics and keeps episodes
visually inspectable.

### D-002 — The core is trainer-independent

- Date: 2026-07-26
- Status: Accepted

Core simulation assemblies must not depend on ML-Agents or a custom trainer.
Adapters translate between trainer types and the versioned environment contract.

Rationale: ML-Agents and modern custom trainers can be evaluated without
rewriting the game or corrupting historical comparisons.

### D-003 — Build a verified simulator before reinforcement learning

- Date: 2026-07-26
- Status: Accepted

Phase 0 contains no trainer or policy dependency. Physics, seeded generation,
reset, events, classification, contract behavior, debug tools, and automated
tests must pass before Phase 1 becomes the project focus.

Rationale: training results are uninterpretable when environment behavior is
still unstable.

### D-004 — Learn skills in increasing control complexity

- Date: 2026-07-26
- Status: Accepted

The learning sequence is:

1. simplified paddle returns;
2. court movement with pretrained locomotion;
3. residual whole-body strokes;
4. rallies against scripted opponents;
5. population training and self-play.

Rationale: this makes failures attributable and preserves useful baselines.

### D-005 — Numeric state precedes camera observations

- Date: 2026-07-26
- Status: Accepted

Initial agents observe structured numeric state. Vision is an optional later
research branch after a stable numeric policy exists.

Rationale: perception should not obscure whether control and reward design work.

### D-006 — Do not learn humanoid locomotion from scratch

- Date: 2026-07-26
- Status: Accepted

Phase 2 integrates and benchmarks a pretrained locomotion controller before
pickleball-specific whole-body fine-tuning.

Rationale: locomotion is a substantial research program on its own and is not
the project's first uncertainty.

### D-007 — IK and reference strokes are scaffolding

- Date: 2026-07-26
- Status: Accepted

IK, procedural strokes, or reference motions may bootstrap reliable behavior,
but the final whole-body controller uses bounded residual reinforcement learning
to improve and adapt the scaffold.

Rationale: scaffolds provide a stable starting point without imposing their
limitations as the final policy.

### D-008 — Scripted opponents precede self-play

- Date: 2026-07-26
- Status: Accepted

Multi-shot play is first trained and evaluated against deterministic,
versioned scripted opponents. Self-play begins only after those baselines pass.

Rationale: a moving opponent distribution makes diagnosis and reproducibility
harder; fixed profiles remain useful even after self-play starts.

### D-009 — Determinism is scoped, not overstated

- Date: 2026-07-26
- Status: Accepted

Generated scenario parameters must be bit-identical for the same seed.
Physics replay must be event-equivalent and numerically within committed
tolerances on the pinned supported environment. The project does not promise
bit-identical PhysX trajectories across arbitrary hardware, platforms, or Unity
versions.

Rationale: this is strong enough for regression testing without making an
unrealistic cross-platform claim.

### D-010 — Phase 0 runs physics at 120 Hz and control at 60 Hz

- Date: 2026-07-26
- Status: Accepted

The canonical physics step is `1/120 s`; one action is held for two ticks by
default. Any change requires replay evidence and a behavioral decision.

Rationale: fast ball-paddle contacts need finer simulation than the default
50 Hz commonly used by Unity, while 60 Hz remains a practical initial control
rate.

### D-011 — Core simulation emits facts and unweighted reward features

- Date: 2026-07-26
- Status: Accepted

The simulator emits events, metrics, and named reward features. Trainer adapters
own scalar weights and transforms, and record them with every run.

Rationale: physical truth remains stable while reward experiments stay explicit
and reproducible.

### D-012 — Roadmap progress is gated by recorded evidence

- Date: 2026-07-26
- Status: Accepted

Later-phase exploration may occur, but the project focus moves forward only
after the current phase's exit criteria pass and the milestone record identifies
the source version, verification commands, artifacts, results, and limitations.

Rationale: a dated evidence trail prevents later success from being projected
back onto an unfinished foundation.

### D-013 — Phase 0 scenario parameters are committed contract data

- Date: 2026-07-26
- Status: Accepted

The nine Phase 0 scenario families are generated by
`ScenarioCatalogV0` from committed defaults, named random streams, difficulty,
and manifest-recorded test overrides. The two net-isolation scenarios place the
controlled paddle behind the launcher so `net/clear` and
`net/contact-continues` measure the net rather than an unintended paddle hit.
The `contact/front-on` and `stability/high-speed` families seed one shared
horizontal contact lane for the ball and paddle, so randomness changes the lane
without turning a contact scenario into a miss scenario.

Rationale: a stable scenario ID is not reproducible if its launch and object
placement parameters are hidden in scenes or tests. Separating the paddle from
the net trajectory also makes each scenario test one named behavior.

Evidence: identical-seed, override-canonicalization, net-clear, and
net-contact PlayMode/EditMode tests in the Phase 0 verification assemblies.

Trade-offs: scenario calibration is now behavioral contract data. Future
changes require a new decision, before/after evidence, and updated regression
expectations.

Affected roadmap/spec sections: Phase 0 deterministic foundation,
environment specification sections 6, 13, 14, and 16.

### D-014 — Out landings use an invisible classification catch floor

- Date: 2026-07-26
- Status: Accepted

The regulation court mesh and its collider remain exactly aligned with the
official playing rectangle. A second non-rendered floor collider sits slightly
below that surface and extends to the configured playable-volume margin.
In-bounds balls contact the visible court first; balls outside the court contact
the lower catch floor and are classified `Out`.

Rationale: without physical support outside the playing rectangle, an out ball
falls through empty space and can only terminate as `PlayableVolumeExit`.
Landing classification requires a contact surface, but enlarging the visible
court collider would make the debug geometry misleading.

Evidence: the PlayMode suite separately verifies a boundary-line
`FarCourtLanding`, an `OutOfBoundsLanding`, and a true
`PlayableVolumeExit`.

Trade-offs: out-of-bounds landing contact points are approximately 2.5 cm below
the regulation surface before projection to `Y=0`. The classifier always uses
the projected point, so zone semantics remain in canonical court coordinates.

Affected roadmap/spec sections: environment specification sections 3, 10, 11,
14, and 15.

### D-015 — The Phase 0 net uses two collider-aligned sloped segments

- Date: 2026-07-26
- Status: Accepted

The simplified net is built from two shallow box segments meeting at court
centre. Each half rises linearly from `0.8636 m` at centre to `0.9144 m` at its
sideline. The visual mesh and collision geometry are the same primitives.

Rationale: a single uniform-height box is inexpensive but does not implement
both accepted canonical net heights. Two segments preserve simple, stable box
colliders while representing the regulation height change closely.

Evidence: EditMode verifies the derived average height and slope; PlayMode
verifies two child colliders under one stable net identity, net clearance, and
continued flight after a net contact.

Trade-offs: the net bottom inherits the shallow segment rotation and can extend
about 2.5 cm below the court at an outer corner. The court occludes that region,
and only the top collision surface is behaviorally relevant in Phase 0.

Affected roadmap/spec sections: environment specification sections 3, 9, 13,
14, and 15.

### D-016 — Freeze the passing Phase 0 contract as env-v0

- Date: 2026-07-26
- Status: Accepted

The trainer-independent contract at verified source commit
`b84125dbd2742d17fdd706ab79515069e8683f7e` is frozen as `env-v0`. Phase 0 is
closed, its evidence remains versioned with the project, and later behavioral
or breaking changes follow the change-control rules in the environment
specification.

Evidence: a source-exact clean checkout, using a package/import cache warmed by
the preceding clean-clone gate, passed 27 EditMode tests, 16 normal PlayMode
tests, and the exact 10,000-episode soak. All 10,000 episodes terminated with
zero invalid numeric states, zero unclassified terminations, and zero state
leaks. The roadmap milestone records the commands, hashes, terminal counts, and
artifact paths.

Trade-offs: this freeze covers the documented Apple M1 Pro/OSXEditor
reproducibility envelope and event-equivalent replay tolerances. It does not
claim bit-identical PhysX trajectories across arbitrary Unity versions,
hardware, or operating systems. The simplified paddle, two-segment net, and
single-exchange scenario scope remain deliberate `env-v0` limits.

Migration and compatibility: Phase 1 adapters must consume `env-v0` without
adding trainer dependencies to the core or simulation assemblies. Phase 1
training is permitted by the roadmap but is not part of this decision or the
Phase 0 release.

Affected roadmap/spec sections: Phase 0 exit criteria, milestone record,
environment specification sections 14–16, and development verification.

### D-017 — Freeze the Phase 1A evaluation protocol before training

- Date: 2026-07-26
- Status: Accepted; phase scheduling and future protocol use superseded by D-020

Phase 1 is divided into Phase 1A evaluation/training readiness and Phase 1B
learned returns. Phase 1A freezes disjoint seed partitions, a four-stage
curriculum, a 37-value numeric observation encoding, the existing six-value
action contract, a scalar reward mapping, metric definitions, and zero/intercept
baselines before a trainer is installed.

Evidence: contract tests verify disjoint partitions and assembly direction;
PlayMode runs both baselines through `env-v0`. The committed held-out gate uses
1,000 manifests in seeds `4000000`–`4000999`.

Trade-offs: the protocol adds explicit upward velocity to the inbound launch
manifests. Unmodified easy/default `env-v0` launches can strike the net before
reaching the paddle, so they are valid environment cases but poor first-control
curricula. The override is manifest-recorded and does not change `env-v0`.

Migration and compatibility: Phase 1B uses `phase1a-protocol-v0`. Any change to
its seeds, stages, encoding, actions, reward weights, metrics, or thresholds
requires a new decision and protocol version.

Affected roadmap/spec sections: Phase 1, Phase 1A specification, architecture,
and development verification.

### D-018 — Target ML-Agents 4.0 without installing it in Phase 1A

- Date: 2026-07-26
- Status: Accepted; installation schedule superseded by D-020

The first trainer adapter targets `com.unity.ml-agents@4.0.3`, the exact package
reported by the Unity 6 package registry during Phase 1A. Upstream Release 23
documents the compatible release line as Unity package 4.0, ML-Agents Python
1.1.0, and Python 3.10.12. The adapter and Python/PyTorch environment are
deferred to Phase 1B and must first pass an exact-version handshake smoke.

Evidence: live package-registry inspection in Unity 6000.5.5f1 and the current
official ML-Agents release and installation documentation.

Trade-offs: this avoids consuming scarce system-volume storage before the
environment is ready and avoids treating the machine's Python 3.14 installation
as supported. It postpones proof that Unity package 4.0.3 and Python package
1.1.0 interoperate on this machine.

Migration and compatibility: trainer types belong in a new adapter assembly.
`Picklebot.Core`, `Picklebot.Simulation`, and `Picklebot.Evaluation` remain free
of ML-Agents references. A custom Python low-level adapter remains a permitted
fallback if the smoke exposes a blocker.

Affected roadmap/spec sections: Phase 1A and 1B, Phase 1A specification,
architecture, and development setup.

### D-019 — Close Phase 1A on source-exact baseline evidence

- Date: 2026-07-26
- Status: Accepted; next-phase scheduling superseded by D-020

`phase1a-protocol-v0` with hash `4ae0928d344f1c3c` is frozen at implementation
commit `48963c26d761b423e2ca124f11c576cd6880eea0`. Phase 1A is complete and
Phase 1B may begin with trainer installation, adapter integration, and a bounded
learning smoke.

Evidence: a clean checkout passed the existing 27 EditMode and 16 normal
PlayMode Phase 0 tests, plus 12 Phase 1A EditMode tests, 3 normal Phase 1A
PlayMode tests, and the exact Phase 1A evidence test. Both baselines completed
all 1,000 held-out episodes without invalid or unclassified termination. The
readiness run completed 20,000 real actions at 4,439 actions per second and
2,093 managed bytes per action in the Unity Editor.

Trade-offs: the heuristic contacts every held-out launch but produces a legal
return in only 33.4% and exits the playable volume in 66.6%. It has no legal
return in the fast launch bucket. This weakness is deliberately committed as
the Phase 1B comparison target, not tuned away after seeing held-out results.
Editor throughput and allocation do not predict trainer-connected player
performance, which Phase 1B must measure separately.

Migration and compatibility: Phase 1B must retain the frozen held-out suite and
must not use it for learning, model selection, early stopping, or reward tuning.
Learned-policy claims must name their trainer configuration, training seeds,
checkpoint, source commit, and this protocol hash.

Affected roadmap/spec sections: Phase 1A close gate, milestone record, Phase 1B
entry, and README milestone.

### D-020 — Insert pickleball physics calibration before training

- Date: 2026-07-26
- Status: Accepted
- Supersedes: the phase-label and scheduling portions of D-017, D-018, and
  D-019

Decision:

Phase 1B is a measured pickleball physics calibration gate that converts
`env-v0` into `env-v1`. The previously planned trainer installation, adapter
integration, and first learned return move to Phase 1C. Phase 1B includes no
reinforcement-learning optimization.

Evidence:

A repository audit found regulation-scale court and ball geometry, stable
120 Hz collision handling, and deterministic tests, but it also found generic
Unity material restitution, linear damping instead of a measured aerodynamic
model, a rectangular paddle envelope larger than the selected legal
representative, a net collider ending at the court sidelines, and no empirical
drop, flight, spin, acrylic-court, or paddle-contact calibration. Current USA
Pickleball equipment standards define measurable ball-drop, ball-dimension,
paddle-size, and PBCoR constraints, while measured trajectory research supports
quadratic drag and spin-dependent lift.

Trade-offs:

Training starts later, and calibrated behavior may invalidate the numerical
meaning of the frozen `env-v0` baselines. The inserted gate requires reference
data, fitting, new tests, source-exact evidence, and a new evaluation protocol.
It avoids spending compute learning exploits of visibly stable but
uncalibrated physics.

Migration and compatibility:

`env-v0`, `phase1a-protocol-v0`, and all Phase 0/1A evidence remain immutable.
Phase 1B uses physical calibration fixtures and dedicated calibration seeds; it
does not tune against the old held-out reward result. The passing simulator is
frozen as `env-v1`. Phase 1C must use a new `env-v1`-dependent protocol, update
observation scales where required, and allocate untouched final-evaluation
seeds before training. The technical trainer target in D-018 remains accepted;
only its scheduled phase changes.

Affected roadmap/spec sections: Phase 1 ordering, Phase 1A direction note,
Phase 1B physics calibration specification, Phase 1C entry, architecture,
development setup, README milestone, and milestone history.

### D-021 — Adopt a bounded practical paddle-spin surrogate before training

- Date: 2026-07-27
- Status: Accepted

Decision:

Before Phase 1C, `env-v1` applies a deterministic residual-slip model at
controlled-paddle contact. Unity remains authoritative for normal restitution.
The project model transfers configured tangential surface slip into ball
translation and rotation, with a `0.02 m/s` deadband, `3 m/s` tangential-delta
cap, `35 rad/s` contact-spin-delta cap, and `80 rad/s` total ball-spin cap.
Phase 1C receives a dedicated 37-value encoder using the same `80 rad/s` spin
scale and rejecting observations not stamped `env-v1`.

Evidence:

The previous paddle fixture recorded incoming and outgoing angular velocity but
accepted zero angular change. Source-exact tests now cover nonzero transfer,
odd symmetry, finite extreme slip, deadband behavior, caps, oblique fixture
response, and equal-and-opposite brush actions through the real environment
step/contact path.

Trade-offs:

The model is useful for learning approximate topspin, backspin, and sidespin,
but it does not model face compliance, dwell time, texture, edge response,
hand/arm inertia, or a particular commercial paddle. Its initial transfer
fractions are conservative engineering priors pending measured paddle-contact
traces. Because every parameter is included in the configuration hash, later
fitting intentionally changes the environment identity and invalidates older
source-exact calibration evidence.

### D-022 — Add a presentation-only Physics Museum before training

- Date: 2026-07-27
- Status: Accepted

Decision:

Before Phase 1C trainer integration, the project maintains an interactive
Physics Museum with six fixed stations: ball drop/rebound, comparative spin
flight, court bounce, paddle brush/spin transfer, net clearance/contact, and a
free-hit regulation court. The museum runs the real `env-v1` environment and
committed calibration fixtures. All input, camera, telemetry, trajectory, and
visual-marker code lives in a separate `Picklebot.Museum` assembly.

Evidence:

Protocol tests freeze the six stations, requests, spin variants, and bounded Mac
input mapping. PlayMode tests exercise every station through `env-v1`, verify
control state does not change the simulator configuration, and retain all three
spin-comparison trajectories. Direct Editor inspection remains part of the
museum verification.

Trade-offs:

The museum adds presentation code and a human judgment step, but it makes scale,
flight, spin, bounce, paddle, and net failures visible before compute is spent.
Feel remains subjective, so museum approval cannot replace measured fixtures,
tolerances, regression tests, or source-exact Phase 1B evidence.

Migration and compatibility:

The museum depends on `Picklebot.Core` and `Picklebot.Simulation`; neither
authoritative assembly may depend on the museum. Physics changes continue
through simulator versioning and calibration change control, never by tuning
museum visuals or controls.

Affected roadmap/spec sections: Phase 1B-to-1C interlude, development setup,
physics museum guide, and simulator architecture.

### D-023 — Authorize a provisional learned-return diagnostic probe

- Date: 2026-07-27
- Status: Accepted
- Supersedes: only the no-training scheduling language in D-020 and the
  Phase 1B specification; all Phase 1B empirical gates remain active

Decision:

Begin `phase1c0-learning-probe-v0` against the current
`provisional-unfitted` `env-v1` implementation before Phase 1B closes. Install
the live-verified ML-Agents compatible line
(`com.unity.ml-agents@4.0.3`, PyPI `mlagents==1.1.0`) in a separate trainer
adapter and isolated Python `3.10.12` Conda environment. On Apple Silicon,
install the Python package's accepted `grpcio==1.48.2` dependency from Conda's
native `osx-arm64` build. Train only on Phase 1C training seeds, select and
promote only with Phase 1C validation seeds, and preserve the Phase 1C
final-evaluation range untouched.

The probe's finish line is a neural checkpoint, with no scripted action
override, visibly controlling the kinematic paddle in Unity and recording
contacts and legal returns across varied unseen validation launches. A
successful probe proves the learning and replay path and supplies behavior for
human physics feedback. It does not close Phase 1B or Phase 1C.

Evidence:

The Physics Museum gives the current simulator an acceptable human feel-check,
while the remaining Phase 1B blockers require empirical datasets not presently
available. The project already owns an `env-v1`-rejecting 37-value observation
encoder, disjoint Phase 1C seed ranges, versioned curriculum stages, and named
reward features. On 2026-07-27, the live Unity registry returned
`com.unity.ml-agents@4.0.3`. Its installed changelog identifies the Unity
6.3–6.5 `GetEntityId` fix, package metadata requires Unity 6000.0, and its
Academy reports communicator `1.5.0`. PyPI `mlagents==1.1.0` requires Python
`3.10.1` through `3.10.12` and `grpcio` through `1.48.2`; Conda's defaults
channel supplies that exact gRPC version as a native `osx-arm64` package. The
Git `release_23_tag` was rejected as the installation source because it builds
with development version metadata (`1.2.0.dev0`) rather than the required
published version.

Trade-offs:

Training now can reveal reward exploits, unreachable actions, poor
observations, or implausible physics sooner, but any physics change can alter
the task enough to invalidate the learned checkpoint. Therefore Phase 1C0
artifacts are diagnostic and disposable, the run is locally bounded, and no
result may be promoted into final Phase 1C evidence. The local machine had
approximately `29 GiB` free at authorization time, so the probe avoids cloning
the full upstream repository and caps retained generated artifacts.

Migration and compatibility:

Historical `env-v0`, Phase 1A, and D-020 evidence remain unchanged. Phase 1A's
then-premature `4.0.3` selection remains historical; D-023 independently
reverifies and authorizes that now-published registry version.
Core, Simulation, and Evaluation retain no ML-Agents references. The adapter,
training scene, YAML configuration, model replay, and provisional evidence
follow [PHASE1C0_LEARNING_PROBE_SPEC.md](PHASE1C0_LEARNING_PROBE_SPEC.md).

Affected roadmap/spec sections: Phase 1B scheduling, Phase 1C entry, architecture,
development setup, Phase 1B status, and the Phase 1C0 probe specification.

### D-024 — Continue the real museum ball after the terminal episode record

- Date: 2026-08-29
- Status: Accepted

Decision:

The Physics Museum drop and court-bounce stations continue the visible ball
from the environment's terminal floor-contact state to the first rebound apex.
The continuation uses the same Rigidbody, collider, Unity physics material,
aerodynamic force model, gravity, and spin decay. It does not create a duplicate
presentation ball or use a separate trajectory integrator. The recorded
`env-v1` observation, event sequence, terminal reason, and training contract
remain unchanged while the museum continues the real ball for inspection.

Evidence:

The environment classifies the first landing and enters `Terminal` after Unity
resolves the contact. The previous museum stopped at that frame. It displayed a
cyan apex marker but did not show the rebound motion that the station name asked
the user to inspect. Focused tests prove that the same real ball rises to a
finite apex while the episode record remains terminal.

Trade-offs:

The post-terminal Rigidbody position is museum state and must not be used as a
new training observation or calibration measurement. The museum labels the
continuation clearly and keeps the independent fixture marker and values visible
for comparison.

Migration and compatibility:

No Core, Simulation, environment-contract, reward, seed, or trainer behavior
changes. Existing Phase 0, Phase 1A, Phase 1B, and Phase 1C0 evidence remains
valid.

Affected roadmap/spec sections: Physics Museum interaction and verification.

### D-025 — Build a separate learned 3D ping-pong rally prototype

- Date: 2026-09-06
- Status: Accepted by the user's active project goal

Decision:

Build a playable two-paddle prototype with simplified table-tennis bounce and
point rules. Both paddles use trained neural actions. The initial milestone is
ten consecutive legal returns on at least three validation launch seeds.
This user-directed work can progress while the pickleball empirical calibration
gates remain open. It does not close those gates or change their evidence.

Implementation choice:

Use local behavioral cloning of offline ballistic stroke examples for the
first model. Share that trained policy between the two player coordinate
frames. Use a separate Unity physics scene with explicitly provisional elastic
materials. Permit scripted serves and resets, but no hidden analytical paddle
controller or ball-velocity correction during rallies. Retain source and model
hashes and compare against stationary paddles on the same validation serves.

Trade-offs:

This creates the requested visible AI rally quickly on the laptop. It is not
training from scratch through reinforcement learning, a regulation sports
simulation, competitive strategy, or a calibrated pickleball result. Refer to
[AI_RALLY.md](AI_RALLY.md) for physics limits, controls, training, and verification.

Affected roadmap/spec sections: the near-term project focus is this separate
prototype. Existing Phase 1B and Phase 1C final-evaluation evidence is preserved.

### D-026 — Compete for points with smaller paddles and energy loss

- Date: 2026-09-06
- Status: Accepted by the user's request
- Supersedes: D-025 as the default visible prototype; retains its evidence

Decision:

Change the default demo from centre-directed cooperative returns to competing
paddles. Reduce paddle faces from 0.40 by 0.40 metres to 0.18 by 0.20 metres.
Use court restitution 0.86, paddle restitution 0.90, and quadratic air drag.
Limit paddle travel to 2 metres per second. Train a goal-conditioned stroke
model locally. Freeze that model, then train a shot-selection policy with PPO
from real Unity terminal point rewards. Use a centre-directed opponent and
shared-policy self-play. Do not reward rally length.

Trade-offs:

The model can choose five landing targets. It does not yet control continuous
shot pace, recovery position, spin, or a humanoid. The physics still needs
empirical calibration. This is not a regulation table-tennis or pickleball
simulation. Training uses the laptop and requires no cloud service.

Migration and compatibility:

Retain the old cooperative scene as `CooperativeRallyV1.unity`. Use the new
competition component in `AIRally.unity`. Keep the older model, runtime,
validation reports, and existing pickleball work unchanged. Competition uses
training seeds below 840000 and a separate validation partition starting at
840000. A 30-second simulation cap awards no point and gives zero reward.

Affected roadmap/spec sections: current prototype focus, architecture, demo
controls, physics settings, training, and validation. See
[COMPETITIVE_MATCH.md](COMPETITIVE_MATCH.md).

### D-027 — Inspect full-size pickleball before further training

- Date: 2026-09-06
- Status: Accepted by the user's request
- Supersedes: D-026 as the current focus; preserves its runtime and evidence

Decision:

Use an outdoor 40-hole ball on an acrylic court as the provisional reference.
Reuse existing full-size geometry and V1 physical models in a separate
inspection scene. Add bounded XYZ paddle motion, three-axis rotation, player
ground markers, and visible drop, angled-bounce, flat-contact, brush-contact,
serve, and granite-reference presets. Let physics continue after contacts and
rule faults. Export trajectories and contacts for comparison with measurements.
Do not start more training during this refinement step.

Evidence and trade-offs:

Court dimensions, ball size, and net-height targets use the existing sourced
geometry. Acrylic rebound, air drag, friction, spin transfer, and motor limits
remain provisional. A simulated rebound is not empirical validation. The
ground-disc kitchen state is not full human footwork. The serve preset starts
after a scripted strike; it does not validate the serving action. The contact
presets use labelled fixed strokes, not a trained controller.

Migration and compatibility:

`PickleballInspection.unity` is a separate manual inspection scene. Keep
`AIRally.unity`, `CooperativeRallyV1.unity`, their models, and earlier physics
calibration evidence unchanged. Do not claim that this inspection contract
freezes `env-v1` or closes Phase 1B.

Affected roadmap/spec sections: README current focus, architecture, roadmap,
and [PICKLEBALL_INSPECTION.md](PICKLEBALL_INSPECTION.md).

### D-028 — Train provisional full-size competitive shot choice

- Date: 2026-09-06
- Status: Accepted scope: the user requests a trainable game with two competing AIs
- Supersedes: D-027's pause on further prototype training only

Decision:

Create a separate full-size match on the unchanged inspection physics. Start
with independent shot-selection policies and terminal win/loss rewards. Use
explicit scripted contact assistance as the initial implementation choice.
Keep this assistance labelled. Do not claim learned end-to-end paddle control.
Use separate training and validation seed partitions and retain physical
contact reports. Preserve the old table-scale scenes and trained models.

Trade-offs:

This produces a visible training experiment before empirical calibration is
complete. It does not certify ball behaviour or replace the measured Phase 1B
gate. The small shot policy learns target choice, not human footwork, swing
mechanics, or complete pickleball strategy. A learned contact controller is
a separate subsequent stage.

Affected documents: README, architecture, roadmap, and
[PICKLEBALL_MATCH.md](PICKLEBALL_MATCH.md).

### D-029 — Develop full-body doubles in five stages

- Date: 2026-09-06
- Status: Accepted scope. The user asked for a persistent goal and implementation.
- Supersedes: None. Preserve the earlier scenes and evidence.

Decision:

Build a separate full-size doubles scene. Add match rules, articulated bodies,
bounded paddle contact, trained contact corrections, and competitive team play.
Use standard side-out scoring to 11, with a two-point lead. Use the 2026 USA
Pickleball rulebook for the implemented physical rules.

Use procedural kinematic bodies and analytic arm and leg inverse kinematics.
One constrained hand pose controls both the paddle and the visible arm. Keep
scripted interception separate from learned contact corrections and shot choice.
Topspin and slice must result from paddle motion at contact. Do not assign a
desired ball trajectory or spin after a shot.

Evidence and limits:

The first contact trials exposed body interference and incorrect spin labels.
Keep failed reports. A legal landing does not prove the requested spin skill.
Use separate training, validation and interactive seed ranges. Do not award a
point when a training rally reaches its time limit.

The outdoor ball and acrylic contact profile remains provisional. Procedural
body control is not learned human balance. Purchased character assets and paid
compute are not part of the approved work.

Track acceptance in [DOUBLES_PROGRESS.md](DOUBLES_PROGRESS.md).

## Decision proposal template

Copy this section to the end of the file:

```text
### D-xxx — Short decision title

- Date: YYYY-MM-DD
- Status: Proposed | Accepted | Rejected
- Supersedes: D-xxx (omit when not applicable)

Decision:

Evidence:

Trade-offs:

Migration and compatibility:

Affected roadmap/spec sections:
```

### D-030 — Prepare Windows environment and migrate editor tooling to Unity CLI

- Date: 2026-09-07
- Status: Accepted; CLI connectivity and actor inference parity verified. Training portability remains open.

The user authorized destination setup and requested migration from the earlier
CoplayDev MCP setup to the official Unity CLI. Use Pixi for a project-local,
locked Windows environment preserving Python 3.10.12, NumPy 1.23.5 and
PyTorch 2.1.2. Preserve the pinned Editor and the original baseline evidence.
CLI connectivity, response compatibility, source identity and model parity
must be established before claiming the transfer ready for training.
CoplayDev removal follows successful CLI verification and requires a separate
record of the package-only baseline deviation, not replacement baseline hashes.
This decision does not authorize model promotion or alter simulation behavior.
See WINDOWS_SETUP.md for commands and migration gates.

Migration evidence (2026-09-08 local): CLI beta.8 rejected Pipeline 0.5.0-exp.1
for command execution, requiring at least 0.6.0-exp.1. That exact package update
and CoplayDev removal now compile and support live eval through the original
Python wrapper. All 156 EditMode tests pass after correcting an obsolete
ML-Agents version assertion. Saved actor inference passes 32 cases. The two
package-file baseline deviations are recorded separately in
config/windows-tooling-migration.json; the original manifest remains immutable.
The Windows Python/C# source-hash discrepancy is unresolved, so this is tooling
readiness, not authorization or readiness for a new training run.

### D-031 � Portable source identity with preserved checkpoint provenance

- Date: 2026-09-08
- Status: Accepted and verified on Windows.

The user asked to fix Windows source-hash compatibility. Python and C# now
normalize repository-relative paths to forward slashes, sort using ordinal
UTF-16 ordering, and normalize source-text CRLF/CR to LF before hashing UTF-8.
Tests folders and the existing presenter exclusions are applied consistently.
Contact, player and team source hashes agree across the two languages.
Artifact byte hashes remain byte-exact and do not normalize line endings.

The hashing code is itself covered by source identity; changing it legitimately
produces a new source revision. No old model sourceHash is overwritten, no
historical report is relabelled, and no stale-source rejection is disabled.
The existing allowHistoricalCandidate path remains explicit and records both
actorTrainingSourceHash and the current sourceHash. Strict legacy evaluation
continues to reject checkpoints trained against a different source revision.
Fresh training, promotion, and new acceptance evidence are outside this fix.

config/windows-source-migration.json records the original commit, original
player identity, new contact/player/team identities, exact implementation
hashes, three baseline source-file changes and 82 preserved artifact hashes.
It builds on the immutable D-030 package migration record. source-check verifies
58 unchanged baseline files plus the three exact source and two exact package
changes; original baseline and package migration checks intentionally remain
strict historical checks. Original source reconstructed from Git, using the
canonical path rules, reproduces the transferred actor's original identity.

Verification: 300 Python tests and 158 Unity EditMode tests pass. Regression
cases cover path separators, enumeration order, case-sensitive sorting,
newline/BOM handling, test exclusions, and detection of real source changes.
Live Unity/Python contact, player and team hashes match. Saved actor inference
passes all 32 cases with maximum error 0.000003814697265625. Evidence is under
artifacts/windows-source-migration and artifacts/windows-hash-*. Original
checkpoints and evidence were checked byte-for-byte against Git.

### D-032 � Continue 2v2 goal with independent shared-weight players and staged controls

- Date: 2026-09-08
- Status: Accepted direction; implementation in progress.

The user explicitly requested a persistent goal for a workable 2v2 game. They
confirmed independent players sharing policy weights, and asked to improve
controls while setting up the movement/jump/energy systems needed for simulation.
The earlier pending controller choice is resolved at this scope level.
Implement the new control behavior in a versioned experimental path, retaining
the existing baseline. Do not silently change V1 action/observation dimensions,
checkpoint metadata, or the frozen final protocol. Shared weights do not permit
sharing player decisions or centrally assigning the hitter.

PLAYER_CONTROLS_V2.md defines the staged contract, present kernel/lab limits,
Windows measurements and remaining collision/paddle/learning integration.
Nine kernel tests pass. The prototype is not a trained or physically calibrated
human controller, and it does not complete the independent-player goal.


D-032 implementation evidence update (2026-09-08): the experimental lab now
resolves four motor proposals together using swept horizontal disc contacts.
Equal-mass inelastic response and safety-enclosure walls are explicit prototype
assumptions, not empirical human contact calibration or pickleball court lines.
Collision velocity changes are reported separately from controlled acceleration.
No V1 physics or acceptance limits changed. All 176 EditMode tests pass; 18 cover
V2 controls/contacts. Body/feet/paddle, rules and learning integration remain open.


D-032 body-pose implementation update (2026-09-08): the experimental contact
world now owns articulated foot/leg/shoulder poses with planted stance feet,
bounded airborne repositioning and explicit unsupported-foot state. Rotated shoe
support is exercised against the unchanged DoublesRules kitchen and late-volley
momentum behavior. All 184 EditMode tests pass (26 V2 control tests). The lab is
still untrained, and ball/paddle/match integration and calibration remain open.


## D-033 - Opt-in control integration with existing doubles physics

- Date: 2026-09-08
- Status: Implemented adapter; game/policy integration remains in progress.

To carry D-032 controls into the actual 2v2 physics, add PlayerBody.ApplyExternalFrame
and PlayerControlMatch. The new adapter drives existing colliders, articulated
meshes and physical paddles from a single contact/body/paddle trial. Default V1
controllers and saved scene assets remain on their original path. Running both
root motors is rejected. Real physical paddle contact is verified in PlayMode.

This explicitly changes shared body source identity. Preserve the pre-adapter
working source archive and all original models/manifests; never rewrite older
checkpoint training hashes. config/player-controls-v2-integration.json records
the exact two affected baseline-scope files, new experimental source inventory
and current identities. player-controls-verify.py checks archived baseline bytes,
82 historical artifacts, exact current scope and live Unity/Python agreement.
D-031 source-check remains historical and intentionally rejects later changes.

Paddle requests are body-local, speed/acceleration/reach/rotation bounded and
atomic with root motion. Infeasible trials are exposed; no hidden final hand
projection or central ball planner is introduced. The adapter currently takes
four supplied command pairs; it is not yet an accepted policy or full-game loop.


## D-034 - Explicit independent-player V2 decision contract

- Date: 2026-09-08
- Status: Interface and physical probe verified; learned gameplay incomplete.

Implement a separate 96-value observation and 15-value direct action contract.
Preserve the identifiable V1 54-value prefix without changing the V1 actor loader.
Do not relabel V1 weights or map categorical shot logits silently into physical
hand controls. Four policy instances may share learned parameters while keeping
their own decisions, memory and random streams. Capture all observations before
inference; retain 12-tick decisions and six-tick latency. Expose the player's own
existing kitchen eligibility and volley-momentum flags through read-only getters.

The V2 physics match can now attach four policies and execute delayed decisions.
The shared-weight integration probe is untrained and is not game-strength or
checkpoint-transfer evidence. 196 EditMode tests and four targeted physics tests
pass. A test-only ambiguous Random reference was corrected; the earlier 188-test
run used old assemblies and is not evidence for D-034. Current build and schema
dimensions were explicitly confirmed before the accepted run.

config/player-controls-v2-decisions.json and player-decisions-verify.py preserve
D-033/D-031 evidence and record current exact scope/identity. The new shared
source change is two rule-state getters; no rule transition behavior changes.
Serving/full-game progression, policy learning and all acceptance gates remain.


## D-035 - Physical serve/reset and complete-game mechanics

- Date: 2026-09-08
- Status: Targeted mechanics tests pass; learned gameplay/acceptance incomplete.

Add disclosed drop-serve and dead-ball reset skills around the independent V2
decision loop. They operate through real bounded body/paddle commands and retain
all collisions, service-foot checks and late volley-momentum resolution. Applied
action observations report actual commands, including assistance. Failure is
terminal; no silent retries or slowed simulation count as successful play.

Diagnostic failures exposed a forearm in the striking plane. The experimental
elbow pole now follows the back of the paddle face, retaining fixed arm lengths
and colliders. Preferred paddle braking reserve has a counted radial recovery
mode; all hard speed/acceleration/reach/rotation/relative-speed limits remain.
The previous adapter source and all failed probes remain available as evidence.

Game mechanics are tested using untrained hold policies. A complete winning
score in that fixture is not learned policy strength or acceptance. The existing
scene assets/default V1 path remain unchanged. Current exact identity/evidence is
recorded by player-controls-v2-game.json and player-game-verify.py; previous
migration/decision records and model hashes are not overwritten.

The user has been asked to clarify learned action scope before costly training:
movement/posture plus shot intent executed by a bounded independent swing, or
direct learned paddle trajectories. Both use the same physical command boundary.

## D-036 - Explicit historical actor intent bridge

The working training assumption is movement/posture plus shot intent, pending
user steering. Four LegacyActorIntentPolicyV2 instances share the unchanged V1
model weights while retaining independent inference traces and RNG streams.
Only the frozen 54-value observation prefix enters that network. Current heading
rotates its movement request into body coordinates. This is explicitly a V1
compatibility bridge, not a model trained on the 96-value V2 observation.

PlayerShotIntentV2 is captured with the movement action and applied after the
same six-tick latency. Each seat owns a separate PlayerIntentSwingV2 contact plan.
The swing planner requests paddle motion and never chooses locomotion or the
hitter. The legacy bridge explicitly requests sprinting and permits automatic
crouch for a planned stroke. New policies can retain their own posture. Physical
speed, acceleration, reach, energy, contacts and support constraints still apply.
Contact planning currently uses neutral residuals and the historical reach
prediction assumptions; the checkpoint's contact-model integration is unfinished.

All 200 EditMode and 162 PlayMode tests pass. Fixed and sampled checkpoint
inference match the original actor over 64 observations each, including random
stream consumption and movement coordinate transforms. Timing tests ensure
mutable policy state cannot change an already queued shot. These are contract
and regression tests, not proof of playable transferred behavior.

The first actual four-checkpoint diagnostic failed at physics step 675: player 2
had no feasible paddle transition. The entire trial was rejected. The preserved
report is artifacts/player-controls-v2/intent-probe-01.json, using only interactive
seed 1300000 and exact actor SHA 61c59e110797290c46b30b91a9fa2d0d3665e92a40f3c998bf2e24ed168edc06.
No game score had been awarded. Do not present this as a playable V2 model.

NEXT: capture the failing motor state, add a reproducible coupled shoulder/paddle
fixture, and improve feasible control execution without increasing physical
limits. Then finish contact-model and trainer/protocol integration and expose
the V2 mode through the original presentation. Training, agent-strength gates,
final evaluation and promotion remain incomplete. Original scene assets remain
unchanged; IndependentPlayers is the selected scene.

Current checks: intent-check / intent-check-unity. D-035 game-check is now a
strict historical snapshot. Current source and test records are
config/player-controls-v2-intent.json and player-controls-v2-intent-tests.json.
The failed first PlayMode run (one CLI timeout log) and its successful clean rerun
are both retained. All 82 historical artifacts and prior records remain intact.

## Bounded wrist recovery (D-037, 2026-09-08)

The exact step-675 failure was reproduced twice. The paddle had angular velocity
(-11.7105, 2.5425, -0.6324) rad/s immediately before the ready target demanded a
wrist stop. Losing the grip's rotational velocity made the 6 m/s shoulder-relative
hand-speed constraint incompatible with the linear acceleration bound for the
orientations previously considered. It was a restricted candidate search, not
proof that every physical wrist orientation was infeasible.

PlayerPaddleControl now tries ten bounded continuations of the previous wrist
rotation after its existing twenty candidates fail. Every candidate retains the
same 12 m/s speed, 100 m/s2 acceleration, 0.62 m reach, 12 rad/s rotation and 6 m/s
relative hand-speed checks. No position projection or relaxed limit was added.
WristRecoverySteps counts this path. The 80 rad/s2 decrement spaces recovery
candidates; it is not a globally imposed angular-acceleration limit. The failed
state is now an exact regression fixture, including all hard constraints and
position integration. Failed trials expose a diagnostic snapshot without
advancing physics. On successful JSON reports, failure/status is authoritative;
Unity may serialize a null snapshot as a zero-valued object.

All 201 EditMode and 162 PlayMode tests pass. The unchanged fixed-inference V1
checkpoint now completes 6,000 steps without controller failure and a separate
full 11-0 game in 11,484 physics steps. All eleven rallies contain only the serve
and one return: five out faults and six wrong-side faults. This resolves a
controller failure; it does not establish good rallies, balanced participation,
competitive 2v2, model acceptance, or trained V2 behavior. Both probes use only
interactive seed 1300000. Full-game evidence: intent-probe-05-full-game.json.

The matching historical contact residual file is still present at
Assets/Picklebot/Doubles/Models/contact.json. Its normalized SHA256 is
6698221451858f044e26a28c58a39447d391c4f1aba58a68f11370926df9cba4, matching the actor.
NEXT: integrate those residuals explicitly, diagnose actual return trajectories,
and finish trainer/protocol and original-scene presentation integration. The
current bridge still uses neutral residuals, disclosed serve/reset assistance,
compatibility sprint and automatic crouch. No new model was trained or promoted.

D-036 source is preserved in artifacts/player-controls-v2/d036-source.zip and
verified against its manifest. Current checks: wrist-check / wrist-check-unity;
prior stage checks remain historical. D-037 source and tests are recorded in
config/player-controls-v2-wrist.json and player-controls-v2-wrist-tests.json.

## Snapshot before hierarchical control (2026-09-11)

Preserve the current ML-Agents player system before implementing strategy and execution policies. The latest critic-key comparison completed without passing its improvement screen; no candidate was promoted. Current capabilities, limitations and the proposed two-policy direction are recorded in [CURRENT_STATE.md](CURRENT_STATE.md). Demo clips are historical recordings with explicit checkpoint identities. The prior long README is preserved in the archive. Source, scenes, ONNX models, five full checkpoints and compact research evidence are included; generated environments, builds and raw rollouts remain local.

### D-038 — Move new training work to mjlab with a paddle-holding G1

- Date: 2026-10-02
- Status: Accepted (user-directed); stage gates in [MJLAB_PIVOT.md](MJLAB_PIVOT.md) are still open
- Supersedes: D-001 for new work. The Unity/ML-Agents system remains the frozen reference under D-001.

Decision: New learning work moves to mjlab: MuJoCo Warp GPU-parallel physics, its Isaac Lab-style task API, and rsl_rl PPO. It runs in WSL2 Ubuntu on the local RTX 4070. The player is mjlab's bundled Unitree G1 with a rigid pickleball paddle fixed to the right wrist. There is no grip or finger model and no scaling or limb edits. A body-less driven paddle rig exists only as a physics test fixture. Code lives in `mjlab/` (package `picklebot_mj`) on branch `feat/mjlab-pivot`. Unity code, scenes, models and evidence are kept unchanged.

Evidence: The 24M-step execution-v1 run (randomized-scale-24m) saturated narrow legality but did not establish target following. Unity CPU physics on 8 cores gives roughly 1,000 policy steps/s (right-acquisition run: ~1.05M steps in 1,007 s). Comparable humanoid and racket-sport work trains with thousands of GPU environments and 10^8–10^9 samples (mjlab G1 velocity: 4096 envs, [512,256,128] ELU actor/critic). Asymmetric critics, LayerNorm/residual networks and teacher→student distillation are native to that tooling but need trainer patches in ML-Agents 1.x. The literature summary is in the 2026-10-02 session notes; the per-project numbers will be rechecked against sources when they are used.

Trade-offs: Unity-specific rules, feeds, curricula and evaluation code must be reimplemented in Python. Ball aerodynamics and fast paddle contacts under MuJoCo soft contact are unvalidated (Stage 1 gate). A balancing humanoid is harder than the previous constrained body. The G1 (~1.3 m) may limit reach and swing speed (Stage 2 measurement). mjlab is Linux-first, so it runs under WSL2. Comparisons with Unity results are qualitative only, because physics and bodies differ.

Migration and compatibility: Nothing is deleted. Seed discipline carries over: training, development and final ranges are disjoint, and final seeds stay unused until a frozen acceptance candidate exists. So do per-skill reporting, fixed-endpoint selection and no automatic promotion. D-006 remains respected: G1 locomotion uses mjlab's established velocity-tracking recipe as the base, rather than a new locomotion research program. Stage 0 must show at least 10× the Unity throughput before Stage 1 proceeds.

Affected roadmap/spec sections: ROADMAP.md and CURRENT_STATE.md gain an mjlab track when Stage 0 completes. The HIERARCHICAL_CONTROL.md goals carry over conceptually; the 136-observation contract does not.
