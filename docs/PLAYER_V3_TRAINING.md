# Picklebot learned serve and return drills

Recorded 2026-09-08T00:26:34.260620+00:00.

The trajectory remains contact skills, learned serves and returns, rallies, then
2v2 self-play. Four independent players share policy weights; each owns its
observations, actions and random generator. Drills rotate one active learner
through all four seats. They supply starting situations and rewards, and the
policy chooses body movement, joint targets and release timing. The V3 learning
path does not invoke the older scripted serve or stroke controllers.

These are training checkpoints, not accepted player models. No candidate has
been promoted into the original playable scene, and full learned 2v2 self-play
has not yet been demonstrated.

## Measured development results

| Evaluation | Episodes | Face contacts | Net crossings | Legal landings | Body/handle faults |
|---|---:|---:|---:|---:|---:|
| Serve before update | 128 | 0 | 0 | 0 | 16 |
| Serve after update | 128 | 0 | 0 | 0 | 14 |
| Nearer return before update | 128 | 52 | 0 | 0 | 53 |
| Nearer return after update | 128 | 52 | 0 | 0 | 55 |

Each before/after pair uses the same 128 sampled-policy development seeds.
Serving uses 1100256–1100383; nearer returns use 1100384–1100511. These episodes
are excluded from optimization. A face-contact episode can later end in a body
fault or bad landing; it is not a completed useful stroke.

The serve pair both recorded 112 releases and 95 drop bounces. There is no clear
serving improvement from this update. The source transition between the serve
and return experiments removes ignored velocity writes while the ball is held;
each development pair uses one consistent runtime.

The broader-exploration comparison changed only torso/arm sampling standard
deviation from about 0.165 to 0.5, preserving all learned mean-network tensors.
On 128 interactive serve trials it produced one illegal face contact and no
accepted serve. On nearer-return trials it reduced face-contact episodes from
50 to 19, with no net crossings in either case. Those pilot episodes were never
optimizer input. This variant was not selected as the new training parent.

## Training completed

- Serve: 1,024 fresh training episodes, 94,216
  attempted decisions and 740 accepted PPO steps.
- Nearer return: 2,048 fresh training episodes,
  27,840 attempted decisions and
  220 accepted PPO steps.
- Across the recorded V3 branches: 15,616 distinct training episodes,
  242,025 attempted decisions, 2,911,898 physics steps and 2,084
  accepted optimizer steps. These totals include the earlier contact experiments;
  they are not totals for full-game training or a single checkpoint's lineage.
- Current updates retain learning rate 0.00002, batch size 512, up to four epochs,
  a measured KL ceiling of 0.01 and atomic rollback of rejected updates.
- Rollout validation checks private action ownership, delayed application,
  terminal transitions, reward accounting, explicit masks, seed partition,
  runtime/model identity and Unity/Python inference parity. Pending actions that
  were never applied are excluded from optimization.

## Body and runtime checks

The current schema has 124 observations and 18 controls. The added control lifts
the non-paddle shoulder through a bounded range; release remains a separate
policy action. The migration preserved the previous 17 output means, with zero
initial weights on the three new observation inputs. It is a reduced body model,
not complete or calibrated human biomechanics.

Jump remains masked because its takeoff/landing is not feasible under the current
paddle acceleration constraints. All other physical control limits remain in
place. Contact/return drills mask release; the serving drill enables it. Serving
starts with the ball held and simulates the policy's actual release and drop.

The simulation previously wrote angular velocity to the held kinematic ball on
every tick. Dynamic forces and spin decay now run only after release. A paired
probe measured the same held position, release position and release velocity,
while the warning count fell from 24 to zero.

- Core editor tests: 226/226 passed in
  `artifacts/controls-v3-held-ball-editor-02.json`.
- Physical integration: 22/25 passed in
  `artifacts/controls-v3-held-ball-playmode-01.json`. The remaining failures are
  the previously recorded scripted aimed return and two V2 serve/game fixtures.
- An editor-test setup attempt made while Play Mode was still active failed
  before producing a test verdict. Its status and log excerpt are retained in
  `artifacts/controls-v3-held-ball-editor-01.json`; the successful rerun follows it.

## Checkpoints and evidence

Current runtime SHA256: `5c5dcb62ee2d4fc51e76697b4b20026ea859cfd84f0753179d66fad713a30eeb`.
Latest candidate: `artifacts/player-v3/near-return-ppo-01/actor.json`.
Candidate SHA256: `a64c754af42008fdb800561b0a4be0cb4b5d8826e63bf477bb90eadbea109907`.

