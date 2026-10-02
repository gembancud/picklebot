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
6. Long runs: launch as an independent Windows process (`Start-Process wsl ... scripts/stage2_train.sh`) with the app's keep-awake on, and watch for the `.exit.json` record. Host sleep killed run return-stand-01.
7. Model selection is always a fixed endpoint (the last checkpoint before the cap); never pick a peak by evaluation. Evaluation uses development seeds only; final seeds stay unused.
4. If blocked, record the blocker under **Open questions** and stop the loop instead of guessing.
5. Keep artifacts (logs, checkpoints, videos) under `mjlab/artifacts/`, which is gitignored. Commit only compact summaries.

## Stage 0 — toolchain and throughput trial
- [x] Record decision D-038 (switch to mjlab, G1 with wrist paddle, Unity frozen) in `docs/DECISIONS.md`, append-only.
- [x] Verify WSL2 sees the GPU (`nvidia-smi` inside Ubuntu); record CUDA and driver versions.
- [x] Install `uv` in WSL user space; create the env under `~/envs/picklebot-mj`; install mjlab (pin the exact version or commit).
- [x] Run mjlab's G1 velocity example for a short run; confirm it trains.
- [x] Benchmark steps/s at 1024, 2048 and 4096 envs, plus GPU memory use; write `mjlab/results/stage0-throughput.md`.
- [x] **Gate:** at least 10× the Unity baseline (≥ 10,000 steps/s) at a usable env count. Record pass or fail; ask the user if it fails.

## Stage 1 — ball and court physics (paddle rig)
- [x] Scaffold the `mjlab/picklebot_mj` package: court geometry (lines, net, kitchen) as MJCF, plus a unit-test setup.
- [x] Ball body (real mass/diameter) with drag and Magnus applied as forces; tests for free-flight trajectories.
- [x] ~~Court bounce with native MuJoCo contacts~~. Tried and found not viable (impact-phase-dependent restitution): `mjlab/results/stage1-bounce.md`. Replaced by the analytic model per **D-039** (user chose option A on 2026-10-02).
- [x] Analytic ball core `picklebot_mj/ball_sim.py`: batched torch state (pos, vel, spin), sub-stepped flight using `ball.aero_force`, and swept sphere-vs-court-plane bounce with an explicit impulse model. The model uses a normal COR, Coulomb friction with the slip/roll transition, and spin coupling. Tests:
  - the official drop band at **every** drop height and phase (sweep 1.95–2.05 m plus random phases);
  - no energy gain;
  - angled bounce slows and gains topspin; backspin checks up;
  - batch-equivalent and deterministic;
  - matches `ball.reference_flight` between bounces.
- [x] Net and posts in the analytic model: swept sphere vs the two tilted net boxes and the post cylinders. Low restitution (Unity 0.10). Tests: a 12 m/s ball is stopped at any timestep; a ball passing 10 cm over the net is untouched; a net-cord touch is handled.
- [x] Paddle impact model: swept sphere vs a moving, rotating paddle face (oriented box, Unity dimensions) using paddle linear and angular velocity. Normal COR is chosen so the PBCoR surrogate is ≤ 0.43; tangential friction gives spin; the equal and opposite impulse is returned. Tests:
  - no tunnelling up to 30 m/s relative speed;
  - PBCoR protocol surrogate ≤ 0.43;
  - momentum conserved with the paddle impulse;
  - the face angle steers the outgoing direction.
- [x] MuJoCo integration on the GPU: court spec plus a non-colliding ball body plus a driven paddle rig in an mjlab env. Each step reads the paddle state from sim, advances the ball sim, writes the ball pose for rendering, and applies the reaction to the paddle via `xfrc_applied`. Scripted swing hits fed balls; record a short video.
- [x] **Gate:** physics report (`mjlab/results/stage1-physics.md`) shows:
  - phase-independent bounce in the official band;
  - flight vs RK4;
  - net stops balls and lets clear balls pass;
  - paddle PBCoR ≤ 0.43, with no tunnelling and no energy gain;
  - GPU throughput with ball and paddle still ≥ 10× the Unity baseline at a usable env count.

## Stage 2 — standing G1 hits a fed ball
- [x] G1 plus a paddle fixed to the right wrist in the scene; reach and swing-speed envelope measured with scripted joint sweeps.
- [x] Rules and legality module (net clearance, in/out, kitchen) ported from the Unity rules, with tests.
- [x] Task: G1 standing (balance required), ball fed toward its forehand, reward for contact then a legal return; dev and train seed ranges defined.
- [x] First training run (≤ 2 h) plus evaluation on dev seeds; video of successes and misses.
- [x] **Gate:** learns legal returns on easy feeds; report written.

