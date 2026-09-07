# Full-size AI match

Status: provisional training experiment. This does not close the measured
physics calibration gate.

Open `Assets/Picklebot/Scenes/PickleballMatch.unity`, press Play, then click
the Game tab. Orange and blue use separate learned shot-selection policies.
The scene repeats points and displays the score. Space pauses play. R repeats
the current serve. The slow-motion button selects quarter speed.

## What is learned

Each side has an independent softmax policy with 30 trainable weights. Inputs
include the ball position and both player positions, expressed in the player's
coordinate frame. The action chooses one of five shot targets. Terminal
REINFORCE updates increase the probability of actions that win points. A win
gives +1 and a loss gives -1. The discount between a player's shots is 0.97.
A 20-second time cap gives no reward and awards no point. There is no reward
for a long rally.

Contact is assisted by `ScriptedStrokeMotor`. It predicts an interception,
chooses a paddle face orientation and swing speed, and sends bounded commands
to the same six-axis paddle motor as the inspection scene. It never changes
the ball position or velocity. The controller is explicitly labelled as
scripted in the scene. This is not learned end-to-end paddle control.

The court, ball, contact models, and motor limits are unchanged from
[PICKLEBALL_INSPECTION.md](PICKLEBALL_INSPECTION.md). The match reuses that
world through simultaneous inputs for both paddles. Serves are scripted ball
launches. Basic rally legality and the ground-disc kitchen proxy apply.
The displayed score is a point counter, not full official service scoring.

## Train locally

Use Unity CLI with the editor in Play Mode:

```sh
unity command eval 'return Picklebot.Match.Editor.MatchEditor.Start(500,true,860000,"training");' --format json
unity command eval 'return Picklebot.Match.Editor.MatchEditor.Status;' --format json
```

The bounded job trains from fresh policies. It does not resume or replace the
older table-scale models. During training, the visible match receives new
policy snapshots every 25 training points. Its displayed points do not update
the training policies unless the separate visible-learning option is enabled.

On completion, the job saves `Assets/Picklebot/Match/Models/agents.json` and
`artifacts/match/training.json`. The model records its configuration and source
hashes. Stopping Play stops the job. An incomplete job does not publish a model.

After training, use the same seeds for trained, centre-target, and stationary
checks. Do not update policies on validation points:

```sh
unity command eval 'return Picklebot.Match.Editor.MatchEditor.Start(100,false,870000,"validation");' --format json
unity command eval 'return Picklebot.Match.Editor.MatchEditor.Start(100,false,870000,"centre",false,true);' --format json
unity command eval 'return Picklebot.Match.Editor.MatchEditor.Start(100,false,870000,"stationary",true);' --format json
```

Wait for each job to complete before starting the next. Training seeds use
[860000,870000). Validation seeds use [870000,880000). Reports retain physical
contacts, shot choices, terminal reasons, movement, and model/source identity.
The learning-rate setting is 0.01. This small policy is a starting experiment,
not a claim of strong competitive play.

## Visible learning

The delivered scene has **Learn during visible play** enabled. It updates the two policies after each
displayed point. Exploration is then enabled. This mode is slower than the
bounded training job. It changes policies in memory only. Use Unity's
**Picklebot > Match > Save visible learning** menu to save a timestamped copy
under `artifacts/match`. It does not overwrite the verified model asset.
Live-learning copies are new experiments. They are not covered by the saved
checkpoint's validation result. Do not use already-played training points to
claim validation of a live-learning copy. The current interactive session
starts at seed 880000, outside the retained training and validation sets.

Next: validate the physical model with measured data, then train the paddle
contact actions. The scripted contact controller must remain labelled until
a learned replacement passes separate tests.

## Initial checkpoint

The first bounded run used 500 training points, starting at seed 860000.
Each policy received 490 terminal updates. Ten points reached the time cap.
The training run averaged 3.372 physical paddle contacts per point. This is
training evidence, not validation or proof of a strong strategy.

The retained validation checks use 30 serves starting at seed 870000 for each
mode. Run `python3 scripts/match-verify.py` to check source and model identity,
training seeds, test results, physical contacts, and validation outcomes.
Run `python3 scripts/inspection-verify.py` to check the unchanged physical
parameters and the inspection regression evidence.

The initial greedy-policy validation had two or more paddle contacts in
26 of 30 points. Sixteen points reached the 20-second cap. This checkpoint
therefore fails the initial competition gate: at least half of validation
points must award a point. The verification script reports this failure.
Do not claim that the initial checkpoint is a strong competitive policy.
Visible learning samples from the policies and explores other shots. It is
not the same as the frozen, highest-probability action check.
The greedy policies selected one cross-court action in all 336 recorded
decisions. This limited shot variety is another task for the next training
stage. The centre-directed baseline reached the time cap on all 30 serves.
Stationary paddles made no paddle contacts on the same 30 serves.