The earlier serve update is retained in `artifacts/player-v3/serve-ppo-01`.
`held-ball-transfer-01` records its unchanged tensors against the corrected
runtime. Source archives for this work are `source-2e879782.zip` and
`source-5c5dcb62.zip`, with file/hash manifests alongside them. The preceding
serving setup has a separate `source-7f8b0b95.zip` archive.

Seed allocations remain in `artifacts/player-v3/seed-ledger.json`. Freshness
against older source-machine experiments is unverified and remains recorded as
such. Final-evaluation seeds 1200000–1299999 have not been consumed, and the
frozen full-game acceptance criteria have not been changed.

## Next work

Both development pairs still have zero legal landings. The return drill currently
penalizes a miss/bad return by 0.1 and a body/handle fault by 1. This may favor
avoiding a difficult incoming ball; it is a hypothesis from the reward code,
not an established explanation of the measured results. Check that incentive
before repeating a large unchanged training series.

Use legal returns and reliable serving as progression evidence, beyond contact
callbacks or safe-drop rewards. Improve the drill curriculum or exploration only
when measurements justify it, while retaining policy control of technique.
Then build up rallies, retain weak-skill drills alongside 2v2 self-play, and run
the full acceptance comparisons before promoting a model for movement review.
Rally reset/score plumbing exists, but the V3 full-game collector, frozen-opponent
comparisons and accepted playable demonstration remain open.

The prior contact-training comparison and history are preserved in
`artifacts/player-v3/training-notes-before-serve-return-01.md`.


8 September 2026: the v5 reward comparison completed four rounds without legal returns. See ML_AGENTS_TRAINING_PLAN.md for the completed evidence and the user-requested ML-Agents 4.1 reassessment. Next work should integrate the maintained trainer, not automatically extend the custom PPO series. No ML-Agents migration or accepted policy is claimed.


ML-Agents integration update — 8 September 2026: the matched SDK/Python stack is installed and verified; the new drill path uses maintained ML-Agents PPO. See `ML_AGENTS_TRAINING_PLAN.md` for current implementation and evidence. A continued framework run reached 131,080 trainer steps. Its held-out contact result was 57/128 versus the unoptimized baseline’s 46/128, with body/handle contacts falling from 14 to 1. This is early drill improvement, not legal serve/return or playable 2v2 acceptance. Historical custom results above remain preserved.


Team framework integration update (8 September 2026): MA-POCA/self-play now runs and resumes on two simultaneous 2v2 courts, reaching 4,268 trainer steps and 84 Adam updates. Bounded enclosure braking, Academy team-switch resets, and complete shutdown accounting are verified. These runs produced zero legal serves or non-serve hits; they establish infrastructure only. See docs/ML_AGENTS_TRAINING_PLAN.md and artifacts/player-v3/mlagents-teams-resume-04/training-verification.json. Final seeds and the playable model remain unchanged.


Return training and monitoring — 8 September 2026

The maintained PPO policy completed 4,123 additional near-return drills on eight parallel courts. Training continued from step 131,080 to 196,622, preserving actor, observation normalization, critic and Adam state. It performed 168 additional Adam updates (504 total). Two legal returns occurred during sampled training. Eight partial episodes and their 756 aggregate physics ticks remain recorded in the run summary. No simulation failures occurred; a new bridge regression ensures software/solver failures cannot be submitted as normal terminal loss samples.

On the same 128 held-out seeds, paddle-face contacts increased from 44 to 77, but legal returns and net crossings remained **0/128**. Body/handle outcomes increased from 19 to 36. Unity/PyTorch actions matched within 1.5e-7 for both evaluations, with zero physical mapping error. This checkpoint is not accepted or promoted.

The user's observation of a nearly stationary paddle arm is supported by measurements: median per-attempt shoulder-yaw motion 11.9 degrees, elbow flexion 5.3 degrees, wrist flexion 18 degrees; the highest sampled paddle speed was 1.59 m/s. All seven paddle-arm joints responded, so the arm was not mechanically frozen. The left arm moved about 71.8 degrees. Its mean requested lift was 70.6 degrees because a neutral continuous policy output maps to physical lift 0.5 (70 degrees). This makes left-arm movement much more obvious and does not establish learned balance or useful swing mechanics.

