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

### D-039 — Simulate the ball with an analytic GPU contact model

- Date: 2026-10-02
- Status: Accepted (user-directed, option A of the Stage 1 bounce finding)
- Amends: D-038 (ball contact physics no longer uses native MuJoCo contacts)

Decision: The ball's flight and its contacts with the court, net, posts and paddle are integrated in batched torch on the GPU by project code. The code sub-steps within each MuJoCo step, uses swept collision tests, and applies an explicit impulse model for normal restitution, Coulomb friction and spin. MuJoCo still simulates the robot at its normal timestep. The paddle pose and velocity are read from MuJoCo each step. The equal and opposite impulse is returned to the paddle body through `xfrc_applied`. Ball contact with any other robot body is detected and treated as a rules event, not a calibrated bounce. The ball is shown in MuJoCo as a non-colliding body driven by the analytic state.

Evidence: `mjlab/results/stage1-bounce.md`. With native soft contacts, rebound is set by the impact phase relative to the timestep: COR 0.10–2.88 at dt 1–2 ms over drop heights 1.95–2.05 m, and still ±0.05 at 0.1 ms. A 12 m/s ball tunnels through the net at 5 ms. MuJoCo has no velocity-level restitution coefficient.

Trade-offs: More project-owned physics code to validate. The ball does not take part in MuJoCo's constraint solver. The paddle coupling is a one-step impulse, not a simultaneous solve; with the paddle about 10× the ball mass this is a small approximation. This matches the Unity reference's use of contact surrogates.

Migration and compatibility: `court.add_ball_contacts` remains as a documented, invalid baseline and is not used in tasks. The aerodynamic model and its RK4 reference (`ball.py`) carry over unchanged. Acceptance remains the official drop band (provisional for the acrylic court), now required at every drop height and impact phase, plus no energy gain and PBCoR ≤ 0.43 for the paddle surrogate.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 1 steps.

### D-040 — Accept Stage 4 with deviations; footwork in the executor, positioning in a strategy layer

- Date: 2026-10-05
- Status: Accepted (user-directed)
- Amends: D-038 (mjlab roadmap stages after Stage 4)

Decision: The Stage 4 gate result (`mjlab/results/stage4-gate.md`) is accepted with its documented deviations. `aim-all-c01/model_7600` misses three family thresholds by under 1 point (wide forehand 84.6 % and backhand 84.4 % vs 85 %; high 69.2 % vs 70 %) and passes aiming, retention and the other seven families. It is the accepted Stage 4 checkpoint. The roadmap is restructured around a two-level hierarchy:
- **The execution policy (executor)** owns footwork: stepping to the ball, adjustment steps and recovering to a commanded court spot. It takes commands for a landing target, a recovery spot and later a shot type.
- **A slower strategy policy** owns court positioning and shot choice from the game context (serve and return, partner and opponent positions, score). It issues those commands and is trained by self-play once the executor is robust.

New stage order:
- Stage 5: footwork;
- Stage 6: robustness and teacher → student distillation;
- Stage 7: two-robot rallies with a scripted strategy;
- Stage 8: learned strategy with self-play;
- Stage 9: serves and 2v2.

Evidence: Contact is 86–90 % in every family from a fixed stance and has stayed in that band since run A3, while legality given contact is about 96 % on lateral feeds and aiming works (A/B gain +0.533 [0.528, 0.539]). The remaining misses are untouched balls, which more standing-only training is unlikely to remove, and match play needs footwork regardless.

Trade-offs: Stage 4's thresholds are not strictly met. The Stage 5 gate re-tests the Stage 4 families (from random starts) at the same 85 % bar, plus contact ≥ 92 %. Releasing the stance risks balance regressions, so falls per robot episode become a gate metric.

Migration and compatibility: The old Stage 5 (robustness of the standing result) is folded into the new Stage 6 for the moving executor. Nothing is deleted. Seed discipline and fixed-endpoint selection are unchanged.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 4 gate, Stages 5–9, Open questions.

### D-041 — Teach footwork with movement drills before hitting on the move

- Date: 2026-10-06
- Status: Accepted (user-directed)
- Amends: D-040 (Stage 5 method; the gate thresholds are unchanged)

Decision: Stage 5 footwork is taught through three drills in the same single executor network, each with its own gate:
1. **Move to a spot without a ball.** Balanced directions and distances up to 3 m, arrival in a ready stance with the paddle up. mjlab's own velocity-tracking and foot-quality rewards serve as the walking teacher, by pointing the twist command toward the spot instead of holding it at zero.
2. **Move and shadow-swing** at a virtual contact point and time, with the feet set before contact and recovery afterwards.
3. **Real balls with a near-to-far reach curriculum.**

Every drill run rehearses the Stage 4 hitting drills (25 % of robot episodes) and maintains earlier drills. If walking does not emerge in Drill 1, the fallback is a separately trained mjlab G1 walking policy used as a leg teacher (user approval first). The Stage 5 gate thresholds from D-040 are unchanged and move to the end of Drill 3.