## Stage 3 — training throughput (ball term)
Baseline: `return-stand` task at about 10k env steps/s at 4096 envs (~9.7 s per iteration). GPU is ~33 % busy; the Python `BallSim` term dominates.
- [x] Profile one training iteration (ball term vs MuJoCo step vs PPO update). Write `mjlab/results/stage3-profile.md` with the time split.
- [x] Remove host syncs from `BallSim` (`.any()`/`.item()`/`float()` branches → branch-free masks; fixed sub-step count per physics step chosen from config, not from data). Keep all existing tests green; add a test that the step makes no host syncs (e.g. `torch.cuda.set_sync_debug_mode("error")`).
- [x] Try CUDA graphs or `torch.compile` on the ball step if still dominant; keep only what is measurably faster and exactly equivalent (compare against the uncompiled step on a fixed batch).
- [x] **Gate:** ≥ 2× the baseline env steps/s on `Picklebot-Return-Stand-G1` at 4096 envs, with all physics tests passing and `model_700` dev evaluation unchanged (legal return within its 95 % interval on seed 4,200,000). Report `mjlab/results/stage3-throughput.md`.

## Stage 4 — wider feeds and aiming (one shared policy)
Each new variable gets its own training run (≤ 2 h each), warm-started from the latest accepted checkpoint where the observation space is unchanged. Evaluate every feed family **separately** on dev seeds, alongside the original easy feed (retention: no more than 5 percentage points of legal-return loss on it).
- [x] **Grip fix (user request, 2026-10-02).** Close-up renders (`scripts/render_grip.py`) showed the paddle face starting ~4 cm inside the G1 fingers (handle hidden in the hand mesh) and the paddle pointing straight along the forearm line. Fix `picklebot_mj/g1_paddle.py`:
  - the face starts beyond the fingertips, and the visible handle sits in the palm;
  - the handle is angled about 35° across the palm, like a real handshake grip, so the paddle is not a straight extension of the forearm.

  Visual parts were done early on request (`561cd7b`, `163f3f4`): `GRIP_V2` (35°, fitted to clear the hand mesh by ≥ 3 mm), a visual closed fist, and a standard 16 × 8 in paddle look (rounded face, edge guard, throat, wrapped grip, butt cap). Remaining here:
  - switch `DEFAULT_GRIP` to v2;
  - make the analytic paddle contact use the rounded-corner face (1 in radius, matching the visual), with tests;
  - re-measure the envelope.

  Keep the paddle body origin at the face centre with `PaddleState` axes. Re-render the close-ups (side, front, top) for the user, update tests, and re-measure the envelope (`stage2_envelope.py`). Stage 2 results (`model_700`) stay as the old-grip record. Stage 4 runs train on the new grip; run A may warm-start from `model_700` (same observation space, documented), and the easy-feed retention baseline is re-established on the new grip.
- [x] Feed curriculum module: named feed families (`easy_forehand` = current; `wide_forehand` 0.65–1.0 m; `backhand` −0.30 to −0.65 m on the left; `deep` / `short` bounce points; `high` / `low` contact heights; `fast` incoming speed; `topspin` / `backspin`) and a sampler mixing them by weights. Offline feed checks (like `tune_feed.py`) per family. Tests.
- [x] Per-family dev evaluation: `stage2_eval.py` gains `--family`, reporting each family's rates in one table.
- [ ] Training run A: lateral widening (easy + wide_forehand + backhand). Evaluate all families plus retention.
- [ ] Target input: a landing-region goal (two regions, deep left / deep right in the far court, as in Unity two-region) added to observations, with a placement reward paid only on legal landings. The observation space changes, so this run is a fresh start or a documented warm-start that expands the network inputs. Placement metric: target hit rate and paired A/B assignment gain (same feeds, swapped targets) with intervals.
- [ ] Training run B: targets on easy + lateral families. Evaluate legality, target hits and A/B gain per family.
- [ ] Training run C: add depth, height, speed and spin families with targets. Evaluate everything per family.
- [ ] **Gate:** a single checkpoint with legal return ≥ 85 % on every lateral family and ≥ 70 % on depth/height/speed/spin families, target-hit A/B gain with a 95 % interval above zero, and easy-feed retention within 5 points. If the gate is not met after run C, record per-family results and stop for the user (no automatic extension). Report `mjlab/results/stage4-gate.md`.

## Stage 5 — robustness of the Stage 4 result
- [ ] Repeat the final Stage 4 training recipe with 2 more training seeds (≤ 2 h each).
- [ ] Evaluate all three on two fresh dev seeds; report per-seed and pooled results with intervals; flag any family whose result depends on the training seed.
- [ ] Record review videos: successes and misses per family (render the env index of a known miss), side and behind views.
- [ ] **Gate:** all three seeds meet the Stage 4 gate thresholds (or the deviations are documented and the user is asked). Report `mjlab/results/stage5-gate.md`.

