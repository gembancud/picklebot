# Stage 5B: hierarchical motion-prior control, a survey and recommendation (2026-10-09)

**Question.** The AMP-style reward failed: the discriminator saturated and the posture rewards conflicted (`stage5b-style.md`). The user chose the hierarchy route instead: a low-level human-motion controller that a task-level policy steers. Which variant should we build on mjlab + rsl_rl 5.x, on top of the existing tracking teacher (`tracking-06-wide/model_21300`, 90.5 % per-stroke success, r-MPKPE 7.8 cm; see `stage5b-tracking.md`)?

**Method.** Web research only, on 2026-10-09. Nothing was downloaded, installed or cloned. Facts come from the arXiv abstract or HTML pages, project pages, GitHub READMEs and the GitHub license API.
- **[unverified]** marks anything I could not confirm from a primary source.
- Licences are as GitHub reports them. "No licence detected" means default copyright: we may read the code but not copy it.

---

## 1. Method options

### 1.1 PULSE: Luo et al., "Universal Humanoid Motion Representations for Physics-Based Control", ICLR 2024 spotlight
Sources: arXiv 2310.04582 (v1 2023-10-06, v2 2024-04-12), https://zhengyiluo.github.io/PULSE/, https://github.com/ZhengyiLuo/PULSE

**Structure: a conditional VAE in action space, distilled from an imitator.**
- **Encoder** E(z | s_p, s_g). It sees proprioception plus the imitation goal, which is the difference to the reference frame, and outputs μ_e and σ_e.
- **Prior** R(z | s_p). It sees **proprioception only** and outputs μ_p and σ_p.
- **Decoder** D(a | s_p, z). It outputs PD targets.
- **Latent:** z ∈ R^32, about half the humanoid's 69 DoF.

**Loss:** L = ‖a_teacher − a‖² + α‖μ_e,t − μ_e,t−1‖² + β·KL(E ‖ R).
- α = 0.005, a temporal-smoothness term on the encoder mean.
- β is annealed from 0.01 to 0.001 between 2.5e9 and 5e9 samples.

**Distillation:** online and DAgger-style.
- The student (encoder → decoder) is rolled out on the imitation task, and the PHC+ teacher labels every visited state with its action.
- About 1e9 samples (the PHC+ teacher took about 1e10), batch size 3072.
- Hard-negative mining on difficult sequences.
- Hardware and wall-clock time are not stated.

**Downstream use:** hierarchical RL with the decoder frozen.
- The task policy outputs a **residual to the prior mean**: a = D(s_p, π_task(s_p, s_g) + μ_p).
- Exploration uses a fixed σ of 0.22, not σ_p. PPO is the algorithm.
- Random rollouts of the prior, with noise injected, give diverse and stable motion.
- On VR-controller tracking, PULSE reached 93.4 % against 37.6 % for ASE at 30 Hz.

**Code and licence:**
- Isaac Gym with Hydra configs (`env_im_vae`, `env_pulse_*`). The repo contains the downstream tasks: speed, reach, strike, terrain and VR tracking.
- **GitHub detects no licence.** The README says to follow the licences of the upstream repos: IsaacGymEnvs, PHC and SMPL-X.
- The PHC repo, which holds the imitator, is BSD-3-Clause-Clear (CMU and NVIDIA). The license API returns "other", and the text is BSD-3-Clause-Clear.

### 1.2 MaskedMimic: Tessler et al., ACM TOG / SIGGRAPH Asia 2024
Sources: arXiv 2409.14393 (2024-09-22), ProtoMotions (§3).

**Two stages:**
1. A **fully constrained tracker** π_FC is trained with RL on motion tracking. It sees the next K reference poses (K is not stated in the main text).
2. It is **distilled with behaviour cloning plus DAgger** into a **partially constrained** controller π_PC: the student acts and the teacher relabels its trajectories with actions.

**π_PC architecture: a conditional VAE.**
- **Prior:** a transformer over the masked goals.
- **Encoder:** fully connected, sees the full target poses, and is used in training only.
- **Decoder:** fully connected, produces the actions.
- The encoder is a **residual to the prior**: μ = μ_ρ(s, g_partial) + μ_E(s, g_full).
- **KL weight** rises linearly from 1e-4 to 1e-2.
- **Latent noise ε is fixed per episode**, which keeps behaviour temporally coherent.
- The latent dimension and the transformer size are in the supplement **[unverified]**.

