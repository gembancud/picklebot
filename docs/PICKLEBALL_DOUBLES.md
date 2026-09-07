# Pickleball doubles

This is a separate development scene. It does not replace the earlier singles game.

## Start the scene

1. Open `Assets/Picklebot/Scenes/PickleballDoubles.unity` in Unity.
2. Press Play.
3. Select the Game tab.
4. Clear the Pause box if it is selected.

Controls:

- Space: pause or continue.
- R: show the last completed rally. Press R again to leave replay and start a new game.
- N: start a new game.
- Centre shots: use a fixed target for contact inspection.

The display identifies trained control and scripted assistance. A missing team
model does not count as a trained AI match.

Visible play samples the trained shot distribution. This permits varied shots.
The models do not learn during normal playback. `Sample Actions` in the
Inspector can be cleared to use the highest-probability shot instead.

## Training design

The contact model has separate parameters for flat shots, topspin and slice.
Parameter search changes paddle pitch, timing, speed and tangential brush speed.
It does not set the ball's velocity or spin to a target value.

The team model selects shot targets and contact styles. The two teams have
separate policies. Teammates share their team's policy and terminal result.
Interception, body movement and inverse kinematics remain scripted assistance.

Use these seed ranges:

| Use | First seed |
| --- | ---: |
| Contact fitting | 900000 |
| Team training | 910000 |
| Contact validation | 930000 |
| Team validation | 940000 |
| Interactive play | 950000 |

Contact validation uses different serves and targets from contact fitting.
Team reports retain game seeds, rally numbers, serve variation and contact events.
A time limit ends a training sample without a winner. It does not award a point.

## Repeat the local checks

Use Unity CLI with this project selected. Start Play before an Editor training job.
The jobs run in small time slices and report status through their `Status` field.

```text
ContactTraining.Start(36, 8, false, true)
ContactTraining.Start(1, 20, true, false, 930100)
TeamTraining.Start(500, true)
TeamTraining.Start(100, false, "trained")
TeamTraining.Start(100, false, "random")
```

These are C# Editor API calls. `ContactTraining` is in
`Picklebot.Doubles.Editor`. `TeamTraining` is in
`Picklebot.DoublesTraining.Editor`.

The initial harness uses `"random"` as the label for sampling the **trained**
policy distribution. It is not an untrained random-agent baseline.
The `"trained"` label selects the highest-probability action.

Do not edit simulation or trainer source during a job. Source changes invalidate
the saved evidence. `Cancel()` stops either job. Contact fitting with `resume`
uses the saved contact model as its starting point and records that model's hash.

Run the final file checks from the project directory:

```sh
.venv/phase1c0/bin/python scripts/doubles-verify.py
```

## Evidence and limits

Read `docs/DOUBLES_PROGRESS.md` for the current acceptance state.
Reports are in `artifacts/doubles/`.

- Court and equipment geometry use the full-size pickleball profile.
- Ball contact, air drag and spin transfer remain provisional.
- The body is an articulated kinematic model. It does not learn balance or joint torque.
- The net has a visual mesh and a rigid collision approximation.
- The replay shows recorded ball, player, paddle, limb and foot poses.
- The rule code supports standard side-out doubles. It does not simulate human line-call disputes or tournament officials.

Rule reference: [2026 USA Pickleball rulebook](https://usapickleball.org/docs/rules/USAP-Official-Rulebook.pdf).