The next learning change must address useful outgoing flight and sensible off-hand behavior. The current reward can improve through additional contact without reliable net clearance. Preserve existing checkpoint semantics when considering action/reset changes. Keep swing decisions learned from the constrained body.

To watch future runs in Unity, choose **Window → Picklebot → Training Monitor**. Select a court, enable its rendering, choose a close player view, and click **Watch speed** or **Fast training**. Watch speed is one physics tick per Editor frame, so wall-clock speed depends on frame rate. The monitor affects presentation and throughput; physical dt, observation/action clocks and rewards remain unchanged. It labels training separately from saved-policy evaluation. Scene view displays the court; Game view may remain blank.

TensorBoard is running locally at http://127.0.0.1:6006/. Filter for Picklebot and inspect FaceContact, NetCrossed, LegalReturn and BodyOrHandle. Earlier contact-training history is included because this is a full continuation; the near-return stage begins at step 131,080. The active trainer has exited successfully; the evaluation is complete and its final court remains visible for inspection. TensorBoard remains available. Its current launcher uses an isolated setuptools compatibility dependency because the training environment's newer setuptools lacks TensorBoard's pkg_resources import.

Evidence: artifacts/player-v3/mlagents-return-train-01, mlagents-return-before-dev-01, mlagents-return-after-dev-01, and mlagents-return-curriculum-01. All paths are under F:/dev/picklebot. Source archives, original checkpoints, seed allocations and failed historical runs are preserved. Final-evaluation seeds remain untouched.


Swing reference feasibility — 8 September 2026

The preview is an authored pose illustration. It uses PlayerUpperBodyMotorV3 and directly applies external frames; the learner uses PlayerControlWorldV3 and its coupled PlayerUpperBodyBoundedV3 constraint solver. The illustration therefore cannot be treated as an already validated training demonstration.

Six isolated tests now exercise the full stationary bodies for all four seats: original phase targets and sampled preview poses, each at duration multipliers 1, 2 and 4. Commands are held at 20 Hz with the existing 25 ms action delay; the world advances at 240 Hz. All 12,054 world ticks (48,216 body ticks) completed without a rejected step. The largest measured paddle-origin speed was 4.303 m/s, acceleration 64.77 m/s², and angular speed 11.967 rad/s, within the unchanged 12/100/11.99 limits. This establishes feasibility for these fixtures, not general feasibility, anatomical realism, collision-safe swings, or learned skill.

| Reference method | Duration multiplier | Maximum arm-angle deviation | Maximum paddle-face deviation |
|---|---:|---:|---:|
| Original phase targets | 1 | 31.43° | 53.82° |
| Sampled preview poses | 1 | 44.09° | 66.79° |
| Sampled preview poses | 2 | 21.52° | 32.35° |
| Sampled preview poses | 4 | 9.70° | 14.98° |

These are deviations from the corresponding time-stretched preview sample, not violations of joint bounds. A duration multiplier of 4 means quarter-speed reference progression. Merely holding the original phase targets for longer does not slow their motor response; only the sampled-pose progression tested here supplies a slower target trajectory. Measurements use paddle origin velocity; they must not be compared directly with earlier face-point speed measurements without accounting for angular velocity.

The current 124-field feed-forward actor sees body, ball, rules and previous actions, but no exercise phase or elapsed exercise time. Recorded observations expose exact conflicts in the timed target sequence. In the four-times-duration phase-target fixture, player 0 has identical observations at ticks 2556 and 2568, while the expected command changes by 1.0 in a physical action channel: hold finish versus recover. The deterministic actor cannot exactly reproduce both timer-selected labels from the same input. This is a dataset/task design issue, not proof of an inadequate RL algorithm. It does not establish that all movement imitation is impossible.

Next experiment: construct short movement demonstrations through the actual constrained motors, initially using the slower reference. Remove timer-only holds, check observation/action consistency, and record actual observations and issued actions rather than treating desired angles or pictures as demonstrations. Keep the current 124-observation / 16-continuous-plus-release actor contract where possible so transferred policy weights remain usable. If timed trajectory tracking is necessary, define observable exercise cues and an explicit checkpoint/gameplay transfer contract before adding inputs. Do not silently give the deployed policy a scripted swing clock or target generator.

Use the maintained ML-Agents imitation support for an isolated, preserved warm-start experiment; validate action scaling and the recorded decision/application delay before optimization. Then compare the warm start with its preserved parent on easy-ball and near-return development outcomes. Movement tracking alone does not qualify the model for self-play or promotion. Feed variation, drop-serve learning, doubles self-play, physical/throughput baselines and all frozen game acceptance criteria remain required.

