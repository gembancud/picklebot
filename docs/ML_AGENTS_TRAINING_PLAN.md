ML-Agents migration and training evidence — 8 September 2026

Use Unity ML-Agents for reinforcement learning. The project now has a working, verified framework connection and exported inference. Successful pickleball learning and playable 2v2 remain the next outcomes to demonstrate.

PPO is the initial drill trainer. MA-POCA with self-play is now a verified team trainer: four Agent instances, one shared Behavior Name, two opposing Team IDs, and a separate cooperative group for each pair on each court. The team critic is used during training; each player chooses its own actions from its own observations. Unity's SoccerTwos example is the closest structural reference. [Agent/team design](https://docs.unity3d.com/Packages/com.unity.ml-agents@4.1/manual/Learning-Environment-Design-Agents.html#defining-multi-agent-scenarios), [SoccerTwos](https://docs.unity3d.com/Packages/com.unity.ml-agents@4.1/manual/Learning-Environment-Examples.html#soccer-twos).

| Component | Installed and verified |
|---|---|
| Unity | Editor 6000.5.5f1; official Unity CLI |
| Learning SDK | com.unity.ml-agents 4.1.0 |
| Python packages | mlagents and mlagents-envs 1.2.0.dev0 from the matching, pinned 4.1 source revision |
| Environment | Separate locked Pixi environment; Python 3.10.12, NumPy 1.23.5 |
| Compute | PyTorch 2.8.0+cu126; real Adam update verified on RTX 4070 |
| Deployment | Framework ONNX running through Unity Inference Engine |

The matching source revision is `ee0a08ccae597094003844d0121317f9790a1676`. The documentation's installation examples include older Python package/release references, so the source revision and dependency lock are recorded explicitly. Unity and Python package version numbers differ. [Pinned release requirements](https://github.com/Unity-Technologies/ml-agents/blob/ee0a08ccae597094003844d0121317f9790a1676/ml-agents/setup.py).

The legacy Python environment and historical custom checkpoints are preserved. The framework comparison starts with a fresh actor because the old JSON actor uses a different network and action distribution. It is not an exact weight conversion.

The integration keeps the existing articulated body, fixed grip, joint limits, paddle limits, physical ball contacts and rules. Its interface is 124 observations, 16 continuous controls and one binary release decision. Jump remains disabled under the current grounded-body contract. Ball release is masked when unavailable. Physics runs at 240 Hz, decisions at 20 Hz, with the existing 25 ms action delay. The framework performs sampling, advantage calculation, optimization and checkpointing. Project code provides the simulation, observations, physical action mapping, rewards and episode lifecycle.

Validation completed:

- The unchanged upstream Ball3DAgent trained in an isolated procedural fixture and resumed from 36,015 to 72,009 steps. This verifies the framework independently of Picklebot; it is not pickleball skill evidence.
- All 226 Editor tests passed after the SDK integration. All three bridge Play Mode tests passed, including body/ball parity with the original control path, action boundaries, terminal observations and seat rotation. Three previously recorded tests for older scripted game/return paths remain separate known failures.
- All three Picklebot exports matched their PyTorch checkpoint on every captured held-out decision. Maximum continuous-action error across all three evaluated exports was below 9e-8; physical mapping error was zero.
- A separate offline check loaded the PPO actor and normalization tensors strictly into the actual MA-POCA policy construction. Its outputs matched exactly on 1,534 recorded observations with matched random samples. The MA-POCA critic, optimizer and step counter were initialized separately. Live group training, team switches and full checkpoint continuation subsequently passed; see the dated team integration update below.

The first Picklebot run completed 2,002 episodes and reached 24,589 trainer steps. It performed 48 Adam minibatch updates. The baseline checkpoint had zero optimizer updates, with running observation statistics already collected. On the same 128 held-out contact drills:

| Outcome | Before optimization | After short PPO run |
|---|---:|---:|
| Paddle-face contact | 46/128 | 47/128 |
| Body or handle contact | 14/128 | 11/128 |
| Miss | 68/128 | 70/128 |

This small difference does not establish useful learning. Contact drills end at the first paddle-face contact, so these results do not measure legal returns or serves. The PPO continuation is now complete. It preserved the actor, critic, normalizer and Adam state, used fresh reserved training seeds, and added 8,472 completed episodes. It reached 131,080 total trainer steps and 336 total Adam minibatch updates. The continuation took approximately 15.4 minutes, including startup. Eight additional episodes were partial at shutdown and are recorded separately. All prior numbered checkpoints remain unchanged.

On the same 128 held-out seeds, the continued checkpoint produced **57 paddle-face contacts, 1 body/handle contact, and 70 misses**. The original baseline produced 46 contacts, 14 body/handle contacts, and 68 misses. Contact improved from 35.9% to 44.5%, and body/handle faults fell from 10.9% to 0.8%. This is encouraging early improvement from one training lineage on one development cohort. Contact remains unreliable, and this task does not test legal returns or serves.

The evaluation ran without a Python trainer and all 1,528 recorded decisions passed the Unity/PyTorch parity check. A CLI return-value error occurred while the Editor switched to Play Mode; inspection confirmed that evaluation had started and subsequently completed all 128 episodes successfully. It was not restarted or silently replaced.

Training should advance through reachable contact, legal short returns, wider feeds, learned drop serves, cooperative rallies, then competitive 2v2. Reset/feed distributions and task rewards define the drills; the policy must choose movement, joint motion, paddle orientation, swing timing and release. No stroke or serve controller supplies the learner's actions. Advancement should depend on held-out task success and observed behavior. Observation stacking, recurrence, larger networks and other algorithms should be controlled comparisons when measured failures justify them. [Training configuration](https://docs.unity3d.com/Packages/com.unity.ml-agents@4.1/manual/Training-Configuration-File.html), [Curriculum](https://docs.unity3d.com/Packages/com.unity.ml-agents@4.1/manual/Training-ML-Agents.html#curriculum).

Simultaneous team trajectories, group rewards, framework resets and snapshot-based self-play now have live integration evidence. Remaining work includes reliable learned skills, a longer opponent curriculum, an executable throughput benchmark, full evaluation protocol coverage and visible evaluation of learned movement. Passing constraints establishes compliance with our implemented body limits; it does not establish complete or anatomically validated biomechanics.

Final acceptance criteria and final evaluation seeds remain untouched. No framework model has been promoted into the original playable scene. Unity has been restored to `IndependentPlayers.unity`, out of Play Mode, with no unsaved scene changes or compilation errors. No trainer is left running.

Evidence in `F:/dev/picklebot`:

- `artifacts/player-v3/mlagents-integration-01/`: environment, sample/resume verification, bridge tests, first paired comparison.
- `artifacts/player-v3/mlagents-drill-01/`: initial physical episodes, source archive and checkpoint verification.
- `artifacts/player-v3/mlagents-before-dev-01/` and `mlagents-after-dev-01/`: held-out episodes, decisions and inference verification.
- `artifacts/player-v3/mlagents-drill-resume-01/`: completed continuation, source archive, checkpoint verification and pre-resume evidence.
- `artifacts/player-v3/mlagents-resumed-dev-01/`: continued-model held-out episodes, decisions and inference verification.
- `artifacts/player-v3/mlagents-integration-01/poca-actor-transfer/`: strict actor-transfer compatibility check and untrained MA-POCA candidate; not a promoted gameplay checkpoint.
- `artifacts/mlagents/articulated-drill-01/`: framework checkpoints and TensorBoard events.
- `tools/mlagents-training/`: pinned source metadata and Pixi manifest/lock. `scripts/setup_mlagents.py` reproduces this environment; `scripts/mlagents_verify.py` verifies it.

The next training milestone is reliable learned contact and legal return skill, with retained checkpoints and held-out comparisons. The team adapter is now verified for short training and continuation runs; competitive skill and full-game acceptance remain unproven. A larger training budget alone does not establish that the task or body is sufficient.


Team integration update — 8 September 2026


The MA-POCA/self-play pipeline now runs and resumes successfully with two simultaneous 2v2 courts. Each of the eight players has its own observation/action state. Four players on the current learning side contribute experience to a shared policy; four checkpoint opponents supply competition. The framework alternates learning teams. The earlier completed drill continuation used eight courts with one active learner per court.

The actor starts from the preserved 131,080-step PPO contact checkpoint. Its actor and observation normalizer transferred strictly into MA-POCA, with a fresh team critic and optimizer. The successful team run reached 2,128 steps and 42 Adam minibatch updates. A separate continuation preserved actor, normalizer, critic, optimizer and step state, then reached **4,268 steps and 84 total updates**. Both actor and critic weights changed, remained finite, and exported valid ONNX files. ONNX validity here is a structural check; these new team exports have not yet received the earlier drill exports' Unity/PyTorch inference parity evaluation.

