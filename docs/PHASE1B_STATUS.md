# Phase 1B implementation status

Status: **Active; not closed**

Updated: `2026-07-27`

Normative direction:
[PHASE1B_PHYSICS_CALIBRATION_SPEC.md](PHASE1B_PHYSICS_CALIBRATION_SPEC.md).
This status file reports implementation progress only. It does not relax or
replace any exit criterion.

## Implemented and passing in the current worktree

- `env-v1` versioned configuration for the `outdoor-40-hole-v0` profile;
- regulation court, ball, post-span net, and legal `8 x 16 inch` paddle
  geometry;
- convex rounded-rectangle hitting-face collision mesh and non-contact handle;
- explicit gravity, quadratic drag, signed spin lift, angular decay, and zero
  Unity rigidbody damping;
- independent RK4 reference integration;
- isolated granite drop, paddle, court, and net fixtures;
- normal paddle impacts at `5`, `10`, and `15 m/s`;
- moving-paddle impacts at `0`, `2`, `4`, and `6 m/s`;
- a parameterized residual-slip paddle surrogate with nonzero, symmetric,
  finite spin transfer, a `35 rad/s` per-contact delta cap, and an `80 rad/s`
  total ball-spin cap;
- integrated upward/downward brush coverage through the real `env-v1` step and
  collision path;
- vertical, shallow, and spun provisional court impacts;
- net clearance, tape, body, and outside-court/inside-post-span contacts;
- deterministic replay;
- a 10,000-episode calibrated soak with no invalid numeric state, state leak,
  unclassified terminal, or detected net tunnelling;
- readiness above both the absolute and Phase 1A regression thresholds;
- a replacement `phase1c-protocol-v0` bound to `env-v1`, with an `80 rad/s`
  spin scale and new reserved seed partitions;
- a concrete 37-value `phase1c-observation-v0` encoder that rejects legacy
  environment state and uses that `80 rad/s` spin scale;
- no API that can construct a Phase 1C final-evaluation request before
  checkpoint and experiment freeze;
- strict empirical flight, acrylic-court, and official-drop input schemas;
- a provenance validator that rejects simulator-generated calibration data;
- an independent deterministic RK4 coefficient fitter with vacuum control and
  bootstrap uncertainty;
- an acrylic response-target summarizer;
- a non-mutating close audit covering source, artifacts, hashes, tag, and
  final-seed hygiene.

Current source-exact checkpoint suites:

- combined Phase 0, Phase 1A, and Phase 1B EditMode: `56/56` passing;
- Phase 1B regular PlayMode: `14/14` passing;
- Phase 1B provisional evidence generator: `1/1` passing;
- Phase 1B 10,000-episode calibrated soak: `1/1` passing.

These are checkpoint results, not Phase 1B closing evidence. The final
source-exact run must refresh them after the configuration and tag freeze.

## Provisional evidence only

Development evidence is generated under:

```text
artifacts/phase1b/provisional/
artifacts/phase1b/soak/
```

It is intentionally ignored by Git and, by default, records
`sourceCommit: uncommitted`. When the runner receives
`PICKLEBOT_SOURCE_COMMIT`, it records that exact checkpoint commit instead;
this improves reproducibility but does not promote the artifacts to closing
evidence. Model-derived flight checks use published coefficients but are not
measured reference trajectories. They are marked:

```text
qualifiesForEmpiricalClose: false
```

No provisional artifact may be copied into `docs/evidence/phase1b/` or cited as
closing evidence merely because it passes a numerical threshold.

## Open exit gates

Phase 1B remains open until all of these are resolved:

1. commit raw measured or published flight coordinates meeting the required
   zero-spin, topspin, backspin, speed, and arc coverage;
2. commit project-owned or equivalent published acrylic-court rebound traces;
3. cite the detailed official drop procedure and resolve its release-height
   datum;
4. fit the final coefficients and change the configuration from
   `provisional-unfitted` only after the empirical gates pass;
5. regenerate all closing evidence from a clean checkout at one exact commit;
6. run the complete Phase 0, Phase 1A, and Phase 1B verification chain;
7. accept the freeze decision, create the local `env-v1` tag, and verify the
   tag reproduces every closing artifact;
8. keep the new Phase 1C final-evaluation seeds untouched.

D-023 now authorizes a bounded Phase 1C0 diagnostic-training exception while
these gates remain open. It does not change any gate above: the simulator stays
`provisional-unfitted`, final-evaluation seeds stay untouched, and every
Phase 1C0 checkpoint is disposable after any physics/configuration change.
Substantive Phase 1C evaluation and closure remain unauthorized until Phase 1B
closes.

The empirical tooling is covered by `scripts/phase1b-empirical-test.sh`.
`scripts/phase1b-close-audit.sh` is intentionally red until the reference
bundle, fitted configuration, closing evidence, clean source commit, and
accepted `env-v1` tag all exist.

## Practical spin-refinement boundary

The paddle can now generate spin from tangential surface motion. The model
uses residual paddle-versus-ball contact slip after Unity resolves the normal
collision, transfers `0.12` of that slip into tangential ball velocity and
`0.35` into ball angular velocity, and applies committed deadband and safety
caps. Equal-and-opposite brush actions are verified to produce opposite spin in
both the pure model and the actual environment contact path.

This is intentionally a useful pre-training proxy, not a claim of precise
paddle-face friction, dwell time, deformation, sweet-spot response, or
commercial-paddle certification. Those effects require measured
paddle-contact traces. All coefficients are configuration-hashed so later
fitting is explicit and cannot silently rewrite the training environment.

## Current external package target

The Phase 1C protocol records the current compatible line, reverified from the
live Unity registry, installed package metadata/changelog, upstream Release 23
source, and communicator version on `2026-07-27`:

- Unity: `com.unity.ml-agents@4.0.3` (communicator `1.5.0`);
- Python: PyPI `mlagents==1.1.0`, with native Conda `grpcio==1.48.2` on
  Apple Silicon.

The Phase 1A `4.0.3` selection remains immutable historical text. It was
premature when selected, but the version is now actually present in the Unity
registry and contains the Unity 6.5 compatibility fixes. D-023, rather than the
historical selection, authorizes its current use.