No policy was trained or replaced in this audit. The previous evaluation is still complete, with 0/128 held-out legal returns. Its retained court remains visible in Unity. Historical evidence, model weights, action/observation semantics, simulation limits and seed ledger are unchanged; final seeds remain untouched.

Evidence: artifacts/player-v3/swing-reference-feasibility-01 in F:/dev/picklebot, including per-decision observations/commands, sampled poses, per-tick extrema, source archive, reference hash and analysis. Audit 03 includes action latency and is authoritative; audit 02 omitted latency and is retained as an intermediate result. Audit 01 returned only a type name, so it supplies no quantitative evidence.


Movement warm start and joint-boundary fix — 8 September 2026

The movement proposal has now been tested with real policy optimization. We recorded 32 authored movement trajectories, using four independent player decision loops per isolated match, 20 Hz decisions, the real six-tick action delay and 240 Hz physics. Duration and amplitude vary by player. The generator removes stationary sample holds from the preview and executes the remaining targets through the full constrained motors. It is Editor-only demonstration tooling, never a runtime controller for the learned players.

The recordings contain 6,495 decisions across 20,916 world ticks. Twenty-four trajectories (4,901 decisions) trained the actor; eight withheld trajectories (1,594 decisions) measured offline action imitation. They are variations of one authored reference, not independent human motion captures or a broad generalization benchmark. Exact identical-observation label differences remain below 0.009 in normalized environment action units; the large timer-only conflicts from the original phase-target fixture are absent. All source records and canonical demonstrations are preserved.

The warm start uses the unmodified pinned ML-Agents BCModule and its Adam implementation. Project-owned code loads each demonstration separately to avoid cross-file terminal transitions, then converts the continuous training labels from canonical Unity controls to the raw coordinates used by the framework's cloning loss (multiply by three). Canonical .demo files retain [-1,1] actions. The conversion was round-tripped through the framework's own action export. Installed BC source matches the pinned vendor source byte-for-byte.

The actor and normalization were copied exactly from the 196,622-step PPO return checkpoint. The experiment then performed 1,024 fresh BC Adam updates, preserving normalization and the original checkpoint. It added zero RL environment steps. The new checkpoint contains actor/global-step state plus BC Adam state; it is an offline warm start, not a full PPO resume with critic/optimizer continuity. Its local RL step counter is zero; parent RL experience and BC updates are separately recorded. Optimization and export took about 8.9 seconds on CUDA, excluding data loading and environment recording; this is not a complete Unity throughput benchmark.

Held-out continuous action RMSE fell from 0.485 to 0.0188; torso-and-paddle-channel RMSE fell from 0.354 to 0.0212. These are normalized action errors on recorded states, not degrees, trajectory-tracking accuracy, or legal-return success.

The first autonomous free-movement check exposed a real motor exception at tick 229 (0.954 seconds): floating-point cancellation in the braking formula caused a joint at 7.786234e-10 degrees to integrate beyond its zero-degree boundary. A single-joint test reproduced it without any learned policy. The fix rationalizes the same braking expression in double precision and rounds its positive result inward by one float step. It does not loosen anatomical, speed or acceleration bounds or snap poses to a target. All 237 Editor tests passed, including six new tiny-distance boundary cases checked at both ends of a joint range.

After the fix, four independent inference agents completed the same 12-second free-movement check (2,880 world ticks, 960 policy decisions) without a failure. Each policy received only its usual private observations; no reference phase, target or scripted action was supplied. Shoulder-yaw ranges were approximately 121–144 degrees and elbow-flexion ranges 37–60 degrees. This establishes substantial autonomous arm movement, not a natural or accurately reproduced stroke.

Both parent and warm-start models were evaluated again under the corrected motor on the same 128 development returns:

| Outcome | Parent PPO | Movement warm start |
|---|---:|---:|
| Paddle-face contact episodes | 77 | 65 |
| Net crossings | 0 | 0 |
| Legal returns | 0 | 0 |
| Body/handle terminal faults | 36 | 54 |
| Misses | 48 | 41 |
| Bad returns | 44 | 33 |

Contact episodes can subsequently end in a body/handle fault, so the contact row is not an additional terminal-outcome category. Unity/PyTorch action error stayed below 1.8e-7 and physical action decoding matched exactly. Both 128-episode evaluations completed without solver/software failures. The corrected-motor outcome counts match their earlier counterparts; original runs remain preserved separately.

