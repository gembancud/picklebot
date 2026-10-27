# Literature review: learned whole-body racket/ball hitting (for Picklebot G1 rallies)

Compiled 2026-10-27. I opened every source below on arXiv or the publisher page. Numbers come from the paper text unless marked otherwise. "Not reported" means I could not find it in the text I read, which was often truncated at about 100k characters, so some details may sit in appendices I did not see. **No pickleball robot paper was found.**

## 1. Systems (newest first)

| System | Robot / sim | Architecture | Priors | Reported success |
|---|---|---|---|---|
| **PingpongDuo** (Jiang et al., arXiv [2610.20579](https://arxiv.org/abs/2610.20579), Oct 2026) | 2x G1 29-DoF, Isaac Lab | Team planner (constrained PPO) proposes lateral base targets; a per-robot state machine switches separate footwork and strike skills; arm residual | ~200 human doubles footwork clips (GMR retarget) | Sim composed legal return 55.6 % (HITTER composed 42.4 %, SMASH 35.8 %). Mean consecutive returns in sim 4.87 vs 3.60 rule-based. Real: >10 alternating strikes |
| **From Hitter to Player** (Dong et al., arXiv [2610.14067](https://arxiv.org/abs/2610.14067), Oct 2026) | G1, sim not named | Model-based strike planner, then MLP whole-body controller (512/256/128); separate PPO strategy picks one of 9 landing targets per stroke | Physics ball model; AMP term in training | Sim legal landing 99.2 %, 94.3 % within 30 cm of target. Real: won 3 games vs one recreational player. Per-shot hit rates only in figures |
| **AdaPT** (Huang et al., arXiv [2608.20087](https://arxiv.org/abs/2608.20087), Aug 2026) | G1 (+ Dobot Atom), **mjlab**, 4096 envs, 4x RTX 4090 | Planner outputs MVAE latent + speed scalar; tracker executes; serve adds residual | Broadcast-video motions of pros (MVAE) | Sim rally success 91.5–96.3 %; real rally hit rate only 44–64 % |
| **SMASH** (Ren et al., arXiv [2604.01158](https://arxiv.org/abs/2604.01158), Apr 2026) | G1 | Model-based predictor picks strike target; one PPO whole-body policy (asymmetric critic); strike reference found by nearest-neighbour search in a motion library | 400 mocap strike clips + Motion-VAE augmentation | Real 50-min run: 93.7 % contact, 59.7 % return (backhand 38.9 %) |
| **CyboRacket** (Ren et al., arXiv [2603.14605](https://arxiv.org/abs/2603.14605), Mar 2026) | G1 | Onboard vision + trajectory prediction feeding end-effector/base commands to the pretrained SONIC whole-body controller | Large pretrained tracker | Tennis hitting demo; no rates in abstract |
| **LATENT** (Zhang et al., arXiv [2603.12686](https://arxiv.org/abs/2603.12686), Mar 2026) | G1 tennis, MuJoCo JAX (Playground), 8 GPUs | Motion tracker, then **distilled into a conditional-VAE latent skill space** (DAgger + KL to a learned prior); high-level policy outputs **latent action + direct wrist correction**; "latent action barrier" clamps the latent to μ ± λσ·tanh | ~5 h of fragment clips (forehand, backhand, shuffle, crossover step) | Sim (return within 2.5 m of target, 10k trials): forehand 96.5 %, backhand 82.1 %, forecourt 86.4 %, backcourt 89.8 %. Real (20 rallies): 78–91 %. Sim self-play: up to 25 consecutive shots over 50 games |
| **Human-like badminton** (Chen et al., arXiv [2602.08370](https://arxiv.org/abs/2602.08370), Feb 2026) | EngineAI PM01, Isaac Lab | Mocap tracking teacher, DAgger into a student conditioned on time-to-hit + target, then AMP-stabilised RL, then interaction refinement | Mocap, then AMP | Sim lift success 95.2 % easy / 91.5 % hard; end-to-end AMP baseline 85.9 / 73.9 %; ASE and VQ baselines ~0 %. Real 9/10 forehand, 7/10 backhand; no rallies |
| **Humanoid whole-body badminton** (Liu et al., arXiv [2511.11218](https://arxiv.org/abs/2511.11218), Nov 2025) | Phybot C1, Isaac Gym, 4096 envs, 1x RTX 4090, 12.4 h total | Single policy; EKF supplies hit position/orientation/time; 3-stage curriculum | **No motion priors** | Real 91.3 % (42/46). Sim two-robot best rally 21 returns. A prediction-free variant was only "modestly" worse (sim, no numbers) |
| **PACE** (Hu et al., arXiv [2509.21690](https://arxiv.org/abs/2509.21690), ICRA 2026) | Booster T1, Isaac Lab, 4096 envs, RTX 4090 | **End-to-end** policy plus a small learned apex predictor; base-shift command Δp = p̂_ball − p_base in the actor obs; privileged critic | No mocap; physics-guided dense rewards | Sim (>250k serves) hit 96–99 %, success 92.3–95.0 % (mixed 94.1 %). Real 93.5 % hit, 61.3 % return. **Without the predictor: "almost no successful returns"** |
| **HITTER** (Su et al., arXiv [2508.21043](https://arxiv.org/abs/2508.21043), Aug 2025) | G1 29-DoF, Isaac Lab | Model-based planner gives racket target pos/vel/time-to-strike and a **base position target**; PPO whole-body controller; asymmetric critic | 2 human swings (video, then GMR), BeyondMimic-style upper-body tracking | Real 24/26 returned (92.3 %); max 106 consecutive shots vs a human (one best trial); robot–robot rallies shown without counts. Footwork mainly lateral |
| **ETH ANYmal badminton** (Ma, Cramariuc, Farshidian, Hutter, arXiv [2505.22974](https://arxiv.org/abs/2505.22974); Science Robotics 2025, DOI 10.1126/scirobotics.adu3922) | ANYmal-D + DynaArm, Isaac Gym, 4096 envs | Single whole-body policy; EKF predicted interception point + time-until-interception as commands; perception-noise model; constrained PPO (N-P3O) | None (no mocap) | Max real rally 10 shots. Sim: "negligible failure" with perfect perception, lower at court borders and **for shots landing behind the robot**. Reached max reward in 4.8 h on a 2080Ti, but **deployment policies trained 11–22 days** |
| **DeepMind competitive table tennis** (D'Ambrosio et al., arXiv [2408.03906](https://arxiv.org/abs/2408.03906), 2024) | ABB arm on 2D gantry (not legged), MuJoCo | **Skill library**: 17 small CNN low-level skills trained with evolution strategies (BGS) + a high-level selector (skill stats tables + online bandit) | Human-play ball distributions; 7 sim–real data cycles | Sim return "typically >80 %"; real per-skill land rate 0.23–0.75; 45 % match wins vs humans |
| **Wang, Hodgins, Won**, "Strategy and Skill Learning for Physics-based Table Tennis Animation" (SIGGRAPH 2024, arXiv [2407.16210](https://arxiv.org/abs/2407.16210)) | Simulated character, Isaac Gym | ASE skill policies, then ball-control policies, then a mixer; strategy trained by iterative self-imitation BC | Mocap | Agent–agent cooperative rally average 16–18 rounds; average 10.9 consecutive returns. No footwork modelled |
| **Vid2Player3D** (Zhang et al., SIGGRAPH 2023, [project](https://research.nvidia.com/labs/toronto-ai/vid2player3d)) | Simulated tennis character | Low-level imitation + motion embedding; high-level planner with **hybrid correction** overriding bad parts of the embedding | Broadcast video | Two-player sim rallies shown; **I could not confirm rally-length numbers** |
| **DeepMind OP3 soccer** (Haarnoja et al., Science Robotics 2024, arXiv [2304.13653](https://arxiv.org/abs/2304.13653)) | Small biped | Skill teachers (score, get-up), then one agent regularised to teachers + self-play | Teachers | Not a hitter. Useful because the KL-to-teacher weight is switched off once performance passes a threshold |

Others seen: SMPLOlympics (arXiv [2407.00187](https://arxiv.org/abs/2407.00187), simulated humanoid sports suite). DeepMind robot-vs-robot cooperative table tennis rallies: sim RL plus a few hours of real fine-tuning, per an [IEEE Spectrum article](https://spectrum.ieee.org/deepmind-table-tennis-robots) from July 2025 (secondary source; no paper verified).

## 2. Footwork, far balls and timing

- **An explicit base target is almost universal.** HITTER gives a base-position target and rewards base tracking only before the strike, with racket rewards only near hit time. PACE puts a base-shift vector (predicted ball xy − base xy) in the actor obs and penalises base position and velocity error. Phybot trains footwork first (Stage 1 `target_approach`, weight 30, 0.3 m tolerance), then removes that reward in Stage 3. PingpongDuo uses a separate footwork skill driven by a planner's lateral targets.
- **Distance drives gait choice (ETH).** Near 0.5 m the robot barely steps. At 1.5 m it uses irregular steps. At 2.2 m it gallops from 1.6 s to 0.6 s before the swing. With 0.4 s available the ball was unreachable.
- **Behind-the-robot and backhand balls are the weak spot everywhere.** ETH is lower for shots landing behind the robot. LATENT is backhand 82 % vs forehand 96.5 %. SMASH real backhand return is 38.9 %. HITTER is lateral-only by design. This matches your left/back weakness, and nobody reports having solved it.
- **Timing / commitment.** Most systems give time-to-hit as an input (HITTER, ETH, Phybot, Chen et al.). Planner estimates converge late: HITTER position error drops under 7.5 cm only about 0.5 s before the strike and timing error under 20 ms about 0.3 s before. Phybot's EKF is under 10 cm at 0.6 s. So the published systems **start moving on a coarse early estimate and refine it**; the base target is updated continuously. No paper describes a separate "commit" mechanism. Your late commitment probably means the policy is not moving toward an early predicted contact point, or is not rewarded for doing so.

## 3. Two-agent rallies / self-play

- **Rallies are harder than fed balls.** PingpongDuo's composed sim legal-return rates of 36–56 % are much lower than the single-ball numbers the same methods report. From Hitter to Player found that **motor self-play on rally-generated states (Stage II, against a lagged snapshot)** beat matched-budget single-ball training on legal-return and landing accuracy at every rally index (figure only). PingpongDuo trains each skill from the states the other skill produces.
- **Reported rally lengths.** Sim: Phybot best 21, LATENT best 25 (over 50 games), Wang et al. average 16–18 (animation, no locomotion), PingpongDuo mean 4.87. Real robot–robot: HITTER and PingpongDuo (>10) show rallies but give few counts.
- **Training recipes.** Shared mirrored policy (PingpongDuo, Phybot, HITTER). Lagged-snapshot opponent (Hitter to Player; OP3 soccer used early snapshots for stability). Self-imitation BC on successful exchanges (Wang et al.). Real fine-tuning in a robot-vs-robot cooperative setup (DeepMind, secondary source).

## 4. Is ~96 % per shot realistic?

Per-shot numbers in sim, with definitions that differ between papers:

- PACE 94.1 % (mixed serves, table tennis, single ball)
- LATENT 96.5 % forehand but 82–90 % on the other categories
- AdaPT 91.5–96.3 %
- Chen et al. 91.5–95.2 % (single shots)
- From Hitter to Player 99.2 % legal landing (it was unclear to me whether this is conditional on contact)

Arithmetic: 0.96^5 = 0.815, 0.94^5 = 0.73, 0.90^5 = 0.59. Your 0.705^5 = 0.17 matches the measured 18.7 %, so shots look roughly independent.

**My read:** about 94–96 % per shot appears in sim only for single balls from a fixed launch distribution, usually forehand-heavy and on a table-tennis-sized workspace. **No paper reports ≥95 % per shot on closed-loop two-robot rally states with large footwork.** The closest closed-loop evidence is LATENT's best of 25 and Phybot's best of 21, which are maxima, not rates. So 80 % of rallies reaching 5 shots is beyond published sim evidence for this setting; it is not impossible, but it is unproven. A two-robot rally also means each robot faces the other's imperfect returns, which is harder than fed balls (the PingpongDuo numbers show this).

## 5. What the literature suggests for us

Across papers, the recurring recipe is: **an explicit interception predictor (point + time-to-hit) and a base-position target fed to a whole-body policy that was trained from the start with those inputs, plus a motion prior for swings, rewards switched by phase, and closed-loop rally training at the end.**

Ranked by fit to our stack:

1. **Keep the latent prior but give the high level a direct correction path and the planner signal, like LATENT.** LATENT is the closest match: G1, latent skill space, and a high-level policy that outputs latent + direct wrist correction. Removing the correction cost 14 pp forehand and 13 pp backhand. That fits our finding that a residual on a frozen stack ignored the teacher input: in every paper the contact target is a **command that the controller was trained to track**, not an optional extra input to a residual. Concretely, turn the planner on and train with predicted contact point, time-to-hit, and a base-target vector, plus a base-tracking reward that is active only before contact (HITTER, PACE).
2. **Phase-switched / annealed shaping (Phybot, Chen et al., OP3).** Phase 1 rewards approach to the predicted contact location (this targets the 1 m end distance and late footwork directly). Then add the hit reward with a tolerance tightened over training (σ 2.0→0.1 m). Then remove the shaping and tune with only domain randomization. For priors, OP3 drops the teacher KL once a performance threshold is reached. Chen et al. show tracking, then DAgger, then AMP fine-tuning beating plain end-to-end AMP (85.9→95.2 % easy).
3. **Rally-state training last (Hitter to Player Stage II, PingpongDuo).** Train the motor policy on states from rallies against a lagged copy, not only on fed balls.
4. **End-to-end from scratch with a privileged critic (PACE, ETH, Phybot)** is viable at our compute: all three used 4096 envs on one consumer GPU, and Phybot took 12.4 h total. But PACE says a predictor is essential, and ETH trained deployment policies for 11–22 days. Note that most "privileged" work uses an asymmetric critic, not teacher-student distillation; distillation appears only for motion priors (LATENT, Chen et al.).
5. **Skill library + selector (DeepMind, Wang et al.)** works on a gantry arm or in animation. It handles footwork poorly and was not used for legged hitters.

Compute reference: 4096 envs is typical (ETH, Phybot, PACE, AdaPT on 4x 4090 in mjlab, LATENT on 8 GPUs). Our 12,288 envs on a 4070 is in range. Wall-clock times are rarely reported.

## Flags / uncertainties

- HITTER's 106 is a single best trial. Most real-world counts are small (10–46 trials).
- The 2026 papers (PingpongDuo, Hitter to Player, AdaPT, SMASH, LATENT) are arXiv preprints; I did not check whether they were peer reviewed.
- Success definitions differ: hit vs legal landing vs within 2.5 m of target. LATENT's 96.5 % uses the 2.5 m-of-target definition.
- I did not verify Vid2Player3D rally statistics, the SMPLOlympics method details, or the DeepMind robot-vs-robot follow-up beyond press coverage.
- The badminton Phybot paper's title changed between versions ("Multi-Stage RL" vs "Annealed RL Curriculum").