| Verification | Result |
|---|---|
| Editor regressions | 231/231 passed after the physical fix |
| ML-Agents bridge, team, reset and shutdown regressions | 11/11 passed |
| Successful initial team run | 2,128 trainer steps; 2 framework resets |
| Full continuation | 2,140 additional steps; 3 framework resets |
| Continuation physical work | 12,954 physics ticks across two courts; 4,360 actor decisions |
| Continuation game accounting | 8 started; all 8 recorded incomplete; no completed games |
| Legal serves / non-serve hits | 0 / 0 |

Three environment problems were corrected:

- A root collision with the lab enclosure could stop the body too abruptly for the arm's existing acceleration limits. A simple backward movement reproduced failure at tick 43. The articulated locomotion path now reserves braking distance before the enclosure wall, including a shared acceleration budget at corners. Both court-end regressions sustain 1,200 ticks while checking root acceleration, paddle acceleration and speed. The rigid contact solver remains in place. This does not prove every future body collision or action sequence feasible.
- Self-play switches cause a full Academy reset. The old adapter retained its physical court clock after the SDK cleared agent commands. The owner now discards that reset's action batch before physics, records unfinished courts and starts fresh allocated games. A test injects the real Academy reset during decision processing.
- Shutdown now records every unfinished court without emitting extra policy rewards. The earlier successful run has two partial shutdown courts without individual snapshots (14 aggregate physics ticks); its original evidence is preserved with that limitation. The continuation has complete per-game accounting.

The policy still selects movement, torso/arm/wrist targets, swing timing, paddle orientation and release. The interface remains 124 observations, 16 continuous controls and one binary release action; physics is 240 Hz, decisions are 20 Hz, and actuation delay is 25 ms. The bounded wall response uses no ball input and supplies no stroke or serve sequence. Joint ranges, grip, paddle speed and acceleration limits were not increased.

These short runs verify training infrastructure, not playable pickleball. Rewards mostly came from faults/timeouts, and no legal serve or return was observed. The four-rally game cap and frequent team switches were integration-test settings. Full training and acceptance must use the intended longer game limits, independent held-out evaluations, partner/end coverage and the frozen game-based criteria. Training Elo here is rally Elo.

Next work is to improve learned contact and legal returns with the parallel drill fleet, add learned release/serve practice, and evaluate the resulting policies before substantial competitive training. The last held-out contact checkpoint achieved 57/128 paddle-face contacts; reliable rallies remain unproven. Larger fleets and executable throughput need measured benchmarks. Per-player observations/actions are independent; independently seeded framework sampling streams are not claimed.

All historical source runs and checkpoints remain preserved. Final evaluation seeds are untouched. No new model was promoted into the playable scene. Unity is restored to IndependentPlayers.unity, out of Play Mode, without unsaved changes or compilation errors. Both successful trainer processes exited with code 0.

Evidence under F:/dev/picklebot:

- artifacts/player-v3/enclosure-braking-01/: original wall failure, constrained feasibility search, source backups and Editor/bridge test results.
- artifacts/player-v3/team-reset-01/: reset/shutdown source backups and final 11-test result.
- artifacts/player-v3/mlagents-teams-smoke-01/: original physical failure, captured joint state and source archive.
- artifacts/player-v3/mlagents-teams-smoke-02/: preserved framework reset failure after initial updates.
- artifacts/player-v3/mlagents-teams-smoke-03/: successful first team run and training-verification.json.
- artifacts/player-v3/mlagents-teams-resume-04/: full resume, source archive, game/rally records, training-verification.json and final-editor-state.json.
- artifacts/mlagents/team-bridge-resume-04/: latest checkpoint and ONNX, including preserved copied numbered checkpoint history.

Latest source identity: b7128c6a270143394c0f30f4dca5c0b026e1236e9d75d4ced9394ba9b272d266.
Latest checkpoint SHA-256: 9cd4756fabc228caf46b3ab7457b9d027da83818d3cdfd3f7d90640e649f45fe.
Latest ONNX SHA-256: 90999d06e9dbfadf81e9da60437fa147769fdc670d513fcee43c01bf501fb370.


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


The next unchanged PPO continuation is running from step 131,124 toward 393,216 on eight drill courts. The full checkpoint and optimizer were resumed, and the pre-continuation trainer directory is preserved and hash-verified. Only the duration changes in the trainer configuration; fresh training seeds 1073072–1089455 are reserved. Startup confirmed trainer connection and new decisions with no simulation failure. The two frozen development cohorts will be repeated after completion; final evaluation seeds remain untouched. TensorBoard continues on port 6007. Evidence: artifacts/player-v3/easy-return-bc-resume-03.
Actual learned-action capture — 8 September 2026

A bounded observer recorded 512 complete attempts from the active easy-return PPO continuation. It copied each learner's observations, continuous controls and physical commands after the framework delivered the action. It did not request decisions, supply actions, change rewards or step physics. It detached after the requested sample. Logging may affect wall-clock throughput, so this interval should not be treated as an uninstrumented performance benchmark.

The sample includes 42 legal returns, 311 bad returns, 106 misses, 43 body/handle faults and 10 other rule terminals. All four player seats are represented (127–129 attempts each). These are actual exploratory training trajectories under changing policy weights, not a frozen-policy evaluation or proof of reliable gameplay.

All 13,983 decision records passed identity, observation/action shape, finite-value, 12-tick decision timing and physical mapping checks. Every terminal record matches the authoritative training log, including exact single-precision reward bits. The two serializers use different decimal representations of those same float values. Eight attempts already in progress when recording started were excluded, and eight partial attempts remained when the observer stopped.

The exact records and hashes are preserved under artifacts/player-v3/easy-return-bc-resume-03/action-capture-01. They are ready for physical replay after the active training run and frozen policy evaluations finish. Replay equivalence and natural movement have not yet been verified. The active training setup remains unchanged, and final evaluation seeds remain untouched.


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


Optional practice-court decision batching â€” 8 September 2026

All five bridge tests passed, including a paired four-court test across twelve episode resets. The new scheduler pauses only after an attempt has finished, until the next common decision boundary. It does not advance physical time during that wait. The player's 20 Hz decision rate and six-tick reaction delay are unchanged. Existing scenes retain the legacy schedule unless the new option is explicitly enabled.

The 393,233-step learned policy was evaluated on the same 128 easy feeds with eight courts under both schedules. Both produced 35 legal returns, 91 bad returns and two misses. All 4,428 decisions and 52,413 physical ticks matched, with maximum observed-state/action differences 0. Terminal records matched exactly.

Decision request groups fell from 3,241 to 569, a 82.4% reduction. Average requests per group increased from 1.37 to 7.78. This reduces fragmented inference requests; it is not yet an end-to-end training speedup measurement. A new training interval must measure that separately. Stochastic sample ordering can change with batch composition.

Evidence and immutable source archives: artifacts/player-v3/aligned-drill-scheduler-01. No final evaluation seeds were used. Learned returns remain incomplete, and full 2v2 acceptance is still outstanding.


The next training interval is running on eight aligned courts from checkpoint 393,233 toward 524,288. Actor, observation normalizer, critic and Adam state resumed from the verified checkpoint. Previous trainer files are archived before mutable continuation. Training seeds 1093552â€“1099695 are reserved, with final seeds untouched.

A live 89.45-second sample processed 19,712 decisions at 220.4 decisions per second, with exactly eight requests per batch. The earlier operational sample measured 126.9 decisions per second. The observed rate ratio is 1.74Ã—; because these samples use different training intervals and checkpoints, this is not an isolated causal speedup benchmark. The separate frozen test establishes that batching preserves the tested physical trajectories and outcomes. Evidence: artifacts/player-v3/easy-return-aligned-resume-05/operational-throughput.json.


Learned-return training through 524,319 steps — 8 September 2026

The aligned eight-court PPO continuation completed from checkpoint 393,233 to 524,319, adding 131,086 trainer experiences. Actor, observation normalizer, critic and optimizer state were resumed. Source, parent checkpoint and archived trainer history were verified. The physical controls, decision/reaction clocks, reset feeds, rewards and optimizer hyperparameters stayed unchanged; only inter-episode scheduling and the training duration changed. The scheduler's separate paired test reproduced all 128 tested trajectories exactly while reducing fragmented decision-request groups.

Frozen deterministic policy evaluations:

| Feed cohort | At 393,233 steps | Latest checkpoint |
|---|---:|---:|
| Easy return | 35/128 | 57/128 |
| Original harder return | 9/128 | 6/128 |

Latest results by independently controlled player seat:

| Seat | Easy legal returns | Harder legal returns |
|---|---:|---:|
| Player 1 | 11/32 | 2/32 |
| Player 2 | 15/32 | 3/32 |
| Player 3 | 18/32 | 0/32 |
| Player 4 | 13/32 | 1/32 |

The latest easy-feed outcomes were {"bad_return": 71, "legal_return": 57}; harder-feed outcomes were {"body_or_handle": 23, "bad_return": 42, "miss": 50, "rule_terminal": 7, "legal_return": 6}. Both exports matched their pinned PyTorch checkpoint within 3.58e-07, with exact physical action mapping. Counts above are outcomes under a fixed policy, not training reward estimates.

