# Training-loop audit (2026-10-28)

Scope: the optimizer side of the rally runs. rsl_rl 5.4.2 PPO as installed in `~/envs/picklebot-mj`, mjlab 1.6.0's runner and
train script, our subclasses in `mjlab/picklebot_mj/rl/` (`sched_ppo.py`, `kl_probe.py`, `reg_ppo.py`), the task
`Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1` (registered at
`mjlab/picklebot_mj/tasks/__init__.py:2157-2171`, runner `CriticWarmupHoldLrRunner`, rl cfg `_s5e_rl_cfg`), the residual
action term, `scripts/train_run.sh`, `scripts/fresh_init.py`, and how resume works.

Method: I read the code. I loaded checkpoints on the CPU (no mjlab, warp or CUDA imports) to look at std parameters, Adam
state, normalizer statistics and weights. I also read the training logs and the ScheduledPPO JSONL logs. I did not run the
environment. Every probe that needed observations used synthetic inputs, and I say so wherever that limits a conclusion.
The scratch scripts are in the session scratchpad (`ck.py`, `hist.py`, `r2.py`, `floor.py`, `gn.py`, `hess.py`, `mu.py`,
`probe.py`, `teach.py`). None of them is part of the repo.

Not re-reported: the summed-KL / 1e-5 floor issue itself (results/selfplay.md, "KL check after the stop").

## Summary in plain words

- **One real bug that matters now:** the new std floor freezes any std that touches it. Output 30's std is fixed at
  exactly 0.1 with zero gradient. Other outputs will freeze the same way if they drift down to 0.1, and in the sweep they
  were drifting toward it. Rally run 18 uses this code, and its main training had not started when I checked.
- **Part of why output 30 collapsed:** the std is a plain (not log) parameter, and Adam moves it by a fixed amount per
  step. As the std shrinks, each step becomes a larger fraction of it. The entropy bonus cannot push back under Adam. Why
  the collapse began in rally run 2 is still unknown. I ruled out four candidate causes.
- **The observation normalizer stopped adapting long ago.** Its sample count is 1.45e10, so each 4,000-iteration run
  moves it by about 8 %. Input columns added later (the teacher inputs) were never really normalized. Some columns are
  constant and would be amplified 100x if they ever changed.
- **The actor gradient is clipped on essentially every mini-batch.** That is not a bug under Adam, but `max_grad_norm`
  does not do what its name suggests.
- **Things I checked that look fine:** time-out bootstrapping, the GAE and returns code, value-loss clipping in practice,
  the critic (it also ran at 1e-5 for 15 runs but shows no sign of starving), mini-batch sizes, and the residual tanh on
  the latent dims (not saturated).

---

## Confirmed findings

### C1. The std floor freezes stds that reach it (zero gradient at and below the floor) - severity HIGH for run 18, confidence high

**Where.** `mjlab/picklebot_mj/rl/sched_ppo.py:39-42` sets rsl_rl's forward-pass clamp:
```python
floor = float(env("PICKLEBOT_STD_MIN", "0.1"))
dist.std_range[0] = floor
```
rsl_rl applies it as `std = self.std_param.clamp(self.std_range[0], self.std_range[1])`
(`rsl_rl/modules/distribution.py:187`). `scripts/fresh_init.py:23` (`std.clamp_(min=a.std_min)`) sets output 30's
parameter to exactly the floor.

**What is wrong.** `torch.clamp` passes zero gradient when its input is at or below `min`. Checked on this torch
(2.14.1): at `p = 0.1`, `p.clamp(0.1, 1e6).backward()` gives grad 0.0. At 0.1000001 it gives 1.0, and at 0.0999 it gives
0.0. So:
1. Output 30's std has received exactly zero gradient since the restart. Neither the surrogate nor the entropy bonus can
   move it.
2. Any other output whose parameter Adam pushes to or below 0.1 is frozen there for good. It gets zero gradient, so it
   can never rise again. The floor works as a one-way ratchet, not as a floor.

**Evidence.** The Adam state of `distribution.std_param` (state 0) at the last checkpoint of each run:

| Run | Adam steps | std_param[30] | exp_avg[30] | sqrt(exp_avg_sq[30]) | median sqrt(exp_avg_sq) |
|---|---|---|---|---|---|
| lrsweep-3e-5 model_28197 | 8,000 | 0.100000001 | 0 | 0 | 8.5e-3 |
| lrsweep-1e-4 model_28197 | 8,000 | 0.100000001 | 0 | 0 | 6.5e-3 |
| lrsweep-3e-4 model_28197 | 8,000 | 0.100000001 | 0 | 0 | 4.1e-3 |
| rally-18-sched-smoke model_27837 | 800 | 0.100000001 | 0 | 0 | 7.1e-3 |

