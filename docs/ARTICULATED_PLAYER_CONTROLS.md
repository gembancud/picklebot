# Articulated player controls

Current direction: user requested natural grip and swing biomechanics, replacing
the paddle-target/push-first controller as the basis for agent development.
The independent-player/shared-policy objective and acceptance criteria remain.

PlayerArmKinematicsV3 implements a forward chain: three shoulder rotations, elbow
flexion, forearm rotation, and two wrist rotations. Fixed segment lengths produce
the hand position; a fixed hand-to-paddle grip transform produces paddle pose.
Contact-point velocity is derived from joint rates plus body motion. No contact
planner chooses the elbow after selecting a paddle position in this module.

The continental prototype is a configurable coordinate convention, not a claim
of calibrated human grip anatomy. The ready posture and joint limits need visual
review and reference-based calibration. This is a kinematic foundation, not yet
a joint motor, torque/muscle simulation, ball-contact integration, or trained agent.

Next: bounded joint motion, a visible grip/forehand/backhand/volley preview using
the existing presentation, actual elbow/hand collider integration, swing phases,
and explicit agent observations/actions for that controller. Preserve the V1
checkpoint as historical initialization rather than silently reinterpreting it.

V2 status at handoff: serve tuning is paused. Current editor tests passed 205,
but targeted PlayMode tests passed only 7/9: legal serve/scoring and complete-game
fixtures still fail after recent controller/collision changes. Previous D-037
201/162 results are historical, not evidence for this working tree. Calibration
loading, crouch acceleration, and face-event ordering are unfinished D-038 work;
the draft record_calibrated_controls.py has not yet been executed. No current
model is accepted. Do not describe the project as a working V2 2v2 demonstration.
All original scene assets remain unchanged. Source before this new module is
archived in artifacts/player-controls-v2/pre-articulated-controls.zip.

Torso foundation added: PlayerTorsoKinematicsV3 composes pelvis motion, axial
turn, forward/back lean and lateral lean before evaluating the articulated arm.
The shoulder is offset from the pelvis by the rotated (.19, .56, 0) reference;
this is a rigid trunk prototype, not a spine or support/balance simulation.
The agent-facing intention interface remains to be implemented; individual
joint angles are currently internal kinematic inputs, not a finalized action space.
Paddle point velocity includes pelvis translation/rotation, torso joint rates,
and arm joint rates without injecting ball speed. Seven new arm/torso tests
verify attachment, fixed segment lengths, reach changes and finite-difference
velocity agreement. Unity editor suite: 212/212 passed, recorded in
artifacts/controls-v3-torso-editmode.json. This does not resolve the existing
V2 PlayMode failures or constitute a playable V3 controller.
Next integration must supply actual articulated elbows to body colliders and
bound joint motion, then provide a visible stroke preview for grip/pose review.

Bounded joint motion added: PlayerJointMotorV3 integrates at 240 Hz with explicit
angle, angular speed and angular acceleration bounds and conservative braking
reserve near range limits. PlayerUpperBodyMotorV3 applies this to three torso
and seven arm joints; its rates are exposed in radians/second for the existing
kinematic velocity calculation. The joint targets remain internal controller
inputs, not ten newly exposed policy actions. Limits are provisional and must
be evaluated with visible strokes and contact tests before training.
Unity editor suite passed 215/215, retained in
artifacts/controls-v3-joint-motor-editmode.json. New evidence includes 30,000
reversal steps, settling at a limit, gradual upper-body motion, fixed grip,
and rejecting invalid requests before advancing joints. These tests establish
motor behavior, not natural stroke quality, global paddle speed limits,
whole-body balance, or accepted gameplay. The motor is not connected to the
V2 physical match yet; its earlier serve/full-game failures remain outstanding.

Physical adapter integration added: PlayerBodyFrame has an explicit articulated
upper-body mode with actual right elbow and torso orientation. It validates
both arm segment lengths before applying state. The old IK path remains the
default for existing V2 matches. PlayerArticulatedFrameV3 composes locomotion
support/legs with torso/arm pose and their derived contact velocities. Torso
collision orientation follows lean and resets upright when returning to the
legacy body. The integration test drives 300 physical steps and checks arm
segment transforms, grip, velocity composition, invalid-frame rejection, and
reset. Targeted PlayMode result: 8/10; the new test passes and the existing
serve/full-game tests still fail. Evidence:
artifacts/controls-v3-articulated-integration-playmode.json.
This is an adapter, not a V3 match or policy connection. Joint-driven strokes
still need visible validation, whole-paddle speed/acceleration enforcement,
support/balance constraints, observations/actions and actual rally integration.