Conclusion: movement imitation is trainable with the existing actor contract, but this first warm start does not yet help it return the ball. It remains a candidate for subsequent on-policy easy-ball adaptation; it is not promoted. The parent is preserved as the comparison baseline. More supervised fitting alone is not justified by these results. The next experiment should connect the learned movement to progressively easier real ball contact and reward actual return outcomes, while checking autonomous motion for drift from the authored reference. No runtime swing program is installed. Serving/release learning, varied returns, doubles self-play, measured physical/throughput baselines and frozen full-game acceptance remain unfinished.

New training allocation: 1060752–1060783, all accounted for; next unallocated training seed is 1060784. Free-movement development seed: 1100768. Paired return development cohort remains 1100640–1100767. Final seeds are untouched. The latest return evaluation is complete, and its last court is retained in Unity for inspection; the optimizer has exited. The completed scene may look stationary until another evaluation or training run is started.

Evidence under F:/dev/picklebot/artifacts/player-v3: movement-demonstrations-01, movement-bc-01, movement-bc-return-dev-01, joint-braking-precision-01, movement-afterfix-parent-dev-01, and movement-afterfix-candidate-dev-01. Source archives, original failed reproduction, numerical regression checks, full policy decision traces, canonical demonstrations, checkpoint hashes, and paired outcomes are included. The CLI timed out while recording demonstrations, but the original execution completed and its files were inspected; it was not restarted. One free-movement observation also timed out after its temporary objects had been cleaned up; a separate repeat saved evidence directly to disk.


Easy-return pilot and longer continuation — 8 September 2026

The movement warm start now has a tested easy-ball adaptation stage. The new easy-return task keeps the near-return player positions, ball physics and joint controls. Its reset uses a 0.65–0.75 second ballistic flight estimate and smaller paddle-local target variation (±0.06 m horizontally, ±0.04 m vertically). Actual contact timing remains subject to drag and gravity. A capped 0.25 reward tracks the best actual forward ball progress after a real face contact; it cannot be earned repeatedly by moving backward and forward. Legal-return success still requires an accepted opponent-side bounce. The original near-return task retains its prior reset/reward behavior.

The physical drill suite passed 3/3 tests (including the new task for all four seats), and the reward cap/oscillation/invalid-input checks passed 2/2. These are curriculum and reward-accounting tests, not full-game acceptance tests.

PPO copied the BC actor/normalizer and the preserved PPO parent's critic exactly, then used fresh PPO Adam state. The completed pilot reached 32,786 new trainer steps, with 72 Adam updates from three complete update buffers. It collected 1,604 complete attempts on eight arenas, 32,899 observed decisions and 386,304 world ticks. Eight partial attempts and their 1,316 aggregate ticks remain accounted for. No simulation failure occurred. There were 740 training contact episodes but no net crossings or legal returns. The mean-reward trend improved temporarily; it did not establish useful outgoing flight.

On the frozen easy-return development cohort:

| Result | Before PPO | After pilot |
|---|---:|---:|
| Face-contact episodes | 112 | 128 |
| Misses | 12 | 0 |
| Body/handle faults | 5 | 0 |
| Bad returns | 111 | 128 |
| Net crossings | 0 | 0 |
| Legal returns | 0 | 0 |

Face contact can precede a later fault, so it is not an additional terminal outcome category. The earlier commentary's 111 contacts counted bad-return outcomes; the exact before count is 112 face-contact episodes.

The original, harder near-return cohort still had 70 face contacts, 59 body/handle faults, 39 misses, 30 bad returns, and zero legal returns. This is improvement on the easier contact task, not demonstrated general return skill. Both exported-policy evaluations matched PyTorch within 1.5e-7 with exact physical action mapping. No model is promoted into accepted gameplay.

In response to the user's interest in training longer, a full PPO continuation is configured from step 32,786 to a target of 131,072, using eight arenas and the same task, reset distribution, reward, constraints, observations, actions and optimization parameters. It resumes actor, normalizer, critic and Adam state (72 prior updates). The complete trainer directory before continuation is preserved and hash-verified in easy-return-bc-resume-02/trainer-before-continuation.zip. The same trainer run ID, easy-return-bc-01, keeps TensorBoard history continuous at http://127.0.0.1:6007/. The RNG seed is set again on process launch; this is not claimed identical to uninterrupted sampling.