## Stage 6+ — later (detail when Stage 5 passes)
Movement plus hitting (footwork using the walking policy as a base or teacher), privileged teacher → student distillation, serves on both sides, then 2v2.

## Open questions
- ~~**BLOCKING (2026-10-02): how should ball contacts be simulated?**~~ **Resolved 2026-10-02: the user chose A → D-039.** Native MuJoCo soft contacts give impact-phase-dependent restitution: COR 0.1–2.9 at dt 1–2 ms, and still ±0.05 at 0.1 ms. At 5 ms the ball tunnels through the net. Evidence: `mjlab/results/stage1-bounce.md`. Options:
  - **A. Analytic ball model (recommended).** MuJoCo collisions for the ball are disabled. Flight and impacts (court plane, net, paddle) are integrated in batched torch on the GPU with sub-stepping and swept collision tests, using an explicit restitution/friction/spin impulse model, as in Unity's contact surrogates. The paddle pose and velocity are read from MuJoCo each step, and the reaction impulse goes back to the hand via `xfrc_applied`. Ball–robot-body touches are detected as faults. The robot keeps dt 5 ms and throughput.
  - **B. Native contacts at a fine timestep** (≤ 0.25 ms) for the whole scene. Roughly 20–50× slower, and COR is still phase-dependent (±0.05–0.1).
  - **C. Accept native contacts at 1–2 ms** with randomised, unphysical bounces. Not recommended: it gains energy (COR > 1) on some impacts.
- ~~WSL RAM is capped at 15 GB.~~ Resolved 2026-10-02: not a constraint up to 8192 envs.
- Does mjlab run cleanly in WSL2 on this machine? (Stage 0)
- Can the G1's reach and swing speed produce competitive returns? (Stage 2)

## Log
- 2026-10-02 — Plan created; worktree and branch set up from `main` `256d7db`.
- 2026-10-02 — D-038 appended to `docs/DECISIONS.md`; D-001 status marked as superseded for new work. No other decision text changed.
- 2026-10-02 — WSL GPU check passed. Ubuntu 22.04.2, kernel 6.18.33.2-microsoft-standard-WSL2. `nvidia-smi` in WSL sees the RTX 4070 (12,282 MiB; ~2.6 GB already used by Windows apps): KMD 610.47, nvidia-smi 610.43.02, CUDA UMD 13.3. `libcuda.so` is present in `/usr/lib/wsl/lib`. WSL sees 16 threads and 15 GB RAM (WSL default cap, half of host RAM; raise it via `.wslconfig` only if needed — a system change, so ask the user first). 891 GB free on the WSL disk.
- 2026-10-02 — Env installed: `~/envs/picklebot-mj` (uv 0.10.11, already present; Python 3.12.13). Pinned `mjlab==1.6.0`, which resolved mujoco 3.11.0, mujoco-warp 3.11.0, warp-lang 1.17.0, rsl-rl-lib 5.4.2 and torch 2.14.1 (CUDA 13.0). Verified torch CUDA is available on the RTX 4070. Warp 1.17 initialised `cuda:0` (sm_89, toolkit 12.9, driver 13.3). `train` and `play` entry points are present. Reproduce with `mjlab/env/setup_wsl.sh`; full freeze in `mjlab/env/requirements-freeze.txt`. `.gitignore` now excludes `mjlab/artifacts/`, `mjlab/logs/` and `__pycache__/`.
- 2026-10-02 — G1 smoke run passed: `Mjlab-Velocity-Flat-Unitree-G1` via `mjlab/scripts/stage0_velocity_smoke.sh 4096 300` (seed 1, TensorBoard). 300 iterations × 4096 envs × 24 steps ≈ 29.5M policy steps in 476 s wall. Mean iteration 1.32 s (collection ~1.06 s, learning ~0.18 s), so ≈ 75k policy steps/s. Policy runs at 50 Hz (5 ms physics, decimation 4); episodes are 20 s (1000 steps). It learns: mean episode length 12 → 190, mean reward −1.16 → +3.71, falls per log window down from ~190 to ~23. Still far from converged at 300 iterations, as expected. Defaults: actor/critic `(512, 256, 128)`. Checkpoints in `mjlab/artifacts/stage0/logs/g1_velocity/2026-10-02_03-09-11_smoke-4096/` (local). GPU memory before the run: 3.0 / 12.3 GB.
- 2026-10-02 — Throughput benchmark (`mjlab/scripts/stage0_throughput.sh 30`, also covering 8192 envs): 28k / 50k / 72k / 99k policy steps/s at 1024 / 2048 / 4096 / 8192 envs; peak device memory 3.4–5.8 GB. **Stage 0 gate PASS**: 28–99× the Unity ~1k steps/s by steps, and roughly 14–40× by simulated seconds (the Unity tick rate was not re-verified). It is an empty-scene measurement and must be re-measured with the ball and paddle in Stage 1. Report: `mjlab/results/stage0-throughput.md`. **Stage 0 complete.**
- 2026-10-02 — Stage 1 scaffold: `mjlab/` is now an installable package `picklebot-mj` (editable in the WSL env; `pytest` dev extra). `picklebot_mj/court.py` builds the court as a `mujoco.MjSpec`. Frame: x along the length with the net at x = 0, near side x < 0; y across; z up. Contents: floor plane, visual-only lines (group 3, no contacts; 2 in wide, inside the area they bound), net as two tilted boxes whose top edge rises linearly 0.8636 m at the centre → 0.9144 m at the sidelines, and posts. Dimensions match Unity `CourtGeometryV0/V1`. 14 tests pass (`mjlab/scripts/test.sh`). They cover: constants vs Unity; net-top height by downward raycast at 8 lateral positions (±1 mm); no gap at the net centre; markings non-colliding; line coverage; a ball dropped on the court settles on the floor.
- 2026-10-02 — Ball and aerodynamics: `picklebot_mj/ball.py`.
  - Free ball body: 24 g, r = 37 mm, hollow-shell inertia (2/3)mr²; Unity used a solid-sphere default.
  - Batched torch drag + Magnus lift + spin-decay wrench for `xfrc_applied`, ported from Unity `AerodynamicModelV1` with `SimulationConfigV1` defaults (Cd 0.30, lift slope 0.195, Cl max 0.25, ρ 1.204, spin decay 0.05/s).
  - RK4 reference ported from `FlightReferenceIntegratorV1`.
  - Bug found and fixed: leaving the explicit inertial frame unset made MjSpec put the CoM at the body offset (1 m away), so spinning balls flew tens of metres off. `ipos`/`iquat` are now set explicitly, with a regression test.
  - MuJoCo flight vs RK4 after 1 s (implicitfast; 5 cases: flat, topspin, backspin dink, sidespin, lob): position error 2.6–3.6 cm at dt 5 ms and 0.5–0.7 cm at dt 1 ms. This is first-order convergence (error ratio ≈ 2 per halving, tested), consistent with ½·g·dt·T. Spin decay matches to 1e-3.
  - 34 tests pass (`mjlab/scripts/test.sh`).
  - Open for the paddle step: whether 5 ms is accurate enough, or contacts force a smaller dt.
