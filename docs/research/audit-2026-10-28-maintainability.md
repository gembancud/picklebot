# Audit: maintainability and lost threads (2026-10-28)

Read-only review of `mjlab/` (package, scripts, tests), `mjlab/results/selfplay.md`, `selfplay-review.md`, `rally-target.md`, `rally-milestones.md`, `docs/PANEL.md`, `docs/DECISIONS.md` (D-038 to D-158), `docs/MJLAB_PIVOT.md` (open questions) and the two literature reviews of 2026-10-27. Nothing was edited, moved or run on the GPU. One CPU-only script read committed result JSONs through `scripts/rally_check.py`'s own functions (numbers in the appendix). Rally run 18 was in its smoke phase at 11:05 on 2026-10-28.

## Summary

- **Refactor: yes, but narrow.** Do not clean up the task registry or delete stale modes. Do make every read self-checking: the checkpoint's saved config (`params/env.yaml`, present for 122 of 138 run dirs) should decide `lam_r`, the leg residual and the teacher gain at evaluation, and the gate scripts should refuse a read whose protocol does not match. That removes the largest class of silent mistakes. Then replace the copy-pasted run drivers with one driver that reads a frozen plan file.
- **Timing.** Run 18's early watcher and endpoint battery will start new processes that import `stage2_eval.py`, `diag/feeder_speed_envelope.py`, `rally_check.py`, `h5f_clean_eval.sh`, `h5c_eval.sh` and `tasks/__init__.py`. Editing those files before run 18 finishes changes run 18's pre-registered reads. Bash also reads a running script as it goes, so `rally_run18.sh` must not be touched. Until then, put new code in new files only.
- **Biggest missed thread.** P(5+) is about feeder-ball legal x (partner-ball legal)^4. In log terms the partner-ball term costs about 7 times more than the feeder term (run 14: ln 0.819 = -0.20 against 4 ln 0.705 = -1.40). Runs 11-17 aimed at feeder balls (the M1 bar) and left/back feeder reach. The weakest shots in every rally are shots 2 and 3 (run 14: 59 % and 67 % against 76-78 % later). No direction split or shot-position diagnosis was ever run on partner balls.
- **The learning-rate floor.** From rally run 2 (iteration 5,200) through run 17 the rate sat at 1e-5, for the actor and the critic (one optimizer). Large, well-represented signals still moved behaviour at that rate (run 4's footwork, run 8's pace). Weak signals and new pathways did not (runs 9, 11, 12, 16, 17). Those "did not help" results, the trend projections of round 28 and D-158's finding are confounded and should be re-tested now.

---

## Part 1. Maintainability

### 1.1 Environment variables

All task-level reads happen at import time. `picklebot_mj/tasks/__init__.py` builds every registered task (env and play configs) when it is imported, so the variables in force at that moment shape every task in the process, training tasks included.

