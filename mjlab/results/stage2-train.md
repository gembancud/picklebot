# Stage 2 — first training run: standing G1 returns a fed ball

Date: 2026-10-02. Task `Picklebot-Return-Stand-G1`, code at `8b3c546` (plus evaluation diagnostics that don't change physics, observations or rewards). Evidence: `mjlab/results/stage2/`.

## Runs
| Run | Outcome | Notes |
|---|---|---|
| `return-stand-01` | **Invalid**, killed at iteration 229 (24 min) when the host slept and the WSL VM shut down | Also trained under a config bug: the inherited `command_vel` curriculum widened the command ranges (lin_vel_x up to 1.0, ang_vel_z −0.5), so the robot was not always commanded to stand. Checkpoints to `model_200.pt` kept locally; not used. |
| `return-stand-02` | **Completed** to the 7,000 s wall cap (exit 124) at iteration 722 | Curriculum removed (regression test `test_command_stays_zero`). The host was kept awake through the app. 4096 envs, mjlab G1 PPO defaults (actor/critic 512-256-128 ELU), seed 1. ~9.7 s per iteration (~10k steps/s; the Python ball term dominates, GPU ~33 % busy). About 71M env steps. |

**Selection rule:** fixed endpoint, the last saved checkpoint before the cap (`model_700.pt`). No peak selection.

## Training curve (run 02, per-episode reward terms from the training log; stochastic policy)
| Iteration | Falls / log window | Contact reward (+1 each) | Legal-return reward (+5 each) | Mean episode length (steps) |
|---:|---:|---:|---:|---:|
| 60 | 361 | 0.000 | 0.00 | 12 |
| 240 | 0.5 | 0.237 | 0.00 | 94 |
| 360 | 2.1 | 0.287 | 0.35 | 121 |
| 540 | 1.3 | 0.318 | 0.80 | 128 |
| 722 | 0.8 | 0.325 | 1.23 | 124 |

Balance came first (falls collapsed by about iteration 240), then contact, then legal returns, which were **still rising at the cap**.

## Development evaluation (deterministic policy, observation noise off)
512 envs × 9 s of sim time per seed; rates are over **completed episodes**; Wilson 95 % intervals. Dev seeds 4,200,000 and 4,200,001 (feed RNG and env seed); training used seed 1. Final seeds unused.

| Checkpoint | Seed | Episodes | Paddle contact | **Legal return** | Falls | Rally endings (non-success) |
|---|---|---:|---|---|---|---|
| `model_0` (untrained) | 4,200,000 | 2,986 | 0.2 % [0.1, 0.4] | 0.0 % [0, 0.13] | 82.9 % [81.5, 84.2] | 534 second bounce, 71 body contact, 7 out, 3 wrong side |
| `model_0` | 4,200,001 | 2,964 | 0.6 % [0.4, 0.9] | 0.0 % [0, 0.13] | 80.5 % [79.0, 81.9] | 575 second bounce, 72 body contact, 8 out, 10 wrong side |
| **`model_700`** | 4,200,000 | 1,541 | **100 %** [99.75, 100] | **96.1 %** [95.0, 97.0] | **0 %** [0, 0.25] | 31 out, 6 wrong side |
| **`model_700`** | 4,200,001 | 1,537 | **100 %** [99.75, 100] | **96.0 %** [94.9, 96.8] | **0 %** [0, 0.25] | 27 out, 8 wrong side |

(`model_700` episodes are fewer because successful episodes run until the return lands, instead of ending early in falls.)

**Stroke diagnostics** (`model_700`, seed 4,200,000; means over 1,832 first contacts):
- paddle face speed at contact **7.10 ± 0.20 m/s**: a consistent, stereotyped swing;
- ball speed in 3.32 m/s, out **11.21 m/s**; consistent with the impulse model (v_p + e·(v_p + v_in) ≈ 11.3);
- contact height 0.65 m;
- net clearance at crossing **1.40 m** (a high, safe loft; 1,583 crossings);
- legal landings at x = **4.58 ± 0.93 m** (mid-to-deep far court), |y| = 0.81 m.

**Video:** `mjlab/artifacts/stage2/return-stand-02-model_700.mp4` (local; side view, dev seed 4,200,002). Committed frames show the ball arriving (frame 25), the backswing as it nears (frame 50), and the follow-through with the ball in flight over the net (frame 75). The 4-env video renders env 0 only and shows successes; misses are characterised by the rally-ending counts above but **not yet shown on video**.

## Interpretation and limits
- On this drill, the policy reliably keeps its balance and returns a fed forehand legally: about 96 % on two dev seeds, a 2.3-point drop from 100 % contact to legal return, with failures mostly long (OUT).
- **Narrow drill.** One feed family: a single bounce, 0.30–0.65 m to the robot's right, knee-to-waist height, standing still, no aiming target. The stroke is one stereotyped loft (paddle speed std 0.2 m/s). There is no evidence yet for wider, faster, spinning or backhand feeds, footwork, placement control or rallies.
- Development seeds were reused across two evaluations of the same checkpoint. These are not final acceptance results.
- Training throughput (~10k steps/s) is limited by the Python ball term; optimising it is the clear next engineering task before longer or wider training.
