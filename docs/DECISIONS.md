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
- Status: Accepted

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
