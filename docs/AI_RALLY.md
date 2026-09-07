# AI rally prototype

This page records the earlier cooperative prototype under D-025. D-026 replaces
the default `AIRally.unity` scene with the [competitive match](COMPETITIVE_MATCH.md).
Use `CooperativeRallyV1.unity` to inspect this earlier model and its elastic physics.
The results below do not describe the new competitive model.

This prototype implements the user-requested 3D ping-pong concept. Two agents
use a trained neural policy to return the ball after one bounce. It is separate
from the calibrated-pickleball roadmap. Phase 1B remains open.

## Run the scene

1. Open `Assets/Picklebot/Scenes/CooperativeRallyV1.unity` in Unity.
2. Press Play and select the Game tab.
3. Watch the orange and blue paddles. Both use the assigned neural model.
4. Use Space to pause. Use R to repeat the current serve. The on-screen buttons
   provide the same controls and a slow-motion option.

A missed return, second bounce, volley, wrong-side landing, net contact, or
out-of-court ball ends the point. The winning side gets one point. A new serve
starts after 1.5 seconds. Serve direction alternates. A replay repeats the same
launch seed and model; it is a fresh simulation rather than a recorded animation.

The serve first bounces on the server's half and then the receiver's half.
Each following stroke must land on the opposite half. The rally counter counts
completed legal returns, after their receiving-side bounce. It excludes the serve.
Net-touch serves lose the point in this simplified rule set. A 90-second point
limit prevents an endless simulation.

## Model and physics

The model was trained locally by behavioral cloning. An offline ballistic
teacher supplies position and angle examples. The runtime never calls that
teacher. Each paddle observes six numbers: current ball position and velocity,
expressed in its own coordinate frame. Two 64-unit tanh layers produce four
commands: impact position x/y and paddle-normal slopes x/y. A bounded motor
moves the paddle to the model's position and angle. The far agent uses the same
weights with a rotated observation frame.

The deployed model is `Assets/Picklebot/Rally/Models/rally-policy.json`.
`RallyNeuralPolicy` evaluates these trained dense weights directly on the CPU.
The model includes training-only normalization values. PyTorch checkpoints and
an ONNX export are retained under `artifacts/rally/training/`. ONNX receives
normalized inputs; the scene uses the JSON model, which includes normalization.
An EditMode test compares C# predictions with 32 PyTorch reference cases for both
player frames.

Unity runs the ball and paddle collisions in a separate local physics scene at
240 Hz. The surface is 3 by 1.8 metres; the net is 0.15 metres high. The ball has
a 0.035-metre radius. Paddle faces are 0.4-metre squares. Gravity is 9.81 m/s².
Restitution is 1, friction and air drag are zero. These ideal elastic settings
are deliberate prototype simplifications, not table-tennis measurements. The
ball receives no scripted velocity correction after the serve. All returns
result from the neural-controlled paddles and Unity collision resolution.

## Reproduce training

Use the existing project Python environment:

```sh
.venv/phase1c0/bin/python scripts/rally-train.py --steps 12000 --seed 810001
```

Dependencies are PyTorch 2.1.2, NumPy 1.23.5, and ONNX 1.15.0, already present in
the Phase 1C0 environment. `config/phase1c0/environment.yml` defines that
environment. The training script fixes data generation, network dimensions,
normalization, optimizer, and learning-rate schedule. The manifest records the
training seed, example counts, update count, tuning error, package version,
trainer hash, and exported weight hash. A separate generator seed supplies
tuning examples. Unity validation uses seeds 820000–820999. The existing Phase
1C final-evaluation partition is not used.

If the model or runtime code changes, repeat Unity validation. Training loss is
not evidence of successful play.

## Reproduce Unity verification

Use the Unity CLI with this project open. Compile changed scripts first and
wait for a successful `recompile_status` result.

```sh
unity command recompile
unity command recompile_status
unity command run_tests --mode editor --filter Picklebot.Rally.Tests --filter_type assembly --async_tests true
unity command test_status
```