| Variable | Read in | Default | Set by | Absence / presence effect | Risk |
|---|---|---|---|---|---|
| `PICKLEBOT_LAM_R` | `tasks/__init__.py` `_residualize` (line 999) | the task's own `lam_r` (1.0 unless passed) | rally_run14-18 reads, lr_sweep, `diag/planner_headroom.sh` (`export`), teacher_obs_check | **Absent at eval: a lam_r-2 checkpoint (runs 14, 16, 17, sweep, 18) is read at lam_r 1, same shapes, strict load passes, no error.** Present at training: overrides lam_r for every residual task whose lam_r is not replaced afterwards (run 10-13 tasks, and even `Court-Res2` / `Volley-Res2`, which pass 2.0 explicitly). Not written to any result JSON. | **High, silent** |
| `PICKLEBOT_TEACHER_GAIN` | `_residualize` -> `_teacher` | 1 | rally_run17 reads | **Absent: a run-17 checkpoint is read with its input at 1/30 scale, silently.** | High, silent |
| `PICKLEBOT_TEACHER` | `_residualize` | off | rally_run16/17 reads | Absent: obs width 124 vs 129, strict load fails. Loud. | Low |
| `PICKLEBOT_LEG_R` | `_residualize` | 0 | rally_run12/13 reads | Absent: action width mismatch, load fails. Loud. | Low |
| `PICKLEBOT_RES_BASE` | `_residualize` | `RES_BASE` (s5c-18-merge17/model_32874) | no script | **Present: swaps the frozen base executor of every residual task, training too. Not recorded in result JSONs.** | Medium, silent |
| `PICKLEBOT_CONTROLLER` | `latent_reach.py` line 77 | task checkpoint (latent-07) | `h5f_c2_h1decoder.sh` | Present: swaps the frozen H1 controller for any latent task (comment says "evaluation only", code does not enforce it). Recorded in `stage2_eval` JSON only. | Medium |
| `PICKLEBOT_V2_BASE` | 3 ResC tasks | `_s5e_base()`: the newest `*_s5e-01-consolidate` dir found by a glob at import | no current script | Import-time filesystem dependence; a "missing" path is returned silently. Historical tasks only. | Low |
| `PICKLEBOT_CRITIC_WARMUP` | `CriticWarmupRunner` | **50** | every rally run 3-18 sets 0 | Absent: 50 actor-frozen updates. With `ScheduledPPO`, the warm-up wrapper and the schedule's own update counter interact (the schedule advances while the actor is frozen, and `hold_lr` resets the rate each update). | Medium |
| `PICKLEBOT_ENVS` | `train_run.sh` | **4096** | run scripts (12,288) | Absent: one third of the batch, silently. | Medium |
| `PICKLEBOT_WALL_CAP` | `train_run.sh` | **7000 s** | run scripts | Absent: a 2 h cap; the "last checkpoint before the cap" endpoint rule then picks a different endpoint. | Medium |
| `PICKLEBOT_LR_PEAK` | `rl/sched_ppo.py` | none (crash) | lr_sweep, run 18 | Loud. | Low |
| `PICKLEBOT_LR_TOTAL` | `sched_ppo.py` | 0 | run 18 (4000), lr_sweep (0) | **Absent: no cooldown, silently.** Not checked against `--agent.max-iterations`. Schedule state is not in the checkpoint: a crash-relaunch restarts the warm-up and shifts the cooldown. | Medium |
| `PICKLEBOT_LR_WARMUP`, `_LR_COOLDOWN`, `_LR_FINAL`, `_KL_GUARD`, `_STD_MIN`, `_SCHED_LOG` | `sched_ppo.py` | 50, 0.2, 1e-5, 0.05, 0.1, none | lr_sweep, run 18 | Defaults equal the run-18 values; logging only for SCHED_LOG. | Low |
| `PICKLEBOT_KL_PROBE_OUT`, `_KL_FIXED_LR` | `rl/kl_probe.py` | required / none | `diag/kl_probe.sh` | Diagnostic. Probe b showed the trap: the resume reloads the optimizer's rate after the probe set it. | Low |
| `PICKLEBOT_RESUME` | `h5f_clean_eval.sh`, `h5f_run0.sh` | 0 | by hand | Present: keeps any existing output file with the same TAG, even from another checkpoint. | Low-medium |
| `PICKLEBOT_REF_*`, `_CRITIC_WARMUP_ITERS` | `rl/reg_ppo.py` | see file | `train_student.sh` | Stage 5 students only. | Historical |
| `PICKLEBOT_STYLE_SAVE/LOAD`, `_GOAL_BANK`, `_OWN_REPLAY`, `_OWN_REPLAY_5H` | tasks | paths | historical scripts | Presence-only overrides. | Historical |

**Mitigation today:** about 50 hand-written `PICKLEBOT_LAM_R=2` prefixes. I checked runs 14-18, the sweep and the headroom read: they are set correctly. Nothing would catch the next one that is missed, and the JSONs cannot show it afterwards.

### 1.2 Task registry