Training block 1060784–1064879 belongs to the pilot; its unused seeds remain reserved. The longer run reserves 1064880–1073071. Easy-return development seeds are 1100769–1100896; original return development seeds remain 1100640–1100767. Final evaluation seeds remain untouched. The longer run requires new checkpoint evaluations on both cohorts before judging whether extra training improves flight or returns. Contact rate and reward alone cannot satisfy that gate, or the unchanged full 2v2 acceptance criteria.

Evidence under F:/dev/picklebot/artifacts/player-v3: easy-return-curriculum-01, easy-return-bc-train-01, easy-return-bc-before-dev-01, easy-return-bc-after-dev-01, easy-return-bc-transfer-dev-01, and easy-return-bc-resume-02. Launch records, source archives, checkpoint lineage, initial strict module-load checks, test reports and episode/decision records are preserved.


Longer fixed-setup training results — 8 September 2026

The PPO continuation completed at 131,124 total easy-return trainer steps (98,338 additional experiences), on eight concurrent drill arenas. Each arena trains one learner, with seats rotating between episodes; the four-player game still uses four independent observations/actions with shared policy weights. The task, reward, constraints and optimizer settings stayed unchanged. Actor, normalizer, critic and Adam state resumed from the pilot. The source and archived pre-continuation trainer files were hash-verified, and no simulation failure occurred.

The continuation recorded 4,503 complete attempts, 2,785 face-contact episodes, 11 net crossings and 9 legal returns. Training uses exploration; these counts do not measure deterministic deployment reliability.

The final exported policy was tested on the same two development cohorts as the pilot:

| Fixed evaluation | Face-contact episodes | Net crossings | Legal returns |
|---|---:|---:|---:|
| Easy, 32,786 steps | 128/128 | 0/128 | 0/128 |
| Easy, longer run | 128/128 | 0/128 | 0/128 |
| Original feed, 32,786 steps | 70/128 | 0/128 | 0/128 |
| Original feed, longer run | 67/128 | 0/128 | 0/128 |

Contact can precede a later fault, so it is not an additional terminal outcome category. Detailed terminal outcomes and checkpoint hashes are preserved in paired-evaluation.json under artifacts/player-v3/easy-return-bc-resume-02. Both new Unity evaluations matched their pinned PyTorch checkpoint within 1.79e-07, with exact physical action mapping.

Rare successful training exploration is evidence that the learner can discover a legal return in this drill. The frozen results determine whether it has learned to repeat it reliably. This experiment does not establish natural biomechanics, serving, rallies or accepted 2v2 play. Final evaluation seeds remain untouched. The run is completed; TensorBoard history remains available on port 6007.


Longer fixed-setup training results — 8 September 2026

The PPO continuation completed at 393,233 total easy-return trainer steps (24,622 additional experiences), on eight concurrent drill arenas. Each arena trains one learner, with seats rotating between episodes; the four-player game still uses four independent observations/actions with shared policy weights. The task, reward, constraints and optimizer settings stayed unchanged. Actor, normalizer, critic and Adam state resumed from the validated 368,611-step checkpoint after a power interruption. The interrupted continuation and its surviving episode records are preserved separately; unknown partial episodes are not reconstructed. The source and archived pre-continuation trainer files were hash-verified, and no simulation failure occurred.

The continuation recorded 773 complete attempts, 652 face-contact episodes, 303 net crossings and 229 legal returns. Training uses exploration; these counts do not measure deterministic deployment reliability.

The final exported policy was tested on the same two development cohorts as the pilot:

| Fixed evaluation | Face-contact episodes | Net crossings | Legal returns |
|---|---:|---:|---:|
| Easy, 131,124 steps | 128/128 | 0/128 | 0/128 |
| Easy, longer run | 126/128 | 60/128 | 35/128 |
| Original feed, 131,124 steps | 67/128 | 0/128 | 0/128 |
| Original feed, longer run | 53/128 | 18/128 | 9/128 |

Contact can precede a later fault, so it is not an additional terminal outcome category. Detailed terminal outcomes and checkpoint hashes are preserved in paired-evaluation.json under artifacts/player-v3/easy-return-power-recovery-04. Both new Unity evaluations matched their pinned PyTorch checkpoint within 2.98e-07, with exact physical action mapping.

Rare successful training exploration is evidence that the learner can discover a legal return in this drill. The frozen results determine whether it has learned to repeat it reliably. This experiment does not establish natural biomechanics, serving, rallies or accepted 2v2 play. Final evaluation seeds remain untouched. The run is completed; TensorBoard history remains available on port 6007.