Visible pose review: Editor.PlayerStrokePreviewV3.Render exports four actual
Unity renders and all 351 bounded-motor steps through ready, preparation,
forward swing and follow-through. It requires PlayMode because DoublesWorld
uses a local physics scene, cleans up its camera/light/render resources, and
leaves authored scene assets unchanged. Output from this review is in the
Codex task outputs/stroke-preview-v3-02 directory (poses.json and four PNGs).
Peak calculated face speed was 7.25224 m/s. No ball-strike test is implied.
The spherical hand geometry cannot validate finger placement/continental grip;
this convention remains provisional. Preview poses are diagnostic targets, not
policy actions or accepted stroke calibration. Original V2 gameplay remains
unchanged by this helper and its existing two integration failures persist.

User grip correction: old prototype aligned paddle longitudinal axis with the
neutral forearm, producing the claw-like orientation the user identified.
The grip now places the handle across the closed hand, perpendicular to the
neutral forearm. Only the named grip factory can construct the transform;
forearm rotation and bounded wrist flexion/deviation control its world pose.
The bevel remains provisional rather than a calibrated continental grip.
Tests explicitly reject reverse elbow motion and out-of-range forearm/wrist
angles, and verify the neutral handle axis and exact attachment. Current
editor tests: 217/217; physical integration: 8/10, same two V2 gameplay failures.
Evidence: artifacts/controls-v3-closed-grip-editmode.json and
artifacts/controls-v3-closed-grip-playmode.json.
Updated actual renders: Codex outputs/stroke-preview-v3-03. Forward-swing
face normal is (0.216599,0.348287,0.912020), facing court +Z with an open upward
tilt (about 24 degrees from forward). This addresses the user's pose-3 concern
without a hidden ball-velocity correction. Moving articulated ball-contact
verification is still pending; it was paused for this grip correction.

User rejected the latest grip/preparation preview as still unnatural. See STROKE_REFERENCE_REVIEW.md for visually inspected coaching references and the corrective workflow. The 90-degree handle convention is not validated anatomy. Further pose tuning is paused until hand/grip axes and reference phases are explicit. The newly added moving-contact test has not yet run.

Hand-frame audit found the previous corrected-grip transform still directed
its handle along the declared palm normal (+Z). The latest transform places
it along the across-palm axis (+X), tangent to the palm plane. Hand rotation,
palm normal, finger direction and across-palm direction are now explicit in
PlayerArmPoseV3. This is a coordinate correction; the bevel and neutral grip
angle remain provisional pending anatomical/visual reference validation.
The first editor run retained one obsolete test failure: wrist flexion was
expected to translate the center face point. With the corrected handle axis,
that joint rotates the face about the shaft; points on the axis do not move.
The corrected test checks normal rotation, stationary axial point, and
nonzero off-axis velocity. Failed evidence is preserved in
artifacts/controls-v3-palm-axis-editmode-01.json; follow-up results are in
artifacts/controls-v3-palm-axis-editmode-02.json. Previous rendered previews
are stale relative to this correction. Moving-contact and PlayMode tests
have not yet been rerun with this transform. Authored scenes are unchanged.

Moving articulated contact is now verified for both advancing and retreating
joint-driven paddle motion using actual PhysX RoundedHittingFace callbacks.
The initial assertion incorrectly required a world-space reversal even when
the paddle retreated. Diagnostics showed incoming (2.87,-2.56,-1.40), outgoing
(0.33,-0.31,0.10), paddle velocity (1.29,-0.62,-0.43), and contact normal
(-.70,.59,.41): the ball separates relative to the retreating paddle. The test
now checks incoming approach and outgoing separation in the moving-surface
frame, and additionally requires outward world-space rebound for an advancing
stroke. Both motions must be nonzero at actual contact. No physics parameters
or ball response code were changed to pass this test.
Final targeted PlayMode: 9/11 passed, with only the two previously recorded V2
serve/full-game failures. Evidence: controls-v3-palm-contact-playmode-03.json
under artifacts; initial failures retained in the unsuffixed and -02 reports.
This proves collision integration for those two constructed contacts, not
natural stroke biomechanics, shot accuracy, legal serves, or accepted 2v2 play.
Reference-linked grip/pose visual review remains the next controller task.

Schematic hand preview added in Editor.PlayerHandPreviewV3 (diagnostic only,
all primitive colliders removed). Actual renders in Codex task outputs/
grip-review-v3-04 show palm, curled fingers and a blue thumb marker. The close-up
exposes an unresolved structural issue: PlayerArmPoseV3.hand is simultaneously
the forearm endpoint/wrist pivot and grip center. The forearm terminates inside
the grasp. Distinct wrist and grip points are needed before anatomical grip
validation. Account explicitly for hand length and existing total reach bounds;
do not silently stretch the arm or reinterpret historical physical acceptance.
Current grip orientation and old four target poses remain unvalidated.
Preview compiled and rendered; no runtime collision code changed this turn.