- **116 task ids** in one 2,232-line module, all built at import (232 configs per import).
- **Composition by mutation chains.** Each task calls its parent's builder and edits the result. Run 17's task sits about 30 builders deep (`..._lamr2_teacher30 -> ..._lamr2 -> ..._pace25 -> ... -> _latent_court_v2_res -> _residualize(_latent_court_l3) -> _latent_court -> _latent_drill3_prior5 -> ... -> return_stand_env_cfg`).
- **Names accumulate modifiers:** `Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-Teacher30-G1` has 13.
- **Order-dependent rewards.** `legal_return` must be the last reward because it clears the step flags. About 15 builders pop and re-insert it by hand. Per-task tests check it; no test checks it for every registered task.
- **Training vs evaluation tasks differ by design.** Every rally checkpoint is read through `Picklebot-Latent-Court-Res-G1` / `-V2-Res-G1` (the frozen batteries), not its training task. Only the network shapes are checked (strict load); action-term parameters are not.
- **Good:** the `test_dNNN_*_differs_only_in_*` tests in `tests/test_stage5f.py` (64 tests) pin each new task to one change. Keep that pattern.

### 1.3 Run drivers and evaluation scripts

- **180 files in `mjlab/scripts`.** 18 rally drivers (plus 13 smoke and 2 init scripts), 14 Stage 5F, 15 Stage 5G and 6 Stage 5H shell scripts, each 30-80 lines.
- **Copied blocks:** the early-kill watcher is pasted into 37 scripts, the read specs (`EV=/MV=/CV=/PA=`) into 27. They differ only in seeds, run names, the `PICKLEBOT_*` prefixes and the check mode.
- **`rally_check.py`** has 13 early modes. Most re-implement the same guard lines (court main, drill v2, move arrival, falls, partner and feeder lines) with small changes. Two defects:
  - an unknown mode falls through to `target()`, and `target` never returns a non-zero exit code;
  - a crash inside a check (a missing key, a typo) exits non-zero, which every watcher reads as a KILL. D-112 fixed this for crashed evaluations but not for crashed checks.
- **No protocol check in the gates.** `m1`, `target`, `teacher-gate` and `sched-gate` do not verify the hand-off (the pairs summary records `handoff`), envs, seconds, task, seed or checkpoint of the JSON they score.
- **Run-dir lookup by suffix** (`ls -d *_$RUN | tail -1` in `stage2_eval.sh` and every watcher) takes the newest matching dir. A reused run name (run 16's relaunch) silently changes which dir is read.

### 1.4 Logic duplicated between training and evaluation

- **The M1 pair-read setup** is coded in `stage2_eval.py` flags and copied by hand into `diag/feeder_speed_envelope.py`, `diag/ready_contact_split.py` and `diag/pair_move_bug.py` ("as stage2_eval.py's M1 read"). The direction-split gate lines depend on the copy staying in sync.
- **"Build env + infer hidden dims + strict load + inference policy"** is repeated in 11 scripts, 38 scripts in all build an env from a task.
- **`wilson()`** is defined twice, with different behaviour at n = 0 (`None` vs `[0, 0]`).
- **Feeder-ball legal is computed two ways** (`pair_stats` from side counts, `boot_low` from court counts). On every committed read since D-138 they agree within 0.0002 (appendix), so this is a maintenance risk, not a current error.
- **Two rally definitions:** the `--rally` streak in `stage2_eval.py` (time-outs end a rally without a failure) and `pairs.py`'s `len_hist` (the target's). They answer different questions; the names do not say so.

### 1.5 Dead code and stale modes

- `BallPhysicsActionCfg` has about 65 flags spanning Stage 2 to rally run 16. Many are only used by historical tasks: reach and learning-progress curricula, hint variants, ghost swings, failure weighting, replay files, per-episode latency, the compensator, timed goals.
- Historical task families: Stage 4 aiming, the students, tracking, latent reach, timed reach, timed ball, the Stage 5E/5F latency tasks.
- **None of this should be deleted.** Old checkpoints must stay loadable and their tasks reproducible. The cost is reading time, not correctness. Mark them as historical in one place instead.

### 1.6 The silent-mistake risks, ranked

