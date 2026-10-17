# Picklebot

**Teaching a simulated humanoid to move around the court and play pickleball.**

Unitree G1 (29 DoF, paddle on the right wrist) · mjlab / MuJoCo Warp on the GPU · PPO · human motion prior from tennis mocap and LAFAN1

| Rally across the court | Court-wide drill |
|:---:|:---:|
| ![G1 returning court-anchored feeds across the court](docs/media/g1-rally.gif) | ![G1 returning feeds from random court positions](docs/media/g1-side.gif) |
| **Kitchen-line play** | **Move to any spot** |
| ![G1 playing from the kitchen line](docs/media/g1-kitchen.gif) | ![G1 walking to spots in every direction](docs/media/g1-move.gif) |

Deterministic, no hints.
- **Rally GIF:** Stage 5D executor `s5d-01-rally/model_1800`, dev seed 4200364 ([Stage 5D report](mjlab/results/stage5d-gate.md)).
- **Other GIFs:** Stage 5C executor `s5c-22-res-rally/model_900`, dev seed 4200910 ([Stage 5C report](mjlab/results/stage5c-gate.md)).

## Where it stands (Stage 5D, 2026-10-17)

| Working | Still learning |
|---|---|
| **Rallies:** 77.4 % of shots aimed at fixed court spots returned (Stage 5C: 62.5 %); 9.6 % of rallies reach 10 shots (5C: 1.75 %) | **Rally length:** 20 % of rallies reaching 10 needs about 85 % per shot; volleys 0 %, lobs 31-49 %, deep reaches 18-61 %, deep backspin 53 % |
| **Court-wide returns:** 78.3 % legal over 20 feed families x 3 court zones; 39 of 55 cells >= 75 % | **Falls:** 5.9 % on court (gate 1 %) |
| **Footwork:** walks to spots 0.5-3 m away in every direction, 99.7-100 % arrival | **Movement style:** score 4.2 (gate 3.86); fast running poses have no human reference yet |
| **Motion prior:** human-like movement learned from tennis mocap and LAFAN1 | **Recovery:** about 1.2 m from the recovery spot after a hit |

Final numbers are pooled over four fresh development seeds and paired against the stage's starting executor. The Stage 5D gate was **not met** (2 of 5 items). The report gives the distance on every criterion and every rule deviation.

## From Unity to mjlab

The project started in Unity with ML-Agents. Its last checkpoint (24M steps) and the docs are kept as a reference ([Unity README](docs/archive/README-unity-2026-10-17.md)). In October 2026 the training moved to mjlab (MuJoCo Warp + rsl_rl) with a Unitree G1 ([plan and log](docs/MJLAB_PIVOT.md)).

| | Unity (to 2026-09) | mjlab (from 2026-10) |
|---|---|---|
| **Body** | Simplified player: bounded shoulder, elbow, wrist and body channels (18) | Unitree G1 humanoid, 29 joints, rigid paddle on the right wrist |
| **Physics** | Unity CPU physics | MuJoCo Warp on the GPU; analytic GPU ball model (drag, spin, bounce, net, paddle) |
| **Throughput** | About 1k env steps/s (8 workers x 16 courts) | 40-55k env steps/s at 12,288 parallel envs on one RTX 4070 |
| **Learning** | ML-Agents PPO, goal-conditioned executor | rsl_rl PPO, plus distillation (DAgger), kickstarting, residual policies, learning-progress curriculum |
| **Motion** | Learned directly in the control channels | Human motion prior: tracking teacher, then a latent controller, then an executor steering its latent |
| **Footwork** | Central returns; wide, deep and short movement still learning | Walks to any spot 0.5-3 m away (99 %+ in every direction) |
| **Shots** | Fixed-ball serve, returns after a bounce, airborne returns | 20 feed families (incl. topspin, backspin, drops, lobs, cross-court) from anywhere on the half court; no serves or volleys yet |
| **Rules** | Two-bounce and kitchen rules in the match engine | The same rules on the GPU (two-bounce, kitchen and momentum faults, out, net) |
| **Best tests** | 224/224 narrow, 260/384 wide, 352/448 randomized returns; 64/64 serves | 78-79 % legal over 55 zone x family cells; 99 %+ move-to-spot arrival; 9.6 % of rallies reach 10 shots (77 % per shot) |

The two sets of numbers come from different tasks, bodies and test batteries, so they are not directly comparable.

## How the G1 learns

1. **Stage 0-4 — ball, court and hitting:** physics trials, then a standing G1 that returns fed balls and aims them.
2. **Stage 5 — footwork drills:** a flat walking teacher and a flat hitting teacher, distilled into one student.
3. **Stage 5B — human motion prior:** a tracking teacher on retargeted tennis mocap and LAFAN1 locomotion, distilled into a latent motion controller. A PPO executor steers its latent space (gate met: 93.9 % legal on the Stage 5B drill, style 3.81).
4. **Stage 5C — full court:** court zones, volleys and kitchen rules, a move-to-spot drill and a rally test.
   - Footwork in the latent space came from **kickstarting** the flat walking teacher.
   - PPO then improves as a **residual** around a frozen two-skill executor, which keeps both skills.
5. **Stage 5D — rally training:** court-anchored feeds from a scripted far-court opponent, long episodes and a rally bonus.
   - Per-shot reliability rose from 62 % to 77 %, and rallies reaching 10 shots from 1.75 % to 9.6 %.
   - Style, speed and gait penalties on the residual did not lower the style score.

[Roadmap and log](docs/MJLAB_PIVOT.md) · [Decision log](docs/DECISIONS.md) (D-038 onward for mjlab) · [Stage 5C runs](mjlab/results/stage5c.md) · [Stage 5D runs](mjlab/results/stage5d.md)

## Try it

Linux or WSL2 with a CUDA GPU. To set up the environment, run `mjlab/env/setup_wsl.sh`, which pins mjlab 1.6.0; the full freeze is in `mjlab/env/requirements-freeze.txt`. Tasks are registered as `Picklebot-*` (`mjlab/picklebot_mj/tasks/`). Training and evaluation scripts are in `mjlab/scripts/` (e.g. `train_run.sh`, `h5c_eval.sh`, `h5c_videos.sh`). Checkpoints and motion data are not in the repository.

## Next

1. **Stage 5E — per-shot reliability:**
   - a realistic rally drill (feed mix, position-dependent recovery, pacing set by the robot's own return);
   - a stance-spot planner fed by noisy, delayed ball state;
   - targeted fixes for falls and the weak shot families;
   - human footwork style from the 100STYLE mocap dataset (CC BY 4.0).
2. **Volleys and net play:** possibly a goal-conditioned motion controller that takes hand and root targets, decided by Stage 5E's rebuild rule.
3. **Later:** robustness and distillation (Stage 6), two-robot rallies, a learned strategy and doubles (Stage 7+).

This is a learning prototype in simulation; nothing here has run on a real robot.

[Unity README](docs/archive/README-unity-2026-10-17.md) · [Older technical archive](docs/archive/README-before-2026-09-11.md) · [Architecture history](docs/ARCHITECTURE.md)
