# Independent player controls V2

Status (2026-09-08): movement, body/feet, bounded paddle and an opt-in adapter
into the existing doubles physics world are implemented. Independent V2 decision scheduling is integrated; learned policy weights, a
trained full-game play and acceptance remain open. A disclosed physical serve/reset
and complete-game mechanics loop are now implemented and tested under D-035.
The goal remains four independent players sharing learned policy weights.

## Bounded wrist recovery (D-037, 2026-09-08)

The exact step-675 failure was reproduced twice. The paddle had angular velocity
(-11.7105, 2.5425, -0.6324) rad/s immediately before the ready target demanded a
wrist stop. Losing the grip's rotational velocity made the 6 m/s shoulder-relative
hand-speed constraint incompatible with the linear acceleration bound for the
orientations previously considered. It was a restricted candidate search, not
proof that every physical wrist orientation was infeasible.

PlayerPaddleControl now tries ten bounded continuations of the previous wrist
rotation after its existing twenty candidates fail. Every candidate retains the
same 12 m/s speed, 100 m/s2 acceleration, 0.62 m reach, 12 rad/s rotation and 6 m/s
relative hand-speed checks. No position projection or relaxed limit was added.
WristRecoverySteps counts this path. The 80 rad/s2 decrement spaces recovery
candidates; it is not a globally imposed angular-acceleration limit. The failed
state is now an exact regression fixture, including all hard constraints and
position integration. Failed trials expose a diagnostic snapshot without
advancing physics. On successful JSON reports, failure/status is authoritative;
Unity may serialize a null snapshot as a zero-valued object.

All 201 EditMode and 162 PlayMode tests pass. The unchanged fixed-inference V1
checkpoint now completes 6,000 steps without controller failure and a separate
full 11-0 game in 11,484 physics steps. All eleven rallies contain only the serve
and one return: five out faults and six wrong-side faults. This resolves a
controller failure; it does not establish good rallies, balanced participation,
competitive 2v2, model acceptance, or trained V2 behavior. Both probes use only
interactive seed 1300000. Full-game evidence: intent-probe-05-full-game.json.

The matching historical contact residual file is still present at
Assets/Picklebot/Doubles/Models/contact.json. Its normalized SHA256 is
6698221451858f044e26a28c58a39447d391c4f1aba58a68f11370926df9cba4, matching the actor.
NEXT: integrate those residuals explicitly, diagnose actual return trajectories,
and finish trainer/protocol and original-scene presentation integration. The
current bridge still uses neutral residuals, disclosed serve/reset assistance,
compatibility sprint and automatic crouch. No new model was trained or promoted.

D-036 source is preserved in artifacts/player-controls-v2/d036-source.zip and
verified against its manifest. Current checks: wrist-check / wrist-check-unity;
prior stage checks remain historical. D-037 source and tests are recorded in
config/player-controls-v2-wrist.json and player-controls-v2-wrist-tests.json.

## Historical checkpoint intent bridge (D-036, 2026-09-08)

The working training assumption is movement/posture plus shot intent, pending
user steering. Four LegacyActorIntentPolicyV2 instances share the unchanged V1
model weights while retaining independent inference traces and RNG streams.
Only the frozen 54-value observation prefix enters that network. Current heading
rotates its movement request into body coordinates. This is explicitly a V1
compatibility bridge, not a model trained on the 96-value V2 observation.

PlayerShotIntentV2 is captured with the movement action and applied after the
same six-tick latency. Each seat owns a separate PlayerIntentSwingV2 contact plan.
The swing planner requests paddle motion and never chooses locomotion or the
hitter. The legacy bridge explicitly requests sprinting and permits automatic
crouch for a planned stroke. New policies can retain their own posture. Physical
speed, acceleration, reach, energy, contacts and support constraints still apply.
Contact planning currently uses neutral residuals and the historical reach
prediction assumptions; the checkpoint's contact-model integration is unfinished.

All 200 EditMode and 162 PlayMode tests pass. Fixed and sampled checkpoint
inference match the original actor over 64 observations each, including random
stream consumption and movement coordinate transforms. Timing tests ensure
mutable policy state cannot change an already queued shot. These are contract
and regression tests, not proof of playable transferred behavior.

The first actual four-checkpoint diagnostic failed at physics step 675: player 2
had no feasible paddle transition. The entire trial was rejected. The preserved
report is artifacts/player-controls-v2/intent-probe-01.json, using only interactive
seed 1300000 and exact actor SHA 61c59e110797290c46b30b91a9fa2d0d3665e92a40f3c998bf2e24ed168edc06.
No game score had been awarded. Do not present this as a playable V2 model.

NEXT: capture the failing motor state, add a reproducible coupled shoulder/paddle
fixture, and improve feasible control execution without increasing physical
limits. Then finish contact-model and trainer/protocol integration and expose
the V2 mode through the original presentation. Training, agent-strength gates,
final evaluation and promotion remain incomplete. Original scene assets remain
unchanged; IndependentPlayers is the selected scene.