- 2026-10-02 — Court bounce step **blocked; not ticked**.
  - Built explicit ball contact pairs (floor, net, posts) and swept 552 contact configurations. A per-dt damping calibration hit the official drop band exactly, but validation showed restitution is set by impact phase, not parameters: COR 0.10–1.64 at 2 ms and 0.11–2.88 at 1 ms over drop heights 1.95–2.05 m, linear in detection depth. Spread is still ±0.05 at 0.1 ms. At 5 ms the ball tunnels through the net.
  - Also found: condim 6 is not suitable for the floor pair; condim 3 is kept.
  - The suite stays green: 50 pass and 13 strict xfails document the findings.
  - Report: `mjlab/results/stage1-bounce.md`. User decision needed (Open questions); loop stopped.
- 2026-10-02 — User chose option A. D-039 appended to `docs/DECISIONS.md` (analytic GPU ball contact model; amends D-038). Stage 1 steps restructured around it. Loop restarted.
- 2026-10-02 — Analytic ball core: `picklebot_mj/ball_sim.py` (`BallSim.step(state, dt, substeps)`, batched torch).
  - **Flight:** RK4 sub-steps of gravity + aero + spin decay.
  - **Court:** swept sphere-vs-plane with time-of-impact interpolation, then a rigid-sphere impulse. Normal COR, Coulomb friction capped by the normal impulse (slip/roll transition) and spin coupling. Resting balls are held on the surface. Contact events carry the first contact point.
  - **Calibration:** court COR **0.6381** (`scripts/calibrate_analytic_cor.py`) puts the official drop apex at 0.813 m.
  - **Tests:** 18 new; suite 68 pass + 13 documented xfails. They cover:
    - phase independence: over the 1.95–2.05 m sweep that native MuJoCo failed, plus 32 random phases, the apex/height ratio spread is < 0.2% at 1, 4 and 10 substeps;
    - the official apex is insensitive to step size (dt 2–20 ms);
    - COR is constant from 0.3–3 m drops;
    - no energy gain over 4,096 random spinning impacts, and the Coulomb cone is respected;
    - energy is monotone through repeated bounces;
    - an angled bounce gains topspin; topspin keeps pace; backspin skids at speed and checks back at low speed;
    - a rolling ball gets no tangential impulse; a ball comes to rest without sinking;
    - flight matches the RK4 reference to 1e-6 m;
    - batches are equivalent and deterministic;
    - CUDA float32 matches CPU float64 within 2 mm.
