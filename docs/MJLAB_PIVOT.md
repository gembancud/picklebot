# mjlab pivot — plan and progress tracker

Branch `feat/mjlab-pivot`, worktree `F:\dev\picklebot-mjlab` (WSL: `/mnt/f/dev/picklebot-mjlab`). Started 2026-10-02 from `main` at `256d7db`.

**Goal:** train simulated robots to play pickleball using current-literature tooling: mjlab (MuJoCo Warp, GPU-parallel), rsl_rl PPO, a Unitree G1 humanoid holding a paddle. The Unity/ML-Agents work stays in this repo, frozen as a reference. It is not deleted or modified by this pivot.

**Decisions so far:**
- G1 (mjlab's bundled model) with a rigid paddle fixed to the right wrist; no finger/grip model; no scaling or limb edits.
- A body-less driven paddle rig is only a physics test fixture, never the player.
- Code lives in `mjlab/` at repo root (Python package `picklebot_mj`). It runs in WSL2 Ubuntu on the RTX 4070. Python environments live in the WSL home directory, not on `/mnt/f`.
- The evaluation discipline from `docs/DECISIONS.md` carries over: disjoint train/dev/final seeds, final seeds unused, no automatic promotion, per-skill reporting, failed results kept.

**Machine:** RTX 4070 12 GB (driver 610.47), Ryzen 7 7800X3D (8 cores), 31 GB RAM, WSL2 Ubuntu. Unity baseline throughput is about 1,000 policy steps/s (8 workers × 16 courts).

## Loop rules
1. Each iteration does **one** unchecked step below, the smallest verifiable unit. Verify it by running it, then tick it and add a dated line to the Log.
2. Commit each completed step on `feat/mjlab-pivot` (`mjlab: <what>`). Push the branch when a whole stage completes.
3. **Stop and ask the user** before:
   - any `sudo`, apt install or system or driver change;
   - touching Unity code, `Assets/`, or the `feat/hierarchical-control` checkout;
   - deleting anything;
   - a stage go/no-go decision that fails or is ambiguous;
   - any training run expected to take longer than 2 hours.
4. If blocked, record the blocker under **Open questions** and stop the loop instead of guessing.
5. Keep artifacts (logs, checkpoints, videos) under `mjlab/artifacts/`, which is gitignored. Commit only compact summaries.

## Stage 0 — toolchain and throughput trial
- [x] Record decision D-038 (switch to mjlab, G1 with wrist paddle, Unity frozen) in `docs/DECISIONS.md`, append-only.
- [x] Verify WSL2 sees the GPU (`nvidia-smi` inside Ubuntu); record CUDA and driver versions.
- [x] Install `uv` in WSL user space; create the env under `~/envs/picklebot-mj`; install mjlab (pin the exact version or commit).
- [x] Run mjlab's G1 velocity example for a short run; confirm it trains.
- [ ] Benchmark steps/s at 1024, 2048 and 4096 envs, plus GPU memory use; write `mjlab/results/stage0-throughput.md`.
- [ ] **Gate:** at least 10× the Unity baseline (≥ 10,000 steps/s) at a usable env count. Record pass or fail; ask the user if it fails.

## Stage 1 — ball and court physics (paddle rig)
- [ ] Scaffold the `mjlab/picklebot_mj` package: court geometry (lines, net, kitchen) as MJCF, plus a unit-test setup.
- [ ] Ball body (real mass/diameter) with drag and Magnus applied as forces; tests for free-flight trajectories.
- [ ] Court bounce (restitution, friction, spin) tuned against the Phase 1B reference numbers in `docs/PHASE1B_PHYSICS_CALIBRATION_SPEC.md` and the env-v1 Unity constants.
- [ ] Driven paddle rig: a paddle moved along scripted paths; impact tests across speeds, with no tunnelling at max swing speed; choose the timestep and substeps.
- [ ] **Gate:** a physics report (`mjlab/results/stage1-physics.md`) shows bounce, flight and paddle impacts within tolerance; GPU-batched throughput is still acceptable.

## Stage 2 — standing G1 hits a fed ball
- [ ] G1 plus a paddle fixed to the right wrist in the scene; reach and swing-speed envelope measured with scripted joint sweeps.
- [ ] Rules and legality module (net clearance, in/out, kitchen) ported from the Unity rules, with tests.
- [ ] Task: G1 standing (balance required), ball fed toward its forehand, reward for contact then a legal return; dev and train seed ranges defined.
- [ ] First training run (≤ 2 h) plus evaluation on dev seeds; video of successes and misses.
- [ ] **Gate:** learns legal returns on easy feeds; report written.

## Stage 3+ — later (detail when Stage 2 passes)
Movement plus hitting (using the walking policy as a base or teacher), target-conditioned returns, privileged teacher → student distillation, both service sides, then 2v2.

## Open questions
- WSL RAM is capped at 15 GB. This is probably fine for training, but check during the Stage 0 benchmark.
- Does mjlab run cleanly in WSL2 on this machine? (Stage 0)
- Can the G1's reach and swing speed produce competitive returns? (Stage 2)

## Log
- 2026-10-02 — Plan created; worktree and branch set up from `main` `256d7db`.
- 2026-10-02 — D-038 appended to `docs/DECISIONS.md`; D-001 status marked as superseded for new work. No other decision text changed.
- 2026-10-02 — WSL GPU check passed. Ubuntu 22.04.2, kernel 6.18.33.2-microsoft-standard-WSL2. `nvidia-smi` in WSL sees the RTX 4070 (12,282 MiB; ~2.6 GB already used by Windows apps): KMD 610.47, nvidia-smi 610.43.02, CUDA UMD 13.3. `libcuda.so` is present in `/usr/lib/wsl/lib`. WSL sees 16 threads and 15 GB RAM (WSL default cap, half of host RAM; raise it via `.wslconfig` only if needed — a system change, so ask the user first). 891 GB free on the WSL disk.
- 2026-10-02 — Env installed: `~/envs/picklebot-mj` (uv 0.10.11, already present; Python 3.12.13). Pinned `mjlab==1.6.0`, which resolved mujoco 3.11.0, mujoco-warp 3.11.0, warp-lang 1.17.0, rsl-rl-lib 5.4.2 and torch 2.14.1 (CUDA 13.0). Verified torch CUDA is available on the RTX 4070. Warp 1.17 initialised `cuda:0` (sm_89, toolkit 12.9, driver 13.3). `train` and `play` entry points are present. Reproduce with `mjlab/env/setup_wsl.sh`; full freeze in `mjlab/env/requirements-freeze.txt`. `.gitignore` now excludes `mjlab/artifacts/`, `mjlab/logs/` and `__pycache__/`.
- 2026-10-02 — G1 smoke run passed: `Mjlab-Velocity-Flat-Unitree-G1` via `mjlab/scripts/stage0_velocity_smoke.sh 4096 300` (seed 1, TensorBoard). 300 iterations × 4096 envs × 24 steps ≈ 29.5M policy steps in 476 s wall. Mean iteration 1.32 s (collection ~1.06 s, learning ~0.18 s), so ≈ 75k policy steps/s. Policy runs at 50 Hz (5 ms physics, decimation 4); episodes are 20 s (1000 steps). It learns: mean episode length 12 → 190, mean reward −1.16 → +3.71, falls per log window down from ~190 to ~23. Still far from converged at 300 iterations, as expected. Defaults: actor/critic `(512, 256, 128)`. Checkpoints in `mjlab/artifacts/stage0/logs/g1_velocity/2026-10-02_03-09-11_smoke-4096/` (local). GPU memory before the run: 3.0 / 12.3 GB.