**Goals, with masks held over several steps for temporal consistency:**
- the positions and/or rotations of any subset of joints at arbitrary future times;
- text (XCLIP);
- object bounding boxes;
- terrain heightmaps.

**Downstream tasks** are solved by **goal engineering** with hand-made finite-state machines, not by a trained high-level RL policy. For example, *reach* is "right-hand target position plus remaining time", and *steering* is "pelvis position and heading plus time".
- The paper shows **no** RL task policy on top of MaskedMimic.
- So for "paddle position at time t plus root target", a task policy that emits sparse goals is plausible but unproven by the paper. It could also emit latent residuals as in PULSE **[unverified that anyone published this]**.

**Compute:** Isaac Gym, 16,384 envs on 4×A100, about 2 weeks in total (π_FC about 30e9 steps, π_PC about 10e9). 30 Hz control, 120 Hz simulation. That covers the whole of AMASS; our data set is about 1/20 of that.

### 1.3 ASE and CALM: why the tracker-distillation methods replaced them
**ASE** (Peng et al., SIGGRAPH 2022, arXiv 2205.01906):
- The low level is trained with **adversarial imitation** (a GAIL-style discriminator) plus a skill-discovery mutual-information encoder. z lies on a unit hypersphere.
- A high-level PPO policy outputs z.
- No tracker is involved, so coverage of the motion set is not guaranteed (mode collapse). It inherits the GAN instability we just saw with AMP.

**CALM** (Tessler et al., SIGGRAPH 2023, arXiv 2305.02195):
- A **motion encoder** maps reference clips to z.
- A **conditional discriminator** trains the low level to produce the encoded motion.
- High-level control works by latent selection or by FSMs.
- It is still adversarial.

**Why PULSE and MaskedMimic replaced them:**
- Distilling a near-perfect tracker by supervised DAgger is stable, covers the whole data set and needs no discriminator.
- PULSE reports large gains over ASE and CALM, for example the 93.4 % vs 37.6 % VR result above.
- LATENT's tennis comparison (§2.2) ranks LATENT > PULSE > ASE > AMP.
- For us, the AMP failure in `stage5b-style.md` is a direct argument against ASE and CALM.

### 1.4 Vid2Player3D: Zhang et al., "Learning Physically Simulated Tennis Skills from Broadcast Videos", SIGGRAPH 2023 (Best Paper Honourable Mention)
Sources: https://research.nvidia.com/labs/toronto-ai/vid2player3d, https://github.com/nv-tlabs/vid2player3d. Most mechanism details below are confirmed only through the LATENT and AdaPT papers' descriptions; I could not load the paper PDF (>10 MB).

**Pipeline:**
1. Broadcast video goes through player detection, camera estimation and 2D → 3D pose.
2. A **low-level imitation policy** with **external residual forces** physically corrects the noisy motion. LATENT notes this assumes unlimited joint torques and a root residual force.
3. A **kinematic motion VAE** is trained on the corrected motion.
4. A **high-level policy** samples in the MVAE latent. The decoded kinematic motion is followed by the separate tracker.

**Racket:** a hybrid action.
- The high-level output is [latent residual, **direct PD targets for the right wrist**], because video wrist estimates are unusable.
- Simple rewards, with no stroke-type labels.

**Footwork:** emerges from the planner choosing MVAE motions. There is no separate footwork module **[detail unverified]**.

**Code:** training code for all three stages plus a demo, Isaac Gym Preview 4. **No trained models**, because of the video licence.
- **Licence: NVIDIA License, non-commercial (research or evaluation only).**

---

## 2. Humanoid racket-sport papers (2025–2026)

