# Doubles development goal

Status: accepted base prototype, 2026-09-06. All five stages passed the checks
below. The earlier singles demo is unchanged.

## Acceptance stages

1. Rules: side-out doubles scoring, service order, serve validation, two-bounce rule, kitchen faults, body faults, and a fault event log.
2. Bodies: four articulated players with a fixed hand grip, arm and leg inverse kinematics, and foot support state.
3. Contact: bounded movement, reach and paddle rotation. Flat, topspin and slice shots must result from paddle contact.
4. Learning: save trained contact and shot-choice models. Record the source, parameters and seeds. Test with separate seeds and fixed opponents.
5. Doubles: both teammates must take part. Test receiver selection, court coverage, separation, full games and visible playback.

Each stage needs code, tests and evidence. Do not mark a stage complete from a screenshot alone.

## Limits

- Use the outdoor 40-hole ball and acrylic court profile. Its contact parameters remain provisional.
- Start with procedural articulated bodies. These are kinematic bodies, not learned balance or muscle control.
- Keep scripted assistance explicit in the display and model report.
- Preserve the museum, inspection, rally and singles scenes and their saved models.
- Use local compute. Paid compute and purchased assets need user approval.
- Do not use proposed rule changes as accepted rules.

Rule source: [USA Pickleball official rules](https://usapickleball.org/rules/).

## Current evidence

The development scene exists. Four procedural bodies, physical drop serves,
body contacts, service order and score updates are implemented.

All 50 tests passed: 43 rule, policy and body-math tests, plus seven physics
integration tests. The latter include three-axis paddle rotation and fixed grip.

The first fitted contact model passed 36/36 landing checks. Its flat and topspin
labels failed spin checks. Reports are retained with the `v1` suffix.

The second model passed 20/20 flat and 20/20 slice validation cases for both
landing and spin. Topspin passed 13/20. Reports are retained with the `v2` suffix.
These reports predate the level apron correction. They are development evidence,
not acceptance evidence for the current scene.

The expanded search completed 864 contact trials. After the teammate recovery
and shoe changes, the saved parameters passed 24 compatibility checks.
They then passed 60 new validation cases: 20/20 for each style, with legal
landings and correct spin classes. The main search report has the `v3` suffix.
The current model records its warm-start model hash in the compatibility report.

The team model completed 500 training rallies and 17 complete games.

Fixed-weight validation passed 100 rallies and completed five games. Six
rallies reached the time limit without awarding a point. The highest-probability
action mode strongly preferred one shot for each team. It is not evidence of
advanced tactical play.

Sampled-policy validation passed 120 rallies and completed four games. Four
rallies reached the time limit. Orange won 50 rallies and Blue won 66. All nine
shot actions and all three contact styles were selected. The mean was 6.025
paddle hits per rally, including the serve. The four players recorded 118,
247, 117 and 262 paddle contact events. These event counts can include contacts
with more than one paddle collider; they are not distinct rally-hit counts.

The scene uses sampled play by default. It loads the saved models, varies the
physical serve target within the tested range, and does not learn during normal
playback. The Game view was checked with actual point scores and all four bodies.

Fault replay preserved 64 body transforms exactly. Physics time, contact count
and score did not change during replay. The saved proof used a wrong-side fault.

`scripts/doubles-verify.py` passed with current source and model hashes.
Earlier rally, competition and inspection verification scripts also passed.

## Stage evidence

| Stage | Accepted evidence |
| --- | --- |
| Rules | Service, scoring, two-bounce, kitchen and fault tests; complete scored games; recorded fault replay |
| Bodies | Four articulated players; fixed-grip and reach tests; recorded limb and foot poses |
| Contact | Three-axis rotation test; 60/60 held-out landing-and-spin cases |
| Learning | Saved contact corrections and two team policies; training history and source/model hashes |
| Doubles | 220 fixed-weight validation rallies; nine complete games; all four players and all shot styles used |

## Evidence files

- `artifacts/doubles/rules-tests.json` and `physics-tests.json`
- `artifacts/doubles/contact-training-v3.json`, `contact-training.json` and `contact-validation.json`
- `artifacts/doubles/teams-training.json`, `teams-trained.json` and `teams-random.json`
- `artifacts/doubles/replay-verification.json` and `trained-2v2.png`
- `Assets/Picklebot/Doubles/Models/contact.json` and `teams.json`

## Acceptance checks

Run `scripts/doubles-verify.py` after all reports exist. It must fail while
evidence is missing or stale. Do not lower a threshold to pass a failed model.

- At least 20 held-out cases per contact style; at least 90% must have a legal landing and the correct spin class.
- Passing rule and physics integration tests.
- At least 500 team-training rallies and 100 held-out doubles rallies.
- At least three complete validation games, with no point awarded on truncation.
- At least ten paddle contact events for each of the four players.
- Verified teammate separation, arm reach and paddle speed bounds.
- A visible match and working fault replay.

These checks establish a base prototype. They do not establish expert playing
strength, calibrated human movement, or certified ball behaviour.