- 2026-10-02 — Net and posts added to `ball_sim.py`.
  - **Geometry:** the net is a slab |x| ≤ 1 cm with its top following `net_height_at(y)` out to the posts; the posts are cylinders. A closest-point sphere test handles face hits, net-cord touches on the top edge and the ends the same way.
  - **Response:** the same impulse model with net COR 0.10 and friction 0.4 (Unity), then depenetration to the surface. Events: `net_contact`, `post_contact`.
  - **Tunnelling guard:** sub-steps adapt so no ball travels more than 0.5 r per sub-step (`substeps_for`).
  - **Tests:** 9 new; suite 78 pass + 13 documented xfails.
    - Balls at 12 and 30 m/s are stopped at 12 positions, with dt 5 ms and 20 ms and only one requested sub-step. They never pass the net face and come back slower than 0.3× their speed.
    - A ball 10 cm over the net is untouched.
    - A net-cord touch deflects the ball upward without energy gain.
    - Balls beyond the posts pass; a ball into a post bounces back.
    - 2,048 random spinning net impacts show no energy gain.
  - Earlier ball tests that dropped balls at x = 0 (now the net plane) were moved to open court. The calibration drop also moved to (−3, 1); COR unchanged.
- 2026-10-02 — Paddle impacts in `ball_sim.py`: `BallSim.step(..., paddle=PaddleState)`.
  - **Geometry and motion:** the paddle face is an oriented box (Unity face 0.2032 × 0.2794 × 0.016 m). Its pose is advanced within the step from its linear and angular velocity (Rodrigues). Sphere-vs-box uses the closest point; a ball centre inside the box exits through the face it approaches.
  - **Response:** kinematic paddle (the arm is far heavier than the ball). Normal COR 0.40 (Unity; PBCoR surrogate ≤ 0.43); friction 0.2 uses the surface velocity, so brushing the ball generates spin.
  - **Outputs:** reaction impulse and angular impulse about the face centre on the paddle (`paddle_impulse`, `paddle_angular_impulse`) plus the contact point, for `xfrc_applied` in the next step. Adaptive sub-steps also account for paddle speed and tip rotation.
  - **Tests:** 11 new; suite 89 pass + 13 documented xfails.
    - PBCoR surrogate 0.40 ± 0.02 at 5/10/20/30 m/s (≤ 0.43).
    - No tunnelling: a 30 m/s swing through a resting ball at 40 phases, dt 5 ms and 20 ms with one requested sub-step, all hit, with exit speed (1 + e)·30 ± 0.2 m/s.
    - The face tilt steers the ball; a ball beside the face misses.
    - Brushing up gives topspin (> 50 rad/s).
    - Momentum is conserved to 1e-9 (ball Δp − gravity = −paddle impulse).
    - 2,048 random spinning impacts show no energy gain beyond depenetration slack.
- 2026-10-02 — GPU integration: `picklebot_mj/rig_env.py`.
  - **Env:** `PickleballRigEnv` is an mjlab `ManagerBasedRlEnv` with a plane terrain plus three mocap entities: court markings/net/posts (`court.court_entity_spec`, visual only), the ball and the paddle.
  - **Physics hook:** the env wraps `sim.step`, so every MuJoCo physics step (5 ms, decimation 4) also advances `BallSim` against the scripted paddle and writes the ball and paddle mocap poses (plus env origins).
  - **Scripted swing:** each 3 s episode tosses a ball 0.5–0.8 m above an intercept at x = −5.5 m. The paddle waits at a wind-up point, then swings through at 7–9 m/s and 30–40° with the face normal along the swing.
  - **Results** (`scripts/stage1_rig.py`, 4096 envs × 300 env steps, 8,192 episodes): paddle hit 100%, landed 100%, in far court 89.9% (the rest long, up to x = 7.83 m, from the swing-speed range), net touches 0. Throughput **38,153 env steps/s** (152,613 physics steps/s) with no robot.
  - **Video:** `scripts/stage1_rig_video.sh` renders headless EGL 960×540, 150 frames, into `mjlab/artifacts/stage1/rig.mp4` (local; frames inspected: contact at frame 15, ball over the net by frame 40). It uses the bundled imageio-ffmpeg; no system ffmpeg needed.
  - **Bugs fixed on the way:** the mocap writer needs explicit env ids; the camera follows env 0's court; court markings are geom group 3; video recording skips the warm-up; the paddle no longer starts underground.
  - **GPU smoke test** `tests/test_rig_env.py`; suite 90 pass + 13 xfails.
  - **Limitations:** the paddle is kinematic, so the reaction impulse is accumulated but not yet applied to a dynamic body (that comes with the G1 wrist in Stage 2). The ball sim costs about 26 ms per physics step at 4096 envs: many small kernels and host syncs in the sub-step loop. Optimisation candidates: branch-free masks without `.any()` syncs, CUDA graphs or `torch.compile`.
