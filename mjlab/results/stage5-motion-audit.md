# Stage 5 motion audit: what holds the robot in place

Date: 2026-10-05. Task `Picklebot-Aim-All-G1` with the accepted Stage 4 checkpoint `aim-all-c01/model_7600`. Script: `scripts/motion_audit.py`; the term dump and measurements are in `stage5-motion-audit.json`. No training was done.

## How far the robot moves now (dev seed 4,200,070; 1024 envs × 16 s; 3,072 robot episodes, 6,852 feeds)
| Measure (per robot episode, ≤ 8 s) | p50 | p90 | p99 | max |
|---|---:|---:|---:|---:|
| Pelvis max displacement from episode start | 0.05 m | 0.14 m | 0.27 m | 0.41 m |
| Pelvis xy path length (includes sway) | 0.45 m | 0.65 m | — | — |
| Foot xy path length (each foot) | 0.11 m | 0.29 m | — | 0.94 m |

Contact rate in this rollout: 89.3 %. The robot essentially does not step: half the episodes move the pelvis less than 5 cm, and most foot motion is shuffling under 30 cm. Every ball is reached by leaning and reaching from the start spot.

## Terms that touch base motion (inherited from mjlab's G1 velocity task unless noted)
| Term | Weight | Effect with the zero command | Planned change (stance-release step) |
|---|---:|---|---|
| `track_linear_velocity` (std 0.5) | +2.0 | **Pays for standing still**: exp(−v²/0.25) of base xy and z speed. It pays the full 2 per step when still, and 0.04 at 1 m/s. This is the main stand-still incentive. | Remove. Stepping is driven by the ball and recovery rewards instead. |
| `track_angular_velocity` (std 0.71) | +2.0 | Pays for zero yaw rate, and for zero roll and pitch rate. Penalises turning toward the ball. | Remove. `body_ang_vel` and `angular_momentum` stay to discourage wobble. |
| `pose` (`variable_posture`) | +1.0 | Always uses `std_standing`, because the command is 0 (< walking threshold 0.05). Tight legs: hip 0.15, knee 0.2, ankle 0.1 rad. **Penalises the leg angles needed to step.** | Use the inherited walking tolerances for legs and waist (hip pitch 0.3, knee 0.35, ankle pitch 0.25 …); keep the free right arm (3.0) and left arm 0.3. Remove command dependence. |
| `foot_clearance`, `foot_swing_height`, `foot_slip`, `soft_landing` | −2.0, −0.25, −0.1, −1e-5 | **Inactive**: all are gated by command magnitude > 0.05. Steps currently get no foot-quality shaping. | Re-enable, gated by actual base speed (> 0.1 m/s) instead of the command, so that steps lift cleanly, don't slide and land softly. |
| `air_time` | 0.0 | Disabled upstream. | Leave off. |
| `upright`, `body_ang_vel`, `angular_momentum`, `dof_pos_limits`, `self_collisions`, `action_rate_l2` | +1.0, −0.05, −0.02, −1.0, −1.0, −0.1 | Balance and smoothness; neutral to stepping. | Keep. |
| `twist` command | — | Zero for all envs, curriculum removed (Stage 2 fix). | Keep zero (now unused by rewards; still observed). Recovery uses its own command (recovery step). |
| `approach_ball` (picklebot) | +2.0 | Rewards the paddle closing on the ball. This is the only pull toward the ball. | Keep; it now becomes a stepping incentive. |
| `reset_base` event | — | Start pose ±0.05 m, yaw ±0.1 rad around `ROBOT_START`. | Random start box (reach-families step). |
| `fell_over` termination (tilt > 70°) | — | The only failure termination. | Keep. Falls per robot episode are a Stage 5 gate metric. |
| `push_robot` event | — | Removed in Stage 2. | Leave out for now (robustness is Stage 6). |

## Conclusion
- **The robot stands still because it is paid to.** Of 2 + 2 per step, the velocity-tracking pair pays the most for holding still. The leg posture term then penalises the joint angles a step needs.
- **The foot-quality penalties that would shape good steps are switched off** by the zero command.
- The stance-release step removes the two tracking terms, loosens leg and waist posture to the walking tolerances, and re-gates the four foot terms on actual base speed.
- Balance terms, the fall termination and the ball rewards stay.