The completed training interval recorded 3,955 full attempts and 1,436 legal returns during exploration. Partial attempts remain accounted for separately. Each drill court has one active learner, with seats rotating across attempts; the intended full game has four independent players sharing policy weights. Reliable serving, rallies and full 2v2 acceptance remain unproven. Final evaluation seeds remain untouched.

Detailed provenance: artifacts/player-v3/easy-return-aligned-resume-05 and the two easy-return-524k development evaluation directories. The power-interrupted earlier run and recovery evidence remain preserved.


Varied return curriculum — 8 September 2026

The next PPO continuation is running from checkpoint 524,319 toward 655,360, using eight aligned practice courts. Each court has one active learner; attempts rotate among all four independent player seats sharing weights. The full actor, observation normalizer, critic and Adam state were copied to a separate run (`varied-return-01`) and resumed. The original easy-return trainer directory remains preserved.

This stage samples reset feeds between the previous easy and original near-return distributions. There is a 25% probability of an unchanged easy feed; otherwise an interpolation parameter is sampled uniformly from 0 to 0.5. Ball placement spread, starting distance and estimated flight duration change only at reset. No swing trajectory, paddle target, hit impulse or serve command is supplied to the policy. The easy-return capped post-contact progress reward remains. These interpolation parameters are not a guarantee of monotonic difficulty for a particular policy.

Five physical drill tests and five ML-Agents bridge tests passed. Checks include reproducible feeds, the first reaction window, easy-endpoint physical trajectory/reward equivalence, near-endpoint reset equivalence, private observations, delayed actions and failure handling. They do not prove full human biomechanics or rally competence.

Before training, the frozen 524,319 policy returned 79/128 feeds legally in the new intermediate development cohort. This is a different feed distribution from the fixed easy/harder cohorts, so its higher success rate is not a training improvement. Per-seat results: {"0": {"episodes": 32, "legalReturns": 12}, "1": {"episodes": 32, "legalReturns": 19}, "2": {"episodes": 32, "legalReturns": 25}, "3": {"episodes": 32, "legalReturns": 23}}. Unity actions matched the PyTorch checkpoint within 2.38e-07; physical action mapping was exact.

The bounded continuation deliberately reuses training-only seed integers 1000000..1008191 under the new varied-return task; these are not claimed fresh. Existing allocations and evidence remain preserved. Development seeds 1100897..1101024 are newly reserved for the fixed intermediate comparison. Final evaluation seeds remain untouched.

Current metrics: http://127.0.0.1:6008/ . The older dashboard remains available on port 6007. After completion, compare the frozen candidate against checkpoint 524,319 on all three fixed cohorts: easy, original near-return and intermediate. Serving, sustained rallies and accepted 2v2 remain unresolved.

Evidence: artifacts/player-v3/varied-return-contract-01, varied-return-524k-before-dev-01 and varied-return-train-01. Current trainer: artifacts/mlagents/varied-return-01.


Varied-return checkpoint comparison — 8 September 2026

The eight-court PPO continuation completed at 655,362 experiences, adding 131,043 to checkpoint 524,319. It retained the physical body, decision clocks and learned action interface, and changed the reset-feed distribution to include easy anchors and intermediate feeds. Full actor, normalizer, critic and Adam continuity was verified. The parent trainer directory remains byte-for-byte preserved.

Frozen deterministic comparisons use the same seed/player pairs within each feed cohort. Counts are actual legal landings, not contact bonuses or training reward.

| Cohort | Before | After | Newly successful seeds | Previously successful seeds now failing |
|---|---:|---:|---:|---:|
| Easy | 57/128 | 63/128 | 31 | 25 |
| Original harder | 6/128 | 8/128 | 4 | 2 |
| Intermediate | 79/128 | 81/128 | 20 | 18 |

Legal returns per seat, before → after (32 attempts per seat):

| Cohort | Player 1 | Player 2 | Player 3 | Player 4 |
|---|---:|---:|---:|---:|
| Easy | 11 → 24 | 15 → 19 | 18 → 13 | 13 → 7 |
| Original harder | 2 → 2 | 3 → 2 | 0 → 0 | 1 → 4 |
| Intermediate | 12 → 21 | 19 → 21 | 25 → 20 | 23 → 19 |

All three Unity exports passed comparison with their pinned PyTorch checkpoint and physical action mapping. This is one training lineage and three development cohorts; it is not a multi-seed robustness study. The interpolation parameter controls feed generation, and is not guaranteed to be monotonically harder for this policy.

Training recorded 4,228 complete attempts, plus 8 partial attempts at shutdown; partial physical time remains accounted for. Serving, sustained rallies, full-court coverage, baseline comparison and accepted 2v2 remain outstanding. Final seeds were not used.

Evidence: artifacts/player-v3/varied-return-train-01 and the three varied-return-655k development directories.


Serve probe and next training decision

The frozen 655,362 checkpoint was tested from all four starting server seats. Every attempt reached its five-second drill limit without releasing the ball: 0/4 releases, accepted serves or legal serves. All 400 release decisions were available (unmasked) and selected hold. Unity/PyTorch parity passed within 2.98e-7. These are four deterministic initial positions; the serve reset does not vary with seed, so this is not a randomized generalization benchmark. The recorded maximumReturnDifficulty setting has no effect on drop-serve tasks.

The return evaluations improved only modestly in aggregate: easy 57→63/128, original harder 6→8/128, intermediate 79→81/128. Easy performance moved unevenly across seats: 11→24, 15→19, 18→13, 13→7. Of the 57 previously successful easy cases, 25 now fail, offset by 31 newly successful cases. No broad retention or robust improvement claim is warranted.

Next implementation: mix learned drop-serve practice with the existing return practice, retaining shared policy weights and four independent actors. Release masks must follow each actual drill task, and episode evidence must record that task, so serve practice cannot be accidentally masked off by an overall curriculum label. Preserve legal-serve success as the measured outcome; release/drop bonuses remain bounded exploratory feedback. The actor must still choose release timing and body/swing controls. Repeat fixed return cohorts to measure forgetting, and inspect serve outcomes before substantial self-play.

Unity now has a separate saved intermediate-return preview: Assets/Picklebot/Scenes/ArticulatedVariedReturnPreview655k.unity, using After655kVariedReturnTraining.onnx. Training has stopped cleanly and saved its final checkpoint. This preview is not the accepted full 2v2 scene.


Mixed serve and return training — 8 September 2026

The next standard PPO continuation is running from checkpoint 655,362 toward 786,432. The complete actor, observation normalizer, critic and Adam state were copied and resumed in a distinct `mixed-practice-01` trainer directory, preserving the previous run.

Eight aligned courts now alternate blocks of four drop-serve starts and four varied-return starts. Every seat receives both tasks under the same policy weights. Episode starts are balanced; experience counts are not, because task durations differ. Actual drill task controls the release mask and recorded task label. Existing single-task resets, rewards, body limits and clocks remain unchanged. No release time or swing sequence is prescribed to the learner.

Six ML-Agents integration tests passed, including a fixture that explicitly sends release commands to verify masks, delayed physical actuation, task/seat coverage and episode accounting. That fixture is confined to tests. A frozen 16-attempt mixed-fleet baseline also matched the pinned PyTorch checkpoint within 2.98e-7 and exact physical action mapping; it showed eight held-ball serve timeouts and three legal returns among eight return attempts. This is an integration baseline, not a generalization estimate.

The live exploration snapshot contains:

{
  "drop-serve": {
    "episodes": 172,
    "decisions": 16794,
    "outcomes": {
      "time_limit": 163,
      "body_or_handle": 9
    },
    "released": 140,
    "dropBounced": 134,
    "bySeat": {
      "0": 43,
      "1": 43,
      "2": 43,
      "3": 43
    }
  },
  "varied-return": {
    "episodes": 176,
    "decisions": 5930,
    "outcomes": {
      "bad_return": 77,
      "legal_return": 71,
      "miss": 10,
      "rule_terminal": 2,
      "body_or_handle": 16
    },
    "released": 176,
    "dropBounced": 0,
    "bySeat": {
      "0": 44,
      "1": 44,
      "2": 44,
      "3": 44
    }
  }
}

Release and drop bounce are intermediate milestones, not successful serves. The final policy must be evaluated separately. TensorBoard at http://127.0.0.1:6008/ now displays both varied-return and mixed-practice runs; task-specific metric names separate drop-serve progress from varied-return results. Historical event files copied into the new run precede the new 655,362-step stage and must not be interpreted as mixed-practice training.

Training-only integers 1008192..1016383 are deliberately reused under this curriculum and recorded as reused. Development and final seeds are excluded from optimizer input. After the bounded continuation, repeat fixed easy, near-return, intermediate and four-position serve probes against checkpoint 655,362, including each seat's results. Full 2v2, serving and sustained rallies remain unproven.

Evidence: artifacts/player-v3/mixed-practice-contract-01, mixed-practice-655k-before-dev-01 and mixed-practice-train-01.


Mixed-practice checkpoint comparison — 8 September 2026

