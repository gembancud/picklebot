# Phase 1B empirical reference acquisition

These inputs are required to turn the working `env-v1` implementation into a
closed physics calibration. Simulator output cannot substitute for them.

The machine-readable schemas and
[`scripts/phase1b_empirical.py`](../../../scripts/phase1b_empirical.py)
enforce this boundary. A trace whose provenance is
`simulator-generated` is rejected even if its numerical errors are small.
The closing summary and fitted manifest also have dedicated schemas, so a
single `closeEligible` flag cannot stand in for the eleven exit gates.

## Preferred acquisition order

1. Request the raw `(time, x, y)` trajectory exports and launch metadata from
   the authors of the cited measured studies. This is the lowest-equipment and
   lowest-storage route.
2. Obtain a published or laboratory trace for a named outdoor ball on a named
   rigid acrylic court system.
3. If suitable raw data cannot be obtained, perform project-owned captures
   using the schemas in this directory.

Do not digitize a plotted figure and silently treat it as raw measurement.
Figure digitization is acceptable only as an explicitly named lower-authority
dataset with a quantified digitization error and an accepted threshold change.
Draft source and standards-authority requests are available in
[`request-templates.md`](request-templates.md).

## Normalized coordinate contract

Coordinate exports must be transformed to `picklebot-world-v1` before fitting:

- metres and seconds;
- right-handed Unity coordinates;
- `y` is vertical and positive upward;
- `z` follows the court length, with the far court at positive `z`;
- `x` follows court width;
- court centre is `(0, 0, 0)`;
- all positions describe the ball centre;
- angular velocity is in radians per second.

The original untransformed export remains the raw artifact. Record separate
SHA-256 hashes for the raw artifact and normalized coordinate export.

## Flight capture minimum

- one named ball model from the current approved outdoor-ball list;
- ball mass, diameter, hole count, and sample identifier;
- a marked ball whose rotation can be measured;
- a repeatable launcher capable of approximately `5` to `15 m/s`;
- two synchronized high-frame-rate cameras or an equivalent calibrated
  trajectory system;
- a calibrated measurement plane and scale;
- recorded frame rate, temperature, air conditions, wind, and uncertainty;
- at least six zero-spin traces, three topspin traces, and three backspin
  traces;
- samples near `31.42` and `62.83 rad/s`;
- low, medium, and high arcs;
- raw video hashes and exported coordinate hashes.

Record ball-centre coordinates. Do not mix top-of-ball and centre coordinates.
The validator treats “approximately `5`–`15 m/s`” as at least one launch no
faster than `5.5 m/s` and one launch no slower than `14.5 m/s`. Each required
spin point must be within `pi rad/s` (`0.5 rps`) of `31.42` or `62.83 rad/s`.
Changing those tolerances requires an explicit spec decision.

## Acrylic-court capture minimum

- named acrylic surface system, base construction, location, and condition;
- named approved outdoor ball and sample identifier;
- temperature and humidity;
- perpendicular high-frame-rate camera, fixed scale, and level surface;
- vertical, shallow-angle, and spun impacts;
- incoming and outgoing ball-centre positions, velocities, and spin;
- at least five trials per case so mean, spread, and outliers are visible;
- raw video and coordinate-export SHA-256 hashes.

The official granite drop interval may be recorded beside these results, but it
does not validate the acrylic court.

## Official drop procedure

The summary Equipment Standards Manual states a `78 inch` release and a
`30-34 inch` rebound measured at the top of the ball, but its summary wording
does not identify whether the release apparatus datum is the ball top, centre,
or bottom. Before close, commit either:

- a detailed current official procedure that resolves the datum; or
- written clarification from the standards authority, with date and source.

Until then the project fixture records `BallTop` as an explicit provisional
choice and may not claim official certification.

The accepted clarification is normalized into
[`official-drop.schema.json`](official-drop.schema.json). The recorded
ball-centre height must agree mathematically with the cited ball-top, centre,
or bottom release datum.

## Expected committed inputs

```text
docs/reference/phase1b/
  flight/
    manifest.json
    traces.jsonl
    raw/
  acrylic-court/
    manifest.json
    impacts.jsonl
    raw/
  official-drop/
    procedure-or-clarification.*
```

Large raw videos need not live directly in Git if repository size becomes
unreasonable. Store them in a stable project-controlled location and commit a
manifest containing immutable URLs, byte sizes, and SHA-256 hashes. Coordinate
exports and all fitting inputs must remain locally reproducible.

Use the JSON schemas in this directory before fitting. A fitting script must
reject missing provenance, units, timestamps, uncertainty, or hashes.

## Validation and fitting commands

The tooling uses only the Python standard library, so it can run from the
existing machine or a minimal Conda environment without installing trainer
packages:

```bash
scripts/phase1b-empirical-test.sh

python3 scripts/phase1b_empirical.py validate

python3 scripts/phase1b_empirical.py fit-flight \
  --bootstrap 50 \
  --output artifacts/phase1b/fitting/flight-fit.json

python3 scripts/phase1b_empirical.py fit-court \
  --output artifacts/phase1b/fitting/acrylic-targets.json
```

The flight fit uses an independent `480 Hz` RK4 integrator, fits `Cd`, the
signed-spin lift slope, and angular decay, records a vacuum control, evaluates
every normative trajectory threshold, and estimates coefficient uncertainty
with a deterministic stratified bootstrap. Acrylic fitting produces measured
normal-restitution, tangential-speed, and spin-transfer targets; Unity contact
parameters still have to be searched and replayed against every trace.

Run the non-mutating final audit at any time:

```bash
scripts/phase1b-close-audit.sh
```

It is expected to fail while Phase 1B is active. It checks the empirical bundle,
non-provisional configuration, closing artifacts and hashes, clean source
commit, `env-v1` tag, and Phase 1C final-seed hygiene.
