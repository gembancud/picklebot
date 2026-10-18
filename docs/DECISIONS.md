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

### D-062 — H4: privileged footwork shaping toward the hitting stance

- Date: 2026-10-12
- Status: Accepted (loop, under the design latitude of D-056)
- Amends: Stage 5B H4 (run 10)

Context: run 9 (move-heavy episode mix) lifted the main metric 50.5 -> 54.1 %, and reach forehand to 46 %. The executor now moves when the ball pulls it to the right. But it never moves left: backhand and reach backhand are 0 %, even with the forehand-side hint. It also ignores abstract spots. `scripts/move_diag.py` on h4-09 (`results/stage5b-h4-h4-09-move-diag.json`): 0 of 2,990 move-drill spots reached within 0.25 m, median closest approach 1.36 m.

The spot input is already body-relative (`recovery_obs`), so perception is not the problem. The problem is exploration: at action std 0.38 the policy never finds the walking those rewards would pay for.

Decision: run 10 adds `stance_progress`, weight 1.0: pelvis speed toward the feed's ideal hitting stance, clamped to +-1 m/s. The stance is the forehand-side stance spot computed from the predicted interception. It is active on **un-hinted** real-ball feeds before the hit; hinted feeds are already covered by spot_progress.
- **Privileged reward only:** the observations are unchanged, so the executor must still read the ball. This is standard footwork shaping.
- **Covers:** the backhand run-around and every reach family, in one term.

Task `Picklebot-Latent-Drill3-Footwork-G1`, otherwise as run 9, from h4-09/model_12400.