| Paper | Robot / sim | Architecture | Human data | Racket and footwork | Results | Code / licence |
|---|---|---|---|---|---|---|
| **LATENT** (arXiv 2603.12686, 2026-03-13; Tsinghua, PKU, Galbot, Shanghai Qi Zhi, Shanghai AI Lab) | **G1**; MuJoCo via mujoco_playground / JAX + brax, 2 kHz sim, 50 Hz policy | **PULSE-style**: tracker → DAgger distillation into a conditional-VAE latent with a learned prior → high-level PPO over the latent | 5 h of amateur mocap from a 3 × 5 m area: forehand, backhand, lateral shuffle, crossover step and similar fragments. Unedited, retargeted with LocoMuJoCo | **Right-wrist control is removed from the tracker**, and the wrist is perturbed in training. The high level outputs [latent, direct right-wrist commands]. **Latent Action Barrier**: a = [D(s, μ_p + λσ_p·tanh(a_lat)), a_wrist]. Footwork comes from the shuffle and crossover primitives in the latent | Sim success rates: LATENT 96.5 / 82.1 % (forehand / backhand) vs PULSE 71.9 / 63.4, ASE 63.5 / 55.2, AMP 41.3 / 36.8. Real G1 vs a human: 90.9 % forehand, 77.8 % backhand returns, multi-shot rallies. Trained "on 8 GPUs" (no time given) | github.com/GalaxyGeneralRobotics/LATENT. **Only the tracker and a small data subset are released**; distillation and the high-level policy are listed as TODO. **No licence detected** (the CC BY 4.0 applies to the paper) |
| **AdaPT** (arXiv 2608.20087, 2026-08-20, CoRL 2026; Noitom, Shanghai AI Lab, SJTU, Dobot) | **G1** (and Dobot Atom); **mjlab**, PPO, 4096 envs on 4×RTX 4090, 3-layer MLPs | **Planner + tracker**: the tracker is trained with *randomized reference blending* (α mixes the current and previous reference frames, so playback speeds up or slows down). **Rally**: the planner outputs an MVAE latent z_t plus a speed α_t, with the MVAE as in Vid2Player3D. **Serve**: direct tracking plus a speed α_t and a residual action Δa | Broadcast video of Nadal, Federer and Djokovic (about 3–4.5 h each), via GVHMR → GMR → physics correction; plus professional mocap retargeted with UMR | The rally tracker also observes root orientation (torso rotation). Wrist perturbation during retargeting. Serve uses keyframe guidance on the racket and wrist through the backswing, and a parabola model of the toss | Sim rally success 91–96 %. Real G1 rally hit rate 44–64 % forehand, 28–56 % backhand. Serve 66–87 %. Baselines: RL-scratch, AMP, PULSE, NCP, Vid2Player3D, DeepMimic, AdaMimic | github.com/noitom-robotics/AdaPT, **Apache-2.0**. The README covers **serve tracking (stage 1)** plus a checkpoint and serve data. **The rally MVAE planner was not visibly released** [unverified]. Builds on AdaMimic (arXiv 2510.14454). rsl_rl version not stated |
| **HITTER** (arXiv 2508.21043, 2025-08-28; UC Berkeley) | **G1** (29 DoF); Isaac Lab, 50 Hz | **Model-based planner** (ball prediction, racket target and timing) + **goal-conditioned RL whole-body controller** | Only 2 clips (forehand and backhand) from GVHMR → GMR, used as an **upper-body imitation reward** | Controller inputs: racket target position and velocity, base target XY, time-to-strike. Sparse high-weight racket position, velocity and orientation rewards near strike; base-position reward before the strike | 92.3 % of 26 thrown balls returned; 106-shot rally with a human; humanoid vs humanoid rallies | No code found |
| **Human-like badminton** (arXiv 2602.08370, 2026-02-09, rev. 2026-09-14) | **EngineAI PM01, not a G1** (5-DoF arms); Isaac Lab | **Imitation-to-Interaction**, four stages: (1) privileged mocap tracker; (2) **goal-conditioned distillation** to a student observing time-to-hit, the target hit state and the target recovery state; (3) **AMP** fine-tuning for stability; (4) interaction RL with shuttle aerodynamics and "manifold expansion" of strike points | Expert badminton mocap, including racket pose, with optimisation retargeting | Racket and root pose targets at impact, with exponential decay weighting near the hit. Root-only recovery targets | Sim 95.2 / 91.5 % (easy / hard lifts). Real 90 % forehand, 70 % backhand lifts (10 trials) | No code found |
| **CyboRacket** (arXiv 2603.14605, 2026-03-15) | G1 | Onboard vision → trajectory prediction → **end-effector and base commands sent to the SONIC whole-body controller** | Through SONIC | Through SONIC | Onboard-vision tennis hitting (abstract only) | Not stated |
| **SMASH** (arXiv 2604.01158, 2026-04-01), table tennis | Robot not named in the abstract **[unverified]** | Whole-body skills with generative augmentation of strike motions; egocentric vision | "Scalable motion priors" | — | Consecutive strikes with onboard sensing | Not stated |