Current checks: intent-check / intent-check-unity. D-035 game-check is now a
strict historical snapshot. Current source and test records are
config/player-controls-v2-intent.json and player-controls-v2-intent-tests.json.
The failed first PlayMode run (one CLI timeout log) and its successful clean rerun
are both retained. All 82 historical artifacts and prior records remain intact.

## Serving and game mechanics (D-035)

PlayerGameV2 runs the existing rule engine through serving, live play, dead-ball
settlement, score resolution, service changes, rally reset and game completion.
All four decision streams continue on the physics clock. The serving phase uses
an explicitly disclosed physical drop-serve skill for the server and ready holds
for other players. Live play uses each player's policy action. Dead-ball reset
holds/brakes the players, then clears a pending kitchen-momentum case through
normal movement after an initial settlement period. It cannot reset or award
points while DoublesRules.ResolveRally still rejects unresolved momentum.

The serve reuses StrokeController's explicit interception/flight planner. It
moves the actual body and paddle; it does not inject ball velocity or skip
collisions. Requests use a bounded forward sprint step, crouch, face orientation
and stroke feed. The recorded request settings are in the D-035 source/manifest:
speed request scale 1.25, pitch bias -4 degrees, drive lead 0.16 s, initial root
target |z|=7.30 m and forward target |z|=6.50 m. These are controller requests;
actual foot positions still determine service legality. Serve assistance is not
learned player skill and must be masked/disclosed in training and evaluation.

Applied-action observations now expose the actual assisted/actor command from
the prior physics step. They do not mislabel ignored actor outputs as executed
controls. Rally summaries retain server identity, score, faults and physical
contacts. Completed games do not continue scoring. Policy or physical-step
failures mark the game terminal; retrying cannot silently consume more time.

Physical probes exposed premature knee/forearm contacts, insufficient service
flight and a paddle transition with an infeasible preferred braking reserve.
Failed reports remain in artifacts/player-controls-v2/serve-probe-*.json.
The experimental elbow bend now follows the back of the actual paddle face,
using the same fixed arm lengths and colliders. The previous D-033 adapter source
is preserved as PlayerBodyExternal-d033.cs.txt and checked against its old digest.
The legacy body/controller path and scene assets remain unchanged.

Paddle recovery may drop the preferred outward braking-reserve target and brake
radially when that preference is temporarily infeasible. Every accepted recovery
step still satisfies 12 m/s speed, 100 m/s2 acceleration, 0.62 m reach, bounded
rotation and 6 m/s shoulder-relative hand speed. Recovery use is counted per
paddle. A mutually infeasible hard-constraint step still fails the game.

Current targeted evidence: eight PlayMode integration tests pass, including a
physical serve that scores and resets, a complete mechanics game to at least 11
with a two-point lead, no further scoring after completion, an unresolved late
volley fault that cannot be reset away, and terminal policy failure. The policies
in the mechanics fixture simply hold ready; this is not agent-strength evidence.
The full regression and diagnostic report are recorded separately below.

Use `pixi run --locked game-check` / `game-check-unity` for the current exact
source and archive/model verification. Earlier decision/integration checks are
historical snapshots and correctly reject subsequent changes. D-035 records the
current scope while preserving earlier manifests and 82 historical artifacts.

Training-design clarification is pending: preserve learned shot intent with a
bounded independent swing controller (closer to transferred policies), or train
direct paddle trajectories. The direct 15-value interface is a physical command
boundary either way; its existence does not decide the learned action space.

## Independent decisions (D-034)

PlayerActionV2 is an explicit 15-value direct-control contract: body-local movement
(2), attack-relative desired yaw (1), crouch/jump/sprint (3), shoulder-relative
body-local hand target (3), wrist angles (3), and body-local paddle feed (3).
Values are finite and bounded; actions own their backing values. Movement is
bounded as one vector. The default action holds a ready hand pose and faces the
attacking end. This does not reinterpret the V1 shot categories as hand commands.

PlayerObservationV2 has 96 values: the identifiable 54-value V1 game prefix,
10 control/proprioception values, 3 shoulder-relative values, 12 foot values,
2 own rule-memory flags, and the player's 15 currently active control values.
Foot values include relative position, heading sin/cos and actual support. The
read-only EstablishedOutside / VolleyMomentumPending getters expose existing
rule state without changing the rules. Opponent actions, policy state, weights,
random streams and future contact plans are not observation inputs.

PlayerDecisionLoopV2 captures owned observations for all four players before
calling any policy. Decisions run every 12 physics ticks and apply after six
ticks (20 Hz / 25 ms at 240 Hz). Each player has its own policy instance and
identity-seeded random stream; teammate identity swaps carry that private stream.
Immutable learned parameters may be shared. Sharing one mutable policy instance
between players is rejected. Reset clears pending/active commands and policy
state; random streams continue rather than replaying their initial draws.