Wrist/grip separation implemented. V3 now has .32 m upper arm, .25 m forearm
and .06 m wrist-to-grip offset. This explicitly splits the previous .31 m
elbow-to-grip budget; it is a provisional reduced-body profile, not a measured
human forearm. Historical V1/V2 lengths and checkpoints remain unchanged.
The 22-degree minimum elbow flexion keeps shoulder-to-wrist reach plus the
hand offset below .62 m for every wrist orientation. Existing sampled reach
and finite-difference velocity tests pass. Both wrist axes now pivot at wrist;
grip translates with the hand. PlayerBodyFrame.rightWrist drives the physical
forearm endpoint and validates .25/.06 segment distances in articulated mode.
Snapshot: artifacts/player-controls-v2/pre-wrist-grip-separation.zip.
Editor: 218/218, artifacts/controls-v3-wrist-grip-editmode.json.
PlayMode: 9/11, artifacts/controls-v3-wrist-grip-playmode.json; advancing and
retreating contacts pass, same two preexisting V2 gameplay failures remain.
Actual close-up inspected in Codex outputs/grip-review-v3-05. Forearm no longer
terminates at grip center. Schematic hand shape/neutral angles are not accepted
biomechanics; reference-linked preparation and contact poses remain pending.

Reference-phase review expanded from four stale targets to ready, unit turn,
loading, forward swing, contact pose, extension, finish and recovery. These are
held diagnostic poses and provisional fits, not a motion-capture reconstruction
or validated continuous stroke. The current ready tip already points upward;
no forearm zero-offset change was justified or made. A bounded grid search of
forearm/wrist angles for the contact target gave (-5,10,0) degrees while keeping
the grip transform fixed. Actual rendered contact normal was
(-.003450,.107573,.994191), rather than the stale edge-forward target. Loading
tip has y=.913301 and recovery matches ready. No ball velocity injection or
runtime policy change. Current output: Codex outputs/stroke-phases-v3-06,
including all 861 simulated steps and eight views. Camera render inspected.
Footwork, timings, natural grip and continuous trajectory remain unvalidated.

Composed-motion audit found a required controller gap. Editor.PlayerUpperBodyAuditV3
runs 12,000 deterministic adversarial joint-target steps at a stationary pelvis
(seed 1300000, interactive diagnostic only). Actual finite-step paddle motion:
max center speed 7.22080 m/s (0 violations of 12), max acceleration 111.88673 m/s2
(3 violations of 100), max angular speed 21.02304 rad/s (1184 violations of 12).
First violation at step 24. Maximum shoulder-to-grip reach .614812 m. Maximum
difference between endpoint analytic and finite-step center velocity .210111 m/s.
Evidence: artifacts/controls-v3-composed-motion-audit-01.json. Earlier passing
joint tests and two contact fixtures do not establish whole-paddle feasibility.
Do not connect this motor to accepted gameplay or train a promoted policy until
joint coordination enforces composed paddle bounds with feasible braking and
includes locomotion contributions. Do not relax the historical paddle limits
or simply clamp post-contact ball velocity. This audit is a stationary-root
necessary check, not full physical acceptance. No final seeds were consumed.

PlayerUpperBodyBoundedV3 adds coordinated stationary-pelvis joint motion.
It projects proposed rates against composed center speed/acceleration and
angular motion, respects per-joint speed/acceleration/braking intervals, and
checks the actual finite pose delta before committing. Returns false atomically
if no feasible step is found; caller must not advance physics after failure.
It is separate from the existing raw motor and not yet wired into gameplay.
Paired deterministic audit-03 completed all 12,000 steps with zero rejections
and zero bound violations: speed 7.197612 m/s, acceleration 89.84354 m/s2,
angular speed 11.988999 rad/s, reach .614778 m. Audit-02 retained the first
version's small numerical angular overshoot, 12.005026, within old diagnostic
tolerance but above the desired strict limit; the final guard uses an 11.99
measurement margin. Regression requires actual travel and all steps accepted.
Remaining: moving pelvis/locomotion, broader trajectories and progress tracking,
matching the velocity used by physical contact to the accepted finite motion,
physical adapter integration, and natural stroke review. Stationary-root stress
success is not full physical or game acceptance. Audit evidence is in
artifacts/controls-v3-composed-motion-audit-03.json.

User requested phase-7 fan-like roll with the face turning backward/downward.
Diagnostic finish target now uses arm angles (-60,55,25,85,90,-50,-20), preserving
contact/extension targets and the grip transform. Actual rendered finish face
points backward/downward. Output: Codex outputs/stroke-phases-v3-08. An earlier
candidate that lowered the whole arm was discarded after its render showed
hand/torso intersection (v3-07 retained). This is a posed finish correction,
not validation of the continuous sweep or self-collision across its trajectory.
Forearm rotation reaches the provisional upper bound; naturalness remains open.
The requested moving-pelvis coordinated solver work was not started before this
user steering; it remains the next physical-controller integration task.

