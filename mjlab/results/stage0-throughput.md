# Stage 0 — mjlab throughput on the local machine

Date: 2026-10-02. Branch `feat/mjlab-pivot`. Script: `mjlab/scripts/stage0_throughput.sh 30`.

**Setup:**
- Hardware: RTX 4070 12 GB under WSL2 Ubuntu 22.04.
- Software: mjlab 1.6.0, mujoco-warp 3.11.0, warp-lang 1.17.0, torch 2.14.1 (CUDA 13.0), rsl-rl-lib 5.4.2.
- Task: `Mjlab-Velocity-Flat-Unitree-G1` with defaults: actor and critic `(512, 256, 128)`, 24 steps per env per iteration, 50 Hz policy (5 ms physics × decimation 4).
- Runs: 30 iterations per env count, seed 1. The first 5 iterations are excluded as warm-up.

| Envs | Steps / iteration | Mean iteration (s) | Collection (s) | Learning (s) | **Policy steps/s** | Peak GPU memory (MiB) |
|---:|---:|---:|---:|---:|---:|---:|
| 1024 | 24,576 | 0.869 | 0.752 | 0.118 | **28,274** | 3,424 |
| 2048 | 49,152 | 0.990 | 0.844 | 0.146 | **49,669** | 3,512 |
| 4096 | 98,304 | 1.359 | 1.152 | 0.207 | **72,325** | 4,394 |
| 8192 | 196,608 | 1.983 | 1.674 | 0.310 | **99,137** | 5,761 |

Peak GPU memory is whole-device usage, including roughly 2.6–3.0 GB used by Windows applications before each run. The 300-iteration smoke run at 4096 envs measured about 75k steps/s, which agrees with this table.

## Gate: ≥ 10× the Unity baseline — **PASS**

The Unity execution-v1 baseline is about 1,000 policy decisions/s (right-acquisition run: ~1.05M steps in 1,007 s, 8 workers × 16 courts).

- **By policy steps:** 28× at 1024 envs, 72× at 4096 envs, 99× at 8192 envs.
- **By simulated time (caveat):** a step is not the same amount of simulated time in both systems. An mjlab step is 20 ms. A Unity decision spans 12 physics ticks, which is 100 ms at 120 Hz or 50 ms at 240 Hz; I didn't re-verify the V3 tick rate. Counting simulated seconds per wall second, the gain is roughly **14–29× at 4096 envs** and **20–40× at 8192 envs**. The gate passes under either measure.
- **What isn't measured yet:** this is an empty flat-ground scene. A pickleball scene adds a ball, a paddle and court contacts, and fast paddle impacts may need a smaller timestep (Stage 1). Throughput must be re-measured there.

## Notes
- Throughput scales sub-linearly with env count: collection time rises slowly, so larger batches are cheap. 8192 envs fits comfortably in memory. Stage 1 and 2 tasks may cost more per env.
- WSL RAM (15 GB cap) was not a constraint in these runs.