- 2026-10-02 — **Stage 1 gate PASS** (`mjlab/results/stage1-physics.md`). All criteria were met with measured evidence: phase-independent official drop band (provisional court), no energy gain, flight vs RK4, net and posts, paddle PBCoR 0.40 ≤ 0.43, no tunnelling, momentum, GPU rig at 100 % hits and 38k env steps/s (38× Unity). Caveats carried into Stage 2: throughput with the G1 is unmeasured (ball sim ~26 ms per physics step at 4096 envs is the main cost); the reaction impulse is not yet applied to a dynamic body; simplified kinematic paddle; provisional court bounce. **Stage 1 complete.**
- 2026-10-02 — Stage 2 step 1: `picklebot_mj/g1_paddle.py` attaches a 0.22 kg paddle body to `right_wrist_yaw_link`.
  - **Grip:** handshake; the handle is centred on the `right_palm` site, the face runs along the hand axis, and its normal is the palm normal. The body origin is the face centre, with axes matching `PaddleState`. Visual-only geoms.
  - **Tests:** 4 new (parent, mass, exact axes and offset in the wrist frame, non-colliding geoms, fixed-base actuator mapping). Suite 94 pass + 13 xfails.
  - **Envelope** (`scripts/stage2_envelope.py`, fixed pelvis at 0.76 m, mjlab actuators):
    - reach of the face centre up to 0.89 m horizontal (95th percentile 0.70), heights 0.30–1.73 m;
    - peak face speed 14.0 m/s (95th percentile 10.3, median 5.7), up to 12.0 m/s along the face normal, about a 17 m/s ball exit.
  - **Caveats:** random pose-pair swings are lower bounds on skill but upper bounds on dynamics (fixed base); joint velocity limits not verified; no paddle self-collision.
  - Report: `mjlab/results/stage2-envelope.md`. No blocker.
- 2026-10-02 — Rules: `picklebot_mj/rules.py`, a batched torch port of Unity `DoublesRules` at rally level.
  - **Ported:** phases; serve landing (diagonal box beyond the kitchen line; the kitchen line is a fault, the centre line is in); two-bounce rule; kitchen volley plus the re-establish-both-feet requirement plus the volley-momentum fault; double hit; wrong receiver; out (lines in); wrong side; second bounce; body contact; player net touch; post (permanent object); lost; truncate. A ball touching the net is not a fault. The first fault sticks.
  - **Frame mapping:** Unity z → x and Unity x → −y, which preserves left/right handedness. `begin_from_feed` supports drill starts (rally or must-bounce context).
  - **Not ported** (not needed for Stage 2): scoring/side-out/server rotation, serve-motion rules and continuous-stroke contact.
  - **Tests:** 24, mirroring 19 Unity rally-level cases by name, plus batching and drill feeds. Suite 118 pass + 13 xfails.
- 2026-10-02 — Task `Picklebot-Return-Stand-G1` (`picklebot_mj/tasks/return_stand.py`), registered through the `mjlab.tasks` entry point so mjlab's `train`/`play` CLIs work unchanged.
  - **Base:** mjlab's flat G1 velocity config (proprioception, joint-position actions with G1 scales, upright/pose/action-rate/limit rewards, fell_over), with a zero velocity command (standing), no pushes, and a pose prior that leaves the right arm free.
  - **Scene:** G1 + wrist paddle at court-local (−5.6, 0.35), facing the net; mocap ball and court; env spacing 20 m.
  - **Ball:** a 0-dim `BallPhysicsAction` term advances `BallSim` on every physics step via the action manager's per-substep hook. It reads the paddle pose and velocity from the robot, applies the reaction impulse to the paddle body through `xfrc_applied`, drives `RallyRules`, and writes the ball mocap. Body contact is approximated by pelvis/torso spheres (0.17 m).
  - **Feed:** one per 3 s episode from the far side, in receive context (must bounce; a volley is an EARLY_VOLLEY fault). Ranges tuned offline (`scripts/tune_feed.py`): 100% bounce exactly once; 80% pass the contact plane at 0.55–1.15 m (p10–p90 0.52–0.66 m); 0.30–0.65 m to the robot's right.
  - **Observations:** ball position and velocity in the base frame, ball relative to the paddle, rally flags (critic also gets spin). Actor 110 / critic 125 dims; 29 actions.
  - **Rewards:** approach shaping exp(−(d/0.25)²) after the bounce and before contact (weight 2); first legal paddle contact +1; legal return (first bounce after the hit lands in the far court) +5; plus the base balance terms.
  - **Terminations:** fell_over, drill_over (rally dead or legal return), time_out.
  - **Seeds** (`picklebot_mj/seeds.py`): train 1–999, dev eval 4,200,000–4,200,999, final 9,200,000–9,200,999 (reserved, unused).
  - **Verification:**
    - Zero-action smoke (64 envs × 400 steps): before tuning, 141 SECOND_BOUNCE endings showed the feed fell short; after tuning, 145 crossings at 0.37–0.66 m.
    - Zero-action G1 falls in this task just as in mjlab's stock velocity task (27 vs 28 falls in 16 envs × 3 s), so balance must be learned.
    - `train` CLI smoke (1024 envs × 5 iterations): runs; contact/approach rewards appear; **4.5–6.3 s per iteration ≈ 5k steps/s at 1024 envs**, to be measured at 4096 before the run.
  - Tests: +2 (seed ranges; GPU build/step/rules/mocap). Suite 120 pass + 13 xfails.