The other stds are moving toward the floor. In the 1e-4 arm the smallest of the other 34 fell from 0.151 to 0.1245 in 400
iterations (output 14), and in the 3e-5 arm to 0.118. Run 18 runs for 4,000 iterations at 1e-4, so several more outputs
are likely to reach 0.1 and freeze. The sched log's `std_min` cannot show this, because it is already pinned at 0.1 by
output 30.

**Cheap fix (pick one).** Keep the forward clamp at rsl_rl's 1e-6 and instead project the parameter after each optimizer
step: `with torch.no_grad(): std_param.clamp_(min=floor)`. This could go in `ScheduledPPO.update` via a hook after
`optimizer.step`, or by wrapping `self.optimizer.step`. The other option is to parameterize as `std = floor +
softplus(param)`. Either way the gradient keeps flowing at the boundary.

**Cheap check on run 18.** Load its checkpoints every 500 iterations. Count `std_param <= 0.1` and the entries of
`exp_avg_sq` that are exactly zero for state 0.

### C2. Scalar-std parameterization plus Adam allowed output 30 to collapse fast, and the entropy bonus could not resist - severity MEDIUM (it caused C1's precondition and the KL issue), confidence medium-high

**Where.** `distribution_cfg = {"class_name": "GaussianDistribution", "init_std": 1.0, "std_type": "scalar"}` comes from
mjlab's `unitree_g1_ppo_runner_cfg`, inherited through `_rl_cfg` -> `_latent_drill3_rl_cfg` -> `_s5e_rl_cfg`. The
entropy coefficient is 0.001 (`tasks/__init__.py:530`).

**What is wrong.** Adam's step on each parameter is about `lr` in parameter units, whatever the gradient's size. With
`std_type: scalar` the parameter is σ itself. A run of consistent gradient signs therefore lowers σ by a fixed absolute
amount each step. Per step that is 0.1 % of σ at 0.1 but 3 % at 0.003, so the collapse speeds up as σ falls.
- The entropy term's gradient on σ_i is -c/σ_i. The surrogate's gradient on σ_i also scales as 1/σ_i, and Adam divides
  both by the same running RMS. So the entropy bonus provides no restoring force that grows as σ shrinks. Under Adam only
  the sign of the sum matters, and at c = 0.001 the entropy term is a small, fixed share of it.
- With log-std, an Adam step changes σ by a constant fraction. Going from 0.1 to 0.0035 needs about 3.3 units of log σ.
  At the same maximum step (20 x 1e-5 per iteration) that would take about 16,000 iterations rather than about 800.

**Evidence (rally run 2, `2026-10-21_20-50-34_rally-02-coop`).**

| ckpt | lr | std30 | std14 | sqrt(v)30 / median latent sqrt(v) |
|---|---|---|---|---|
| 3400 | 7.6e-5 | 0.218 | 0.248 | 1.3 |
| 4400 | 5.1e-5 | 0.151 | 0.197 | 1.9 |
| 4800 | 7.6e-5 | 0.100 | 0.157 | 3.0 |
| 5000 | 7.6e-5 | 0.069 | 0.138 | 4.3 |
| 5200 | 1.0e-5 | 0.039 | 0.117 | 7.4 |
| 5400 | 1.5e-5 | 0.0089 | 0.109 | 23 |
| 5600 | 1.0e-5 | 0.0035 | 0.112 | 101 |
| 6400 | 1.0e-5 | 0.0036 | 0.133 | 137 |

Between 4,800 and 5,600, σ_30 fell about 1.2e-4 per iteration. That is most of Adam's maximum of 20 steps x lr once the
rate was near 1e-5, which is 2e-4 per iteration. The saved rates are snapshots that swing between 1e-5 and 7.6e-5. The
fall was linear in absolute units, which is what a scalar parameter under Adam does. Its gradient RMS rose about 100x as σ fell,
the 1/σ scaling, while Adam's step stayed the same. All latent stds shrank in run 2 (output 14 went 0.248 -> 0.109 and
later recovered). Output 30 started lowest and fell fastest. Note: rally runs 1-2 also ran the default 50-iteration critic
warm-up, because their scripts did not set PICKLEBOT_CRITIC_WARMUP; I see no link to the collapse.

