# Picklebot Physics Museum

Status: **Interactive feel-check tool for `env-v1`**

The Physics Museum makes the current calibrated simulator tangible before
trainer integration. It is deliberately a view and control layer over the real
`PicklebotEnvironmentV1`; it does not own or replace ball, paddle, court, or net
physics.

Open `Assets/Picklebot/Scenes/PhysicsMuseum.unity` and enter Play Mode.

## Stations

| Key | Station | What to inspect |
|---|---|---|
| `1` | Ball drop and rebound | Official-height release, first court impact, real Unity-physics rebound, fixture-measured rebound apex, drift, and energy ratio |
| `2` | Spin flight | Source-identical zero-spin, `+10 rps` topspin, and `-10 rps` backspin trajectories retained together |
| `3` | Court bounce | Oblique spun impact, real Unity-physics rebound, incoming/outgoing velocity, spin, and fixture-measured rebound |
| `4` | Paddle brush | Tangential paddle motion creating observable topspin, backspin, or sidespin |
| `5` | Net interaction | Toggleable clean clearance and tape/body-contact cases through the regulation post-span net |
| `6` | Free hit | Hands-on regulation court using the same numeric action and observation contract intended for the agent |

The drop and court-bounce stations run the live environment through its first
floor contact. The episode record then remains terminal, as required by the
training contract. The museum continues the same visible Rigidbody through the
same Unity collider, physics material, aerodynamic forces, gravity, and spin
decay until the first rebound apex. It does not create a duplicate ball. The
cyan marker and numeric measurements still come from the committed calibration
fixture. The net station combines its live episode with the matching fixture.

## Mac controls

| Input | Effect |
|---|---|
| `1`–`6` | Select station |
| `Space` | Launch or restart the selected station |
| `R` | Reset to the selected station's release state |
| `P` | Pause or resume |
| `[` or `]` | Cycle `0.25x`, `0.5x`, and `1x` playback |
| `V` | Toggle the net clearance/contact variant |
| Mouse/trackpad click-drag | Move the paddle across the visible horizontal/vertical target plane and create brush velocity |
| `W` / `S` | Move paddle in depth |
| `Q` / `E` | Pitch paddle |
| `A` / `D` | Yaw paddle |
| `Z` / `X` | Roll paddle |

The on-screen buttons mirror station selection, launch, reset, pause, speed,
and variant controls. Clicking or dragging only affects the paddle in the two
manual stations.

## What is displayed

- live `env-v1` seed, scenario, state, tick, and simulation time;
- ball velocity, speed, angular velocity, spin in rad/s and rps;
- paddle linear and angular velocity;
- event/contact count and most recent contact;
- colored trajectory overlays and spin-axis line;
- station-specific rebound, court-impact, or net-contact measurements.
- a clear `REAL UNITY PHYSICS REBOUND` label while the museum continuation runs.

Trajectory colors in the spin comparison are yellow for zero spin, coral for
topspin, and cyan for backspin. Cyan standalone markers show measured rebound
apices. Contact markers are presentation objects only.

## Interpretation boundary

The museum answers “does this look and feel like a credible learning
environment?” It is useful for spotting wrong scale, floaty gravity, implausible
drag/lift, dead spin, strange bounce, paddle-control difficulty, and bad net
geometry.

It does **not** close empirical calibration. Visual judgment is affected by
camera perspective, playback speed, display refresh, and human expectation.
Calibration claims still require the versioned numeric fixtures, source data,
tolerances, automated tests, and evidence specified in
`PHASE1B_PHYSICS_CALIBRATION_SPEC.md`.

The assembly boundary enforces this distinction:

- `Picklebot.Core` and `Picklebot.Simulation` remain authoritative;
- `Picklebot.Museum` may call the simulator, render observations, and continue
  the real ball after the terminal episode record for inspection;
- simulator assemblies do not reference museum controls or presentation.