**Related non-racket work using the same pattern:**
- **RoboStriker** (boxing, arXiv 2601.22517): tracker → distilled hyperspherical latent → latent-space self-play.
- **Spherical Latent Motion Prior** (arXiv 2603.01294): tracker distillation plus adversarial and semantic terms.
- **Hybrid Motion Priors** (arXiv 2607.24083, G1): an RVQ discrete codebook distilled from an imitation expert.
- **SONIC** (arXiv 2511.07820, NVIDIA, G1): a 100M-frame tracker that acts as the decoder of a universal token space, with a kinematic planner on top.
  - Code: github.com/NVlabs/GR00T-WholeBodyControl, Apache-2.0. Weights are under the NVIDIA Open Model License.
  - Trained in Isaac Lab, not mjlab.
- **BeyondMimic** (arXiv 2508.08241): its second half distils trackers into a latent diffusion policy steered by classifier guidance.
- Found but not checked: "Humanoid Whole-Body Badminton via an Annealed RL Curriculum" (arXiv 2511.11218).
- No pickleball-specific humanoid paper was found.

---

## 3. Reusable libraries and code (for mjlab with rsl-rl-lib 5.4.2)

| Code | What it gives us | Simulator | Licence | Fit |
|---|---|---|---|---|
| **ProtoMotions 3** (github.com/NVlabs/ProtoMotions; created 2024-09, pushed 2026-09-22) | MaskedMimic, AMP, ASE, PPO, GPC/PEFT, ADD; G1 tracker-to-real tutorial; trains one tracker on BONES-SEED (~142k motions). The README lists **PULSE**, but the docs do not **[unverified]** | Isaac Gym, IsaacLab 3.0, Newton 1.0, Genesis (untested), **MuJoCo CPU** (used for evaluation and testing) | **Apache-2.0** | Best reference for **MaskedMimic model and loss code**, which can be ported. Not runnable on MuJoCo Warp or mjlab. Uses its own RL stack, not rsl_rl |
| PULSE / PHC (ZhengyiLuo) | The canonical PULSE VAE, prior and DAgger, and the downstream tasks | Isaac Gym | PULSE: none detected. PHC: BSD-3-Clause-Clear | Read for exact architecture; re-implement, don't copy PULSE |
| LATENT (Galbot) | Tracker only so far | MuJoCo / JAX / brax | None detected | Paper formulas only |
| AdaPT + AdaMimic | Speed-adaptive tracking and serve residual tracking, on **mjlab** | mjlab | Apache-2.0 | The closest code base to ours. Useful for the tracker's speed adaptation and for residual tracking |
| amp-rsl-rl (ami-iit) | AMP on rsl_rl PPO | Simulator-agnostic in principle; targets IsaacLab | BSD-3-Clause | No longer on our path |
| GR00T-WholeBodyControl / SONIC | A pretrained G1 tracker with 64-d motion tokens and a kinematic planner | Isaac Lab / deployment | Code Apache-2.0; weights under the NVIDIA Open Model License | Different robot model (no paddle) and simulator. A reference for a "planner + universal tracker" design |
| **rsl_rl 5.x itself** | PPO and **student-teacher Distillation** | — | BSD-3 | Distillation steps the env with **student** actions and regresses onto the teacher's (DAgger-style). That is from my knowledge of rsl_rl; **not re-verified for 5.4.2**. A KL / VAE student needs a **custom algorithm or module subclass** |

