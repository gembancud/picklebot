# Competitive paddle prototype

D-026 changes the default demo from cooperative returns to competitive points.
The earlier [cooperative prototype](AI_RALLY.md) remains available.

## Run

1. Open `Assets/Picklebot/Scenes/AIRally.unity` in Unity.
2. Press Play. Select the Game tab.
3. Use Space to pause. Use R to repeat the serve.
4. Use the Slow motion button to inspect contact and rebound.

Each paddle must return the ball after one bounce. The return must land on the
opposite half. A miss, second bounce, volley, wrong-side landing, or net contact
ends the point. The score increases for the winner. A new serve starts after
1.5 seconds. Serve direction alternates. A 30-second safety cap awards no point.
This is a simplified point loop, not full match scoring or regulation service.

## Physics and size

| Setting | Earlier demo | Competitive demo |
| --- | ---: | ---: |
| Court | 1.8 by 3 m | 1.8 by 3 m |
| Paddle face | 0.40 by 0.40 m | 0.18 by 0.20 m |
| Paddle thickness | 0.035 m | 0.020 m |
| Ball radius | 0.035 m | 0.025 m |
| Court restitution | 1.00 | 0.86 |
| Paddle restitution | 1.00 | 0.90 |
| Maximum paddle travel speed | 8 m/s | 2 m/s |
| Air drag | None | Acceleration = -0.025 × speed × velocity |

Gravity is 9.81 m/s². The physics step is 1/240 second. Ball restitution is 1;
surface restitution combines by multiplication. Friction is zero. There is no
spin model. A kinematic paddle can add energy through its physical swing.
No code changes ball velocity during a point to guide it towards a target.
Only the serve reset assigns velocity. Gravity, drag, and collisions then act
on the ball. A 1 m drop produced a first rebound of about 0.719 m in Unity.

These are explicit prototype settings. They are not measured table-tennis or
pickleball parameters. The original pickleball calibration gate remains open.

## Two learned controls

The stroke network observes ball position, ball velocity, bounce state, a
landing target, and flight duration. Two 96-unit tanh layers produce six motor
commands: impact x/y, normal slopes x/y, swing speed, and contact time.
Offline numerical examples train this network by behavioral cloning. The
runtime does not use the numerical teacher. A bounded motor follows the six
commands. The paddle keeps its current position after a hit; there is no
scripted return to the centre.

The shot-selection network observes the ball state and both paddle x
positions. Two 32-unit tanh layers produce five action logits. The actions
select left/right short, left/right deep, or centre landing targets. The game
uses the highest-logit action. This makes a replay repeatable on the same
runtime. Each side uses its own rotated observation frame and motor state.
Both sides share trained weights. Shared weights do not imply a shared reward.

The shot policy trains with PPO. Each point gives the winner +1 and the loser
-1. A time cap gives both sides zero. Rewards have a 0.97 discount between a
player's shots. An entropy term of 0.02 supports exploration. Training alternates
between a centre-directed opponent on each side and shared-policy self-play.
The stroke model remains frozen. There is no reward for long rallies.

The shot choices and motor are still constrained. This is an initial
competitive policy, not a general sports agent. It does not learn recovery
position, a continuous landing target, shot pace, spin, or body movement.

## Local training

Use the existing `.venv/phase1c0` environment. The scripts use CPU PyTorch.
No cloud machine is required for this experiment.

```sh
.venv/phase1c0/bin/python scripts/competition-skill-train.py --steps 18000
```

Import the stroke model and compile the Unity scripts. Enter Play mode before
shot training. Pause the visible demo so it does not compete for simulation
time. The collector uses a separate hidden local physics scene.

```sh
.venv/phase1c0/bin/python scripts/competition-train.py --iterations 30 --episodes 96
.venv/phase1c0/bin/python scripts/competition-reference.py
```

Training records are in `artifacts/competition/train-*.json`. PyTorch checkpoints
are in `artifacts/competition/training/`. Runtime models, manifests, and Python
reference outputs are in `Assets/Picklebot/Competition/Models/`.
Training point seeds start at 830500. Validation uses [840000,850000). These
partitions do not use the original pickleball final-evaluation seeds.