The PPO continuation completed at 786,481 experiences, adding 131,119. Full checkpoint/optimizer continuity, finite model state, source identity and unchanged parent trainer files passed verification. It alternated serve and return starts across all seats, using existing task rewards and unchanged body controls. Release timing and swing remained policy decisions.

Frozen deterministic legal-return outcomes:

| Feeds | Before at 655,362 | After |
|---|---:|---:|
| Easy | 63/128 | 73/128 |
| Original harder | 8/128 | 2/128 |
| Intermediate | 81/128 | 93/128 |

Legal returns by seat, before → after (32 attempts each):

| Feeds | Player 1 | Player 2 | Player 3 | Player 4 |
|---|---:|---:|---:|---:|
| Easy | 24 → 13 | 19 → 15 | 13 → 26 | 7 → 19 |
| Original harder | 2 → 0 | 2 → 1 | 0 → 1 | 4 → 0 |
| Intermediate | 21 → 23 | 21 → 22 | 20 → 25 | 19 → 23 |

The four-position serve probe changed from 0/4 releases and 0/4 legal serves to 4/4 releases, 0/4 paddle-face contacts and 0/4 legal serves. New outcomes: {"time_limit": 4}. These are four deterministic initial positions, not a randomized serve-generalization study.

All four recorded Unity evaluations passed pinned PyTorch action parity and exact physical action mapping. One lineage and small development cohorts do not establish robustness or full 2v2 acceptance. Training exploration totals are separated by task in training-verification.json; partial episodes and their physical time remain recorded.

The unchanged gamma=0.99 weights a terminal -1 at decision 100 by about -0.370 at the start, versus -0.826 at decision 20. This isolated terminal calculation excludes shaping and critic estimates; it suggests a timing incentive to investigate, not a proven explanation of policy behavior. See terminal-timing-diagnostic.json. No reward or discount change was made during this run.

Reliable serving, sustained rallies, full-court coverage and accepted independent-player 2v2 remain outstanding. Final evaluation seeds were not used.

Evidence: artifacts/player-v3/mixed-practice-train-01 and the four mixed-practice-786k evaluation directories.


Serve reach diagnosis and next step

The frozen policy now commands release at observation tick 0 in all four positions. At the closest sampled post-bounce state, ball-to-paddle-origin separation remains approximately 0.870–0.870 m. In the canonical root-relative frame, the ball is about 0.20 m left and 0.43 m high, while the paddle origin is 0.31 m right and 1.11 m high. These 20 Hz samples explain where the observed policy misses; they do not prove the ball is unreachable by the constrained body or measure continuous closest-face separation.

Before another long unchanged run, verify low drop-bounce reachability with the current body and grip limits, using existing physical fixtures where possible. Then isolate a curriculum/reward experiment that rewards learning the missing low contact while retaining full legal-serve evaluation and return practice. The discount timing asymmetry is a separate hypothesis to test. Avoid changing several factors at once or prescribing runtime swing/release actions. Harder-return retention regressed (8→2/128), so increased easy/intermediate performance cannot justify promotion as an overall game policy.

Unity has a saved diagnostic preview at Assets/Picklebot/Scenes/ArticulatedMixedPracticePreview786k.unity. It shows four learned serve attempts, then four learned intermediate-return attempts, repeated once. It is a saved-policy practice preview, not live training or the accepted 2v2 game. The trainer exited cleanly and no continuation is currently running.


Low drop-contact feasibility — 8 September 2026

The current constrained body can contact its dropped ball. An isolated physical search produced 15 paddle-face contacts in 27 tested constant-command trajectories. All contacts followed a real drop bounce and had accepted serve contact rules. None produced a legal service-box landing; 15 ended in bad returns and 12 timed out. No trial had a body solver failure.

A half-crouch candidate repeated actual contact at all four player positions. The new permanent regression executes the fixed candidate through the normal private policy loop, 20 Hz decisions, six-tick actuation delay, bounded body motion and real ball physics. It checks release at tick 7, post-bounce contact, accepted serve motion and paddle speed limits. All five serve lifecycle/physical tests passed.

The geometric solver selected a fixed target before each diagnostic trial; no solver drives the learner. Successful contact occurred in sampled half/full-crouch candidates. These results show existence of a reachable trajectory, not exhaustive reachability, natural human biomechanics, or learned serving. The earlier V2 scripted serve was not used. No paddle limit, joint limit, ball impulse, runtime learner command, training checkpoint or reward was modified, and no fixture commands were used as training demonstrations.

The 786,481 policy still has zero serve contacts in its frozen probe; its sampled paddle-to-ball separation stayed around 0.87 m after the bounce. That is a learned positioning gap for the tested reset, rather than evidence that the body must be relaxed. The next curriculum can isolate actual drop-bounce contact before requiring the full legal landing, retaining return practice and separate full-serve evaluation. The discount-timing diagnostic remains a separate hypothesis; it does not establish the cause of the missing skill.

All audit seeds are in the interactive range 1301000..1301063, excluded from optimizer input and final acceptance. Evidence and archived source: artifacts/player-v3/drop-reach-audit-01. The shared-policy 2v2 objective remains incomplete.


# Contact and return continuation — 8 September 2026

Unity was already open on the saved 786k preview. The previous 786,481-step checkpoint survived and matches its recorded SHA-256. That stage completed cleanly; no damaged or speculative checkpoint recovery was needed.

Standard ML-Agents PPO is now continuing from 786,481 toward 917,504 experiences in `drop-contact-01`, with the complete actor, normalizer, critic and Adam state copied from the preserved parent. Eight aligned courts rotate all four player seats through drop-contact and varied-return practice using shared weights. Each court has one active learner for its drill. This is not simultaneous four-player match training yet.

The new `drop-contact` task ends at a real accepted paddle-face contact after the policy releases the held ball and it bounces. It is recorded as `serve_contact`; the unchanged `drop-serve` evaluation still requires a legal service-box landing. A post-bounce closest-distance bonus is capped at 0.5 per attempt and cannot be repeated by retreating. Existing release/bounce bonuses remain 0.05 each. Before-bounce proximity receives no bonus in this new task. Its terminal reward is +1 for valid contact, -1 for failure. Return rewards, body limits, action timing, architecture and PPO gamma remain unchanged. This is a combined contact-curriculum experiment, not an isolated coefficient comparison.

The policy still selects every body, paddle and release action. No feasibility command or preview stroke was installed in the learner or supplied as demonstrations. Fifteen targeted tests passed: three contact/bonus tests, seven fleet integration tests and five existing serve tests. The physical test shows that the contact milestone and full serve task follow the same trajectory through contact, then correctly distinguish contact from a failed landing.

The frozen 786k baseline on the new fleet has 8 drop-contact timeouts, 7 legal returns and 1 body/handle failure in 16 attempts. The eight drop attempts repeat the four deterministic serving positions; they are not eight randomized serve situations. All 1,091 recorded decisions matched the pinned PyTorch actor within 2.98e-7, with exact physical action mapping.

Live training startup snapshot (exploration, not a frozen evaluation):

```json
{
  "drop-contact": {
    "episodes": 232,
    "decisions": 22917,
    "outcomes": {
      "time_limit": 229,
      "body_or_handle": 3
    },
    "released": 232,
    "dropBounced": 229,
    "bySeat": {
      "0": 58,
      "1": 58,
      "2": 58,
      "3": 58
    }
  },
  "varied-return": {
    "episodes": 236,
    "decisions": 7293,
    "outcomes": {
      "body_or_handle": 37,
      "legal_return": 94,
      "bad_return": 81,
      "miss": 20,
      "rule_terminal": 4
    },
    "released": 236,
    "dropBounced": 0,
    "bySeat": {
      "0": 59,
      "1": 59,
      "2": 59,
      "3": 59
    }
  }
}
```

Watch the selected live court in Unity's Scene view through Window > Picklebot > Training Monitor. Its Watch speed button slows presentation while all courts continue learning. TensorBoard: http://127.0.0.1:6008/?darkMode=true#timeseries&regexInput=Picklebot . Select the drop-contact run; useful metrics include Picklebot/drop-contact/ServeContact, Released, DropBounced and Picklebot/varied-return/LegalReturn. Copied historical curves below step 786,481 belong to earlier curricula.

After this bounded stage, evaluate the frozen export on the paired contact fleet, all four full serve positions, and the existing easy, near and varied-return probes, including each seat's retention. More shaping reward alone will not demonstrate better serving. Full 2v2 and sustained rallies remain unproven. Development and final seeds are excluded from optimization; training-only integers 1016384..1024575 are explicitly recorded as reused. No final acceptance seeds consumed.

Evidence: artifacts/player-v3/drop-contact-contract-01, drop-contact-786k-before-dev-01 and drop-contact-train-01. Source identity: 7454caa3c88b66c81f7f995ac9884dd04fc0cc60b01b76409c143c398a502307.


# Contact curriculum result — 917,565 steps

This bounded PPO continuation completed, but it did not teach the missing drop contact. There were zero contacts in 1,005 exploratory drop attempts. 1,005 releases and 997 drop bounces were observed. The return practice produced 417 legal returns during exploration; those are not a frozen-policy success rate.