PlayerControlMatch.AttachPolicies / StepAgents now drive the physical integration
through this interface. Policy inference currently requires a caller-provided
IPlayerPolicyV2 implementation. No trained V2 neural network or checkpoint
conversion is claimed. Invalid policy/capture/physics steps fail explicitly;
automatic recovery/retry is not implemented and must not count as elapsed play.

Validation: all 196 EditMode tests pass, including eight new contract tests;
all four targeted physics-adapter tests pass. The new physics test runs 120 ticks,
records 40 decisions, checks each policy is called 10 times, and confirms all four
real bodies move using separate policy instances referencing common probe weights.
These untrained probe weights prove the interface, not playing skill. Previous
full PlayMode 157/157 and Python 300/300 results belong to D-033; they are retained
as historical evidence rather than claimed as new full-suite runs for D-034.

Current verification is `pixi run --locked decisions-check` (or
`decisions-check-unity` with the CLI on PATH). The D-034 record preserves D-033
and D-031 records, existing body adapter bytes and 82 model/evidence files. It
explicitly adds the two read-only getters in DoublesRules.cs to recorded scope.
Older source-check and controls-check remain strict historical snapshot checks.
Saved scene assets remain unchanged; IndependentPlayers remains the open scene.

## Current implementation

PlayerControlWorld owns four private motors, body poses and paddles. All four
commands are evaluated from pre-step state and committed only after the complete
contact/body/paddle solve succeeds. No central hitter selection or ball-driven
movement is present. Command rejection cannot advance only some players.

Movement is body-local with heading, crouch, jump and sprint requests. The motor
uses a vector acceleration budget, directional speed limits, bounded yaw, fatigue
and crouch speed scaling. Each player has private energy and jump-edge state.
Flight has no steering or energy refill. Landing recovery prevents instant
re-jumping. The separate 10-value proprioception contract has not been silently
appended to the V1 54-input actor.

Swept equal-mass, frictionless, inelastic horizontal disc contacts resolve player
motion together. Contact delta-velocity is recorded separately from motor
acceleration. Radius is 0.28 m; the small prototype jump cannot clear another
torso. Root bounds x +/-4.2 m and signed z 0.38..8.1 m are a safety enclosure,
not physical pickleball boundary walls. Initial overlaps or solver convergence
failure are errors, not hidden position projections.

The analytic gait keeps stance feet planted while one foot swings. Each leg has
two 0.46 m segments; impossible extension fails rather than stretching geometry.
Turning/crouching changes hips and shoulder position. Flight carries the existing
feet with root translation and bounds relative repositioning to 6 m/s. Landing
arrests sole height while retaining horizontal placement. This is an analytic
gait, not a force/balance or muscle simulation.

Oriented 0.13 x 0.28 m supported shoe rectangles are intersected with the kitchen.
Swinging or airborne feet cannot establish ground support. Both feet must be
supported outside to restore outside status. Momentum recovery conservatively
requires stationary horizontal motion, outside support, grounding and no landing
recovery pending. Existing DoublesRules retains kitchen and volley-momentum
memory, including a late kitchen landing after an apparent rally end.

PlayerPaddleControl accepts body-local hand target, wrist angles and feed velocity.
The resulting single velocity is constrained by 12 m/s speed, 100 m/s2
acceleration, 0.62 m arm reach and a braking reserve. Rotation is bounded to
12 rad/s, with wrist angle limits. Shoulder-relative hand speed is bounded to
6 m/s. The controller can slow a requested wrist rotation to remain feasible;
it does not project the final hand position. If constraints are mutually
infeasible, the entire trial is rejected explicitly. Recovery from arbitrary
infeasible agent requests still needs a recorded integration policy; rejected
trials cannot count as successful simulated time.

## Connection to existing game physics

PlayerControlMatch (PlayerControlsIntegration assembly) uses the existing
DoublesWorld court, ball, aerodynamic model, collision reporting, paddle spin
transfer, rule engine and articulated body meshes. Callers currently supply
four movement commands and four paddle commands directly. It has no learned
policy, hidden serve planner or autonomous full-game loop yet.

PlayerBody.ApplyExternalFrame is an explicit opt-in API. It applies the already
integrated root, joints, support state and physical kinematic paddle target. It
does not run the legacy movement motor. Attempting both motors on one body fails.
Rally reset clears the external mode and restores the legacy torso dimensions.
The existing IndependentPlayers and PickleballDoubles scene assets are unchanged,
and their default controllers continue on the legacy path.