The test runner can leave an empty scene active. Open `CooperativeRallyV1.unity` again,
then press Play before running the evaluations:

```sh
unity command eval 'return Picklebot.Rally.Editor.RallyEditor.Evaluate(820000, 100, "neural-final");'
unity command eval 'return Picklebot.Rally.Editor.RallyEditor.Status;'
```

Wait for `completed`. Then evaluate the stationary-paddle baseline:

```sh
unity command eval 'return Picklebot.Rally.Editor.RallyEditor.Evaluate(820000, 100, "zero-action-final", true);'
unity command eval 'return Picklebot.Rally.Editor.RallyEditor.Status;'
```

Before the verifier, also retain the completed test status as
`artifacts/rally/validation/rule-and-export-tests.json` and run the three-seed
repeatability check after the baseline finishes:

```sh
unity command eval 'System.IO.File.Copy("Temp/pipeline_test_status.json", "artifacts/rally/validation/rule-and-export-tests.json", true); return "Test result retained";'
unity command eval 'return Picklebot.Rally.Editor.RallyEditor.Evaluate(820000, 3, "repeatability-final");'
unity command eval 'return Picklebot.Rally.Editor.RallyEditor.Status;'
.venv/phase1c0/bin/python scripts/rally-verify.py
```

The evaluator runs the actual Unity physics and the same neural policy used in
the visible scene. It caps each evaluation at 20 legal returns. Reports include
each serve, collision event sequence, contact count, completed returns, point
result, policy hash, and runtime-source hash. The verifier rejects stale models
or runtime evidence and checks the alternating physical paddle/landing events.

The acceptance target is at least ten legal returns on three distinct
validation launches. The full 100-launch report and zero-action comparison
must be retained. These results describe this easy serve distribution, not
arbitrary opponent shots or competitive play.

## Verified result: 2026-09-06

The final evaluation used 100 serves, seeds 820000 through 820099. Both trained
paddles used model SHA-256
`579feb87c5400a4004a0a4ee5ab56fdac302b8efb8f3028b276896442d79cad8`.
The runtime-source hash was
`83478fdf55a3e0045d7859bf2445960f155a3ddd7250c52cbcb81a41f08c82b1`.

| Measure | Neural paddles | Stationary paddles |
| --- | ---: | ---: |
| Legal first return | 100/100 | 0/100 |
| At least 10 consecutive legal returns | 90/100 | 0/100 |
| Reached the evaluation cap of 20 returns | 90/100 | 0/100 |
| Mean completed returns | 18.71 | 0 |

Nine neural episodes ended with a wrong-side landing. One ended with net
contact. The other 90 stopped at the evaluation cap. Seeds 820000, 820001, and
820002 each reached 20 legal returns. This exceeds the initial goal of ten
returns on three distinct validation launches.

Evidence:

- `artifacts/rally/validation/neural-final.json`
- `artifacts/rally/validation/zero-action-final.json`
- `artifacts/rally/validation/rule-and-export-tests.json`: 7/7 passed
- `artifacts/rally/validation/repeatability-final.json`: seeds 820000–820002
  reproduced identical collision events and episode results in a separate run
- `artifacts/rally/game-view-final.png`: actual Game view with controls and a
  visible live rally counter of 29; this is supplementary to the capped benchmark
- `scripts/rally-verify.py`: passed against the current runtime and model hashes

Manual runtime checks through Unity CLI also confirmed pause, replay, scoring,
and automatic serving. Pause kept elapsed time at 16.5290775 seconds and the
return count at 29 across separate reads. Replay reset time and returns to zero
while retaining seed 820000. A controlled out-of-court ball in the visible demo
awarded the point and automatically advanced to seed 820001. This injected
fault was separate from the benchmark physics scene and reports.

## Historical next step

D-026 now adds energy loss, smaller paddles, and point-based reinforcement
learning. This cooperative prototype remains available as the earlier baseline.
