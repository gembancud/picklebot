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
- off-centre, oblique, symmetry, and numeric spin-transfer measurements;
- vertical, shallow, and spun provisional court impacts;
- net clearance, tape, body, and outside-court/inside-post-span contacts;
- deterministic replay;
- a 10,000-episode calibrated soak with no invalid numeric state, state leak,
  unclassified terminal, or detected net tunnelling;
- readiness above both the absolute and Phase 1A regression thresholds;
- a replacement `phase1c-protocol-v0` bound to `env-v1`, with an `80 rad/s`
  spin scale and new reserved seed partitions;
- no API that can construct a Phase 1C final-evaluation request before
  checkpoint and experiment freeze.
- strict empirical flight, acrylic-court, and official-drop input schemas;
- a provenance validator that rejects simulator-generated calibration data;
- an independent deterministic RK4 coefficient fitter with vacuum control and
  bootstrap uncertainty;
- an acrylic response-target summarizer;
- a non-mutating close audit covering source, artifacts, hashes, tag, and
  final-seed hygiene.

Current source-exact checkpoint suites:

- combined Phase 0, Phase 1A, and Phase 1B EditMode: `50/50` passing;
- Phase 1B regular PlayMode: `13/13` passing;
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

No RL trainer installation or training is authorized before those gates close.

The empirical tooling is covered by `scripts/phase1b-empirical-test.sh`.
`scripts/phase1b-close-audit.sh` is intentionally red until the reference
bundle, fitted configuration, closing evidence, clean source commit, and
accepted `env-v1` tag all exist.

## Current external package target

The Phase 1C protocol records the current stable release pair verified on
`2026-07-26`:

- Unity: `com.unity.ml-agents@4.0.0`;
- Python: `mlagents==1.1.0`.

The older Phase 1A historical constant `com.unity.ml-agents@4.0.3` remains
immutable but must not be used as the Phase 1C install target. No trainer package
is installed during Phase 1B.