The manual PlayerControlLab remains a diagnostic fixture, not the game scene.
Its lower-body visuals are available with 1-4 selection, WASD movement, Q/E turn,
Shift sprint, C crouch, Space jump and R reset. Paddle state is now integrated
internally but that lab does not yet display or offer manual paddle commands.
IndependentPlayers was restored as the open scene after the user questioned
the visual change. Do not switch the visible scene without explaining it.

## Parameters and calibration

All human parameters remain provisional engineering choices: forward/lateral/
backward speeds 3.8/3.0/2.3 m/s; acceleration and braking 14 m/s2; turning
360 degrees/s; jump height 0.25 m; gravity 9.81 m/s2; landing recovery 0.18 s;
jump energy cost 0.12; sprint drain 0.12/s; stationary recovery 0.08/s.
The ball model is provisional outdoor 40-hole/acrylic physics, not newly measured
physical calibration. The trial world currently allocates per step and needs
throughput measurement before training-scale optimization.

## Evidence and source identity

D-033 records the opt-in integration. The exact pre-adapter working source is
preserved at artifacts/player-controls-v2/pre-body-integration.zip, with digest
in config/player-controls-v2-pre-integration.json. Original D-030/D-031 records,
baseline manifest and 82 model/evidence files are unchanged.

The current shared source identity changes because PlayerBody.cs and the new
PlayerBodyExternal.cs are part of the contact/player/team source scopes. V2
additionally hashes all non-test control/integration C# sources, including
parameter defaults. Do not relabel old model sourceHash values. Transfer and
historical evaluation must keep original training identity separate from current
runtime identity. No old checkpoint is accepted as V2 by this change.

Run `pixi run --locked controls-check`, or `controls-check-unity` with Unity CLI
on PATH, to verify exact integration scope, archived baseline bytes, preserved
artifacts and source hashes. D-031 `source-check` remains a strict historical
snapshot verifier and intentionally rejects the subsequent body-adapter changes.
Its implementation/evidence were not rewritten to mask those changes.

Current checks: 188 EditMode tests (including 30 control tests) and 300 Python
tests pass. The three targeted PlayMode adapter tests pass, including 360 combined
physics steps, real paddle-ball contact/rebound, single root integration and
legacy reset. All 157 non-explicit PlayMode tests also pass (artifacts/controls-v2-full-playmode.json). Narrow
motor/contact checks are not full-game or agent-strength evidence.

Earlier preserved evidence:
- Kernel: 9 tests, config/player-controls-v2-kernel.json.
- Contacts: 176 total EditMode tests, 18 controls; config/player-controls-v2-contacts.json.
- Body/feet: 184 total EditMode tests, 26 controls; config/player-controls-v2-body.json.
- V1 throughput: 6000 steps/mode, roughly 2764 baseline, 6234 independent hold,
  2526 independent attempt steps/s. These do not measure the new V2 adapter.
- V1 CPU update proxy: 200 synthetic batches of 2048 in 0.482 s; not PPO strength.
- V1 physical audit records known legacy acceleration spikes separately from
  bounded independent-controller probes; do not reinterpret them as V2 passes.

## Required next work

1. The independent 96-input/15-action interface is integrated. Implement and
   validate actual policy inference/initialization against this explicit contract,
   preserving simultaneous observations and private delayed decisions.
2. Serve/reset and full-game mechanics are implemented. Add playable manual/
   agent control to the existing presentation with clear selection/diagnostics,
   and verify beyond the stationary-opponent mechanics fixture.
3. Establish handling and measurements for infeasible requests without hiding
   constraint violations or slowing simulated time silently. Probe collisions,
   rapid posture changes, contacts, service and long sequences.
4. Define checkpoint transfer or imitation initialization with lineage. Version
   the trainer, full V2 source/profile/protocol identity and acceptance contract.
   Preserve the original V1 final protocol and its evidence.
5. Measure V2 physical behavior and throughput, reserve seed blocks against the
   retained source-machine history, then conduct bounded development and staged
   training. Final-evaluation seeds stay unused during tuning.
6. Make final verification migration-aware via exact evidence, not ignored files.
   Prove full games, strength, per-seat participation, partner/opponent robustness,
   physical limits and the playable scene before accepting a model.

No new RL training, model promotion or final evaluation has been performed here.


D-035 final mechanics evidence: 196 EditMode tests and 162 non-explicit PlayMode
tests pass, including eight targeted V2 integration/game tests. The final bounded
diagnostic completed 11-0 in 10,805 physics steps with 11 rallies, 2,089 assisted
serve steps and 2,651 assisted reset steps. All scoring followed physical serves
and unreturned balls against untrained hold policies. This does not establish
non-serve participation, learned returns, opponent strength or full acceptance.
Evidence: artifacts/player-controls-v2/game-probe-11.json and
config/player-controls-v2-game-tests.json. The existing IndependentPlayers scene
is open and Play is stopped. No model promotion or final-evaluation seeds used.
