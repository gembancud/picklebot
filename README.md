# Picklebot

**A humanoid robot in a computer simulation learns to play pickleball.**

| Rally across the court | Returns from all parts of the court |
|:---:|:---:|
| ![The robot returns balls that land at different places on the court](docs/media/g1-rally.gif) | ![The robot returns balls from random positions on the court](docs/media/g1-side.gif) |
| **Play near the net** | **Walk to a spot** |
| ![The robot plays from the line near the net](docs/media/g1-kitchen.gif) | ![The robot walks to spots in all directions](docs/media/g1-move.gif) |

Each GIF is a short part of one test. The robot gets no help signals during the test.

## What is this project?

Pickleball is a paddle sport. It is similar to tennis on a small court.

This project teaches a robot to play pickleball. The robot is a Unitree G1. The G1 is a humanoid robot with 29 joints. A paddle is attached to its right wrist.

All of the work is in a computer simulation. The simulation calculates the movement of the robot, the ball and the paddle with the laws of physics. No real robot is used yet.

Nobody writes the movements of the robot by hand. The robot learns them by practice.

## How the robot learns

1. **Trial and reward.**
   - The robot tries an action.
   - The computer gives it points for a good result, for example a ball that goes over the net.
   - It loses points for a bad result, for example a fall.
   - After millions of tries, the robot does more of the actions that get points.

   This method is "reinforcement learning".
2. **Many courts at the same time.** One graphics card runs approximately 12,000 copies of the court at the same time. Thus, the robot gets a very large quantity of practice in a few hours.
3. **Human movement as a model.**
   - We use recordings of real people who play tennis, walk and run (motion capture).
   - First, the robot learns to copy these movements.
   - Then, it builds all of its actions from them.

   This makes its movement look more human.
4. **Teachers and students.** Sometimes we train a specialist, for example a robot that only walks. Then a second robot learns to copy the specialist. This is how one robot gets many skills.
5. **Small corrections.** When a skill is good, we keep it fixed. A small second controller learns corrections on top of it. Thus, the robot does not forget the old skill.

## What the robot can do now (October 2026)

| The robot can | The robot cannot do this yet |
|---|---|
| **Walk to a spot.** It walks to spots 0.5 m to 3 m away, in all directions. It arrives 99.7 % to 100 % of the time. | **Volleys.** It cannot hit the ball before the ball bounces (0 %). |
| **Return balls.** We send 20 types of shots to all parts of its half of the court. Approximately 78 % of them go back over the net legally. | **Some difficult shots.** High lobs: 31 % to 49 %. Deep balls behind it: 18 % to 61 %. Backspin balls when it stands near the back line: 53 %. |
| **Play rallies.** The balls land at fixed places on the court, as in a game. It returns 77 % of these balls. Approximately 1 rally in 10 gets to 10 shots. Before the last stage, it was fewer than 2 rallies in 100. | **Stay balanced.** It falls in approximately 6 % of the practice points. The target is 1 %. |
| **Use human movements** when it walks and hits. These movements come from recordings of people. | **Run like a person.** At high speed, it moves less like a human. We have no recordings of people who run with a paddle yet. |

**Why long rallies are difficult.** A rally of 10 shots needs 10 good returns, one after the other. With 77 % for each shot, only approximately 1 rally in 10 gets to 10 shots. For 2 rallies in 10, the robot must return approximately 85 % of its shots.

**How we test.**
- Each stage has a target, the "gate".
- We test each robot many thousands of times, with new random situations.
- We report all results, also the failures.

The last stage (5D) did not reach its gate: 2 of 5 items passed. [Stage 5D report](mjlab/results/stage5d-gate.md)

## Project stages

| Stage | What the robot learned | Result |
|---|---|---|
| 0 to 4 | Ball physics. A robot that stands, hits balls and aims them. | Passed (stage 4 with small exceptions) |
| 5 | Walking and hitting together. | Not passed. Its best robot was the start for 5B. |
| 5B | Human-like movement from motion capture. | Passed: 93.9 % of returns legal |
| 5C | Play on the whole court. Walk to any spot. | Not passed: walking passed, volleys and falls failed |
| 5D | Rallies against balls that land at fixed places. | Not passed: rallies to 10 shots rose from 1.75 % to 9.6 % |

## Next steps

1. **Stage 5E: more reliable shots.**
   - A practice game that is more like a real game.
   - The robot gets the spot where it must stand for each ball. A planner calculates this spot from the flight of the ball. The planner gets ball data with small errors and delays, as a real camera gives.
   - Fixes for the falls and for the difficult shots.
   - Recordings of human footwork from the 100STYLE dataset (Mason, Starke and Komura, CC BY 4.0) for more human movement.