**mjlab** (github.com/mujocolab/mjlab, Apache-2.0, MuJoCo Warp 3.11) ships velocity and tracking tasks. It has no built-in distillation, AMP or latent-prior components. **No mjlab-native PULSE, MaskedMimic or ASE implementation was found.** AdaPT is the only mjlab racket-sport hierarchy found.

---

## 4. Recommendation for this project

### Choice: a LATENT-style latent action space (PULSE distillation) built from the existing tracking teacher, with the executor re-trained as a high-level PPO policy over [latent residual, right-wrist correction]
**Why this variant:**
1. **It reuses what we have.** The tracking teacher already exists, and PULSE, MaskedMimic and LATENT all *start* from a tracker. Distillation is supervised DAgger, which avoids the discriminator that failed.
2. **The closest published evidence matches our setup:**
   - LATENT is the same robot (G1), the same sport family, MuJoCo, and a similarly small, imperfect data set (5 h vs our ~2.4 h).
   - Its high-level policy over the latent beat PULSE, ASE and AMP in simulation and transferred to a real G1.
3. **It suits a PPO task policy.** The executor keeps its own rewards and drills: only its action space changes, from 29 joint targets to a 32-d latent plus 3 wrist DoF. The planner/tracker route (Vid2Player3D, AdaPT) needs an extra kinematic generator *and* puts generated, off-distribution references through a tracker that is still at 7.8 cm r-MPKPE.
4. **It stays compatible with MaskedMimic.** We can later add a sparse-goal prior (paddle pose at time t, root target) by changing the prior's input. MaskedMimic itself is the bigger build: a transformer prior, masking curricula, and published compute of 2 weeks on 4×A100 for AMASS. Its paper never shows an RL policy driving it.

### Pipeline (one variable per step, each with a frozen plan)
**P0. Teacher coverage.** Done or in progress. The teacher must cover the behaviours the executor needs:
- tennis strokes;
- LAFAN1 locomotion (walk, run, sprint);
- **ready stance, split-step, lateral shuffle and crossover**. LATENT's data had these explicitly; LAFAN1 may not. **Gap: check this.**
- Pickleball-specific dinks and underhand serves are absent from tennis clips. The latent can only express what the teacher tracks.

**P1. Teacher robustness.** DAgger visits states off the reference, so the teacher must recover from them. Evaluate the teacher with the student in control: as an early check, record teacher-label disagreement on student-visited states.

**P2. Distillation (new mjlab task plus a custom rsl_rl student).**
- **Encoder** E(s_p, g): g is the teacher's own command observation (reference joints and anchor error).
- **Prior** R(s_p) and **decoder** D(s_p, z): proprioception only, with **no reference information**.
- **z ∈ R^32**, the PULSE and LATENT-style default. Start with MLPs the width of the teacher.
- **Loss:** MSE to the teacher's action + α·0.005 smoothness + β·KL. Use PULSE's β 0.01 → 0.001 or MaskedMimic's 1e-4 → 1e-2; **pick one schedule up front**. Optionally make the encoder residual to the prior, as in MaskedMimic.
- **Rollouts with the student acting** (DAgger), on the same motion sampler, adaptive sampling, randomisation and terminations as the teacher.
- **Optional, LATENT-style:** drop right-wrist outputs from the decoder and perturb the wrist in training, so the high level owns the paddle face.
  - Our retarget already fixes the paddle normal during swings (`stage5b-paddle-orientation.md`), so this is a choice, not a necessity.
  - Make it the **second** variant, not the first.

**P3. Freeze the prior and decoder** and export them to an mjlab **action term**. It maps the high-level action [a_lat (32), a_wrist (3)] to joint PD targets:
- q* = D(s_p, μ_p + λσ_p·tanh(a_lat));
- wrist = decoder wrist + bounded residual.
- rsl_rl stays unmodified for the high level.
- Sanity check: rollouts from the prior alone with a_lat = noise. They should give stable, human-looking motion with no falls.