- 2026-10-02 — First training run and dev evaluation (`mjlab/results/stage2-train.md`).
  - **Run 01 invalid:** killed at iteration 229 when the host slept (WSL VM shut down), and trained under a config bug: the inherited `command_vel` curriculum widened the standing command. Fixed (`8b3c546`) with a regression test.
  - **Run 02:** launched as an independent `wsl.exe` process with the app keeping the host awake. 4096 envs, completed to the 7,000 s cap at iteration 722 (~71M steps, ~9.7 s per iteration).
  - **Selection:** fixed endpoint `model_700`.
  - **Dev evaluation** (deterministic, 512 envs × 9 s, seeds 4,200,000 / 4,200,001): contact 100 %, **legal return 96.1 % [95.0, 97.0] / 96.0 % [94.9, 96.8]**, falls 0 %. Failures: 31/27 out, 6/8 wrong side. The untrained `model_0` scored 0 % legal returns with 81–83 % falls.
  - **Stroke:** paddle 7.1 ± 0.2 m/s at contact; ball 3.3 → 11.2 m/s; net clearance 1.40 m; landing x 4.58 ± 0.93 m.
  - **Video:** side view; frames show backswing, contact and the ball over the net (successes only so far).
  - **Evaluation fix:** rates now use per-episode tallies recorded at episode end (the first version divided events by finished episodes and could exceed 1).
  - **Caveats:** one narrow feed family, a stereotyped high loft, reused dev seeds, misses not yet on video.
  - Suite 121 pass + 13 xfails.