Evidence:
- Runs F1 and F2 (`mjlab/results/stage5-run-f1.md`, `stage5-run-f2.md`) trained hitting with free feet directly. The robot learned one movement, a lean and step to its right: reach_forehand ~74 % legal, while reach_backhand, reach_short and reach_deep stayed at 0 % contact.
- Recovery error stayed at ~0.8 m median.
- Widening the distance shaping to 1.5 m (F2) changed none of this.
- The policy lineage starts from a standing policy, and PPO exploration around it does not find multi-step gaits.
- The user's view, drawn from human coaching practice, is that repositioning is trained as its own skill before it is combined with the swing.
- Comparable work trains locomotion or skills separately before combining them, e.g. DeepMind's humanoid soccer pretrains get-up and kicking skills.

Trade-offs:
- More runs: about 3–5 two-hour runs instead of one or two.
- New task machinery: a spot sequence, a ready-stance reward, shadow-swing targets and a reach curriculum.
- The twist command, removed as a stand-still incentive in D-040's stance release, returns as a movement teacher. It is active only in move episodes, and remains zero (with free feet) in hitting rehearsal.
- Interference between drills is controlled by rehearsal and per-drill retention checks.

Migration and compatibility:
- F1 and F2 artifacts and reports stay as they are. `footwork-f02/model_12000` is the parent of Drill 1.
- The Stage 5 steps already completed (motion audit, reach families, recovery command, stance release, F1, F2) remain valid infrastructure.
- Seed discipline and fixed-endpoint selection are unchanged.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5 (drill plan), Open questions.

### D-042 — Specialist teachers distilled into one larger student instead of one policy trading skills

- Date: 2026-10-06
- Status: Accepted (user-directed)
- Amends: D-041 (Stage 5 method after Drill 1; the gate thresholds are unchanged)

Decision: Stage 5 skills are no longer traded off inside one 512-256-128 policy. Instead:
- each skill is trained by a specialist teacher with only its own rewards, until its own gate is met or it plateaus:
  - a walking teacher on move-to-spot only;
  - a hitting teacher on hitting only, with aiming and recovery;
- the teachers are distilled with DAgger into one larger student (1024-512-256 with LayerNorm), routed by episode type;
- the student is then fine-tuned with RL on the combined drills (shadow-swing, then real balls with a near-to-far reach curriculum) under a KL pull-back toward the routed teacher.

Teacher training may chain fixed-endpoint 2-hour runs (loop rule 9), up to 4 per teacher. The Drill 1 gate becomes informational; it names the walking-teacher parent.

Evidence:
- **Drill 1** (`stage5-run-d1.md`, `stage5-run-d1b.md`) trained walking and hitting in one policy with rehearsal. Each change moved the balance rather than raising both:
  - D1: 91 % arrival with retention −2.0 overall, but −6.7 to −7.6 on three families;
  - D1b: oversampling the right side cost forward movement (arrival 69 %) and retention (−6.7 overall);
  - D1c: more hitting rehearsal raised the training hitting reward and lowered arrivals.
- **Causes:**
  - one small network and a shared value function serving rewards of very different scales (dense walking terms versus sparse hitting events);
  - 2-hour runs that end before the skills settle.
- **Established practice** for many skills in one controller: train specialists, then distil (policy distillation; DeepMind humanoid soccer). Imitation is supervised learning and does not have RL's reward tug-of-war. Larger, normalised networks help once training is stable (e.g. SimBa, BRO).
- The user wants skills to saturate rather than settle at a shared ~80 %, and prefers a capable teacher distilled into a student.

Trade-offs:
- New code: distillation with DAgger and teacher routing, and a KL-regularised fine-tune.
- Longer teacher training through chained runs.
- The student starts from imitation, so the combined behaviour (the move-to-swing transition) is only learned in the fine-tunes.
- A same-size student is also distilled as a control, so the effect of capacity is measured, not assumed.

Migration and compatibility:
- Drill tasks, reach feeds, the recovery command and eval scripts are reused as the teachers' training and evaluation tasks.
- D1, D1b and D1c stay on record.
- Seed discipline and fixed-endpoint selection are unchanged. Choosing a teacher parent between completed endpoints on dev seeds is documented as such.
- Stage 6's teacher → student step reuses the same distillation code.

Affected roadmap/spec sections: MJLAB_PIVOT.md loop rule 9, Stage 5 (teachers and student).

### D-043 — Exclude feeds cut off by the episode time limit from evaluation rates

- Date: 2026-10-06
- Status: Accepted (measurement correction found by the loop; reported to the user for review)
- Amends: the evaluation definitions behind Stage 4–5 gates (thresholds unchanged)

Decision: In feeding-machine evaluations, a feed still in progress when a robot episode resets for its time limit (not tallied, not ended by a fall) is **censored**. It is excluded from contact, legal-return and placement rates and reported as `censored_feeds`. Feeds ended by a fall still count. Gate comparisons against earlier checkpoints re-evaluate those checkpoints with the corrected metric on the same feeds.