2. **Volleys and play at the net.**
3. **Later:**
   - a more robust robot;
   - two robots that play against each other;
   - a robot that decides its own strategy;
   - doubles.

This is a research prototype in simulation. Nothing here has run on a real robot.

## Words used in this project

| Word | Meaning |
|---|---|
| Simulation | A computer model of the robot, ball and court that obeys physics. |
| Reinforcement learning (RL) | Learning by trial and reward. |
| Policy, controller, executor | The program that tells the robot joints what to do, many times each second. |
| Motion capture (mocap) | Recordings of real human movement. |
| Drill | A practice exercise, for example "walk to this spot" or "return this ball". |
| Feed | A ball that is sent to the robot. |
| Rally | A series of returns without a miss. |
| Volley | A hit before the ball bounces. |
| Kitchen | The area near the net. In pickleball, you cannot volley from this area. |
| Gate | The target that a stage must reach. |
| Seed | A number that sets the random situations in a test. Each test uses new seeds, so the results are fair. |

## From Unity to mjlab

The project started in the Unity game engine. In October 2026, it moved to mjlab. mjlab is a robot simulator that runs on a graphics card. The old Unity work stays as a reference ([Unity README](docs/archive/README-unity-2026-10-17.md)).

| | Unity (to September 2026) | mjlab (from October 2026) |
|---|---|---|
| **Body** | A simple player with 18 controls | The Unitree G1 humanoid robot with 29 joints and a paddle |
| **Physics** | Calculated on the main processor | Calculated on the graphics card, with a ball model for spin, bounce and net |
| **Speed of practice** | Approximately 1,000 steps each second | 40,000 to 55,000 steps each second |
| **Movement** | Learned directly | Learned from human recordings |
| **Footwork** | Mostly in the center of the court | Walks to any spot 0.5 m to 3 m away |
| **Shots** | Serves and returns | 20 types of returns from all parts of the court. No serves or volleys yet. |

The two projects use different robots and different tests. Thus, you cannot compare their numbers directly.

## Technical details

This section is for readers who know robot learning.

- **Stack:**
  - mjlab 1.6 (MuJoCo Warp) and rsl_rl PPO;
  - one RTX 4070 at 12,288 parallel environments;
  - an analytic GPU ball model (drag, spin, bounce, net, paddle).
- **Motion prior:**
  - H0: a tracking teacher on retargeted tennis mocap and LAFAN1;
  - H1: a latent motion controller distilled from H0;
  - an executor (PPO) that steers the latent space at lambda 3.
- **Methods:**
  - DAgger distillation;
  - kickstarting (footwork from a flat walking teacher);
  - residual PPO around a frozen executor;
  - a learning-progress curriculum over feed family, level and court zone.
- **Shown executors:**
  - rally GIF: Stage 5D `s5d-01-rally/model_1800`, dev seed 4200364;
  - other GIFs: Stage 5C `s5c-22-res-rally/model_900`, dev seed 4200910.

  All are deterministic, with no hints.
- **Evaluation:** final numbers are pooled over four fresh development seeds and paired against the stage's starting executor. Final acceptance seeds are never used.

**Try it:** Linux or WSL2 with a CUDA GPU.
- **Setup:** run `mjlab/env/setup_wsl.sh`, which pins mjlab 1.6.0. The full freeze is in `mjlab/env/requirements-freeze.txt`.
- **Tasks:** registered as `Picklebot-*` (`mjlab/picklebot_mj/tasks/`).
- **Scripts:** training and evaluation scripts are in `mjlab/scripts/` (e.g. `train_run.sh`, `h5c_eval.sh`, `h5c_videos.sh`).
- **Not in the repository:** checkpoints and motion data.

**Links:**
- [Roadmap and log](docs/MJLAB_PIVOT.md)
- [Decision log](docs/DECISIONS.md) (D-038 onward for mjlab)
- run logs: [Stage 5C](mjlab/results/stage5c.md), [Stage 5D](mjlab/results/stage5d.md)
- gate reports: [Stage 5C](mjlab/results/stage5c-gate.md), [Stage 5D](mjlab/results/stage5d-gate.md)
- [Unity README](docs/archive/README-unity-2026-10-17.md), [older technical archive](docs/archive/README-before-2026-09-11.md), [architecture history](docs/ARCHITECTURE.md)