1. **`PICKLEBOT_LAM_R`** absent at evaluation, or leaking into training (1.1). Same shapes, no error, not recorded.
2. **`PICKLEBOT_TEACHER_GAIN`** absent at evaluation.
3. **Result files do not carry the policy interface** (`lam_r`, `leg_r`, teacher gain, base checkpoint, controller). A wrong read cannot be found later. The data needed to check it already sits next to each checkpoint in `params/env.yaml`, except in the 11 hand-made init/surgery dirs (for example `lrsweep-init`, `rally-16-teacher-init`, `rally-14-lamr2-init`).
4. **Gates score whatever JSON they are given:** no hand-off, envs, seconds, seed or checkpoint check; unknown modes fall through; checker crashes become kills.
5. **`PICKLEBOT_RES_BASE` / `PICKLEBOT_CONTROLLER`** silently swap frozen networks in every task in the process.
6. **Run-dir lookup by suffix**, and `PICKLEBOT_RESUME` keeping stale outputs.
7. **Training defaults:** 4,096 envs, a 7,000 s cap, a 50-update critic warm-up, and no cooldown when `PICKLEBOT_LR_TOTAL` is absent. `launch.json` records the env count but not the other `PICKLEBOT_*` variables or the schedule.
8. **The schedule restarts on relaunch** (ScheduledPPO keeps its update count in memory).
9. **Training seeds are not checked.** `TRAIN_SEEDS` is 1-999, but the KL probes, the sweep and run 18 trained on 4219950-4219966 from `DEV_EVAL_SEEDS`. This is logged in the ledger and no eval seed was reused, but it breaks the invariant `seeds.check_disjoint` exists to protect.
10. **Editing shared evaluation files while a run's watcher or endpoint is pending** changes that run's pre-registered reads.

### 1.7 Recommendation: a staged, narrow refactor

The constraints: old checkpoints must load and evaluate with the same configuration (GPU reads are not bit-reproducible, D-121, so "identical" means the same config and agreement within the identical-run spread of about 1.4 points); results and the decision log are append-only; run 18 is training.

**Stage 0: now, no shared file touched (about 2 hours).**
- A new CPU-only script, for example `scripts/interface_audit.py`. It parses `params/env.yaml` with a loader that ignores the `!!python` tags. It prints each run's policy interface: action-term class, `lam`, `lam_r`, `wrist_r`, `leg_r`, H1 checkpoint, base checkpoint, actor observation names in order with their scale and history length. Use it to list all 138 run dirs and flag the 11 without a config.
- An appended D-159 (see 2.4). `DECISIONS.md` is not valid UTF-8; append with a byte-preserving method and check the diff.

**Stage 1: after run 18's endpoint battery, evaluation side only (about 1 day plus about 1 GPU-hour of parity reads).**
- One helper, for example `picklebot_mj/evalkit.py`: build env -> infer hidden dims -> strict load -> inference policy. Use it in `stage2_eval.py` and the diagnostic scripts. It also replaces the hand-copied M1 setup with one function.
- **The interface guard,** inside that helper:
  - read the checkpoint's `params/env.yaml`, or an `interface.json` sidecar for surgery dirs;
  - compare the policy-interface fields with the evaluation config;
  - refuse on a mismatch unless the caller names the field (`--allow-interface-diff lam_r`);
  - write the fingerprint, the `PICKLEBOT_*` environment and the git commit into every result JSON.
  - Sensor noise and delay fields are excluded on purpose: training and the frozen batteries differ there by design (D-113).
- **Better still: `--interface-from-checkpoint`.** The evaluation copies `lam_r`, `leg_r` and the teacher gain from the checkpoint's config. `PICKLEBOT_LAM_R` stays for exact reproduction of old command lines, and the read errors if the two disagree.
- **Sidecars** for the 11 init dirs, generated from the parent's `env.yaml` plus the known surgery. From now on, `lam_r_init.py`, `expand_checkpoint.py`, `leg_residual_init.py` and `fresh_init.py` write one.
- **Gate hardening in `rally_check.py`:**
  - `m1` / `target` / gates assert hand-off `contact`, 2,048 envs, 120 s, the task id, a seed in the run's ledger allocation, and the checkpoint path;
  - unknown modes exit with an error; `target` returns its verdict;
  - watchers distinguish "CHECK CRASHED (no kill)" from a kill.
