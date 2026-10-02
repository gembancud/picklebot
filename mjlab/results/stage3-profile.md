# Stage 3 — where does training time go?

Date: 2026-10-02. Task `Picklebot-Return-Stand-G1`, 4096 envs, RTX 4070. Profiler: `mjlab/scripts/stage3_profile.py` (CUDA-synchronised timers around the ball term, the MuJoCo step/forward and the whole env step; random actions; 60 env steps after warm-up). Raw: `stage3-profile-baseline.json`.

## Env step (random actions)
| Part | ms per env step (4 physics steps) | Share |
|---|---:|---:|
| **Ball term** (`BallPhysicsAction.apply_actions`, 4×) | **125.3** | **67.9 %** |
| MuJoCo step (4×) | 24.0 | 13.0 % |
| MuJoCo forward | 5.7 | 3.1 % |
| Other managers (obs, rewards, terminations, resets, actions) | 29.6 | 16.0 % |
| **Total** | 184.7 (22.2k env steps/s) | |

## Training iteration (run return-stand-02, 723 iterations, 24 env steps each)
| Part | Mean s per iteration |
|---|---:|
| Collection (env stepping + policy inference) | **9.29** (97 %) |
| PPO learning | 0.26 (3 %) |

Collection time **rose from 5.4 s (iteration 0) to 11.2 s (iteration 722)** as the policy learned a fast swing. A trained policy costs about 390 ms per env step versus 185 ms with random actions.

## Diagnosis
`BallSim.step` chooses its sub-step count from the **batch maximum** of ball + paddle speed (`substeps_for`, with a host sync), so one fast env makes all 4096 envs sub-step more. Each sub-step runs a Python sequence of many small kernels (RK4 aero ×4 evaluations, court, net and paddle tests), with several `.any()` host syncs per sub-step. Cost therefore grows with how hard the policy swings, which is the opposite of what training wants.

## Plan (next steps of Stage 3)
1. **No host syncs:** remove `bool(x.any())`/`float(...)` branches (always compute, mask with `torch.where`); fixed sub-step count per physics step from config, sized for the maximum design speed (e.g. 40 m/s relative → ≤ 0.5 r travel), not from data.
2. **Fewer, larger kernels:** cheaper flight integration per sub-step (aero evaluated once per physics step or a semi-implicit update, if the RK4 reference tolerance still holds), fused contact tests.
3. **CUDA graphs or `torch.compile`** on the fixed-shape, sync-free step.
Gate: ≥ 2× env steps/s on the trained-policy workload, physics tests green, and `model_700` dev evaluation unchanged within its interval.