Moving-pelvis integration (2026-09-08): the coordinated solver now includes a
proposed pelvis translation/rotation in the same finite-step feasibility check
as the ten upper-body joint rates. An infeasible step leaves pelvis, joints and
velocities unchanged. ComposeBounded forwards accepted finite-step paddle
linear/angular velocity to the physical body adapter. Editor evidence:
artifacts/controls-v3-moving-pelvis-editor.json, 220/220 passed, including 6,000
smooth moving-root steps and an impossible 100 m step rejection. This supersedes
the earlier note that moving-pelvis work had not started.

New physical fixture BoundedPaddleSeparatesVaryingSpeedBallsWhilePelvisMoves
covers incoming speeds 2/4/6 m/s and advancing/retreating motion with a translating
pelvis. It currently FAILS; do not count all six cases as executed successfully.
At 2 m/s, retreating direction +1, tick 28, the first face callback has outgoing
relative normal speed -0.826924 m/s. The preceding advancing case passed. The
failure occurs after finite-step contact-velocity agreement and speed checks.
Evidence: artifacts/controls-v3-bounded-contact-playmode-02.json (9/12 passed;
this new failure plus the two pre-existing V2 serve/full-game failures).
Next investigate the whole contact episode and actual Rigidbody motion versus
reported surface velocity, including first-callback timing. A first callback
alone may not establish completed rebound; cause is not yet proven. Do not
inject ball velocity or relax physical limits to pass this assertion.

The stroke preview is programmatically posed diagnostic material, not learned
motion or complete biomechanical validation. Prioritize a controllable bounded
stroke returning varying incoming balls over further held-pose refinement.
No new training, accepted policy, final seeds, or playable-scene promotion.

Contact-episode investigation (2026-09-08): retained trace at
artifacts/controls-v3-contact-episode-trace.csv and the trace run at
artifacts/controls-v3-contact-trace-playmode.json. All six speed/direction cases
show outward relative velocity after face entry. The slow retreating case
enters at tick 28 and separates at tick 30 (8.33 ms later); all other cases
separate at their first callback. In the slow case, reported paddle linear
velocity agrees with Rigidbody velocity to about 1e-7 m/s and angular velocity
to about 4e-5 rad/s around contact. The failure was an unjustified requirement
for separation on the first callback; the exact engine contact timing mechanism
has not been independently established.

The bounded regression now requires separation within four 240 Hz physics
steps, a real face callback, no intervening non-face/other-player collision,
Rigidbody/reported velocity agreement, bounded motion, and outward world-space
return for advancing strokes. No simulation physics or limits changed. All six
cases pass. Current physical integration result is 10/12, with only the two
pre-existing V2 game/serve failures remaining:
artifacts/controls-v3-bounded-contact-playmode-03.json. The temporary trace test
was removed after collecting evidence; its generation script remains in Codex
work/trace_bounded_contact.py. This supersedes the previous unresolved bounded
contact failure, without claiming biomechanical calibration or legal rallies.

Still required for the actual game: controllable stroke interception of varying
ball positions, legal returns over the net, recovery, self-clearance, integration
of four independent controllers and observations, and accepted policy evaluation.
Current collision fixture launches balls near the paddle and supplies joint
targets; it does not demonstrate an agent selecting or timing a stroke. Existing
face callback spin/rule event timing also deserves verification against resolved
contact before claiming accurate slow-contact simulation.

Serve baseline investigation (2026-09-08): current hold-policy probe preserved in
artifacts/controls-v3-serve-current-01.json; pre-contact pose at tick 175 in
artifacts/controls-v3-serve-precontact-01.json. Current serve collides with the
handle and forearm at about .746 s, before face contact at .750 s. Its planned
impact is .7583 s at y=.5225. Pre-contact shoulder y=.8 shows crouch has already
reached its lower limit; this is not simply delayed crouching. Body faults and
short/illegal serves prevent the expected score. The test assertion displaying
expected 1 / actual 0 concerns scoring, not evidence of no completed rallies.

Three bounded diagnostic sweeps (18 total trials) are preserved as
artifacts/controls-v3-serve-clearance-01.json through -03.json. Higher contact
locations alone (.1435/.1835/.2235) do not eliminate handle contact. At pitch
bias +12/+20 and speed scale 1.25, face-only contact is achieved but the serve
hits the net or lands short. Increasing requested speed to 1.5 with small timing
changes reintroduces handle/body contact; none of the 18 trials scored. All used
interactive seed 1300000, existing limits and rules. No trial was promoted and
no runtime parameters changed. Both probes completed and Play Mode was stopped.

