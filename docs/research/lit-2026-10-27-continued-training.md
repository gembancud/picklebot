# Literature review: LR schedules, plasticity, and warm-start fine-tuning for the G1 residual PPO plateau

Date: 2026-10-27. Every source below was checked for title, authors, year and link. I mark my own inferences as **[inference]**. I mark anything I could not confirm as **[unverified]**.

---

## 0. Two facts from the code that matter most

- **rsl_rl adaptive rule** (`rsl_rl/algorithms/ppo.py`, main branch). It uses `kl_mean = mean(kl)`. If `kl_mean > 2*desired_kl`, then `lr = max(1e-5, lr/1.5)`. If `kl_mean < desired_kl/2`, then `lr = min(1e-2, lr*1.5)`. The defaults are `desired_kl=0.01`, `entropy_coef=0.01` and `max_grad_norm=1.0`. The rule comes from Rudin et al., *Learning to Walk in Minutes Using Massively Parallel Deep RL*, CoRL 2021 ([arXiv 2109.11978](https://arxiv.org/abs/2109.11978)), Alg. 1. TorchRL's `KLAdaptiveLR` ([docs](https://docs.pytorch.org/rl/main/reference/generated/torchrl.objectives.KLAdaptiveLR.html)) documents the same rule.
- **KL is summed over action dimensions** (`rsl_rl/modules/distribution.py`: `kl_divergence(Normal(old), Normal(new)).sum(dim=-1)`). The std is clamped to `std_range`, which defaults to `(1e-6, 1e6)`. `std_type` can be `"scalar"` or `"log"`.

**[inference]** Per dimension, the mean-shift part of the Gaussian KL is (Δμ)²/(2σ²). With σ = 0.002, a mean shift of only 0.002 adds 0.5 to the KL. That is 50 times the 0.01 target, from one dimension. The other 34 dimensions (σ ≈ 0.18) would need a shift about 90 times larger to add the same amount. So the collapsed dimension alone can hold the summed KL above 2 × 0.01 and pin the LR at the 1e-5 floor. The std also sits at 0.002 under a *scalar* parameterization, so a single Adam step of about 1e-5 changes it by roughly 0.5 %. Your suspicion fits the arithmetic. You can test it directly by logging KL per dimension (§6).

---

## 1. LR schedules for continuing or open-ended training

**Newest consensus (LLM pretraining, 2024–2025): warmup-stable-decay (WSD) and "constant + cooldown" replace cosine when you don't know the training length.**
- MiniCPM (Hu et al., 2024, [arXiv 2404.06395](https://arxiv.org/abs/2404.06395)) introduced WSD: warmup, then a long constant phase, then a short decay. Loss drops sharply during the decay. Any checkpoint from the constant phase can be continued.
- Hägele et al., *Scaling Laws and Compute-Optimal Training Beyond Fixed Training Durations*, NeurIPS 2024 ([arXiv 2405.18392](https://arxiv.org/abs/2405.18392)):
  - Constant LR plus cooldown matches cosine. Gains level off at a cooldown of about 20 % of steps.
  - A **1−sqrt** cooldown shape beats linear.
  - Weight averaging (SWA) helps at no extra cost.
  - Schedule-free optimizers work, but not optimally.
- Wen et al., *Understanding WSD Learning Rates: A River Valley Loss Landscape Perspective*, ICLR 2025 ([arXiv 2410.05192](https://arxiv.org/abs/2410.05192)). A high constant LR makes progress "along the river" while bouncing between the valley walls. The decay removes the bouncing, and that is when the progress shows. **[inference]** If so, sitting at a tiny LR for 17 runs is like being stuck in a permanent cooldown: no noise left, but also almost no progress along the valley.

**Continual pre-training: re-warm, then re-decay.**
- Gupta et al., 2023 ([arXiv 2308.04014](https://arxiv.org/abs/2308.04014)): re-warming raises loss at first but gives better adaptation over the longer run. The workshop version of the paper reports different conclusions from the arXiv version, so treat it as mixed evidence.
- Ibrahim et al., *Simple and Scalable Strategies to Continually Pre-train LLMs*, TMLR 2024 ([arXiv 2403.08763](https://arxiv.org/abs/2403.08763)): LR re-warming + re-decaying + **replay** of old data matches retraining from scratch. Re-warming raises both adaptation *and* forgetting, which is why replay is needed. The paper also proposes "infinite" schedules to avoid repeated re-warming.

**Schedule-free.** Defazio et al., *The Road Less Scheduled*, NeurIPS 2024 ([arXiv 2405.15682](https://arxiv.org/abs/2405.15682)). No schedule is needed, and it matches or beats scheduled training. You still have to sweep LR and weight decay, and the best values differ from scheduled ones. I found no robotics-PPO adoption. It is not the conservative choice here.

**Cyclic schedules** (SGDR-style, older) are mostly replaced by WSD/WSD-S in current practice. Wen et al. report that WSD-S beats cyclic-cosine when you want many checkpoints.

---

## 2. How robot-learning PPO stacks set the LR

| Stack | LR setting (verified) |
|---|---|
| rsl_rl / legged_gym (ETH) | adaptive KL, desired_kl 0.01, clamp [1e-5, 1e-2] (Rudin 2021; [RSL-RL paper, arXiv 2509.10771](https://arxiv.org/abs/2509.10771)) |
| Isaac Lab ([arXiv 2511.04831](https://arxiv.org/abs/2511.04831)) | rsl_rl wrapper; `schedule`, `desired_kl`; std type `scalar` by default, `log` optional ([cfg docs](https://isaac-sim.github.io/IsaacLab/v2.2.0/_modules/isaaclab_rl/rsl_rl/rl_cfg.html)) |
| mjlab ([arXiv 2601.22074](https://arxiv.org/abs/2601.22074)), G1 tracking cfg | lr 1e-3, adaptive, desired_kl 0.01, entropy 0.005, 5 epochs × 4 minibatches, init_std 1.0, **scalar std**, actor 512-256-128 ([rl_cfg.py](https://github.com/mujocolab/mjlab)) |
| BeyondMimic (Liao et al. 2025, [arXiv 2508.08241](https://arxiv.org/abs/2508.08241)) | G1 tracking built on rsl_rl/Isaac Lab. I did not confirm its exact LR settings **[unverified]**, but mjlab's tracking task follows it. |
| MuJoCo Playground / Brax PPO (G1 joystick) | **fixed** lr 3e-4, no schedule, entropy 0.005, 8192 envs ([locomotion_params.py](https://github.com/google-deepmind/mujoco_playground)) |
| skrl KLAdaptiveLR | threshold 0.008, min_lr 1e-6 ([docs](https://skrl.readthedocs.io/en/latest/api/resources/schedulers/kl_adaptive.html)) |

Older general guidance: Andrychowicz et al., *What Matters in On-Policy RL*, ICLR 2021 ([arXiv 2006.05990](https://arxiv.org/abs/2006.05990)).
- Use Adam with LR 3e-4 as a safe default. Linear decay "may slightly improve performance but is of secondary importance".
- Always normalize observations.
- Make the last policy layer 100× smaller at init.
- Use softplus (or exp with clipping) for the std.

**Known failure modes of adaptive KL.** I found no paper or GitHub issue that documents "collapsed std drives LR to floor" **[unverified as a published failure mode]**. It follows directly from the summed KL (§0). The fixes below are supported by the code and by general practice:
1. **Std floor / log parameterization.** Set `std_type="log"` and raise `std_range[0]` (both available in current rsl_rl). The literature gives no numeric floor. Something like 0.02–0.05 of the action scale is my judgment **[inference]**.
2. **Make the KL that the controller sees robust.** Options: cap or exclude the collapsed dimension, normalize by the number of dimensions, or raise `desired_kl`. None of these is standard in rsl_rl, so each would be a custom change.
3. **Replace adaptive with a fixed schedule plus a KL guard.** That is the Brax/Playground approach.
4. **Entropy bonus.** It does not reliably stop collapse in one dimension, because the entropy of a summed Gaussian is linear in log σ, while the KL is quadratic in 1/σ **[inference]**.

LLM-RL has a parallel problem. Cui et al. 2025, *The Entropy Mechanism of RL for Reasoning LMs* ([arXiv 2505.22617](https://arxiv.org/abs/2505.22617)): performance saturates once entropy collapses. Their fixes (Clip-Cov/KL-Cov) throttle the updates that drive the collapse. That supports treating std collapse as a real ceiling, not a cosmetic issue.

Newer PPO-at-scale result: Beukman et al., *Preventing Learning Stagnation in PPO by Scaling to 1 Million Parallel Environments*, RLC 2026 ([arXiv 2603.06009](https://arxiv.org/abs/2603.06009)). PPO plateaus can come from the outer-loop step being too large relative to gradient noise ("thrashing"). The remedies are a smaller step or more samples per update. This is the **opposite** risk to yours. It is worth one control run with a larger batch (§6).

---

## 3. Plasticity loss: causes and remedies, filtered for PPO

**Causes** (consensus 2023–2025):
- Dormant/dead units: Sokar et al., ICML 2023, ReDo ([PMLR v202](https://proceedings.mlr.press/v202/sokar23a.html)).
- Weight-norm growth and loss of unit diversity: Dohare et al., *Loss of plasticity in deep continual learning*, Nature 632, 2024 ([doi 10.1038/s41586-024-07711-7](https://doi.org/10.1038/s41586-024-07711-7)).
- Feature-rank collapse in PPO: Moalla et al., *No Representation, No Trust*, NeurIPS 2024 ([arXiv 2405.00662](https://arxiv.org/abs/2405.00662)). They show PPO-Clip's trust region gets weaker as the representation degrades, and they propose an auxiliary loss (PFO).
- Several separable causes: Lyle et al., *Disentangling the Causes of Plasticity Loss*, CoLLAs 2024 ([arXiv 2402.18762](https://arxiv.org/abs/2402.18762)). Their best combination is LayerNorm + weight decay.
- Stale Adam moments after the target changes: Asadi et al., NeurIPS 2023 ([arXiv 2306.17833](https://arxiv.org/abs/2306.17833)), for value-based RL. Ellis et al., *Adam on Local Time* (Adam-Rel), NeurIPS 2024 ([arXiv 2412.17113](https://arxiv.org/abs/2412.17113)), tested on PPO and off-policy methods: reset Adam's timestep at each new target.

**The on-policy evidence that matters most.** Juliani & Ash, *A Study of Plasticity Loss in On-Policy Deep RL*, NeurIPS 2024 ([arXiv 2405.19153](https://arxiv.org/abs/2405.19153)), studied PPO:
- **Worked:** intermittent shrink+perturb (β=0.5), "soft" shrink+perturb applied every step (β=1e-6 toward the init weights), regenerative L2-to-init, and LayerNorm (best when combined with soft S&P or L2-init). ReDo helped, but least.
- **Failed or underperformed doing nothing:** final-layer reset, plasticity injection, and CReLU in some shifts.
- Weight magnitude was the strongest correlate.

**Older methods.**
- Primacy-bias resets: Nikishin et al., ICML 2022 ([arXiv 2205.07802](https://arxiv.org/abs/2205.07802)). Designed for replay-buffer agents.
- Plasticity injection: Nikishin et al., NeurIPS 2023 ([arXiv 2305.15555](https://arxiv.org/abs/2305.15555)). Useful as a diagnostic.
- Shrink-and-perturb warm start: Ash & Adams, NeurIPS 2020 ([arXiv 1910.08475](https://arxiv.org/abs/1910.08475)). It shows warm-started nets can end up worse than nets trained from scratch.
- Continual backprop (Dohare 2024).

**Architectures (newest, mostly off-policy).**
- SimBa: Lee et al., ICLR 2025 ([arXiv 2410.09754](https://arxiv.org/abs/2410.09754)). Obs-norm + residual blocks + LayerNorm, with gains also reported for PPO.
- SimbaV2: ICML 2025 ([arXiv 2502.15280](https://arxiv.org/abs/2502.15280)). Hyperspherical normalization to control weight and feature norms.
- BRO: Nauman et al., NeurIPS 2024 ([arXiv 2405.16158](https://arxiv.org/abs/2405.16158)).

**What applies to us [inference].**
- Massively parallel PPO with 12k envs is mildly nonstationary within a run. The main nonstationarity is *between* your 17 warm starts (new inputs, new opponents/tasks).
- The cheapest remedies that fit PPO are a fresh Adam, L2-to-init or soft S&P, and monitoring dormant units and weight norms.
- LayerNorm/SimBa-style blocks are a larger change. They break exact warm-start and belong in a separate experiment.
- Resets matter less in on-policy RL because there is no replay buffer to re-learn from.

---

## 4. Fine-tuning a pre-trained policy with RL

- **Critic warm-up, then an actor LR ramp.** PIRLNav (Ramrakhya et al., CVPR 2023, [arXiv 2301.07302](https://arxiv.org/abs/2301.07302)) is a PPO-family case (DD-PPO):
  - Phase 1 trains only the critic (actor frozen) until its loss plateaus, which took about 8M steps.
  - Over the next 4M steps, the actor LR ramps 0 → 1.5e-5 while the critic LR decays 2.5e-4 → 1.5e-5.
  - Ablations without this recipe lost 2.5–5 pp of success.
- **Value calibration before policy updates** (off-policy analogue): WSRL, Zhou et al., ICLR 2025 ([arXiv 2412.07762](https://arxiv.org/abs/2412.07762)). A short warm-up rollout phase recalibrates the value function, which prevents an early collapse.
- **Forgetting is the main fine-tuning failure.** Wołczyk et al., ICML 2024 ([arXiv 2402.02868](https://arxiv.org/abs/2402.02868)): a pre-trained policy degrades on states that fine-tuning does not visit early. Knowledge-retention methods (BC/KL to the old policy, replay of old task mix) fix this. For you, that means keeping the old opponent/feeder/rally mixture in the curriculum.
- **KL-to-reference with periodic reference reset** (LLM-RL, transfers fairly directly): ProRL, Liu et al., NeurIPS 2025 ([arXiv 2505.24864](https://arxiv.org/abs/2505.24864)). Long RL runs stay stable with a KL penalty to a reference that is periodically reset to the current policy.
- **Residual RL over a frozen base**, which is your setup: Ankile et al., ResiP 2024 ([arXiv 2407.16677](https://arxiv.org/abs/2407.16677)). I could not confirm the exact algorithm details in that paper **[unverified]**.
- **Gradual unfreezing.** I found no robotics-PPO paper that specifically tests unfreezing a frozen decoder or base. PIRLNav keeps its encoders frozen throughout. **[gap]**

---

## 5. Warm-starting after adding input columns

- Net2Net (Chen, Goodfellow, Shlens, ICLR 2016, [arXiv 1511.05641](https://arxiv.org/abs/1511.05641)) and OpenAI Five "surgery" (Raiman, Zhang, Dennison 2019, [arXiv 1912.06719](https://arxiv.org/abs/1912.06719); Dota paper [arXiv 1912.06680](https://arxiv.org/abs/1912.06680)) are the precedents for function-preserving growth. Five went through about 20 feature and architecture changes over 10 months. I could not open the PDFs to confirm exactly how new input weights were initialized **[unverified]**.
- **[inference] Why your new columns didn't grow.** Zero-initialized *input* weights still get a gradient (δ·xᵀ), so zero-init by itself is not the problem. Three things scale that gradient down together:
  1. LR at 1e-5.
  2. The normalizer is frozen (count ≈ 1.5e10). If the new columns' running mean/var were never estimated, they reach the network at raw scale. If raw values are small, their gradient is small.
  3. The PPO advantage signal that these inputs explain is weak.
- **Fixes:**
  - (a) Re-estimate the normalizer stats, at least for the new columns, from fresh rollouts. Or reset the count to a small value so the stats adapt during warm-up.
  - (b) Initialize the new columns with small random weights (e.g. 0.1× the default init) instead of exactly zero, so the function stays nearly the same.
  - (c) Optionally give a separate, higher-LR param group to the new first-layer columns for the first few hundred iterations.
  - (d) Log the gradient norm and weight norm of those columns.

---

## 6. Recommended recipe for a properly restarted run 14

The numbers are anchored to the cited work where possible. Everything else is my judgment. Assumed budget: about 480 iterations per hour, so a 6–7 h run is about 3000 iterations. Change the optimizer side only, and keep the reward and curriculum identical to run 14 (one variable at a time).

1. **Load run-14 actor + critic weights. Do not load the Adam state** (fresh moments and timestep; Asadi 2023, Ellis 2024).
2. **Fix the std.**
   - Switch to `std_type="log"`.
   - Set `std_range` min to about 0.02–0.05 in action units **[judgment]**.
   - Re-set the collapsed dimension to that floor, and leave the others as they are.
   - Expect a small temporary drop from the extra noise in that one dimension.
3. **Normalizer.** Refresh the stats from about 50 iterations of rollouts with the frozen policy. This matters especially for the new columns. Then either keep updating the stats (with a capped count) or freeze them.
4. **Critic warm-up.** Run about 50–100 iterations with actor LR = 0 and critic LR 3e-4 (PIRLNav pattern). Stop when the value loss and explained variance plateau.
5. **Actor warm-up** over about 100 iterations: 0 → peak.
   - Peak 1e-4 (conservative) to 3e-4 (Andrychowicz default; Brax G1 uses 3e-4). mjlab starts adaptive at 1e-3.
   - Use a fixed schedule instead of adaptive. Keep a KL **guard**: skip the remaining epochs if the per-dimension-capped KL is above about 0.05.
6. **Stable phase** at the peak for about 75–80 % of iterations. Save checkpoints often. These checkpoints can seed future cooldowns, WSD-style.
7. **Cooldown.** Use 1−sqrt decay to about 1e-5 over the last ~20 % (Hägele 2024). Select only the fixed-endpoint checkpoint, as per your plan rules.
8. **Forgetting control.** Keep the full old task mixture. Optionally add a small KL-to-run-14 penalty during warm-up and decay it to 0 (ProRL/Wołczyk logic). This adds a second variable, so leave it off unless forgetting appears.
9. **Plasticity guard (optional, second experiment).** Use L2-to-init or soft shrink+perturb (β≈1e-6 per step; Juliani & Ash).

**Evidence that separates "optimizer-limited" from "policy's real limit":**
- **A. Per-dimension KL log.** If one dimension supplies most of the KL in old runs, the adaptive controller was the bottleneck. This is diagnostic, not proof that a higher LR will help.
- **B. Short LR sweep from the same checkpoint** (fresh Adam, std fixed, constant LR {3e-5, 1e-4, 3e-4}, about 400 iterations each, on dev seeds). If any arm beats run 14's P(5+) beyond its interval → optimizer-limited. If all arms stay flat while value loss falls and the KL is healthy → closer to a real capacity or task limit.
- **C. Larger batch at the same LR** (Beukman 2026). If this improves results, the plateau was noise-limited, not LR-limited.
- **D. Plasticity probes.** Track dormant-unit fraction (ReDo), weight-norm growth and feature rank (Moalla). Optionally train a fresh residual from zero init with the new recipe. If it catches up to and passes run 14, the warm-start lineage had lost plasticity (Ash & Adams).
- **E. New-column use.** Track gradient and weight norms of the new input columns, and run an ablation that zeros those inputs at eval. No change means they are still unused.

Report legal returns and target hits per variation, with intervals, as the project rules require. A single averaged number won't separate these hypotheses.

---

**Newest vs older:**
- *Newest (2024–2026):* WSD/cooldown; on-policy plasticity studies (Juliani & Ash; Moalla); Adam-Rel; SimBa/SimbaV2; PPO stagnation at scale (Beukman); entropy-collapse work in LLM-RL.
- *Older consensus:* adaptive-KL LR (2021) is still the robotics default; Andrychowicz 2020/21 defaults; Net2Net (2016); primacy-bias resets (2022).
