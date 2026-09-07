# Full-size pickleball inspection

Status: provisional manual environment. No new training has started.
Reference: outdoor 40-hole ball on an acrylic hard court.
Version: `pickleball-inspection-v1-provisional`.

## Start the scene

1. Open `Assets/Picklebot/Scenes/PickleballInspection.unity`.
2. Press Play in Unity.
3. Click the Game tab. Click a preset button or press a number from 1 to 7.
4. Press Space to pause or resume. Press R to restart the selected preset.

The scene starts paused. A preset starts its simulation. The ball continues
after contact and after a rule fault. Each run has a 20-second limit. This
limit does not reset the ball or correct its path. Reset starts a new run.

## Controls

| Control | Function |
|---|---|
| Arrow keys | Move the selected paddle in world X/Z |
| Q / E | Move the paddle down / up |
| I / K | Rotate about world X: pitch |
| J / L | Rotate about world Y: yaw |
| U / O | Rotate about world Z: roll |
| W / A / S / D | Move the selected player ground marker in world X/Z |
| Tab | Select the orange or blue paddle |
| C | Select court, paddle, or ball camera |
| Space / R | Pause or resume / restart preset |
| Slow motion button | Select quarter speed or normal speed |
| Export measurements | Save the current run as JSON |

The fixed-stroke option applies only to presets 3–5 and the orange paddle.
Clear this option for manual inspection. The fixed stroke is not an AI model.
The blue paddle does not automatically return the ball.

## Presets

| Key | Preset | Purpose |
|---|---|---|
| 1 | Court drop | Drop with the bottom of the ball 1 m above the court |
| 2 | Angled bounce | Inspect horizontal speed loss and rebound direction |
| 3 | Flat strike | Inspect a moving paddle contact |
| 4 | Brush up | Inspect upward tangential motion and spin transfer |
| 5 | Brush down | Compare the opposite brush direction |
| 6 | Serve and rules | Inspect diagonal serve landing and rally legality |
| 7 | Granite reference | Drop with the bottom of the ball 1.9812 m above a slab |

The granite preset disables the court collider. It does not combine two
overlapping contact materials. The chosen release-height datum is an explicit
assumption, not certification evidence. Both ball-bottom and ball-top rebound
heights are reported. The other presets do not apply rally rules.

## Geometry and physical limits

The court is 6.096 m wide and 13.4112 m long. The kitchen extends 2.1336 m
from the net on each side. Net-height targets are 0.8636 m at the centre and
0.9144 m at the sidelines. The existing net uses four box segments, not a
deformable net. Court dimensions include the outside boundary lines.
These dimensions follow the [USA Pickleball rules summary](https://usapickleball.org/rules/summary/).

The ball is 74 mm in diameter and has a mass of 24 g. Paddle outer dimensions
are 203.2 × 406.4 × 16 mm, including the handle. The face has rounded corners.
The ball geometry is a sphere; its 40 holes are represented by provisional
aerodynamic coefficients, not individual mesh holes. Equipment dimensions and
the granite rebound reference come from the
[USA Pickleball equipment manual](https://equipment.usapickleball.org/docs/Equipment-Standards-Manual.pdf).

The ball is a dynamic rigid body. Paddles are kinematic rigid bodies controlled
through position and rotation targets. The local physics step is 1/240 s.
The scene reuses `SimulationConfigV1`, `AerodynamicModelV1`, and
`PaddleSpinTransferV1`. The last model adds a bounded contact-based spin and
tangential-velocity change after the collision solver. It is an explicit,
provisional contact model; it does not steer the ball to a target.

Motor limits are design assumptions, not measured human limits:

- Paddle speed: 5 m/s. Translation acceleration: 24 m/s².
- Angular speed: 6 rad/s. Angular acceleration: 30 rad/s².
- Paddle centre height: 0.25–2.5 m. Horizontal reach: 1.15 m from the marker.
- Player speed: 3 m/s. Player acceleration: 12 m/s².
- Player ground-disc radius: 0.22 m. Players remain on their own side.

## Rules and limits

The serve must land diagonally beyond the kitchen line. The receiver must
allow the serve to bounce. The server must allow the return to bounce. After
these two bounces, legal volleys are permitted. Wrong-side landings, out
landings, and second bounces end the rule state. A net touch alone is not a
fault. The ball must still land legally. Physics continues after a fault.

A ground disc represents each player's feet. A volley from the kitchen is a
fault. Entry into the kitchen after a volley is also flagged until the marker
has stopped outside it for 0.2 seconds. This is a limited momentum proxy.
It does not model feet, jumping, body contact, equipment touching the kitchen,
or all officiating exceptions. Repeated paddle hits are treated as faults.
There is no match scoring or full service-action validation. The serve preset
launches the ball after a scripted strike.

## Measurements and verification

The export button writes `artifacts/inspection/inspection-<UTC>.json`.
It includes configuration text and hash, the preset, first rebound height,
ball position/velocity/spin at 240 Hz, and contact records. Each contact has
a point, normal, pre-step velocity/spin, and post-solver/contact-model values.
The incoming values are sampled before the physics step, not at an exact
sub-step contact time. Exports are marked `empiricalCalibration: false`.

The current court-drop simulation gives about 0.395 m of first rebound from
a 1 m release, measured to the ball bottom. This is about 39.5% in height.
It is not a claim that all outdoor balls rebound by that amount on acrylic.
Height ratio and velocity restitution are different quantities; without air
drag, the height ratio is approximately the square of restitution.

Unity test assemblies:

- `Picklebot.Inspection.Tests`: serve, bounce, volley, and kitchen rule states.
- `Picklebot.Inspection.PlayTests`: visible construction, geometry, drop
  continuation, six paddle axes, motor limits, physical contacts, brush spin,
  serve landing, granite isolation, trace export data, and reset repeatability.

`Picklebot.Inspection.Editor.InspectionEditor.Verify()` records all seven
presets during Play Mode. The report is `artifacts/inspection/verification.json`.
It includes hashes of the Inspection, Core, and Simulation C# source files.
The old competition and cooperative evidence remains separate.
Run `python3 scripts/inspection-verify.py` to check the retained report against
current source hashes, test results, and preset outcomes.

## Next calibration gate

1. Record the ball make, model, condition, temperature, and court surface.
2. Measure repeated drops at known heights. Use a fixed camera and a scale.
3. Measure angled rebounds and horizontal speed loss.
4. Measure flight decay and flat/brush paddle contacts with known motion.
5. Fit the provisional parameters. Reserve separate trials for validation.
6. Freeze geometry, contact models, motor limits, rules, and observations.
7. Train a single legal return first. Then train competitive play.

Passing these simulated tests does not close the empirical Phase 1B gate.
Do not use the previous table-scale trained models as full-size pickleball
validation. No cloud machine is required for this inspection work.