**Why it started is still unknown.** What I ruled out (all on CPU, partly with synthetic states):
- *Decoder sensitivity.* I measured 2·σ_prior,i·|∂dec/∂z_i| on 513 synthetic proprio states around the latent
  controller's normalizer mean. Dim 30 is 1.66x the median and ranks 4th of 32. Dims 14, 25 and 23 are more sensitive and
  did not collapse. Not enough on its own.
- *tanh saturation.* Output 30's mean is small: |μ| about 0.27 on synthetic inputs, bias 0.004, and the KL check
  reports tanh 0.07-0.35. Not saturated.
- *The critic's last-action input* (an action→advantage path through V(s_{t+1})). The critic's raw-input gain on
  last-action dim 30 is the largest of the 32 latent dims: 2.26 against a median of about 1.3, at run 14's end. But the
  critic's curvature d²V/da_30² is about 0.005 per unit², orders of magnitude too small to drive σ toward 0.003.
- *Gradient clipping.* The std parameter carries 0.1-0.3 % of the actor's squared gradient norm, so it does not set
  the clip factor.

There is a balance point near 0.002-0.004. In run 14, `lam_r_init` halved σ_30 to 0.0017, and it climbed back to
0.0022. Whatever sets that point is very sensitive to output 30's noise. A cheap test on one rollout: per output, log the
correlation E[Â·(ε_i² − 1)] (the score-function push on σ_i) and the PPO clip fraction. Also check which reward terms
correlate with ε_30. Output 30 is pinned at 0.1 by C1, so it cannot collapse again in run 18.

**Fix for the next restart (not mid-run).** Use `std_type: "log"` and convert with `log_std_param = log(std_param)`.
mjlab's loader already handles `log_std` keys. Also log the per-output min and max std. The logged "Mean action std"
(0.23) hid output 30 at 0.002 for 15 runs.

### C3. The observation normalizer has effectively stopped adapting; added columns are never normalized - severity MEDIUM, confidence high

**Where.** `rsl_rl/modules/normalization.py:58-66`. The update rate is `count_x / count` with `until=None`. The count is
restored on every resume. New columns are added by `scripts/expand_checkpoint.py:22`, which sets mean 0 and var 1 but
keeps the shared count.

**What is wrong.**
- At run 14's end the actor normalizer count is 1.449e10 and the critic's 1.414e10. With 12,288 envs each step moves the
  statistics by 8.5e-7 of the gap, about 2e-5 per iteration and about 8 % over a 4,000-iteration run. The mean and std
  are an average over the whole lineage of tasks, back through Stage 5C. Shifts from new tasks, such as pairs, partner
  balls or the lam_r change, are barely reflected.
- Added columns stay at their placeholder statistics. The teacher inputs (rally runs 16-17, columns 124-128) started at
  mean 0 / std 1. After 2,100 iterations of run 16 their std was 0.98. In run 17, whose inputs were multiplied by 30, the
  std had reached only 1.9-3.5. So those inputs entered at raw scale. D-157's reasoning ("a gain-times larger step") was
  right only because the normalizer is frozen. A fresh normalizer would have cancelled the gain.
- Constant columns carry a trap: their std is exactly 0, and with eps = 0.01 any change is amplified 100x. These are
  actor columns 102-104 (the twist command, always 0) and actor 116 / critic 131 (target x = 0.6711, always target A).
  If an evaluation or task ever uses another target (`--target B`, random targets) or a non-zero twist, those inputs jump
  by (Δx)/0.01. Evaluations use `--target A` today, so this is latent, not active.

**Evidence.** Normalizer statistics from `model_27798.pt` (run 14) and the rally-16 / rally-17 checkpoints (scratch
`teach.py`): new-column std 1.0000 → 0.98 (run 16, 2,100 iterations) and 1.0 → 1.9-3.5 (run 17).

**Cheap fix.** When expanding or restarting, reset the count to something like 1e7, or give each column its own count,
so the statistics follow the current task within a few hundred iterations. For constant columns, either drop them or
raise eps. Note: re-normalizing changes the network's effective input scaling, so do it only together with the learning
rate restart and a short critic warm-up.

### C4. The actor gradient is clipped on (essentially) every mini-batch - severity LOW, confidence high

**Where.** `rsl_rl/algorithms/ppo.py:302` (`clip_grad_norm_(actor.parameters(), 1.0)`) and `max_grad_norm: 1.0`.