Evidence: `mjlab/results/eval-censoring-fix.md`. On the same feeds, 20.3 % (hitting teacher) and 10.8 % (`model_7600`) of all feeds were untouched balls cut off at the time limit and counted as misses. Excluding them, contact is 99.7 % and 99.6 %: the "85–90 % contact ceiling" reported since Stage 4 run A3 was mostly this artefact.

Trade-offs: Results before 2026-10-06 are not comparable to corrected ones without re-evaluation. Earlier gate outcomes (Stage 4 gate, F1/F2, Drill 1 retention) may differ under the corrected metric. They are not re-litigated automatically.

Migration and compatibility: Historical JSON and reports are kept unchanged. Training is unaffected (rewards never used these tallies). Test `test_feed_cut_off_by_time_limit_is_censored_not_missed`.

Affected roadmap/spec sections: MJLAB_PIVOT.md evaluation of all remaining gates.

### D-044 — Adopt the recommended robot-learning upgrades: motion priors, adaptive curriculum, domain randomisation, multi-task fixes

- Date: 2026-10-06
- Status: Accepted (user-directed: "opt for what you would recommend")
- Amends: D-042 (Stage 5 student fine-tunes), D-038 (roadmap: new Stage 5B; Stage 6 additions)

Decision:
1. **Human motion priors (new Stage 5B).**
   - Survey open tennis and pickleball motion data (tennis approved), retarget it to the paddle-holding G1, and train a tracking teacher on mjlab's G1 motion-tracking task.
   - Then add an AMP-style style reward, or tracking-teacher distillation, to the executor.
   - Gate: Stage 5 performance kept, style clearly improved.
2. **Adaptive curriculum sampler** for all later training (already planned, `a25c6c8`).
3. **Domain randomisation and latency** in the teachers before the Stage 6 deployable student: mass and inertia, friction, motor strength, sensor noise and delay. The student inherits robustness.
4. **Multi-task fixes** in the student fine-tunes if interference appears: separate critic heads per skill and per-task value normalisation (PopArt-style).
5. **Evaluation discipline stays as is** (fixed seeds, held-out final seeds, intervals, fixed endpoints, metric audits).
6. **Skill-latent hierarchies** (ASE/CALM) are noted as an option for the Stage 8 System 1/System 2 interface, not scheduled.

Downloads of datasets or tools need the user's approval of name, source, size and licence (loop rule 10).

