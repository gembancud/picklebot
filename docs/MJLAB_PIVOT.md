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
- [ ] Record decision D-038 (switch to mjlab, G1 with wrist paddle, Unity frozen) in `docs/DECISIONS.md`, append-only.
- [ ] Verify WSL2 sees the GPU (`nvidia-smi` inside Ubuntu); record CUDA and driver versions.
- [ ] Install `uv` in WSL user space; create the env under `~/envs/picklebot-mj`; install mjlab (pin the exact version or commit).
- [ ] Run mjlab's G1 velocity example for a short run; confirm it trains.
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
- Does mjlab run cleanly in WSL2 on this machine? (Stage 0)
- Can the G1's reach and swing speed produce competitive returns? (Stage 2)

## Log
- 2026-10-02 — Plan created; worktree and branch set up from `main` `256d7db`.