The frozen exported policy was compared on the same development conditions as checkpoint 786,481:

| Probe | Before (786,481) | After (917,565) |
|---|---:|---:|
| Easy returns | 73/128 | 84/128 |
| Harder near returns | 2/128 | 11/128 |
| Intermediate varied returns | 93/128 | 97/128 |
| Legal serve landings | 0/4 | 0/4 |
| Valid drop contacts | 0/8 | 0/8 |


Per-seat successes after training (seats 0, 1, 2, 3):

- Easy returns: 24, 14, 31, 15.
- Harder near returns: 1, 2, 5, 3.
- Intermediate varied returns: 22, 24, 29, 22.
- Legal serve landings: 0, 0, 0, 0.
- Valid drop contacts: 0, 0, 0, 0.

The pooled return totals improved, but retention is uneven: easy-return seats 1 and 3 declined (15 to 14 and 19 to 15), while intermediate-return seats 0 and 3 each lost one success. Body/handle failures increased from 0 to 4 in easy returns, 31 to 36 in near returns, and 6 to 14 in intermediate returns. The small mixed-fleet return subset fell from 7/8 to 6/8. These regressions remain part of the result; the policy is not promoted as an overall game solution.

Serve probes cover four deterministic starting positions, not randomized generalization. The contact fleet repeats each position twice. The intermediate return feed retains its maximum difficulty of 0.5. Contact success is distinct from a legal service-box landing. All five evaluations verified Unity/PyTorch action parity and the exact physical-action mapping; final acceptance seeds remain untouched.

The post-bounce 20 Hz samples put the closest ball-to-paddle-origin distance at 0.891–0.891 m across the four positions, versus about 0.870 m before this stage. This is a sampled distance to the paddle transform origin, not its nearest hitting-face surface or a continuous collision test. The existing separate physical fixture already demonstrated that low contact is reachable with current limits; it was not used for training or demonstrations.

Training resumed the full optimizer state from 786,481 to 917,565 (+131,084 experiences). Adam advanced from 2,136 to 2,496. 2,013 completed episodes and 8 partial episodes were retained, including 4,080 partial physics ticks. The trainer exited with code 0. Actor, normalizer and optimizer tensors were finite; the parent trainer directory was hash-verified unchanged. No simulation/solver failure was treated as an ordinary loss.

The contact curriculum did not achieve its target. Preserve this run as negative evidence rather than extending it unchanged or promoting it to full-game play. The next useful development experiment is to connect the return skill the policy can already perform to lower contacts: test a reset-only feed-height curriculum and measure whether gradual lowering produces actual low paddle-face hits. Ball flight and body limits must remain physical, and all movement must stay policy chosen. Before training that experiment, establish its baseline and physical/reset contract. Continue full legal-serve and per-seat return retention checks; more shaping reward is not acceptance. The timing/discount hypothesis remains separate and was not changed in this run.