- 2026-10-02 — **Stage 2 gate PASS** (`mjlab/results/stage2-gate.md`): legal returns on easy feeds at about 96 % on dev seeds, with balance and a real stroke. Carried forward: single feed family, stereotyped loft without aiming, single training seed and reused dev seeds, misses not filmed, simplified paddle and body contact, ~10k steps/s limited by the Python ball term. **Stage 2 complete; loop ends here per its instruction.** Next steps are for the user to choose (see the gate report).
- 2026-10-02 — User asked for a better grip and paddle look: grip v2 (35° handshake, fitted to the hand mesh), a visual closed fist and a standard 16 × 8 in paddle look, built early (`561cd7b`, `163f3f4`), visual only; v1 remains the default until Stage 4. Stages 3–5 planned (`02e31ba`); loop restarted to Stage 5.
- 2026-10-02 — Stage 3 profile (`mjlab/results/stage3-profile.md`). Env step at 4096 envs with random actions: 185 ms, of which the **ball term is 68 %** (125 ms), MuJoCo 16 % and other managers 16 %. Training run 02: collection 97 % (9.29 s per iteration), PPO 0.26 s; collection grew 5.4 → 11.2 s as the swing sped up. Cause: batch-max adaptive sub-steps with host syncs and many small kernels. Plan: sync-free fixed sub-steps, fewer kernels, then CUDA graphs or `torch.compile`.
- 2026-10-02 — Sync-free ball step.  - **Change:** `BallSim.step(..., adaptive=False)` uses a fixed sub-step count and a branch-free body: court impact by in-sub-step interpolation instead of two extra RK4 integrations, and net/paddle/rest always computed and masked. Cached constants. The task uses 6 sub-steps per 5 ms physics step and has no `.any()`/`bincount`/list-index syncs. Adaptive mode is kept for tools and tests.  - **Tests:** all 39 ball/net/paddle physics tests unchanged and green with the new numerics. New: a zero-host-sync test (`torch.cuda.set_sync_debug_mode("error")`) and a no-tunnelling test at the training setting (30 m/s, 40 phases). Suite 125 pass + 13 xfails.  - **Speed: not faster yet.** Random actions: 185 → 263 ms per env step. Trained `model_700` policy: fixed 6 sub-steps 240 ms (ball 190) vs adaptive 214 ms (ball 159). The cost is kernel-launch count, not syncs; the step is now fixed-shape and sync-free, as needed for `torch.compile`/CUDA graphs (next step). Raw: `mjlab/results/stage3-profile-*.json`.
- 2026-10-02 — Compiled ball step: `CompiledBallSim` runs `torch.compile` (mode default, fullgraph, static shapes) on the sync-free fixed-sub-step step. The task uses it by default (`compile_ball`), with ~48 s compile once per process.  - **Ball step alone** (4096 balls + paddles, 6 sub-steps): **32.1 → 3.46 ms per physics step (9.3×)**; max deviation 6e-6 m; identical contacts. CUDA-graph mode (`reduce-overhead`) failed on reused output buffers and was not used.  - **Env step with the trained `model_700` policy:** 240 → 110 ms (ball term 190 → 58 ms); **37.3k env steps/s** vs 19.2k for adaptive sub-steps on the same workload (1.95×). The rest of the ball term (rules, diagnostics, mocap writes) is now the next cost.  - **Tests:** new `test_ball_compile.py` (compiled vs eager over 40 steps on 2048 balls: >99 % within 1 mm, contact counts within 1 %). Suite 126 pass + 13 xfails.
- 2026-10-02 — **Stage 3 gate PASS** (`mjlab/results/stage3-throughput.md`): resumed training from `model_700` runs at **2.42 s per iteration (40.6k env steps/s)**, 3.95× the run 02 average and 4.76× its matched late workload. `model_700` dev evaluation on the new code: 96.5 % [95.5, 97.3] legal returns (was 96.1 % [95.0, 97.0]); physics tests green. **Stage 3 complete.**
- 2026-10-03 — Stage 4 grip step done.  - **Grip:** `DEFAULT_GRIP` = v2 (35° handshake grip, visual closed fist, standard 16 × 8 in paddle look). Stage 2 results remain the v1 record.  - **Contact:** the analytic paddle contact now uses the drawn rounded face (`BallParams.paddle_corner_radius` = 1 in, set by the task; default 0 elsewhere). New test: a ball just off the corner diagonal touches the square face but misses the rounded one, and centre hits are identical.  - **Envelope** (`results/stage4-envelope-v2.json`): reach 0.90 m (v1 0.89), face heights 0.29–1.73 m; peak face speed 15.1 m/s (v1 14.0), along the normal 14.1 m/s (v1 12.0).  - Suite 127 pass + 13 xfails.
- 2026-10-03 — Feed families: `picklebot_mj/feeds.py`.  - **Families (10):** easy_forehand (the Stage 2 drill), wide_forehand, backhand, deep, short, high, low, fast, topspin, backspin. `FeedMix` weights sample a family per episode; the task gathers each env's ranges as tensors (no syncs) and keeps per-family episode tallies.  - **Offline check** (`scripts/tune_feed.py --families`, 2048 feeds each; table in `results/stage4-feed-families.txt`): every family bounces exactly once before the contact plane (100 %), arrives within the measured reach, and differs from easy as intended (high median ~0.87 vs 0.60 m; low ~0.49; fast ~5.4 vs 3.4 m/s; wide/backhand lateral bands; deep/short bounce points).  - **Short and high limits:** short needed a steeper arc to stay reachable while standing, because truly short balls need footwork (Stage 6). High is capped around 0.9–1.0 m by the court COR for a standing contact plane.  - Tests: 13 new (`tests/test_feeds.py`). Suite 140 pass + 13 xfails.
- 2026-10-03 — Per-family evaluation: `stage2_eval.py --families <list|all> [--grip v1]` samples families uniformly and prints a per-family table (episodes, contact, legal return with Wilson 95 % interval, falls). `--grip v1` rebuilds the Stage 2 robot (inline grip, square face) for old checkpoints. The task term now exposes `paddle_corner_radius`; `get_g1_paddle_cfg(grip)` was added.  - **Baseline `model_700` on its own v1 robot**, all 10 families (dev seed 4,200,010; 1024 envs × 15 s; about 650–780 episodes each). Legal return:    - easy 96.7 % [95.0, 97.8]; topspin 95.5 %; deep 76.5 %; backspin 61.0 %; wide forehand 44.9 % (63 % contact);    - low 15.0 % (100 % contact); fast 2.6 % (99 % contact); short 0.3 % (36 % contact);    - backhand 0 % (0 % contact); high 0 % (0.1 % contact). No falls in any family.  - **`model_700` on the new v2 grip, without retraining:** easy legal return 91.0 % [89.4, 92.3] (seed 4,200,011); transfer is good enough to warm-start.  - Results: `results/stage4-eval-model_700-*.json`.