Evidence:
- The Stage 5 experience: hand-tuned oversampling (D1b, HT-b) is what adaptive curricula automate; shared-policy interference is what multi-task normalisation addresses.
- Current humanoid practice gets natural motion from human data: DeepMimic, AMP/ASE, PHC, OmniH2O, BeyondMimic (whose method mjlab's tracking task follows), and broadcast-video tennis work.
- Sim-to-real practice depends on domain randomisation and privileged teacher → student (RMA and later work).
- The user asked for industry-standard methods rather than hand-built ones.

Trade-offs:
- Motion data needs licensing checks, retargeting, and a paddle that may not match the human racket.
- AMP rewards can conflict with task rewards. Gated by the "no task regression" rule.
- Domain randomisation lowers peak simulated performance in exchange for robustness.
- More stages before matches.

Migration and compatibility: Stage 5 proceeds as planned (D-042) and is not interrupted. Stage 5B follows the Stage 5 gate, and Stage 6 follows Stage 5B. All earlier artefacts are kept.

Affected roadmap/spec sections: MJLAB_PIVOT.md loop rule 10, Stage 5 fine-tunes, new Stage 5B, Stage 6 (domain randomisation step), Stage 8 note.

### D-045 — Accept Drill 2 with deviations; diagnose from videos, then the Drill 3 reach curriculum

- Date: 2026-10-07
- Status: Accepted (user-directed: "do 2 and 1 together")
- Amends: D-041/D-042 (Stage 5 Drill 2 gate)

Decision: Drill 2 is accepted with documented deviations.

The student (`student-swing-d2c/model_3900`):
- swings accurately on 11 of 14 families;
- keeps walking and hitting intact;
- does not reach the reach backhand / short / deep balls;
- misses the feet-set, recovery and fall thresholds.

Next steps:
- Videos of the reach swings are reviewed first, and anything they show feeds the Drill 3 design.
- Drill 3 (real balls with a near-to-far reach curriculum) starts from `student-swing-d2c/model_3900`.
- The deviations are re-checked at the unchanged Stage 5 gate.

Evidence: `mjlab/results/stage5-run-sd2.md`. Across S-D2, S-D2b (interception hint) and S-D2c (reward for following the hint), the reach families stayed at 0.36–0.39 / 0.79–0.81 / 0.91–0.94 m median distance with no forgetting elsewhere. A near-to-far curriculum is the standard remedy for targets too far to discover by exploration.

Trade-offs: Drill 2's thresholds are not met. The risk moves to Drill 3 and the Stage 5 gate. If Drill 3 also stalls on these families, Stage 5B motion priors and the feet-set/recovery thresholds are the next options.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5 (Drill 2 result, S-D2c video step, Drill 3).

### D-046 — Provisional Stage 5 student; start Stage 5B motion priors (downloads approved)

- Date: 2026-10-07
- Status: Accepted (user: "sure lets do what you recommend", replying to option 1 of `mjlab/results/stage5-gate.md`)
- Amends: D-042/D-045 (Stage 5 gate), D-044 (Stage 5B parent)

Decision: the Stage 5 gate is not met. The S-D3b student (`2026-10-07_11-51-32_student-drill3-d3b/model_6500`) becomes the **provisional** Stage 5 student, with documented deviations:
- reach backhand / short / deep legal 22 / 2 / 2 %;
- falls 5.7-6.9 % per robot episode;
- median recovery 1.03 m;
- fixed-start retention low -6.1 and fast -7.3 points vs `model_7600`.

Stage 5B starts now with it as the parent. The Stage 5 gate thresholds are unchanged and are re-checked after Stage 5B. Rule 8 follow-up 2 was not run.

Approved downloads (rule 10):
- **Tennis-MoCap BVH** (github.com/jdpulgarin/Tennis-MoCap, ~209 MB, CC BY-SA 3.0).
- **LAFAN1 retargeted to G1, `g1/*.csv`** (Unitree's Hugging Face dataset, ~90 MB). Derived from CC BY-NC-ND 4.0, so non-commercial research only and never redistributed: kept under the git-ignored `mjlab/artifacts/motion/` and never committed or pushed. The user approved this licence condition by accepting the recommendation.
- **GMR retargeter** (github.com/YanjieZe/GMR, ~276 MB + Python dependencies, MIT), installed into the project venv only.

Phase B data (GVHMR, SMPL-X) and AdaPT are not approved.

Evidence: S-D3 and S-D3b (`stage5-run-sd3.md`, `stage5-gate.md`):
- A gentler curriculum start and a 1.3-1.7x sampling share did not move the reach families.
- Contact on deep balls is about 2 %.
- The videos show lunging, tipping back and no balanced crossover. This is a movement-quality gap, which Stage 5B targets.

Trade-offs: Stage 5B proceeds from a parent that misses part of the Stage 5 gate. Its "Stage 5 gate still met" gate becomes "no regression beyond 5 points vs the provisional student, and the Stage 5 gate re-checked".

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5 gate, Open questions, Stage 5B.

### D-047 — LAFAN1 footwork data: retarget from the official Ubisoft release (non-commercial)

- Date: 2026-10-08
- Status: Accepted (user: "yes go with option 1, its non-commercial")
- Amends: D-046 (approved download list)

Decision: Unitree's retargeted LAFAN1 dataset on Hugging Face no longer exists (the API's 401 was a not-found). Instead:
- Download the original LAFAN1 BVH release, `lafan1.zip` (github.com/ubisoft/ubisoft-laforge-animation-dataset, 144 MB, CC BY-NC-ND 4.0).
- Retarget it to the paddle G1 with GMR's LAFAN1 -> G1 mapping and this project's pipeline: capsule self-collision avoidance, warm start, grounding, quality filter.
- Use it as general footwork style data (walks, runs, sidesteps, direction changes) for the tracking teacher and the style prior.

The user confirmed the project is non-commercial research. LAFAN1 and everything derived from it (retargeted clips, motion files) stay in the git-ignored `mjlab/artifacts/motion/` and are never committed or pushed. A policy trained partly on it carries the same non-commercial restriction.

Rejected:
- the third-party Hugging Face re-upload of Unitree's files (redistribution of a no-redistribution dataset);
- ember-lab-berkeley/LAFAN-G1 (its licence claim conflicts with the source, and it is in a different format).

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B (footwork data step).

### D-048 — Tracking teacher gate scored per stroke

- Date: 2026-10-08
- Status: Accepted (user: "go with option 1, score per stroke")
- Amends: the tracking-teacher gate definition set on 2026-10-08 (MJLAB_PIVOT.md Stage 5B)

Decision: the tracking gate's success is measured on **single-stroke segments**, not on whole takes. The thresholds are unchanged:
- success >= 90 % overall and >= 80 % for every stroke type;
- root-relative MPKPE <= 6 cm;
- falls <= 1 %.

A segment is one swing, cut from each take around a right-hand speed peak (`scripts/motion/tracking_eval.py --per-stroke`). The robot starts on the reference at the segment start; the segment succeeds if it reaches the segment end with no termination.

The candidate evaluated is the one named before the per-stroke numbers existed: tracking-06-wide/model_21300. The other fixed endpoints are reported for information only.

Evidence (`mjlab/results/stage5b-tracking.md`):
- 81 of 90 Tennis-MoCap clips are 20-30 s takes of about 10-15 repeated strokes, and whole-take success requires all of them without a single termination.
- The best whole-take success (58.9 %) is about 96 % per stroke. A 90 % whole-take bar is close to a 99.3 % per-stroke requirement, far stricter than the per-clip success of BeyondMimic-style trackers on short clips, which the gate was meant to resemble.

Trade-offs:
- Per-stroke scoring does not test recovery across a long rally of strokes; the task-level gates (Stage 5/6) cover that.
- Segment boundaries depend on a peak-detection rule, which is fixed and documented here before evaluation.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B tracking-teacher gate, Open questions.

### D-049 — Accept the wide tracking teacher with a tracking-error deviation

- Date: 2026-10-08
- Status: Accepted (user: "go with option 1, accept it")
- Amends: D-048 (tracking-teacher gate)

Decision: `tracking-06-wide/model_21300` (task `Picklebot-Tracking-Tennis-Big-G1`, 1024-512-256) is the **provisional tracking teacher** for Stage 5B.

Per-stroke (D-048, dev seed 4,200,306, 697 segments):
- success 90.5 %, every stroke type 82.7-94.7 %;
- falls 0.

Documented deviation: root-relative MPKPE is 7.8 cm against the 6 cm bound.

Rationale: the teacher is used as a style source (style prior or distillation) for the executor, where stroke completion matters more than a couple of centimetres of pose error. Part of the error is reference motion the G1 cannot reach (ankle roll, waist pitch and shoulder yaw limits; the retargeting already leaves 2.4-3.4 cm).

The bound is unchanged and is reported again if the teacher is retrained.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B (tracking teacher), Open questions.

### D-050 — Hierarchical motion-prior executor (low-level human-motion controller steered by a task policy)

- Date: 2026-10-09
- Status: Accepted (user: "The most latest one is in option three, right? ... Let's go for it then.")
- Amends: D-044 (Stage 5B style prior), D-049 (use of the tracking teacher)

Decision: the executor's natural motion comes from a **hierarchical motion prior** instead of a style reward on the existing executor (AMP failed after three runs; `mjlab/results/stage5b-style.md`):
- A **low-level controller** built from the accepted tracking teacher (`tracking-06-wide/model_21300`) and the retargeted human clips (Tennis-MoCap strokes + LAFAN1 footwork). It can only produce human-like motion.
- A **task-level policy** steers it to move, set up and return balls.

This is the direction of current work on natural physics-based humanoids and racket sports (PULSE, MaskedMimic, Vid2Player3D and recent G1 tennis work).

The exact variant (e.g. a PULSE-style latent skill space distilled from the tracker, or a MaskedMimic-style sparse-goal controller) is chosen from a short literature and library survey (`mjlab/results/stage5b-hierarchy-survey.md`) before anything is built. Stage 5B is rewritten into concrete steps with gates.

**Unchanged:**
- The Stage 5 task gates and the "no task regression beyond 5 points" rule, now measured against S-D3-style-c (the task-best executor: Stage 4 families 95.6-98.2 %, retention within 5 points everywhere).
- The style score (median nearest-clip pose distance, target at least 20 % below the S-D3b baseline of 4.82).

S-D3-style-c is kept as the fallback executor if the hierarchy cannot match its task performance.

Trade-offs:
- A larger redesign, with new training stages (controller distillation, then the task policy).
- Task performance may at first fall below the flat executor's.
- Ball-contact precision depends on how finely the low-level controller can be steered.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B (rewritten), Open questions.

### D-051 — Drop LAFAN1 jumps and mixed actions from the teacher's motion set; bounded continuation of H0

- Date: 2026-10-09
- Status: Accepted (user: "go with option 1, drop those clips")
- Amends: D-047 (LAFAN1 tracking set), the H0 gate scope (MJLAB_PIVOT.md Stage 5B)

Decision:
- **Smaller set.** `jumps1_*` and `multipleActions1_*` (7 clips) leave the LAFAN1 tracking set. 17 clips remain (70.7 min): walk, run, sprint, fight-and-sports. These clips are not pickleball footwork and caused most falls (7.7 % and 13.8 % of their windows).
- **Same gate on the new set.** H0's thresholds are unchanged, now on the reduced LAFAN1 set: tennis >= 87.5 % overall and >= 77 % per stroke type, LAFAN1 >= 85 %, falls <= 1 %.
- **Bounded continuation.** Up to 2 more chained <= 2 h runs from tracking-12-huge/model_38300 on the new set, each evaluated on a fresh dev seed.
- **Provisional acceptance, fixed now.** If the gate is still missed, the last fixed endpoint is accepted as the provisional H0 teacher for H1 only if every item is within 3 points of its threshold:
  - tennis >= 84.5 % overall;
  - every stroke type >= 74 %;
  - LAFAN1 >= 82 %;
  - falls <= 2 %.
  Otherwise the loop stops for the user.

Evidence: `mjlab/results/stage5b-h0-tracking-12-huge.json`. Without these two clip types, the same model's LAFAN1 score is about 77 % on the reported per-type numbers.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H0, Open questions.

### D-052 — Long-training block for the H0 teacher

- Date: 2026-10-09
- Status: Accepted (user: "yes, switch to the long-training block")
- Amends: D-051 (replaces its "up to 2 more runs"), loop rule 9's 4-run chain limit for this teacher only

Decision: the H0 teacher (2048-1024-512, task `Picklebot-Tracking-TennisLafan2-Huge-G1`) trains as a long block. The rules are fixed before the block:
- **Length:** up to **10 chained <= 2 h runs** from tracking-12-huge/model_38300, tracking-13-huge being run 1, about 20 GPU-hours.
- **Batch size:** after run 1, a short smoke at 8192 envs. If it fits in memory and gives >= 1.3x the samples per second of 4096 envs, runs 2+ use 8192 envs. Otherwise they stay at 4096. Both results are recorded.
- **Evaluation:** every 2 runs, a per-stroke + LAFAN1 evaluation on a fresh dev seed (`tracking_eval.py --per-stroke`). The main metric is the mean of tennis overall and LAFAN1 overall success.
- **Learning-rate decay:** the final 2 runs use a fixed, lower learning rate (1e-4, schedule fixed; the default is adaptive from 1e-3). They are runs 9-10, or the 2 runs right after the first evaluation that gains < 1 point on the main metric. After the decay runs the block ends.
- **Gates:** the H0 gate (D-051) is unchanged. If it is missed at the end, D-051's provisional-acceptance rule applies (every item within 3 points). Otherwise the loop stops for the user.

Evidence: the user's question whether training length, rather than method, is the limit. The tracker has had about 3.8e9 samples (about 21 GPU-hours); published trackers use several times more compute. The learning curves show diminishing returns but no hard plateau.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H0.

### D-053 — H2 becomes a diagnostic; H3 with the prior-imitation latent controller

- Date: 2026-10-11
- Status: Accepted (user: "go with option 1, move on to H3")
- Amends: D-050 (Stage 5B H2 gate), MJLAB_PIVOT.md H3

Decision:
- **H2 is a diagnostic, not a gate.** Its results stay recorded (`mjlab/results/stage5b-h2.md`). Prior-only rollouts fall 37-46 % (no noise / noise) from mid-motion starts. The controller is instead judged by H3 controllability and the H4 style score.
- **Controller:** `latent-07/latent_10651`. It passes H1 (93.2 % tennis, 88.8 % LAFAN1) and was trained with the prior imitation loss.
- **H3 action term:**
  - z = mu_p + lambda * sigma_p * tanh(a_lat), with **lambda = 0.5** (smaller than the 1.0 first planned, because the prior is loose);
  - plus a bounded right-wrist residual of +-0.3 rad;
  - the prior and decoder are frozen.
- **H3 gate, fixed before training:**
  - a paddle target (0.3-0.7 m from the right shoulder) and a root target (within 1 m), both resampled every 2 s;
  - a target counts as reached if it comes within 10 cm at any time in its 2 s window;
  - >= 80 % of paddle targets and >= 80 % of root targets reached after one <= 2 h run;
  - falls <= 5 % per episode;
  - dev-seed evaluation.

Evidence: H2 runs and diagnostics (`stage5b-h2.md`). In LATENT the high level is trained to choose z within the prior's barrier and never samples the prior at random.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H2, H3, Open questions.

### D-054 — CalTennis video pilot: GVHMR downloads approved

- Date: 2026-10-11
- Status: Accepted (user: "if you need my approval bro you got it. lets go!")
- Amends: rule 10 approvals for Stage 5B (video pilot, `mjlab/results/stage5b-video-pilot-survey.md`)

Decision: download and install, all into git-ignored locations:
- the GVHMR code (github.com/zju3dv/GVHMR, non-commercial research licence);
- its own Python venv (`~/envs/gvhmr`: torch 2.3 + cu121 and the GVHMR requirements; ultralytics is AGPL-3.0, used locally);
- pytorch3d 0.7.6;
- the GVHMR checkpoints (gvhmr, hmr2, vitpose-h, yolov8x; about 5.6 GB). The official Google Drive comes first; the Hugging Face mirror `camenduru/GVHMR` is the fallback if Drive refuses an unattended download.

The SMPL-X v1.1 and SMPL v1.1.0 body models need the user's own registration (MPI non-commercial, single-user) and are supplied by the user.

Pilot data: the CalTennis side views E_01 and W_01 of session 09_18_2025_16_15_court5 (CC BY-NC 4.0, already downloaded; players about 180-240 px tall, full body visible). The project is non-commercial (D-047). Video-derived motion and anything trained on it stay local.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B (new video-pilot step).

### D-055 — Bounded H3 extension

- Date: 2026-10-11
- Status: Accepted (user: "go with option 1, do the H3 extension")
- Amends: D-053 (H3), rule 8 for H3 only

Decision: up to **3 more <= 2 h runs** for H3, one change each, each warm-started from the previous fixed endpoint, starting from reach-03-l1/model_17500 (lambda 1.0). Order fixed now:
- **E1:** add a root *progress* reward: pelvis velocity toward the root target, clamped to [-1, 1] m/s, weight 1.0. The 1.0 m distance kernel is kept.
- **E2:** add a latent action penalty, L2 on a_lat, weight 0.01, to keep z nearer the prior mean and reduce falls.
- **E3:** more training of the E2 setup.

Rules:
- Each run is evaluated deterministically on a fresh dev seed.
- **The gate is unchanged:** >= 80 % paddle and >= 80 % root targets within 10 cm, falls <= 5 %. Reach rates at 25 cm are also reported, for information only. The user did not change the tolerance.
- The extension stops early if a run meets the gate.
- If none does, the loop stops for the user.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H3, Open questions.

### D-056 — H3 accepted; budgeted push to the Stage 5B checkpoint

- Date: 2026-10-12
- Status: Accepted (user: the Stage 5B loop prompt of 2026-10-12)
- Amends: D-053/D-055 (H3), rule 8 for H4 and the Stage 5B gate

Decision:
1. **H3 is accepted as sufficient** (option 1). Corrected evaluation of reach-06/model_34700: paddle 100 %, falls 0.1 %, root 59.4 % (10 cm). H4 uses the reach-06/model_34700 controller and action space: latent-07/latent_10651, lambda 1.0, wrist residual 0.3. V1 (the video pilot, which needs the user's SMPL files) and H5 are skipped.
2. **Budget:** for H4 and the Stage 5B gate, up to **15 training runs in total** replace rule 8's two follow-ups. Each run:
   - is at most 2 h;
   - has a fixed endpoint;
   - is evaluated on a fresh dev seed;
   - changes one thing, written down before launch;
   - warm-starts where sensible.

   Design changes within H4's scope (rewards, curriculum, observations, network size, distilling from the flat student, using the wrist residual) are allowed, each recorded as a decision entry with its reason. Climbing stops early if 3 runs in a row improve the main metric by less than 1 point.
3. **Targets, in order:**
   - (a) the H4 gate as written: no family's legal return more than 5 points below S-D3-style-c's; target hits and A/B gain with intervals; style score <= 3.86; side-by-side videos;
   - (b) then climb toward the original Stage 5 thresholds while holding style <= 3.86: every family including reach >= 75 % legal, A/B gain CI > 0, recovery <= 0.5 m, falls <= 1 %, retention.

   Thresholds are never loosened.
4. **End:** when the targets are met or the budget or plateau runs out, the loop:
   - renders review videos of the best fixed endpoint: a continuous Drill 3 sequence across families (side and behind views), plus a side-by-side with S-D3-style-c;
   - writes `mjlab/results/stage5b-gate.md` (pass or fail, every family);
   - commits, pushes if the stage passed, and stops for the user.
5. **Still stop and ask** before sudo or system changes, Unity or the feat/hierarchical-control checkout, deletions, downloads, any run over 2 h, or using final seeds.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B (H3, H4, gate), Open questions.

### D-057 — H4: no distillation from the flat student; return shaping instead

- Date: 2026-10-12
- Status: Accepted (loop, under the design latitude of D-056)
- Amends: Stage 5B H4 (run 2)

Context: h4-01 (fresh PPO over the latent, 1,300 iterations) reaches style 2.74 (target <= 3.86; S-D3-style-c 4.84), robot falls 0.5 % per episode and recovery 0.58 m. But it has 0 % legal returns: it touches 18 % of balls, with a mean paddle speed of 0.8 m/s at contact, and no ball crosses the net.

Considered: distilling S-D3-style-c into the H4 policy through the frozen decoder (DAgger; `scripts/distill_h4.py`, tested). It was rejected on evidence:
- **Smoke run** (60 iterations): the imitation error rose from 0.30 to about 2.0 and stayed there, while robot episodes ended more often.
- **Expressiveness floor** (`scripts/latent_reach_floor.py`, `results/stage5b-h4-latent-floor.json`). Even fitted per state on the teacher's own states, the decoder reproduces the teacher's joint actions only by saturating 70 % of the latent commands at lambda 1 (overall MSE 0.185 against action variance 2.18; right-arm residual 0.37 against variance 1.19).
- **Conclusion:** imitating the flat student pushes the executor to the edge of the human-motion space, toward the motion style we are replacing.

Decision: H4 run 2 continues PPO from h4-01/model_1300 with **one added reward**: a one-shot `return_shaping` at the first legal contact. It pays half for the outgoing ball speed toward the net (capped at 6 m/s) and half if its drag-free ballistic path clears the net. Weight 2.0/step_dt, between paddle_contact (1.0) and legal_return (5.0). It is read before legal_return, which clears the step flags. Task `Picklebot-Latent-Drill3-Shaped-G1`.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-058 — H4: lower PPO entropy, then show the stance hint on half the real-ball feeds

- Date: 2026-10-12
- Status: Accepted (loop, under the design latitude of D-056)
- Amends: Stage 5B H4 (runs 3 and 5)

1. **Run 3: entropy coefficient 0.01 -> 0.001** (`Picklebot-Latent-Drill3-Shaped-LowEnt-G1`, runs 3-4).
   - The latent action passes through tanh, so extra noise costs the policy almost nothing while the entropy bonus keeps paying for it. Action std rose 1.0 -> 1.30 over runs 1-2.
   - With the change, std fell to 0.41, and the first legal returns appeared (run 3: 0.2 %; run 4: 3.5 % no hint).
2. **Run 5: the stance hint on half the real-ball feeds** (`hit_hint_prob` 0.5; `Picklebot-Latent-Drill3-HalfHint-G1`). h4-04 returns 40.9 % legally with the hint but 3.5 % without it (contact 59 % vs 21 %). Every real-ball training feed showed the hint, so the executor follows it and never learned to read the ball itself. The flat student learned that in Stage 4, before the hint existed.
   - The hidden half must find the interception point from the ball observations.
   - The hinted half keeps the movement teaching.
   - The gate keeps its no-hint measure; the hint is a training aid only.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-059 — H4: stance hint on the forehand side ("run around the backhand")

- Date: 2026-10-12
- Status: Accepted (loop, under the design latitude of D-056)
- Amends: Stage 5B H4 (run 7), D-058

Context: h4-06 returns the nine forehand-side Stage 4 families at 66-81 % (no hint), but **backhand at 0 % with contact 0 %, even with the hint**. That is despite backhand already getting the largest adaptive feed share (12.4 %). A rendered sequence (`artifacts/videos/h4/h4-05-backhand-*`) shows the robot standing in its ready pose with the paddle on its right while the ball passes on its left. The stance hint (`stance_spot`) assumes a backhand stroke: it places the pelvis 0.4 m to the right of a ball on the left. The executor has not learned a backhand. With zero contacts the rewards give it nothing to learn from.

Decision: run 7 places every hinted stance on the forehand side (pelvis 0.5 m to the left of the predicted contact, as for forehands). This teaches the human "run around the backhand" footwork with the stroke the executor already has. Implementation: `hint_forehand_only` in the ball term; task `Picklebot-Latent-Drill3-FhHint-G1`, otherwise as run 6 (hint on 20 % of real-ball feeds).

Trade-off, left open: this does not teach a true backhand stroke. That matters most for reach_backhand (1-2.5 m to the left), where running around adds distance. If backhand stays at 0 %, a backhand-specific approach is a later decision.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-060 — H4: reward progress toward the spot the executor is shown

- Date: 2026-10-12
- Status: Accepted (loop, under the design latitude of D-056)
- Amends: Stage 5B H4 (run 8), D-059

Context: after run 7 the forehand-side families return 65-86 % (main metric 50.4 %), but three failures share one cause. **The executor has never learned to travel to a commanded spot:**
- `move_arrival` is 0 in every H4 run (h4-01..07), and the move-tracking reward fell from 0.107 to 0.054 per episode.
- Backhand stays at 0 % contact with the forehand-side hint: the hint asks for a 0.8-1.15 m sidestep that the robot never takes. Rendered: `artifacts/videos/h4/h4-07-backhand-*`.
- The reach families are at 0-15 %, and recovery worsens every run (0.375 -> 0.625 -> 0.775 -> 0.825 m).

For every forehand feed, the hinted spot is within about 0.2 m of where the robot already stands, so ignoring the spot input costs almost nothing there.

In H3 the same gap (moving the pelvis to a target through the latent) was closed by a progress reward: root reach went 10.6 -> 45.5 % in one run (D-055 E1).

Decision: run 8 adds `spot_progress`, weight 1.0: pelvis speed toward the spot input, clamped to +-1 m/s, zero within 0.1 m. It is active only when the spot is meant to be followed:
- move-drill episodes;
- ghost-swing episodes;
- hinted real-ball feeds before the hit;
- every real-ball feed after the hit (the recovery spot).

Un-hinted approaches get no spot pull, so the ball must still be read. Task `Picklebot-Latent-Drill3-Progress-G1`, otherwise as run 7.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-061 — H4: shift the episode mix from ghost swings to move-to-spot drills

- Date: 2026-10-12
- Status: Accepted (loop, under the design latitude of D-056)
- Amends: Stage 5B H4 (run 9), D-060

Context: run 8 added the spot-progress reward (D-060). The main metric held at 50.5 % (+0.1). Reach forehand rose 15.5 -> 25.1 %. But the executor still never arrives at a move-drill spot (`move_arrival` 0), the progress reward stays small (about 0.02 per episode), backhand stays at 0 % and recovery at 0.775 m. Only 15 % of episodes practise moving. The flat student learned to walk to spots in Drill 1 with 75 % move episodes.

Decision: run 9 changes the episode mix, real balls held at 60 %:
- move-to-spot 0.15 -> 0.35;
- ghost-ball swings 0.25 -> 0.05. They taught the swing early; it now exists (contact speed 4-5 m/s, 64-86 % legal on forehand-side families).

Task `Picklebot-Latent-Drill3-MoveMix-G1`, otherwise as run 8, from h4-08/model_11100.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.