- **A golden regression test (CPU):** run every old `rally_check.py` mode on the committed result files and compare verdicts and printed numbers before and after.
- **Parity reads:** a 64-env pair read and a short court read of run 14's model_27798 with the old and new code on one seed, compared against the identical-run spread.
- **Risk:** low. The guard only reads, and with correct inputs it passes. The main risk is a false refusal on an old run; `--allow-interface-diff` is the escape hatch, and it is recorded.

**Stage 2: training side, for new runs only (1-2 days).**
- `train_run.sh` refuses to start when an eval-only variable (`LAM_R`, `LEG_R`, `TEACHER*`, `RES_BASE`, `CONTROLLER`) is set. It requires `PICKLEBOT_ENVS` and `PICKLEBOT_WALL_CAP`, asserts the seed is in `TRAIN_SEEDS` (or a recorded exception), and writes every `PICKLEBOT_*` variable into `launch.json`. Shell-level only: no task or checkpoint changes.
- **ScheduledPPO v2** in a new class (leave the one run 18 uses unchanged):
  - schedule position derived from the iteration number and a recorded start iteration, so a relaunch continues the schedule;
  - refuses if the cooldown total does not match `max_iterations`;
  - logs value loss and explained variance next to the KL shares.
- **One run driver** (`scripts/rally_run.py` or one bash template) that reads a committed, frozen `plan.json`:
  - task, parent, seeds, early checkpoint, read specs, the named kill lines, endpoint seeds, environment;
  - it resolves the run dir from `launch.json`, not by suffix;
  - the old drivers stay as historical files and are never rerun.
- **Composable early-check lines** in `rally_check.py`. The old mode names stay as aliases, proved equal by the golden test.

**Stage 3: optional; defer unless many more variants are coming (2-4 days).**
- When the GPU is free, dump all 116 task configs to YAML once and commit the dump as a golden file.
- New runs could then register short ids (`Picklebot-Rally-R19-G1`) built as "named base + a declared list of overrides". The override list goes into `launch.json`, and the "differs only in" test is generated from it.
- Do not rewrite the 116 existing builders. If you ever do, the golden dump must match byte for byte.
- **Not recommended:** deleting stale flags or tasks, renaming ids, moving modules, reformatting. All of that is cosmetic, it risks old checkpoints, and it removes no class of mistake.

---

## Part 2. What was missed

### 2.1 Conclusions reached while the learning rate sat at 1e-5

The KL check (selfplay.md) shows the rate pinned at rsl_rl's floor from rally run 2's iteration 5,200 through run 17. Actor and critic share one optimizer, so the critic also learned at 1e-5 while new reward terms were added (runs 8-11) with no critic warm-up. The observation normalizer is effectively frozen too (count about 1.5e10). At that rate, strong signals in existing outputs still moved behaviour (run 4's footwork +23 points, run 8's pace). New rows or columns and weak signals did not.

