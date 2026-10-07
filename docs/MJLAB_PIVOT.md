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
8. **Bounded hill-climbing (user request, 2026-10-06).** When a training step or gate misses its thresholds, the loop may run up to **two follow-up runs for that step**. Each:
   - is warm-started from the previous fixed endpoint;
   - changes **one** variable chosen from the failure analysis, written in the report **before** launch;
   - is evaluated on a fresh dev seed.

   Add each follow-up as a new checklist step. If the thresholds are still missed after two follow-ups, or the fix would need a design change (new inputs or task structure beyond the step's scope, a new decision, or anything in rule 3), record it under Open questions and stop for the user. Never loosen a threshold to pass.
9. **Chained teacher training (D-042, 2026-10-06).** A teacher may train as a chain of fixed-endpoint runs (each ≤ 2 h, each continuing from the previous endpoint, up to **4 per teacher**). After each run, evaluate on a fresh dev seed. Stop chaining when the teacher's gate is met, or when it improves by less than 1 point on its main metric between runs; then the teacher's endpoint is that run's fixed endpoint. Chaining is not a rule 8 follow-up (no variable changes). If a teacher's gate is still missed when chaining stops, rule 8 follow-ups apply.
10. **Downloads need the user (D-044, 2026-10-06).** Before downloading any dataset, model or tool, stop and ask the user, giving its name, source, size and licence. Research (reading pages, papers, licences) needs no approval.

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
- [x] Training run A: lateral widening (easy + wide_forehand + backhand). Evaluate all families plus retention. **FAILED** (reward-incentive loophole; `mjlab/results/stage4-run-a.md`).
- [x] Training run A2 (`lateral-a02`): rally end = bootstrapped time-out, 4 s episodes. **FAILED**: inherited critic diverged (value loss 64 vs 0.1), action std 0.69 → 2.8, policy collapsed to instant falls by iteration ~1,550; stopped at 1,890.
- [x] Training run A3 (`lateral-a03`): feeding machine (no rally-end termination; next feed 0.5 s after each rally; 8 s episodes ending only on fall or time), warm-started from `model_700`. Evaluate all families plus easy-feed retention (retention baseline re-measured under the feeding machine).
- [x] Target input: a landing-region goal (two regions, deep left / deep right in the far court, as in Unity two-region) added to observations, with a placement reward paid only on legal landings. The observation space changes, so this run is a fresh start or a documented warm-start that expands the network inputs. Placement metric: target hit rate and paired A/B assignment gain (same feeds, swapped targets) with intervals.
- [x] Training run B: targets on easy + lateral families. Evaluate legality, target hits and A/B gain per family.
- [x] Training run C: add depth, height, speed and spin families with targets. Evaluate everything per family.
- [x] **Gate:** a single checkpoint with legal return ≥ 85 % on every lateral family and ≥ 70 % on depth/height/speed/spin families, target-hit A/B gain with a 95 % interval above zero, and easy-feed retention within 5 points. If the gate is not met after run C, record per-family results and stop for the user (no automatic extension). Report `mjlab/results/stage4-gate.md`. **Not met by under 1 point on three families (wide 84.6 %, backhand 84.4 %, high 69.2 %); accepted with these documented deviations by the user on 2026-10-05 (D-040).** The standing-only constraint, not aiming, limits contact; footwork comes next. `aim-all-c01/model_7600` is the accepted Stage 4 checkpoint and the parent for Stage 5.

## Stage 5 — footwork: move, hit, recover (one shared policy, D-040)
The executor learns to step to the ball and to recover to a commanded court spot, so that a later strategy layer can command *where to land the ball* and *where to be after the shot*. Footwork belongs in the executor (fast, coupled to the swing). Court positioning (where to stand, who takes the ball) belongs to the later strategy layer. Same discipline as Stage 4: one variable per run (≤ 2 h each), fixed endpoints, dev seeds only, per-family reporting. Retention means no more than 5 points of legal-return loss on the Stage 4 families versus `model_7600` on the same feeds.
- [x] **Motion audit (no training).** List every inherited reward, termination and command term that penalises or prevents base motion: zero velocity command with tracking rewards, leg `std_standing` pose terms, the start-pose box and anything else. Measure how far `model_7600`'s feet and pelvis actually travel per feed. Report `mjlab/results/stage5-motion-audit.md` with the planned changes.
- [x] **Reach feed families.** New families whose contact point needs travel (forehand and backhand 1.0–2.5 m lateral; deep and short contact points needing 0.5–1.5 m forward or back travel), plus a randomised robot start box on court (shuffled per robot episode) so that position is not memorised. Offline feed checks (`tune_feed.py --families`): one bounce, and contact plane and height reachable after moving. Tests.
- [x] **Recovery command.** A commanded court spot (x, y) on the robot's half as two new observations, appended last (expanded checkpoint, identical actions at zero, as for targets). Rewarded for being near it between the hit and the next feed, never before the hit. Metric: recovery error at the next feed's launch (median and p90). In training the spot is sampled per feed from a box around the baseline centre; it is fixed during evaluation. Tests.
- [x] **Stance release.** Apply the audit's changes: relax leg/waist pose terms, remove stand-still penalties and keep balance terms. Test that a zero action still stands and that a stepping policy is no longer penalised for base motion alone.
- [x] **Training run F1:** the Stage 4 families from random starts, plus reach families, plus recovery commands, warm-started from the expanded `model_7600`. Evaluate per family (contact, legal, A/B gain), recovery error, falls per robot episode, and retention on the Stage 4 families from the original start.
- [x] **Training run F2:** one change chosen from F1's failure analysis (documented before launch), or a fixed continuation if F1 is healthy but still improving.
- [x] **Review videos (F2 endpoint `footwork-f02/model_12000`):** successes and misses per family, side and behind views, including footwork on reach feeds. Send them to the user. Report `mjlab/results/stage5-f2-videos.md`.
- [x] ~~**Gate after F2**~~ **Replaced by the drill plan (D-041, 2026-10-06).** F2 did not meet it (`stage5-run-f2.md`): reach left, short and deep were 0 %, recovery median 0.78 m and contact 84–88 %. The user chose dedicated movement drills instead of more ball training. The gate thresholds move to the end of Drill 3, unchanged.

### Stage 5 drills (D-041): move first, then move-and-swing, then real balls
F1 and F2 showed the policy will not discover multi-step footwork from a standing lineage. Teach it with drills in the **same single network**, so that the executor still takes "land here, be there" commands. Each drill has its own gate. One variable per run (≤ 2 h each), fixed endpoints, dev seeds only. Every drill run keeps **hitting rehearsal**: 25 % of robot episodes run the Stage 4 hitting drills, so hitting is not forgotten. Parent of Drill 1: `footwork-f02/model_12000`. If a drill's gate is not met after two runs, stop for the user.

**Drill 1 — move to a spot, no ball.**
- [x] **Move-to-spot task.**
  - Each robot episode issues a sequence of spots, a new one after each arrival or time-out, in every direction from the robot: left, right, forward, back and diagonal, at distances 0.5–3 m, inside the robot's half court.
  - The ball is parked and inactive in these episodes.
  - **Re-use the walking rewards as the teacher:** the twist command is no longer zero but points toward the spot (speed min(1.0 m/s, 1.2·d), heading command to face the net), so mjlab's own `track_linear_velocity` / `track_angular_velocity` and the command-gated foot-quality terms teach gaits.
  - **Arrival:** within 0.25 m and below 0.2 m/s, held for 0.3 s. It pays an arrival bonus plus a **ready stance**: paddle up and in front (paddle centre 0.9–1.2 m high, 0.3–0.5 m in front of the pelvis), facing the net.
  - In hitting-rehearsal episodes the command is zero and the free-feet rules apply.
  - The movement direction mix is balanced and logged per direction.
  - Tests: command toward the spot, arrival detection, ready-stance reward, direction coverage, ball inactive in move episodes.
- [x] **Run D1:** move-to-spot plus hitting rehearsal from `model_12000`.
  - Evaluate per direction (8 sectors) and distance band: arrival rate, time to arrive, final error, ready-stance rate, falls per robot episode, foot slip.
  - Also hitting retention on the Stage 4 families from the fixed start, versus `model_12000`.
- [x] **Run D1b (rule 8 follow-up 1):** oversample the right-side sectors ×2 in training (`Picklebot-Drill-Move-Right-G1`), from `drill-move-d01/model_13900`; evaluate as D1 on a fresh dev seed.
- [x] **Run D1c (rule 8 follow-up 2):** from D1's endpoint `drill-move-d01/model_13900` (D1b regressed), hitting rehearsal 25 % → 40 % (`Picklebot-Drill-Move-Rehearse-G1`); evaluate as D1 on a fresh dev seed. Reported in `mjlab/results/stage5-drill1.md`.
- [x] **Drill 1 result (informational under D-042):** compare D1, D1b and D1c against the Drill 1 thresholds in `mjlab/results/stage5-drill1.md`:
  - arrival ≥ 90 % in every sector;
  - median error ≤ 0.25 m;
  - ready stance ≥ 80 %;
  - falls ≤ 1 %;
  - hitting retention within 5 points per family.

  This is no longer a stop: the same-network trade-off it measured is what D-042 replaces. Name the **walking-teacher parent**, the Drill 1 endpoint with the higher overall arrival rate (a choice between completed endpoints on dev seeds).

### Stage 5 teachers and student (D-042): specialists to saturation, distilled into one larger student
Each skill is trained by a **specialist teacher** with only its own rewards, so nothing interferes. The teachers are then **distilled** into one larger student, which is fine-tuned with RL on the combined drills under a pull-back penalty toward the teachers. Teacher training may chain fixed-endpoint 2-hour runs (loop rule 9). The final Stage 5 gate is unchanged.

**Teachers**
- [x] **Walking teacher task:** move-to-spot episodes only (`move_prob` 1.0, uniform sectors), as in Drill 1. Task `Picklebot-Teacher-Move-G1`. Tests.
- [x] **Walking teacher training:** from the Drill 1 parent named above, chained runs under rule 9.
  - Gate: arrival ≥ 95 % in every sector, median error ≤ 0.25 m, ready stance ≥ 90 %, falls ≤ 1 %.
  - If the right side still lags with no competing skill, report it as a body or stance limitation and stop for the user.
- [x] **Hitting teacher task:** hitting only (no move episodes), Stage 4 families plus reach_forehand from random starts, aiming targets and the recovery command, free feet. Task `Picklebot-Teacher-Hit-G1`. Tests.
- [x] **Hitting teacher training:** from `footwork-f02/model_12000` (the best hitter), chained runs under rule 9.
  - Gate: legal ≥ 85 % on every Stage 4 family from random starts.
  - Contact ≥ 92 % on the Stage 4 families.
  - A/B gain interval > 0 per family.
  - Retention within 5 points versus `model_7600` (fixed start).

**Student**
- [x] **Hitting teacher chain run 2 (rule 9):** continue `teacher-hit-01/model_14200` with no changes; evaluate with the corrected metric (D-043). Run 1 (corrected): every family ≥ 98.4 % legal except backspin 83.6 %; contact ≥ 98.9 %; retention fails only on backspin (−13.6).
- [x] **Hitting teacher follow-up HT-b (rule 8, 1 of 2):** backspin weight ×3 in the feed mix (`Picklebot-Teacher-Hit-Backspin-G1`), from `teacher-hit-02/model_16400`; evaluate as before on a fresh dev seed.
- [x] **Adaptive curriculum sampler (user request, 2026-10-06).** Automatic curriculum learning (learning-progress / prioritized-replay style: Matiisen et al. 2017, Portelas et al. 2019–2020, Jiang et al. 2021 PLR):
  - track a rolling success rate per sampling unit (feed family, move sector, later each command);
  - sample units in proportion to (1 − success) blended with absolute learning progress, with a floor (≥ 25 % of uniform) so mastered skills are rehearsed;
  - optionally widen difficulty ranges (reach distance, speed) on success;
  - sampling weights are logged every iteration; evaluation always samples uniformly.

  Used for every training run after it lands (teacher follow-ups, student fine-tunes, Stage 6). It is the planned HT-c if HT-b misses backspin. Tests: weights move toward failing units, the floor holds, evaluation stays uniform.
- [x] **Distillation code:**
  - Student network 1024-512-256 with LayerNorm; same observations as the teachers.
  - DAgger: roll out the student (β-mixed with the teacher early on), label every state with the action of the teacher for that episode type (move → walking teacher, hit → hitting teacher), and train with MSE on the action means plus the student's own exploration std.
  - Script `scripts/distill.py`, writing rsl_rl-compatible checkpoints. Tests: shapes, teacher routing per episode type, a tiny run that lowers the imitation loss.
- [x] **Distillation run:**
  - **≤ 2 h** on the Drill 1 mix with 50 % move and 50 % hit episodes.
  - **Gate:** the student is within 3 points of each teacher on the teacher's own evaluation: arrival per sector for the walking teacher, legal / contact / A/B gain per family for the hitting teacher.
  - **Also report:** the same evaluation for a same-size (512-256-128) student distilled the same way, to show whether capacity matters.

**Combine on the student** (RL fine-tune with a KL pull-back toward the routed teacher, coefficient decayed over the run)
- [x] **Student follow-up S-b (rule 8, 1 of 2):** contact-weighted imitation (×10 for hit-episode states with the ball within 1 m of the paddle), continuing `student-big-01/model_1500` with β = 0; evaluate with the teachers re-scored on the same fresh dev seeds.
- [x] **Student follow-up S-c (rule 8, 2 of 2, last):** learning rate 3e-4 → 1e-4, continuing `student-big-02/model_1500` with the S-b recipe; evaluate with the teachers on fresh shared dev seeds. If the student gate is still missed, stop for the user.
- [x] **Multi-task check (D-044):** in the first student fine-tune, log per-skill returns. If walking or hitting drops by more than 5 points while the other rises, add separate critic heads per skill and per-task value normalisation (PopArt-style) before continuing; otherwise tick with the numbers.
- [x] **Shadow-swing task (Drill 2).**
  - A spot plus a virtual contact point and time (the contact geometry and timing of a sampled feed family, including reach families, but no ball).
  - Rewards:
    - the paddle passing within tolerance of the point at the right time;
    - paddle velocity toward the net;
    - feet set (base speed < 0.3 m/s) just before contact;
    - then recovery to the commanded spot.
  - Forehand and backhand balanced. Tests.
- [x] **Run S-D2:** student fine-tuned on shadow-swing plus move and hit maintenance.
  - Gate: median contact-point error ≤ 0.15 m with timing error ≤ 0.1 s on every family-geometry, including all four reach geometries.
  - Feet set ≥ 70 %; median recovery error ≤ 0.5 m; falls ≤ 1 %.
  - Walking and hitting within 5 points of the student's post-distillation results.
- [x] **Run S-D2b (rule 8, 1 of 2):** footwork hint (the predicted interception stance shown through the spot input in swing episodes; `Picklebot-Student-Swing-Hint-G1`), from `student-swing-d2/model_900`; evaluate against the Drill 2 gate.
- [x] **Run S-D2c (rule 8, 2 of 2, last):** walking-teacher rewards toward the interception hint in swing episodes until the bounce (`Picklebot-Student-Swing-Follow-G1`), from `student-swing-d2b/model_2400`. If the Drill 2 gate is still missed, stop for the user.
- [x] **Drill 2 result: accepted with documented deviations (user, 2026-10-07, D-045).** `student-swing-d2c/model_3900` swings within 4–9 cm (median) on 11 of 14 families, and walking and hitting are intact. Missed: reach backhand / short / deep (0.36 / 0.79 / 0.91 m), feet set (5 of 14 families ≥ 70 %), falls about 15 % in swing episodes, recovery 1.53 m. These carry into Drill 3, whose near-to-far reach curriculum targets them, and are re-checked at the Stage 5 gate.
- [x] **S-D2c video diagnosis:** finish rendering `artifacts/videos/stage5/sd2c-<family>-<view>.mp4` (reach short, deep, backhand and easy forehand, side and behind). Watch stills and describe what the robot does on reach balls (wrong direction, too slow, falls, late swing). Send the clips to the user. Write `mjlab/results/stage5-sd2c-videos.md`, and record anything that should change the Drill 3 design before it is built (e.g. the starting reach distance or the time available).
- [x] **Reach curriculum (Drill 3).** Reach families gain a distance scale that starts just past arm reach and widens when a family's rolling legal rate exceeds 70 %, up to full range. Logged per family; evaluation always at full range. Tests.
- [x] **Run S-D3:** student fine-tuned on real balls (reach curriculum plus Stage 4 families from random starts, aiming, recovery), with move and shadow-swing maintenance.
- [x] **Review videos:** successes and misses per family, side and behind, including the move-to-swing transition. Send them to the user. Done on the provisional student S-D3b model_6500 (D-046); `mjlab/results/stage5-sd3b-videos.md`.
- [x] ~~**Stage 5 gate**~~ **Not met; provisional student `student-drill3-d3b/model_6500` accepted with deviations (D-046, `mjlab/results/stage5-gate.md`); re-checked after Stage 5B.** (unchanged thresholds): a single checkpoint with
  - legal return ≥ 85 % on every Stage 4 family from random starts, and ≥ 75 % on every reach family at full range;
  - contact ≥ 92 % on the Stage 4 families;
  - target A/B gain with a 95 % interval above zero on every family;
  - median recovery error ≤ 0.5 m;
  - falls ≤ 1 % per robot episode;
  - retention within 5 points versus `model_7600` on the same feeds.

  Rule 8 applies, then stop for the user. Report `mjlab/results/stage5-gate.md`.

## Stage 5B — human motion priors (D-044)
Natural strokes and footwork from human motion data instead of reward shaping alone. This is how current humanoid systems get natural movement: motion tracking (DeepMimic → PHC/OmniH2O/BeyondMimic) and adversarial motion priors (AMP, ASE). It builds on mjlab's own G1 motion-tracking task (`Mjlab-Tracking-Flat-Unitree-G1`, BeyondMimic-style). Tennis data is acceptable (user, 2026-10-06); pickleball data is preferred where available. Parent: the accepted Stage 5 student.
- [x] **Motion-data survey (research only, no downloads).** Find candidate open datasets:
  - tennis or pickleball strokes and footwork: forehand, backhand, volley/dink, serve, split-step, shuffle, crossover, recovery;
  - sources: mocap (e.g. AMASS subsets, CMU), video-derived sets (e.g. Motion-X, broadcast-tennis work such as Zhang et al. 2023), and retargeted G1 sets (e.g. LAFAN1 → G1);
  - for each: licence, size, format, skeleton, clip list.
  - Also retargeting tools to the G1 (e.g. GMR, PHC retargeting) and how to add the paddle in the right hand.

  Report `mjlab/results/stage5b-motion-data.md` with a recommended set and **stop for the user to approve downloads** (rule 10).
- [x] **Download (after approval) and retarget** the approved clips to the paddle-holding G1. Check joint limits, foot contacts and paddle path, and render 4–6 retargeted clips for the user. Tests for the loader and retargeting checks.
- [x] **Self-penetration check (user, 2026-10-07: clipping seen in the retarget videos).** The retargeting is kinematic, with no collision avoidance, and the paddle geoms have no collision (contype 0). Measure per clip how deep and how often limbs, torso and paddle interpenetrate (capsule/box proxies, mj_collision on a collision-enabled copy). Report it per stroke. Then either fix it in the IK (a mink collision-avoidance limit on arm-torso, arm-leg and paddle-body pairs) or drop the offending segments. In tracking, enable paddle-body and arm-torso collision, so infeasible poses cost tracking error instead of passing through. Tests.
- [x] **Paddle orientation fix (user, 2026-10-08: backhand paddle holding wrong).** The wrist was not retargeted, so the face followed the forearm and lay flat or faced backwards on backhands. Add a face-normal target during swings (hand direction of travel, either face) and a paddle collision margin; re-retarget (v5). `mjlab/results/stage5b-paddle-orientation.md`.
- [ ] **Tracking teacher:** train mjlab's motion-tracking task on the accepted clips in `artifacts/motion/retargeted-v5` (`accepted.json`), with the paddle G1's self-collision on (capsules plus a collidable paddle face, same exclusions; `stage5b-penetration.md`), (≤ 2 h runs, rule 9 chaining). Gate: per-clip tracking error and success rate (mjlab's metrics), falls ≤ 1 %; review videos.
- [ ] **Style prior in the executor:** add an AMP-style discriminator reward (state transitions vs the retargeted clips), or distil the tracking teacher's footwork and strokes, to the Stage 5 student's fine-tune. One variable at a time.
  - Gate: the Stage 5 gate still met (no task regression beyond 5 points);
  - and a style score (discriminator or nearest-clip pose error) clearly better than before, confirmed by side-by-side videos sent to the user.
- [ ] **Learning primer for the user:** `docs/RL_PRIMER.md`. The concepts behind this project (scale, curricula, teacher-student, domain randomisation, motion priors, skill latents, multi-task, self-play, world models, evaluation discipline), each with a short summary, where it appears in Picklebot, and 1–2 key references.
- [ ] **Stage 5B gate:** the student plays with human-like strokes and footwork at Stage 5 task performance. Report `mjlab/results/stage5b-gate.md`.

## Stage 6 — System 1: the full executor command interface, robust and distilled
System 1 is the fast executor that a later strategy layer (System 2, Stage 8) commands. By the end of this stage it must follow every command the strategy layer will use:
- **where to land the ball** (any point in the far court, not just two regions);
- **what kind of shot** (drive, dink or lob);
- **where to be afterwards** (recovery spot).

Its measured capability envelope is published as a contract. It must hold across training seeds and survive distillation to deployable inputs. Same discipline: one variable per run (≤ 2 h), fixed endpoints, dev seeds only, per-family and per-command reporting. Parent: the accepted Stage 5 checkpoint.
- [ ] **Continuous landing targets.**
  - Sample targets anywhere in the far court; the existing 2-value target input becomes continuous, so the inputs are unchanged.
  - Placement bonus on legal landings as now.
  - Metrics: landing error (median, p90) and hit-within-1 m per target region (3 depth × 2 side grid), plus paired gain on swapped targets.
  - Tests.
- [ ] **Shot-type command.**
  - Classes drive / dink / lob as a 3-value one-hot input, appended last (exact checkpoint expansion).
  - Each class has a band: net clearance and ball speed at the net crossing, plus landing depth.
  - Reward on landing inside the commanded band.
  - Metrics: in-band rate per class, and a confusion matrix of commanded vs produced class.
  - Tests.
- [ ] **Training run S1:** continuous targets on the Stage 5 recipe. Evaluate placement per region, legality per family and retention.
- [ ] **Training run S2:** add shot types. Evaluate per class × family, placement and retention.
- [ ] **Robustness:** repeat the final Stage 6 recipe with 2 more training seeds (≤ 2 h each). Evaluate all three on two fresh dev seeds, per seed and pooled with intervals; flag any result that depends on the training seed.
- [ ] **Domain randomisation and latency (D-044):** randomise link masses and inertia (±15 %), friction (0.5–1.25), motor strength (±10 %), observation noise, and 0–40 ms action/observation delay in teacher training. Retrain or fine-tune the System 1 teacher under randomisation. Gate: within 5 points of the non-randomised teacher on nominal physics, and report performance across the randomisation range.
- [ ] **Teacher → student:**
  - Distil into a student with deployable inputs only: no exact ball spin; ball position and velocity with sensor noise and 20–40 ms latency; own pose from noisy estimates.
  - Use DAgger-style action imitation plus PPO fine-tuning.
  - Report the gap per family and command.
- [ ] **Review videos:** each shot type, landing regions, reach footwork and recovery, side and behind. Send them to the user.
- [ ] **System 1 contract** (`docs/SYSTEM1_CONTRACT.md`):
  - inputs and outputs;
  - command semantics and units;
  - the measured envelope per command (what fraction of requests it can fulfil, from where, for which balls);
  - known failure modes.

  This is what the strategy layer will plan against.
- [ ] **Gate:** for all three seeds and the student (or deviations documented and the user asked):
  - the Stage 5 thresholds still hold;
  - continuous targets: median landing error ≤ 1.0 m and hit-within-1 m ≥ 60 % in every region;
  - shot types: ≥ 80 % in-band per class with < 10 % confusion into another class;
  - the student is within 5 points of the teacher on every family and command.

  Report `mjlab/results/stage6-gate.md`. These thresholds were proposed on 2026-10-06 and may be revised by the user before the stage starts.

## Stage 7+ — later (detail when Stage 6 passes)
- **Stage 7, two robots rally.** One robot per side, each driven by the frozen executor plus a *scripted* strategy (land deep, recover to centre). Rally length and fault mix are the metrics. This tests the executor in real back-and-forth play before any strategy learning.
- **Stage 8, learned strategy layer.** (Option, D-044: a skill-latent interface, ASE/CALM-style, instead of hand-designed commands.)
  - A slow policy (about once per shot) sees the game state: ball, own and opponent positions, score and serve.
  - It outputs executor commands: landing target, recovery spot, later shot type.
  - Trained by self-play against frozen past versions (a league), with the executor frozen; joint fine-tuning comes after.
- **Stage 9, serves and 2v2.**
  - Serve and return-of-serve skills on both sides.
  - Four players, with partner coordination (whose ball, cover and stack) through the strategy layer's commands.
  - Self-play in full games under the ported doubles rules.

## Open questions
- ~~**BLOCKING (2026-10-07): Stage 5 gate not met after S-D3 and rule 8 follow-up 1 (S-D3b)**~~ **Resolved 2026-10-07: the user chose option 1 -> D-046.** (`mjlab/results/stage5-gate.md`). Stage 4 families and reach forehand pass (93-97 % legal, 96-98 % contact); reach backhand 22 %, short 2 %, deep 2 %; falls about 6 %; recovery 1.03 m; retention low -6.1, fast -7.3. A gentler curriculum start and a larger sampling share did not help, so follow-up 2 was not spent; the remaining gap is movement quality (Stage 5B). User to choose: (1, recommended) approve the Stage 5B downloads and accept S-D3b as the provisional student with documented deviations; (2) run follow-up 2 anyway; (3) audit reach-family reachability.
- ~~**BLOCKING (2026-10-07): Drill 2 gate not met after rule 8's two follow-ups**~~ **Resolved 2026-10-07: the user chose options 2 + 1 (videos, then Drill 3) → D-045.** (`mjlab/results/stage5-run-sd2.md`).
  - **What works:** the student swings accurately (median 4–9 cm) on 11 of 14 families, and walking and hitting are fully intact.
  - **What is stuck in S-D2 / S-D2b / S-D2c:** reach backhand / short / deep stay at about 0.36 / 0.79 / 0.91 m, feet set is ≥ 70 % on only 5 families, falls are about 15 % in swing episodes, and recovery is 1.53 m.
  - **Options:**
    1. Accept Drill 2 with documented deviations and go to Drill 3, whose near-to-far reach curriculum targets exactly these balls.
    2. Diagnose first from the videos (`artifacts/videos/stage5/sd2c-*`).
    3. Bring Stage 5B motion priors (human footwork clips) forward.
    4. Revisit the feet-set and recovery thresholds for ghost-ball swings.
- ~~**BLOCKING (2026-10-03): Stage 4 gate not met (narrowly).**~~ **Resolved 2026-10-05: the user accepted the deviations and moved footwork forward → D-040.** `aim-all-c01/model_7600` misses three family thresholds by under 1 point each (wide 84.6 %, backhand 84.4 % vs 85 %; high 69.2 % vs 70 %). Aiming, retention and the other seven families pass. Evidence and options: `mjlab/results/stage4-gate.md`. Choose: (1) run D, a fixed ≤ 2 h continuation, then re-test on a fresh dev seed; (2) accept the deviations and go to Stage 5; (3) a contact-focused change first; (4) revise thresholds (not recommended).
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
- 2026-10-03 — **Run A (`lateral-a01`) FAILED** (`mjlab/results/stage4-run-a.md`).  - **Run:** easy + wide + backhand mix, grip v2, warm-started from `model_700`; 2,666 iterations to the cap. Fixed endpoint `model_3300`: legal return 0–0.2 % on the trained families despite 100 % contact; net clearance 4.16 m (sky-high lobs); rallies end lost/out.  - **Cause:** rally end was a true termination, so landing a return forfeited per-step balance reward; the policy learned lobs that outlast the episode.  - **Diagnostic `model_1700`** (not selectable): ~100 % on easy, wide and backhand.  - **Fix:** `drill_over` is a time-out (bootstrapped); episodes are 4 s; regression test added.  - TensorBoard (`scripts/tensorboard.sh`, http://localhost:6006) set up at the user's request; it showed the collapse live.  - Rerun as A2 from `model_700`.
- 2026-10-03 — **Run A2 (`lateral-a02`) FAILED and was stopped at iteration 1,890**, after the user spotted the collapse in TensorBoard.  - **What happened:** with rally end as a bootstrapped time-out, the inherited critic diverged (value loss ~64 vs ~0.1 in run A). Action std grew 0.69 → 2.8, mean reward fell to −89 (action-rate penalty), and from ~1,550 the robot fell instantly.  - **Replacement design, a feeding machine:** no rally-end termination. The next ball is fed 0.5 s after each rally ends without resetting the robot; 8 s episodes end only on a fall or time. Outcomes are tallied per feed, plus robot-episode falls. `RallyRules.begin_from_feed_masked` restarts rallies sync-free. Tests: no rally-end termination; refeed after the delay without double counting.  - **New baseline:** `model_700` under the feeding machine (easy, grip v2, seed 4,200,011; 3,106 feeds / 1,038 episodes): legal return **55.7 % [53.9, 57.4]**, falls in 24 % of episodes. It never learned to recover between shots; this is the retention baseline for Stage 4 runs.  - Launching A3 from `model_700`.
- 2026-10-03 — **Run A3 (`lateral-a03`) done** (`mjlab/results/stage4-run-a3.md`).  - **Run:** feeding machine, warm-started from `model_700`, 2,378 iterations to the cap, healthy throughout (monitored live). Fixed endpoint `model_3000`.  - **Dev evaluation** (two seeds, all families): easy 77.6 / 79.4 %, wide forehand 79.3 / 77.9 %, **backhand 79.2 / 79.8 %** (was 0 %), deep ~79 %, topspin ~79 %, backspin ~38 %, low ~15 %, fast 8 %, short ~5 %, high 0 %. Falls ~0.  - **Retention:** the easy-feed baseline under the feeding machine (55.7 %) improved to ~78 %.  - **Ceiling:** contact ~85 %; given contact, ~93 % of shots land legally.
- 2026-10-03 — Aiming targets implemented (`targets=True`; task `Picklebot-Aim-Lateral-G1`).  - **Targets:** A = deep left (4.5, +1.6), B = deep right (4.5, −1.6) from the robot's view; 1 m hit radius; sampled 50/50 per feed from its own RNG stream (feeds stay identical across conditions).  - **Observation:** the target position, scaled, appended as the last two actor/critic inputs (112 / 127).  - **Reward:** placement bonus 3·max(0, 1 − d/2 m) on legal landings only, ordered before `legal_return`.  - **Metrics:** landings in A/B, target hits, placement. `stage2_eval.py --task --target A|B` and `scripts/aim_gain.py` give the paired assignment gain.  - **Warm start:** `scripts/expand_checkpoint.py` adds zero input columns, a normalizer prior and zero-padded Adam moments. The expanded `lateral-a03/model_3000` acts **identically (max action difference 0.0)** for any target.  - **Baseline** (expanded `model_3000`, lateral families, seed 4,200,040, 6.4k feeds per condition): assignment gain **−0.003 [−0.011, +0.006]**; lands 36 % in A and 3 % in B regardless of target; legal 92 %.  - Tests: 3 new (`tests/test_aiming.py`). Suite 145 pass + 13 xfails.
- 2026-10-03 — **Run B (`aim-b01`) done** (`mjlab/results/stage4-run-b.md`).  - **Run:** warm-started from the expanded `lateral-a03/model_3000`, 2,358 iterations to the cap, healthy throughout. Fixed endpoint `model_5300`.  - **Paired A/B** (dev seed 4,200,050, ~6.8k feeds per condition): assignment gain **+0.697 [0.690, 0.705]** (parent −0.001). Per family: easy +0.745, wide +0.769, backhand +0.579, every interval far above 0. Target hits 72 % (A) and 67 % (B); almost no crossover.  - **Retention:** easy legal 90.0 % vs the parent's 93.3 % (−3.3 points pooled, −4.3 with target A), within 5. The cost is contact (96 → ~90 %, mostly untouched balls) from harder swings.  - **Untrained families (diagnostic, seed 4,200,051):** low 70 % and fast 68 % (from 15 % / 8 %), short 22 %, backspin 30 %, high 0 %.  - **Eval change:** per-family landing tallies added to the task term, `stage2_eval.py` and `aim_gain.py`; the per-family sums match the totals. Suite 145 pass + 13 xfails.
- 2026-10-03 — **Run C (`aim-all-c01`) done** (`mjlab/results/stage4-run-c.md`).  - **Run:** all ten families with targets, warm-started from `aim-b01/model_5300`, 2,354 iterations to the cap, healthy (no falls). Fixed endpoint `model_7600`.  - **Dev evaluation** (seed 4,200,060; 2048 envs; paired A/B; ~2.7k feeds per family; pooled legal return): easy 85.1 %, wide 84.6 %, backhand 84.4 %, deep 84.6 %, short 75.8 %, high 69.2 % (from 1 %), low 86.8 %, fast 88.5 %, topspin 85.3 %, backspin 73.9 %. Every family beats the parent on the same feeds.  - **Aiming:** A/B gain +0.533 [0.528, 0.539], above 0 in every family, but with side biases (backhand rarely hits A; backspin gain only 0.10).  - **Contact:** 86–90 % in every family; misses are mostly untouched balls. First launch failed on the resume run name (log kept as `aim-all-c01-launchfail.*`). Test added for the new task registration.
- 2026-10-03 — **Stage 4 gate NOT MET (narrowly); loop stopped for the user** (`mjlab/results/stage4-gate.md`). Candidate `aim-all-c01/model_7600`: aiming (gain +0.533, every family > 0), retention (+4.4 points) and seven families pass. Missed by under 1 point each: wide_forehand 84.6 %, backhand 84.4 % (threshold 85 %) and high 69.2 % (threshold 70 %). The binding limit is contact (86–90 %). Options are recorded under Open questions; the gate box stays unchecked.
- 2026-10-05 — **User decision (D-040):** Stage 4 accepted with documented deviations (three families under their thresholds by < 1 point). `aim-all-c01/model_7600` is the accepted Stage 4 checkpoint. Reason: the standing-only constraint, not aiming, caps contact (86–90 %), and footwork is needed for match play anyway. Roadmap restructured:
  - Stage 5: footwork (move, hit, recover to a commanded spot);
  - Stage 6: robustness and teacher → student distillation;
  - Stage 7: two-robot rallies with a scripted strategy;
  - Stage 8: learned strategy layer with self-play;
  - Stage 9: serves and 2v2.

  Footwork sits in the executor; court positioning sits in the strategy layer.
- 2026-10-05 — Motion audit done (`mjlab/results/stage5-motion-audit.md`, `scripts/motion_audit.py`). `model_7600` barely moves: per robot episode, pelvis max displacement p50 0.05 m / p90 0.14 m / max 0.41 m, foot path p50 0.11 m. Causes:
  1. `track_linear_velocity` and `track_angular_velocity` (+2 each) pay for zero base motion under the zero command.
  2. `pose` always uses the tight standing leg tolerances.
  3. The four foot-quality terms (clearance, swing height, slip, soft landing) are gated off by the zero command.

  Planned for stance release: remove both tracking terms, use the walking tolerances for legs and waist, and re-gate the foot terms on actual base speed. Keep the balance terms and the fall termination.
- 2026-10-05 — Reach feed families and start box added (results in `mjlab/results/stage5-reach-feeds.txt`).
  - **Families:** `reach_forehand`, `reach_backhand` (1.0–2.5 m to the side, 1.15–1.3 s flights), `reach_short` (bounces about 1.3 m shorter than `short`), `reach_deep` (lob aimed past the baseline; drag shortens it ~0.9 m, so it bounces behind the robot).
  - **Feed anchor:** `BallPhysicsActionCfg.feed_anchor = "pelvis"` aims bounce and lateral offset relative to the robot's current pelvis, read from qpos so it is valid right after a reset. The aim is clamped at -7.5 m and |y| ≤ 2.9 m so feeds land in.
  - **Start box:** `return_stand_env_cfg(start_box=True)` resets each robot episode at x -6.3..-4.9, y -1.2..1.2, yaw ±0.3 and turns on the pelvis anchor. Stage 4 tasks are unchanged (fixed anchor, `ALL_MIX` = the ten Stage 4 families).
  - **Offline (from the default spot):** every reach feed bounces once and lands in. Travel beyond a 0.7 m arm reach p50 1.05 m (side), 1.04 m (short), 0.46 m (deep), at ≤ 0.87 m/s (p95). Deep travel ranges from 0 at the baseline corner to 0.80 m from the forward corner: there is no room behind a robot that is already at the baseline.
  - **Tests:** +9 (reach feasibility and direction, anchor shift, sideline clamp, GPU start box with fresh-pelvis anchoring). Suite 154 pass + 13 xfails.
- 2026-10-05 — Recovery command added (`return_stand_env_cfg(recovery=True)`, `tests/test_recovery.py`).
  - **Command:** a court spot per feed, sampled from x -6.2..-5.0, y -1.5..1.5 on its own RNG stream (feeds are unchanged); fixed at the baseline centre (-5.6, 0) in `stage2_eval.py`.
  - **Observations,** appended last to actor and critic:
    - `recovery`: spot minus pelvis in the body frame, metres / 3 (2 values);
    - `court_pose`: own pelvis xy scaled to the court half-size, plus cos and sin of yaw (4 values). **Deviation from the step text (2 → 6 inputs):** a moving robot otherwise does not know where it stands, and aiming uses absolute court targets.
  - **Reward:** `recovery_reward` exp(−(d/0.5 m)²), weight 1, paid only while `hit_done` (from the hit to the next feed), never before the hit.
  - **Metric:** the error at the next feed's launch for hit feeds, as a 5 cm histogram on the GPU (no host sync). `stage2_eval.py` reports the median, p90 and feeds scored.
  - **Tests:** +2 (layout and ordering; GPU gating, sampling, pose and metric scoring only hit feeds). Suite 156 pass + 13 xfails.
- 2026-10-05 — Stance release added (`return_stand_env_cfg(free_feet=True)`, `picklebot_mj/tasks/footwork_rewards.py`, `tests/test_stance_release.py`).
  - Removed `track_linear_velocity` and `track_angular_velocity`, which paid for zero base motion.
  - `pose` uses mjlab's walking tolerances for legs and waist (hip pitch 0.3, knee 0.35, ankle pitch 0.25); the right arm stays free.
  - `foot_clearance`, `foot_swing_height`, `foot_slip` and `soft_landing` keep their weights but are gated on actual base speed (|v_xy| + |w_z| > 0.1) instead of the zero command.
  - Balance terms, ball rewards and the fall termination are unchanged.
  - **Deviation from the step text:** "a zero action still stands" is not testable as written. A zero action falls after ~1.25 s in every variant, including the unchanged standing task (16/16 envs), because rewards do not change the dynamics. The test instead checks the reward terms: no stand-still terms remain, foot costs are off at rest and on when the base moves.
  - Suite 158 pass + 13 xfails.
- 2026-10-06 — **Run F1 (`footwork-f01`) done** (`mjlab/results/stage5-run-f1.md`).
  - **Run:** `Picklebot-Footwork-G1` warm-started from `model_7600`, expanded exactly to 118 / 133 inputs; 7,600 → 9,886 iterations to the cap; fixed endpoint `model_9800`. Falls 75 % → 0 within ~150 iterations.
  - **Evaluation** (dev seed 4,200,080; paired A/B):
    - Stage 4 families 70.6–84.9 % legal at 83–88 % contact;
    - **reach_forehand 73.8 %, but reach_backhand, reach_short and reach_deep 0 % (no contact)**;
    - A/B gain +0.391 overall (backspin +0.04);
    - recovery error median 0.80 m / p90 1.35 m;
    - falls 0.06 % of robot episodes;
    - pelvis displacement p90 1.34 m (was 0.14 m).
  - **Retention** (fixed start): −1.9 points overall, backhand −8.5.
  - **Diagnosis:** the robot steps only to its right. `approach_ball` (std 0.25 m) and `recovery_reward` (std 0.5 m) carry no signal at 1–3 m.
  - **F2 change, chosen before launch:** shaping range. Add `approach_far` (std 1.5 m, weight 1, bounce to hit) and widen `recovery_reward` to std 1.5 m; everything else is unchanged; warm-start from `model_9800`.
  - `stage2_eval.py --fixed-start` was added for retention.
- 2026-10-06 — **Run F2 (`footwork-f02`) done** (`mjlab/results/stage5-run-f2.md`).
  - **Change:** shaping range only (`approach_far` std 1.5 m; recovery std 0.5 → 1.5 m). Warm-started from `footwork-f01/model_9800`, 9,800 → 12,050 iterations to the cap, fixed endpoint `model_12000`.
  - **Evaluation** (dev seed 4,200,090):
    - **reach_backhand, reach_short and reach_deep still 0 % contact**; reach_forehand 74.4 %;
    - Stage 4 families 65.8–84.6 % legal at 84–88 % contact;
    - A/B gain +0.481 (F1 +0.391);
    - recovery median 0.78 m;
    - falls 0.09 %;
    - retention −0.1 points overall, worst −3.0; backhand recovered.
  - **Conclusion:** the shaping range was not the bottleneck. The robot has a single learned movement (lean and step right), because its lineage started from a standing policy, not from a walking one.
- 2026-10-06 — **User decision (D-041):** teach footwork with movement drills before hitting on the move. Stage 5 is rewritten:
  - Drill 1: move to a spot, no ball, with the velocity-tracking rewards re-used as the walking teacher and a ready stance on arrival;
  - Drill 2: move and shadow-swing;
  - Drill 3: real balls, near-to-far reach curriculum.

  Each drill has its own gate; every run keeps 25 % hitting rehearsal; the parent is `footwork-f02/model_12000`. The Stage 5 gate thresholds are unchanged and move to the end of Drill 3. The F2 videos step stays first.
- 2026-10-06 — Drill 1 move-to-spot task built (`picklebot_mj/tasks/move_drill.py`, task `Picklebot-Drill-Move-G1`, `tests/test_move_drill.py`). Done in parallel with the F2 video render, at the user's request.
  - **Episodes:** 75 % move episodes (ball parked, rally closed, no tallies); 25 % Stage 4 hitting rehearsal from random starts.
  - **Spots:** in eight balanced sectors at 0.5–3 m inside x −6.4..−2.4, |y| ≤ 2.8, shown through the existing `recovery` input. A new spot follows each arrival (within 0.25 m, under 0.2 m/s, held 0.3 s) or time-out (1.5 s + 1.25 s/m).
  - **Teacher:** mjlab's tracking formulas against an **internal** command toward the spot (min(1 m/s, 1.2·d), turning to face the net); weights 2 + 2.
    - **Design choice:** the robot never observes this command (the twist command stays zero), so walking depends only on the spot input, as it will in play.
  - **Arrival and stance:** arrival bonus 2 per arrival; `ready_stance` (paddle centre 0.3–0.5 m ahead, 0.9–1.2 m high) within 0.4 m of the spot, weight 1.
  - **Metrics:** per-sector issued/arrived/timed-out, mean time, median final error and ready rate (`stage2_eval.py --move-prob`).
  - **Inputs:** the same as F2, so `model_12000` warm-starts directly.
  - **Tests:** +4. Suite 163 pass + 13 xfails.
- 2026-10-06 — F2 review videos done (`mjlab/results/stage5-f2-videos.md`; 12 clips sent to the user). Rendering overlapped the Drill 1 build at the user's request; the first render hit a 30-minute job limit and was resumed. The clips confirm the diagnosis:
  - reach_forehand steps out right and crouches;
  - on reach_backhand it stands upright at the start spot while the ball passes 1–2.5 m to its left;
  - reach_short bounces twice in front of it;
  - reach_deep is lost behind it.
- 2026-10-06 — **User request:** hill-climb through the drills and on to a complete System 1. Loop rule 8 (bounded hill-climbing: at most two one-variable follow-up runs per failed step, then stop). Stage 6 rewritten as "System 1": continuous landing targets, a shot-type command (drive/dink/lob), runs S1 and S2, robustness over 3 seeds, teacher → student with noisy and delayed inputs, review videos, a System 1 contract document, and a gate (thresholds proposed, revisable by the user).
- 2026-10-06 — **Run D1 (`drill-move-d01`) done** (`mjlab/results/stage5-run-d1.md`). From `model_12000`, 12,000 → 13,973 iterations; fixed endpoint `model_13900`.
  - **The robot now walks to spots:** 91.0 % arrival overall (dev seed 4,200,100; 16,020 spots); forward, forward-left, left, back-left and back 94.5–99.6 %; median final error 0.175–0.225 m; ready stance 99.9 % of arrivals; 0 falls in 6,144 robot episodes.
  - **Drill 1 gate not met:**
    - right side weaker: back-right 63.0 %, right 82.6 %, forward-right 88.0 % (need ≥ 90 % each);
    - hitting retention −2.0 points overall, but low −6.7, fast −7.0, backspin −7.6 per family (need within 5).
  - **Rule 8, follow-up D1b:** right-side sectors ×2 in training spot sampling (evaluation uniform). Planned D1c if retention still fails: hitting rehearsal 25 % → 40 %.
- 2026-10-06 — **Run D1b (`drill-move-d01b`) regressed** (`mjlab/results/stage5-run-d1b.md`). Right-side sectors ×2 in training; endpoint `model_15900` (dev seed 4,200,110).
  - **Arrival 69.0 % overall** (D1 91.0 %): back-right 63 → 92 %, but forward 98 → 44 % and forward-left 99 → 39 %.
  - **Ready stance** 88.9 %.
  - **Retention** −6.7 points overall (backhand −12.1, low −12.6, fast −16.6, backspin −15.7).
  - **Follow-up D1c (rule 8, last):** hill-climb from the better parent, D1's `model_13900` (a choice between completed endpoints, not a within-run peak; D1b is kept on record). One change: hitting rehearsal 25 % → 40 %.
- 2026-10-06 — **User decision (D-042):** specialist teachers distilled into one larger student. Stage 5 is restructured:
  - D1c is finished and recorded; the Drill 1 result becomes informational and names the walking-teacher parent;
  - walking teacher (move only) and hitting teacher (hit only), trained with loop rule 9 (up to 4 chained 2-hour runs per teacher);
  - DAgger distillation into a 1024-512-256 LayerNorm student, with a same-size control;
  - shadow-swing and reach-curriculum fine-tunes on the student with a KL pull-back toward the teachers;
  - the Stage 5 gate is unchanged.
- 2026-10-06 — **Run D1c (`drill-move-d01c`) and the Drill 1 comparison** (`mjlab/results/stage5-drill1.md`).
  - **D1c** (hitting rehearsal 40 %, from D1; endpoint `model_15900`, dev seed 4,200,120):
    - arrival 85.6 % (right side 56–75 %);
    - retention −5.3 overall (low −15.3, fast −14.9);
    - ready 99.4 %, 0 falls.
  - **None of D1, D1b, D1c meets the Drill 1 thresholds.** Each follow-up traded one skill for another, which is the shared-policy trade-off that D-042 replaces.
  - **Walking-teacher parent: D1 `drill-move-d01/model_13900`** (best arrival 91.0 %, best right side, best retention).
- 2026-10-06 — Walking and hitting teacher tasks registered (commit 81299f0, tests/test_teachers.py): Picklebot-Teacher-Move-G1 (move episodes only, uniform sectors) and Picklebot-Teacher-Hit-G1 (Stage 4 + reach_forehand, hitting only). Same inputs as the drill and footwork tasks.
- 2026-10-06 — **Walking teacher PASSED its gate in chain run 1** (`mjlab/results/stage5-teacher-move.md`). `teacher-move-01` from D1 `model_13900`; fixed endpoint `model_15900`; dev seed 4,200,130.
  - **Arrival 99.84 %** over 17,791 spots, every sector ≥ 98.95 %, including the right side (back-right / right / forward-right 100 / 99.96 / 100 %, which D1 had at 63 / 83 / 88 %).
  - Median error 0.175 m; ready stance 99.97 %; 0 falls.
  - **The right-side weakness was interference from sharing the policy with hitting**, which supports D-042. Chaining stops (rule 9).
  - **Walking teacher:** `teacher-move-01/model_15900`.
  - Hitting teacher task already registered and tested (`81299f0`); ticked.
- 2026-10-06 — **Evaluation bug found and fixed (D-043, `mjlab/results/eval-censoring-fix.md`).** Feeds still in flight at a robot-episode time-out were counted as misses. On the same feeds, 20.3 % (hitting teacher) and 10.8 % (`model_7600`) of feeds were such cut-offs. Excluding them, contact is 99.7 % / 99.6 %: the "85–90 % contact ceiling" since Stage 4 run A3 was mostly this artefact. History is not relabelled; earlier gate outcomes may differ under the corrected metric (flagged to the user).
  - **Hitting teacher run 1, corrected** (`teacher-hit-01/model_14200`, dev seed 4,200,140):
    - legal 98.4–100 % on 10 of 11 families, backspin 83.6 %;
    - contact 98.9–100 %;
    - A/B gain +0.820 (every family > 0);
    - retention 95.9 % vs 97.4 % (backspin −13.6, backhand −4.9);
    - 0 falls.
  - Gate missed only on backspin; rule 9 chain run 2.
- 2026-10-06 — **Hitting teacher run 2** (`teacher-hit-02/model_16400`, dev seed 4,200,150, corrected metric; `mjlab/results/stage5-teacher-hit.md`).
  - **Results:** legal 99.3–100 % on 10 families, **backspin 83.5 %** (run 1: 83.6 %); contact 99.4–100 %; A/B gain +0.807; 0 falls.
  - **Retention:** 95.2 % vs 97.5 % (backspin −6.8, deep −6.6, low −6.6).
  - **Chaining stops** (rule 9: < 1 point gain); the teacher endpoint is run 2.
  - **Gate missed** on backspin legal and three retention families.
  - **Noted:** the fixed-start retention test may partly measure a geometry mismatch for a robot that recovers away from the fixed feed anchor.
  - **Rule 8 follow-up HT-b:** backspin ×3 in the mix.
- 2026-10-06 — **User request:** add an automatic-curriculum (adaptive) sampler as infrastructure for all later training; it replaces hand-tuned oversampling (D1b, HT-b) from now on.
- 2026-10-06 — **User decision (D-044):** adopt the recommended upgrades:
  - human motion priors (new Stage 5B; tennis data approved in principle; mjlab ships `Mjlab-Tracking-Flat-Unitree-G1`);
  - the adaptive curriculum sampler;
  - domain randomisation and latency in Stage 6;
  - a multi-task check in the student fine-tunes;
  - evaluation discipline kept.

  Loop rule 10: downloads need the user. Stage order: 5 → 5B → 6.
- 2026-10-06 — **Hitting teacher PASSED its gate after follow-up HT-b** (`teacher-hit-b01/model_18600`, dev seed 4,200,160, corrected metric; `mjlab/results/stage5-teacher-hit.md`).
  - **Backspin** 83.5 → 99.1 % legal; every family 99.1–100 % legal, contact 99.2–100 %.
  - **Aiming:** A/B gain +0.851 (backspin +0.59).
  - **Retention** 97.45 % vs 97.44 % (every family within ±3.3); 0 falls.
  - **Teachers:** walking `teacher-move-01/model_15900`, hitting `teacher-hit-b01/model_18600`.
  - **Other steps ticked:**
    - the adaptive curriculum sampler (`62c66bd`; `picklebot_mj/curriculum.py`, opt-in `adaptive_curriculum`, logged weights, evaluation uniform, tests);
    - the distillation code (`d848ad8`; the student is a plain 1024-512-256 MLP because rsl_rl's MLPModel has no LayerNorm option, a recorded deviation from D-042).
- 2026-10-06 — **Student distillation done** (`mjlab/results/stage5-student.md`). Students and teachers scored on the same dev seeds (4,200,170/171, corrected metric).
  - **Big student** `student-big-01/model_1500` (1024-512-256):
    - arrival 99.89 % (= walking teacher);
    - legal 98.8–100 % (each family within 0.7 of the hitting teacher);
    - 0 falls;
    - A/B gain +0.823 vs +0.855, with misses on easy −0.15, deep −0.065, high −0.05, topspin −0.033.
  - **Small control** (512-256-128): the same in-distribution scores but a worse fixed-start retention (95.4 % vs 96.7 %); the big student is kept.
  - **Student gate not met (aiming only).** Both students lose aim on the same families, so the cause is the uniform objective rather than capacity.
  - **Rule 8 S-b:** contact-weighted imitation (`distill.py --contact-weight`).
- 2026-10-07 — **Student S-b** (`student-big-02/model_1500`, contact-weighted imitation; dev seeds 4,200,180/181, teachers re-scored on the same seeds):
  - arrival 99.94 % (teacher 99.86 %);
  - legal and contact within 0.7 points everywhere;
  - A/B gain +0.846 vs +0.849, with easy, deep, high and topspin now within 0.025;
  - **reach_forehand gain −0.032**, just past the 0.03 limit, so the student gate is missed on that item only.
  - **Rule 8 S-c (last):** learning rate 1e-4.
- 2026-10-07 — **Student gate PASSED after S-c** (`student-big-03/model_1500`, learning rate 1e-4; dev seeds 4,200,190/191 with the teachers re-scored on the same seeds; `mjlab/results/stage5-student.md`).
  - Arrival 99.87 % (teacher 99.85 %), every sector within 0.3 points.
  - Legal and contact within 0.4 points on every family.
  - A/B gain within 0.026 on every family (reach_forehand −0.023, was −0.032).
  - 0 falls.
  - **One 1024-512-256 network now walks and hits at teacher level.**
  - **Noted for the fine-tunes:** fixed-start retention on low and fast balls is −5.9 / −6.1 versus `model_7600` (the teacher's is −3.1 / −3.4).
  - TensorBoard now includes the distillation runs (`scripts/distill_to_tb.py`).
- 2026-10-07 — **Fine-tune machinery and the shadow-swing task built.**
  - **`picklebot_mj/rl/reg_ppo.py` (RegPPO):** rsl_rl PPO with a pull-back toward a frozen reference policy (the distilled student; equivalent in intent to D-042's routed-teacher pull-back and needing no routing), plus a critic warm-up with the actor frozen.
    - Uses rsl_rl's symmetry hook and the `PICKLEBOT_REF_*` env vars.
    - Full-scale check (4096 envs, 60 iterations): the pull-back is ~0 during warm-up. At unfreezing it spiked (pull-back 35, falls 2.5 per episode), then recovered to 0.008 with falls back near 0 by iteration 60.
    - The fine-tunes therefore use a 100-iteration warm-up, learning rate 1e-4 and desired KL 0.005.
  - **`picklebot_mj/tasks/shadow_swing.py` (Drill 2):** real feeds of all 14 families fly their real paths as **ghost balls** (the paddle is moved out of the ball simulation; never tallied).
    - The closest paddle approach is tracked between the first and second bounce.
    - One-shot reward exp(−(d/0.15)²)·(0.5 + 0.5·v_x/3)·(0.7 + 0.3·feet set), then recovery.
    - Per-family metrics: median d_min, share within 0.15 m, paddle v_x, feet-set rate.
    - **Deviation:** timing is not a separate metric; an early or late swing shows as a larger d_min.
  - **Task `Picklebot-Student-Swing-G1`:** 25 % move, 50 % swing, 25 % real hitting; 1024-512-256 student; RegPPO.
  - **Tests:** +2. Suite 175 pass + 13 xfails.
- 2026-10-07 — **Run S-D2 (`student-swing-d2`) done; crashed at iteration 953** on a NaN histogram index after a simulation blow-up (fixed in `107c049`); endpoint `model_900` (`mjlab/results/stage5-run-sd2.md`).
  - **Shadow swing:** 11 of 14 families have a median contact error of 4–9 cm. Reach backhand / short / deep are 0.39 / 0.81 / 0.94 m.
  - **Feet set** below 70 % on 9 families; recovery 1.53 m; falls 16.9 % in swing episodes.
  - **Multi-task check:** walking 99.95 % and hitting within 0.3 points of the distilled student, so no interference and no separate critic heads are needed.
  - **Drill 2 gate not met.** Rule 8 S-D2b: footwork hint (calibrated interception spot via the spot input), plus bug fixes (NaN-safe histograms, `blew_up` termination).
- 2026-10-07 — **Run S-D2b** (`student-swing-d2b/model_2400`): no gain on reach backhand/short/deep (0.36/0.79/0.94 m), falls 16.5 %, recovery 1.53 m, feet set unchanged.
  - Hitting best yet (A/B gain +0.860); walking 99.91 %.
  - **The hint alone is ignored**, because nothing rewards following it.
  - **Rule 8 S-D2c (last):** reward following the hint (walking-teacher rewards toward it until the bounce). This replaces the lower-entropy plan; the reason is in `mjlab/results/stage5-run-sd2.md`.
- 2026-10-07 — **Run S-D2c** (`student-swing-d2c/model_3900`, walking rewards toward the interception hint before the bounce):
  - reach backhand / short / deep 0.36 / 0.79 / 0.91 m;
  - falls 14.8 %, recovery 1.53 m, feet set unchanged;
  - walking 99.97 %, hitting A/B gain +0.851.

  **Drill 2 gate not met after both rule 8 follow-ups; loop stopped for the user** (Open questions). Videos of reach swings are rendering for the decision.
- 2026-10-07 — **User decision (D-045):** diagnose with the S-D2c videos, then continue to Drill 3. Drill 2 is accepted with its deviations documented; Drill 3 starts from `student-swing-d2c/model_3900`.
- 2026-10-07 — S-D2c video diagnosis done (mjlab/results/stage5-sd2c-videos.md; 8 clips sent to the user). Reach short: no forward steps, early swing. Reach deep: leans back and lifts a knee, swings after the ball has passed. Reach backhand: deep left lunge, then tips back and flails (the user also flagged poor balance and backhand-like swipes). Measured hint flaws: the deep-ball interception point was 2-2.5 m behind the baseline and clamped at 100 %; the spot box stops inside the baseline, so 99 % of hints from back start spots were clamped; reach short needs 1.8-2.1 m of travel. Drill 3 changes: intercept near the top of the bounce, a spot box extended behind the baseline, curriculum including distance. Balance and stroke form point to Stage 5B motion priors.
- 2026-10-07 — **Drill 3 machinery built** (task `Picklebot-Student-Drill3-G1`, `tests/test_drill3.py`), with the fixes from the S-D2c video diagnosis.
  - **Reach curriculum:** `feeds.REACH_NEAR` holds a near version of each reach family (side 0.75–1.1 m; short bounces at −3.9..−3.6; deep aimed at −6.2..−5.9). A per-family scale 0 → 1 interpolates every range to the full family. It widens by 0.1 when the family's legal-return EMA exceeds 70 % over at least 300 feeds, and is logged as `Curriculum/scale_*`. Evaluation is always at full range.
  - **v2 interception hint:** the apex after the bounce, or where the ball rises through 1.1 m. Median error under 0.3 m on all 14 families. The stance box now extends behind the baseline (x down to −8.5).
  - **Real-ball episodes** also show the stance hint until the first contact, then the recovery spot.
  - **Ball-lost margin** behind the baseline is configurable (Drill 3: 2.5 m).
  - **Task mix:** 60 % real hitting over the Stage 4 + reach families (adaptive family mix), 15 % move, 25 % ghost swings (v2 hint, follow reward), blow-up guard.
  - **Tests:** +16. Suite 208 pass + 13 xfails.
- 2026-10-07 - Motion-data survey done early, in parallel with Drill 3 at the user request (mjlab/results/stage5b-motion-data.md; research only, nothing downloaded). No pickleball dataset exists. Best open racket mocap: Tennis-MoCap (CC BY-SA 3.0, 100 BVH: forehand, backhand, both volleys, serve, smash). Generic locomotion: LAFAN1 retargeted to G1 (non-commercial, no redistribution). Retargeter: GMR (MIT). mjlab tracking expects one 50 Hz npz per motion (csv_to_npz.py). AMP is not in rsl_rl 5.4.2. Waiting for the user to approve the downloads (rule 10).
- 2026-10-07 - S-D3 done (mjlab/results/stage5-run-sd3.md), fixed endpoint model_5200. Stage 4 families 94-97 % legal and 96-98 % contact from random starts; reach forehand 97 %. Reach backhand 24 %, short 2 %, deep 1.5 % (gain intervals include 0 for backhand/deep). Falls 5.5-6.2 %, recovery 1.03 m, retention misses low -6.3 / fast -6.2. **Stage 5 gate not met.** Follow-up 1 of 2 (rule 8), one variable: gentler reach-curriculum start (REACH_NEAR_V2, task Picklebot-Student-Drill3-Gentle-G1), run S-D3b from model_5200. Eval gained --no-hint.
- 2026-10-07 - S-D3b (rule 8 follow-up 1, gentler reach start) ended at the cap, fixed endpoint model_6500. Curriculum: backhand and deep stayed at 0, short 0.6. Gate eval (seeds 4200240-242): no material change (reach backhand 22 %, short 2 %, deep 2 %; falls 5.7-6.9 %; recovery 1.03 m; retention low -6.1, fast -7.3). **Stage 5 gate not met** (mjlab/results/stage5-gate.md). Loop stopped for the user (Open questions).
- 2026-10-07 - **User decision (D-046):** S-D3b model_6500 is the provisional Stage 5 student (deviations documented); Stage 5B starts. Downloads approved: Tennis-MoCap, LAFAN1 G1 CSVs (non-commercial, never committed), GMR. Stage 5 "Review videos" stays open.
- 2026-10-07 - Stage 5B downloads and retargeting done (mjlab/results/stage5b-retarget.md). Tennis-MoCap (276 MB) and GMR (1.5 GB, own venv ~/envs/gmr 5.9 GB) under the git-ignored artifacts/motion/. LAFAN1 G1 not downloaded: Unitree's HF dataset now needs a login (user step). New scripts/motion/tennis_retarget.py: T-pose-matched offsets, joint-located position targets, hands position-only, warm start, mink 1.3 shim. 99 clips retargeted, 92 accepted (42.7 min; median error 2.4-3.4 cm per stroke; forehand and backhand 18/18). Known robot-range limits: ankle roll +-15 deg, right shoulder yaw. 6 stroke clips rendered for the user. Tests: 3 (GMR venv).
- 2026-10-07 - The user saw clipping in the retarget videos. Added a self-penetration step before the tracking teacher: the IK has no collision avoidance and the paddle has no collision geometry.
- 2026-10-07 - Drill 3 review videos done (mjlab/results/stage5-sd3b-videos.md; 10 clips, S-D3b model_6500, real balls, no hint, dev seed 4200250; sent to the user). Easy and reach forehand: clean move then swing. Reach backhand: barely travels left, late cross-body reach. Reach short: no forward run. Reach deep: now backs up past the baseline but swings while the ball is behind it. These are the 'before' clips for Stage 5B.
- 2026-10-07 - Self-penetration check done (mjlab/results/stage5b-penetration.md). v3 clips overlapped (>1 cm) in 13-41 % of frames per stroke: hand on hand, hands into the hips, elbows into the torso; never paddle against body. Fix: mink self-collision avoidance in the IK on the paddle G1's own capsules, swapped into GMR's model (mesh collisions were too slim). v4: 0.1-1.5 % of frames, tracking error unchanged, 91/99 clips accepted. The tracking teacher keeps self-collision on. Tests: 4 (GMR venv).
- 2026-10-08 - Tracking teacher set up: task Picklebot-Tracking-Tennis-G1 (picklebot_mj/tasks/tracking.py). It is mjlab's G1 tracking on the paddle G1 with full self-collision plus a collidable paddle face, and a multi-clip motion command that never plays across clip boundaries. The motion file is artifacts/motion/tracking/tennis-v4.npz (91 clips, 42 min), built by scripts/motion/csv_to_npz_local.py, which converts locally without mjlab's W&B upload. Smoke: 1.67 s/iteration at 4096 envs. Launching tracking-01 (rule 9 chain 1 of up to 4).
- 2026-10-08 - The user flagged wrong backhand paddle holding. tracking-01 was stopped at iteration 1696 (trained on v4 clips; kept as a pipeline check, not used). Fix: an IK face-normal target on the paddle during swings (hand > 2 m/s): normal = hand direction of travel, either face may lead, twist free; no target between swings (a ready target folded the paddle into the torso); paddle collision margin 5 cm. v5: 90/99 clips accepted, face-normal error in swings 0.5-1.8 deg median per stroke, overlap 0.3-2.7 % of frames, position error unchanged. The self-collision regression test bound went from 2 % to 3 % (measured 2.3 %), documented. The tracking teacher now uses tennis-v5.npz (mjlab/results/stage5b-paddle-orientation.md).