Considered and kept for later: pulling the executor toward the H3 reach-06 walker in move episodes (a teacher regulariser through RegPPO's hook). It is more plumbing, and the main metric needs direct progress under the plateau rule.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-063 — H4: the latent controller cannot step left or back; fall penalty for run 11

- Date: 2026-10-13
- Status: Accepted (loop, under the design latitude of D-056); finding 1 is reported to the user
- Amends: Stage 5B H4 (run 11)

1. **Finding (outside H4's scope):** the human-motion controller is directionally biased. `scripts/reach_direction_diag.py` on the H3 walker reach-06/model_34700, with the root target forced 0.8 m from the pelvis in the heading frame (dev seed 4200470, `results/stage5b-h4-reach-direction-diag.json`):

   | Direction | Within 10 cm | Within 25 cm | Median closest approach |
   |---|---:|---:|---:|
   | Forward | 91.9 % | 99.3 % | 0.03 m |
   | Right | 77.5 % | 95.7 % | 0.04 m |
   | **Left** | **22.5 %** | **41.8 %** | 0.32 m |
   | **Back** | **1.3 %** | **24.7 %** | 0.34 m |

   The tracking data is right-handed tennis plus mostly forward LAFAN1 walking. Inside the latent barrier (lambda 1, about one prior std), leftward and backward steps are rare. This explains why H4 never moves left: backhand and reach backhand stay at 0 % contact, even with the forehand-side hint (D-059) and the stance shaping (D-062). Run 10's backhand video shows the robot planted while the ball passes on its left.

   Fixing it needs a controller change outside H4's scope (D-056 fixed H4 to the reach-06 controller and action space):
   - mirrored (left-handed) and more backward/lateral motion data in the H0/H1 training;
   - a wider latent barrier;
   - a root-velocity channel beside the latent.

   This is left to the user and reported with the end-of-loop videos.
2. **Run 11: add H3's fall penalty** (-50 on a terminating fall; `Picklebot-Latent-Drill3-FallPen-G1`), from h4-10/model_13800. The drill task ends an episode on a fall but never penalised it. h4-10 falls in 6.0 % of robot episodes (target <= 1 %; H3 with the penalty: 0.1 %).

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4, Open questions; `mjlab/results/stage5b-h4.md`.

### D-064 — Stop H4 climbing after run 11; videos and gate report

- Date: 2026-10-13
- Status: Accepted (user: "go with option 1, let run 11 finish first")
- Amends: D-056 (the 15-run budget ends at run 11)

Context: H4 reaches human-like play on balls fed near the robot. With no hint, the nine forehand-side Stage 4 families return 79-90 % legally at style 2.90 (target <= 3.86; S-D3-style-c 4.84). Reach forehand is 64.5 %. The movement half of the target (backhand, the left/back reach families, recovery) is limited by the latent controller's directional bias and low speed (D-063). The 1.5 m direction test: covered within 2 s, about 1.1 m forward/right but only about 0.5 m left/back.

Decision:
- Run 11 (fall penalty) finishes and is evaluated as planned. Climbing then stops; runs 12-15 are not used.
- The candidate is the better of the h4-10 and h4-11 fixed endpoints by the main metric on their dev evaluations.
- **Final gate evaluation:** the candidate and S-D3-style-c on the same fresh dev seeds with the same script.
- **Review videos:** a continuous Drill 3 sequence across families (side and behind views), and a side-by-side with S-D3-style-c.
- **Report:** `mjlab/results/stage5b-gate.md`, pass or fail with every family reported. No push unless the stage passes.
- **For the user afterwards:** the agility test (train the H3 walker on 1-3 m targets in all directions) and the controller fixes in D-063 (mirrored or extra lateral/backward motion data, a wider latent barrier).

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4 and gate.

### D-065 — Maximise H4: GPU throughput, an adaptive curriculum, then controller fixes if needed

- Date: 2026-10-13
- Status: Accepted (user: the H4 maximisation loop prompt of 2026-10-13, after reviewing the h4-10 videos: "not really mostly impressed yet")
- Amends: D-064 (H4 continues), D-056 (budget)

Decision:
1. Finish D-064: `mjlab/results/stage5b-gate.md` from the paired gate evaluation of h4-10 and S-D3-style-c (fail, every family).
2. **GPU first.** Training used the GPU poorly: 25-50 % utilisation, 2.7 of 12 GB, 55 of 200 W during evaluation. The drill task runs at about 19k steps/s against 91k for the reach task. Benchmark H4 training at 4096 / 8192 / 16384 envs (`scripts/bench_envs.sh`) plus safe speed-ups (no system change), then train with the fastest configuration that fits.
3. **Adaptive training.** Replace the family-level feed mix with a learning-progress curriculum over continuous feed parameters (lateral offset, depth, speed, spin). Every family, backhand included, starts from easy variants that give a learning signal and widens with success. The existing family mix re-weights by failure, but backhand got 12 % of feeds and still 0 contacts, so sampling where it fails cannot help when failing gives no signal. If throughput allows, tune reward weights by population-based training instead of by hand.
4. **Escalation** if backhand or left/back movement still does not learn:
   - (a) test whether the H3 walker can put the paddle on the backhand side;
   - (b) an agility H3 walker (1-3 m targets, all directions, less time, left and back balanced) as a footwork teacher;
   - (c) retrain the motion controller (H0, then H1) with mirrored copies of the existing LAFAN1 locomotion clips (no downloads), then redo H3/H4.
5. **Budget:** up to 25 training runs, each <= 2 h with a fixed endpoint, evaluated on a fresh dev seed, one change written before launch, warm starts where sensible. Design changes are allowed with decision entries. The plateau stop (3 runs in a row < 1 point on the no-hint pooled legal return) applies to H4 runs only.
6. **Targets:** the H4 gate as written, then the original Stage 5 thresholds. Never loosened.
7. **End:** review videos of the best fixed endpoint (closer side and behind views, side-by-side with S-D3-style-c, a backhand-only clip), stage5b-gate.md updated, commit, push if the stage passed, then stop for the user.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4 and gate.

### D-066 — H4 training at 12,288 envs with fewer host syncs; learning-progress feed curriculum

- Date: 2026-10-13
- Status: Accepted (loop, under D-065)
- Amends: D-065 steps 2-3; Stage 5B H4 (run 12)

1. **Throughput** (`scripts/bench_envs.sh`, `scripts/profile_env_step.py`, `scripts/find_syncs.py`).
   - **Diagnosis:** the drill step was bound by per-step overhead, not GPU compute. Iteration time was flat from 4,096 to 8,192 envs, at 30-50 % GPU utilisation and about 55 W. The profile showed 78 % of step time in the ball term and **175 CUDA syncs per step**: a per-family GPU-boolean check in the per-feed logging loop (56), Python-scalar index assignments (about 60) and small constant tensors rebuilt on every call (about 40).
   - **Fixes, behaviour-preserving:**
     - a host-side active-family list;
     - `index_fill_` / `masked_fill_` instead of scalar index assignment (`rules._fill`);
     - per-device cached constants (`shadow_swing._const`).

     Result: 175 -> 15 syncs per step; the rest are inside mjlab.
   - **Benchmark** (steps/s, clean GPU):

     | Envs | Before | After the fixes | GPU memory |
     |---:|---:|---:|---:|
     | 4,096 | 19.3k | 23.3k | 3.9 GB |
     | 12,288 | 48.1k | **55.3k** | 7.4 GB |
     | 16,384 | 52.9k | 60.5k | 9.1 GB |

     **Training now uses 12,288 envs** (`train_run.sh` reads PICKLEBOT_ENVS): about 2.9x the samples per 2 h run, leaving memory for an evaluation to overlap the next run. 16,384 is only 9 % faster.
   - **Equivalence:** all tests pass. The single exception, test_style, passes alone but hits torch.compile's recompile limit when the whole suite runs in one process. The h4-10 no-hint evaluation on the same seed gives 58.42 % (old code), and 57.04 % / 58.37 % in two runs of the new code. GPU nondeterminism alone varies this metric by about +-1.4 points run to run, so borderline plateau decisions (around 1 point) get a repeat evaluation.
2. **Learning-progress feed curriculum** (`curriculum.LPSampler`, `feeds.LP_EASY`, ball term `lp_curriculum`; task `Picklebot-Latent-Drill3-LP-G1`).
   - **Units:** (family x 5 difficulty levels). A level s in [0, 1], jittered continuously within its bin, interpolates every feed range (lateral offset, depth, speed, height, spin) from an easy end to the full family.
   - **Easy ends:** the easy-forehand feed for the Stage 4 families. A ball almost straight at the body (lateral -0.15..0.10 m) for backhand. The full backhand range for reach backhand. The wide forehand range for reach forehand. Nearer bounces for reach short and reach deep.
   - **Priority:** learning progress plus intermediate success (10-90 %), with a floor of 0.2 of uniform. Units that never succeed no longer soak up feeds; the old (1 - success) term had given backhand 12 % of feeds at 0 contacts.
   - **Replaces:** the family-level adaptive mix and the reach curriculum. Evaluations turn it off (full families).
   - **Run 12:** h4-10's task (Footwork) with this curriculum, from h4-10/model_13800 (the best endpoint), at the new 12,288-env standing configuration. The env count is the D-065 standing throughput setting, not the run's experimental change, but it also triples the PPO batch. That confound is recorded with the result.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-067 — H4 curriculum: keep rehearsing mastered units

- Date: 2026-10-13
- Status: Accepted (loop, under D-065)
- Amends: D-066 (LPSampler scoring)

Context:
- **Run 13** (working learning-progress curriculum): main metric 74.4 %, backhand 74.5 %, 8 families passing the H4 gate bar.
- **Run 14** (more training): 74.3 %, flat. Underneath, backhand rose 74.5 -> 83.6 % and reach short 36.8 -> 57.4 %, while easy forehand fell 97.9 -> 87.3 %, backspin 93.2 -> 87.4 % and high 92.0 -> 89.3 %.

The sampler scored mastered units (success >= 90 %) like hopeless ones (OUT_OF_BAND 0.2), so feeds moved away from them and they decayed: catastrophic forgetting. The gate needs every family, so mastered skills must stay in the mix.

Video of h4-13 on backhand feeds (`artifacts/videos/h4/h4-13-backhand-*`): the robot now steps left and swings across its body to the left, with the paddle high on its left side. That is a real backhand-side stroke. Reach backhand (1-2.5 m left) stays at 0 % at every curriculum level (none above 10 % success), consistent with the controller's leftward-travel limit (D-063).

Decision: run 15 sets `lp_mastered_weight` = 1.0, so mastered units score like in-band units; hopeless units stay at 0.2. Task `Picklebot-Latent-Drill3-LP-Rehearse-G1`, from h4-14/model_17100.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-068 — H4 curriculum: rehearse mastered units only at the top level

- Date: 2026-10-13
- Status: Accepted (loop, under D-065)
- Amends: D-067

Context: run 15 (D-067, mastered units at full weight) scored **67.4 %**, down 6.9 points from run 14, with every family worse (easy forehand 70.2 %, backhand 76.0 %). Its training numbers looked better than ever: legal reward 0.88-0.93 per episode, easy forehand 0.98. With every mastered (family x level) unit at full weight, practice spread evenly over the many mastered *easy* levels, so the full-range levels the gate measures were diluted. The training reward rose because the balls were easier.

The continuation run already launched (h4-16-more, same configuration) was stopped at iteration 18,304, about 100 iterations in, once run 15's evaluation refuted the configuration. It produced no endpoint and is not counted.

Decision: run 16 rehearses mastered units at full weight **only at the top, full-range level** of each family. Mastered easy levels drop back to 0.2; in-band units keep 1.0 plus learning progress. Task `Picklebot-Latent-Drill3-LP-Top-G1`, from h4-14/model_17100 (the parent of run 15).

Plateau count after run 15: 2 (runs 14 and 15 below best + 1 point). Run 16 must reach >= 75.4 % or H4 climbing stops (D-065).

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-069 — Next stage: full-court coverage (Stage 5C)

- Date: 2026-10-13
- Status: Accepted (user: "yes, queue the full-court coverage stage next")
- Amends: roadmap order (new Stage 5C between Stage 5B and Stage 6)

Context: the H4 executor plays a baseline game.
- **Positions:** it starts and recovers within about 1.5 m of the baseline centre (about 8-10 % of its half court).
- **Moves:** feeds ask for at most about 2.5 m of travel, it never reached a move-drill spot, and it never plays near the kitchen or volleys.
- **Controller:** it covers about 1.1 m in 2 s forward or right, but only about 0.5 m left or back (D-063).

Decision: after the D-065 loop ends, **Stage 5C — full-court coverage** teaches the executor to cover the whole half court:
1. **Agile, all-direction footwork.**
   - First an agility version of the H3 walker: 1-3 m targets in all directions with less time per target, left and back balanced, measured per direction (`scripts/reach_direction_diag.py`).
   - If left and back stay slow, retrain the motion controller with mirrored copies of the existing LAFAN1 locomotion clips (H0 teacher, then H1 latent, chained; no downloads) and redo the walker.
2. **A court-wide drill.**
   - Start and recovery spots over the whole half court, including the kitchen line.
   - Feeds that pull the robot to the net (short and drop balls), push it back (lobs) and cross the full width.
   - Volley families (pre-bounce hits outside the kitchen; two-bounce and kitchen rules enforced).
   - A working move-to-spot drill.
3. **H4 trained on the court-wide drill** with the learning-progress curriculum over (family x level x court zone), warm-started from the best D-065 endpoint (on the new controller if step 1 retrains it).
4. **Gate** (proposed; the user may revise before the stage starts):
   - legal return >= 75 % for every family in every court zone;
   - move-to-spot arrival >= 90 % in every direction (0.5-3 m);
   - volleys >= 75 % legal;
   - recovery <= 0.5 m;
   - falls <= 1 %;
   - style <= 3.86;
   - review videos of full-court play.
5. **Budget:** up to 30 runs, each <= 2 h, with the D-065 discipline (fixed endpoints, fresh dev seeds, one change per run, decision entries for design changes, plateau stop on executor runs only).

Affected roadmap/spec sections: MJLAB_PIVOT.md (new Stage 5C).

### D-070 — H4 return shaping: require a net-clearance margin

- Date: 2026-10-13
- Status: Accepted (loop, under D-065)
- Amends: D-057 (`return_shaping`)

Context:
- **Run 17:** 79.7 % pooled no-hint legal, the first H4 endpoint above S-D3-style-c (78.7 %).
- **Backspin** has slid 93.2 % (run 13) -> 87.4 -> 77.8 -> 73.2 -> 72.2 %, with contact at 99.5 %, so it is return quality, not reach.
- **Backspin-only evaluation** (dev seed 4200524, `artifacts/eval/backspin-h4-1{3,7}.json`):

  | | h4-13 | h4-17 |
  |---|---:|---:|
  | wrong-side endings (ball back on its own side, i.e. into the net) | 428 | 3,017 |
  | mean net clearance | 0.415 m | 0.19 m |
  | legal | 96.4 % | 75.4 % |
  | outgoing speed | 11.4 m/s | 11.8 m/s |

  Same pace, lower path.

`return_shaping`'s net check gave full credit to any outgoing ball whose drag-free path clears the tape at all. As aiming improved (A/B gain up on every family), the policy learned to hit flat at that edge. With real drag, and spin that the actor cannot observe, backspin returns then fall into the net.

Decision: run 18 requires **0.3 m of predicted clearance** (the clearance h4-13 kept) for the net half of `return_shaping`. Task `Picklebot-Latent-Drill3-Margin-G1`, otherwise as run 17, from h4-17-more/model_19300.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-071 — H4: reward the real net clearance; style drift is whole-body (prior-likelihood penalty next)

- Date: 2026-10-14
- Status: Accepted (loop, under D-065)
- Amends: D-070

Context: run 20 scored **88.6 %** (+3.0). Reach backhand rose to 53.3 % and reach deep to 46.8 %; recovery is 0.325 m. Two problems remain:
1. **Backspin slipped again** (92.5 -> 88.8 -> 80.8 %). Backspin-only evaluation, h4-18 -> h4-20 (dev seed 4200524):
   - mean real net clearance 0.315 -> 0.208 m;
   - wrong-side (netted) endings 673 -> 2,701;
   - landing depth 3.25 -> 3.04 m, as aiming pulls returns flatter.

   The 0.3 m margin of D-070 sits on a drag- and spin-free prediction. The actor cannot observe spin, and for backspin the real flight drops below that prediction.
2. **Style is drifting toward the limit:** 3.31 -> 3.56 -> 3.69 (limit 3.86). `scripts/wrist_style_diag.py` (dev seed 4200540):
   - the wrist residual is the same in h4-13 and h4-20 (0.24 rad mean);
   - style without the right wrist still rises from 2.69 to 3.23.

   So the drift is whole-body posture (lunging), not the wrist. The latent L2 on the raw action is flat across runs (-0.25 to -0.28 per episode) and says little once tanh saturates.

Decision:
- **Run 21:** add `net_clearance`, a one-shot reward when the returned ball really crosses the net (the simulated ball, so drag and spin are included). It is graded by its clearance over the tape up to 0.3 m, weight 1.0/step_dt. Task `Picklebot-Latent-Drill3-NetReal-G1`, from h4-20/model_22200.
- **Run 22 (planned):** protect style with a prior-likelihood penalty on the latent, `(lam * tanh(a_lat))^2`, i.e. the latent's distance from the prior mean in prior-std units (as in PULSE/ASE). The current drift (+0.13 per run) should keep run 21 under 3.86.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-072 — H4: prior-likelihood latent penalty to stop the style drift

- Date: 2026-10-14
- Status: Accepted (loop, under D-065; planned in D-071)
- Amends: Stage 5B H4 (run 22)

Context: run 21 (real net-clearance reward, D-071) scored 88.1 % (-0.5 against run 20; plateau count 1).
- **Fixed:** backspin 80.8 -> 91.5 % (passes; mean real clearance 0.77 m).
- **New high:** reach backhand 67.5 %.
- **Slipped:** wide forehand 91.2 % (bar 92.5), fast 87.5 % (bar 92.6), reach forehand 82.0 % (bar 92.6).
- **Style 3.75**, against the 3.86 limit, after rising every run (3.08 -> 3.19 -> 3.31 -> 3.56 -> 3.69 -> 3.75). It is whole-body drift, not the wrist residual (D-071).

h4-21's latents average sum (lam tanh a)^2 = 7.7 of 32 per step, with 3 % of dimensions saturated.

Decision: run 22 adds `latent_prior_nll`, sum (lam * tanh(a_lat))^2, the latent's squared distance from the prior mean in prior-std units (-2 log p(z|s) up to a constant, as in PULSE/ASE). Weight -0.01, about 0.6 per episode at h4-21's spread (legal return is about 0.85 per episode). Task `Picklebot-Latent-Drill3-Prior-G1` (the run-21 task plus this term), from h4-21/model_23300.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-073 — H4: stronger prior-likelihood penalty (0.01 -> 0.05)

- Date: 2026-10-14
- Status: Accepted (loop, under D-065)
- Amends: D-072

Context: run 22 scored **91.0 %** (+2.4; plateau count reset). 13 of 14 families pass the H4 gate bar; only reach forehand misses (90.1 %, bar 92.6). Backspin is 97.1 %, reach backhand 78.3 %, recovery 0.275 m and robot falls 1.6 %.

But **style is 3.82**, only 0.04 under the 3.86 limit. The prior-likelihood penalty at 0.01 averaged only -0.10 per episode in training, and style still rose (3.75 -> 3.82).

Decision: run 23 raises the weight to -0.05, about -0.5 per episode, so style is held under the limit. The risk is losing some reach-forehand performance. Task `Picklebot-Latent-Drill3-Prior5-G1`, from h4-22/model_24400.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B H4; `mjlab/results/stage5b-h4.md`.

### D-074 — Stage 5B gate met (H4 executor h4-25b)

- Date: 2026-10-14
- Status: Accepted (loop end under D-065; the stage passes on D-056 target a)
- Amends: Stage 5B (H4 and gate)

Result (`mjlab/results/stage5b-gate.md`): paired final evaluation of `h4-25b-more/model_27700` against S-D3-style-c on fresh dev seeds 4200570-573.
- **H4 gate met:**
  - all 14 families within 5 points of S-D3-style-c or better;
  - pooled no-hint legal 93.9 % vs 78.3 %;
  - style 3.81 <= 3.86;
  - A/B gain CI above 0 on all 14 families.
- **Original Stage 5 thresholds (target b), partly met:**
  - met: Stage 4 legal and contact, A/B gain, recovery 0.275 m, reach forehand/backhand/short >= 75 %;
  - missed: reach deep 73.3 %, falls 1.68 %, retention from the old Stage 4 fixed start (fast -24, low -13, backhand -10). These carry into Stage 5C, which covers full-court footwork and start positions.

Decision: H4 and the Stage 5B gate are ticked, h4-25b/model_27700 is the Stage 5B executor, and the branch is pushed (the stage passed). Next is Stage 5C, full-court coverage (D-069).

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5B, Stage 5C.

### D-075 — Stage 5C, full-court coverage: plan and budget

- Date: 2026-10-14
- Status: Accepted (user: the Stage 5C loop prompt of 2026-10-14)
- Amends: D-069 (Stage 5C)

Decision:
1. **Starting point:** the Stage 5B executor `h4-25b-more/model_27700`. Training at 12,288 envs (PICKLEBOT_ENVS) with the learning-progress curriculum.
2. **Footwork first: an agility H3 walker.**
   - **Task:** root targets 1-3 m away in all directions, uniform angle (left and back balanced), with less time per target than H3 (1 m in 2 s). Warm-started from reach-06/model_34700.
   - **Measure** per direction with `scripts/reach_direction_diag.py` at 1.5 m and 2.5 m.
   - **"Left/back stay slow" (fixed now):** within 25 cm at 1.5 m, left or back reaches less than 75 % of the mean of right and forward, after the walker's runs (up to 3).

     If so, retrain the motion controller (H0 teacher, then H1 latent, chained) with mirrored copies of the existing LAFAN1 locomotion clips (no downloads), and redo the walker.
3. **Court-wide drill:**
   - start and recovery spots over the whole half court, including the kitchen line;
   - feeds that pull to the net, push back and cross the full width;
   - volley families (two-bounce and kitchen rules enforced);
   - a working move-to-spot drill.

   Tests for each. Then H4 is trained on it with the curriculum over family x level x court zone.
4. **Budget:** up to 30 training runs. Each run is <= 2 h, has a fixed endpoint, is evaluated on a fresh dev seed (borderline evaluations repeated; noise about +-1.4 points), changes one thing written before launch, and warm-starts where sensible. Design changes get decision entries. The plateau stop applies to executor runs only.
5. **Gate:**
   - every family in every court zone >= 75 % legal;
   - move-to-spot arrival >= 90 % in every direction (0.5-3 m);
   - volleys >= 75 % legal;
   - recovery <= 0.5 m;
   - falls <= 1 %;
   - style <= 3.86;
   - no Stage 5B drill family more than 5 points below h4-25b.

   Never loosened.
6. **End:** paired final evaluation on fresh dev seeds and close-camera full-court videos (side, behind, kitchen play, a long sequence across the court). Then `mjlab/results/stage5c-gate.md`, commit, push if passed, and stop for the user.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C.

### D-076 — Stage 5C court-wide drill design

- Date: 2026-10-14
- Status: Accepted (loop, under D-075)
- Amends: Stage 5C (drill task)

Decision, all opt-in by `court_wide` (earlier tasks unchanged): task `Picklebot-Latent-Court-G1`, built on h4-25b's task.
1. **Court zones** by the robot's pelvis x at feed time: back (x < -5.0), mid (-5.0..-3.4), front (>= -3.4, up to the kitchen line -2.13). Outcomes are tallied per zone x family (`ep_zone_family`).
2. **Start and recovery spots** anywhere from the baseline to the kitchen line (start x -6.4..-2.4, y +-2.6; recovery x -6.2..-2.4, y +-2.5).
3. **Six court families** (`feeds.COURT_FAMILIES`), relative to the pelvis:
   - drop: bounces 2-3.5 m in front;
   - lob: lands 2-3.5 m behind;
   - cross forehand and cross backhand: 2.5-4 m sideways;
   - volley forehand and volley backhand: aimed to bounce behind the robot, taken before the bounce.

   Each is fed only in the zones where `scripts/tune_court_feeds.py` measured it valid. Drop and reach short are back/mid (from the front they land beyond the net 64 % and 99 % of the time); lob and volleys are mid/front; everything else is valid everywhere (`artifacts/eval/court-feeds-v1.json`). Hint drag factors are calibrated with `artifacts/eval/hint_calib2.py`.
4. **Volleys:** fed in rally phase, so they may be taken before the bounce. The kitchen rules are now enforced from the robot's ankle positions every physics step (`rules.feet`): a volley with a foot in the kitchen, or unestablished outside it, is a kitchen fault. Approach shaping and the stance hint use the pre-bounce interception point for volleys (descending through 1.0 m, with a 9.5 % drag shortfall).
5. **Curriculum:** one learning-progress sampler per court zone, over the families valid there (family x 5 levels). Without the curriculum (evaluation), families are drawn only from those valid in each env's zone.

Tests: `tests/test_court_drill.py` (zone coverage and validity, volley rally phase, kitchen state from the feet, volley hint), plus the updated family-parametrised tests.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C.

### D-077 — Stage 5C: retrain the motion controller with mirrored LAFAN1 locomotion

- Date: 2026-10-14
- Status: Accepted (loop; D-075 criterion met)
- Amends: Stage 5C footwork step

Context: run 1 (s5c-01-agility) trained the H3 walker on 1-3 m targets in every direction for a full 2 h run. The training curve stayed flat (root reward about 0.20, mean distance about 1.22 m throughout). Per direction at 1.5 m (`results/stage5c-agility-01-dir-*.json`, dev seed 4200610):

| Direction | Within 25 cm | Distance covered in 2 s |
|---|---:|---:|
| Forward | 32 % | ~1.2 m |
| Right | 27 % | ~1.1 m |
| Left | 0.1 % | ~0.55 m |
| Back | 0 % | ~0.5 m |

At 2.5 m nothing reaches the target. These match the reach-06 baseline: harder training does not unlock leftward or backward travel. The D-075 criterion (left/back below 75 % of right/forward) is met by a wide margin. A flat run is decisive, so the two optional further walker runs are not used.

Decision: retrain the motion controller.
1. **Mirrored data:** left-right mirror the 17 LAFAN1 clips of the current set (walk, run, sprint, fight/sports; `scripts/motion/mirror_g1_csv.py`, tested). Root y and rotation are reflected; left and right joints swap, with roll and yaw negated. The result goes to `lafan-g1-mirror.npz`. No downloads.
2. **Motion set:** merge tennis-v5 + LAFAN1 + mirrored LAFAN1 into `tennis-lafan3.npz`, sampled 0.5 / 0.25 / 0.25 by source (task `Picklebot-Tracking-TennisLafan3-Huge-G1`).
3. **H0:** continue the H0 teacher (`tracking-20-decay/model_60800`) on it in chained <= 2 h runs, until the mirrored clips track like the originals and tennis stays within the H0 gate.
4. **H1:** continue the latent distillation from latent-07 on the new teacher and data. Starting from latent-07 keeps the latent space close to the one H4 was trained on, so h4-25b can be warm-started on the new controller.
5. **Agility walker:** redo it on the new controller, measured by the same per-direction criterion.

Meanwhile the court-wide executor runs (on latent-07) continue on the parts that do not need faster footwork: volleys, kitchen play and zone play.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-078 — Stage 5C: re-aim the volley feeds to waist-to-chest height

- Date: 2026-10-14
- Status: Accepted (loop)
- Amends: D-076 (volley families)

Context: run 2 (s5c-02-court, model_28400; `mjlab/results/stage5c-s5c-02-*.json`, dev seeds 4200620-623) raised the court-wide main metric from 52.0 % to 71.3 %, but both volley families scored 0 % legal in every zone. Contact was 6 % (forehand) and 0.1 % (backhand); the few contacts came after the bounce, 0.38 m high on average. The learning-progress sampler kept every volley unit at its floor weight (top-level success 0.000 for the whole run). An offline check of the D-076 feeds (`mjlab/artifacts/eval/volley_geom.py`) shows why: aimed 1.0-1.6 m behind the robot, they pass the pelvis knee-high and dipping (median 0.44-0.58 m in the mid zone). That is a hard low dig, not the waist-to-chest volley a beginner drill starts with, and well below the paddle's ready height (0.9-1.2 m).

Decision: re-aim both volley families. The aim moves to 2.6-3.0 m behind the robot, still clamped inside the baseline by `BOUNCE_AIM_MIN`, with a flatter, faster arc: start height 0.95-1.25 m, flight time 0.70-0.85 s. They now pass the pelvis at 0.7-1.2 m (mid zone 0.79-1.01, front zone 0.89-1.23, 5th-95th percentile) and 7-10.5 m/s.
- The learning-progress easy end is the same flat ball with narrower ranges, about 0.75-1.2 m.
- Lateral offsets, spin and the court zones (mid, front) are unchanged.
- The offline feed check still gives 100 % landing in and 100 % in the volley window in every zone.
- The volley stance-hint test still passes.

Run 2's volley results were measured on the old definitions and are reported as such. The next executor run (run 4) changes only this: it warm-starts from run 2's endpoint.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/picklebot_mj/feeds.py`; `mjlab/results/stage5c.md`.

### D-079 — Stage 5C: stop the H0 chain at run 3b and distil H1 from it

- Date: 2026-10-14
- Status: Accepted (loop)
- Amends: D-077 step 3

Context: the D-077 H0 gate asked for mirrored LAFAN1 >= 86.2 % (H0's LAFAN1 minus 3 points). Each checkpoint was scored on two dev seeds (`mjlab/results/stage5c-h0-*.json`):

| Checkpoint | Tennis | LAFAN1 | Mirrored LAFAN1 | Serve | Smash |
|---|---:|---:|---:|---:|---:|
| H0 (tracking-20-decay/60800), before any mirrored data (seed 4200642) | 93.9 | 90.1 | **83.4** | 89.7 | 90.8 |
| Run 3b (s5c-03b/63300) | 94.0 / 94.1 | 88.7 / 88.7 | 84.9 / 84.8 | 88.3 / 89.3 | 90.5 / 89.5 |
| Run 5 (s5c-05/65900) | 93.1 / 93.5 | 89.6 / 89.9 | 85.7 / 86.2 | 84.0 / 85.7 | 87.8 / 87.4 |

Three findings:
1. **H0 already tracked the mirrored clips at 83.4 % before training on them.** The H3 walker's missing left/back footwork is therefore not mainly a teacher problem. It comes from what the H1 latent space was distilled on: tennis plus right-handed, forward-heavy LAFAN1.
2. **Run 3b's mirrored locomotion is close to the originals.** Walk 92.7 / 93.0 against 94.6 / 94.8; run 81.4 / 81.7 against 86.7 / 84.3; sprint 78.3 / 78.7 against 80.7 / 82.4. Most of the remaining gap is the mirrored fight/sports clips (63-66 % against 75 %).
3. **Run 5 bought about 1 point of mirrored tracking at the cost of serve (-4.5) and smash (-2.5 points).** Its serve is more than 3 points below H0 on both seeds.

Decision:
- **H0 chain stopped at run 3b.** Its mirrored LAFAN1 score is 1.3 points short of the 86.2 % H0 target; this is recorded as *not met*, not reinterpreted.
- **H1 is distilled from run 3b's teacher** (s5c-03b/model_63300). Run 3b keeps every tennis stroke within 3 points of H0, and its locomotion clips, original and mirrored, track within about 3-5 points of each other.
- **What decides D-077 is the agility walker on the new controller**: left/back reach against right/forward, measured as in run 1. That test is unchanged.

H1 run (run 6), changing only the data and teacher from latent-07:
- teacher s5c-03b/model_63300, task `Picklebot-Tracking-TennisLafan3-Huge-G1`;
- init latent-07/latent_10651; latent-07's settings otherwise (KL 1e-4, prior imitation 0.5, smoothness 0.005, DAgger with student rollouts);
- fixed endpoint: the checkpoint written at the 6,900 s cap.

H1 check, fixed before launch, by `tracking_eval.py --latent --per-stroke` on two fresh dev seeds:
- tennis and LAFAN1 within 3 points of latent-07 (93.2 / 88.8 %);
- mirrored LAFAN1 within 3 points of the new LAFAN1 score.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-080 — Stage 5C: the latent action barrier, not the motion data, limits footwork; walker at lambda = 3

- Date: 2026-10-15
- Status: Accepted (loop)
- Amends: D-077, D-079 (footwork path)

Context:
- **Run 7** (s5c-07-agility-m, the agility walker on the mirrored-data controller s5c-06/latent_12162; dev seed 4200660; `mjlab/results/stage5c-agility-07-dir-*.json`). Within 25 cm at 1.5 m, against run 1 on latent-07: forward 51 % (32 %), right 9 % (27 %), left 0.4 % (0.1 %), back 0 % (0 %). At 2.5 m nothing is reached. **Left and back did not improve.**
- **Latent barrier check** (`mjlab/scripts/motion/latent_barrier_check.py`, dev seed 4200661; `mjlab/results/stage5c-barrier-l07.json`, `-l06m.json`). The walker and the executor act through z = mu_p + lam * sigma_p * tanh(a) with lam = 1, so every latent dimension stays within one prior standard deviation of the prior mean. While the controller tracks its own training clips through the encoder, the largest per-dimension distance |mu_q - mu_p| / sigma_p has a median of 2.1-2.9 (90th percentile 3.2-4.9) in every clip group, on both controllers.
- **Coverage by lam** (share of steps whose latent lies inside the barrier, latent-07):

  | Clip group | lam = 1 | lam = 2 | lam = 3 |
  |---|---:|---:|---:|
  | Tennis strokes | 0-1 % | 24-32 % | 63-73 % |
  | LAFAN1 walk / run / sprint | 0.3-2.6 % | 39-45 % | 82-83 % |
  | Mirrored LAFAN1 walk / run / sprint | 0-0.4 % | 22-24 % | 66-70 % |

  This is what a 32-dimensional Gaussian predicts: the chance that all 32 dimensions lie within 1 sigma is 0.68^32 ≈ 5e-6; within 2 sigma, 0.23; within 3 sigma, 0.92.

**Conclusion.** At lam = 1 the walker can only nudge the prior's default continuation of the current motion. It cannot select a sidestep or a backpedal even though the decoder reproduces both (mirrored walk tracked at 92-93 % through the encoder, even by latent-07). The mirrored-data retrain (D-077) left the barrier unchanged, which is why runs 6-7 did not help. The H3 history fits: lam 0.5 -> 1.0 raised root-target reach from 3.2 % to 8.5 % and paddle reach from 62 % to 73 % (reach-02 -> reach-03, `stage5b-h3.md`).

Decision:
- **Keep latent-07** as the controller. The mirrored-data controller (s5c-06) cost about 10 points of serve and did not unlock footwork. Its artifacts and reports stay as they are.
- **Run 8:** the agility walker of run 1 on latent-07 with **lam = 3.0**, the only change (task `Picklebot-Latent-Reach-Agility-L3-G1`). It warm-starts from run 1's endpoint, has a fixed endpoint at the last checkpoint before the cap, and is measured per direction as in run 1.
- **If left/back become reachable,** the executor moves to a wider barrier in its own run, watching style (<= 3.86) and falls. Its prior penalty (`latent_prior_nll`, (lam * tanh a)^2) grows with lam^2, and that interaction is part of that run's write-up.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-081 — Stage 5C: teach the latent controller the walking teacher's footwork

- Date: 2026-10-15
- Status: Accepted (loop)
- Amends: D-077, D-079, D-080 (footwork path)

Context: four walker runs measured within 25 cm of a 1.5 m target (dev seeds 4200610-680; `mjlab/results/stage5c-agility-0*-dir-*.json`):

| Run | Controller | lam | Start | Fwd | Right | Left | Back |
|---|---|---|---|---:|---:|---:|---:|
| 1 | latent-07 | 1 | warm (reach-06) | 32 % | 27 % | 0.1 % | 0 % |
| 7 | mirrored-data controller (s5c-06) | 1 | warm (run 1) | 51 % | 9 % | 0.4 % | 0 % |
| 8 | latent-07 | 3 | warm (run 1) | 63 % | 33 % | 0.4 % | 0 % |
| 9 | latent-07 | 3 | fresh | 63 % | 26 % | 0.2 % | 0 % |

None of them steps left or back. The flat walking teacher (`Picklebot-Teacher-Move-G1`/model_15900) reaches 99-100 % of move-drill spots in every direction, so the body can. The motion data the latent space is built from shows the gap. Counting frames moving faster than 0.3 m/s, by direction in the heading frame:
- **LAFAN1** is 69 % forward and about 10 % each left, right and back. Mirroring it keeps that mix.
- **The tennis clips** favour the forehand side.

The prior (the walker's and executor's action centre) is conditioned on state. From a ready stance, it has almost never seen a left shuffle or a backpedal.

Decision:
1. **Footwork data from the walking teacher** (`mjlab/scripts/motion/record_policy_clips.py`, training seed 11). 128 move-to-spot episodes of 30 s each, no falls, recorded as G1 motion CSVs and converted with `csv_to_npz_local.py` (`footwork-teacher.npz`: 128 clips, 191,872 frames). Moving frames: forward 37k, left 38k, right 36k, back 27k; median speed 0.72 m/s.
2. **Motion set** `tennis-lafan4.npz`: tennis-v5 + LAFAN1 + mirrored LAFAN1 + footwork, sampled 0.5 / 0.15 / 0.1 / 0.25 (task `Picklebot-Tracking-TennisLafan4-Huge-G1`).
3. **No H0 run is needed.** Run 3b's teacher (s5c-03b/model_63300) already tracks every footwork window at 100 % (dev seed 4200690, `mjlab/results/stage5c-h0-03b-lafan4.json`), and the clips are its own robot's motion.
4. **H1 (run 10)** is distilled from latent-07/latent_10651 with run 3b's teacher on tennis-lafan4, latent-07's settings otherwise (as run 6, D-079). Fixed endpoint: the checkpoint at the 6,900 s cap.
   - Check, fixed now (two fresh dev seeds, encoder path, `tracking_eval.py --latent --per-stroke`): tennis and LAFAN1 within 3 points of latent-07 (93.4 / 89.0 % on seed 4200651), footwork >= 95 %.
   - Serve and smash are reported separately, since run 6 lost about 10 points of serve.
5. **Walker (run 11)** on the run-10 controller at lam = 3, measured per direction as before. The style of the footwork, and so of anything built on it, is judged by the style score in later executor runs (gate <= 3.86).

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-082 — Stage 5C: kickstart the executor's footwork from the walking teacher at lambda = 3

- Date: 2026-10-15
- Status: Accepted (loop)
- Amends: D-081 (footwork path); D-057 (the distillation reasoning, for footwork only)

Context:
- **Run 11** (s5c-11-agility-f-l3; the fresh lambda-3 walker on the footwork controller s5c-10/latent_12135; dev seed 4200710). Within 25 cm at 1.5 m: forward 74 %, right 27 %, left 0.5 %, back 0 %.
  - The run was cut at 1:51:42 of its cap when WSL shut down (no exit record; WSL was found stopped at 18:11).
  - Its last checkpoint, model_2800, is at the same iteration as run 9's endpoint, so the two compare directly.
- **Five walker runs, three controllers, two barriers: left and back never open up.** Travel toward 1.5 m targets in 2 s is about 0.35 m/s left and 0.25 m/s back, against 0.75 m/s forward.
- **Expressiveness floor** (`mjlab/scripts/latent_reach_floor.py`, now with `--task/--latent/--move-prob`; walking teacher on move-only episodes, dev seed 4200720; `mjlab/results/stage5c-floor-move-*.json`). Per state, the best latent command reproduces the walking teacher's *leg* actions as follows (action variance 0.389):

  | Controller | lam = 1 | lam = 3 |
  |---|---:|---:|
  | latent-07 | 0.072 MSE (59 % of latent commands saturated) | **0.027 MSE (93 % explained)** |
  | Footwork controller s5c-10 | 0.099 | 0.061 |

  The footwork controller fits worse: its decoder imitates H0's tracking actions on those clips, not the walking teacher's actions.
- **Conclusion.** Through latent-07 at lambda = 3 the decoder can produce the walking teacher's footwork. PPO over the latent just never finds it from a ready stance.

Decision: copy the footwork in directly, by kickstarting (two-teacher policy distillation; `mjlab/scripts/kickstart_h4.py`, tested).
- **Teachers:**
  - The walking teacher (`Picklebot-Teacher-Move-G1`/model_15900) gives the joint-space target in move-to-spot episodes.
  - A frozen copy of the starting executor gives it in every other episode, scored with its own barrier, lam = 1, so hitting is kept.
- **Student:** the executor on `Picklebot-Latent-Court-L3-G1` (the court drill with lam = 3), trained by MSE through the frozen latent-07 prior and decoder.
- **Rollouts:** DAgger on the student's states, with 50 % move episodes. In the first 20 % of the budget, a decaying share of envs executes the starting executor's action converted to lam = 3 (the same latent), so the barrier switch does not start with falls.

D-057's objection was that imitating the flat hitting student would push the executor to the edge of the human-motion space. Here only the footwork is imitated, and the floor shows it fits inside the lam = 3 barrier (93 % explained, 26 % saturated).

Runs:
- **Run 12:** the kickstart from s5c-02/model_28400. Fixed endpoint: the checkpoint at the 6,900 s cap. Evaluated with `h5c_eval.sh ... Picklebot-Latent-Court-L3-G1` on fresh dev seeds.
  - Primary: move-to-spot arrival per direction, where all runs so far score 0 %.
  - Kept: court legal returns, style, falls.
- **Run 13:** PPO on the lam = 3 court task from run 12's endpoint, to win back what the distillation costs in hitting.
- The style gate (<= 3.86) applies as before. The leg motion now comes from the walking teacher through the human-motion decoder, and the style score will show what that costs.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-084 — Stage 5C: two-teacher kickstart with exact latent copying of the hitting teacher

- Date: 2026-10-15
- Status: Accepted (loop)
- Amends: D-082 (runs after the first kickstart)

Context:
- **Run 12** (kickstart, joint-space losses; `stage5c-s5c-12-*.json`): move-to-spot arrival 76-99 % in every direction and style 3.585, but court legal returns 22 %.
  - On evaluation states the kickstarted executor stays close to its starting executor's joint targets (MSE 0.004, right wrist 0.031; `mjlab/artifacts/eval/ks_diag.py`). Its latent still differs by 0.14 prior sigmas per dimension (median).
  - A return depends on paddle timing around contact, which that loss does not pin down.
- **Run 13** (PPO from run 12): stopped after about 200 of an expected 1,000 iterations, counted. Falls rose to 158-315 per logging interval. Cause: the action-noise std inherited from lam = 1 (about 0.38) moves the latent 3x further at lam = 3.
- **Run 14** (PPO from run 12, latent std x 1/3, `scripts/rescale_action_std.py`; dev seeds 4200750-753; `stage5c-s5c-14-*.json`):
  - Court main metric **74.9 %** (best so far; 42/55 cells). Stage 5B families within 5 points of h4-25b except backspin (-9.8) and reach_deep (-58).
  - **Move-to-spot arrival 0 %, the footwork is gone.** Style 3.868 (limit 3.86), recovery 1.68 m, falls 4.2 %.
  - Under PPO's action noise the robot never holds still long enough to "arrive", so the arrival reward never fires. Meanwhile the latent prior penalty pulls the latent back toward the prior mean.

Decision (run 15): kickstart again (`mjlab/scripts/kickstart_h4.py`, extended):
- **Hitting:** matched exactly in the latent. From run 14's endpoint, ball episodes match run 14's own latent and wrist command (`--hit-loss latent`, lam_self = 3). Both share the barrier, so the copy is exactly representable.
- **Footwork:** move-to-spot episodes match the walking teacher in joint space, as in run 12.
- No PPO, no noise, no penalties. Fixed endpoint: the checkpoint at the 6,900 s cap.
- **The question:** can one network hold run 14's hitting and run 12's footwork when both are copied rather than rewarded?
- **Still open after that:** recovery after the hit (the walking teacher's skill, needed in ball episodes), volleys, lobs and reach_deep, falls, and style.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-085 — Stage 5C: walk back to the recovery spot after every hit (walking teacher in the recovery phase)

- Date: 2026-10-16
- Status: Accepted (loop)
- Amends: D-084

Context: **run 15** (two-teacher kickstart, D-084; dev seeds 4200760-763; `mjlab/results/stage5c-s5c-15-*.json`) is the first executor with both skills.
- **Hitting:** court main metric 74.5 %, 42/55 cells (run 14: 74.9 %). Stage 5B families within 5 points of h4-25b except backspin (-11.4) and reach_deep (-58).
- **Footwork:** move-to-spot arrival fwd 88.5, fwd-left 45.5, left 67.1, back-left 95.0, back 96.5, back-right 95.2, right 92.4, fwd-right 82.7 %.
- **Still failing:** recovery 1.68 m, falls 4.0 %, style 3.872.

Recovery is the pelvis distance to the commanded recovery spot when the next feed fires (`recover_hist`, hit feeds only). In ball episodes every target comes from run 14, which never learned to walk back.

Decision (run 16, `mjlab/scripts/kickstart_h4.py --recover`):
- **Recovery phase:** in a ball episode, from 0.2 s after the robot's first legal contact, or once the rally is dead, the target switches to the walking teacher.
- **What the teacher sees:** the robot, the recovery spot and a ball parked as in move-to-spot episodes. Its ball inputs are recomputed for the parked ball, with the rally flags a move episode shows.
- **Unchanged from run 15:** move episodes still copy the walking teacher, and the hitting part still copies run 14's latent exactly.
- **Start:** from run 15's endpoint (no beta phase). Fixed endpoint: the checkpoint at the 6,900 s cap.
- **Smoke run:** about a third of all steps are recovery phase.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-086 — Stage 5C: reviewed plan for the remaining runs (user-approved)

- Date: 2026-10-16
- Status: Accepted (user, after a five-reviewer consensus round)
- Amends: D-075 loop practice (evaluation rules, order of work)

Context: five read-only reviewers looked at runs 1-18: RL methods, motion priors, pickleball drill design, experiment design, and infrastructure. In a second round they voted on a merged plan, and the user approved it ("go with the agreed plan"). The user made no decision on the plateau-rule rewording or on Windows/WSL sleep settings, so the plateau rule stays as in D-075 and no system settings are changed.

Findings on record (all verified):
1. **Walker runs 1, 7, 8, 9 and 11 were confounded.** The reach task's paddle target is world-fixed at the starting shoulder for each 2 s window, weighted 2.0 against root 1.0 + progress 1.0, so travel was penalised. They show nothing about the controller's footwork.
2. **Run 4 was planned and never run.** The re-aimed volley feeds (D-078) entered training from run 12 without a run of their own. Counted runs: 17 used, 13 left.
3. **Runs that changed more than one thing:** run 6 (teacher and data), run 12 (lambda, method, teacher, episode mix, beta phase), run 15 (loss, teacher and start), run 18 (teacher and start).
4. **Recovery shows the same median, 1.675 m, in runs 14, 15 and 17.** As scored (a random spot up to about 6 m away, judged at the next feed about 1.5-2 s later, with pelvis-anchored feeds), it does not tell policies apart.
5. **Move-to-spot falls were not in the gate:** runs 14 and 17 fall in every move episode.
6. **Cells with fewer than 30 episodes counted as passing** in `h5c_summary.py`, and `h5c_eval.sh` hid failed jobs.
7. **Kickstart losses plateau after 6-30 min.** With `--beta-frac 0` the first iteration still mixes in the hitting teacher, and every family teacher was mapped with one global lam-self.

Plan:
- **0. No-run fixes:**
  - Evaluate run 18 against every gate item before building on it.
  - Falls in the gate = the worse of the court and move-to-spot drills.
  - Cells under 30 episodes count as unresolved, never passing.
  - Evaluation jobs must exit 0 and write a fresh JSON.
  - Run directories are matched exactly.
  - The final evaluation pools 4+ seeds per cell, declared here.
  - A main-metric change under 2 points is re-evaluated on a second seed before it counts for the plateau rule.
  - Recovery gets a stand-still baseline (the gap at contact).
  - The split-step and kitchen-line-zone metrics are reported, not gated.
  - Kickstart: beta fix, per-teacher lam, early stop.
  - TF32 on; PPO iteration limit sized to the 2 h cap.
- **1. Run 19: residual executor around a frozen run 18** (or run 15 if run 18 lacks both skills). z = z_ref(s) + lam_r sigma_p tanh(a).
  - Start: the residual output starts at zero and its std at about 0.1; it also acts on the wrist.
  - The frozen executor sees its own last action. Before launch, check that zero residual reproduces run 18.
  - Penalty (lam_r tanh a)^2, heavier in move episodes.
  - Kill rules fixed at launch: style above 3.86, arrival down more than 15 points in any direction, or more move-drill falls.
- **2. Volley specialist (2 runs).** Train unanchored at lam 3 with an easy on-ramp as curriculum level 0 (soft 4-6 m/s ball, ramping to the gate's 7-10 m/s feeds; training only), then merge with per-teacher lam. Kill rule: volley contact < 5 % at a fixed checkpoint on unchanged evaluation feeds.
- **3. Recovery.** Court-aimed feeds for training and the rally evaluation only; the 55-cell gate drill keeps D-076's pelvis-anchored feeds.
  - Recovery is also scored with the move drill's time model (1.5 s + 1.25 s/m), threshold 0.5 m unchanged, next to the original measure.
  - Runs 15, 17 and 18 are re-scored on it.
- **4. Rally evaluation** (evaluation only): consecutive feeds from a scripted far-court opponent; P(rally >= 10) with a CI, reported next to the gate.
- **5. Reserve and report.** Two runs are kept in reserve. The final candidate is named before the paired final evaluation, and the report states the gate result with the distance and CI on each criterion and lists every rule deviation.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`; `mjlab/scripts/h5c_summary.py`, `h5c_eval.sh`, `stage2_eval.sh`.

### D-087 — Stage 5C: run 19 result, the style kill rule, and the volley specialist (run 20)

- Date: 2026-10-16
- Status: Accepted (loop, under D-086)
- Amends: D-086 (record of run 19; run 20 launch)

Run 19, the residual executor around frozen run 18 (D-086; dev seeds 4200810-815, `mjlab/results/stage5c-s5c-19-*.json`):
- **Move-to-spot arrival passes the gate in every direction**, the first gate item met in Stage 5C: fwd 99.7, fwd-left 94.8, left 96.9, back-left 98.2, back 98.0, back-right 99.7, right 99.8, fwd-right 99.5 %. Move-drill falls 0.07 %.
- **Court main metric 79.3 % / 79.5 % on two seeds** (run 18: 79.9 / 81.0 %). Court falls 4.6 %. Backspin@back fell to 58 %.
- **Recovery** (time model) 1.325 m, against a stand-still gap of 2.075 m.
- **Rally** P(>= 10) 0.0, mean ended rally 0.19 shots.
- **Endpoint:** the run hit its 2 h cap at iteration about 990, slowed while a rally smoke test shared the GPU, so the fixed endpoint is the last checkpoint, model_900.

**The kill rule fixed at launch, "style above 3.86", triggered: style 4.162.** It was written without noticing that the base (run 18) was already at 4.008, so as written it could never pass from that base. It stands as triggered: run 19 is not continued, and the residual's style remains open. No post-hoc reinterpretation.

**Plateau count:** run 18 (80.5 % pooled, vs run 17's 80.4 %) is strike 1, run 19 (79.4 % pooled) strike 2. The next executor run must reach at least 81.5 % court main metric (two-seed mean when within 2 points), or the loop ends.

**Run 20: volley specialist (a teacher run, not counted for the plateau rule).**
- PPO on `Picklebot-Latent-Court-Volley-L3-G1`: volley feeds only, starts and recovery spots in the mid and front zones, no move or ghost episodes, lambda 3, learning-progress curriculum with the D-086 on-ramp (level 0: 5.7-7.7 m/s at 0.7-1.2 m), hint probability 0.2 as in every executor run.
- Starts from run 18 (the lambda-3 two-skill executor; volley contact 0 %). Fixed endpoint: iteration 1,000, or the last checkpoint before the cap.
- **Kill rule:** volley contact below 5 % at the endpoint, on the unchanged gate feeds (court drill, volley families, no hint), ends volley work for this stage.
- If it passes, run 21 merges it with `kickstart_h4.py --family-teacher` (per-teacher lambda).

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-088 — Stage 5C: run 20 result; the volley specialist as a residual (run 21)

- Date: 2026-10-16
- Status: Accepted (loop, under D-086)
- Amends: D-087

Run 20 (s5c-20b-volley; plain PPO from run 18 on the volley-only task):
- **It collapsed:** falls 4 -> 222 per logging interval and episode length 56 steps (1.1 s) by iteration 33,050.
- **Stopped early at model_33000 and counted.** The first launch, s5c-20-volley, crashed at start-up on an empty back-zone sampler (fixed, test added) and is not counted.
- **Kill-rule check on the gate feeds** (dev seed 4200830, `mjlab/results/stage5c-s5c-20-volley-kill.json`):
  - Volley contact: forehand 13.6 %, backhand 0 %, pooled 6.8 %, above the 5 % line.
  - Legal returns 0 %; falls 72-77 % of volley episodes.
- **The kill rule formally did not trigger, but run 20 is not a usable teacher.**

Pattern: plain PPO started from a kickstarted (distilled) executor has blown up into falls every time (runs 13, 14, 20). PPO as a residual around a frozen executor did not (run 19).

Decision, run 21, the last volley attempt:
- **Setup:** the volley specialist as a residual around frozen run 18, lam_r = 2 (so it can reach volley motions run 18 lacks), on `Picklebot-Latent-Court-Volley-Res2-G1`. Otherwise run 20's task and settings.
- **Start:** residual zero-initialised, std 0.1 (`scripts/residual_init.py` from run 18).
- **Endpoint:** fixed at iteration 1,000, or the last checkpoint before the cap.
- **Kill rule, fixed now:** on the gate's volley feeds (court drill, no hint), pooled contact < 10 % or volley-episode falls > 20 % ends volley work for this stage. Only then would a merge run follow.
- **Teacher run:** not counted for the plateau rule.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-089 — Stage 5C: volley work ends; run 22 trains the residual executor on court-aimed feeds

- Date: 2026-10-16
- Status: Accepted (loop, under D-086)
- Amends: D-088

Run 21 (residual volley specialist, lam_r 2, around frozen run 18):
- **Training:** paddle contact 0.0000 and falls 0 for all 1,000 iterations.
- **Kill rule check** on the gate feeds (dev seed 4200840, `mjlab/results/stage5c-s5c-21-volley-kill.json`): contact forehand 0.0 %, backhand 3.2 %, pooled 1.6 % < 10 %.
- **The kill rule triggers: volley work ends for Stage 5C.** The volley gate items (4 cells, "volleys >= 75 %") are reported as not met.
- Three ways were tried: feed re-aim (D-078), plain PPO specialist (run 20), residual specialist (run 21). None produced a single legal volley.

Run 22: the most valuable remaining executor run, per the D-086 plan step 3.
- **What it targets:** the rally evaluation shows the gap. Run 18 returns 80 % of pelvis-anchored feeds but 36 % of court-anchored ones, with no 10-shot rally: it hits balls aimed at it but cannot get itself to the ball.
- **Change** (one, against run 19's setup): half of the *training* feeds are court-anchored. The feed anchor is the start spot, drawn per feed (`court_anchor_prob` 0.5, `Picklebot-Latent-Court-Res-Rally-G1`, test added). The 55-cell gate drill keeps D-076's pelvis-anchored feeds.
- **Setup:** a fresh residual around frozen run 18 (lam_r 1, zero-initialised, std 0.1, `s5c-19-init/model_0`). It does not continue run 19, per its kill rule.
- **Endpoint:** iteration 1,000, or the last checkpoint before the cap.
- **Kill rules, fixed now** (written against the base's actual values this time): style above 4.16 (run 18's 4.008 + 0.15), move arrival below 90 % in any direction, or move-drill falls above 1 %.
- **Plateau:** this is an executor run. It must reach 81.5 % on the main metric (two-seed mean if within 2 points of the best), or the plateau rule ends the loop and the final evaluation follows.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`.

### D-090 — Stage 5C: plateau stop; final candidate named (run 22); rally evaluation fix

- Date: 2026-10-16
- Status: Accepted (loop, D-075 rule 6)
- Amends: D-086, D-089

Run 22 (residual around frozen run 18, half the training feeds court-anchored; dev seeds 4200850-855; `mjlab/results/stage5c-s5c-22-*.json`):
- **Gate drill (pelvis-anchored):** court main metric 78.5 %, 40/55 cells.
- **Footwork:** move-to-spot arrival 99.4-99.9 % in every direction (gate met), move-drill falls 0.05 %.
- **Court falls** 3.8 %.
- **Recovery** (time model) 1.275 m, the best so far (stand-still gap 2.075 m).
- **Style** 4.026, under its kill line of 4.16 but above the gate's 3.86.
- **Stage 5B regression:** backspin -37 (backspin@back 50 %), fast -6.5, reach_deep -9.5.
- **Court-anchored (rally) feeds:** legal 43.3 % (run 18: 36.2 %, run 19: 38.6 %).

**Plateau stop.** Runs 18 (80.5 % two-seed mean against run 17's 80.4 %), 19 (79.4 %) and 22 (78.5 %) are three executor runs in a row each improving the main metric by less than 1 point. Run 22 is 2.0 points below the best, so no repeat was needed. Under D-075 rule 6 the loop ends: paired final evaluation, review videos, gate report. Runs used: 21 counted (1, 2, 3b, 5-19, 20b, 21, 22), 9 unused.

**Final candidate, named before the final evaluation: run 22, s5c-22-res-rally/model_900.** Among the two-skill executors it meets the most gate items: arrival, and move-drill falls under the D-086 rule. It also has the best recovery and the best court-anchored legal rate. Run 18 has the higher main metric but fails arrival.

**Final evaluation:**
- `scripts/h5c_final.sh`: candidate and stage baseline h4-25b on the same four fresh dev seeds 4200900-903, pooled per cell (the D-086 rule). Then the candidate's other gate jobs on 4200904.
- Review videos: `scripts/h5c_videos.sh`, seed 4200910.

**Rally evaluation fix.** P(rally >= 10) read 0 for every run because a training-length episode (EPISODE_S) fits only about 7-8 feeds: a 10-shot rally could never complete. Rally evaluations now run one episode as long as the evaluation. Runs 18 and 22 are re-scored (90 s, seed 4200860; `stage5c-s5c-18-rally90.json`, `-22-rally90.json`). Earlier rally numbers are kept but marked capped.

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5C; `mjlab/results/stage5c.md`; `mjlab/results/stage5c-gate.md`.

### D-091 — Stage 5D: rally training (user-approved plan, gate and budget)

- Date: 2026-10-17
- Status: Accepted (user: rally target P(rally >= 10) >= 20 %, 15 runs)
- Amends: roadmap (Stage 5D inserted before Stage 6)

Context: Stage 5C ended with the gate not met (D-090). The candidate (run 22) returns 79 % of pelvis-anchored balls but only 62 % of court-anchored ones, and 1.6 % of rallies reach 10 shots. Training on court-anchored feeds (run 22) moved rallies most. Volleys, falls and style did not respond to more training, and the residual executor cannot move more than lam_r sigma from its base. The user asked for rally training that bundles the fixes practice cannot supply.

**Gate (thresholds never loosened):**
- **Rally:** P(rally >= 10) >= 20 % on the rally evaluation: court-anchored feeds, 90 s episodes, no hint. Final evaluation pooled over 4 fresh dev seeds.
- **Falls:** court falls <= 1 % (the worse of court and move drill, D-086).
- **Style:** <= 3.86.
- **Arrival:** move-to-spot >= 90 % in every direction.
- **Court drill:** main metric (pelvis-anchored, 55 cells) no more than 2 points below run 22's final 78.8 %. Volleys are excluded from this stage.

**Budget and loop rules:**
- Up to 15 training runs, each <= 2 h with a fixed endpoint written before launch. One change per run, written down before launch. Warm starts where sensible. Fresh dev seeds for every evaluation; final seeds never used.
- Main metric for the plateau rule: P(rally >= 10). The loop stops after 3 executor runs in a row each improving it by less than 2 points absolute. Changes within 3 points of the best are re-evaluated on a second seed before they count.
- Kill rules are fixed at launch, against the base's actual values.
- Stop and ask the user before sudo or system changes, Unity or the feat/hierarchical-control checkout, deleting anything, any download, any run over 2 h, or using final seeds.
- End: paired final evaluation, review videos (side, behind, a long rally), `mjlab/results/stage5d-gate.md`, commit, push.

**Plan:**
1. **Build first (no runs):**
   - a rally drill task: a scripted far-court opponent whose shots are aimed at court regions, long episodes, the recovery spot set by a simple court-position rule, and a reward for each legal return in a rally;
   - a falls diagnosis of run 22 (phase, family, zone, posture at the fall);
   - consolidation support: kickstart a new base from a residual executor read as one composite policy;
   - tests for each.
2. **Training:** residual PPO from run 22 on the rally drill. One change per run after that:
   - a style anchor;
   - a falls fix chosen from the diagnosis;
   - consolidation merges every 3-4 PPO runs, to lift the residual's bound.

Affected roadmap/spec sections: MJLAB_PIVOT.md (new Stage 5D section); `mjlab/results/stage5d.md`.

### D-092 — Stage 5D build: rally drill, falls diagnosis, consolidation; run 1

- Date: 2026-10-17
- Status: Accepted (loop, under D-091)
- Amends: D-091

**Falls diagnosis of run 22** (`mjlab/scripts/diag/falls_diag.py`, court drill, dev seed 4200920, `mjlab/results/stage5d-falls-run22.json`):
- **When:** 289 falls in 12,333 robot episodes, 61 % while the ball is still incoming (before any contact), 20 % between feeds, 13 % after the hit, 6 % in the contact window.
- **Speed:** median pelvis speed one step before a fall 1.59 m/s, against 0.58 m/s otherwise.
- **Where:** concentrated in the long-reach families (lob 50, cross_backhand 41, reach_deep 38, cross_forehand 36, drop 23) and in the mid (147) and front (95) zones.
- **Conclusion:** the falls come from running too fast for balls far away. That sets the falls fix for a later run: a speed or balance term, one change.

**Rally drill** (`Picklebot-Latent-Court-Rally-G1`, residual around run 18 as in Stage 5C runs 19 and 22):
- **Feeds:** 75 % court-anchored. Those feeds send the robot to the fixed baseline-centre recovery spot, as the rally evaluation does.
- **Episodes:** 30 s, so that rallies can build.
- **Rally bonus:** at each legal return, 2.5 / step_dt x min(streak, 10) / 10, read just before legal_return. The streak counts consecutive legal returns and is reset by a missed feed or a reset. Tests added.
- **Bug fix:** the per-feed court-anchor draw was re-drawn for in-flight feeds at every refeed. It is now restored as the feed's zone and unit are. Run 22's feeds were unaffected, since the draw was only used inside the same feed call.
- **Deviation from D-091's wording:** the "scripted far-court opponent" keeps the existing feed origin (start x 0.8-1.2 m). The gate's rally evaluation uses that origin, so training and gate match. A far-baseline opponent would change every family's flight geometry and invalidate the tuned feeds.

**Consolidation** (`mjlab/scripts/consolidate.py`, `tests/test_consolidate.py`):
- It distils a residual executor into one lambda-3 executor by DAgger. The composite is read exactly in the lambda-3 action space: tanh(a) = tanh(a_base) + (lam_r / lam) tanh(a_res), clamped, wrist likewise, each part fed its own last action.
- Smoke run (run 22 into a student starting from run 18): the loss fell 0.037 -> 0.020 in 14 iterations, and about 4 % of target values hit the clamp.
- The student task is `Picklebot-Latent-Court-Rally-L3-G1`. `_residualize` now takes the base checkpoint, for the next residual stage.

**Run 1 (s5d-01-rally):**
- **Change:** PPO continuation of run 22's residual policy (around frozen run 18) on the rally drill. The only change from run 22 is the task (the rally drill).
- **Endpoint:** iteration 1,900 (1,000 more), or the last checkpoint before the cap.
- **Kill rules, fixed now against run 22's final values:**
  - style > 4.17 (4.017 + 0.15);
  - move arrival < 90 % in any direction;
  - move-drill falls > 1 %;
  - court main metric < 76.8 % (the gate floor).

Affected roadmap/spec sections: MJLAB_PIVOT.md Stage 5D; `mjlab/results/stage5d.md`.

### D-093 — Stage 5D run 1 result (style kill rule) and run 2 with a style anchor

- Date: 2026-10-17
- Status: Accepted (loop, under D-091)
- Amends: D-092

Run 1 (s5d-01-rally; PPO continuation of run 22 on the rally drill; endpoint model_1800, the last checkpoint before the cap; dev seeds 4200930-935, `mjlab/results/stage5c-s5d-01-*.json`):
- **Rally P(>= 10) 9.67 %** [9.05, 10.34], mean ended rally 2.68 (run 22: 1.6 %, 1.44). That is +8.1 points on the main metric.
- **Arrival** 99.5-100 % in every direction; move-drill falls 0.15 %.
- **Court** main metric 77.9 % (gate floor 76.8 %).
- **Recovery** (time model) 1.175 m.
- **Court falls 6.1 %** (run 22: 3.3 %).
- **Style 4.199: the kill rule fixed at launch (style > 4.17) triggers.** As in D-087, run 1 is not continued or built on.

Cause of the style drift (code reading): the residual tasks replaced D-072's prior-likelihood penalty with a penalty toward the frozen base. Nothing pulls the composite latent toward the prior mean any more, so PPO moves it into poses far from the clips.

**Run 2 (s5d-02-rally-style):**
- **Change:** run 1's recipe from run 22 (the rally drill), plus the style anchor `composite_prior_nll`: sum (lam tanh(a_base) + lam_r tanh(a))^2 = |z - mu_p|^2 / sigma_p^2 on the composite latent, weight 0.05 (Stage 5B's Prior5 value, which held style at 3.81), next to the residual penalty. Task `Picklebot-Latent-Court-Rally-Style-G1`, test added.
- **Measured against run 1:** the one change is the style anchor. It starts again from run 22 because run 1's kill rule triggered.
- **Endpoint:** iteration 1,900, or the last checkpoint before the cap.
- **Kill rules** (against run 22, the base): style > 4.17, arrival < 90 % in any direction, move-drill falls > 1 %, court main metric < 76.8 %.
- **Court falls:** they rose to 6.1 % in run 1. The falls fix (D-092 diagnosis) is the next change after style.

Affected roadmap/spec sections: `mjlab/results/stage5d.md`.

### D-094 — Stage 5D run 2 result; style breakdown; run 3 with an overspeed penalty

- Date: 2026-10-17
- Status: Accepted (loop, under D-091)
- Amends: D-093

Run 2 (s5d-02-rally-style, model_1800; dev seeds 4200940-945, repeats 4200950-953; `mjlab/results/stage5c-s5d-02-*.json`):
- **Rally P(>= 10)** 7.57 % / 7.73 % (mean 7.65 %).
- **Style** 4.148 / 4.133: the anchor at weight 0.05 moved style by only about -0.05.
- **Arrival right** 85.8 % / 86.6 %: **the kill rule (arrival < 90 % in any direction) triggers.**
- Court 77.8 %; court falls 5.1 %.
- The run 1 style repeat (4.196) confirms run 1's kill rule.
- **Plateau:** run 1 improved the main metric by +8.1 points; run 2 is strike 1 (7.65 % against 9.67 %).

**Style breakdown** (`mjlab/scripts/diag/style_breakdown.py`, court drill as the gate's style job, dev seed 4200960, `mjlab/results/stage5d-stylebd-*.json`):

| Executor | Style median | Slow poses (< 0.8 m/s) | Fast poses (>= 0.8 m/s) | Fast share |
|---|---:|---:|---:|---:|
| h4-25b (Stage 5B gate executor) | 3.88 | 3.44 | 4.48 | 32 % |
| run 22 | 4.02 | 3.58 | 4.50 | 34 % |
| run 1 (s5d-01) | 4.22 | 3.75 | 4.59 | 39 % |

- **h4-25b itself scores 3.88 on the court drill** (3.81 on the Stage 5B drill), above the 3.86 gate.
- **Fast poses sit at about 4.5 for every executor.** The running gait with the paddle is far from the clip set.
- **Rally training raises the fast share and the slow-pose distance.**
- **No feature group dominates:** legs 26-30 %, right wrist 15-17 %, left arm 14-17 %, waist 11-12 %.
- **Reported, not acted on:** the style gate (never loosened) may be out of reach on this drill for any executor that moves this much. It stays as written.

**Run 3 (s5d-03-rally-speed):**
- **Change:** run 1's recipe from run 22 (the rally drill), plus the falls fix, a penalty -0.5 (v - 1.2)^2 on pelvis ground speed above 1.2 m/s (`overspeed`, `Picklebot-Latent-Court-Rally-Speed-G1`, test added).
- **Measured against run 1:** this is the only change, chosen because run 22's falls happen at a median 1.59 m/s (D-092) and fast poses are the costly ones for style.
- **No style anchor:** run 2 showed it cost rally and arrival for little style.
- **Endpoint and kill rules:** endpoint iteration 1,900 or the last checkpoint before the cap. Kill rules as runs 1-2 (against run 22): style > 4.17, arrival < 90 % in any direction, move-drill falls > 1 %, court < 76.8 %.

Affected roadmap/spec sections: `mjlab/results/stage5d.md`.

### D-095 — Stage 5D run 3 result; run 4 with a gait anchor

- Date: 2026-10-17
- Status: Accepted (loop, under D-091)
- Amends: D-094

Run 3 (s5d-03-rally-speed, model_1800; dev seeds 4200970-975, rally repeat 4200980; `mjlab/results/stage5c-s5d-03-*.json`):
- **Rally P(>= 10)** 8.44 % / 8.96 % (mean 8.70 %).
- **Court falls 4.7 %** (run 1: 6.1 %); move-drill falls 0.1 %; arrival 98.7-99.9 %.
- Court 78.0 %; recovery 1.225 m.
- **Style 4.210: the kill rule (> 4.17) triggers.** The overspeed penalty barely engaged (about -0.006 per episode), so the robot rarely exceeds 1.2 m/s, and it did not move style.
- **Plateau:** strike 2 (run 2: 7.65 %, run 3: 8.70 %, against run 1's 9.67 %). Run 4 must reach at least 11.67 %, or the plateau rule ends Stage 5D.

**Run 4 (s5d-04-rally-gait):**
- **Change:** run 1's recipe from run 22 (the rally drill), plus a gait anchor (`gait_anchor`, `Picklebot-Latent-Court-Rally-Gait-G1`, test added). The reward is 1.0 x exp(-mean((q - q_walk)^2) / 0.22^2) for matching the flat walking teacher's joint action while walking.
  - **Move-to-spot episodes:** the teacher sees the real observation.
  - **Ball episodes before the ball is within 1 m and before contact:** the teacher sees a parked ball, with the feed's ideal stance spot as its target.
- **Why:** fast poses cost about 4.5 in style for every executor (D-094), while run 12, whose footwork was distilled from this teacher, scored 3.585. Run 22's falls happen while running (D-092).
- **Endpoint:** iteration 1,900, or the last checkpoint before the cap.
- **Kill rules** (against run 22): style > 4.17, arrival < 90 % in any direction, move-drill falls > 1 %, court < 76.8 %.

Affected roadmap/spec sections: `mjlab/results/stage5d.md`.

### D-096 — Direction review (five reviewers) and user decisions; Stage 5D end rule and final candidate rule

- Date: 2026-10-17
- Status: Accepted (user, recorded before run 4's evaluation result)
- Amends: D-091 (Stage 5D end), roadmap (next stage)

A second five-reviewer round (RL methods, motion and style, pickleball drill design, experiment design, architecture) reviewed Stage 5D runs 1-3 while run 4 was training. Shared findings:
1. **Rally length is a per-shot reliability problem.** Feeds are independent, so P(rally >= 10) is about p^10 (run 1: p = 77.4 %, 0.774^10 = 7.7 %; the gate's 20 % needs p of about 0.85). Five families carry most of the misses on court-anchored feeds: reach_deep 46 %, backspin 52 %, fast 56 %, low 66 %, cross_backhand 67 %. The other 12 sit at 79-93 %. Runs 1-3 changed nothing for those families.
2. **The style gate as measured is likely out of reach on this drill.** h4-25b scores 3.88; fast poses cost about 4.5 for every executor because the reference has no running with a paddle; rally training raises the fast share.
3. **The gait anchor (run 4) is flawed:** it matches all joints, arms included, during the approach, and its reward is only paid while the ball is more than 1 m away.
4. **The rally drill design itself pushes falls and style up:** uniform extreme feeds, sprints back to the baseline centre, machine-set pacing.
5. **The loop rules interact badly:** the plateau bar came from a killed run, no run compounded on another, the kill rules do not watch court falls, and runs 2-3 had undersized reward weights.

Disagreement: the architecture reviewer recommends replacing H1, H4 and the residual stack with a goal-conditioned controller plus an analytic interception planner. The others recommend keeping the stack and changing what it is trained on.

**User decisions:**
1. **Stage 5D rules unchanged.** If run 4 does not reach 11.67 %, the plateau rule ends Stage 5D (final evaluation, videos, gate report).
2. **Style:** obtain real human footwork motion capture for the reference and the controller data. That is a download, so the dataset, source, size and licence go to the user for approval before anything is fetched.
3. **Next stage:** keep the stack. Fix the rally drill (realistic feed mix, position-dependent recovery, pacing from the robot's own return), weight feeds by failure rate, add a backspin family teacher, and give the executor the interception (stance) spot on every feed. A controller rebuild is decided from that stage's evidence.

**Final candidate rule for Stage 5D (fixed now, before run 4's result):** the candidate is the run among 1-4 with the highest P(rally >= 10), taking the mean over the seeds evaluated, whatever its kill rules. The report states every kill-rule result and the best run that passed its kill rules (run 22).

Affected roadmap/spec sections: MJLAB_PIVOT.md (Stage 5D end, next stage); `mjlab/results/stage5d.md`.

### D-097 — Realigned plan (reviewer round 2) and user decisions; Stage 5D run 4 result; end procedure

- Date: 2026-10-17
- Status: Accepted (user)
- Amends: D-096

**Run 4** (s5d-04-rally-gait, model_1700, the last checkpoint before the cap; dev seeds 4200990-995):
- Rally P(>= 10) 8.0 % [7.4, 8.6].
- Court 77.0 %, court falls 5.9 %.
- **Style 4.184: the kill rule (> 4.17) triggers.** Arrival 99.5-100 %.
- **Plateau:** it falls short of run 1's 9.67 % + 2. It lies within 3 points of the best, so it is repeated on a second seed (below).

**Reviewer round 2:** the five reviewers voted on the realigned plan. Amendments adopted:
- **5D final candidate:** runs 1-4 are rally-evaluated on the same two fresh dev seeds (4201000, 4201001), which also serves as run 4's second-seed repeat. The candidate is the run with the highest mean. It is labelled "best rally, failed kill rules" and evaluated in the paired final evaluation next to run 22, the best run that passed its kill rules.
- **5D report:** every kill-rule result; per-shot p with CIs next to P(rally >= 10), and the p^10 finding; the style finding; runs 2-3 under-dosed; run 1's bundled bug fix; court falls 3-6 % since Stage 5C.
- **Next stage (5E), before any training run:**
  1. **Freeze drill v2 and its evaluation:**
     - feed groups, evenly weighted inside each group, never two extremes in a row: neutral 60 % (easy_forehand, wide_forehand, backhand, deep, short, high, low, topspin), moderate 25 % (fast, backspin, reach_forehand, reach_backhand, reach_short), extreme 15 % (cross_forehand, cross_backhand, reach_deep, drop);
     - recovery x = clamp(x_contact, -5.6, -4.5), y = clamp(0.4 y_contact, -1.2, 1.2);
     - next feed 0.2 s after the robot's return lands or is ruled dead;
     - failure-weighted sampling in training only, with the extreme share capped at 25 %.
  2. **Stance (interception) spot computed by a planner from noisy, delayed ball observations,** not the feed geometry. Evaluations are reported with the spot clean, perturbed and absent.
  3. **Sim-to-real from the start:** 20-40 ms observation latency and ball-state noise, and a check of the actuator limits.
  4. **Run 0:** run 22, and the consolidated base, scored on the frozen evaluation.
  5. **Loop rules:**
     - kill thresholds fixed for the whole stage from the base's drill-v2 values, including court falls;
     - a killed run still counts as a plateau strike, measured against the best passing run;
     - a consolidation is a counted run under the same kill rules;
     - each new term is sized offline (10-30 % of the task reward magnitude) and logged in training;
     - gamma 0.995 with a critic warm-up.
- **Run order, one change each:** consolidation, then a properly sized falls fix, then the stance spot on every feed, then failure-weighted feeds, then the backspin family teacher.
- **Rebuild decision rule, fixed now.**
  - No controller rebuild if, with the spot on every feed (pooled over 4 seeds), all three hold: per-shot p >= 0.85 on drill v2; lob, reach_deep, cross_backhand and backspin@back each >= 75 %; court falls <= 2 %.
  - Rebuild if any of these holds: p plateaus below 0.80; a weak family stays below 65 %; volley contact stays below 20 % with the spot given.
- **Offline (no GPU) in parallel:** a planner module with tests, the goal-conditioned controller's command spec, and a reachability map.

**User decisions:**
1. **Stage 5E gate:**
   - per-shot legal p >= 0.80 on drill v2, with group floors neutral >= 0.92, moderate >= 0.80, extreme >= 0.55;
   - stretch target p >= 0.85;
   - court falls <= 1 %, move-to-spot arrival >= 90 % in every direction, court main metric >= 76.8 %;
   - P(rally >= 5), P(rally >= 10) and the old 5D rally evaluation reported, with no-hint and perturbed-spot results.
2. **Download approved:** 100STYLE (Zenodo record 8127870, CC BY 4.0, raw BVH only, about 1.5 GB), into the git-ignored `mjlab/artifacts/motion/`. Clips are filtered to neutral and athletic styles by a rule written before any robot is scored, and the dataset is credited.
3. **Style gated on a new reference:** style <= 3.86 is measured against tennis-v5 + LAFAN1 + the filtered 100STYLE footwork clips, with h4-25b re-scored on it as calibration. Each source's share of the reference sample is fixed in advance. The old-reference score is always reported alongside. The user approved this as a partial loosening (a larger, footwork-heavy reference lowers distances mechanically).
4. **Footwork path:**
   - first a free check: track the new clips through latent-07's encoder;
   - if >= 90 %, use a discriminator style reward with the new clips;
   - otherwise H0 -> H1 retraining.

Affected roadmap/spec sections: MJLAB_PIVOT.md (Stage 5E to be written); `mjlab/results/stage5d.md`.

### D-098 — Round-3 review of D-097, user answers, seed correction

- Date: 2026-10-17
- Status: Accepted (user)
- Amends: D-097 (seeds, 5E details)

**Review.** Five reviewers checked the D-097 decisions. Four agreed with caveats. The pickleball reviewer objected to the 5D candidate rule: only runs that passed their kill rules should be eligible, and the candidate should be picked before the paired final on fresh seeds.

**User answers.**
- **5D candidate:** unchanged from D-097. The best mean P(rally >= 10) of runs 1-4 on the same two seeds is the candidate, labelled "best rally, failed kill rules". It is paired against run 22, the best run that passed its kill rules, on fresh seeds disjoint from the selection seeds. Every kill-rule failure is listed as a deviation.
- **Style threshold on the new reference:** stays absolute at 3.86. h4-25b's re-score is reported for information only, and the old-reference score is always reported.

**Caveats adopted for Stage 5E.**
- **Style reference:**
  - A held-out 100STYLE slice is used only as style reference and never for training.
  - The filter rule is written against 100STYLE's own style labels: neutral walking and sidestep only.
  - Retarget quality is checked (foot sliding, ground contact) before any clip is used.
  - Wrist joints are excluded from the style discriminator.
  - The tracking teacher is checked on held-out clips.
  - The reference, filter and shares are frozen before any scoring.
- **Download:** confirm the exact download size before fetching, and record the CC BY 4.0 attribution.
- **Group floors:** judged on Wilson lower bounds.
- **Falls fix:** its mechanism is written down before its run.
- **Action delay:** 0-20 ms.
- **Stance spot:**
  - Run 0 evaluates the spot-given baseline first.
  - At evaluation the spot comes from the noisy, delayed planner.
- **Gate scope:** the report states that the 5E gate of p >= 0.80 implies about 11 % P(rally >= 10), below 5D's 20 %. Only the 0.85 stretch target matches it.

**Seed correction (D-097 erratum).** D-097 named seeds 4201000/4201001, which lie outside DEV_EVAL_SEEDS (4200000-4200999). The evaluator's guard rejected them before anything ran. Replacements, from text-searched unused blocks:
- same-seed rally comparison: 4200961 and 4200962;
- paired final (h5d_final.sh): S = 4200325 (uses 4200325-4200350).

Affected roadmap/spec sections: MJLAB_PIVOT.md (Stage 5E); `mjlab/results/stage5d.md`; `mjlab/artifacts/eval/samesd.sh`.

### D-099 — Stage 5D gate: not met (plateau stop); candidate run 1; Stage 5E next

- Date: 2026-10-17
- Status: Accepted (loop end, D-091)
- Amends: none (records the Stage 5D result)

**Plateau stop.** Runs 2-4 did not improve on run 1's P(rally >= 10) by 2 points. Run 4's second-seed repeat confirmed the third strike. 4 of the 15 runs were used.

**Candidate (rule D-096, kept in D-098):** run 1, `s5d-01-rally/model_1800`, labelled "best rally, failed kill rules" (style). It has the best same-seed mean on dev seeds 4200961/2: 9.58 % vs 7.91 / 8.44 / 7.87 % for runs 2-4.

**Paired final vs run 22** (dev seeds 4200325-4200350, no final seeds):

| Item | Run 1 | Run 22 | Gate |
|---|---|---|---|
| P(rally >= 10), pooled over 4 seeds | 9.59 % [9.27, 9.91] | 1.75 % [1.64, 1.87] | >= 20 %: fail |
| Per-shot p on court-anchored feeds | 77.4 % | 62.5 % | — |
| Court main metric | 78.3 % [78.0, 78.6] | 78.8 % | >= 76.8 %: pass |
| Court falls | 5.9 % | 3.3 % | <= 1 %: fail |
| Style | 4.202 | 4.017 | <= 3.86: fail |
| Arrival, every direction | 99.7-100 % | 99.4-99.95 % | >= 90 %: pass |

2 of 5 gate items are met.

**Next:** Stage 5E as planned in D-097/D-098 (MJLAB_PIVOT.md). Report: `mjlab/results/stage5d-gate.md`.

Affected roadmap/spec sections: MJLAB_PIVOT.md (Stage 5D checklist, log); `mjlab/results/stage5d-gate.md`; `mjlab/results/stage5d.md`.

### D-100 — Stage 5E start point, budget and plateau rule

- Date: 2026-10-18
- Status: Accepted (user)
- Amends: D-097, D-098 (Stage 5E loop rules)

**User decisions:**
1. **Start point:** Stage 5D candidate run 1 (`s5d-01-rally/model_1800`).
   - The first training run is its consolidation into a fresh lambda-3 base (`scripts/consolidate.py`, a counted run).
   - Run 22 stays as the comparison executor in run 0 and in the final paired evaluation.
2. **Budget:** up to 15 training runs, each <= 2 h with a fixed endpoint and one change written down before launch.
3. **Plateau:** stop after 3 executor runs in a row each improving per-shot legal p on drill v2 by < 1 point absolute.
   - Killed runs count as strikes against the best passing run (D-097).
   - A run within 1.5 points of the best is repeated on a second seed.

**Unchanged:**
- **Build order:** drill v2 and its frozen evaluation, the stance-spot planner, latency and noise, the style reference; then run 0, then training.
- **Gate:** D-097/D-098.
- **Stop and ask the user before:** sudo or system changes, Unity or the feat/hierarchical-control checkout, deleting anything, any download, any run over 2 h, or using final seeds.

Affected roadmap/spec sections: MJLAB_PIVOT.md (Stage 5E).