This evidence argues against further blind parameter tuning of the legacy
translation/feed serve. Next implementation should use a reachable stroke
trajectory with explicit hand/body clearance and check the resulting physical
ball flight. The new V3 bounded articulated controller remains the intended
control direction; the V2 planner currently assumes a contact motion the body
executor does not realize reliably. Keep the two failing game tests visible.

Stroke intention aiming (2026-09-08): PlayerStrokeAimV3 converts a requested
world-space paddle-face point and face normal to torso + seven arm joint targets.
It uses the existing analytic kinematic derivatives with damped task-space least
squares, joint-range clamping and descent line search. Paddle roll is free; the
fixed grip remains enforced through FK. Returned residuals explicitly distinguish
geometric success (<=5 mm, <=2 degrees) from an unreachable/unresolved request.
This class does not move the player or ball. Execution uses the existing bounded
motor; timing, collision clearance and legal flight are NOT certified by Reached.

Evidence: artifacts/controls-v3-stroke-aim-editor-01.json, 223/223 editor passes.
New coverage includes a reachable arm/torso contact configuration from four
pelvis orientations; a 10 m unreachable target and invalid zero normal; and
bounded motor execution of a Cartesian contact-point and face-direction request.
The latter reaches within 6 mm / 2 degrees after 480 motor ticks with unchanged
speed/acceleration checks. These are geometric/control checks, not ball returns.
A Unity editor Stopwatch probe completed 1,000 repeated nearby solves in 30.6905
ms, all geometrically reached. This is a small warm repeated-target cost sample,
not end-to-end four-player throughput or worst-case solver performance.

Next connect moving contact-point intentions to actual incoming-ball prediction,
verify body/handle clearance through the continuous path and physical legal
returns, then expose the controller to four private player decision instances.
No runtime scene/controller replacement, training, checkpoint modification or
final evaluation occurred. V2 serve and full-game failures remain unresolved.

Continuous aimed physical stroke fixture (2026-09-08): added
PlayerAimedReturnV3Tests.ContinuousAimedSwingReturnsIncomingBallAcrossNet.
The fixture places a player 3.5 m forward of its reset position, prepares through
300 bounded motor ticks, releases a physical ball .8 m ahead at 5 m/s, and drives
a moving Cartesian face-point target through inverse aiming and the bounded
motor. No ball velocity edits after release, no collider removal, and every
geometric aim and motor step must succeed. First floor contact (including out
floor) must be in the opposite court after a net crossing; body/forearm/handle
checks remain in the fixture. This is a flight fixture, not a rules-validated
rally: its warmup can alter rally state, which is not reset to a legal live-rally
history. Do not call a future pass of this test full legal-game acceptance.

Evidence artifacts/controls-v3-aimed-return-playmode-01.json through -05.json.
All attempts made face contact without the checked forearm/handle collision,
but the return requirement FAILS. Initial .25 upward face request landed at
(2.27,0,-1.62); .5 face request landed at (2.44,0,-1.03) with outgoing velocity
(.531,2.411,3.888). Earlier acceleration moved contact earlier but still landed
short. Requested 4 m/s target motion with longer follow-through produced actual
contact normal (.199,.412,.889), despite requested normal (0,.447,.894), and
outgoing velocity (1.861,2.425,3.971), landing (3.39,0,-.93). Thus the wider miss
was NOT proof of greater forward power or a net crossing. Current physical test
result is 10/13: this failed return plus the two existing V2 game/serve failures.

The geometric inverse solution does not imply the independently rate-limited
joint motor follows that Cartesian path/orientation during a fast stroke.
Next address coordinated task-space trajectory tracking (including face normal
and contact-point velocity) under the same joint and whole-paddle limits. Avoid
more scalar pitch/speed tweaks until the actual transient tracking error is
controlled. Retain the failed court-return requirement rather than weakening it
to face contact. No final seeds, training, policy promotion or scene replacement.

USER DIRECTION — learned play first (2026-09-08; supersedes prior next steps)

The user explicitly wants the model to learn serving and playing with a
constrained body, followed by observation of learned movements and correction
of unnatural freedoms. Stop tuning programmed serves/stroke trajectories as a
prerequisite for training or a substitute for learned control. Constraint and
feasibility tests remain useful, but a hand-authored stroke need not win a
court-return fixture before we expose the constrained body to learning.