| Where | Conclusion as recorded | Engaged? | Confounded by the floor? | Re-test? |
|---|---|---|---|---|
| Run 3 (D-139) | Continuing gives little | flat | Yes. The sweep's 1e-4 arm gained +3.8 points of P(5+) in 400 iterations. | Run 18 is the re-test. |
| Round 28 / D-142 / D-143 | Partner-ball flat at 52-56 % for 4-5 runs; M2 and the target "out of reach within these rules"; trend +2.1 points per run | — | Yes: runs 3-6 were all at the floor. | Re-project from run 18's slope before any 25-90 GPU-hour option. |
| Run 6 (D-143) | Turning off the stale `stance_progress` term did not help, so it stays on from run 7 | small term | Yes | Yes, cheaply; see 2.2 item 7. |
| Run 7 (D-144) | keep_alive x2 makes deeper, faster shots | yes | Mostly not | No |
| Run 8 (D-145/146) | Pace ceiling -50 costs 2.8 points of feeder balls | yes (bootstrap -3.6 to -2.0) | Partly: the cost might shrink with a learner that can re-adapt. | Low |
| Run 9 (D-148) | Partner-only pace gate does not engage | no (5x weaker) | Yes: a weak signal at the floor | Low |
| Run 11 (D-150) | A +50 bonus on the five weakest feeder families moved nothing (-0.3) | no | Yes: a weak signal, a 1e-5 critic, no warm-up | **Yes.** The sweep shows that with a working learner the reward pulls toward the common balls (left/back contact fell in every arm), so re-weighting toward weak balls is now a real lever. Round 33's option (a), a heavier weak-family mix, was never run. |
| Run 12 (D-152) | Leg residual +-0.1 rad does not engage (rows at 0.11 vs 0.28) | no | Yes: new rows at the floor | Low; the latent route is better (round 37). |
| Run 13 (D-153) | Leg residual +-0.3 rad breaks the gait; route closed | yes, through exploration noise | Not mainly | No |
| Run 15 (D-155) | lam_r 3 is worse; "the useful range is about 2 sigma" | yes, negative | Partly: the inexact 2/3 init for saturated rows, a 1.5x step, and no room to re-adapt | Low-medium |
| Runs 16-17 (D-156-158) | The teacher input is unused; "fine-tuning cannot grow a new pathway within a run" | no | **Yes, fully** (D-158 says the rate was pinned) | **Yes**; see 2.2 items 2-3. |
| Round 40 options | Teacher from scratch, accept run 14, bigger net, retrain the controller | — | Premised on the floor | The cheapest option, run 17's task with the fixed optimizer, was not on the list. |
| LR sweep (2026-10-28) | No rate gains left/back | yes | No (after the fix), but only 400 iterations, no critic warm-up, frozen normalizer | It is a diagnostic; run 18 is the real read. |

### 2.2 Missed threads, ranked by how likely they matter for 80 % P(5+)

