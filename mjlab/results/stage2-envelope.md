# Stage 2 — G1 + wrist paddle: reach and swing-speed envelope

Date: 2026-10-02. Script: `mjlab/scripts/stage2_envelope.py --samples 20000 --swings 400` (seed 0). Raw: `stage2-envelope.json`.

## Model
- mjlab's bundled Unitree G1 (29 DoF, 33.56 kg incl. paddle) with mjlab's position actuators. Shoulders, elbow and wrist roll are 5020 motors (25 N·m); wrist pitch and yaw are 4010 motors (5 N·m). PD gains are set from a 10 Hz natural frequency.
- Paddle (`picklebot_mj/g1_paddle.py`): child of `right_wrist_yaw_link`, handshake grip. The handle is centred on the `right_palm` site and the face extends along the hand axis with its normal along the palm normal (wrist +y). Unity dimensions (face 0.2032 × 0.2794 × 0.016 m, handle 0.127 m); mass 0.22 kg. The body origin is the face centre, so its pose feeds `ball_sim.PaddleState` directly. Geoms are visual only.
- Measurement setup: fixed pelvis at the knees-bent standing height (0.76 m), gravity on, timestep 2 ms. No balance or reaction on the base; legs held at the keyframe.

## Reach (20,000 uniform samples of 7 right-arm + 3 waist joints within limits)
| Quantity | Value |
|---|---|
| Max horizontal distance of the face centre from the pelvis axis | **0.89 m** (95th percentile 0.70 m) |
| Max forward / right / left | 0.85 / 0.86 / 0.79 m |
| Face-centre height range | 0.30 – 1.73 m (5–95 %: 0.60 – 1.47 m) |

For reference, a regulation net is 0.86–0.91 m high. Standing still, the G1 covers roughly a 1.7 m wide band; wider balls need footwork (Stage 3).

## Swing speed (400 random pose-to-pose step commands on the 7 arm joints, 0.4 s window)
| Quantity | Value |
|---|---|
| Peak face-centre speed, max | **14.0 m/s** |
| 95th percentile / median | 10.3 / 5.7 m/s |
| Peak speed along the face normal, max (95th percentile) | **12.0 m/s** (9.0) |

With the paddle COR of 0.40, a 12 m/s normal swing sends a stationary ball out at about 17 m/s. That is drive pace for pickleball; dinks and resets need far less. The Unity constrained body was capped at a 12 m/s hand speed (D-037).

## Caveats
- These are **lower bounds on capability**: uncoordinated random targets, no waist or leg drive, no optimisation. A trained policy can sequence joints (kinetic chain) for more speed.
- **Upper-bound caveats:** fixed base (no balance cost or reaction torques on the pelvis), and mjlab's actuator model enforces torque limits but I did not verify joint velocity limits (37/22 rad/s motor specs). Free-standing swings may be slower or destabilising; Stage 2 training measures this in context.
- The paddle does not collide with the robot's body or the floor (visual only), so self-intersecting swings are possible in this measurement.

## Verdict
The G1 with this paddle is physically capable of reaching typical contact heights near the body and producing drive-speed swings. No blocker for Stage 2.