Next work: version the articulated-body policy action/observation contract and
connect it to the training environment and rollout collector. Four players have
private observations/actions/decision state and shared policy weights. The
learned policy owns locomotion, torso/arm commands, stroke timing and serving
decisions. The simulator owns joint direction/range, speed and acceleration
limits, fixed grip, collision response and doubles rules. Do not route learned
actions through PlayerServeSkillV2, StrokeController, hard-coded swing phases or
an automatic interception planner. Ball-feed/reset curricula must be explicitly
disclosed and separate from unassisted gameplay evaluation. Serving needs an
explicit possession/release contract so its timing can be learned too. Preserve
historical checkpoints/contracts; V3 needs a versioned action schema and its own
training provenance.

Short environment/rollout validity checks should lead into training, then
learned-play inspection. Do not require visually perfect scripted technique.
The geometric aim and task-space tracking helpers remain isolated diagnostics
unless a later explicit policy-control design calls for them; they do not
supply agent strategy or technique. Prior held-pose previews are not training
demonstrations or target strokes.

Interrupted work status: PlayerUpperBodyBoundedV3 is now partial; TryStep uses
shared private TryRates. New PlayerUpperBodyTrackingV3.cs solves bounded joint
rates for requested face-point velocity and direction, then checks exact motion
limits before committing. Only the diagnostic return test uses TryTrack. The
pending run completed at 10/13 physical tests (still three failures), preserved
in artifacts/controls-v3-task-tracking-playmode-03.json. No full editor regression
has yet been run after this refactor; last full editor evidence (223 passes)
predates it. No training has started for the articulated body. Do not promote
this diagnostic controller or claim current game acceptance.

Learning environment implementation (2026-09-08)

Implemented, compiled and tested the first direct articulated learning interface:

- PlayerActionV3 (PlayerControls): version player-action-v3-joints-17. Indices
  0/1 are body-local movement; 2 requested turn rate scaled by 180 deg/s; 3
  crouch, 4 jump, 5 sprint; 6..8 torso angle targets; 9..15 the seven arm joint
  angle targets; 16 ball release. Nonnegative channels 3/4/5/16 are [0,1],
  others [-1,1]. Arm zero maps to Ready and each signed endpoint maps to its
  corresponding anatomical prototype bound. No stroke phase/shot/intercept input.
- PlayerControlWorldV3: four private root, procedural leg and bounded articulated
  motors. Deep forks make each proposed four-player step atomic. New root turn
  rate ramp (720 deg/s2, 180 deg/s requested maximum) avoids instantaneous yaw
  rate changes. Same court/partner contact solver; no ball state in this kernel.
  Failure returns false with RejectedPlayer and commits no physical state.
- Deep Fork methods added to PlayerUpperBodyMotorV3 and PlayerUpperBodyBoundedV3.
- PlayerLearningMatchV3: actual DoublesWorld colliders, four bodies, direct policy
  actions only. No ServeSkill, StrokeController, inverse aiming or task-space
  tracker on its execution path. Holds the ball below the procedural left hand
  until the server requests release. Initial serving protocol is a drop from
  rest (no toss impulse); release timing and body preparation are policy-owned.
  Held ball is kinematic with collisions disabled only while possessed; release
  restores dynamics/collisions. Ball flight is physical after release.
- PlayerObservationV3: version player-observation-v3-joints-121. First 54 values
  are the existing observable scene/rule state; add locomotion/turn/crouch rate,
  shoulder/feet/support, rule momentum, own 10 joint angles/rates, own 17 active
  actions, and server-possession flag. Private owned data; no teammate actions.
- PlayerDecisionLoopV3: four distinct policy instances, all observations captured
  before inference, private RNG by identity, shared-weight-compatible interface,
  20 Hz decisions with 6 physics ticks of latency. No V2 shot-intent adaptation.

Evidence: artifacts/controls-v3-learning-editor-01.json = 226/226.
artifacts/controls-v3-learning-playmode-01.json = 12/15. Both new learning tests
pass: separate observations/decisions with delayed release, and a non-server
cannot release the held ball. The three remaining failures are old V2 serve/game
and the scripted aimed-return diagnostic. Per the explicit user direction, stop
tuning that scripted technique; retain its historical failure as diagnostic
evidence, not a prerequisite that dictates learned play.

No V3 actor, training rollout collector, reward implementation or training run
exists yet. Prior checkpoints use an incompatible schema and remain unchanged.
Next: drill reset/reward/termination contract, learning rollouts and shared V3
policy/PPO with action-distribution parity checks, then learned skill inspection
and progression toward 2v2 self-play. Drills precede self-play as confirmed to
the user; they provide varying starts/ball feeds and outcomes, not prescribed
stroke sequences. Final evaluation seeds remain untouched.

Outstanding mechanics and integration issues to handle explicitly:

- Jump presently requests an immediate vertical root impulse that the bounded
  paddle cannot follow; the new atomic-rejection test proves this is rejected.
  Do not present jump as functional or silently relax the paddle limit. Fix its
  physical execution or disclose a temporary drill action mask before training.