**Evidence.** The RMS of the post-clip actor gradient norm, reconstructed from Adam's bias-corrected `exp_avg_sq` summed
over the actor's parameters, is 1.000 in every checkpoint checked: rally-02 at 3400, 5000 and 6400, run 14's end,
lrsweep-1e-4's end and run 18's smoke. For the critic it is 0.44-0.97, so the critic is clipped only sometimes.

**Meaning.** The actor's raw gradient norm is above 1 essentially always, so `max_grad_norm` is a constant normalization
rather than a guard against outliers. Under Adam this is mostly harmless. It does mean each mini-batch counts equally
whatever its signal, and that the learning rate alone sets the step size. **Check:** log the value `clip_grad_norm_`
returns, which is the pre-clip norm.

---

## Suspicions (plausible, not confirmed)

### S1. The wrist-residual outputs (32-34) are mostly inert and their noise grows unchecked - severity LOW-MEDIUM, confidence medium-low

The wrist stds rose steadily across the lineage: 0.10 at s5c-22 → 0.34 at s5d-01 → 0.55 at rally-01 → 0.75 at rally-10 →
0.77 at run 14's end, with no reversal. Their gradient RMS is about 4x smaller than the latent outputs' (sqrt(v) 5.5e-5
against 2.2e-4). The normalizer history for last-action columns 99-101 has mean +4.4 / -0.15 / -4.8 and std 8.0 / 1.5 /
13.3, so in the past these outputs were often far into tanh saturation. On synthetic inputs today, 25-33 % of samples have
|μ| > 2 on outputs 32 and 34.

Rising std together with a weak gradient means only the entropy bonus is acting on these outputs. In training rollouts,
`wrist_r · tanh(a)` (`latent_reach.py:434`) adds up to about ±0.06 rad of random paddle-face motion on unsaturated
samples. Evaluation runs the mean policy, so training and evaluation differ there. **Check:** log the wrist outputs'
|μ| and the fraction beyond |μ| > 2 from a rollout. If they are inert, cap their std with a max on `std_range` or
remove them.

### S2. Four latent residual dims barely move the robot - severity LOW, confidence low-medium (synthetic states)

The residual enters as `lam_r · σ_prior · tanh(a)` (`latent_reach.py:429`). On synthetic states the latent prior's σ is
0.056-0.089 for dims 2, 4, 7 and 13, against a median of about 0.87 for the rest. Their joint-space effect is 30-40x below
the median: 0.007-0.014 against 0.31. Consistent with this, their policy stds are the highest of the latent stds
(0.195-0.200 against a median of 0.181), the entropy-only drift seen in S1. This wastes 4 of the 32 outputs but does no
harm. Confirm on real rollout states before acting.

### S3. The KL guard cannot stop the first mini-batch step - severity LOW, confidence high (as a design fact)

`sched_ppo.py` checks each mini-batch's KL before that mini-batch's step. The first mini-batch always sees a KL of 0 and
always steps. In the 3e-4 arm, from update 51 onward, every update tripped after that one step, with a KL of 0.45-0.67
(results/lrsweep-3e-4-train.jsonl). So one step could exceed the guard by 10x. At 1e-4 (run 18) the KL max was 0.020 with
no trips, so this is not active now. If a guard that truly bounds the KL is wanted, check the KL after the update and
revert to a parameter snapshot.

### S4. Resume and config hazards - severity LOW, confidence high

- **What a resume restores.** It restores weights, the normalizer with its count (see C3), Adam's moments, the learning
  rate, the iteration counter (`iter`) and mjlab's `common_step_counter`. `PPO.load` sets `self.learning_rate` from the
  optimizer's param group (`ppo.py:390-391`), so the `learning_rate: 0.001` in every `params/agent.yaml` was silently
  replaced by the saved rate. That is how the 1e-5 floor carried over from run to run. The kl_probe "b" run hit the same
  thing.
- **What a resume does not restore.** It does not restore ScheduledPPO's `updates` counter, CriticWarmupRunner's
  `_warm_updates` or RegPPO's counter. If run 18 is ever resumed from one of its own checkpoints, the 50-update warm-up
  repeats and the cooldown (u > 3,200 of `PICKLEBOT_LR_TOTAL`) shifts. `init_at_random_ep_len=True` re-randomizes
  episode lengths on every launch, which is fine.