## Verification

Compile first. Confirm that `recompile_status` reports no errors. Then run:

```sh
unity command run_tests --mode editor --filter Picklebot.Competition.Tests --filter_type assembly --async_tests true
unity command test_status
unity command run_tests --mode play --filter Picklebot.Competition.PlayTests --filter_type assembly --async_tests true
unity command test_status
```

Wait for each test run to finish before starting the next. The Play mode tests
check paddle size and measured rebound. The Editor tests check model validation,
64 PyTorch-to-C# reference predictions for each model, and shot changes when the
opponent changes side. Run the existing
`Picklebot.Rally.Tests` assembly to check bounce and point rules as well.
The test runner can change the active scene. Open `AIRally.unity` again and
enter Play before point evaluations.

```sh
unity command eval 'return Picklebot.Competition.Editor.CompetitionEditor.Collect(840000,100,"self-final","Assets/Picklebot/Competition/Models/strategy.json","self");'
unity command eval 'return Picklebot.Competition.Editor.CompetitionEditor.Status;'
```

Wait for completion before starting another collection. Use mode `near` and
then `far` with labels `near-final` and `far-final` to test the policy against
the centre-directed opponent on both sides. An empty policy path selects the
centre-directed stroke baseline. Reports include source and model hashes,
physical collision events, decisions, terminal winners, and paddle travel.

Do not use training loss alone as evidence of successful play. Do not count
time-cap episodes as wins. These checks cover a limited serve distribution;
they do not establish strong play against arbitrary opponents.

Run `scripts/competition-evaluate.py` to collect the full fixed-seed set.
Retain the completed test status files as `competition-tests.json`,
`physics-tests.json`, and `rally-tests.json` under `artifacts/competition/`.
Then run:

```sh
.venv/phase1c0/bin/python scripts/competition-verify.py
```

The verifier checks model provenance, current source hashes, physical paddle
and landing events, unused serve seeds, point results, movement, and three
exact point replays. It writes `artifacts/competition/verification.json`.

## Verified result: 2026-09-06

PPO training completed 30 batches of 96 points in about 6.3 minutes on the
laptop. The stroke model was trained separately. No cloud machine was used.

| Check | Result |
| --- | ---: |
| Model and tactical Editor tests | 5/5 passed |
| Physics Play mode tests | 2/2 passed |
| Existing rule and rally export tests | 7/7 passed |
| Competitive near side versus centre opponent | 100/100 points won |
| Competitive far side versus centre opponent | 100/100 points won |
| Self-play legal returns before a miss | 2 in each of 100 points |
| Self-play winners | 50 orange; 50 blue |
| Combined lateral paddle travel per self-play point | 2.064 m |
| Combined lateral travel per centre-baseline point | 0.322 m |
| Separate three-seed replay | Exact event and result match |

All match evaluations used unused serves starting at seed 840000. The centre
baseline used 20 serves with the same smaller paddles and new physics. Each
baseline rally reached the 30-second cap, with 46 legal returns and no point
awarded. The competitive points ended through missed legal returns, not net
faults or invalid serves. The greedy policy selected short left/right targets;
it did not select the centre or deep targets in this evaluation. A separate
test confirmed that the target changes when the opponent changes side.

The centre opponent is weak. These results show competitive placement and
movement, not broad playing strength. The current receiver does not learn a
recovery position between shots. Its limited reach makes self-play points
short. Learned recovery movement and a wider opponent set are the next steps.

The stroke model hash is
`7a53a3066c7cb376a6839758ee943e4f965f4d471a6ff7b8a1283fa9b0a7ef5d`.
The shot-selection model hash is
`9e6ade3596e97669bb887019a1fa3f216ee77cf46acf5340b6ba0c234de02989`.
The runtime hash is
`52bb59ee956da7851fb3c5d7e46b385a4c0d178343eb039dd4629403b9ba6007`.
The verifier also passed for the unchanged historical cooperative runtime.

Evidence is in `artifacts/competition/`: `self-final.json`, `near-final.json`,
`far-final.json`, `centre-final.json`, `repeat-final.json`, the three test
reports, `verification.json`, and the actual Game view `game-view.png`.