- Infeasible physical steps terminate the match via Failure with no physics time
  advancement; trainer must record these as failed/truncated transitions, never
  silently drop samples or count frozen states as successful rollouts.
- StepAgents currently does not catch inference exceptions into Failure (unlike
  the V2 game wrapper); fix terminal failure handling before rollout collection.
- Match currently has no full rally/game reset wrapper, rewards or drill modes.
- Holding/releasing uses a procedural non-hitting hand and at-rest drop protocol,
  not a learned second arm or a physically simulated grasp. Do not claim full
  serve biomechanics. No V3 self-collision projection yet beyond existing physical
  body-vs-ball/players contacts; grip and individual joint limits are provisional.
- Joint/locomotion parameter values remain uncalibrated human prototypes.

First neural contact-drill rollout (2026-09-08)

The learning-first path now includes PlayerActorV3 / PlayerActorModelV3, Python
scripts/player_v3_actor.py, PlayerContactDrillV3, Editor/PlayerDrillRolloutV3,
scripts/player_v3_rollouts.py, and scripts/player-v3-ppo.py. The PPO updater is
implemented but has NOT executed an accepted optimization update yet.

Bootstrap actor: artifacts/player-v3/bootstrap-01/actor.json.
SHA256 29e4f19932e8951fb75a3fa94606aeacb9bebc1211328f1b10660e123ad03113.
Runtime source hash (Unity/Python verified equal):
88c3f278607dbb0fa4ea0bf1bd5aaa60d4dffe458f652b8fef0db9535b4cbfe1.
Transferred the old checkpoint's two hidden layers, with its first 54 input
columns retained and new observation columns zero initialized. All 17 output
heads are freshly initialized; old shot/serve logic is not imported. Original
parent actor SHA remains 61c59e110797290c46b30b91a9fa2d0d3665e92a40f3c998bf2e24ed168edc06,
verified unchanged. V3 actor metadata explicitly reports trainingSteps=0 and
the parent training source. Exploration is a raw diagonal Gaussian with tanh
action mapping; nonnegative controls use (tanh+1)/2. PPO computes ratios on
stored raw samples, so a fixed action transform cancels in the ratio. Masks
exclude inactive action channels from log probability and entropy.

Unity parity at bootstrap-01/unity-parity.json and parity-check.json:
mean max error 1.19e-6, action/logProbability error 0 for the fixed sample.
Model weights are shared privately and immutable to player actors; samples/RNG
remain per player. No V1 checkpoint metadata or historical model was rewritten.

First drill: grounded contact, randomly varied feed distance .35-.65 m, lateral
offset +/-.16 m, vertical offset +/-.12 m, speed 3-5 m/s relative to the initial
paddle. The learner rotates through all four seats. Other players are held with
an explicit all-off action mask; learner jump and release are masked. Root,
torso and arm control remain learned. Jump takeoff/landing remain unresolved;
the temporary grounded mask was explicitly disclosed to the user. No joint or
paddle constraint was loosened. Match.InitializeContactDrill supplies disclosed
synthetic live-rally rule history and a physical ball feed at reset; it provides
no stroke command or subsequent ball steering. This is a curriculum drill, not
an unassisted game/serve evaluation.

Reward: bounded distance-progress potential (.05 * change in distance capped at
2 m), +1 for a face callback, -1 for body/handle/other-player contact or infeasible
step, zero additional terminal reward for miss/rule terminal/time limit. Body
contact has priority over face contact in the same recorded step. Contact success
does NOT establish a clean full contact episode, useful return, legal rally or
natural technique; later drills/evaluation must cover those. Maximum 360 ticks.
Software exceptions are recorded, and PPO refuses any episode with such an
exception. Inference exceptions now make PlayerLearningMatchV3 terminal.

Pilot: artifacts/player-v3/contact-pilot-01, interactive seeds 1300000..1300015.
All 16 episodes completed: 9 face contacts, 3 body/handle contacts, 4 misses,
no infeasible steps or exceptions. 709 physics ticks, 65 decision records;
57 attempted actions and 8 explicitly pending/unattempted records. 0.448 seconds
collector elapsed (small editor sample, not full-game throughput). validation.json
confirms ownership/clock/mask/seed/terminal/reward accounting on every record.
Unity/Python max rollout errors: means 3.34e-6, actions 0, log probability 2.885e-5.
Unattempted pending decisions receive no reward and are excluded explicitly from
PPO inputs. Rewards before first applied decision remain separately accounted.

PPO implementation accepts training split only, validates source/actor/protocol
and input hashes, uses per-episode GAE, masked raw-Gaussian log probabilities,
shared actor/value networks and the existing atomic optimizer/KL rollback helper.
It exports an actor/critic plus provenance only after accepted updates. Feeding
the interactive pilot was intentionally tested and rejected before any output
directory was created. No optimization or new trained V3 checkpoint exists yet.

