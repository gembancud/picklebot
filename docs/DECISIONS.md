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