1. **Partner balls carry the target; shots 2-3 are the weak link.** *High; cheap diagnostic.*
   - P(5+) is close to f x q^4, with f the feeder-ball rate and q the partner-ball rate. For run 14 the f x q^4 estimate is 0.203 against 0.187 measured.
   - The q term costs about 7 times more than f in log terms. Even at f = 0.90 the target needs q of about 0.971.
   - Next-shot rates (run 14's target read): shot 1 (the feeder return) 0.797, shot 2 0.593, shot 3 0.669, then 0.761, 0.778, 0.768. Shot 2 is the lowest in every committed read since run 2.
   - Round 29 noted survival conditioning, but the dip is large and stable. A plausible cause: the return of a hard feed is a hard ball for the partner. Run 7's premise read found the fast third of partner balls was reached 44 % of the time against 74-76 % for the rest.
   - **Never measured:** the direction split for partner balls (`feeder_speed_envelope.py` covers feeder balls only), and partner-ball legal by shot position against incoming speed and origin.
   - Runs 11-17 all aimed at feeder balls (the M1 bar). M1 is a milestone; the frozen target is dominated by q.
2. **Re-test the floor-confounded results with the working optimizer**, after run 18, one change each (see 2.1). *High.*
   - First: run 17's teacher input, or better item 3's deployable form, on run 18's optimizer, with the normalizer stats for the new columns re-estimated (lit review section 5).
   - Second: the weak-family mix or the feeder bonus.
   - Then re-project reachability.
3. **The stance spot or predicted contact on every ball, as a deployable input.** *High.*
   - The user decided this in D-096 (decision 3: "give the executor the interception (stance) spot on every feed"), and D-097 (item 2) specified a planner on noisy, delayed observations. It was built for drill-v2 feeds only: D-116 left court feeds without it, and partner hand-offs get none.
   - The e4 teacher used the *true* state, so it needed distillation. The noisy planner already exists (`planner_mode = "noisy"`) and uses only what the robot sees.
   - Literature: an explicit predictor and base target is "almost universal". PACE reports "almost no successful returns" without its predictor. The target is a command the controller is trained to track, with a base-tracking reward active only before contact (HITTER, PACE).
   - Protocol note: the M1 and target read task has the planner off. An agent-side predictor computed from the actor's own observations changes the agent, not a bar, but the panel should record that in a D-entry before the first read.
4. **The crossing-vs-contact feeder gap is unexplained and is larger than the M1 gap.** *High for M1, medium for the target.*
   - On the same checkpoints, feeder-ball legal reads 4-6 points higher with the crossing hand-off: run 5 86.3 vs 81.9 %, run 10 86.4 vs 80.1 %, run 14 86.7 vs 81.9 %. Under crossing it is above M1's 85 %.
   - D-139 called it "pair state", and the 2 s refeed read ruled out recovery time. The cause was never found.
   - It is either behaviour (the robot's state when the feeder ball fires after a longer rally) or an artefact of the contact hand-off path. Since every target read uses that path, it should be explained before more feeder-ball training.
   - A read split of feeder-ball outcomes by the robot's state at launch (distance to its recovery spot, time since its last contact, whether it just hit) on one checkpoint would settle it.
5. **The residual is bounded around a frozen base that never learned rally footwork.** *Medium-high.*
   - Every rally policy is a residual within lam_r sigma of `s5c-18-merge17` (Stage 5C run 18). The one lever that worked, lam_r 2, loosened exactly that bound.
   - D-091 planned "consolidation merges every 3-4 PPO runs, to lift the residual's bound". It was tried once (Stage 5E run 1: an 11-minute distillation that lost skill and was killed) and never again.
   - With a working optimizer: consolidate run 14 or 18 into a new base (DAgger to convergence, then PPO), then a fresh residual around it.
6. **The residual-prior tax was never tested on the rally line.** *Medium.*
   - `residual_prior_nll` (-0.05 x sum (lam_r tanh a)^2, 3x in move episodes) charges for every latent move away from the frozen base, the move a left or back step needs.
   - D-110 pre-registered a "style tax" run (the same run with the style weight halved) once skill plateaus. It was never run.
   - The rally target does not gate style. A relaxation needs its D-entry and D-110's realism guards (falls, jerk, foot slip).
7. **A known-wrong reward term is still on.** *Medium-low on its own, cheap.*
   - D-142 found `stance_progress` pulls the pelvis toward a stale spot on court feeds and partner hand-offs (the last planned spot, or (0, 0) after a reset). Run 6 set it to 0 and, at the floor, saw no change, so runs 7-18 kept it.
   - It is in run 18's smoke log (-0.005 per episode).
   - Either point it at the planner's or the true stance spot on every live ball, which is also the literature's phase-switched approach reward (Phybot, HITTER), or set it to 0 as a correction.
8. **Run 18 skipped parts of the restart recipe** (literature review section 6). *Medium.*
   - Skipped: a normalizer refresh, a critic warm-up after 15 runs of critic learning at 1e-5, and value-loss and explained-variance monitoring.
   - Watch run 18's TensorBoard value loss and its `results/rally-18-train.jsonl` KL shares.
9. **Why output 30's std collapsed is "not known yet".** *Medium-low.*
   - The floor of 0.1 now forces noise on that latent dimension. If a real cost (falls, the residual prior) drove the collapse, the floor fights it.
   - Check which reward term's gradient shrinks that std, and watch fell_over and output 30's KL share in run 18.
10. **An asymmetric critic with privileged contact information was never tried.** *Medium.*
    - Contact point and time to contact as critic-only inputs. The actor is unchanged, so no student is needed. `expand_checkpoint.py` already widens critics.
    - The literature notes that most "privileged" work in this area uses an asymmetric critic, not teacher-student distillation. It may sharpen credit for early footwork.
11. **Untried checks on whether the learner is limited:** a larger-batch control (Beukman 2026), plasticity probes (dormant units, weight norms, feature rank), and a fresh residual from zero init with the new optimizer (tests lost plasticity in the 17-warm-start lineage). *Low-medium.*
12. **Untried self-play forms:** a lagged-snapshot partner and rally-state training (From Hitter to Player). The shared current policy plays both sides. *Low for now.*
13. **D-063's third controller fix, "a root-velocity channel beside the latent",** was never tried. Item 3 covers the same need more cheaply. *Low.*

### 2.3 Literature ideas never tried

- **Continued-training review:** normalizer refresh; critic warm-up then an actor ramp (PIRLNav); `std_type="log"`; a per-dimension KL cap; a separate parameter group or higher rate for new columns (architecture's round-39 option); KL-to-reference with resets (ProRL); L2-to-init or soft shrink-and-perturb; weight averaging; a larger batch; plasticity probes; a fresh-from-zero residual.
- **Already done:** fresh Adam, a std floor, a fixed schedule with a KL guard, warm-up, a 1-sqrt cooldown (run 18), per-output KL logging, the new-column zeroing ablation (run 17).
- **Racket-sports review:** contact and base target as tracked commands, with a pre-contact base-tracking reward (HITTER, PACE); phase-switched and annealed shaping (Phybot, Chen et al., OP3); rally-state training against a lagged copy; an asymmetric privileged critic; end-to-end training from scratch with a predictor.
- **Tried in a form the review argues against:** the contact point as an optional extra input to a residual on a frozen stack (runs 16-17).
- **Framing to carry forward:** no paper reports 95 % or more per shot on closed-loop two-robot rally states; the target needs about 96 %. Re-project reachability from run 18 before choosing a 25-90 GPU-hour option.

### 2.4 Record-keeping

- **No D-entry since D-158.** The KL check, the LR sweep (with its pre-registered "no full run" outcome) and run 18 (user-approved, judged on rally numbers) are only in `selfplay.md` and commit messages. PANEL.md asks for a D-entry for direction changes.
- An appended D-159 should also:
  - record that the training seeds 4219950-4219966 came from the development block;
  - state that D-158's "finding" and round 28's reachability verdict were made with the rate at its floor. Do not rewrite them.

---

## Appendix. CPU read of committed results (`rally_check.py` functions; no mjlab import)

| Read | Hand-off | Feeder legal | Partner legal | P(5+) | Next-shot rates, shots 1-6 |
|---|---|---|---|---|---|
| rally-05-target | contact | 0.819 | 0.552 | 0.087 | 0.794, 0.461, 0.537, 0.655, 0.678, 0.684 |
| rally-05-target-crossing | crossing | 0.863 | 0.416 | 0.047 | 0.854, 0.352, 0.425, 0.596, 0.617, 0.599 |
| rally-10-target | contact | 0.801 | 0.631 | 0.133 | 0.775, 0.512, 0.627, 0.716, 0.746, 0.723 |
| rally-10-target-crossing | crossing | 0.864 | 0.498 | 0.074 | 0.856, 0.420, 0.506, 0.623, 0.655, 0.644 |
| rally-14-target | contact | 0.819 | 0.705 | 0.187 | 0.797, 0.593, 0.669, 0.761, 0.778, 0.768 |
| rally-14-target-crossing | crossing | 0.867 | 0.565 | 0.105 | 0.858, 0.504, 0.546, 0.658, 0.675, 0.673 |
| lrsweep parent (run 14) | contact | 0.818 | 0.704 | 0.185 | 0.793, 0.593, 0.670, 0.760, 0.773, 0.764 |
| lrsweep 1e-4 arm | contact | 0.806 | 0.751 | 0.223 | 0.779, 0.610, 0.713, 0.801, 0.823, 0.822 |

- The two feeder-ball definitions (side counts vs court counts) agree within 0.0002 on every read after D-138. Run 2's read differs by 1.2 points, the documented D-138 fall-counting fix.
- The 1e-4 arm gains on shots 2-6 and loses on shot 1 (the feeder ball): the same pattern as its left/back result.
