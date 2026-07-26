# Picklebot Phase 1B physics calibration specification

Status: **Normative**

Version: `physics-calibration-v0`

Input environment: `env-v0`

Required output environment: `env-v1`

Phase 1B converts the stable but deliberately simplified `env-v0` simulator
into a measured pickleball-physics baseline before trainer installation or
substantive reinforcement learning. It preserves the deterministic environment
contract and Phase 1A evidence while replacing uncalibrated physical constants
and collision approximations with versioned, testable values.

## 1. Completion boundary

Phase 1B provides:

- a named outdoor 40-hole reference-ball profile;
- measured ball-drop, flight, spin, court-contact, and paddle-contact fixtures;
- quadratic aerodynamic drag and a validated spin-lift model;
- a legal representative paddle collision envelope;
- a regulation-width net collision envelope;
- calibration evidence with provenance and uncertainty;
- a source-exact `env-v1` freeze;
- regenerated scripted baselines clearly separated from `env-v0`.

Phase 1B excludes:

- ML-Agents installation and trainer dependencies;
- policy optimization or checkpoint selection;
- humanoid arm, grip, acceleration, or whole-body dynamics;
- computational fluid dynamics of individual ball holes;
- deformable ball, paddle, court, or net meshes;
- wind randomization;
- full serve, double-bounce, non-volley-zone fault, scoring, and match rules.

Those exclusions keep calibration bounded. Phase 1C begins trainer integration
and learned paddle returns only after this gate closes.

## 2. Source hierarchy and reproducibility

Calibration sources, in descending order of authority, are:

1. current USA Pickleball equipment and court standards;
2. peer-reviewed measured pickleball trajectories;
3. project-owned physical captures of an approved ball, paddle, and acrylic
   court under recorded conditions;
4. explicitly labelled engineering assumptions.

Every final coefficient must name its source, fitting method, uncertainty, and
date in a machine-readable calibration manifest. A plausible-looking trajectory
or hand-tuned Unity material is not evidence.

Current reference sources:

- [2026 USA Pickleball Official Rulebook](https://usapickleball.org/rules/);
- [USA Pickleball Equipment Standards Manual](https://equipment.usapickleball.org/docs/Equipment-Standards-Manual.pdf);
- [current USA Pickleball approved ball list](https://equipment.usapickleball.org/view/ball-list/);
- [USA Pickleball PBCoR 0.43 requirement](https://equipment.usapickleball.org/pbcor/);
- [measured pickleball trajectory model](https://journals.sagepub.com/doi/10.1177/17479541251365200);
- [free-flight outdoor/indoor drag and lift measurements](https://twu.tennis-warehouse.com/learning_center/pickleball/pickleball_aerodynamics.php).

## 3. Reference profile

The first calibrated profile is `outdoor-40-hole-v0`.

Nominal conditions:

| Property | Value |
|---|---:|
| Ball mass | `0.024 kg` |
| Ball diameter | `0.074 m` |
| Hole class | outdoor, 40-hole |
| Gravity | `(0, -9.81, 0) m/s^2` |
| Air temperature | `20 C` |
| Air density | `1.204 kg/m^3` |
| Wind | `0 m/s` |
| Court | rigid acrylic reference surface |
| Physics frequency | `120 Hz` |
| Control frequency | `60 Hz` |

Mass and diameter already sit inside the official ball limits and remain
unchanged unless evidence requires a new named profile. Environmental
conditions are nominal simulation conditions, not claims about every real
venue.

## 4. Geometry gate

The following `env-v0` geometry remains normative:

- court: `13.4112 m` long by `6.0960 m` wide;
- non-volley-zone depth: `2.1336 m` per side;
- net: `0.9144 m` at the sidelines and `0.8636 m` at centre;
- ball: `0.074 m` diameter.

The net collider must extend across the regulation `6.7056 m` post span rather
than ending at the court sidelines. A rigid segmented collider remains
acceptable; flexible mesh and cord deformation are deferred.

The representative paddle is a legal `8 × 16 inch`
(`0.2032 × 0.4064 m`) outer envelope with a rounded rectangular hitting face,
a non-contact handle region, and nominal `16 mm` thickness. Its width plus
length equals, but does not exceed, the official `24 inch` limit; length remains
below `17 inches`. Only the hitting face may return the ball.

The paddle remains kinematic for Phase 1C. Its lack of hand/arm inertia must be
recorded as a model limitation rather than disguised through a decorative mass.

## 5. Ball-drop calibration

Create a dedicated calibration fixture independent of the gameplay court.

For the official compliance fixture:

1. use a rigid granite-reference surface;
2. set the drop apparatus to `1.981 m` above the surface and match the
   reference procedure's ball-top/centre/bottom datum;
3. release with zero linear and angular velocity;
4. record the first rebound apex at the top of the ball;
5. use nominal `21.1 C` conditions, corresponding to the official
   `70 +/- 5 F` test band.

The Equipment Standards Manual explicitly defines the rebound at the top of the
ball but does not disambiguate the release-height datum in its summary wording.
The calibration manifest must therefore cite the detailed procedure used,
record the selected datum and initial ball-centre height, and may not infer the
datum silently.

Acceptance:

- first rebound apex is between `0.762 m` and `0.864 m`;
- time of first impact is within `0.01 s` of the gravity-only reference for the
  recorded initial ball-centre height;
- horizontal drift is at most `0.01 m`;
- total mechanical energy does not increase across the impact;
- the result is deterministic within committed replay tolerances.

Court rebound is a separate calibration. It requires either project-owned
physical capture on the chosen acrylic surface or a published trace with
equivalent conditions. The physical reference artifact and its uncertainty
must be committed. The official granite interval may be used as a provisional
sanity bound but may not be presented as acrylic-court validation.

## 6. Aerodynamic model

Unity `Rigidbody.linearDamping` is not the authoritative flight model in
`env-v1`.

At every physics tick, relative air velocity is:

```text
v_air = v_ball - v_wind
```

Quadratic drag is:

```text
F_drag = -0.5 * rho * Cd * area * |v_air| * v_air
area = pi * radius^2
```

Spin lift is:

```text
spin_parameter = radius * |omega_perpendicular| / max(|v_air|, epsilon)
F_lift = 0.5 * rho * Cl(spin_parameter, spin_sign) * area * |v_air|^2
         * normalized(cross(omega, v_air))
```

Requirements:

- `Cd`, the signed `Cl` fit, air density, wind, and angular-decay parameters
  live in versioned configuration, not scene objects;
- the initial drag search range is `0.25`–`0.35`, centred on the published
  outdoor-ball estimate near `0.30`;
- topspin and backspin may use different fitted lift curves when supported by
  evidence;
- zero spin must not produce synthetic Magnus lift;
- aerodynamic forces must remain finite at zero or very low speed;
- the same inputs must produce the same force before integration.

The final coefficients are selected by trajectory fit, not by the initial
search range.

## 7. Flight-trajectory calibration

The committed reference dataset must include at least:

- six zero-spin trajectories spanning `5`–`15 m/s`;
- three topspin and three backspin trajectories;
- spin samples at approximately `5` and `10 revolutions/s`
  (`31.42` and `62.83 rad/s`);
- at least one low arc, one medium arc, and one high arc;
- initial position, velocity, spin, environment, timestamps, and provenance.

For every trace, compare simulated and reference ball-centre positions at the
reference timestamps.

Acceptance:

- RMS position error no greater than `0.15 m`;
- maximum position error no greater than `0.30 m`;
- landing-point error no greater than `0.20 m`;
- flight-time error no greater than `0.05 s`;
- terminal classification agrees with the reference;
- topspin and backspin deflect in the physically correct directions;
- a vacuum/no-aerodynamics control is recorded to show that calibration is
  measuring an actual aerodynamic improvement.

If the source dataset's stated uncertainty is wider than a threshold, the
threshold must widen explicitly in a new decision rather than silently passing.

## 8. Paddle-contact calibration

Unity material bounciness is an implementation parameter, not a certified
Paddle/Ball Coefficient of Restitution measurement.

Create a versioned project surrogate for the current USA Pickleball PBCoR
protocol. It must record ball model, impact speed, impact position, paddle
fixture, incoming/outgoing velocity, spin, and effective restitution.

Acceptance:

- effective PBCoR never exceeds the current `0.43` limit;
- until measured reference-paddle data is committed, use a conservative project
  target of `0.40 +/- 0.03`, explicitly labelled as an engineering target
  rather than USA Pickleball certification;
- a stationary paddle does not add mechanical energy;
- normal impacts at relative speeds of `5`, `10`, and `15 m/s` are monotonic;
- off-centre and oblique impacts remain finite and left/right symmetric;
- moving-paddle cases at `0`, `2`, `4`, and `6 m/s` produce monotonic outgoing
  speed without unexplained energy gain;
- friction/spin transfer is measured rather than inferred from a Unity
  coefficient.

The simulator must not claim that this surrogate certifies a commercial paddle.

## 9. Court and net contacts

Court-contact evidence must include vertical, shallow-angle, and spun impacts.
Acceptance covers:

- first rebound height and outgoing speed against the physical/reference trace;
- no numerical sticking or repeated logical contacts;
- finite spin transfer and decay;
- correct in, kitchen, line, and out classification;
- no energy gain beyond the committed solver tolerance.

Net evidence must include clean clearance, tape-height contact, body contact,
sideline/post-span contact, and continued flight. The rigid net may dissipate
energy but must not act as an active spring.

## 10. Determinism and stability

Keep manual scripted simulation at 120 Hz, continuous collision detection, and
the existing reset/event contract unless before/after evidence accepts a
change.

Required tests:

- EditMode tests for force direction, magnitude, zero-speed behavior,
  coefficient serialization, and geometry;
- PlayMode tests for official drop, court rebound, flight traces,
  paddle-contact fixtures, net contacts, reset, and replay;
- the existing Phase 0 regression suite, migrated only where `env-v1`
  intentionally changes behavior;
- at least 10,000 seeded calibrated episodes without NaN, infinity, state leak,
  unclassified terminal, or contact tunnelling.

Performance must remain at least:

- `500` action steps/s in the Editor readiness fixture;
- no more than `4096` managed bytes/action;
- no regression greater than `25%` from the Phase 1A source-exact throughput
  without an accepted performance trade-off.

## 11. Versioning and policy-evaluation hygiene

`env-v0`, `phase1a-protocol-v0`, and their evidence remain immutable.

Physics fitting must not optimize the Phase 1A heuristic's reward or held-out
success rate. It uses physical calibration fixtures and dedicated calibration
seeds. The old held-out set may be rerun only after `env-v1` coefficients freeze,
and its result is labelled a cross-environment regression rather than a
continuation of the old benchmark.

Before Phase 1C training:

- create a new protocol whose environment dependency is `env-v1`;
- raise observation spin scales if the calibrated envelope exceeds the current
  `50 rad/s` scale;
- allocate a new untouched final-evaluation seed range;
- record the new reward mapping and baseline hashes;
- do not evaluate the new final seed range until a checkpoint and experiment
  configuration are frozen.

## 12. Evidence artifacts

Phase 1B closing evidence belongs under:

```text
docs/evidence/phase1b/
  summary.json
  calibration-manifest.json
  ball-drop.jsonl
  flight-traces.jsonl
  paddle-contact.jsonl
  court-net-contact.jsonl
  tests/
```

The summary identifies:

- verified source commit and `env-v1` tag;
- Unity version, platform, hardware, physics-settings hash, and configuration
  hash;
- source URLs or local reference-artifact hashes;
- fitted coefficients with uncertainty;
- every acceptance result and any limitation;
- SHA-256 hashes of all closing artifacts.

## 13. Exit criteria

Phase 1B closes only when:

1. the geometry gate passes;
2. official ball-drop acceptance passes;
3. court rebound has a committed physical or equivalent published reference;
4. all flight traces pass the error thresholds;
5. the paddle-contact surrogate passes and remains at or below PBCoR `0.43`;
6. court and net contact gates pass;
7. deterministic replay and the 10,000-episode stability gate pass;
8. readiness and allocation thresholds pass;
9. a source-exact clean checkout reproduces all tests and artifacts;
10. `env-v1` is frozen by an accepted decision and local tag;
11. the replacement Phase 1C training/evaluation protocol is prepared without
    touching its new final-evaluation seeds.

No reinforcement-learning training begins before this phase closes. A failure
to obtain sufficient physical reference data is a reported blocker, not
permission to tune by eye.