ML-Agents 4.1 supports [curricula over environment parameters](https://docs.unity3d.com/Packages/com.unity.ml-agents@4.1/manual/Training-ML-Agents.html#curriculum). The proposed feed-height progression is our next experiment based on this project's results, not a Unity-validated recipe. A combined reward mean across drop and return tasks should not be used to claim that the drop lesson is solved.

Unity model asset: Assets/Picklebot/PlayerLearning/Models/After917kDropContactTraining.onnx. Saved diagnostic preview: Assets/Picklebot/Scenes/ArticulatedMixedPracticePreview917k.unity. This is a development policy, not an accepted 2v2 model.

Evidence: artifacts/player-v3/drop-contact-train-01 and the five drop-contact-917k evaluation directories. ONNX SHA-256: 7737dac151aef209a596b2552e9cec2f9cd7da5fa6ec7eb47f163760387a5284. Source identity: 7454caa3c88b66c81f7f995ac9884dd04fc0cc60b01b76409c143c398a502307.


# Lower-feed training — 8 September 2026

Standard ML-Agents PPO is continuing from checkpoint 917,565 toward 1,048,576 experiences with the full actor, normalizer, critic and Adam state preserved. Eight aligned courts alternate blocks of four low-return starts and four varied-return starts, covering all four seats under shared policy weights. Each court has one active learner for its drill; this is not four-player match training yet.

The new lesson lowers the easy-return feed by 20 cm only at reset. The model starts in its usual pose and chooses every movement and swing. Ball dynamics, body limits, action/observation schema, timing, legal-return reward and PPO settings are unchanged. The normal-height varied-return task retains maximum difficulty 0.5. No feasibility command, stroke preview, body-pose target, demonstration or runtime ball assistance is installed in the learner.

Six paired 128-attempt feed-height probes established the baseline. At zero lowering, all 4,863 policy decision rows and every reward/outcome exactly match the prior easy-return evaluation. Fifteen relevant tests passed. The chosen 20 cm baseline has 79/128 paddle-face contacts and 71/128 legal returns; see the full curve in outputs/low-feed-baseline.md. This is a first bounded lesson, not automatic graduation to deep feeds or serving.

Live startup snapshot (exploratory training, not frozen evaluation):

```json
{
  "low-return": {
    "episodes": 370,
    "outcomes": {
      "body_or_handle": 102,
      "bad_return": 92,
      "legal_return": 150,
      "miss": 22,
      "rule_terminal": 4
    },
    "contacts": 254,
    "bySeat": {
      "0": 93,
      "1": 92,
      "2": 93,
      "3": 92
    }
  },
  "varied-return": {
    "episodes": 368,
    "outcomes": {
      "bad_return": 150,
      "legal_return": 149,
      "body_or_handle": 38,
      "miss": 20,
      "rule_terminal": 11
    },
    "contacts": 323,
    "bySeat": {
      "0": 93,
      "1": 91,
      "2": 92,
      "3": 92
    }
  }
}
```

Watch the selected court in Unity's Scene view via Window > Picklebot > Training Monitor. Watch speed slows presentation while every court keeps advancing. TensorBoard at http://127.0.0.1:6008/ includes low-feed alongside the previous runs. Track Picklebot/low-return/LegalReturn, FaceContact and ContactBallHeight, plus varied-return retention. ContactBallHeight is the ball centre measured at actual contact and is conditional on a contact occurring; a lower median alone is not success. Historical curves below step 917,565 belong to preceding curricula.

After this continuation, repeat the full height curve, near/varied-return retention and all four full serving positions. Measure per-seat performance and body/handle errors. Lowered feeds are a route toward low contact; they do not establish release timing, cross-body serve positioning, legal serving, sustained rallies or accepted 2v2 play. Training integers 1024576..1032767 are explicitly reused; development and final seeds remain excluded from optimization.

Evidence: artifacts/player-v3/low-feed-contract-01, low-feed-917k-00cm through 80cm evaluation directories, and low-feed-train-01. Source identity: 65c0bf89e228b9c9c2d7f0af38a5705c2829f3b4b2612b929b496b101a609ce1.


## Low-feed checkpoint 1,048,587 recovered and evaluated

Completed low-feed-01 (+131,022 experiences). Paired development legal returns: normal 84→106/128; 20 cm lower 71→116/128; varied 97→117/128; 40 cm lower 13→23/128. Near returns 11→10/128, 60/80 cm zero face contacts, drop serving zero contacts in four probes. All nine exports verified against PyTorch; final seeds untouched. Eight-arena training complete, optimizer stopped. Saved normal-speed ArticulatedLowFeedPreview1048k.unity. Next: gradually deepen the lower-feed lesson while retaining varied returns and per-seat/serve checks. Full serving and playable 2v2 remain unmet. See artifacts/player-v3/low-feed-train-01/results.md and paired-evaluation.json.


# Lower-feed continuation: 30 cm lesson

PPO is continuing from 1,048,587 toward 1,179,648 agent experiences with its full actor, normalizer, critic and Adam state preserved. Run: low-feed-02. Eight aligned practice arenas alternate blocks of four low-return and four varied-return starts; all four player positions contribute to the shared policy. Each drill has one active learner, not a four-player match.

The lower feed moves from a 20 cm to a 30 cm vertical reset offset. Its frozen baseline was 77/128 legal returns and 96/128 paddle-face contacts, with per-seat legal returns 23, 17, 15 and 22/32. The 40 cm baseline had only 23/128 legal returns. Existing body limits, dynamics, rewards, actions, observations, timing and PPO settings are unchanged. No scripted strokes, demonstrations or runtime assistance were added.

Startup verified checkpoint 1,064,947, Adam update 2880, actor maximum parameter change 0.006899, and successful episodes for both tasks across all four positions. These are exploratory training data, not a post-training performance claim.

Unity's Training Monitor shows the selected court. Watch speed slows presentation while all courts advance. TensorBoard at http://127.0.0.1:6008/ now includes low-feed-30cm alongside low-feed-20cm and earlier histories; curves before step 1,048,587 in the resumed run come from prior curricula. The monitor's existing metrics button still targets the older port 6006; use the 6008 link for this run.

After completion, verify the full checkpoint and exports, then repeat 0/10/20/30/40/60/80 cm paired development probes, near/varied returns and all four starting serve positions. Track legal returns, body failures and seat retention. Held-ball serving and accepted 2v2 remain unmet. Training integers 1032768..1040959 are explicitly reused, and final seeds remain untouched.

Evidence: artifacts/player-v3/low-feed-train-02. Source identity: 0f7a96a9d31b09ab6e52eed1a3bb2eb736f26151cd1d8a0b88907764f01a1e1e.


# Lower-feed continuation results

The 30 cm lower-feed lesson completed at checkpoint 1,179,663, adding 131,076 agent experiences. Standard ML-Agents PPO retained the full actor, observation normalizer, critic and Adam state from checkpoint 1,048,587. Eight aligned courts alternated lower-feed and varied-return starts, covering all four player positions. The previous trainer directory is hash-verified unchanged.

| Paired development probe | Previous legal | Current legal | Current face contacts | Current body/handle failures |
|---|---:|---:|---:|---:|
| Normal feed | 106/128 | 89/128 | 128/128 | 0/128 |
| 10 cm lower | 116/128 | 117/128 | 128/128 | 0/128 |
| 20 cm lower | 116/128 | 120/128 | 128/128 | 0/128 |
| 30 cm lower (trained) | 77/128 | 123/128 | 125/128 | 3/128 |
| 40 cm lower | 23/128 | 83/128 | 95/128 | 30/128 |
| 60 cm lower | 0/128 | 3/128 | 38/128 | 45/128 |
| 80 cm lower | 0/128 | 0/128 | 0/128 | 0/128 |
| Near return | 10/128 | 13/128 | 44/128 | 27/128 |
| Varied return | 117/128 | 96/128 | 123/128 | 4/128 |
| Held-ball serving | 0/4 | 0/4 | 0/4 | 0/4 |

| Probe | Previous legal by seat (32 each) | Current legal by seat (32 each) |
|---|---|---|
| 00cm | 26, 32, 31, 17 | 19, 20, 31, 19 |
| 20cm | 32, 28, 30, 26 | 32, 30, 32, 26 |
| 30cm | 23, 17, 15, 22 | 32, 32, 30, 29 |
| 40cm | 9, 4, 2, 8 | 23, 25, 20, 15 |
| near | 2, 3, 2, 3 | 4, 4, 1, 4 |
| varied | 30, 31, 32, 24 | 26, 24, 23, 23 |

All 10 evaluation runs passed source/model/checkpoint identity, transition accounting and exported-policy parity checks. Maximum Unity/PyTorch continuous-action error was 4.17e-07; physical mapping error was zero. Every attempt, including misses and rule/body failures, remains in the results.

These are deterministic paired development comparisons on reused development seeds, not multiple independent training replications or final acceptance. Feed lowering means a vertical reset offset, not actual contact height. Serving probes cover four deterministic starting positions; their seeds do not randomize those resets.

The only learning-task change was moving the fixed lower-feed offset from 20 to 30 cm. Body limits, ball physics, rewards, observations, action semantics, control timing and PPO hyperparameters were preserved. Movement and swing remain learned. No scripted serve, stroke demonstration or runtime ball assistance was added.

Training completed 4,238 episodes and recorded 1,551,405 physical ticks. 7 partial episodes (1488 physical ticks) were retained in accounting. Training integers 1032768..1040959 were explicitly reused; no held-out seeds entered optimization and no final seeds were consumed.

Evidence: artifacts/player-v3/low-feed-train-02/paired-evaluation.json and training-verification.json, plus all low-feed-1179k-* evaluation directories. Serving distance samples, when available, are in low-feed-1179k-serve-probe-01/sampled-reach-diagnostic.json; they are not continuous collision or feasibility measurements.

Latest dashboard: http://127.0.0.1:6008/ (low-feed-30cm). Full serving, sustained rallies and accepted 2v2 have not been demonstrated.
# Next learning experiment

The completed 30 cm lesson improved paired legal returns at 30 cm (77 to 123/128) and transferred to 40 cm (23 to 83/128). Normal-height returns declined from 106 to 89/128 and varied returns from 117 to 96/128. This checkpoint adds useful low-contact skill but is not an across-the-board replacement for the previous checkpoint.

Next, train a mixture of reset heights spanning normal feeds through 40 cm lowering, including explicit normal-height rehearsal while retaining varied-return practice. Verify the reset sampler, endpoint equivalence, task routing, per-seat coverage and source provenance before training. Preserve all body limits, private observations/actions, physical timing, release rules and learned stroke control. This is a curriculum change, not a body redesign or scripted hit.

Compare all heights, near/varied retention and held-ball serving again after a bounded continuation. Keep both checkpoints and their evidence; do not consume final seeds or promote either as accepted 2v2.

Serving remains a separate unresolved transfer problem. The four deterministic starting positions still produced zero contact. The best sampled post-bounce ball-to-paddle-origin distance is about 0.824 m (previously 0.851 m). At that sample, the ball is about 0.416 m above the root and on its left, while the paddle origin is about 1.099 m above the root and on its right. These 20 Hz samples are not continuous collision distances or a reachability proof. Existing physical fixtures already show that constrained low-drop contact is feasible; their command sequence must remain test-only. Address the actual serve reset geometry and release/preparation learning after stabilizing height coverage, rather than treating lower feeds alone as serving completion.



# Mixed-height training

Run mixed-height-01 resumes checkpoint 1,179,663 with the full actor, normalizer, critic and Adam state and trains toward 1,441,792 agent experiences (about 262,000 additional). Eight aligned practice courts contribute to shared policy weights. Every lower-feed height covers all four player positions; each drill has one active learner, not a four-player match.

The new reset schedule alternates blocks of four lower feeds and four varied returns. Lower feeds rotate through 0, 10, 20, 30 and 40 cm vertical offsets. Each height receives 10% of starts and varied returns 50%, including their existing easy-feed component. Start proportions are not guaranteed decision proportions. Physics, body limits, rewards, private observations/actions and PPO hyperparameters are unchanged. Swing and body motion remain learned, with no demonstrations or runtime ball assistance.

Sixteen tests passed. Fixed 30 cm compatibility reproduced all 4,927 policy decisions and all 128 episodes exactly under the previous checkpoint. The new frozen 80-episode, eight-court baseline had 65 legal returns, 13 bad returns and 2 body/handle failures; every task/height covered all player positions. Both baseline exports passed Unity/PyTorch parity and complete transition accounting. The original larger development probes remain the retention tests, and final seeds are untouched.

Startup verification found checkpoint 1,212,409, Adam update 3288, finite changed actor parameters (maximum change 0.013100) and completed attempts at every height from every seat. This proves the curriculum is training, not that retention or serving improved.

Watch Unity through Window > Picklebot > Training Monitor. The corrected metrics button opens http://127.0.0.1:6008/ . Select mixed-height and track Picklebot/height-0cm through height-40cm LegalReturn, FaceContact and BodyOrHandle, alongside varied-return metrics. The dashboard retains earlier runs; history before 1,179,663 in the resumed run belongs to prior curricula.

Training-only integers 1040960..1057343 are explicitly reused; 16,384 allocated starts accommodate the longer budget. After completion, verify the checkpoint/export and repeat the seven fixed heights, near/varied returns, all four serving positions and the 80-episode mixed fleet. Preserve failed/partial attempts and all earlier evidence. Accepted serving, sustained rallies and full 2v2 remain unmet.

Evidence: artifacts/player-v3/mixed-height-contract-01 and mixed-height-train-01. Training source identity: 2a1007c45c0768940c5a34183b0c3b36e06606c377a04ef1d28f1af0aa154220.
# Serving release diagnostic

The immediate release seen in deterministic previews does not establish collapsed release exploration. The framework's categorical distribution at the four recorded initial held-ball states gives:

| Checkpoint | Hold probability | Release probability |
|---|---:|---:|
| 917,565 | 44.85% | 55.15% |
| 1,048,587 | 34.16% | 65.84% |
| 1,179,663 | 35.74% | 64.26% |
| 1,286,112 (mixed-height snapshot) | 33.00% | 67.00% |

Values are effectively equal across the four starting positions. A deterministic rollout chooses the larger probability and therefore releases immediately; stochastic training still has substantial probability of choosing hold at the initial state. This evidence does not justify resetting the release policy, forcing a waiting period or changing the release controls.

This is a conditional distribution check on the same four initial observations, not a sampled serving rollout. It does not measure the probability of holding for an entire preparation sequence, later held-ball states, successful contact or serving reliability. Full serving remains unmet. Continue the mixed-height experiment unchanged and assess its completed checkpoint before selecting the next serving intervention.

Evidence: `F:/dev/picklebot/artifacts/player-v3/serve-release-distribution-01/probabilities.json` and `analysis.py`. The diagnostic pins each checkpoint and the original observation trace by hash and uses the installed ML-Agents actor/distribution implementation. It changes no policy, optimizer, simulation or training source.

# Feed placement and serving coverage

The recorded initial states confirm a gap between incoming-feed practice and serving. In each of the normal, 30 cm lower, 40 cm lower, varied and near-return cohorts, all 128 feeds start at canonical X = +0.3453 m relative to the player root. Across these five cohorts, all 640 starts are on the right. The four held-ball serve positions start at X = -0.2800 m on the left.

Other geometry differs too: feed starts are roughly 1.73–2.73 m ahead, while the held serve is 0.375 m ahead and 1.01 m above the root. Lowering the existing feed changes its height but retains its initial lateral placement. These are reset measurements, not a claim that every later observation stays on the right. Earlier serving training did expose the held-ball state, but failed to discover paddle contact.

This does not establish that placement is the sole cause of failed serves. It does justify a next developmental probe of gradual leftward feed translations, with unchanged bodies, dynamics and controls, before committing to further right-side height lessons. Measure paddle-face contacts, legal returns and body/handle failures at every player position; retain the existing height and varied-return checks. The actor must choose its own footwork, arm motion and swing. Do not prescribe an interception pose, force a serving delay or alter the ball after reset.

Serving still needs its own complete held-ball evaluation. Incoming-feed success cannot establish release preparation, legal service landing or playable 2v2. Final-evaluation seeds remain untouched.

Evidence: reset-placement-diagnostic.json, which pins the observation encoder, reset implementation and six recorded decision traces by hash. Probabilities in serve-release-distribution-01 separately show that deterministic immediate release is not proof of collapsed release exploration.



# Mixed-height training results

The five-height curriculum completed at checkpoint 1,441,798, adding 262,135 agent experiences. Eight aligned courts alternated normal/10/20/30/40 cm lowered feeds with varied-return practice. Each height covered all four player positions under shared policy weights. The complete parent checkpoint and its evidence remain unchanged.

| Paired development probe | Parent legal | Current legal | Current face contacts | Current body/handle failures |
|---|---:|---:|---:|---:|
| Normal feed | 89/128 | 126/128 | 128/128 | 0/128 |
| 10 cm lower | 117/128 | 127/128 | 127/128 | 1/128 |
| 20 cm lower | 120/128 | 115/128 | 115/128 | 13/128 |
| 30 cm lower | 123/128 | 67/128 | 75/128 | 52/128 |
| 40 cm lower | 83/128 | 40/128 | 52/128 | 72/128 |
| 60 cm lower | 3/128 | 1/128 | 6/128 | 47/128 |
| 80 cm lower | 0/128 | 0/128 | 0/128 | 1/128 |
| Near return | 13/128 | 14/128 | 55/128 | 31/128 |
| Varied return | 96/128 | 122/128 | 126/128 | 2/128 |
| Held-ball serving | 0/4 | 0/4 | 0/4 | 0/4 |
| Mixed-height fleet | 65/80 | 73/80 | 74/80 | 6/80 |

The parent had already lost some earlier normal-height and varied-return performance. Compare against checkpoint 1,048,587 as well:

| Retention probe | Earlier 1,048,587 | Parent 1,179,663 | Current |
|---|---:|---:|---:|
| Normal feed | 106/128 | 89/128 | 126/128 |
| Varied return | 117/128 | 96/128 | 122/128 |

| Probe | Parent legal by seat (32 each) | Current legal by seat (32 each) |
|---|---|---|
| 00cm | 19, 20, 31, 19 | 32, 31, 32, 31 |
| 20cm | 32, 30, 32, 26 | 32, 26, 25, 32 |
| 30cm | 32, 32, 30, 29 | 25, 8, 11, 23 |
| 40cm | 23, 25, 20, 15 | 16, 0, 7, 17 |
| near | 4, 4, 1, 4 | 1, 4, 3, 6 |
| varied | 26, 24, 23, 23 | 30, 32, 32, 28 |

All 11 evaluation runs passed source/model/checkpoint identity, transition accounting and exported-policy parity checks. Maximum Unity/PyTorch continuous-action error was 4.77e-07; physical mapping error was zero. All failures remain in the denominators.

These are deterministic paired development comparisons on reused development conditions, not independent training replications or final acceptance. Feed lowering is a reset offset, not the actual ball height at contact. The four serving positions use deterministic starting geometry; different seeds do not make them randomized serve trials.

The curriculum changed only reset selection and added per-height telemetry. Sixteen relevant tests passed before training, and fixed-height compatibility reproduced all 4,927 decisions and 128 episodes exactly. Body limits, ball physics, rewards, private observations/actions, timing and PPO hyperparameters remained unchanged. No scripted stroke, forced serving delay, demonstration or runtime ball assistance was added.

Training completed 8,105 episodes and recorded 3,102,643 physical ticks. 8 partial episodes (1884 ticks) remain in accounting. The full actor, normalizer, critic and Adam state was resumed; actor parameters changed and the parent directory was hash-verified unchanged.

Training integers 1040960..1057343 were explicitly reused; no held-out seeds entered optimization and no final seeds were consumed. Full serving, sustained rallies and accepted 2v2 remain unmet.

Evidence: artifacts/player-v3/mixed-height-contract-01 and mixed-height-train-01, plus all mixed-height-1441k-* probe directories. Dashboard: http://127.0.0.1:6008/ (mixed-height).
# Mixed-height outcome and next step

The mixed-height run recovered normal-height and varied-return performance beyond the earlier 1,048,587 reference: 126/128 normal and 122/128 varied legal returns. However, it lost much of the parent checkpoint's low-contact skill: 30 cm fell from 123 to 67/128 and 40 cm from 83 to 40/128, with higher body/handle failures. The small mixed-fleet aggregate improved from 65 to 73/80; that aggregate does not override the larger per-height probes. This is a tradeoff, not successful retention across all heights. Preserve both checkpoints; neither is an accepted full-game policy.

Serving remains zero-contact at all four deterministic starting positions. The release distribution diagnostic did not support collapsed exploration, so do not reset that head or force a delay. The reset placement audit did establish a coverage gap: incoming feeds start 0.345 m to the player's right, while the held ball starts 0.280 m to the left and substantially closer. This is not a causal proof, but it gives a concrete next developmental test.

Next: add reset-only lateral feed translation with a zero-offset compatibility endpoint, then measure gradual leftward placements at a manageable height for both useful checkpoints before choosing a continuation. Preserve the bounded body, grip, timing, observation/action schema, rewards and actual ball physics. The learner must choose footwork and swing. Include right-side height and varied-return retention, per-seat failures and the complete held-ball serve probe. Do not repeatedly deepen the same right-side feed and call that serving progress.

The longer mixed run took about 1,288 seconds for 262,135 new trainer experiences (about 203.5 experiences/second including startup and exports). Before much larger budgets, a separate headless/process throughput check may be worthwhile. It must preserve physical timing, seed/evidence isolation, player ownership and policy behavior; speed alone is not evidence of better play. No such runtime change was made in this stage.

Accounting: the environment observed 262,336 decisions, with 262,179 decisions in completed episodes and 157 in partial episodes. The trainer step advanced by 262,135. These are separate counters; do not silently identify every observed transition with an optimizer-consumed experience. Eight partial episodes account for 1,884 physical ticks. Final-evaluation seeds remain untouched.

Source and measured results: artifacts/player-v3/mixed-height-train-01/results.md, paired-evaluation.json and training-verification.json. Supporting diagnostics: serve-release-distribution-01 and reset-placement-gap-01.



## Lateral feed contract and paired baseline

The reset-only change passed 13 tests and 14 paired frozen evaluations. All eight zero-offset replay probes exactly preserved prior decision rows and episode fields. The archived physical drill version is player-v3-grounded-drills-10-lateral-feeds. No policy weights, body bounds, grip, action/observation fields, rewards, latency or post-reset ball physics changed. No optimizer ran.

At 20 cm left and 20 cm lower, checkpoint 1,179,663 made 76 face contacts but only 11 legal returns (per seat 0,2,3,6). Its failures were 52 body/handle without prior face contact, 31 body/handle after prior face contact, 22 bad returns and 12 rule terminations. Checkpoint 1,441,798 made 62 face contacts and four legal returns (0,0,4,0), with 66 body/handle failures without prior face contact and 35 after contact. These categories do not identify a particular body surface or prove every failure shares one biomechanical cause.

Both checkpoints had zero face contacts and 128 body/handle failures at 40 and 60 cm left. Both still failed all four real held-ball serving positions. Translating incoming feeds exposes a placement gap; it is not a serving success or a full causal explanation of serving failure.

Use the preserved 1,179,663 checkpoint (low-feed-02) as the parent of a separately named lateral-practice branch: it retains 123/128 legal returns at 30 cm lowering and offers more legal/contact examples at 20 cm left. The newer checkpoint remains preserved and is still the stronger varied-return reference (122 versus 96/128). Do not overwrite either checkpoint or choose a model solely by its highest step number.

Next implement and verify a reset schedule with four low-feed conditions: 20 cm lowering at 0, 10 and 20 cm left, plus unchanged 30 cm lowering. Each condition must cover all four seats, alternating each four-seat block with four varied returns. This gives each low condition 12.5% of starts and varied returns 50%; experience fractions will differ with episode length. Ten cm left is an interpolated stepping stone, not an already measured result. Use eight aligned arenas with private player observations/actions and shared weights. Preserve the held-ball serve evaluation and per-seat retention probes.

Before optimization, verify routing/seed accounting and run a frozen schedule baseline. Continue the full parent actor, normalizer, critic and Adam state with standard PPO and a bounded additional budget (about 262,000 trainer experiences). Keep the current physical/reward contract; no scripted footwork, swing demonstration, imposed release timing or forced contact. Deliberately allocate training-only seed reuse; do not feed the development traces into training. Reevaluate lateral placement, right-side heights, varied returns and unassisted serving together before choosing another continuation.

This schedule and training continuation are planned, not implemented/launched in this stage. Playable 2v2, learned serving and sustained rallies remain unmet; final evaluation seeds are untouched. A separate process-throughput pilot remains an option before substantially larger training budgets.

Evidence: artifacts/player-v3/lateral-feed-contract-01/{verification.json,results.md,paired-evaluation.json,next-step.md}.


# Gradual lateral PPO training

Run lateral-practice-01 branches from the preserved 1,179,663 checkpoint with full actor, normalizer, critic and Adam state. It targets 1,441,792 agent experiences (about 262,000 additional). This is a separate branch from mixed-height-01, not its continuation; compare run IDs as well as step numbers.

Eight aligned courts contribute to shared policy weights. Each drill has one active player, with all four player positions covered by each condition. The reset schedule alternates varied returns with 20 cm lowered feeds at 0/10/20 cm left and a retained 30 cm lowered feed at zero lateral offset. Each low condition receives 12.5% of starts; varied returns receive 50%. These are start fractions, not guaranteed experience fractions.

Ten tests passed, including independent reset equivalence for all conditions/seats and existing ML-Agents bridge behavior. The unchanged 20 cm-left endpoint exactly reproduced all 2,773 prior decisions and 128 episodes. The frozen 64-episode fleet baseline and full per-placement comparisons are preserved. Physical body limits, grips, actions, observations, rewards, latency, PPO parameters and post-reset flight remain unchanged; no prescribed stroke or release timing was added.

Startup verified checkpoint 1,196,007, Adam step 3240, finite changed actor weights (maximum change 0.006279) and completed attempts for every condition from every seat. This proves optimization is running, not that lateral returns or serving improved. Current exploratory training rates must be followed by frozen evaluations.

Watch Unity through Window > Picklebot > Training Monitor. TensorBoard at http://127.0.0.1:6008/ includes lateral-practice and the earlier runs. Track Picklebot/left-0cm-lower-20cm, left-10cm-lower-20cm, left-20cm-lower-20cm and left-0cm-lower-30cm LegalReturn/FaceContact/BodyOrHandle, alongside varied-return metrics. History before 1,179,663 belongs to the parent curricula.

Training-only seeds 1057344..1073727 are deliberately reused. Development traces are not optimizer input; final seeds remain untouched. At completion verify the full state/export, then repeat lateral placements, right-side height retention, near/varied returns, held-ball serving and the 64-episode fleet. Serving, sustained rallies and accepted playable 2v2 remain unmet.

Evidence: artifacts/player-v3/lateral-curriculum-contract-01 and lateral-practice-train-01. Source identity: 4704667d2100b28939f7dcb2f2517e41d0d4f0b5df8905667176691a30c20135.


# Lateral-practice outcome and next step

Run lateral-practice-01 completed at 1,441,809, adding 262,146 trainer experiences from low-feed-02 at 1,179,663. Full-state verification found Adam step 3,960, finite changed actor weights, exact numbered/exported policy agreement and an unchanged parent directory. There were 8,441 complete episodes and eight partial episodes. Observed decisions were 262,272; completed-episode decisions were 262,146 and the remaining 126 observed decisions belonged to partial episodes (1,512 physics ticks). These counters happen to align with the trainer delta in this run; they do not prove every recorded transition entered an optimizer update.

The frozen results show broader easy-return competence but failure on the intended hard placement. The unchanged 20 cm lowered feed improved 120 to 128/128, 10 cm left improved 86 to 98/128, normal height improved 89 to 121/128, and varied returns improved 96 to 112/128. Retained 30/40 cm lowered feeds fell from 123/83 to 116/75. Twenty cm left fell from 11 to 5/128 with 104 body/handle failures. Forty and sixty cm left still had zero face contacts and 128 body/handle failures each. The small fleet rose 49 to 51/64; that aggregate does not override the harder 128-attempt results. Per-seat regressions remain in the report, including 10 cm-left seat 3 falling from 26 to 21/32.

Serving still has zero contacts and zero legal serves across all four deterministic held-ball starting positions. The sampled post-bounce ball-to-paddle-origin minimum is about 0.804 m, versus about 0.824 m in the parent. This 20 Hz distance diagnostic is not a continuous surface distance, legal contact or reachability proof. Do not describe the slight proximity change as learned serving.

Preserve this model as a useful candidate for subsequent work, alongside both low-feed-02 and mixed-height-01. It has a better balance of normal/lower/varied competence than the mixed-height branch, but is not uniformly superior and is not accepted for full 2v2. The observed difficulty does not justify removing body collisions, scripting footwork, adjusting the ball after reset or prescribing a stroke.

Do not simply repeat the same 262,000-experience mixture. The 20 cm-left condition had 12.5% of starts but only 8.97% of completed-episode decisions (23,513 of 262,146), because failed attempts ended sooner. This is evidence of exposure imbalance, not proof that weighting alone will solve the behavior. A next learning experiment should give the hard condition substantially more practice while retaining easier returns, and compare against the best historical hard-placement result as well as the immediate parent.

First implement and verify the standalone worker startup/evidence partitioning described in artifacts/player-v3/headless-readiness-01/readiness.md, then run a bounded throughput pilot with equal total arena counts. The installed framework and Windows build support are available, but simply raising num_envs would duplicate project-owned physical seeds and collide on evidence files. Keep this completed checkpoint fixed for an Editor/standalone behavior comparison. The infrastructure pilot must preserve clocks, controls, observations, reset distributions and collision behavior; it does not itself establish better play.

After that, a concrete next curriculum candidate is 50% of starts at 20 cm left/20 cm lower, 25% varied returns, 12.5% at 10 cm left/20 cm lower, and 12.5% retained 30 cm lowering. Every condition must cover all four seats. Verify actual experience fractions and run the same independent lateral, height, near/varied and real-serving evaluations. This weighted schedule is a proposal, not implemented or trained here. Choose a bounded budget after measuring throughput; keep PPO and the physical/reward contract unchanged for an interpretable first comparison.

All 15 current evaluations passed source/model identity, exported-policy parity and complete transition accounting. Maximum Unity/PyTorch action error was 4.17e-07; physical mapping error was zero. No final seeds entered testing or optimization. Accepted serving, sustained rallies, complete competitive games and the frozen independent-player 2v2 acceptance gates remain unmet.

Model asset: Assets/Picklebot/PlayerLearning/Models/AfterLateralPractice01.onnx. Saved observation scene: Assets/Picklebot/Scenes/ArticulatedLateralPracticePreview01.unity. Training model SHA-256: ef6b7aa074d3dfeecff659deaad0438ace217462b11224f8f9884744fd003bc6. Full paired results: results.md and paired-evaluation.json in this evidence directory.


## Checkpoint clone retention correction (2026-09-08)

The focused-lateral-01 final check found that copied run_logs/training_status.json retained absolute historical checkpoint paths. Stock retention removed 128 older checkpoint files. All 128 were restored to pinned hashes from preserved copies; audit and recovery records are in artifacts/player-v3/focused-lateral-train-01. The trained checkpoint was unaffected.

All future branches must use scripts/mlagents_clone_run.py to clone completed trainer output and rebase checkpoint/final-checkpoint paths into the destination. Do not reuse the earlier copytree-only preparation pattern. The helper preserves full checkpoint bytes and records sourceFiles, cloneFiles and metadata rewrites. Launch verification must compare cloneFiles for the new run and sourceFiles for the parent. Stock cleanup was regression-tested to delete only cloned fixture checkpoints, preserving source and ancestor bytes.


## Focused lateral result (2026-09-08)

The verified 1,966,119-step policy improved 20 cm left returns from 5/128 to 102/128 and 10 cm left from 98/128 to 128/128. Varied returns fell from 112/128 to 85/128, and retained 30 cm lowering from 116/128 to 80/128. All 16 frozen evaluations (1,860 episodes) passed source/model/action checks. The four actual held-ball serves still released at observation tick 0, bounced, and made no paddle contact. No accepted playable model and no final seeds consumed.

The next learning experiment should address real held-ball contact using the stronger policy while retaining representative returns, followed by legal serve/rally learning and standalone team-arena integration. Full details and failed outcomes are in artifacts/player-v3/focused-lateral-train-01/{results.md,next-step.md,paired-evaluation.json,stage-verification.json}. The learned inspection scene is Assets/Picklebot/Scenes/ArticulatedFocusedLateralPreview01.unity. Use the corrected clone helper for all further branches.