Current physical regression: artifacts/controls-v3-drill-playmode-01.json = 13/16.
All learning-environment tests including terminal inference failure pass. Three
pre-existing failures remain: the isolated scripted aimed return and V2 serve/
full game. Last full editor run is 226/226 (before actor/drill additions; Unity
compiled all current code and the pilot/physical suite executed current code).
Play Mode was stopped after the pilot; subsequent physical test run completed.

PENDING USER QUESTION (do not infer an answer from elapsed time): docs/
PLAYER_AGENTS_TRANSFER.md line 78 asks for fresh training/development seed blocks
checked against records on the original machine. These records are absent here.
Asked whether to reuse training-only seeds under separate V3 provenance or wait
for original records to allocate a fresh block. Final range remains untouched.
Once answered, collect a first actual training block with the same bootstrap
actor/source; validate it; execute the PPO updater; verify exported policy parity
and assess fresh development drills. Do not train on the interactive pilot or
silently relabel its split. Continue toward serving/returns/rallies then 2v2
self-play and the unchanged acceptance gates. No task blocker status was set.

## 2026-09-08: learned drill training is now running

This entry supersedes the pending seed question and zero-update status above.
No user answer to the optional seed-history question was received. The existing
authorization to train and the frozen train/development/final split allow a
separately recorded V3 experiment. Historical freshness across V1/V2 is explicitly
unverified; this is not a claim of user approval or globally unused integers.
artifacts/player-v3/seed-ledger.json records allocations. The interactive pilot
and development feeds are excluded from optimization; final seeds are untouched.

Following the user's learning-first direction, the curriculum uses learned contact drills, then learned
serves and returns, rallies, and 2v2 self-play. Drills may supply feeds, reset
conditions and task rewards. They must not supply stroke phases, joint sequences,
automatic shot selection, intercept steering, or serve execution to the policy.
The constrained body defines available motions; the policy learns their use.
The user will review learned motion for unnatural behavior after learning works.

Bootstrap development baseline: contact-baseline-dev-01, 128 feeds, 86 face-contact
callbacks, 18 body/handle contacts, 24 misses. First training block:
contact-train-01, seeds 1000000..1000255, 813 attempted decisions / 9887 physics
ticks, 184 face contacts, 26 body/handle contacts, 46 misses. Validation passed.
ppo-01 rejected its first update at KL 0.081996 (limit 0.01), rolled back and did
not export an actor. ppo-02 used learning rate 0.00002 with the same KL limit;
28 optimizer steps were accepted. Actor SHA256:
d14ca21564a361d4e663bbb3c5ed91153d3cd980522ba25db3b7a0d64a75a63b.
Unity/Python parity passed. contact-ppo02-dev-01 produced the same aggregate
86/18/24 development outcomes: training ran, but improvement was not established.

The next block is allocated as 1000256..1002303, 2048 episodes from ppo-02.
runtime-identity-01.json captures the current Unity 6000.5.5f1 configuration and
physics identity before this block (it is not a retroactive runtime capture for
earlier batches). Source SHA256 remains
88c3f278607dbb0fa4ea0bf1bd5aaa60d4dffe458f652b8fef0db9535b4cbfe1.
Physics settings identity 9b08a30530c965c7; simulation configuration identity
b0e21687f3c2838c. All historical artifacts and the original parent actor remain.

Contact callback success remains a pipeline/early curriculum metric, not proof
of clean separation, useful return, natural technique, legal serve or a game.
Check stationary-player outcomes before interpreting success as learned skill.
No V3 model has been promoted into the playable scene. The active 2v2 goal and
unchanged full-game acceptance requirements remain open.


## 2026-09-08: current learned drill training handoff

See docs/PLAYER_V3_TRAINING.md for the current state. Reaction drills v2, two physical tests, 1124 accepted PPO optimizer steps across 12544 training episodes, a completed three-round transferred-policy series and a fresh-trunk comparison are recorded. No accepted 2v2 model exists and final seeds remain untouched. Earlier pending-seed/no-optimization notes are superseded. Unity is left in Play Mode with no active collector after these runs.


## 2026-09-08: learned serve and nearer-return updates

See docs/PLAYER_V3_TRAINING.md for the current 124-observation/18-control schema, bounded off-hand lift, learned release, preserved rally score/reset lifecycle, warning fix, and separate training/development results. V3 totals are now 15,616 training episodes and 2,084 accepted optimizer steps across branches. Neither serving nor nearer-return development has a legal landing yet; no model is accepted or promoted and final seeds remain untouched. Current source is 5c5dcb62ee2d4fc51e76697b4b20026ea859cfd84f0753179d66fad713a30eeb. The previous contact-only status above is historical.