**P4. Re-train the executor over the latent** with the existing drills and rewards. **Remove the posture and style rewards** that conflicted: style should now come from the decoder.
- This is a fresh policy (a new action space), not a warm start. A BC warm start from S-D3b actions is not possible because the action spaces differ.
- Keep the same evaluation (`s5_gate_eval.sh`) and the 5-point retention rule against S-D3b.

**P5 (later, optional).** A MaskedMimic-style sparse-goal prior, or AdaPT-style speed adaptation of the tracker. A separate decision entry.

### Compute (estimates, not measured; RTX 4070, ~72k policy steps/s for flat velocity at 4096 envs per `stage0-throughput.md`, tracking will be slower)
- **Distillation:** PULSE used about 1e9 samples for AMASS, about 40 h of motion **[the AMASS size is from my own knowledge, not this research]**. At our ~2.4 h, **1–3e8 samples is a reasonable first budget**: about 1–2 h at 40–60k steps/s, fitting one or two of our ≤ 2 h runs. Teacher inference adds per-step cost, but no critic or PPO update is needed.
- **High-level executor:** comparable to the current executor runs (several chained ≤ 2 h runs). The latent space should cut exploration cost (PULSE and LATENT report faster learning than scratch), but **this is not guaranteed for our drills**.

### Risks
1. **Teacher quality caps the student.** The student can at best match it: r-MPKPE 7.8 cm (gate ≤ 6 cm unmet), and serves and smashes at 83–85 % per stroke.
2. **Coverage gaps.** There is no data for ready-position footwork or dinks, so the executor cannot produce them through the latent. AMP was failing for the same reason.
3. **KL balance.** If β is too high, the encoder carries no information and the student cannot track. If β is too low, the prior is uninformative and high-level exploration drifts off-manifold, giving robotic or unstable motion.
4. **Precision at contact.** A 32-d latent at 50 Hz may lack the precision to place the paddle face. LATENT's ablation says both the wrist correction and the Latent Action Barrier matter.
5. **Real-robot observations.** Teacher-only privileged observations (e.g. anchor or base linear velocity) must not leak into the prior or decoder if we deploy.
6. **Licences.**
   - PULSE and LATENT have no licence detected, so re-implement from the papers; don't copy.
   - Vid2Player3D is NVIDIA non-commercial.
   - LAFAN1 is CC BY-NC-ND, already restricted to non-commercial use (D-047).
   - ProtoMotions, AdaPT and mjlab are Apache-2.0, so their code can be reused with attribution.

### Gates (to fix before each launch; dev seeds only; final seeds never used)
- **G1, distillation fidelity:**
  - the student (encoder → decoder), on the same per-stroke evaluation as the teacher (`stage5b-tracking-06-wide-perstroke.json` protocol), keeps success ≥ teacher − 3 points overall and per stroke type;
  - r-MPKPE ≤ teacher + 1 cm;
  - falls ≤ 1 %;
  - LAFAN clips are evaluated separately.
- **G2, prior quality:** 1,000 rollouts of 10 s from the prior alone (noise σ fixed in the plan):
  - fall rate ≤ 5 % (threshold to confirm);
  - the style score (`scripts/motion/style_score.py`) of the prior rollouts close to the human floor of 0.94. For example ≤ 2.0, which is to be fixed in the plan.
- **G3, controllability:** a simple *paddle-reach* task (paddle to a random point within reach, plus a root target) learns to ≥ X % within a short, fixed budget over the latent. This checks that the latent can be steered before the full executor is attempted.
- **G4, executor:**
  - the Stage 5 task gate against S-D3b, with ≤ 5-point legal-return loss per family (no averaging);
  - target hits and A/B gain with intervals;
  - the style score **≥ 20 % lower** than S-D3b (the gate from `stage5b-style.md`);
  - side-by-side videos for the user.

### Not verified / open
- MaskedMimic's latent dimension, K and transformer size (they are in the supplement).
- Vid2Player3D's MVAE latent size and its exact wrist joints (the paper PDF could not be loaded).
- LATENT's latent dimension, λ, β and wall-clock time.
- Whether AdaPT released its rally MVAE planner, and its rsl_rl version.
- The robot used by SMASH.
- Whether ProtoMotions currently ships PULSE.
- The details of rsl_rl 5.4.2's Distillation internals.