- **What the recorded config misses.** The run settings that live in environment variables (PICKLEBOT_LR_*,
  PICKLEBOT_STD_MIN, PICKLEBOT_KL_GUARD, PICKLEBOT_CRITIC_WARMUP) appear in neither `params/agent.yaml` nor
  `<run>.launch.json`. Run 18's agent.yaml still says `schedule: adaptive`. The task-shaping variables (PICKLEBOT_LAM_R,
  PICKLEBOT_RES_BASE, PICKLEBOT_LEG_R, PICKLEBOT_TEACHER(_GAIN), `tasks/__init__.py:999-1013`) are read at import and
  reshape every residual task. lam_r does end up in env.yaml, and I found no wrong use in rally runs 14-18's scripts. Still,
  a forgotten `PICKLEBOT_LAM_R=2` on an evaluation of a lam_r-2 checkpoint would silently evaluate it at lam_r 1.
  **Cheap fix:** have train_run.sh dump `env | grep PICKLEBOT_` into launch.json. Store lam_r and the teacher gain in the
  checkpoint's `infos` and assert them at load.
- **Two spellings of the warm-up variable.** RegPPO reads `PICKLEBOT_CRITIC_WARMUP_ITERS`
  (`reg_ppo.py:82`) and the runner reads `PICKLEBOT_CRITIC_WARMUP` (`tasks/__init__.py:1359`). RegPPO is not used now.

### S5. The critic shares the actor's learning rate (an extension of the KL issue) - severity LOW, confidence medium

There is a single Adam param group over actor and critic (`ppo.py:92-94`), so the critic also learned at 1e-5 through
runs 2-17. I looked for harm and found none clear. The value loss is flat at 0.26-0.28 at 1e-5 (run 14), 3e-5 and 1e-4.
After each resume it drops from about 0.70 to 0.27 within 10 iterations. So the critic does not look starved, even with
`PICKLEBOT_CRITIC_WARMUP=0` since rally run 3. Value-loss clipping (`clip_param` 0.2 in raw return units, value about
6-12) allows little movement per update, but the critic still keeps up.

---

## Checked and found OK

- **Time-outs and terminations.** `time_out` is the only `time_out=True` term. `fell_over` and `blew_up` are terminal.
  mjlab sets `extras["time_outs"] = truncated` (`is_finite_horizon: false`). rsl_rl bootstraps with γ·V(s_t) of the
  pre-step observation (`ppo.py:151-155`), the standard rsl_rl approximation. Pair mode does not reset the partner env;
  it only ends the rally (`pairs.py:55-71`).
- **GAE and returns** (`ppo.py:163-188`) are standard. γ is 0.995 and λ 0.95, so the GAE horizon is about 18 steps. The
  24-step rollouts bootstrap from the last value. Advantages are normalized over the whole batch.
- **Reward scale.** mjlab multiplies by dt (0.02), so a one-shot weight X/step_dt pays X. At an event that is: legal 5,
  partner 3, rally ≤ 2.5, keep-alive ≤ 2, contact 1, net clearance ≤ 1, pace −0.5. Dense per-step reward averages about
  0.06 and V is about 6-12. No term dwarfs the others.
- **Batching.** 12,288 x 24 = 294,912 samples per iteration, in 4 mini-batches of 73,728, over 5 epochs. That is 20
  steps per iteration, which is reasonable. rsl_rl reuses one permutation for all 5 epochs, a minor standard behaviour.
- **Residual tanh on the latent dims.** It is not saturated (|μ| ≈ 0.15-0.31 on synthetic inputs, none beyond 2). PPO
  does not backpropagate through the env-side tanh, so saturation could only reduce the env's sensitivity; it cannot kill
  the gradient.
- **ScheduledPPO's rate plumbing.** The rate is set before each update and overridden per mini-batch through the patched
  `get_kl_divergence`. The adaptive rule is handed `desired_kl`, so it does nothing. A `lr 0.0` in saved optimizer
  groups after a guard trip is reset at the next update.
- **fresh_init's empty Adam state** is safe with the 50-update warm-up.

## Suggested order of action

1. Before or early in run 18: fix C1 (projection instead of the forward clamp), or at least monitor which stds sit at
   0.1 with zero `exp_avg_sq`.
2. At the next restart: switch to log-std (C2), reset the normalizer counts or re-estimate the statistics (C3), and log
   per-output min and max std plus the pre-clip gradient norm (C4).
3. Diagnose output 30's original collapse with the per-output E[Â·(ε²−1)] and clip-fraction log from one rollout (C2).
