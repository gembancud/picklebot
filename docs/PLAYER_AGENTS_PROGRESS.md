# Independent player agents

Status: active, not complete. Started 2026-09-06. The app goal was found marked
blocked at 08:50 UTC. The user resumed it at 16:40 UTC (2026-09-07 locally).
The retention trial and the contact, shot-quality, and teacher-gap diagnoses are complete.
No candidate or command change is promoted. The proposed movement, jump, and energy
controller is awaiting the user's decision. No controller change is approved.

## Latest verified state — 2026-09-07 13:27 UTC

- This goal turn made progress. Evaluation process **21371** ended with
  exit code 0. All four stages in `stage-evaluation-20260907-131117`
  completed. The runner checked that Unity was idle before it exited.
  No new training run has started.
- Repeated the serve and return audits from their recorded decisions.
  Repeated both full-game verifiers for the starting and updated actors.
  All repeated results match the saved audits. Source snapshots, model
  hashes, plan hash, report hashes, physical limits, game identities,
  court ends, baseline modes, and sampling settings pass their checks.
  Saved comparison: `artifacts/player-agents/trunk-self-play-comparison-20260907.json`.

| Actor and execution | Game wins | Rally wins | Legal returns | Time-limit rallies |
| --- | --- | --- | --- | --- |
| Starting 122354, fixed | 0/8 | 45/206 | 904 | 37/206 |
| Updated 130353, fixed | 0/8 | 67/211 | 583 | 14/211 |
| Starting 122354, sampled | 0/8 | 50/177 | 383 | 9/177 |
| Updated 130353, sampled | 0/8 | 48/177 | 484 | 9/177 |

- Fixed-action rally wins rise from 21.84% to 31.75%. Time limits fall
  from 17.96% to 6.64%. Sampled rally wins fall from 28.25% to 27.12%;
  its time-limit fraction remains 5.08%. These are mixed, small-sample
  development results. The update does not establish overall match
  improvement. All 16 updated-model games were lost. No promotion.
- Fixed report: `development-evaluation-20260907-131311`, completion
  SHA-256 `c2b4a68e4931d082e73cbd013e2895872f33258f47358ec661a3c35bbc21b1c3`,
  394.008 seconds. Sampled report:
  `development-evaluation-20260907-132000`, completion SHA-256
  `9a39bce13ab404c8def8e75fc3b1475aca4d9c2b421446916aee72dde98471fc`,
  315.080 seconds. Both use the unchanged development seeds
  1141000 through 1141007. Final evaluation seeds remain unused.
- Basic-skill results remain fixed serves 7/12, sampled serves 9/12,
  short returns 15/16, and deep returns 10/16. Only deep returns rise,
  by one landing. Detailed evidence and hashes are in the stage folder.
- The saved comparison also records aggregate rally fault counts.
  Sampled losses include 44 WrongSide, 36 BodyContact, and 21 SecondBounce
  faults. These labels do not isolate the physical or policy cause.
  Full-game reports do not contain complete contact traces. Do not claim
  full-match action replay from these reports.
- All 63 baseline files remain unchanged. The diff whitespace check
  passes. Runtime, physics, scene, models installed in the scene, and
  the frozen final protocol are unchanged. The latest 296-test result
  remains valid for the unchanged source; tests were not rerun for this
  report-only update. Ball physics remains provisional and uncalibrated.
- The user is considering a 7800X3D / RTX 4070 / 32 GB desktop. Its OS
  is still unknown. Keep new training stopped while the transfer choice
  is pending. No files have been transferred, published, or removed.
  A clone alone omits the uncommitted player code and ignored models.
  Fresh self-play needs the source, selected actor/critic, opponent
  checkpoints, baseline manifest and its required reports, and frozen
  plans. The latest actor folder is about 1.9 MB. Bulk historical traces
  can stay here, but must be retained for audit and experiment replay.
- NEXT: establish the destination OS and transfer scope, verify the
  unchanged simulation and actor there, and measure throughput before
  adding workers or CUDA. The existing trainer is CPU-only. Do not
  assume hardware alone fixes the weak match results. A subsequent
  training plan should test stronger opponent coverage; 9/9 training
  wins against an older model did not transfer to baseline game wins.
- Full goal active and incomplete. Final baseline/older/partner
  acceptance, useful held-out coverage, improved match performance,
  and final playable-scene proof are not established for this actor.

## Previous verified state — 2026-09-07 13:16 UTC

- The previous goal turn made progress. The two-update self-play run
  `training-loop-20260907-125203` is complete. Its independent audit is
  `artifacts/player-agents/trunk-self-play-audit-20260907.json`.
  The final actor is `ppo-20260907-130353/actor.json`, SHA-256
  `61c59e110797290c46b30b91a9fa2d0d3665e92a40f3c998bf2e24ed168edc06`.
- The audit verifies both complete-game collections, reward-derived
  updates, carried critic, policy likelihoods, model lineage, physical
  limits, source snapshots, seed splits, and Unity output parity.
  Collection produced 60,436 and 42,634 candidate decisions in 316.200
  and 223.345 seconds. Model updates took 43.343 and 21.384 seconds.
  The second collection won 9/9 games against the older model, before
  the second update. The two small baseline checks each won 0/2 games.
  These training outcomes do not prove improvement after an update.
- All 296 Python tests passed. The new `player-stage-evaluate.py`
  runner passed its first real serve and return audit stages. It checks
  the active Unity callback before each stage and rejects overlapping
  jobs. It preserves the actor, source snapshots, hashes, and failures.
- ACTIVE evaluation process **21371**:
  `artifacts/player-agents/stage-evaluation-20260907-131117`.
  Plan SHA-256:
  `ac50bdd201aff7cd2d2c390d395d79f3d5098f23abc7ccdf54c4087a155c570b`.
  It runs 36 serves, 64 short/deep cases, eight fixed-action games,
  then eight sampled-action games. All use existing development seeds.
  No final seeds or scene promotion are involved.
- Serve report `serve-return-20260907-131120.json`: fixed 7/12 legal
  returns, sampled 9/12, teacher 11/12. These match the starting actor.
  All 5,164 actor decisions replay and all motor checks pass.
- Return report `teacher-gap-20260907-131156.json`: short 15/16 legal
  landings, deep 10/16. Starting actor: short 15/16, deep 9/16.
  All 2,456 actor decisions replay; 32 teacher controls match exactly;
  motor checks pass. These small fixtures do not establish match gains.
- First full-game child is `model-comparison-20260907-131308`, report
  `development-evaluation-20260907-131311`. At 13:15:31 UTC the actual
  Unity `TickFinal` callback was in group 2. Do not restart the driver
  or change its dependencies. Finish both inference modes, then compare
  each with the same starting-actor reference listed below.
- The user reported laptop heat and asked about moving the project.
  No new training run will start while the machine choice is pending.
  The already-running evaluation can finish. No transfer, cloud job,
  installation, cleanup, or publication is authorized or performed.
  The user supplied a desktop with AMD 7800X3D, RTX 4070, and 32 GB RAM.
  Its operating system is not yet supplied. The present trainer uses CPU
  tensors and two PyTorch threads. CUDA is not enabled automatically by
  copying the project. Validate the unchanged setup on the destination
  before changing device execution or adding simulation workers.
- Baseline check: all 63 files remain unchanged. Runtime source remains
  `7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
  No runtime, physics, scene, baseline, or final-protocol changes.
  No model is accepted. The full goal remains active and incomplete.

## Previous verified state — 2026-09-07 12:53 UTC

- This turn made progress. It audited the earlier two-update self-play
  run, completed a new hidden-layer movement fit and its physical probes,
  and finished paired fixed/sampled full-game comparisons. It then started
  another bounded team-win trial. No candidate is accepted or promoted.
- Sampled comparison process 72358 ended with exit code 0. Both eight-game
  runs and both fixed-action references passed repeated independent checks
  in `sampled-policy-comparison-audit-20260907.json`. This covers source and
  model hashes, snapshots, per-player ownership, both ends, baseline modes,
  identity swaps, sampling settings, motor limits and complete-game outcomes.

| Actor and execution | Game wins | Rally wins | Legal returns | Time-limit rallies |
| --- | --- | --- | --- | --- |
| Parent 114743, fixed | 0/8 | 21/131 | 347 | 6/131 |
| Hidden-layer 122354, fixed | 0/8 | 45/206 | 904 | 37/206 |
| Parent 114743, sampled | 0/8 | 31/147 | 247 | 0/147 |
| Hidden-layer 122354, sampled | 0/8 | 50/177 | 383 | 9/177 |

- Sampled parent report: `development-evaluation-20260907-124137`,
  completion hash `0d62bc2022775b84005b46283a2717dd879303d0fc297a11299162f1eb7706c7`,
  180.903 seconds. Sampled candidate report:
  `development-evaluation-20260907-124449`, completion hash
  `0845347fdba927bffd141d830c39522a0d1060c0c3399966f8dcc7ef9f7403f7`,
  237.064 seconds. The candidate's sampled rally-win rate rises from the
  parent's 21.09% to 28.25%; its time-limit fraction is 5.08%, below 10%.
  These are eight-game development results, not final match-strength proof.
  All models still lost all games. Fixed execution has excessive time limits.
- Froze `config/player-agents/trunk-self-play-v1.json`, hash
  `1123ff7f103e05455a3bc1d43091b3d9129035203cf39a5c0c97710ab60f0baa`.
  Initial actor: hidden-layer 122354, hash
  `e21be494d4b93557178849f990bd2acd0b72b81f9896d822ab4f3d3fec29e291`.
  Initial training-only critic: PPO 121049, hash
  `2654079c86e12297dcbf0286055052a190ee9fec2abcbfc40ddbbde00cddc552`.
  Frozen opponents: a saved copy of initial 122354, then parent 114743.
  Two updates; 256 requested rallies per collection; finish each final game.
  Both teams sample independent actions. Full-game team-win reward, all
  action heads, gamma=lambda=1, raw advantages, entropy coefficient zero,
  four epochs, batch 1024, LR 0.00003, clip 0.1, KL rollback at 0.01.
  Training seeds 1077100 and 1078100. Small development seeds 1177100 and
  1178100. These bases had no earlier matching collection or plan records.
- ACTIVE process **37993**, driver `training-loop-20260907-125203`.
  Latest process output: 9/256 rallies in the first collection. At
  12:52:56 UTC, the actual `PlayerCompetition.Tick` callback was live.
  Unity was playing and busy. Runtime source remains
  `7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
  Do not restart this run, edit its dependencies, or overlap another Unity
  job between collection, fitting, parity and development stages.
- NEXT: poll 37993. On terminal completion, audit the loop with
  `player_self_play_audit.py` and `trunk-self-play-v1.json`. Then repeat the
  same 36 real serves and 64 short/deep cases. Run eight fixed and eight
  sampled development games at 1141000..1141007 for the final actor.
  Compare each sampling mode to its own initial-actor reference above.
  Pre-update training wins are not update gains. Keep all failures.
- All 290 Python tests pass; both new auditors compile; diff whitespace
  check passes. All 63 baseline files remain unchanged. No final-seed
  evaluation plans exist. Disk was 6.3 GiB free before the new collection.
  No runtime, physics, saved scene, baseline, final-protocol, cloud,
  publication or cleanup changes. Goal active and incomplete.

## Previous verified state — 2026-09-07 12:44 UTC

- Process 60387 is terminal, exit code 0. Hidden-layer model 122354
  completed all eight fixed-action games in `development-evaluation-20260907-123009`.
  Independent audit: `trunk-movement-games-audit-20260907.json`. Completion
  SHA-256: `24104cf7bb72069d5a6fd0ff100f6e717acc1aa5276d7755dc929141c2d9b8d8`.
  Results: 0/8 game wins, 45/206 rally wins, 904 legal returns, 37 no-point
  time limits, 459.900 seconds. Parent: 0/8, 21/131, 347 returns, six limits.
  The new model sustains more returns, but 17.96% of rallies reach the cap.
  This exceeds the unchanged 10% limit. It is not accepted or promoted.
- The new model's sampled serve returns were 9/12, versus 7/12 with fixed
  actions. Freeze a separate two-model sampling comparison before running
  it. Plan: `config/player-agents/sampled-policy-comparison-v1.json`, hash
  `d649e2a0fcecb4eca20fc72632633c994f38b9768764f07daf307a718c51f3bb`.
  Parent weighted actor 114743 runs first, then hidden-layer actor 122354.
  Both use sampled actions, the same development seeds 1141000..1141007,
  both baseline modes, both ends, identity swaps and unchanged limits.
  Each model's fixed-action result is retained as a separate reference.
  This is not training. Do not credit an inference-mode change as learning.
- Added explicit `--sampled-actor` to the external comparison driver after
  the fixed-action run ended and Unity was verified idle. Default stays
  fixed actions. Validation requires the requested boolean mode to match
  the reserved plan and every report. Three tests failed before the change;
  all 290 Python tests now pass. Red evidence is retained in
  `sampled-comparison-tests-red-20260907.txt`. Driver snapshots preserve
  earlier runs. Current driver hash:
  `3b506db8be5c1015b22c04f8dc096029cea9a23d5d76454fae66195887d38a9a`.
- ACTIVE process **72358**, driver `model-comparison-20260907-124135`.
  First run: `development-evaluation-20260907-124137`. Parent model is
  active; latest verified process output was group 5. Do not restart the
  driver or launch a second Unity job between its two scheduled actors.
  No active driver dependencies may change until the full pair is terminal.
- NEXT: poll 72358, then run `player_sampling_comparison_audit.py` with
  the driver folder and frozen sampling plan. It repeats all 32 games'
  source/model, sampling, schedule, identity, motor and outcome checks
  across both fixed references and both new sampled runs. Compare training
  within each sampling mode; report time limits and failures explicitly.
  Only then choose the next team-win training trial. No final seeds or
  acceptance thresholds changed. Baseline 63 files remain unchanged.
  Goal active and incomplete.

## Previous verified state — 2026-09-07 12:33 UTC

- Hidden-layer movement fit 73991 finished with exit code 0. Saved model:
  `trunk-movement-fit-20260907-122354/actor.json`, SHA-256
  `e21be494d4b93557178849f990bd2acd0b72b81f9896d822ab4f3d3fec29e291`.
  It ran 100 epochs / 14,900 updates in 107.605 seconds. Development
  selection chose epoch 98 / 14,602 updates. Independent audit:
  `trunk-movement-fit-audit-20260907.json`. All eight source banks, seeds,
  source snapshots, model lineage, head parameter freezes and physical
  collection limits passed. This is supervised training, not team-win RL.
- Weighted movement loss decreased in every development bank. Primary:
  0.786966 to 0.509072; normal: 0.148300 to 0.108174; short: 0.046280 to
  0.029600; deep: 0.099684 to 0.059379. Output drift is not zero: primary
  hit decisions changed in 0.192% of rows and shot choices in 5.014%.
  Fixed output parameters do not imply fixed outputs when features change.
- Unity parity passed 32 cases with maximum error 0.00000381470. Parity
  input SHA-256: `2a504e876a8802e9be260e216f0fa075927fea6f44252fec16c6525d58665c30`.
- Serve probe `serve-return-20260907-122709.json` completed. Deterministic:
  12/12 hits, 7 landings, unchanged. Sampled: 12/12 hits, 9 landings versus
  the parent's 5. Teacher: 11 landings, unchanged. All 5,164 actor decisions
  replayed; physical serves match exactly; all motor checks passed. Audit:
  `trunk-movement-serves-audit-20260907.json`.
- Short/deep probe `teacher-gap-20260907-122838.json` completed. Short:
  16 hits and 15 landings, unchanged from parent. Deep: 13 hits and 9
  landings, versus 12 hits and 9 landings. Deep landings changed from 6/3
  across the two ends to 5/4. One end regressed; do not hide that result.
  All 32 teacher controls match exactly, all 2,464 actor decisions replay,
  and all motor checks pass. Audit: `trunk-movement-returns-audit-20260907.json`.
- ACTIVE eight-game comparison process **60387**. Driver folder:
  `model-comparison-20260907-123006`. Report folder:
  `development-evaluation-20260907-123009`. Actor is the new hidden-layer
  model. The unchanged development seeds are 1141000..1141007. The first
  game lost 2–11 with 181 candidate legal returns, compared with 85 for
  the parent. At 12:32:35 UTC, read-only inspection of the actual callback
  showed group 1, 30 completed rallies, score 1–9. This is not a final
  comparison or acceptance result. Poll this process; do not restart it.
- NEXT: finish and audit all eight games with the existing verifier and
  complete-game outcome checks. Compare scores, wins, legal hits and
  truncations against parent 114743, self-play 121049 and older 094032.
  Better prediction loss or longer rallies do not prove stronger play.
  Retain all failures. Do not change the baseline or install a scene model.
  Runtime source remains 7a998e12...fad845. No physics changes. Disk was
  7.5 GiB free at 12:28 UTC; no cleanup was done. Goal active and incomplete.

## Previous verified state — 2026-09-07 12:25 UTC

- Previous turn was a verified wait on self-play process 75488. This turn
  completed its audit and all required local development comparisons.
  Process 75488 is terminal with exit code 0. Do not restart it.
- `near-contact-self-play-audit-20260907.json` verifies both updates,
  training-only carried critic values, complete-game rewards, recorded
  actor likelihoods, source/seed/model ownership, motor limits and Unity
  parity. Collections had 34,450 and 28,112 candidate decisions, from
  10 and 14 full games. Collection times were 191.066 and 164.353 seconds.
  Optimizer times were 16.387 and 9.725 seconds. These are local results.
  Pre-update training wins are not evidence that an update improved play.
- Final actor `ppo-20260907-121049/actor.json`, SHA-256
  `d72ec3a5511b8c080fa79416b1dbc72f82c6ca7aea5324d1690fc302824218f1`.
  All 32 parity cases passed, maximum error 0.00000381470. The actor is
  not promoted. The original baseline is unchanged.
- The same 36 real serves completed in `serve-return-20260907-121243.json`.
  Deterministic: 12 hits, 7 legal landings. Sampled: 12 hits, 5 landings.
  The teacher control stayed at 11 landings. All 4,920 recorded actor
  decisions replayed; physical serves matched exactly; motor checks passed.
  Audit: `near-contact-self-play-serves-audit-20260907.json`.
- The same 64 short/deep cases completed in `teacher-gap-20260907-121427.json`.
  Short: 16/16 hits and landings, versus 15 landings before self-play.
  Deep: 12/16 hits and 9 landings, unchanged. All 32 teacher controls match
  exactly; all 2,416 actor decisions and all motor checks pass. Audit:
  `near-contact-self-play-returns-audit-20260907.json`.
- The eight full development games completed in
  `development-evaluation-20260907-121557`. Audit:
  `near-contact-self-play-games-audit-20260907.json`. Completion SHA-256:
  `6318cb76af3ab880f9bc1b19f227f8e4e8a653c374b348c86290277193050664`.
  Results: 0/8 wins, 20/135 rally wins, 273 legal returns, five no-point
  truncations, 162.428 seconds. Starting actor: 0/8, 21/131, 347 returns.
  This self-play trial did not improve match performance. Keep the failure.
- New frozen plan `config/player-agents/trunk-movement-v1.json`, SHA-256
  `a0a3c4c673e2f6f4418e241466896ab2708bdf05a4b28214f6d50247569ddbc3`.
  Test whether trainable hidden features improve movement approximation.
  Parent is weighted movement actor 114743, not the failed self-play actor.
  Reuse the exact existing eight data banks. No new collection is needed.
  Train both hidden layers and the two movement output rows for 100 epochs,
  batch 1024, LR 0.0001, equal source weights, two CPU threads. Retain the
  near-contact movement loss and add a soft non-movement logit MSE penalty.
  Hit/shot output parameters and exploration stay fixed. Actual hit/shot
  outputs can change because hidden features change; audit their drift.
  This is supervised correction, not team-win training or final acceptance.
- ACTIVE fit process **73991**, `trunk-movement-fit-20260907-122354`.
  The process produced epoch 31 output when polled. Do not restart it or
  edit its trainer dependencies. New trainer and auditor have separate
  names, so earlier experiment provenance is preserved. All 287 Python
  tests pass. Unity was idle and playing at 12:23:59 UTC; source is unchanged.
- NEXT: poll process 73991, audit with `player_trunk_movement_fit_audit.py`,
  verify Unity parity, and repeat the unchanged 36 serves, 64 short/deep
  cases and eight games. Compare to parent 114743. No promotion before proof.
  Free disk space was 6.5 GiB before fitting. No cleanup is authorized.
  No runtime, scene, physics, baseline, final-seed or cloud changes.
  Goal active and incomplete.

## Previous verified state — 2026-09-07 12:04 UTC

- Weighted-movement full-game comparison is complete and audited in
  `near-contact-movement-games-audit-20260907.json`. Report folder
  `development-evaluation-20260907-115632`, completion hash
  `006f506de4285d739f2b7398c9051d82404f7b7dfccf7025f81262f0fe728b8f`.
  Results: 0/8 wins, 21/131 rally wins, 347 legal returns, six no-point
  truncations, 183.605 seconds. Unweighted movement had 0/8, 13/118 and
  259 returns; parent 104524 had 0/8, 16/124 and 285. This is a local
  rally/return improvement, not accepted match strength. Older 094032
  still had more rally wins and returns (51/185, 497), also 0/8 games.
  All source, model, schedule, identity and candidate motor checks pass.
- Froze `config/player-agents/near-contact-self-play-v1.json`. Initial
  actor 114743 (hash 014a86a1...220615); training-only critic from PPO
  104524, hash `377d21179b7b33c6adf8d14debda1e0e0400d89a8336902bb0f82c67201ea8eb`.
  Two updates, 256 requested rallies each, finishing the current game.
  Opponents: saved copy of initial actor, then older PPO 094032. Training
  seeds 1075000 and 1076000; small development checks 1175000 and 1176000.
  All action heads train on full-game team-win rewards, gamma=lambda=1,
  raw advantages, zero entropy coefficient, four epochs, batch 1024,
  LR 0.00003, clip 0.1 and post-update KL rollback at 0.01. No selector.
- ACTIVE process **75488**, `training-loop-20260907-120308`.
  At 12:04:04 UTC, the authoritative Unity reader confirmed the actual
  `PlayerCompetition.Tick` callback is live. The latest driver output was
  15/256 rallies in the first collection. Do not restart this loop. Do not
  start another Unity job between its collection, fitting, parity and
  development stages. Preserve all active trainer dependencies.
- NEXT: poll process 75488. After terminal completion, audit the complete
  loop with `player_self_play_audit.py` and the new frozen plan. Replay
  team rewards, carried critic values, actor likelihoods and lineage.
  Repeat the same 36 serves, 64 short/deep cases and eight full development
  games for its final actor. Compare with initial weighted actor 114743,
  parent 104524 and older 094032. Pre-update self-play wins are not proof
  that an update improved the model. Retain all failures; no promotion.
- All 282 Python tests pass; 63 baseline files unchanged; no final plans
  exist; diff whitespace check passes. Runtime remains 7a998e12...fad845.
  No saved-scene, physics, controller, final-seed, paid-compute, publication
  or cleanup changes. Goal active and incomplete.

## Previous verified state — 2026-09-07 11:57 UTC

- Near-contact weighted fit session 41871 completed successfully.
  Actor `contact-movement-fit-20260907-114743/actor.json`, hash
  `014a86a1608532ed72845813973e0e3448ef9591d6b79e1c96766561dd220615`.
  Fitting took 114.354 seconds for 200 epochs / 29,800 updates. Selection
  chose epoch 150. Independent audit
  `near-contact-movement-fit-audit-20260907.json` replays source selection,
  input hashes, weighted development losses, exact frozen hidden/hit/shot
  parameters and all collection motors. The primary actor-state banks
  are not new: 2,187 training and 702 development primary rows receive
  near-contact weighting. All other source rows and weights are recorded.
  Unity parity passes all 32 cases, maximum error 0.00000190735.
- Serve probe `serve-return-20260907-115147.json` is terminal and audited.
  Fixed-choice model: 12 hits and 7 landings out of 12, versus 12 and 5
  for the unweighted movement fit. Sampled model: 12 hits and 5 landings,
  versus 12 and 7. The sampled result regressed. Teacher controls and all
  physical limits pass. Audit `near-contact-movement-serves-audit-20260907.json`.
- Short/deep probe `teacher-gap-20260907-115344.json` is terminal and
  audited. Deep: 12/16 hits and 9/16 landings, versus 13 and 8 unweighted.
  Short: 16/16 hits and 15/16 landings, versus 16 and 12 unweighted.
  All 32 teacher controls match exactly; actor replay and all motor checks
  pass. Audit `near-contact-movement-returns-audit-20260907.json`.
- ACTIVE eight-game comparison process 33192. It evaluates the weighted
  actor against the unchanged baseline at development seeds 1141000..1141007,
  both court ends and baseline modes, with identity swaps. Poll this exact
  driver; do not restart it. No competitive improvement is claimed yet.
  No new team-win training is started before this comparison finishes.
- Goal active and incomplete. No candidate promoted, no runtime or scene
  change, no baseline overwrite, no final seeds, no paid compute or cleanup.

## Previous verified state — 2026-09-07 11:48 UTC

- Previous turn was progress: it saved and tested a movement-corrected
  model, retained its failed full-game result, and narrowed the contact
  diagnosis. Unity was rechecked idle at 11:38:42 UTC. Runtime remains
  `7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
- New `player-serve-window-probe.cs` completed 60 matched cases as
  `serve-window-20260907-114207.json`. Modes 0/1/2 exactly match the
  original deterministic, sampled and teacher controls. In mode 3, only
  the receiver receives zero movement during the final 200 ms before
  planned impact through 55 ms after it. Mode 4 uses teacher movement
  only in that interval. Both use ordinary 20 Hz decisions, 25 ms latency,
  and all physical constraints. No body teleport, forced stop, ball
  change, hit/shot replacement or runtime selector is used.
- Audit `serve-window-audit-20260907.json` passes source/model/reference
  hashes, all motor checks, action-component checks, window gates, and
  actor replay. Deterministic 5/12 landings; stop control 6/12; late
  teacher movement 7/12. All modes contact 12/12. Late foot commands do
  not solve the failure. These controls remain diagnostic only.
- Contact-point velocity now includes angular velocity cross offset,
  checked against `PlayerBody.ContactVelocity`. All seven deterministic
  failures have zero angular velocity at contact. Hand reach is about
  0.602–0.603 m, and reconstructed stopped-posture braking slack is within
  0.00005 m/s of zero. This strongly points to insufficient reach reserve.
  It is not a record of the exact projection trial. The hard 0.62 m reach,
  100 m/s² paddle acceleration and all other limits remain unchanged.
- Froze `near-contact-movement-v1.json`. Reuse the same four training and
  four development banks and parent actor 104524. Train the same two
  movement output rows only. Multiply movement loss by 16 for rows with
  expected team, teacher attempt, ball height 0.1–2 m and horizontal ball
  distance at most 1.5 m. These conditions use recorded own-player inputs
  and training labels, never diagnostic rows. This tests near-contact
  precision before altering any physical controller.
- ACTIVE fit session 41871, `contact-movement-fit-20260907-114743`.
  The fitter is `player-agents-fit-contact-movement.py`; independent audit
  is `player_contact_movement_fit_audit.py`. The earlier unweighted fitter
  and audit are preserved so their frozen input hashes remain valid.
  After fitting, check exact non-movement parameters and Unity parity,
  then repeat the same 36 serves, 64 short/deep fixtures and eight full
  development games. Do not promote on prediction loss alone.
- All 282 Python tests pass; 63 baseline files remain unchanged; diff
  whitespace check passes. No runtime, saved scene, final seeds, paid
  compute, publication or cleanup. Goal active and incomplete.

## Previous verified state — 2026-09-07 11:37 UTC

- The complete actor-state movement trial is terminal. Unity was checked
  idle at 11:35:15 UTC. No training or diagnostic job needs a restart.
  The goal is active and incomplete. The new actor is not promoted.
- Eight full development games in `development-evaluation-20260907-112817`
  passed the schedule, source/model hashes, complete outcomes, player
  identities and candidate motor audit. Results: 0/8 wins, 13/118 rally
  wins, 259 legal returns, five no-point truncations, 154.280 seconds.
  Parent 104524 had 0/8 wins, 16/124 rally wins and 285 legal returns.
  Better serve contacts did not transfer to better match play. Retain the
  failed candidate and `actor-state-movement-games-audit-20260907.json`.
  Completion hash: `0dbcc901f37ddca483b890a918ad939ad337451c005210155638549b16f5bdb6`.
- Short/deep diagnostic `teacher-gap-20260907-112638.json` is audited in
  `actor-state-movement-returns-audit-20260907.json`. Deep: 13/16 hits,
  8/16 landings, versus parent 13/16 and 6/16. Short: 16/16 hits,
  12/16 landings, versus parent 15/16 and 15/16. All 32 teacher controls
  match exactly; 2,406 actor decisions replay; all motors pass. This is
  mixed skill transfer, not a retained-skill or match-strength pass.
- New read-only `player-serve-contact-probe.cs` records receiver state
  immediately before and after the physical return. It changes no action,
  collision, plan or ball. Report `serve-contact-20260907-113424.json`
  completed and exactly matched all 36 original cases, including events,
  contacts, starting state and decision count. Audit replays 5,168 actor
  decisions, checks the one-physics-step timestamps and all motor limits.
  Report hash: `5418b8936e340f7e8ba72528dfb6376e037dda98ff6b0b0eb9d16a7051188156`.
- Contact audit and analysis are saved as `actor-state-movement-contact-audit-20260907.json`
  and `actor-state-movement-contact-analysis-20260907.json`. All seven
  deterministic WrongSide returns contact 17–30 ms AFTER the planned
  impact time, inside the bounded 55 ms follow-through. The paddle-centre
  velocity projected onto the planned normal is below planned swing speed
  by 0.38–1.45 m/s. This is translational centre velocity, not complete
  contact-point velocity. Rotation is not accounted for in that comparison.
  These observations rule out pre-swing contact in this fixture set, but
  do not isolate foot motion, reach limiting, rotation or target tracking.
- The new approach audit shows the former 39–47 cm forward error is much
  smaller. This supports contact improvement but does not prove a robust
  hitting policy. Do not run another identical PPO loop based on these
  drill gains. Next: isolate the foot-motion / bounded-paddle execution
  interaction during the committed swing window. Record contact-point
  velocity and physical limiter state. Use a matched diagnostic control
  before deciding whether to change training weights or the bounded swing.
  No central hitter selection, runtime teacher recovery or physics steering.
- All 275 Python tests pass. No runtime, saved scene, ball settings or
  baseline model changed. Final seeds remain unused. No paid compute,
  publication or cleanup. Preserve all trial artifacts. Fitter and its
  independent auditor are `player-agents-fit-movement.py` and
  `player_movement_fit_audit.py`; the frozen plan is `actor-state-movement-v1.json`.

## Previous verified state — 2026-09-07 11:27 UTC

- Both actor-state collections completed without teacher execution.
  Training `curriculum-20260907-111706.json`: 256 rallies, 68,416 actor
  decisions, 226.911 seconds, 301.51 decisions/second. Development
  `curriculum-20260907-112139.json`: 64 rallies, 18,768 actor decisions,
  62.478 seconds, 300.39 decisions/second. Both include serve-flight,
  return-flight and rally states. These are local collection measurements,
  not cloud estimates. All four player motor checks pass.
- Saved `movement-fit-20260907-112323/actor.json`, SHA-256
  `68619f6f49f1175751f7f095555c43e129a0aaf4d136aef3936b5cab63e6bc30`.
  Fit 200 epochs / 29,800 optimizer updates in 39.323 seconds. Development
  selection chose epoch 168 / update 25,032. Audit
  `actor-state-movement-fit-audit-20260907.json` replays selection from all
  eight validated source banks and checks source, parent, plan and trainer
  hashes. Only the two final movement rows and biases changed. Hidden,
  hit/shot and exploration parameters remain exact. Same-input hit/shot
  outputs match exactly; changed trajectories can still change decisions.
- Actor-state development movement loss improved 0.63054 to 0.39794.
  Older normal-bank movement loss worsened 0.03792 to 0.09544. Short/deep
  prediction losses also increased slightly. No behavioral retention is
  inferred from the selected prediction loss. Unity parity passes all
  32 cases, maximum error 0.00000190735.
- Real serve report `serve-return-20260907-112520.json`, hash
  `157cd33601f4915e8d581e4c54c3acce2cb899ad08a4709c4fda50f6c632bbff`.
  Audit `actor-state-movement-serves-audit-20260907.json`: deterministic
  12/12 hits, 5/12 landings; sampled 12/12 hits, 7/12 landings. Parent
  104524 had 6/12 hits, 3/12 landings and 7/12 hits, 5/12 landings,
  respectively. All remaining faults are WrongSide. Teacher control is
  unchanged at 12 hits / 11 landings. All motor checks pass; 5,168 actor
  decisions replay. This is better serve contact, not match-strength proof.
- ACTIVE short/deep diagnostic `teacher-gap-20260907-112638.json` started
  at 11:26:38 UTC. Audit this exact report after its callback ends. Then
  complete the same eight development games at 1141000..1141007. No scene
  or runtime change, baseline replacement, final seeds or paid compute.
  Goal active and incomplete; candidate not promoted.

## Previous verified state — 2026-09-07 11:20 UTC

- Resumed the pending serve-action diagnosis. Unity was idle at 11:13:44 UTC.
  The previous job had completed as `serve-action-20260907-110702.json`.
  It was not restarted. Audit `serve-action-audit-20260907.json` verifies
  all 60 cases, exact matches to the original 36 control outcomes, 9,060
  actor decisions, 2,540 separately labelled teacher decisions, and motor
  limits. Physical serve difference is zero. Report SHA-256:
  `094e4ca03c2c8d1aecbe55b6b09396ba43753a42ad89be9f48864c683bbef7e8`.
- Deterministic actor: 6/12 hits and 3/12 landings. Replacing only the
  designated receiver's movement with teacher movement gave 12/12 hits
  and landings. Replacing only its shot gave 11/12 hits and 8/12 landings.
  Other players and the receiver's hit/leave action remain actor-controlled.
  These are privileged diagnostic interventions, not deployable results.
  The six original body-contact failures had a 39–47 cm forward-position
  gap against the teacher in `serve-approach-audit-20260907.json`.
- Fixed a valid audit edge case: the decision loop validates an already
  bounded action again. Float32 movement on the unit circle can change by
  about 0.00000015. The audit now accepts only this narrow normalization
  case. Shot and hit/leave must still match exactly; model replay remains
  required. Two tests reject unrelated movement drift and discrete changes.
- Froze `config/player-agents/actor-state-movement-v1.json`. Collect all
  phases from four deterministic copies of actor 104524. Teacher probability
  is zero: the teacher supplies labels but executes no action. This differs
  from the earlier learner-state trial against a frozen baseline opponent.
  Training seed 1097000, 256 rallies; development seed 1197000, 64 rallies.
  No diagnostic or final observations enter training.
- ACTIVE `PlayerCurriculum` collection started 11:17:06 UTC. At 11:20:07
  it reported 202/256 rallies, 54,300 rows and 305 learner-side returns.
  Poll this exact job; do not restart. After completion, collect the separate
  development bank. New external fitter trains only the two final movement
  rows and biases using current-state labels plus normal, short and deep
  retention banks. Hidden layers, hit/shot rows and exploration stay exact.
  No selector or runtime teacher movement will be installed.
- All 272 Python tests pass. The baseline's 63 files remain unchanged.
  Runtime remains `7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
  The goal remains active. Match improvement, final evaluation and final
  playable acceptance are still unproved. No paid compute or scene changes.

## Previous verified state — 2026-09-07 10:57 UTC

- All work in the serve-correction and two-update self-play trial is terminal.
  Unity was checked idle at 10:55:58 UTC; there is no job to restart.
  The goal remains active and incomplete. No candidate is promoted.
- Final actor 104524 completed `development-evaluation-20260907-105212`.
  Audit `serve-retention-self-play-games-audit-20260907.json` passed the
  exact schedule, artifact hashes, complete game outcomes, player identity
  assignments and candidate motor limits. Completion SHA-256
  `1cb387df9fa40bc6d2bb251ecc366519bfa6babd4798aa6eb3c130938aa2c122`.
  Results: 0/8 wins, 16/124 rally wins, 285 legal returns, six no-point
  truncations, 158.531 seconds. Starting actor 102622 had 0/8 wins,
  28/151 rally wins and 320 returns; original parent 094032 had 0/8 wins,
  51/185 rally wins and 497 returns. This trial did NOT establish better
  baseline match play. Retain both checkpoints and every failed result.
- Final real-serve probe `serve-return-20260907-104756.json`: deterministic
  6/12 hits, 3/12 legal landings; sampled 7/12 hits, 5/12 landings. Compared
  with starting actor 102622, one landing was lost in each mode. Both
  deterministic receivers facing service seats 1 and 3 failed all fixtures.
  Teacher controls still match exactly (12 hits, 11 landings); 4,176 actor
  decisions replay and all four motors pass. Audit
  `serve-retention-self-play-serves-audit-20260907.json`.
- Final short/deep probe `teacher-gap-20260907-104927.json`: deep 13/16
  hits, 6/16 landings; short 15/16 hits, 15/16 landings. Landing counts match
  initial actor 102622 and original parent 094032. All 32 teacher controls
  match; 2,356 actor decisions replay; all four motors pass. Audit
  `serve-retention-self-play-returns-audit-20260907.json`.
- Next safe step: inspect the saved matched serve trajectories for failed
  receivers, comparing their own movement and paddle approach with teacher
  controls. Use the evidence to choose a specific collection/model change;
  do not launch another identical PPO loop or use diagnostic rows as training
  data. In particular, check whether actor-visited return states differ from
  pure-teacher lessons before planning new mixed-policy collection. Existing
  earlier mixed-policy trials must be checked before claiming a new approach.
- Final checks: 258 Python tests pass; baseline 63 files unchanged;
  `git diff --check` passes. Runtime source remains
  `7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
  No physics/controller change, selector, scene replacement, final seeds,
  paid compute, publication or cleanup. The original demo remains intact.

## Previous verified state — 2026-09-07 10:48 UTC

- Self-play driver session 80891 exited successfully. Loop
  `training-loop-20260907-103902` passed the complete audit in
  `serve-retention-self-play-audit-20260907.json`: frozen opponents, seed
  partitions, full-game reward and carried critic replay, actor likelihoods,
  candidate/opponent physical limits, trainer lineage, and Unity parity.
- Iteration 1: nine training games, four wins before update, 261 rallies,
  29,810 rows, 18 separate player trajectories. Collection 153.012 seconds.
  Actor `ppo-20260907-104158/actor.json`, hash
  `7ab54cc70381bca3e83aad835f919d876444a6fd255a4b8460a2d515889d169d`.
  120 accepted updates, 12,054 positive and 17,756 negative advantage rows;
  final KL 0.0024558525. Fit 10.413 seconds. Both small baseline check games
  lost (1-11 and 11-0). All 32 parity cases pass.
- Iteration 2: 12 training games, nine wins before update, 270 rallies,
  28,490 rows, 24 player trajectories. Collection 144.529 seconds. Final
  actor `ppo-20260907-104524/actor.json`, hash
  `4204bf92906ceed70f627e9371d62192de683e85fec92d40ab3df13dfd417833`.
  112 updates, 17,756 positive and 10,734 negative advantage rows; final KL
  0.0024056872. Fit 9.118 seconds. Three small baseline check games all lost
  (1-11, 11-0, 0-11). All 32 Unity parity cases pass, max error 0.0000038147.
- Do not call the pre-update wins an improvement from RL. The first
  collection still had 101/261 serve-only rallies; the second had 142/270.
  No baseline-winning model has been proved and no model has been promoted.
- ACTIVE real-serve diagnostic `serve-return-20260907-104756.json` for
  final actor 104524. Next: audit this same job after it completes, then run
  the frozen 64 short/deep controls and eight full development games if motors
  pass. The driver is terminal; Unity diagnostic jobs must remain sequential.
  Runtime, baseline, final seeds and playable demo remain unchanged.

## Previous verified state — 2026-09-07 10:39 UTC

- Four-source actor 102622 completed all eight development games in
  `development-evaluation-20260907-103402`. Audit
  `serve-retention-games-audit-20260907.json` passed provenance, schedule,
  completed game outcomes, player identities and candidate motor checks.
  Results: 0/8 wins, 28/151 rally wins, 320 legal returns, five no-point
  truncations, 187.263 seconds. Completion SHA-256
  `fc5549b0f06628612704858bea6a8f0eddff3d30f567ff9ab2986f06c1d4273d`.
  Scores: 3-11, 0-11, 11-1, 11-1, 1-11, 0-11, 11-0, 11-0 in group order.
  This recovers part of the three-source regression (212 returns), but remains
  below original parent 094032 (497 returns, 51/185 rally wins, 0/8 games).
  No candidate is promoted. Better serves are not broad match-strength proof.
- Froze `config/player-agents/serve-retention-self-play-v2.json`, SHA-256
  `dfc148e5a2c4847761ecbbb22330e1ba0b5f5506001ced524a1c5431a163561b`.
  Experimental initial actor 102622; carried critic from 094032, hash
  `33c6227506d454e628442d3bc27bc052489ada03bf51c4cc97b6a4af8422a2f8`.
  Two game-win PPO iterations, 256 rallies each (finish the current complete
  game), fixed opponents 102622 then 094032. Training seeds 1095000/1096000;
  separate small development checks 1186000/1187000. Four epochs, batch 1024,
  LR 0.00003, all action heads, raw full-game advantages, no entropy bonus,
  clip 0.1, target KL 0.01 and post-update rollback. No runtime selector.
- ACTIVE process session **80891**, folder
  `artifacts/player-agents/training-loop-20260907-103902`.
  At 10:39:25 UTC the actual `PlayerCompetition.Tick` callback was live;
  the driver reported 14/256 rallies in the first collection, no completed
  games yet. Do NOT restart this sequence. Do not start another Unity job
  between its collection, fitting, parity and development stages.
- NEXT: poll that exact process and authoritative job reader. After terminal
  completion, run `scripts/player_self_play_audit.py` on the loop and frozen
  v2 plan; save its audit. Test its final actor with the SAME 36 serve-return
  and 64 short/deep controls, then eight development games 1141000..1141007
  if motors pass. Compare to both 102622 and 094032. No final seeds used.
- The new serve bank includes receiver examples for all four seats
  (715, 681, 1,385, 1,211 decisions). This does not prove balanced coverage.
  All 258 Python tests pass, `git diff --check` passes, and baseline 63 files
  were rechecked unchanged. Runtime remains 7a998e12...fad845. The playable
  scene/model is unchanged. The goal is active and incomplete.

## Previous verified state — 2026-09-07 10:34 UTC

- Four-source fit completed as `imitation-20260907-102622/actor.json`, SHA-256
  `ba0050b42363519eecc41af196a8e416dad1b673046455b0a23833a18656824a`.
  Frozen plan SHA-256 `0ec5f92a977728cbbd32cbdad8c1c6ec39a83a0f368771cd44b944158b1eb5af`.
  Selected epoch 16 of 60, 1,568 selected steps, 5,880 total updates;
  99,906 training rows and 41,324 development rows; fit took 58.455 seconds.
  Audit `serve-retention-fit-audit-20260907.json` passed, including phase
  coverage, teacher motors, selected loss replay and 32 Unity parity cases.
- Real-serve probe `serve-return-20260907-102859.json`: deterministic 7/12
  hits and 4/12 legal returns; sampled 7/12 hits and 6/12 returns. These
  remain above parent 094032's 0/12 and 2/12 landings but below three-source
  100955's 9/12 in both modes. All teacher controls match. Replayed 4,188
  actor decisions; all four motors pass. Audit `serve-retention-returns-audit-20260907.json`.
- Short/deep probe `teacher-gap-20260907-103154.json`: deep 13/16 hits,
  6/16 legal landings; short 15/16 hits, 15/16 landings. Landing counts match
  parent 094032. All 32 teacher controls match and 2,334 actor decisions
  replay; all four motors pass. Duration 36.599 seconds. Audit
  `serve-retention-short-deep-audit-20260907.json`. An early audit correctly
  rejected the still-running report; the same completed report then passed.
- ACTIVE eight-game development evaluation:
  `development-evaluation-20260907-103402`, actor 102622, same seeds
  1141000..1141007, both baseline modes and court ends, half identity swaps.
  No contact override, runtime edit, scene installation or final evaluation.
  Next: wait on the existing generated TickFinal callback, audit completion,
  compare with parents, then choose the next game-win training stage.
- All 258 Python tests pass; baseline 63 files unchanged at the earlier check.
  Runtime hash remains 7a998e12...fad845. Disk free was 8.1 GiB at 10:27 UTC.

## Previous verified state — 2026-09-07 10:25 UTC

- Corrective actor 100955 completed the same eight development games in
  `development-evaluation-20260907-102042`: 0/8 wins, zero score points in
  every game, 10/114 rally wins, 212 legal returns, zero truncations. Parent
  094032 had 51/185 rally wins and 497 returns on the same seeds. The new
  actor is not promoted. Completion SHA-256
  `7f859fd380157f98fcd02cc8369b56df41892dcb2bb149f0f95b1072cee4c528`.
  Audit: `serve-curriculum-games-audit-20260907.json`; candidate motors pass.
- Short/deep probe `teacher-gap-20260907-101825.json` completed and passed.
  Actor deep: 12/16 hits, 7/16 legal landings. Short: 15/16 hits, 14/16
  landings. Parent landings were 6/16 deep and 15/16 short. All 32 teacher
  controls match; 2,324 actor decisions replay; all four motors pass.
  Audit: `serve-curriculum-retention-audit-20260907.json`.
- Source inspection found ZERO returnFlight examples in the three-bank
  corrective fit. Its primary 15,968 rows were serveFlight; the 13,406 short
  and 10,656 deep rows were all rally phase. Thus the third-shot phase was
  absent. This supports a coverage/forgetting hypothesis, not sole-cause proof.
- Frozen `config/player-agents/serve-return-retention-v2.json`: reuse the
  same parent 094032, serve/short/deep banks, and optimizer settings; add the
  existing normal training bank 043639 and development bank 044309 as a
  fourth equally sampled source. No fresh data collection or runtime change.
  The normal training bank adds 7,414 returnFlight examples and 44,308 rally
  examples. Required phase coverage is now audited in both source partitions.
  All 258 Python tests pass. Audit source count follows the exact frozen plan;
  extra, reordered, wrong-primary, ambiguous and absent-phase cases are tested.
- Next: finish the four-bank source preflight; run the 60-epoch local fit,
  audit Unity parity and selected loss, then repeat the SAME physical and
  eight-game development checks. Keep both failed and improved artifacts.

## Previous verified state — 2026-09-07 10:18 UTC

- Resumed the existing refresh runner 87683. It exited successfully; no
  collection was restarted. The preceding conversational turn added no
  implementation evidence. This continuation completed the saved fit audit.
- New actor `imitation-20260907-100955/actor.json`, SHA-256
  `8e8c74b2a74952e22039a6278ceedf3ed7f26aa0149e9da4ec74aa93b54c917c`.
  This is a supervised corrective fit, not a new team-win RL update.
  Audit `serve-curriculum-fit-audit-20260907.json` verifies source partitions,
  selected serve-flight row identities, four-player teacher motor limits,
  parent/trainer hashes, selected-epoch loss replay, and 32 Unity parity cases.
  Training: 40,030 selected examples; development: 9,950 examples. Selected
  epoch 9 of 60, 360 selected fit-local steps, 2,400 total optimizer updates.
  Fit time 39.156 seconds. Unity maximum output error 0.0000038147.
- Primary collection completed 128 training rallies in 560.626 seconds and
  32 development rallies in 126.631 seconds. Of 188,564 training rows,
  15,968 serve-flight rows were selected, including 3,992 receiver decisions.
  Development selected 4,004 of 36,880 rows. Short/deep retention banks remain
  separate. Diagnostic fixtures and final seeds did not enter training.
- Completed real-serve probe `serve-return-20260907-101621.json`, audited in
  `serve-curriculum-returns-audit-20260907.json`. Exact physical serve controls
  match. Deterministic actor: 12/12 hits, 9/12 legal landings (parent 0/12).
  Sampled actor: 11/12 hits, 9/12 legal landings (parent 2/12). Teacher remains
  12/12 hits, 11/12 landings. Replayed 5,096 actor decisions; all four motors
  pass. Duration 25.717 seconds. This is a matched diagnostic improvement,
  not evidence of improved full-game win rate or final acceptance.
- Short/deep retention probe now running with the same frozen fixtures.
  Next: audit its result, then run the unchanged eight development games.
  The demo model and baseline 63 files remain unchanged. No promotion.

## Previous verified state — 2026-09-07 10:02 UTC

- Completed self-play actor 094032's full development run
  `development-evaluation-20260907-094502`. Completion SHA-256
  `8b7b25b952f1c19ee27c0ec89c4545cc581a73aad35caa8d10e9bdaf70affe9d`.
  Zero wins in eight complete games, 51/185 rally wins, 497 legal returns,
  14 no-point truncated rallies. Candidate motors pass. Duration: 330.594
  seconds. Some scores improved, others fell; no broad match-strength claim.
  Audit: `single-policy-self-play-games-audit-20260907.json`.
- New isolated probe `scripts/player-serve-return-probe.cs` tests 12 real
  independent-controller serves across all four service seats and three
  jitters. Modes: deterministic actor, sampled actor, privileged teacher.
  No injected ball state, changed contact settings, or runtime selector.
  Only service-seat dead-ball transitions occur before each actual serve.
- Probe `serve-return-20260907-095109.json` completed 36 cases in 19.690
  seconds. Physical serve contact states match EXACTLY across all modes.
  All 36 serves landed legally. Deterministic actor: 0/12 return hits and
  landings. Sampled actor: 2/12 hits and landings. Teacher: 12/12 hits,
  11/12 legal return landings. Deterministic failures: seven BodyContact,
  five Out. Four motor checks pass. Auditor `scripts/player_serve_return.py`
  replayed all 3,740 actor decisions and checked 2,540 labelled teacher
  decisions separately. Likelihood error: 0.0000104904.
  Audit: `serve-return-audit-20260907.json`, report SHA-256
  `4ea277248961e4ef03dbad1069ce895843cfaf2d518e0df52eefa5df2866a44c`.
- The previous normal training bank 043639 used frozen-baseline opponents.
  Its serve-flight states therefore do not establish coverage of the
  independent-controller serves used by self-play. This distribution gap is
  a plausible cause, not a proven sole cause. The matched teacher controls
  show that the current physical limits permit these returns.
- Froze `config/player-agents/serve-return-curriculum-v1.json`: a new four-
  player teacher curriculum using real independent-controller serves.
  Training seed 1091000, 128 rallies; separate development seed 1194000,
  32 rallies. Teacher probability 1, fixed shot -1, baselineOpponent false.
  No diagnostic or final data enters training. Primary bank selection uses
  phase.serveFlight at observation index 40; it retains owned labels and
  records a hash of selected row indices. Separate short/deep banks remain.
- ACTIVE runner process session 87683:
  `artifacts/player-agents/refresh-20260907-100110`. It is attached to the
  EXISTING live `PlayerCurriculum` job, not a new copy. Pending training report:
  `artifacts/player-agents/curriculum-20260907-095746.json` (data .jsonl exists;
  the report is written on completion). At 10:01:29 UTC collection had 42/128
  rallies, 68,716 rows, and 593 teacher-side returns. These are teacher results,
  not learned-model results. Recheck this exact runner and Unity job; do not
  restart them because the pending report is absent.
- The attached runner will validate the teacher motors, collect development
  lessons, fit 60 epochs from actor 094032, verify Unity parity, and run the
  existing 32-rally sampled-baseline check at seed 1191000. Fit: width 256,
  batch 1024, LR 0.0003, neutral-paddle probability 0.5, balanced three sources,
  no soft retention penalty. This is supervised corrective training, not RL.
  Added four-player and phase-selection options to existing trainers; defaults
  retain the earlier paths. All 254 player Python tests pass, including new
  event-outcome, phase-filter, and explicit four-player-mode tests.
- NEXT after runner completion: audit fit and selected source rows; run the
  same 36 serve-return controls and 64 short/deep controls; audit all motor
  and policy traces; then run the unchanged eight development games if motors
  pass. Do not promote from teacher accuracy alone. No new model exists yet.
- Baseline 63 files unchanged; `git diff --check` passes. Runtime remains
  `7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
  Disk free at 10:01 UTC: 8.4 GiB. No cleanup or cloud work is authorized.
  Final evaluation seeds and playable scene/model remain unchanged.

## Previous verified state — 2026-09-07 09:47 UTC

- The two-iteration self-play driver `training-loop-20260907-093513` completed.
  Terminal process session 86516 exited 0. Audit:
  `single-policy-self-play-audit-20260907.json`, produced by
  `scripts/player_self_play_audit.py`. The audit replays the initial carried
  critic values, complete-game advantages, and parent sample likelihoods.
  It checks actor lineage, fixed opponents, source/trainer snapshots, motor
  limits, seed partitions, and Unity parity. It does not replay every Adam step.
- First update: actor 093702, hash
  `6e6322bdd6a5c6ee7dd4d2202b58fa4b214b8b4ed4087eacafd7367638d5c01b`,
  56 accepted updates. Second collection: six games, three wins and three
  losses against the older actor, 16,096 rows, 111.425 seconds. These wins
  occurred BEFORE the second update, on different seeds from earlier runs.
  Do not interpret them as a paired playing-strength improvement.
- Second update: `artifacts/player-agents/ppo-20260907-094032/actor.json`, hash
  `58a5a4ad51bf77ab4259a251ede4ddca69729ea717e7c0c74bfe2c95f286b93a`.
  64 accepted updates, 9,286 positive and 6,810 negative advantages. Final KL
  0.002373277, below 0.01. Fit: 5.050 seconds. Unity parity: 32 cases passed,
  maximum error 0.000007629. Both small post-update baseline checks lost all
  their games: three for the first update and two for the second.
- Return probe `teacher-gap-20260907-094301.json` completed in 42.231 seconds.
  All 32 teacher controls match the reference; all 2,306 actor decisions
  replay; four motor checks pass. Deep: 12 hits, 6 legal landings in 16 cases.
  Short: 16 hits, 15 legal landings in 16 cases (one fewer than parent 091227).
  Audit: `single-policy-self-play-returns-audit-20260907.json`.
- ACTIVE Unity job: `development-evaluation-20260907-094502`, actor 094032,
  unchanged eight development seeds 1141000..1141007. At 09:46:34 UTC the
  generated `TickFinal` callback was live in group 1. Do not restart it.
  Next: wait on this job, then audit completion with `verify_run` from
  `scripts/player-compare-models.py` and retain no-point truncations.
- The self-play audit exposes weak serve-return play. Two of the initial
  self-play wins recorded ZERO candidate legal returns. In that collection,
  82/137 rallies ended with one rule-counted hit: 57 BodyContact and 25 Out.
  This is evidence against treating self-play wins alone as skill progress.
  Further serve-return diagnosis is the next candidate step if the full-game
  comparison also fails. No new drill, sampling change, controller change,
  reward shaping, or model promotion has been applied.
- All 248 player Python tests pass. Baseline manifest remains 63 unchanged
  files; `git diff --check` passes. Runtime source remains 7a998e12...fad845.
  Final evaluation seeds remain unused. The playable demo model is unchanged.

## Previous verified state — 2026-09-07 09:41 UTC

- Completed and audited the corrected model's eight development games:
  `development-evaluation-20260907-092217`, completion SHA-256
  `14ad1c558f8dd9c2b137c2d1b1f69f5948127e7a8fe7d13e63ad81b62d0e9f14`.
  Zero game wins, 47/175 rally wins, 450 legal returns, ten no-point truncated
  rallies. Candidate motor checks pass; frozen baseline motor differences
  remain separately recorded. Duration: 373.630 seconds. The distilled parent
  had 0/8 game wins, 32/149 rally wins, and 333 legal returns. More returns in
  this development run do not prove general improvement or final acceptance.
  Audit: `game-win-correction-games-audit-20260907.json`.
- Froze `config/player-agents/single-policy-self-play-v1.json`: two complete-game
  PPO collections, first against a frozen copy of the initial model, then the
  older 032230 actor. Four independent actors; no runtime selector. Carry the
  critic; raw advantages; zero entropy bonus; no physics/controller changes.
  Training seed bases 1088000 and 1089000. Small development checks use 1189000
  and 1190000. Final seeds stay unused.
- Initial attempt `training-loop-20260907-093021` stopped before collection.
  The CLI discovery file was missing, while Unity PID 1955 still listened on
  port 7800. Pipeline reported no Safe Mode. The computer-use skill restored
  the connection with Window > Pipeline > Stop Server, then Start Server.
  No Editor restart, package update, or scene save was needed for that recovery.
  At 09:34:41 UTC no training job was running, and the last
  competition report was still 090515. The failed attempt is retained.
- ACTIVE driver session 86516: `training-loop-20260907-093513`. Recheck this
  exact session/job before another collection. First self-play collection
  `competition-20260907-093514` completed eight games: three candidate wins,
  five losses, 13,436 rows, 95.619 seconds. These are PRE-UPDATE outcomes.
  Actor `ppo-20260907-093702` applied 56 updates with 3,538 positive and 9,898
  negative advantages. Its three small baseline development games all lost.
- Second training collection `competition-20260907-093821` and actor update
  `ppo-20260907-094032` are complete. At 09:40:39 UTC the driver's second
  development check was running. Whole-loop audit, return retention, and
  full eight-game development comparison remain to do. No model promoted.
- Added explicit entropy/advantage options to the driver and initial critic
  hashes to optimizer provenance. Added `scripts/player_self_play_audit.py`
  to verify carried-critic advantages, player reward ownership, likelihoods,
  frozen opponents, and exports. Three signal tests and one CLI validation
  test pass. All 248 player Python tests pass. Baseline 63 files unchanged.

## Previous verified state — 2026-09-07 09:26 UTC

- Continue with one complete player policy and separate player decisions.
  No further selector fitting, controller changes, or model promotion.
- Audited the first complete-game PPO cycle `training-loop-20260907-090342`.
  Its seven training games all lost. The new critic produced zero values.
  Centering the constant negative advantages removed every reward-derived
  actor gradient. Retained and rejected the entropy-only checkpoint
  `ppo-20260907-090512`. Audit: `game-win-zero-signal-audit-20260907.json`.
- Corrected alternative: `ppo-20260907-091227/actor.json`, SHA-256
  `8a8ee9b824d607f69f8e753944b01d5ec9603d67983e980e73b0f30b1986c6f2`.
  It starts from the original distilled parent, not the rejected update.
  Plan: `config/player-agents/game-win-correction-v1.json`. Same original
  on-policy data: seven games, 15,298 rows, 14 separate player trajectories.
  Raw negative advantages, no entropy bonus, all action heads, 60 updates.
  This is a high-variance all-loss estimate, not evidence of improved play.
- New read-only correction audit verifies frozen inputs, trainer snapshots,
  player reward ownership, parent sample likelihood, and final checkpoint KL.
  Final measured KL: 0.0024518424, below 0.01. Fit: 14.506 seconds.
  Unity parity: 32 cases passed, maximum output error 0.000003815.
  Audit: `game-win-correction-audit-20260907.json`. It does not replay each
  optimizer step or certify match strength.
- Return probe `teacher-gap-20260907-091932.json`: 32 exact teacher controls,
  2,312 independent actor decisions replayed, all four motor checks passed.
  Deep: 12 hits and 6 legal landings in 16 cases (2/8 and 4/8 across ends).
  Short: 16 hits and 16 legal landings in 16 cases (8/8 on each end).
  Audit: `game-win-correction-returns-audit-20260907.json`.
- ACTIVE Unity job: `development-evaluation-20260907-092217`, eight unchanged
  development seeds 1141000..1141007. No final seeds. At 09:26:22 UTC the
  generated `TickFinal` callback was live, in group 4, score 2-7, 14 rallies.
  Do not restart it. Use `scripts/player-unity-job-status.cs`, then verify its
  completion and all eight reports with `player-compare-models.py::verify_run`.
  Game performance is still unverified. The demo has not loaded this model.
- Added zero-signal rejection and post-update KL rollback to the PPO trainer.
  This turn extracted the rollback step and added five tests. They check
  first-step rejection, existing Adam moments/counters, nonfinite KL, failed
  measurement, and accepted steps. The saved 091227 trainer snapshot remains
  unchanged. All 244 player Python tests pass. All 63 baseline files unchanged.
  `git diff --check` passes. Runtime source remains
  `7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
- User asked about progressing from drills to self-play. Recommended staged
  return training, short competitive points, then full games against recent
  and older saved policies. Keep separate fixed opponents for measuring
  improvement. Self-play score alone cannot prove progress. No larger run
  has started, and no cloud compute or new reward shaping was authorized.

## Previous verified state — 2026-09-07 09:00 UTC

- Completed one single-actor distillation trial. Plan:
  `config/player-agents/policy-distillation-v1.json`, hash
  `1a82c7c2592cfd367e7cf897241fcd4b522213ebd5ee9769e2e8697aee50ac77`.
  The older PPO actor supplies targets for normal and deep training examples.
  The short-return actor supplies targets for short-ball examples. Each example
  has one teacher. Unlike the earlier retention trial, the older model is not
  also imposed on short-ball examples. Teacher identity is not a model input.
- New model: `artifacts/player-agents/policy-distillation-20260907-085007/actor.json`,
  SHA-256 `bb958efac86a58764185b49444a8e8c5ff038c93fd5add010251cd090a90f745`.
  It is one ordinary `player-actor-v1` network: 54-256-256-12. Each player uses
  its own observations and actions. No runtime selector, central hitter choice,
  controller change, or added model input is present. Teacher paths in metadata
  describe training provenance only; Unity does not load them for inference.
- Fit: 83,938 training examples, 37,320 separate development examples, 60 epochs,
  4,920 optimizer updates, two CPU threads, 42.497 seconds for fit/export/checks
  after data loading. Equal expected source sampling and 50% neutral-paddle
  augmentation are recorded. Teacher targets are evaluated on the same original
  or augmented observation as the student. Epoch 59 was selected by the fixed
  equal-source development loss; its checkpoint contains 4,838 new updates.
  This is supervised skill transfer, not a new game-win RL update.
- Training audit replayed the selected checkpoint's development loss exactly:
  0.009610259595016638. All 48 Unity/Python parity cases passed, with maximum
  output error 0.000003815. Audit:
  `artifacts/player-agents/policy-distillation-audit-20260907.json`.
- Physical return test: `teacher-gap-20260907-085205.json`, 64 cases including
  32 exact sampled-teacher controls. The new actor made 12 hits and 6 legal
  landings in 16 deep cases, plus 16 hits and 15 legal landings in 16 short
  cases. Deep legal landings were 2/8 and 4/8 across ends; short landings were
  8/8 and 7/8. The saved older actor had 7/16 deep and 0/16 short landings.
  All 2,322 candidate actions replayed from their own observations. All four
  players' motor checks passed. Test duration: 32.929 seconds. Audit:
  `artifacts/player-agents/policy-distillation-returns-audit-20260907.json`.
- Full baseline evaluation: `development-evaluation-20260907-085437/`, unchanged
  development seeds 1141000..1141007, both ends, both baseline modes, and the
  existing identity-swap schedule. Zero wins in eight complete games, 32/149
  rally wins, and 333 candidate legal returns. Five no-point truncated rallies
  remain recorded. Candidate motor checks pass; frozen-baseline motor failures
  remain separately disclosed. Duration: 185.007 seconds. Completion hash:
  `c0798fb94f57a7a8f90be37a1d88a279f7065c54e0376abdabc74fa8c17b7677`.
  Audit: `artifacts/player-agents/policy-distillation-games-audit-20260907.json`.
  The older reference had 0/8 wins, 51/185 rally wins, and 402 legal returns.
  Do not promote this candidate or claim improved match performance.
- Fixed a diagnostic status blind spot with the new read-only
  `scripts/player-unity-job-status.cs`. Generated callbacks have names such as
  `<Execute>g__TickFinal|7`, so `StartsWith("Tick")` misses them. The new reader
  checks generated test owners and Picklebot callbacks, and excludes Unity's
  watchdog/auto-tick callbacks. Its generated-callback self-test passed. At
  08:58:45 UTC it reported Play active, busy false, and no test jobs. Use this
  reader before new jobs; old external snippets' start guards are not all fixed.
- All 232 Python tests pass (15.604 seconds), including eight new distillation
  tests. Baseline manifest: all 63 files unchanged. `git diff --check` passes.
  Runtime source remains `7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
  The Unity CLI skill was used only for isolated tests and model parity. No
  playable scene, runtime C# source, model asset, or final seed changed.
- Next bounded path: train the single actor from complete-game outcomes against
  a frozen older actor, then repeat skill-retention and full-game development
  checks. Keep the independent single-policy architecture. Do not run another
  selector fit or infer match success from supervised loss. The proposed human
  movement, jump, and energy contract still needs the user's decision before
  a major controller/training change. No training or evaluation job is running.

## Previous verified state — 2026-09-07 08:45 UTC

- Direction: one complete player policy, instantiated independently for each
  player. Shared weights remain allowed. Stop further selector development;
  retain selector checkpoints as unpromoted experiments. The user asked why
  we were not using one policy per player. No new jump, energy, body-heading,
  or directional motor change has been approved or implemented.
- Completed three isolated fixed-policy games with the same development seed
  1141000, the older PPO 032230 actor, candidate team 0, unchanged identities,
  deterministic candidate actions, and the maximum-probability frozen baseline.
  Collector: `scripts/player-fixed-policy-repeat.cs`. No selector was loaded.
  Evidence: `artifacts/player-agents/fixed-policy-repeat-20260907-083721/`.
- All three runs ended 0-11 after 13 rallies, with 28 candidate legal returns,
  25,635 physics steps, and 3,340 candidate decisions each. Every recorded
  public-state row and contact row matched exactly across the three runs.
  All 10,020 candidate decisions replayed from their own observations through
  the single actor. Collection took 91.548 seconds. This is repeatability
  evidence for one test setup, not proof of general determinism or better play.
- Audit: `artifacts/player-agents/fixed-policy-repeat-audit-20260907.json`.
  Completion hash: `fc38fadcf61782a71a69396fe9666308ca063f67f4bf64d59d33a5f14f11f9bd`.
  Runtime source stayed `7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
  All test callbacks were absent at 08:44:41 UTC. Unity remained in Play.
- Historical comparison: every candidate observation/action in the new fixed
  run matches bootstrap selector game 0 from 075653, which used only the older
  expert. The 082035 game also used only the older expert, but first differs
  at decision row 1306, rally index 3, observation tick 1584. Ball observations
  already differ before the resulting candidate action differs. Evidence:
  `artifacts/player-agents/fixed-policy-repeat-history-20260907.json`.
  The earlier outlier remains unexplained; the three repeats did not reproduce
  it. Do not attribute that score change to selector learning or claim a fix.
- Retained the completed previous selector RL trial. Four training games
  against the older actor produced 17,610 candidate decisions and three wins
  during pre-update collection. A bounded 72-update selector fit was saved as
  `skill-gate-ppo-20260907-081921/gate.json`, hash `790dc46e...`. Its later
  eight-game baseline evaluation still had zero wins: 54/188 rally wins,
  420 legal returns, 57,630 replayed decisions, and four no-point truncated
  rallies. These are not accepted match gains. Revised audit:
  `artifacts/player-agents/skill-gate-ppo-games-audit-20260907.json`.
  The original physical plan has stale profile-supervision boilerplate;
  checkpoint metadata and report method identify the game-win-labelled update.
  The original reports and collector snapshot were not rewritten.
- Added six repeat-comparison tests. All 224 Python tests pass (15.738 seconds),
  including 219 player tests.
  The 63-file baseline and `git diff --check` pass. The Unity CLI skill was
  used for isolated tests only. No runtime source, playable scene, model asset,
  contact configuration, or final evaluation seed changed.
- Next: retain the single-policy path and settle the proposed controller
  contract before a major training cycle. If the unexplained outlier recurs,
  compare full contact traces around rally 3 / ticks 1572-1584 before using
  small score differences as evidence. No new training job is running.

## Previous verified state — 2026-09-07 08:05 UTC

- Completed all eight development games for the learned selector in
  `skill-gate-games-20260907-075653/`. External collector:
  `scripts/player-skill-gate-games.cs`, SHA-256
  `64df2720ec819ee2c2c8bbff5b2ca827b02505742ad87e634ac009965fc47ff4`.
  The collector keeps the prior full-game runner's schedule and limits:
  seeds 1141000..1141007, both court ends, maximum and sampled baseline
  modes, and teammate identity swaps. It cannot use final seeds. It records
  the selector action before applying the normal 25 ms action delay.
- The gate lost all eight games: 54/188 rally wins (28.72%) and 402 legal
  returns. The re-audited older parent lost the same eight games with
  51/185 rally wins (27.57%) and 402 returns. One sampled-baseline score
  improved from 3-11 to 5-11; another declined from 2-11 to 1-11. This
  does not establish better match play. Do not promote the selector.
- All 56,504 candidate decisions replayed from the acting player's own
  54 observations. The short expert was selected 294 times (0.520%);
  the older expert was selected 56,210 times. The 112 expert changes include
  changes across rally boundaries. The two games that used only the older
  expert reproduced all shared recorded game fields and rally rows from
  the saved parent run. This is not a full per-step trajectory comparison.
- All games reached legal final scores. Four no-point time-limit rallies
  remain in the denominator (4/188, 2.13%). The first new verifier incorrectly
  rejected any rally without a winner. Inspection confirmed the unchanged
  rules permit these truncations. Added time/fault/unchanged-score checks
  and a regression test; the original physical run was not repeated.
  Initial audit failure is retained in
  `skill-gate-games-initial-audit-failure-20260907.json`.
- Candidate motor and guard checks passed, including scripted candidate
  serves. Frozen-baseline paddle-acceleration violations remain disclosed
  in the reports; they are not candidate failures or removed evidence.
  Audit: `skill-gate-games-audit-20260907.json`, SHA-256
  `58d3a8c6cf371cac00147f0596755e7ecf33c595d71a86210d608713be7ef5d6`.
  Paired comparison: `skill-gate-games-comparison-20260907.json`, SHA-256
  `e775161d4932f0bf39fbdb5e65e47da9ca34df7e9d013081dfe98e6de9ee4030`.
- The run took 252.812 seconds. All 211 Python tests pass (18.200 seconds).
  The 63-file baseline and `git diff --check` pass. At 08:01:40 UTC all
  diagnostic callbacks were absent; runtime source remained `7a998e12...`.
  The Unity CLI skill was used for isolated complete-game evaluation. No
  playable scene, runtime C# source, controller, or existing model changed.
- Source-profile selection retained two skills in injected fixtures but
  rarely selected the short expert in baseline games. Next bounded path:
  learn selection from actual game outcomes on separate training seeds,
  with frozen experts, then repeat development evaluation. Do not treat
  this supervised gate as game-win-trained or change final acceptance.
  No new game-win training job started. The proposed human-like controller
  remains unapproved, and no large training cycle is scheduled for it.

## Previous verified state — 2026-09-07 07:52 UTC

- Completed one bounded learned-selector bootstrap. Plan:
  `config/player-agents/skill-gate-bootstrap-v1.json`. The selector is a
  54-32-1 network with its own `player-skill-gate-v1` schema, not an actor
  export. It selects an unchanged older PPO 032230 or short-return 051422
  expert from the acting player's own observations. Each expert receives
  that player's unmodified input. The selector masks paddle-pose inputs
  25..36 to avoid classifying by consequences of the teacher's action.
- The source label is explicit: kitchen training bank selects the short
  expert; deep and normal-match banks select the older expert. Sampling
  gives each source equal expected mass. The fit used 30 epochs, 2,460
  updates, two CPU threads, and 4.229 seconds. Three separate development
  banks selected epoch 30. This is supervised source classification, not
  team-win RL. No diagnostic cases or final seeds entered training.
  Artifact: `skill-gate-20260907-074705/gate.json`, SHA-256
  `7ee8a0c7c443fb283cf239fab0cd78a46e1b4924a6cc55fc85a02dcb4fb3c5aa`.
- External collector `scripts/player-skill-gate-probe.cs` passed 48 Python/
  Unity inference parity cases (maximum error 0.000003815), then completed
  64 physical cases in 36.616 seconds. Report:
  `skill-gate-probe-20260907-074915.json`, SHA-256
  `62f3e6168d274ce631e9ef65346704517b66370a87913d824c9b50b67af3bfa5`.
  All 32 sampled-teacher controls matched their saved physical traces.
  The selector made 12 hits and 7 legal landings in 16 deep cases, and
  16 hits with 16 legal landings in 16 short cases. Deep landings were
  3 and 4 across the court ends; short landings were 8 on each end.
- The auditor replayed all 2,384 candidate decisions, including gate logits,
  expert choices, movement, hit/leave, and shot selection. All four-player
  motor checks passed. Deep cases had 20 within-player expert changes;
  short cases had 48. No hysteresis or privileged runtime choice was used.
  Shadow teacher labels stayed diagnostic-only. Audit:
  `skill-gate-audit-20260907.json`, SHA-256
  `54ef6937b1fbce81ee8663073f86aa74b1fe50e697a9c8ca7902cc8032ce212b`.
- The selector preserves the older deep-return count and the short skill
  on these matched starts. Next: test complete development games against
  the frozen baseline, with the same court-end and identity schedule used
  for prior candidates. Do not promote this gate or claim match improvement
  from injected return fixtures. The team-game-win training and final
  held-out acceptance requirements remain unchanged.
- All 205 Python tests pass (16.848 seconds), including nine selector tests.
  The 63-file baseline and `git diff --check` pass. At 07:52:09 UTC, Unity
  was in Play with no running jobs or diagnostic callbacks. Runtime source
  remains `7a998e12...`. The Unity CLI skill was used for an isolated match;
  no scene, runtime C# source, or existing model weight changed. The proposed
  movement, jump, and energy controller still needs the user's approval.

## Previous verified state — 2026-09-07 07:40 UTC

- Finished the saved balanced-model audit. Physical report:
  `teacher-gap-20260907-073157.json`, SHA-256
  `e190594f13d9a14e4dc027785fba442d861988593672f9028a26d3d2c9f01c90`.
  Candidate: imitation 055351, actor SHA-256
  `d5bcb7a8503247558f9f61a3dd95d0c66d0adf9f58e55d240c6e6b150635e390`.
  All 32 teacher controls matched the reference. Python replay verified
  1,880 actor decisions from each player's own observations. Trace and motor
  checks passed. The model made 11 hits and 7 legal landings in 16 deep
  cases, and 7 hits with only 1 legal landing in 16 short cases.
- Re-audited the older and short-return models with the current verifier.
  The older model remains at 7/16 deep and 0/16 short legal landings.
  The short-return model remains at 6/16 deep and 16/16 short legal landings.
  The balanced model does not retain both skills. Do not promote it.
  These are injected development cases, not complete competitive games.
  Audit: `teacher-gap-balanced-audit-20260907.json`, SHA-256
  `de586aa57cfb9f9d70fc77a40e1d513c9d7b02e9aeaf0ee6c7963972ac4fe793`.
  Combined results: `teacher-gap-comparison-20260907.json`.
- All 196 Python tests pass (18.904 seconds). The 63-file baseline and
  `git diff --check` pass. No runtime code, scene, model weights, training
  data, or evaluation conditions changed in this audit. No Unity job was
  started. This audit does not establish the current Editor state.
- The user asked whether human-like movement limits should come next.
  Recommended order: directional ground movement; explicit crouch and
  reach; grounded takeoff and landing recovery; per-player energy; staged
  retraining. Realistic mode should not add mid-air propulsion. Constant
  energy refill is a simulation setting, not validated human physiology.
  These controller changes are not approved or implemented. A player-local
  learned selector remains a possible current-controller experiment; the
  balanced model is not evidence that this selector will work.

## Previous verified state — 2026-09-07 07:27 UTC

- Completed 352 physical teacher-shot cases on 32 matched starting states:
  16 deep and 16 short/kitchen incoming balls, alternating court ends. Every
  state used nine fixed canonical shots, the sampled baseline-team teacher,
  and a repeat of fixed shot zero. All colliders stayed enabled. Opponents
  used constant leave actions. The teacher retained privileged movement and
  hitter selection; no such selection was added to the runtime player actor.
- Collector: `scripts/player-shot-quality.cs`. Report:
  `shot-quality-20260907-071111.json`, SHA-256
  `bca2df18ca98e0e6a6e53b3a251bf3c59a94d32bb148e33b34ac69504a155e9f`.
  All 32 repeated controls matched exactly, including physical trace hashes.
  The verifier checked 157,201 physical steps and 52,992 decisions, initial
  observations, canonical shot mapping, latency, events, and all four motors.
  All checks passed. The run took 229.59 seconds. These fixture timings are
  not a new full-match training throughput benchmark.
- The sampled teacher landed 28/32 returns: 12/16 deep and 16/16 short. Fixed
  shot zero landed 26/32. A hindsight choice among all nine fixed shots could
  land 29/32. Only one sampled-teacher miss had a successful fixed alternative.
  This does not support replacing teacher shot selection as a general fix.
  Changing a fixed shot can also change teacher movement and hitter choice;
  this is not a same-contact impulse comparison. Audit:
  `shot-quality-audit-20260907.json`.
- Added `scripts/player-teacher-gap.cs` to compare a saved actor with the
  sampled teacher on those exact starts. It records diagnostic teacher labels
  on actor states but never substitutes them for actor actions. Two candidate
  actor instances use their own observations; two opponents use constant
  leave actions. Labels and seeds are development-only and must not enter
  a training bank. Each run has 64 cases and a hashed collector snapshot.
- Older PPO 032230: `teacher-gap-20260907-071836.json`, SHA-256
  `0df4ed54ca2c25a5094d249797e93e0309e9c591d40c1172db7557b28ac7677d`.
  It made 12 hits and 7 legal landings in 16 deep fixtures, and six hits with
  zero legal landings in 16 short fixtures. Its historical-runtime provenance
  is explicit. The teacher remained at 12 deep and 16 short landings.
- Short-return imitation 051422: `teacher-gap-20260907-072502.json`, SHA-256
  `4bea50faccae3e6c3e5601fe029dffb1a832debc53390335858f6303717e1153`.
  It made 13 hits and 6 landings in 16 deep fixtures, and 16 hits with 16
  landings in 16 short fixtures. Both runs reproduced all 32 sampled-teacher
  control traces exactly. All four-player motor checks passed. Python replay
  reproduced 1,926 older-model actions and 2,416 short-model actions from each
  player's saved observations. No teacher action replaced a replayed action.
  Audits: `teacher-gap-parent-audit-20260907.json` and
  `teacher-gap-short-audit-20260907.json`.
- The short-return skill is learned in one saved model. The evidence favours
  retaining and combining learned skills, not another global contact-physics
  adjustment or replacement of the successful teacher. Before another large
  training cycle, compare the balanced/retention model on these same starts
  and test a player-local learned skill selector if the models remain
  complementary. Any selector must use only that player's observations.
  A hindsight per-fixture model choice is not a deployable or learned selector.
  Full competitive team-game-win evaluation remains required.
- All 196 Python tests pass. The 63-file baseline and `git diff --check` pass.
  Runtime source remains `7a998e12...`. At 07:26:08 UTC all Unity diagnostic
  callbacks were absent. The diagnostic actor-path setting now names imitation
  051422; the playable scene and its model were not changed. No new model was
  trained or promoted, and no final seed was used. The proposed movement,
  jump, and energy controller is still awaiting the user's approval.

### Saved contact-geometry audit — 07:05 UTC

- Completed a read-only geometry audit of the two saved match-contact reports
  from 05:26 and 05:28. New analyzer: `scripts/player_contact_geometry.py`.
  It first reruns the existing source/model/motor/ownership verifier. It then
  measures contact delay, contact-normal error, longitudinal paddle position,
  and linear plus angular paddle-point speed. Output and analyzer snapshot:
  `contact-geometry-audit-20260907.json` and its `.analyzer.py` sibling.
- The audit includes 138 parent contacts and 74 rejected-child contacts. It
  explicitly excludes two unplanned shots and two multiple-contact shots.
  Recorded contact normals were within one degree of the planned direction
  in 127/138 parent contacts and 63/74 child contacts. Recorded angular motion
  contributed zero normal speed in all 212 included contacts.
- A global timing correction is not established. The median contact delay
  among upright legal landings was 16.01 ms for the parent and 20.17 ms for
  the child. Late contact therefore also occurs in successful returns.
  All four child WrongSide contacts had the planned normal direction. Their
  mean paddle-point normal speed was 2.26 m/s below the planned speed. Four
  other child shots hit the handle before a BodyContact fault. Keep these
  different failure types separate; neither a single cause nor a fix is proved.
- The factory's face-center offset matches the swing's .0635 m offset. The
  recorded grip position allows recovery of the paddle's local Y axis only.
  These are post-step poses, not exact impact poses. The audit must not label
  an edge collision from a post-step point alone. Surface names and actual
  collision normals remain separate evidence. No collision was replayed here.
- The next useful check is the training teacher's shot quality under the
  player motor. `PlayerOracle` either uses a fixed shot or samples the frozen
  baseline team policy. It does not compare the physical outcomes of available
  shots under the constrained player motor. Before collecting new teacher
  labels, compare all nine shots on identical injected incoming fixtures.
  Keep those privileged comparisons training/diagnostic-only. Do not add
  central shot selection to the live player policies or treat fixture landings
  as the final team-game-win objective. Do not repeat the rejected global ramp.
- All 184 Python tests pass, including seven new geometry-audit tests. The
  63-file baseline and `git diff --check` pass. No runtime, scene, model,
  training data, or final seed changed. No Unity job was started in this audit.
  The original goal remains incomplete. The new movement controller still
  requires the user's approval.

### Isolated swing-ramp diagnosis — 06:57 UTC

- Completed a 72-case isolated swing timing test. The three modes are the actual
  runtime swing, an exact local copy, and the local copy with a 120 ms acceleration
  ramp. The ramp keeps the same initial backswing displacement and planned contact
  velocity. It changes no motor limits, contact coefficients, or runtime source.
  Each mode has 24 fixtures: two ends, four depths, and flat/topspin/slice shots.
- Report: `swing-ramp-probe-20260907-065225.json`, SHA-256
  `c7d08134ef27ccc5538bc4041acfe129d4bb6b9f12bd46157eaec6fd5961bbd7`.
  It retains a collector snapshot and 72 hashed per-step traces. The original
  failed recorder run (`swing-ramp-probe-20260907-065120.json`) is also retained.
  That run stopped before completing a case because the JSON recorder tried to
  serialize a Unity vector's recursive properties. The corrected recorder uses
  explicit numeric event positions. Both jobs are terminal; no callback remains.
- The local control reproduced every physical trace hash, contact record, event,
  and case metric from the actual runtime in all 24 fixtures. The ramp changed
  all 24 traces. Legal landings fell from 10/24 to 4/24. Flat landings fell from
  six to two, topspin stayed at two, and slice fell from two to zero. Both modes
  recorded 14 hits, but the ramp included two handle contacts. Do not promote it.
- `scripts/player_swing_ramp.py` audits source, contact, snapshot, and trace
  hashes. It checks 27,062 recorded physical steps, exact control equality,
  fixture identity, timing, landing consistency, and the existing motor bounds.
  Independent trace checks found peak paddle speed 6.44425 m/s, acceleration
  100.01156 m/s², reach .61230 m, and angular speed 12.00098 rad/s. These are
  inside the established numerical tolerances. Stationary feet did not move.
  Audit: `swing-ramp-audit-20260907.json`. Six new verifier tests cover changed
  controls, incomplete schedules, case labels, and invalid physical traces.
  All 177 Python tests pass. The baseline check and `git diff --check` pass.
- This is not match-strength or human-limit evidence. As in the original
  contact fixture, all player colliders are disabled only after a legal hit to
  isolate outgoing flight. The ball parameters remain uncalibrated. No actor,
  scene, saved contact fit, training seed, or final evaluation seed is changed.
- This particular ramp does not solve the return problem. Future stroke work
  must check position, rotation, and speed at the actual collision together.
  Do not infer that more preparation time alone produces a better shot.
  Runtime source remains `7a998e12...`; all 63 baseline files are unchanged.

### Flat-brush command diagnosis — 06:39 UTC

- Completed an offline flight audit of the existing paired contact traces.
  `scripts/player-flight-plan-audit.cs` uses the current flight calculation on
  saved numbers only. It creates no world or actor and moves no live object.
  Report: `flight-plan-audit-20260907-062911.json`, with a hashed collector and
  sibling summary. It includes 207 single-face planned contacts and explicitly
  skips two unplanned, two multiple-contact, and five non-face shots.
- The audit separates recorded outgoing flight, recorded flight without spin,
  simplified planned impulse, and simplified measured paddle-point impulse.
  For the rejected child's 68 upright shots, geometric opposite-court success
  was 62, 62, 67, and 62 respectively. For the parent's 129 upright shots, it
  was 119, 120, 120, and 116. The simplified impulses omit friction and brush
  transfer. Net clearance is geometric; no collision or opponent is simulated.
  These are diagnostic comparisons, not causal proof or match outcomes.
  Of 143 recorded legal landings included in the audit, 141 were within 5 cm
  of the free-flight prediction. Two parent cases differed by more than 5 cm;
  maximum error was 1.619 m. Do not treat this as an exact physical replay.
- Tested the hypothesis that the flat stroke's upward brush command consumes
  needed paddle motion. New external collector `scripts/player-brush-command.cs`
  changes only a temporary candidate flat-stroke brushBias from five to zero.
  Pitch, timing, speed scale, other strokes, ball materials, and motor limits
  are unchanged. No saved model or scene is edited. This is not a new controller.
- Both short traces used PPO 032230 with explicit historical provenance,
  seeds 1198000–1198003, sampled baseline opponents, and both court ends.
  Bias-five control `brush-command-20260907-063245.json` exactly reproduced
  the original parent's complete game records, all shot traces, and all events
  in `contact-outcomes-20260907-052617.json`. Each case has a 16-rally cap.
- Zero-brush trace `brush-command-20260907-063514.json` did not establish an
  improvement: 20/62 rally wins, versus 23/64 in the control. The control has
  four partial games; zero brush has one complete loss and three partial games.
  Legal contacts/next legal landings were 147/108 versus 141/101. Post-hit
  candidate WrongSide faults rose from six to eleven, and BodyContact faults
  from three to seven. The state and shot distributions differ after treatment,
  so per-shot speed averages are not a same-contact causal comparison.
- `scripts/player_brush_command.py` verifies the exact control, paired settings,
  source/model/snapshot hashes, strict single-parameter change, resolved rallies,
  partial-game labels, and candidate motor bounds. All checks passed. Six new
  tests reject hidden changes, bad labels, non-finite values, wrong actors, and
  changed control events. All 171 Python tests pass. Plan and audit:
  `brush-command-plan-20260907.json`, `brush-command-audit-20260907.json`.
- Do not promote zero brush or infer that removing spin solves the return
  problem. These results favour checking the coupled stroke execution against
  the actual body pose and bounded motor, instead of another global coefficient
  change. Any future privileged shot-quality labels must remain training-only;
  live actors must keep their own observations and decisions. The full game-win
  acceptance requirements remain unchanged. At 06:39:19 UTC all Unity collectors
  were idle. Runtime source remains `7a998e12...`; the 63-file baseline is unchanged.

### Paired output-retention trial — 06:23 UTC

- Added an optional soft output-retention penalty to the imitation trainer.
  It compares movement latents, hit probabilities, and shot probabilities
  against a frozen copy of the initial actor. Training uses original recorded
  observations for this penalty. Development data selects the checkpoint only.
  The default weight is zero. There is no runtime or action-space change.
  Seven new tests cover option validation, each loss component, frozen-reference
  gradients, finite extreme hit logits, and malformed outputs. All 165 Python
  tests pass. The 63-file baseline is unchanged.
- Both planned ten-epoch runs completed: `imitation-20260907-055338` has weight
  zero and `imitation-20260907-055351` has weight ten. Both selected update 820.
  They used the same initial actor, six source reports, random seed, per-source
  sampled counts, and optimizer settings. All data, parent, trainer snapshot,
  and current-runtime hashes passed. The historical parent remains explicitly
  labelled. Output audit: `retention-smoke-output-audit-20260907.json`.
- Weight ten reduced output drift on all three development banks, but gave a
  poorer fit to teacher labels than weight zero. Movement output MSE relative
  to the parent fell from .009836 to .000682 on normal states, .041688 to
  .001843 on short states, and .004604 to .000475 on deep states. This measures
  output similarity, not retained match skill. No final seeds were used.
- Both saved actors passed 32 Unity output-parity cases. Maximum errors were
  .0000114441 (weight zero) and .0000038147 (weight ten). Paired 48-case coverage
  reports are `coverage-20260907-061053.json` and `coverage-20260907-061144.json`.
  In 16 learned cases, weight zero made 11 contacts and 10 legal landings;
  weight ten made 12 contacts and 8 landings. The older parent made 10/9.
  Both movement-disabled controls made zero contacts. Both teacher controls
  made 12 contacts and 10 landings. All four-player motor, schedule, own-player
  observation, and timing checks passed. Replayed 3,630 saved actor decisions.
  Audit: `retention-smoke-coverage-audit-20260907.json`.
- Neither candidate retained every parent group result. Weight zero lost one
  deep contact and landing on team 1. Weight ten retained all eight deep
  contacts, but lost one team-1 landing. In seed 1115015, the retention actor
  contacted at the same recorded time and position as the parent, but its
  return hit the net and landed on its own side. Small output changes can
  still change physical results. Do not promote either model from these tests.
- Completed the same eight development games for both candidates, with seeds
  1141000–1141007, both ends, identity swaps, maximum/sampled baseline modes,
  and no contact override. Driver: `model-comparison-20260907-061254/progress.json`.
  Process 73991 completed with exit code zero. Weight zero lost all eight
  games: 31/157 rally wins (19.75%) and 447 legal returns. Weight ten also
  lost all eight: 47/175 rally wins (26.86%) and 419 returns. The older parent
  recorded 51/185 rally wins (27.57%) and 402 returns on the same schedule.
  All eight-game completion, artifact, physical, identity, and condition checks
  passed again for all three actors. Audit: `retention-smoke-match-audit-20260907.json`.
- The soft penalty limits the measured regression versus the unpenalized fit,
  but does not establish improved play over the parent. Do not promote either
  candidate or repeat this same teacher-only recipe as a match-strength fix.
  Future work must improve actual return outcomes and competitive decisions,
  not merely teacher fit or contact count. The controller decision remains open;
  avoid another large training cycle before that choice. The full game-win,
  held-out, partner, and playable-scene acceptance requirements remain in force.
  At 06:23:14 UTC all Unity collectors were idle, with no Tick callbacks.
  The saved scene, older preview actor, controller, and runtime source are unchanged.

### Output-component diagnosis — 05:46 UTC

- Completed a four-mode diagnostic output ablation, without training or runtime
  changes. `scripts/player-action-ablation.cs` derives the earlier short-contact
  schedule but records both actors' outputs and the applied action. It substitutes
  one component from PPO 032230 on the same own-player observation. No teacher,
  future intercept, central hitter selection, or physical override is used.
  These mixed policies are diagnostic only, not saved trained actors.
- The `none` control in `action-ablation-20260907-053706.json` exactly reproduces
  all rally events, contact traces, game records, and motor metrics from the
  earlier child trace `contact-outcomes-20260907-052833.json`. All 11,240 recorded
  decisions were reproduced from both saved actors, with zero substitutions.
- All four modes used seeds 1198000–1198003 and identical source, models, contact,
  rules, opponent, and timing. Each ends at game completion or 16 rallies, so
  partial games remain labelled. Results (rally wins / rallies; legal contacts;
  body faults after opponent hits):
  - Child unchanged: 6/53; 75; 16.
  - Reference movement only: 12/61; 183; 6. Report 053849.
  - Reference hit/leave decision only: 13/56; 73; 11. Report 054129.
  - Reference shot choice only: 14/61; 81; 14. Report 054259.
  - Earlier complete parent policy on the same short schedule: 23/64; 141; 8.
  Contact count alone does not establish better play. All three components
  contribute to the child's regression; no single-component substitution
  exceeds the parent result. The hit-decision trial substituted only 99 of
  11,368 decisions, showing why aggregate prediction accuracy is insufficient.
- `scripts/player_action_ablation.py` verifies source/model artifacts, four
  scheduled cases, motor limits, paired own-player observations, decision timing,
  action bounds, exact substituted fields, and both actors' replayed outputs.
  All 58,172 recorded decision rows passed. Five new tests cover allowed changes,
  wrong sources, missing teammates, duplicates, timing, ownership, and malformed
  actions. All 158 Python tests pass. Summary and immutable evidence hashes:
  `output-ablation-plan-20260907-0537.json`; each report has a sibling audit file.
- No model was promoted. The next correction must preserve the older policy's
  movement and hit decisions as well as its shot choices; do not continue the
  same unconstrained teacher-only fit from the rejected child. The proposed
  movement/jump/energy controller is still awaiting a user decision. It has
  not been implemented. The baseline and saved scene remain unchanged.
  At 05:46:38 UTC, all training and diagnostic collectors were idle.

### Paired contact diagnosis — 05:31 UTC

- Completed a paired contact diagnosis without training or runtime changes.
  Summary: `paired-contact-diagnosis-20260907-0526.json`. Both actors used
  seeds 1198000–1198003, sampled baseline opponents, both ends, the current
  runtime, and zero contact override. All source, artifact, schedule, and
  candidate motor checks passed. No final seeds were used.
- Parent trace `contact-outcomes-20260907-052617.json` contains 64 rallies,
  141 legal contacts, 101 legal landings, and 30 opponent interceptions before
  landing. Candidate trace `contact-outcomes-20260907-052833.json` contains
  53 rallies, 75 contacts, 43 landings, and 21 such interceptions. All four
  parent games stopped at the disclosed 16-rally diagnostic limit. The child
  lost three complete games; its fourth stopped at the limit. These traces
  are not four complete matched games or final acceptance evidence.
- Body-fault context is now included in `scripts/player_contact_outcomes.py`.
  Six added tests check both ends, own/partner/opponent hit identity, event
  timing, rally boundaries, and fault ownership. All 153 Python tests pass.
  The parent had 12 candidate body faults: eight after an opponent hit,
  three after its own hit, and one before any recorded hit. The child had 24:
  sixteen after an opponent hit, four after its own hit, and four before a
  recorded hit. The last category must not be treated as a known incoming
  return; serve events are not legal-hit events in this trace.
- The next diagnostic target is receiving position and hit timing during
  actual opponent returns. The traces do not isolate which action or contact
  geometry caused each fault. Do not infer a causal fix from aggregate shot
  speed or pitch. The child remains rejected. At 05:31:08 UTC all collectors
  were idle. The 63-file baseline and existing preview were not changed.
  The proposed movement, jump, and energy controller remains unimplemented.

### Small recovery trial — 05:22 UTC

- Completed a small deep-rehearsal trial while the controller decision remains
  open. Plan and results: `deep-rehearsal-trial-20260907-0512.json`.
  No runtime source, controller, reward, contact model, or frozen protocol changed.
  The new current-source deep teacher data uses 160 training seeds from 1062000
  and 40 development seeds from 1196000. Reports: `incoming-20260907-051229.json`
  and `incoming-20260907-051343.json`. Training had 129 contacts and 85 legal
  landings; development had 35 contacts and 22 legal landings. All ownership,
  reset-range, source, and four-player motor checks passed.
- The trial combined normal, short, and deep sources with equal sampling mass.
  It used the explicitly historical PPO 032230 parent. Eighty epochs completed
  in 65.83 seconds, using 83,938 training rows and 37,320 development rows.
  Saved actor: `imitation-20260907-051422/actor.json`, SHA-256
  `80986c037192063d5d90030f2341bb4c7f3239958c55f433988694745bb19826`.
  All 32 export parity cases passed, maximum error 0.000003814697265625.
  All six data hashes were verified again after fitting.
- Fixed coverage improved relative to the rejected short-only refresh, but
  did not preserve the parent skill: nine contacts and six legal landings in
  16 learned cases; five contacts and four landings in eight deep-start cases.
  Parent results were ten/nine overall and eight/seven at deep starts.
  The new actor also made 38 contacts and 31 legal landings in 40 short cases
  from seed 1197000, with eight kitchen groundstrokes and no teacher decisions.
  All 3,102 applied actions were reproduced from the saved actor. Audit:
  `deep-rehearsal-retention-20260907-0517.json`. Its failure result is retained.
  Short seeds differ from the previous short-only refresh; do not call that a
  paired short-skill comparison.
- The eight matched development games were worse than the parent: zero wins,
  nine rally wins out of 108, and 213 legal returns. The parent had zero game
  wins, 51/185 rally wins, and 402 legal returns on the same repaired runtime.
  Both court ends, partner identity swaps, and maximum/sampled baseline modes
  were included. All runner, identity, physical, source, hash, and schedule
  checks passed. Audit: `deep-rehearsal-matches-20260907-0522.json`.
  Driver process 41364 completed with exit code 0. Do not promote this actor
  or repeat the same supervised recipe. Fixture recovery is not match strength.
- At 05:22:02 UTC, all collectors were idle. The live preview still used
  experimental PPO 032230 and was paused. No final seeds were used, and the
  saved scene was not edited. The 63-file baseline remains unchanged.

### Previous verified checks

- Completed the reusable `scripts/player_skill_retention.py` check.
  All 147 Python tests pass, including nine new retention tests. The check
  validates the fixed paired schedule, all four motor records, observation
  ownership, action timing, source hashes, and teacher-free short-ball control.
  It also reproduced all 3,052 applied short-ball actions with the saved actor.
  Result: exit 1, because deep-start coverage regressed on both court ends.
  This is a model failure, not a failed audit process. Evidence is saved in
  `artifacts/player-agents/skill-retention-audit-20260907-verified.json`.
  All 63 baseline files remain unchanged. No new training or controller
  changes were started. The proposed controller choice remains open.

- Read-only retention diagnosis: `skill-retention-diagnosis-20260907-0500.json`.
  The deep-start failure is systematic. In the eight 6 m start cases,
  parent PPO 032230 made eight contacts and seven legal landings; the new
  imitation actor made no contacts. Both request a hit and form a plan.
  At 0.3 seconds, the child has advanced farther toward the net in every
  case, by 0.1768 m on average. This records movement drift, not proof of
  a unique causal parameter.
- Of 59,876 normal-match training labels, only 675 have an expected-team
  rally state, self depth at least 5 m, and incoming canonical speed at
  least 6 m/s. The short-ball source has none. With equal source sampling,
  these records have only 0.564% expected sampling mass. The next curriculum
  needs explicit deep-ball practice and separate deep/short retention
  checks. Normal match labels alone did not preserve the earlier skill.
  This analysis changed no controller, actor, reward, or acceptance limit.
  The movement-controller approval question remains open.

- Process 48636 completed with exit code 0. It saved experimental actor
  `imitation-20260907-044649/actor.json`, SHA-256
  `ef247b1979b4d8840a4a20a7aed2d6211416726c4aa0c08a3b6c01a97306454b`.
  All 32 Unity parity cases passed; maximum error was 0.000005722046.
  The actor lost all three complete baseline development games, winning
  four of 41 rallies. Match report: `competition-20260907-044840.json`.
  Repeated source, parent, artifact, data, and motor checks passed.
- The actor-only short-ball check used 40 new development seeds from
  1195000, with zero teacher decisions. It made 38 legal contacts and
  33 legal landings, including 13 kitchen groundstrokes. Report:
  `incoming-20260907-045128.json`. All data and motor checks passed.
- Deep-ball coverage regressed. `coverage-20260907-045246.json` recorded
  three contacts and two legal landings in 16 learned cases. Its parent,
  PPO 032230, made ten contacts and nine legal landings on the same current
  runtime and fixtures in `coverage-20260907-045413.json`. Both movement-
  disabled controls made zero contacts. All 96 cases passed four-player
  motor, ownership, action timing, and artifact checks. Do not promote the
  new actor. Short-ball learning did not preserve deep-court coverage.
- No training or diagnostic collector remains active after these checks.
  No final seeds were used. The saved scene and 63-file baseline are unchanged.
- The user proposed body-relative directional limits, explicit crouch,
  jumping, landing recovery, and a constant-refill energy budget. The
  recommendation is to implement them before further large training runs,
  with realistic flight rather than unrestricted air steering. An approval
  question is open. No such runtime changes have been made. The current
  body is sealed, forces movement to ground level, and fixes body facing by
  court end. A proper controller version is needed; this is not just a
  change to three speed constants. Preserve the frozen original body.

### Completed kitchen repair and training sequence

- Kitchen contact repair `7a998e12...` passed all 79 existing runtime tests,
  all 15 Editor tests, and all 33 original doubles rule tests. Six added
  physical-return tests also pass, with body and paddle colliders kept active.
- The repeated stationary kitchen probe completed 48 cases: 36 legal hits
  and 24 legal landings, versus four hits and no legal landings before repair.
  All 12 cases at body depth 2.1 m produced legal kitchen groundstrokes and
  landings. All physical and artifact checks passed. This is fixture proof,
  not match-strength evidence. Failures at other depths remain recorded.
- The eight-game paired development check completed for historical PPO
  032230 on the repaired runtime. Process 17646 ended with exit code 0; driver
  `model-comparison-20260907-042551/progress.json`; results
  `development-evaluation-20260907-042554`. Repeated artifact, motor, and
  identity checks passed. The actor lost all eight games: 51/185 rally wins
  and 402 legal returns, versus 55/184 and 352 before repair. More returns
  did not establish stronger play. Final seeds remain unused.
- The temporary four-player PPO 032230 preview is restored in Game view.
  The scene is unchanged. This historical policy is not accepted.
- The external incoming-ball collector now has an explicit `kitchen`
  profile. Its 160 training fixtures completed, from seed
  1060000, in `incoming-20260907-043315.json`. All 160 produced legal
  landings; 65 recorded a kitchen groundstroke. It records slower incoming speed,
  closer initial player depths, and its exact source snapshot. The default
  `deep` profile retains its original ranges. The match runner does not
  depend on this external collector. No active runtime source was changed.
- The input validator checks the new profile's exact declared ranges,
  actual ball and player reset states, and legal-contact prerequisites.
  Five new Python tests cover valid mirrored resets and invalid records.
  All 133 Python tests pass. Forty separate short-ball development fixtures
  from seed 1192000 also produced 40 legal landings, including 14 kitchen
  groundstrokes. Both complete reports passed ownership, data, reset-range,
  physical-limit, and source checks. These are teacher results, not actor results.
- Completed process: **48636**, driver `refresh-20260907-043716/progress.json`.
  It fitted the current-runtime policy. `curriculum-20260907-043639.json`
  completed 128 teacher-controlled baseline training rallies from seed
  1061000, with 59,876 labels, five wins in five complete games, and one
  partial game. `curriculum-20260907-044309.json` completed 64 separate
  development rallies from seed 1193000, with 31,374 labels, one complete
  teacher win and one partial game. Both passed repeated data and motor
  checks. The fit combines these with the short-ball sets: 73,282 training
  rows and 34,738 development rows, with equal source sampling. It checked
  export parity and collected
  actor-only development matches from seed 1194000. Initialization uses
  historical PPO 032230 explicitly; all training data must use the repaired
  runtime. No parent source hash was rewritten. The run is terminal and
  its unsuccessful policy remains retained for inspection.

### Earlier verified stages

- The constrained serve now lands legally in all 24 regression cases. The
  movement limits and all 63 frozen baseline files are unchanged.
- Prior runtime source `7a04ba2e...` passed 73/73 runtime and 15/15 Editor
  tests. The Python suite passed 102/102. A new motor recovery proposal is
  under test after a later training game exposed a physical-limit failure.
- Saved policy `ppo-20260906-222751` achieved 12/16 coverage contacts
  and 10/16 legal landings. Disabling movement produced no contacts.
- It made 296 legal returns in eight paired baseline games, compared with
  245 for its three-source imitation parent. It still lost all eight games.
- Both local team rally-win PPO updates are complete. The 16-game paired
  partner test passed all control and motor checks. Each partner condition
  won four of eight games against the three-source imitation parent.
- Four local game-win updates are complete: 1,121 rallies, 19/34 training
  game wins against the saved parent. Baseline development had no game wins.
- A contact diagnostic found deep flat shots landing about 2.3 metres short.
  Three bounded swing trials did not establish an improvement and were rejected.
- Six local shot-selection updates are complete: 1,564 training rallies and
  15 development games, with no game wins. All motor and output checks passed.
- The paired 32-game comparison is complete. All four actors lost every game.
  The shot-only children and full-rally-credit trial did not improve rally wins.
  They are retained as unsuccessful trials, not promoted models.
- A privileged diagnostic teacher won one complete baseline game, 11–8,
  with the unchanged bounded motor. Its second game was partial. This is not
  a learned-player result. The larger teacher collection and four-source
  corrective fit are now complete.
- New experimental actor `imitation-20260907-001146` kept 12/16 coverage
  contacts and 10/16 legal landings. Movement-disabled controls made no contact.
  It won 23 rallies in 135 paired-test rallies, versus its parent's 17/125,
  but still lost all eight games. Improvement across court ends is unproven.
- Learner-controlled correction and its fit are complete. Actor
  `imitation-20260907-002944` won 38/159 paired-test rallies but lost all
  eight games. Coverage fell to 11 contacts and nine legal landings in 16 cases.
  This is an experimental training parent, not an accepted model.
- The eight-stage pool run stopped at stage five's physical check. Four
  model updates are complete; the failed fifth collection was not optimized.
  Game seed 1048016 recorded one infeasible paddle step and 1002.218 m/s²
  acceleration for player 0. The run remains retained as stopped.
- An exact 120-frame replay reproduced the failure with zero state error.
  The first proposed stopping constraint failed an older low-swing case
  and was rejected. A narrower recovery-posture constraint passes all 12
  recorded motor cases, 75 runtime tests, and 15 Editor tests. The complete
  27-rally failure game and eight fresh development games pass motor checks.
  Python tests now pass 107/107. The repair is retained. A new source-tracked
  run completed two more stages, then stopped at another motor check. No playing
  model is accepted; the old run remains stopped and its failed data excluded.
- The first resumed update is complete. Its collection won 16/18 training
  games against imitation 001146, with all motor checks passed. The updated
  actor lost three baseline check games. The second resumed update saved
  actor `ppo-20260907-020226`, then lost two baseline check games.
- The third resumed collection completed 542 rallies and 17 games, but
  failed its motor gate. No third update or fourth collection ran. An exact
  replay reproduced one rejected step with zero position or velocity error.
  Measured physical limits passed. The projection solver needs more than
  64 iterations at a narrow constraint intersection. A 128-iteration change
  passes 77 runtime tests, 15 Editor tests, and the complete 38-rally failure
  game. Physical limits and acceptance thresholds are unchanged. Two local
  training stages completed with fresh data under source `85da5a21...`.
  They saved PPO 023841 and PPO 024551, with 27/37 training game wins against
  older opponents. Both models lost their two baseline development games.
- PPO 024551 made 11/16 coverage contacts and eight legal landings. The
  movement-disabled control made no contact. All 48 diagnostic cases passed
  provenance and four-player motor checks. The four-model, 32-game paired
  comparison is complete: all models lost all eight baseline games. PPO
  010356 had the best overall and weaker-end rally-win rate. It is the parent
  for a new all-heads rally-win curriculum against the frozen baseline.
  No final seed block has been reserved.
- The training-data validator now checks all four players when the opponent
  is a saved actor. The original baseline motor remains separate. The new
  test failed before the fix; all 109 Python tests now pass. Both completed
  training collections and both development reports pass the updated check.
- The Game view and its provisional, untrained label were readable. An
  actual `I` key press changed the intent display. Space, N, and R keyboard
  checks also passed with Game view focused. Replay motion did not advance
  the live match. A temporary PPO 010356 preview now runs four learned
  players. The saved scene remains unchanged. This is not an accepted model.
- The final game-win objective remains unchanged. No model is accepted or
  promoted. The goal is active; no external blocker is present.
- The four-stage rally curriculum is complete: 1,038 training rallies,
  263,808 decision rows, and no wins in 60 training or nine development
  games. All eight reports pass repeated artifact and motor checks. Each
  saved model passes 32-case Unity/Python output parity. The fixed 32-game
  comparison completed with no game wins. PPO 032230 had the best rally
  rate and weaker-end rate, but match improvement remains unproven.
- A new 48-case isolated contact check passed all physical limits. Neutral
  residuals did not improve legal landings. The current PPO 032230 contact
  trace confirms deep-right flat landings average 2.31 metres short. A
  temporary candidate-only three-degree upward flat-face trial reduced
  recorded post-hit faults. Six degrees did not retain that benefit. The
  three-degree full-game test lost all eight games and reduced rally wins.
  The correction is rejected. All 128 Python tests pass.
- A kitchen-groundstroke limitation is now under repair. Before the change,
  48 stationary kitchen cases made four hits and no legal landings. Two
  regression tests failed because the planner required contact at 2.654 m
  from the net after a kitchen bounce. The repaired low-contact planner
  passes both cases. The full runtime suite is running. Current source is
  `7a998e12...`; no policy is yet trained on this source. The baseline is
  unchanged. The saved scene has not been edited.

## Goal

Four players must select their own movement and shots. Each pair must work to
win against the other pair. Keep the existing doubles game as a fixed baseline.
Keep physical paddle contact, the current rules, bounded swing control, and
body inverse kinematics (IK). Do not describe IK as learned body control.

The user approved this work on 2026-09-06. No further choice is needed to start.
Use local compute. Purchases and paid compute need separate approval.

## Control boundary

- Each player receives a separate observation and returns a separate action.
- Model parameters can be shared. Runtime decisions cannot be shared by a
  central hitter selector.
- Observations include current ball position, velocity and spin; the player's
  movement and paddle state; teammate and opponent positions and velocities;
  and public rule and score state. Encode positions in a player-relative frame.
- Do not give an actor another player's unexecuted action, a future collision,
  a future landing, or a hidden opponent model state.
- Start with exact simulator measurements. This is not camera vision. Add
  measured decision intervals and action latency before the final evaluation.
  Noise and occlusion are later extensions, not required for this stage.
- Actions select ground movement, hit or leave, and shot target/style. Keep the
  existing nine shot options initially. Continuous shot targets can come later.
- The low-level swing controller can predict flight and execute a selected
  shot. It cannot move the player's feet to an intercept automatically.
- Collision separation and motor bounds are safety constraints. Record their
  interventions. Do not label their correction as learned team coverage.
- Keep the drop-serve routine as an explicit scripted reset skill. Independent
  movement and shot decisions apply during returns and open rallies. Report
  serve and non-serve hits separately.
- During training, a value estimator can use joint match state. It must not be
  needed by the actors during playback. Start with shared-parameter MAPPO and
  an optional imitation warm start. Record all scripted teacher assistance.

## Work stages

1. **Preserve and measure.** Save source/model hashes for the current doubles
   baseline. Re-run its verifier. Measure local simulation and training speed.
2. **Expose intent and check limits.** Show each player's move target, hit/leave
   choice and shot target. Record faults, missed returns, simultaneous chases,
   separation corrections, speed, acceleration, stopping distance and reach.
   Audit rebound and contact checks. Do not replace missing physical data with
   a claimed calibration.
3. **Separate player control.** Add the player observation/action boundary and
   an independent-player match mode. Preserve the existing doubles scene and
   saved models. Test that one actor cannot set a teammate's action.
4. **Train locally.** Start with return drills, then pair coverage, then 2v2.
   Use team win/loss rewards. Any temporary shaping must be bounded, recorded
   and removed or disclosed in the final stage. Do not reward rally duration
   as the final objective. Use saved opponents to reduce training instability.
5. **Evaluate and show.** Run the frozen evaluation below. Save models, reports,
   fault replay and a playable scene. Check the Game view. Update controls and
   the learned-versus-scripted labels. Keep unsuccessful runs as evidence.

## Evaluation protocol v1

Freeze this protocol before final training. Store its hash in each final report.
Development experiments can change code and curricula. They cannot consume the
final evaluation seeds for training or model selection.

Seed partitions:

| Use | Inclusive range |
| --- | --- |
| Training and teacher data | 1000000–1099999 |
| Development and model selection | 1100000–1199999 |
| Final evaluation | 1200000–1299999 |
| Interactive games | 1300000–1399999 |

The final comparison uses 80 complete games. Use 40 against the saved baseline
with maximum-probability shots and 40 against the same baseline with sampled
shots. For each mode, put the candidate on each court end for 20 games. Swap
teammate identities in half of each group. Use the same legal serve variation
range for both methods. Preserve the baseline's two team policies; record which
one is the opponent. Also report results against an older player checkpoint.

Acceptance conditions:

- The 95% Wilson lower bound of the candidate's pooled baseline game-win rate
  must exceed 0.5. Each baseline mode must have at least a 0.5 game-win rate.
- Report court-end and teammate-swap results separately. Do not hide a weak
  condition in a pooled mean.
- All four player seats must make at least 20 distinct legal non-serve hits
  across the final games. Count rule hits, not collider callback events.
- No more than 10% of final rallies may end at the training time limit. Such
  rallies award no point. A game that reaches an evaluator safety cap is an
  incomplete game, not a candidate win; it must be reported, not omitted.
- Tests must cover observation ownership, coordinate transforms, action bounds,
  independent simultaneous decisions, actor export parity, rule integration,
  source/model provenance and reward signs for both court ends.
- Audit motor and reach limits under aggressive movement, not only successful
  rallies. Report contact correction separately from commanded acceleration.
  Fix non-finite states and unexplained physical-limit violations before
  accepting a model. Keep the accepted baseline unchanged if fixes are needed.
- Measure coverage with fixed ball probes and report same-ball chases, uncovered
  returns, teammate proximity and safety interventions. Test an ablation with
  learned movement disabled on development seeds to show what movement adds.
- Playback must load the evaluated actor without its training value estimator.
  Show four separate decisions and verify pause, reset and fault replay.
- Final reports must record source, model, contact-model, physics configuration
  and protocol hashes, seed lists, action timing, training steps and elapsed time.
  Do not declare success from a screenshot or a count of training rallies.

If the candidate fails, keep the goal active and improve it with development
data. A further final evaluation must use a fresh seed block and retain the
failed report. Do not reduce a threshold to accept a failed model.

## Physics evidence boundary

The selected profile is an outdoor 40-hole ball on acrylic. Its configuration
hash at the start is `b0e21687f3c2838c`. Court restitution is 0.64. This parameter
is not a 64% rebound-height claim. Direct simulated height, speed and spin checks
are required. Material behaviour remains provisional until suitable measured
court/ball data is available. Missing physical measurements do not stop the
player-control prototype, but they prevent a claim of physical calibration.

## Start checks

- Unity 6000.5.5f1 is connected through Unity CLI.
- The current doubles scene and model files exist. No training job is active.
- `scripts/doubles-verify.py` passes for the existing baseline.
- Existing local Python: `.venv/phase1c0/bin/python`, version 3.10.12.
- Existing PyTorch: 2.1.2. Start with CPU checks. Measure usable acceleration
  and complete simulation/training throughput before making a compute decision.
- The worktree contains earlier changes. Preserve them; do not clean or commit
  them as part of this stage.

## Progress

- [x] Create the end-to-end goal and record the control boundary.
- [x] Verify the existing doubles acceptance evidence.
- [x] Freeze the baseline manifest and measure initial throughput.
- [x] Add independent player observations, actions and intent display.
- [ ] Audit movement and contact limits.
- [ ] Train and save player policies.
- [ ] Pass final comparisons and verify the playable scene.

## Development evidence: 2026-09-06, control foundation

This is implementation evidence, not acceptance of trained players.

- New module: `Assets/Picklebot/PlayerAgents`. The 63-file doubles baseline
  manifest still matches. The existing doubles verifier still passes.
- Observation v1 has 54 scalar inputs. Each player has a separate input copy,
  action and random stream. A policy receives no world or controller reference.
- Decisions run at 20 Hz. Actions apply after six physics ticks (25 ms).
  All four observations are captured before any actor is called.
- The new swing path does not use automatic intercept foot movement. It uses
  the requested movement action, subject to motor and collision-safety bounds.
- Eleven contract tests and eight runtime tests passed. Reports are
  `artifacts/player-agents/contract-tests-v1.json` and `runtime-tests-v2.json`.
- The first stress audit found a 779 m/s² correction when the old body controller
  drove teammates together. That failed case is retained. The new braking path
  measured a maximum of 14.001 m/s² and a minimum separation of 0.640 m in the
  corresponding case. It does not select a recovery position or hitter.
- The free-movement stop test measured 0.508 m stopping distance in 0.271 s
  from approximately 3.8 m/s. Rotation/reach and court-limit probes were finite.
  Broader stress and contact regression checks are still required for acceptance.
- Direct simulated drops from centre heights 1, 1.5 and 2 m gave rebound-distance
  ratios of 39.47%, 38.74% and 38.12%. The ratio uses the ball radius as the
  contact datum. These are simulator measurements, not measured acrylic-ball data.
- Current audit: `artifacts/player-agents/physics-audit-20260906-064918.json`.
- Current throughput: `artifacts/player-agents/throughput-20260906-065104.json`.
  The fixed baseline ran at about 2,090 physics steps/s. Four constant hit-attempt
  actors ran at about 1,905 steps/s. This is about 7.9 times physical time, with
  Editor scheduling included. The actors in this probe are untrained.
- CPU network-update probe: `artifacts/player-agents/cpu-throughput-20260906-064200.json`.
  A 54-64-64-12 network processed about 459,000 samples/s in the synthetic update
  test. This is not PPO throughput. MPS was available outside the restricted
  process, but the measured update used the CPU. Local training remains the plan.
- The evaluation settings are frozen in `config/player-agents/evaluation-v1.json`.
  Final training/evaluation reports must include this file's hash.

## Control-probe scene

`Assets/Picklebot/Scenes/IndependentPlayers.unity` exists. Create/open it with
the menu `Picklebot > Player agents > Open control probe`, then press Play.
It currently uses constant, untrained actions. It is not the final trained game.

- Space: pause.
- N: start a new game.
- R: show or leave the last fault replay.
- I: show or hide intent lines.

The Game view shows all four players, their requested movement, hit/leave choice,
shot index, legal non-serve hit count and safety-brake state. It also states that
the actors are untrained and that body IK and swing execution remain scripted.
The view was inspected in `artifacts/player-agents/control-probe.png`.

Replay uses 65 separate mesh copies with no colliders. A 336-frame replay was
checked at three positions. Maximum pose error was below 0.000001. Entering,
seeking and leaving replay preserved live ball and paddle positions, velocities,
body state, score, contact count and physics time. The report is
`artifacts/player-agents/replay-audit-20260906-065047.json`. Re-run with
`unity command eval_file scripts/player-replay-audit.cs --format json` after a
completed rally in the control probe.

## Next implementation work after the control foundation

1. Add the actor model loader and Python/Unity inference-parity tests.
2. Add training-only teacher records and a local rollout bridge. Do not restore
   a central hitter selector in the player execution path.
3. Fit return/movement skills, then train competitive pair play with saved
   opponents and team rewards. Measure complete rollout-and-update throughput.
4. Expand physical stress cases and coverage probes before final evaluation.

The goal remains active. See the first model experiments below.

## Development evidence: first imitation models

The actor interface and first example-based training path are implemented.
These models are not accepted for gameplay. Competitive RL has not started.

- `PlayerActor.cs` loads a 54-128-128-12 network with about 25,000 parameters.
  The outputs are two movement means, a hit/leave logit and nine shot logits.
  Each runtime actor has its own sample trace and random stream. Four actors
  can share read-only weights. No training value estimator is used for inference.
- `PlayerTeacher.cs` records a disclosed scripted teacher. It captures actor
  observations before the teacher step and records requested actions. Planned
  intercepts are labels used by the teacher, not inputs to the learned actor.
- Training set: `teacher-20260906-070406.json` and its `.jsonl` data under
  `artifacts/player-agents`. It has 128 rallies, five games and 88,948 records.
  Collection took 127.4 seconds. Seeds start at 1000000.
- Development set: `teacher-20260906-070642.json` and its `.jsonl` data.
  It has 32 rallies on seeds starting at 1100000. Final evaluation seeds have
  not been used.
- Python fitting: `scripts/player-agents-imitate.py`. The shared network/export
  implementation is in `scripts/player_actor.py`. Training records source,
  protocol, contact, baseline-manifest, data and trainer hashes.
- All 15 Editor contract/actor tests passed. The report is
  `artifacts/player-agents/actor-contract-tests-v1.json`. Four Python actor tests
  also passed, including export round-trip and no cross-player batch state.
- A random-weight export matched Unity on 64 inputs with maximum output error
  0.000000179. The first trained export matched on 32 inputs with maximum error
  0.000003815. Reports are saved with the respective model folders.

### First model: rejected development result

Folder: `artifacts/player-agents/imitation-20260906-070739`.

Fitting took about 30 seconds on the CPU. The example prediction results looked
strong, but physical self-play did not. Across 32 development rallies, the model
made only eight legal non-serve hits: 3, 2, 0 and 3 by seat. Mean hits per rally
were 1.25, including the serve. This is not useful doubles play.

Replacing paddle-state inputs with a neutral pose reduced hit recall to 9.03%,
from approximately 99.7% with the teacher paddle poses. The teacher's paddle had
already moved for a hit. The learned model relied on that consequence to decide
whether to start a hit. The low example error did not establish a usable policy.

### Second model: rejected development result

Folder: `artifacts/player-agents/imitation-20260906-071340`.

The trainer neutralizes the paddle inputs in 80% of examples. This improves the
neutral-paddle hit-recall check to approximately 98%, depending on the epoch.
Fitting took about 42 seconds. The saved model passes Unity/Python output parity.

It still made only eight legal non-serve hits across the same 32 development
rallies: 2, 0, 0 and 6 by seat. Mean hits per rally remained 1.25. The augmentation
does not solve the physical return problem by itself. Both failed models and
their full development reports are retained.

### Additional movement failure

Learned movement reached states not covered by the first stress tests. The first
model's development report includes acceleration corrections up to 263 m/s²;
the second includes a correction up to 335 m/s². These are not accepted motion.
`scripts/player-motion-probe.cs` reproduced the first correction at the outer
X limit, during dead-ball settling. The body was still moving outward at the
limit. The initial braking check was insufficient for changing directions.
The revised vector brake below addresses the reproduced boundary cases.

### Next action from these results

1. Run privileged teacher actions through the new action interface as a diagnostic.
   Do not put a teacher selector into learned-player execution. This separates
   low-level interface failures from model errors.
2. Add changing-direction/corner cases to the movement audit and fix the boundary
   correction without changing the frozen doubles baseline.
3. Add learner-state teacher records or staged mixed-control rollouts. The new
   policy must learn from states it reaches, not only scripted-player states.
4. Then add competitive updates and fixed-opponent evaluation. Do not substitute
   imitation accuracy or self-play game counts for the frozen win-rate gate.

No failed model has replaced the accepted doubles models. The control-probe
scene still defaults to explicitly untrained actions. The goal is not complete.

## Development evidence: control diagnosis and revised brake

- `PlayerControlProbe.cs` supplies privileged teacher actions through the actual
  player decision loop, including 20 Hz decisions and 25 ms latency. It is an
  Editor-only diagnostic. It is not used by exported actors.
- `teacher-control-20260906-072821.json` records 177 legal non-serve hits in 32
  development rallies. Mean total hits were 6.53, including serves. This is
  evidence that the new action path can make returns. It is not a learned result
  or a paired baseline comparison. This probe used seed 1100200; the failed
  model probes used 1100100, so these counts are not a matched-seed comparison.
- The boundary stress script reproduced corrections up to 432 m/s² during turns.
  The old check assumed separate acceleration budgets for X and Z. The body has
  one shared vector budget. The new check predicts the complete stopping path
  after the next motor step. It brakes when that path would reach the boundary.
- `boundary-stress-after-v2.json` records four 4,800-step cases. These include
  turns, random moves, corner chases, partner chases and dead-ball settling.
  Maximum measured acceleration was 14.025 m/s². No case exceeded 14.05 m/s².
  Boundary clearance stayed at least 0.040 m. This does not establish safety
  for every possible partner interaction or physical contact.
- `runtime-tests-v3.json` records 12 passed runtime tests, including all four
  stress cases. `actor-contract-tests-v2.json` records 15 passed Editor tests.
  The 63-file frozen baseline still matches. Seven Python actor/data tests pass.
- The repeated `boundary-stress-before-v1.json` has a source-timing caveat.
  Its adjacent provenance file records the loaded assembly hash. Do not use it
  as source-matched final evidence. The first `after-v1` command failed because
  Play mode was off. The successful result is `after-v2`.

`PlayerCurriculum.cs` now collects teacher labels on independent-control states.
It can mix a prior model's actions with teacher actions. Each report records the
teacher fraction, actual teacher/model decision counts and both source hashes.
Prior development models can supply states, but they are not relabelled as
trained on new source. Actor-only evaluation still requires matching source.
The first drill uses one fixed shot. Competitive reward training is still pending.

The first independent-control training set is
`artifacts/player-agents/curriculum-20260906-073727.json` with its `.jsonl` file.
It contains 61,764 examples from 96 rallies. Collection took 130.6 seconds.
All actions in this set came from the teacher. The teacher made 508 legal
non-serve hits, with 133, 116, 117 and 142 by seat. This is not a learned result.
The training source hash is
`0850b0bb1c728841315bb3df0bdfda66075190c40f6b2c68308da7c08bccb4ae`.

The Python data loader checks source, contact, team-model and baseline hashes.
It also checks the seed partition, player index, row count, finite observations
and valid actions. Final evaluation seeds remain unused.

### Third model: fixed-shot imitation, rejected

The model in `artifacts/player-agents/imitation-20260906-074116` was fitted for
160 epochs in 46 seconds. It used the new 61,764-row training set and separate
19,360-row development set (`curriculum-20260906-074005.json`). Unity/Python
output parity passed.

The model-only report `development-selfplay-20260906-074228.json` has just three
legal returns in 32 rallies, by seat 1, 1, 0 and 1. This failed model is retained.
Its movement correction reached 152.2 m/s². The saved trace
`artifacts/player-agents/third-actor-motion-trace.json` locates the correction at
rally 9, approximately 3.0 seconds, when players 2 and 3 converge. This is a
partner-separation correction, not the outer court boundary case fixed above.
The current partner brake still needs a changing-direction test and repair.

The next collection mixes teacher and third-model actions with a 50% teacher
probability. This is disclosed training assistance, not independent game play.
It will add teacher labels for states reached by the failed model.

### Fourth model: useful development progress, not accepted

`curriculum-20260906-074412.json` contains 41,040 mixed-control examples from
96 training rallies. Actual decisions were 20,471 teacher actions and 20,569
model actions. Collection took 95.2 seconds. It used the third model without
changing that model's recorded source hash.

The fourth model is `artifacts/player-agents/imitation-20260906-074641`.
It used both training sets, for 102,804 examples. Fitting took 68.7 seconds.
Unity/Python parity passed on 32 cases, with maximum error 0.000003815.

Its model-only report `development-selfplay-20260906-074811.json` has 76 legal
returns in 32 rallies, by seat 21, 20, 15 and 20. Mean total hits were 3.375,
including serves. This uses the same development setup and initial seed as
the third model. It shows that learner-state examples helped. It does not
establish competitive match performance or a final acceptance pass.

The fourth model still reached a partner correction of 170.6 m/s². It has not
replaced the accepted doubles models or the default control-probe scene.

The initial random crossing stress did not reproduce this class of failure.
`partner-stress-before-v1.json` retains those four passing diagnostic cases.
A recorded 120-frame sequence in `partner-motion-fixture-v1.csv` does reproduce
the third model's 152.2 m/s² correction. `partner-replay-before-v1.json` records
that reproduction, without a model or teacher in the replay path.
Fixture hash: `9d4d7a7bc892fcb4e2a5fa74c8651cdd9fbf0809a353f237be08b8466fe824f9`.
The capture command timed out at the CLI after writing the complete fixture;
the separate replay command completed successfully and verified the failure.

## Partner-brake repair

The partner brake now checks stopping distance from actual vector speed, not
only its closing component. It checks the next motor velocity. This accounts
for acceleration shared between the forward and sideways directions. It does
not select a hitter, recovery position or shot.

- `partner-replay-after-v1.json`: the recorded failure now has maximum
  acceleration 14.012 m/s² and minimum separation 0.657 m. No threshold violation.
- `partner-stress-after-v1.json`: all four crossing/pursuit cases stay below
  14.05 m/s². Minimum separation across the cases is 0.641 m.
- `boundary-stress-after-v3.json`: all four boundary/corner cases remain below
  14.05 m/s² after the partner repair.
- The recorded inputs are stored in
  `Assets/Picklebot/PlayerAgents/Tests/Fixtures/partner-motion-v1.csv`.
  The runtime regression checks its hash and replays it without a model.
  Test-only reflection restores the captured initial velocity; it is not
  available as an actor action.
- `runtime-tests-v4.json`: all 13 runtime tests pass after the repair, including
  the recorded partner regression. The 15 Editor contract tests and seven
  Python tests also passed in this work stage. The frozen baseline is unchanged.

Source hash at this repair:
`e962ea6bf7b9e173392d722252dbdd4c8c41b4d699931596340382b460d6a85f`.
The four models were trained on earlier source. Their hashes and results are
retained as historical development evidence. Do not relabel them as trained
on this repaired motor. The default evaluator correctly rejects stale source.

Next work:

1. Collect new-source learner-state data with the fourth model as a disclosed
   historical development actor. `PlayerCurriculum.Start` permits this only
   for training/development collection and records both source hashes.
2. Fit and test a new-source model. Check movement limits over complete games,
   not only the recorded failure and synthetic stress cases.
3. Add competitive updates, a frozen-baseline opponent adapter, coverage probes
   and the final comparisons. No competitive RL or final evaluation has run yet.
4. Install only an evaluated model in the final scene. Recheck controls and
   fault replay with that model. Keep the existing doubles baseline intact.

The goal remains active. The models show useful progress, but the complete
independent-player 2v2 acceptance conditions are not met.

## Competitive training path: implementation in progress

`BaselineControl.cs` adapts the saved doubles controller for use as an opponent
in the independent-player world. A team mask restricts it to its own seats.
It cannot call a learned player's body step. Its prepare phase reads state but
does not move any body. Four-player actor-only matches have no baseline adapter.

The player decision loop now supports inactive baseline seats. It does not call
an actor for those seats or emit training records for them. Per-player motion
maxima separate candidate movement from the frozen opponent's movement.

The first physical parity test passed eight sampled-policy rallies. It also
matched every checked state for 30,000 maximum-probability steps, but that mode
completed only four long rallies before the test cap. The failed cap report is
retained as `artifacts/player-agents/baseline-adapter-tests-v1.json`. The test cap
was increased to allow eight full rallies; no opponent behaviour was changed.

`PlayerCompetition.cs` implements development comparisons and on-policy training
collection against either the frozen baseline or an older actor checkpoint.
It alternates candidate court ends between games and preserves separate player
actions. It records complete game boundaries, faults, legal hits, per-player
motion limits, hashes and training-only sample traces. Final seeds are rejected.
Incomplete games are retained and stop the run; they cannot become training wins.

The collector supports two disclosed objectives:

- `rally_win`: each candidate teammate receives the same terminal rally result.
- `game_win`: each candidate teammate receives the same terminal game result.

There is no rally-duration reward or teacher action in this collector. A value
estimator can read the current own and teammate observations during Python
training. The exported actor still reads only its own 54-value observation.

`scripts/player_ppo.py` contains the training-only critic, independent action
log probabilities, terminal-aware advantage estimates and clipped PPO loss.
`scripts/player-agents-ppo.py` validates a rollout, checks Python/Unity sampled
log probabilities, applies one update, and saves actor, critic and provenance.
These implementation checks are not evidence of improved playing strength.

### Verified baseline adapter and first competitive update

- `baseline-adapter-tests-v2.json`: all 17 runtime tests passed. Both sampled
  and maximum-probability baseline modes matched the original controller for
  eight rallies. The comparison checks every physics step, including ball and
  paddle positions, player positions, faults, scores and service state.
- `actor-contract-tests-v3.json`: all 15 Editor tests passed.
- `competition-20260906-081942.json`: the fourth imitation model lost all three
  development games, each 0–11. It made 36 legal returns in 35 rallies, but won
  no rally. Candidate acceleration stayed below 14.05 m/s². This comparison
  used the repaired motor and explicitly retained the older training source.
- `competition-20260906-082100.json`: first competitive training batch, with
  sampled candidate actions. It contains 13,098 decisions from 70 rallies and
  five complete games. Candidate teams won eight rallies and made 66 returns.
  Collection took 43.2 seconds. The objective was shared terminal rally reward.
- `ppo-20260906-082245`: first PPO actor and training-only critic. Six minibatch
  updates were applied before the policy-change limit stopped the pass. Python
  and Unity sample log probabilities differed by at most 0.00001431. Export
  parity passed. No teacher action entered this PPO collection.
- `competition-20260906-082358.json`: the first PPO model still lost the same
  three development games, each 0–11. It made 35 returns in 35 rallies. This
  is not an improvement. Both reports are retained.

The rollout validator also checks simultaneous own/teammate critic inputs,
terminal placement and team reward signs against the recorded game/rally result.
It validated all 140 player episodes in the first real competitive batch.
Fifteen Python actor, data and PPO tests pass.

### Shot exploration stage

The swing controller previously restarted its contact plan on every sampled
shot change. It now keeps the selected target within the final 130 ms before
planned contact and the 55 ms follow-through window. The actor can still move
or cancel its attempt. This is a bounded low-level execution rule, not a
central hitter selector. The HUD shows requested and selected shot indices.

`scripts/player-agents-explore.py` rescales only the nine shot logits of an
existing model. It preserves movement and hit outputs, the original training
source and the parent hash. Its outputs are labelled as exploration starts,
not trained improvements. `exploration-20260906-083040` uses a scale of 0.2.
The next collection will use game-win rewards against an older saved actor.

### First full-game reward batch

`competition-20260906-083237.json` records 106 training rallies and four complete
games against the fourth imitation actor. The exploration candidate won two
games and lost two. The batch contains 17,778 sampled candidate decisions. It
took 65.7 seconds to collect. Rewards occur only at the end of each full game.
Candidate maxima stayed within numerical tolerances of 3.8 m/s body speed,
14 m/s² acceleration, 12 m/s paddle speed and 0.62 m reach.

`ppo-20260906-083431` is the first update from that batch. Six minibatch updates
were applied before the policy-change limit. Log-probability parity error was
0.00001335. Export parity passed. This experiment used discounted GAE and is
retained separately from the undiscounted game-outcome experiment below.

The game-win trainer now uses gamma 1 and lambda 1 for complete-game returns.
Thus the same final win/loss result reaches early decisions without a preference
for a longer losing game. This is Monte Carlo advantage estimation with a
training-only learned value baseline. Rally-win warm starts retain their earlier
GAE settings. The training report records the exact settings for each run.

`ppo-20260906-083807` is the undiscounted full-game experiment from the same
on-policy batch and same exploration parent. It applied 280 minibatch updates
at learning rate 0.00001. Final measured KL was 0.00187. Export parity passed.
This is an alternative update from the same parent, not an off-policy update
from a changed actor.

The older-opponent development comparison uses sampled players and initial seed
1100800. The exploration parent won both complete games: 11–7 on the near end,
then 13–11 on the far end. It made 75 returns in 75 rallies. The undiscounted
PPO model lost both games: 6–11 on the near end, then 9–11 on the far end. It made
72 returns in 71 rallies. Reports are `competition-20260906-083712.json` and
`competition-20260906-083849.json`. Two games are a small sample, but they do not
support an improvement claim. The updated model is not accepted as better.

Training throughput for the first real competitive batch was 108,701 physics
steps in 43.2 seconds. The optimizer portion took 0.14 seconds; data loading and
CLI overhead are separate. The combined measured rollout/optimizer portions
were about 2,507 physics steps per second. Local simulation remains practical.

The shot-commitment regression passed in `shot-commitment-test-v1.json`. It uses
a physical contact plan and checks target retention, actor movement and cancel.
The source after this control change is
`87df81f849b2aa68d413f058a83048991817ac577441a3852c86b59c4178982e`.

The current evidence points toward broader return training against varied
baseline shots. Fixed-shot self-play success did not transfer to the baseline.
Continue the competitive comparisons, but do not treat optimizer updates or
wins against a weaker old actor as the final goal.

### Varied-shot baseline curriculum

`competition-20260906-084338.json` tested the undiscounted PPO actor against the
sampled frozen baseline on development seed 1100900. It lost all three complete
games. Candidate scores were 1–11, 0–11 and 1–11 across 39 rallies. This is not
an accepted model.

The curriculum now supports a frozen baseline opponent. It records labels and
actions only for the candidate pair. It alternates the candidate court end at
each new game. The teacher can use one return shot while the baseline uses all
of its shot options. This broadens incoming-ball states without adding a
teacher to the exported actor.

Reports identify opponent mode, candidate end, teacher and learner decision
counts, candidate and opponent returns, and complete or partial game results.
A requested imitation-data limit can end a partial game, but it cannot count
as a win. Safety-cap and failed runs are rejected by the data loader. Ownership
checks reject opponent records, duplicates and missing teammate decisions.
All 19 Python actor and PPO tests pass after this change. All 63 frozen baseline
files remain unchanged, and the doubles verifier passes.

All 18 runtime regressions passed after the collector change in 62.31 seconds.
All 15 Editor tests also passed. The first runtime launch failed before testing
because Play mode was already active. The second launch produced the pass result.
See `runtime-test-summary-20260906-085642.json` and
`editor-tests-20260906-085835.json`. The current Unity source hash is
`9a66ef3114f5b642cdab6e582767523e25ffddaad9386c1b1eca90f38d5de0e4`.

`curriculum-20260906-085939.json` collected 64 teacher-controlled training
rallies against the sampled baseline on seeds starting at 1001000. It contains
34,308 candidate-only records, 291 candidate returns and 285 opponent returns.
Collection took 143.82 seconds. The teacher pair won the near-end game 11–5 and
lost the far-end game 2–11. A third partial game ended at the requested data
limit and is not a win. The current-source loader and ownership checks accept
the batch. These are teacher results, not learned-model results.

`curriculum-20260906-090254.json` used the fourth imitation model for a 50/50
teacher/learner mixture. It started on the far end at training seed 1001100.
The 64 rallies produced 13,782 valid candidate records: 6,822 teacher decisions
and 6,960 learner decisions. The candidate pair made 90 returns but lost all
five complete games. Collection took 62.10 seconds. The final partial game is
retained. This batch supplies labels on learner-reached states; it does not
show a competitive improvement.

`curriculum-20260906-090429.json` supplies 16,238 teacher-controlled development
records on seeds starting at 1101000. The 32 rallies contain 135 candidate
returns. The far-end teacher pair lost its complete game 6–11; the next near-end
game is partial. The batch took 66.25 seconds. It is separate from the two
training batches. No final evaluation seeds have been used.

`imitation-20260906-090616` is the next return warm start. It uses two 256-unit
hidden layers and the 48,090 records from the two current-source training
batches. It trained for 160 epochs in 58.24 seconds. The separate development
batch has 16,238 records. Its model hash is
`40aa880383c0f28c95069a8643fc15d4e09b0f1fc5e4b4d3e2d1b351afa19b24`.
Unity/Python parity passed on 32 inputs with maximum error 0.00000191. This is
supervised return training, not a claim of competitive success.

`competition-20260906-090740.json` tested this model without teacher help against
the sampled baseline, using deterministic candidate actions and development
seed 1101100. It made 90 legal returns and won seven rallies across 37 rallies.
It lost both complete games: 1–11 on the near end and 2–11 on the far end.
Maximum candidate acceleration was 14.0142 m/s². The run took 42.98 seconds.
The model does not meet the final game-win requirement.

The matched older-model check is `competition-20260906-090902.json`. It uses
the same initial development seed, baseline mode and deterministic candidate
setting. The fourth imitation actor made 43 returns and won three rallies in
40 rallies. It lost all three complete games. The new warm start made more
returns per rally (2.43 versus 1.08), but neither model won a game. Game lengths
and later trajectories differ. This small comparison supports a return-skill
improvement only; it is not final competitive acceptance.

Next: collect further learner-state labels with the new warm start and less
teacher intervention, then repeat teacher-free baseline comparisons. Continue
team-win training only with recorded on-policy batches. The final 80-game
comparison, coverage probes, movement ablation and accepted playable model
remain incomplete. Do not reduce the fixed acceptance conditions.

## Resumed training: 2026-09-07 local time

The previous completed training cycle made progress: it added baseline-opponent
data collection, validated candidate-only records, saved a model and measured
teacher-free returns. The later goal-control exchange did not train a model.
The resumed goal has a fresh blocked audit. No current project blocker is known.

Preflight confirmed Unity is connected, Play is active, no collector is running,
the current source still matches `9a66ef3114f5b642cdab6e582767523e25ffddaad9386c1b1eca90f38d5de0e4`,
and all 63 baseline files remain unchanged. The next batch uses the current
return model for 90 percent of decisions and the teacher for 10 percent.
It starts at training seed 1001200 and requests 128 rallies against the sampled
baseline. Final evaluation seeds remain reserved.

The first batch, `curriculum-20260906-164136.json`, stopped with an incomplete
game after 77 rallies. It reached the 35-second rally limit. Its 24,594 rows
are retained but excluded from training. A same-seed repeat,
`curriculum-20260906-164637.json`, completed 128 rallies in 246.24 seconds.
It supplied 48,450 valid rows: 4,962 teacher decisions and 43,488 learner
decisions. The candidate pair made 399 returns. The repeat did not reproduce
the stall. Full-match deterministic repeatability is therefore not established.

`imitation-20260906-165201` trained before the runtime reset change below.
It uses 96,540 training rows and the unchanged 16,238-row development set.
Training took 80.24 seconds for 160 epochs with two 256-unit hidden layers.
Its actor hash is
`d364339d8b1ee56d9223a206501158c9366ee871092f2131782ce8e5bc8f6176`.
Development movement error increased. This model is not accepted as an
improvement. Its training source remains `9a66ef3114f5b642cdab6e582767523e25ffddaad9386c1b1eca90f38d5de0e4`.

## Dead-ball reset correction: 2026-09-07 local time

Source inspection found a reproducible unresolved-fault case. After a volley
momentum fault, a stationary player inside the kitchen never stepped out.
The frozen rules correctly waited for actual foot clearance before scoring.
Four new regression cases failed on the old controller. This is evidence of
the reset defect, not proof that it caused the earlier collection failure.
See `reset-tests-red-20260906-1659.json`.

`PlayerDeadBallReset` now commands a slow step away from the net only after
a recorded kitchen momentum fault, one second of dead-ball time, and low
body speed. It uses the normal movement constraints and actual feet. It
does not alter rule state, scoring, actor decisions or live-rally movement.
The helper stops when both feet are outside. The demo labels this scripted
reset. Metrics include `deadBallClearanceSteps`.

All nine focused cases pass, including all four seats with either controller
type, unchanged winner and scoring, physical limits, and reset-state isolation.
See `reset-tests-green-20260906-1703.json`. All 27 runtime tests then passed
in 63.21 seconds. The full report is `runtime-tests-20260906-1704.json`.
Both eight-rally baseline parity modes still pass. All 15 Editor tests passed;
see `editor-tests-20260906-1704.json`. All 19 Python actor/PPO tests passed.
All 63 frozen baseline files remain unchanged. The original doubles verifier
also passed against its saved evidence.

Current runtime source hash:
`19e9cac6e7bf5def0fdb803477519078980bc1da69962801a4c3c37ce34ecc7d`.
The new actor passed Unity/Python parity on 32 inputs, with maximum error
0.00000287. It still has its true older training source hash. Development
comparison explicitly permits historical models and records both hashes.

Unity had intermittent main-thread timeouts. UI inspection found an open Edit
menu after an Escape request did not dismiss it. The menu's Cancel action
closed it, and compilation status responded again. Do not interpret a CLI
timeout as a completed test. Read the report's actual test count and results.

The new model's teacher-free development run is
`competition-20260906-170506.json`. It lost all three games: candidate scores
0–11, 1–11 and 2–11. It made 108 returns and won six of 44 rallies in 53.79
seconds. Candidate acceleration stayed below 14.027 m/s². The much larger
all-player acceleration values belong to the frozen baseline opponent.
This remains a disclosed baseline limitation, not candidate movement evidence.

The matched previous-model run is `competition-20260906-170634.json`.
It reproduced the earlier 37 rallies, 90 returns, seven rally wins and two
game losses: 1–11 and 2–11. It took 41.45 seconds. Both checks use development
seed 1101100, deterministic candidates and the sampled frozen baseline.
Neither run needed dead-ball clearance. The sixth imitation model is not
promoted. The fifth model remains the return warm start for team-win training.

## Repeated team-win updates

`exploration-20260906-170811` scales the fifth model's shot logits by 0.4.
This is disclosed exploration initialization, not learning. Its training source
hash is not rewritten. `competition-20260906-170833.json` then collected
234 rallies from seven complete games against the saved fifth actor. Training
seeds start at 1002000. The candidate pair won one game. Collection supplied
28,038 on-policy rows in 128.77 seconds, with team game-win rewards only.

`ppo-20260906-171151` used those rows for 112 updates in 1.53 seconds.
It used four epochs, batch size 1024 and learning rate 0.00003. Sampled log
probability error between Unity and Python was 0.00000906. Export parity passed.
Its actor hash is `71e0abb095cac3ddd81d33069dd279a6148f9d0617b5e42e084edd944ae1e100`.
The teacher-free baseline check, `competition-20260906-171246.json`, lost all
three games, with candidate scores 1–11, 1–11 and 0–11 across 41 rallies.
This update is not an accepted competitive improvement.

`scripts/player-agents-train-loop.py` now supports bounded consecutive updates
with a fixed saved opponent. Each iteration saves collection, PPO, export-parity
and development evidence. It checks current source, model identity, opponent,
seed split and complete games. It does not retry uncertain state-changing CLI
commands, use final seeds or promote models. Four parser/target tests were added;
all 23 Python tests pass. The first four-iteration run starts from this PPO model
and critic, requests 256 rallies per iteration, and starts training seeds at
1003000 and development seeds at 1102000. Results remain pending.

Active run: `artifacts/player-agents/training-loop-20260906-171424/progress.json`.
The local process is running as terminal session 23611. Do not start another
Unity collection or change C# while it runs. Read its saved progress before
continuing. The driver performs four bounded iterations and does not select
or install a model.

Iteration 1 collected 286 rallies from eight complete games in 165.11 seconds.
The candidate won three games and 140 rallies, with no truncated rally.
The 34,254 rows produced `ppo-20260906-171721`, with 136 updates in 1.88 seconds.
Export parity passed. The baseline development check,
`competition-20260906-171722.json`, made 84 returns in 38 rallies but lost all
three games 0–11. It used development seed 1102000. This is not an accepted
improvement. Iteration 2 finished collection at training seed 1004000 and is
now testing its update at development seed 1103000. The progress file is the
current run record; this text is a checkpoint, not a live status feed.

Next: let this bounded run finish, inspect all saved development results, and
retain failures. Keep the goal active. Final 80-game acceptance, useful coverage,
movement ablation and a verified accepted model in the scene remain incomplete.

## Four-update result: 2026-09-07 local time

`training-loop-20260906-171424` finished successfully. Its process, session
23611, exited with code 0. The saved progress file identifies all four models,
collection files, parity checks and baseline development checks. A copy of the
driver and the PlayerAgents source was retained with the run before later
trainer changes.

| Update | Training rows | Training game wins | Saved model | Baseline development game wins |
| --- | ---: | ---: | --- | ---: |
| 1 | 34,254 | 3/8 | ppo-20260906-171721 | 0/3 |
| 2 | 32,946 | 7/9 | ppo-20260906-172050 | 0/3 |
| 3 | 30,476 | 6/8 | ppo-20260906-172429 | 0/2 |
| 4 | 31,822 | 5/8 | ppo-20260906-172759 | 0/2 |

These are complete games. The development checks use different development
seed blocks, so they are not a matched ranking of the four models. None passes
the strong-baseline requirement.

The last model then played the saved fifth imitation actor on development seeds
starting at 1107000. `competition-20260906-172910.json` contains 140 rallies and
four complete games. The candidate won three games, including both far-end
games. It made 66 returns. The matched starting-model check,
`competition-20260906-173214.json`, used the same initial seed and settings.
It contains 147 rallies and four complete games. The starting model won two
games, both on the near end, and made 75 returns. Both candidates used
deterministic actions against the sampled saved opponent. This small result
supports a possible game-performance improvement against that opponent only.
It does not establish a robust win-rate gain or strong-baseline acceptance.

## Acceptance checks and next training stage

`scripts/player_acceptance.py` checks the frozen baseline schedule and statistics.
It requires 80 unique final game seeds, both baseline modes, balanced court ends
and partner swaps, current provenance, fixed control timing, per-seat non-serve
returns and the fixed Wilson and truncation gates. Incomplete games remain in
the denominator. Missing evidence is rejected. These are baseline checks only;
they do not claim that coverage, ablation, physical tests or the scene are done.

`scripts/player-agents-final-check.py` checks actual source/model/baseline hashes
and export parity before applying those gates. It writes a new audit artifact
even on failure. `final-check-development-rejection-20260906-1726.json` confirms
that it rejects a real development report used as final evidence. Its filename
was chosen before execution; its internal UTC timestamp is authoritative.
The final collector still needs explicit partner-swap and timing fields. No
final evaluation games have been run. Ten acceptance unit tests pass.

The PPO trainer now has a `--heads shots` stage. It freezes hidden layers,
movement outputs, hit output and movement noise. Only the nine shot logits
can change. A test applies five optimizer updates and verifies that movement
and hit outputs stay exactly unchanged. The trainer also checks protected
parameter changes after each real update. All 34 Python tests pass.

The next bounded run is
`artifacts/player-agents/training-loop-20260906-173623/progress.json`,
terminal session 33016. It starts from `ppo-20260906-172759`, trains against
the frozen sampled baseline, and requests four updates of 128 rallies each.
Training seeds start at 1008000; development seeds start at 1108000. This stage
uses team rally-win rewards to train shot strategy while preserving return
controls. Earlier complete-game training remains recorded. The run saves
trainer and runtime source snapshots. Do not edit C# or its trainer files while
it runs. Inspect the live handle and saved progress before starting other jobs.

The first real shot-only update is `ppo-20260906-173836`. It used 32,818
on-policy rows for 132 optimizer updates in 1.49 seconds. The measured maximum
change to protected movement/hit/noise parameters is exactly zero. Export
parity passed. Its baseline development check,
`competition-20260906-173838.json`, lost all three games, with candidate scores
3–11, 0–11 and 1–11 across 46 rallies. No model is promoted. The second
shot-only iteration is collecting new games. Terminal session 33016 is live.

## Shot-only stage completed

Session 33016 exited with code 0. The run
`training-loop-20260906-173623/progress.json` contains all four completed updates.
Each update passed export parity and kept protected parameters exactly unchanged.

| Model | Training rows | Updates | Baseline development game wins |
| --- | ---: | ---: | ---: |
| ppo-20260906-173836 | 32,818 | 132 | 0/3 |
| ppo-20260906-174154 | 36,248 | 144 | 0/2 |
| ppo-20260906-174443 | 26,026 | 104 | 0/3 |
| ppo-20260906-174805 | 30,704 | 120 | 0/3 |

The last actor hash is
`fa51e4e7b2a0e94a743d33b15da6ae8797c98a43e6f7d5e644589b8147ab28dc`.
These results do not establish improved baseline play. More training is not
started until the contact limitations below are addressed.

## Fixed-ball coverage and expired swings

`scripts/player-coverage-probe.cs` runs 48 development cases: 16 fixed incoming
ball setups, each with learned control, disabled movement, and a labelled
privileged diagnostic teacher. It uses both court ends, four lanes and two
starting depths. The incoming ball is injected explicitly. A real initial
drop establishes the serve-bounce observation; the rally rule setup uses
public rule calls. Opponents stand still. This is not a match or final test.
The probe records source/model/script hashes, actions, observations, actual
paddle contacts, legal landing events, movement and frame traces. It does not
change any gameplay source or use a teacher in the learned cases.

The first report, `coverage-20260906-175038.json`, completed all 48 cases.
The learned model and movement-disabled model made no legal hits. The teacher
made four legal hits and two legal landings in its 16 cases. The report with
additional action and paddle traces is `coverage-20260906-175644.json`.

An initial interpretation that the incoming setup might be out of bounds was
incorrect. The trace shows a legal first bounce at depth 4.281 m. The out
fault is the second bounce after the missed return. The sampled rebound peak
is about 0.476 m. The frozen swing planner excludes contact below 0.52 m.
This prevents a post-bounce attempt on that trajectory. Some early volleys are
possible, but the teacher also misses most of these difficult setups. Do not
use this as evidence of useful learned coverage or a passed movement ablation.

The action traces also found 29 learned-control frames with an expired swing
still active. `StrokeController.Plan` can retain a plan indefinitely once it
enters the commitment window. A new execution regression reproduced that
defect; see `swing-expiry-red-20260906-1800.json`.

`PlayerSwing` now clears a missed plan after its existing 55 ms follow-through.
It can then plan another swing if the actor still requests a hit. This does
not select a hitter, change foot movement, extend the reach, or alter the ball.
All 28 runtime tests passed in 66.99 seconds, including both baseline parity
modes. All 15 Editor tests and 34 Python tests passed. See
`swing-expiry-runtime-green-20260906-1803.json` and
`swing-expiry-editor-green-20260906-1803.json`. All 63 baseline files are unchanged.

The current runtime source hash is
`0cd19ada7f06647abc72e26d46de6fba42c259cd3ed2bfbe0ff10a59e99e548f`.
Saved models retain their true earlier training source hashes. The post-fix
probe, `coverage-20260906-180402.json`, has zero expired-plan frames. Coverage
is unchanged: learned 0/16 legal landings, movement-disabled 0/16, teacher 2/16.
Thus the expiry defect is fixed, but low-ball contact remains unresolved.

Current state: Play is active; no training collector or coverage callback is
running. No model has been installed as accepted. Keep the goal active.
Next, test a bounded low-ball contact/grip extension in PlayerAgents while
preserving the original baseline. Do not increase ball bounce, enlarge the
paddle, stretch the arm, teleport a player or add automatic live-rally foot
movement to make the probe pass. Check physical feasibility and contact limits
before new training. The final collector with partner swaps, full acceptance,
useful coverage and the accepted playable scene are still incomplete.

### Low rebound execution and paddle-limit investigation — 2026-09-06 18:28 UTC

The existing planner rejected all contacts below 0.52 m. Two new regression
cases failed on both court ends before the change. Evidence:
`low-rebound-red-20260906-1812.json`. The first planning-only green result is
`low-rebound-plan-green-20260906-1814.json`.

Added `PlayerContactPlan` in PlayerAgents. It retains the frozen normal-height
planner and adds a 0.30–0.52 m fallback. The low grip rolls -80 degrees, within
the existing body limit. It checks travel acceleration, preparation time,
crouch, rotation time and arm reach. It does not move feet or the ball. The
privileged diagnostic teacher uses the same execution planner. Exported actors
still receive only their own observation and action interface.

The original contact residual model was fitted to upright higher contacts.
The new low grip therefore uses neutral residuals. No baseline model or source
was edited. This is not a calibrated low-contact model.

Physical diagnostics exposed a second problem: the original body's hard reach
projection can override its nominal paddle acceleration. A low-contact run
reached about 714 m/s². Added `PlayerPaddleMotor` to constrain commanded velocity
before the body step. It checks speed, acceleration and the next hand position.
It prefers early braking and a 6 m/s shoulder-relative hand speed, with slower
crouch/rotation where necessary. These preferences do not replace the hard
constraints. If no hard-feasible command is found, it reports that condition;
it does not claim a guaranteed physical solution. Full-body kinematic modelling
remains provisional. New metrics record paddle acceleration and failed guards.

Retained physical diagnostic runs include `low-contact-20260906-181522.json`,
`181850`, `182014`, `182126`, `182235`, `182338`, `182442` and `182614` (the same
filename prefix and `.json` suffix). These are development experiments, not
final evaluation. The overly slow variant reduced legal returns; it was not
used as evidence of improved play. The final listed run has 16/16 real legal
contacts and 8/16 legal landings across four stationary depths, two court ends
and loaded/unloaded residual settings. Its maximum measured acceleration is
100.012 m/s², within the 100.1 numerical test tolerance. Deeper stationary
contacts still fail to clear the net or reach the correct side. The initial
probe measured reach before physics synchronization; later runs measure it
after simulation, which is the correct comparison with the 0.62 m limit.

Coverage `coverage-20260906-182615.json` completed all 48 cases. The diagnostic
teacher made 12/16 legal contacts and 10/16 legal landings, versus 4/16 and 2/16
before the low-grip extension. The historical learned actor and its disabled-
movement ablation still made 0/16. This is execution progress, not learned
coverage or accepted match performance. No actor has been promoted.

The permanent low-rebound test now checks eight cases: four depths on both
court ends, physical low-face contact, unchanged feet, reach, speed, angular
speed and acceleration. It also requires legal landings for the two nearer
depths. A full runtime test run is in progress. Python: 34 tests passed.
Baseline: all 63 files unchanged. Final evaluation seeds remain unused.

The full runtime suite passed: 36/36 tests in 71.81 seconds, including all eight
physical low-contact cases. Saved report:
`low-contact-runtime-green-20260906-1830.json`. Editor tests passed 15/15 in
0.8 seconds: `low-contact-editor-green-20260906-1831.json`. Current source hash:
`1459f288708b9e580d0bef43dbda99a130e847fd263b415e8d3dd271fcd9b82e`.
The guard now tries the hard constraints alone if its preferred braking
clearance is temporarily infeasible. An unresolved hard constraint remains
explicitly reported. Global paddle-acceleration metrics include the unchanged
scripted serve and any baseline-controlled players; interpret ownership and
phase before attributing those values to the independent swing controller.

Throughput `throughput-20260906-183153.json` measured 6,000 physics steps per
case on this laptop: saved baseline 2,084 steps/s, independent hold 4,169
steps/s, and independent constant attempt 1,939 steps/s. This is a short local
benchmark, not a claim about cloud performance or a learned policy. Its global
paddle-acceleration peak includes the unchanged scripted serve. No cloud
resources were requested.

Fresh current-source curriculum collection started at 18:32:30 UTC:
256 requested rallies, training seed 1013000, privileged teacher probability
1, fixed flat shot, frozen sampled baseline opponent, alternating candidate
court ends. No historical rows will be relabelled as current-source data.
This stage is imitation warm-start data, not competitive reward training.

`scripts/player-agents-refresh.py` continues that exact collection and checks
the saved report identity before fitting. It rejects incomplete reports,
different jobs, stale source, wrong splits and changed teacher settings. Its
five tests pass; the Python player suite now has 39 passing tests. It will
collect 64 development rallies at seed 1117000, fit a 256-unit imitation actor
for 160 epochs, check Unity export parity, and run 32 requested actor-only
development rallies at seed 1118000. It does not install or promote a model.
Driver state: `artifacts/player-agents/refresh-20260906-183631/progress.json`.
The initial 256-rally collection completed successfully. Development collection
is now active. Keep runtime source unchanged until this bounded run finishes.

### Current-source warm start failed actor-only checks — 2026-09-06 18:50 UTC

The bounded refresh completed. Training collection has 135,086 decisions,
256 rallies and 1,144 candidate-side teacher returns in 644.1 seconds. Its
teacher-controlled pair won 2/8 completed games; the requested rally cutoff
left one additional game incomplete. This is teacher performance only.
Development collection `curriculum-20260906-184328.json` has 33,180 decisions
from 64 rallies. Fitting took 166.5 seconds for 160 epochs.

Saved candidate: `imitation-20260906-184615/actor.json`, hash
`575b356c394283792188708bfdbf92a55fd69dcdff28ee918fe406446e62b5de`.
Unity parity passed 32 cases, maximum error 0.000003815. Actor-only report
`competition-20260906-184903.json` completed 35 rallies and three games. The
candidate lost all three 0–11. It is not accepted or installed.

Current-source coverage `coverage-20260906-184945.json` completed all 48 cases.
Teacher: 12/16 legal contacts, 10/16 landings. Actor and movement-disabled
actor: 0/16. The trace shows the learner requesting a hit but moving toward
the 3.5 m recovery depth instead of braking at its contact location. In the
right-wide, 6 m start fixture, it moves about 2.91 m and lets the ball pass.
The teacher's corresponding forward command decreases toward zero at contact;
the learner's command instead rises above 0.9. Good prediction loss on teacher
states is not evidence of closed-loop control success.

Corrective collection started at 18:52:13 UTC: 128 training rallies, seed
1014000, same baseline opponent, current actor checkpoint, teacher action
probability 0.25, fixed flat shot. The teacher labels all candidate decisions
on this mixture's states. This is disclosed dataset aggregation, not RL and
not actor-only evaluation. Added `--initial-actor` to the imitation fitter;
it checks source/configuration/contact/protocol, width and recorded training,
and records the parent checkpoint hash. Its tests bring the Python suite to
44 passing tests. Runtime source remains unchanged. No final seeds were used.

### Corrective fine-tune: more real returns, still not accepted — 2026-09-06 19:00 UTC

Corrective training `curriculum-20260906-185213.json` completed 128 rallies and
26,214 decisions in 147.0 seconds: 6,441 teacher actions and 19,773 actor
actions. All recorded labels remain teacher labels on those reached states.
Separate development `curriculum-20260906-185533.json` has 6,426 decisions.
The fine-tune used the previous checkpoint, 80 epochs, learning rate 0.0001,
batch 1024 and the existing 0.8 neutral-paddle augmentation. It took 19.3 s.

New checkpoint: `imitation-20260906-185656/actor.json`, hash
`88858b3d81eabe52ac80b4f22d30dbd6817effd4eb6af4ab8cb9d1fd6c074061`.
Its parent hash is recorded in `training.json`. Unity parity passed with
maximum error 0.000003815. Coverage `coverage-20260906-185756.json` still gives
0/16 legal landings for learned and movement-disabled actors, versus 10/16
for the privileged teacher. No coverage success is claimed.

Actor-only matches `competition-20260906-185814.json`, development seed
1120000, completed 48 rallies. The candidate made 80 legal non-serve returns,
split 24/35/6/15 across its four physical seats. It lost three games, scoring
0, 0 and 1 against 11. Its parent made 6 returns in 35 rallies on development
seed 1118000. These are different seed blocks; the increase is a development
signal, not a paired causal estimate or acceptance result. Retain both runs.
The new report has 26 failed paddle-guard steps. Their phases and measured
corrections still require a focused audit; do not claim universal bounded
paddle motion from the successful stationary tests.

This turn made progress: low-ball execution is tested, actual acceleration
corrections were reduced in the low-contact fixtures, and corrective training
produced more real returns. It is not a blocker turn and the goal is not
complete. Current source remains
`1459f288708b9e580d0bef43dbda99a130e847fd263b415e8d3dd271fcd9b82e`.
All 63 baseline files are unchanged. Unity tests: 36 runtime + 15 Editor.
Python tests: 44. Play is active, all six Editor job flags are false, and
coverage callback count is zero. Refresh process 19133 and fit process 67521
both exited successfully. No model was installed or promoted.

Next work: use a varied incoming-ball skill curriculum before more full-match
reward training. Randomize incoming lane, depth, velocity and player starting
positions with separate training/development seeds. Use the existing physical
ball and public rule setup, record injected resets explicitly, and retain
teacher/actor ownership and source/script hashes. Do not train on the fixed
coverage probe's development records or final seeds. The candidate must learn
to move to and brake near its contact location, without scripted live foot
targets or a central runtime hitter selector. Reuse the current checkpoint
for corrective fitting where provenance permits. Then repeat actor-only
coverage, movement ablation and match checks. The final collector with actual
partner identity swaps, broad physical audit, final match acceptance and the
verified accepted playable scene remain unfinished.

### Varied incoming-ball curriculum — 2026-09-06 19:06 UTC

The preceding turn was progress, not a blocker. Added the external collector
`scripts/player-incoming-curriculum.cs`. It uses the existing public rule setup
and a real serve drop to establish observations, then explicitly injects one
initial ball state. It varies lane, height, depth, velocity, and both candidate
players' initial positions. Opponents stand still during this skill stage.
The ball then follows the existing simulation. Each candidate still uses the
20 Hz / 25 ms decision path; teacher action replacement is confined to the
recorded training mixture. No exported actor receives an intercept or scripted
foot target. Each run retains a collector snapshot and hash, runtime/model
hashes, initial states, executed-action identity, teacher labels and physical
contacts. It records zero completed games and no game winners.

The loader now validates candidate-only fixture ownership, timing, snapshot
integrity and the distinction from completed matches. Four added tests pass;
the Python player suite now has 48 passing tests. Runtime source stays
`1459f288708b9e580d0bef43dbda99a130e847fd263b415e8d3dd271fcd9b82e`.
All 63 baseline files remain unchanged.

Smoke report `incoming-20260906-190449.json`: eight development fixtures at seed
1120900; 568 validated decisions; 7/8 real contacts and 4/8 legal landings.
These were privileged-teacher actions, not learned performance. A 640-fixture
training run started at 19:06:32 UTC, seed 1015000, teacher probability 0.5,
with parent actor `imitation-20260906-185656/actor.json`. Report path:
`incoming-20260906-190632.json`. Do not start another Editor job while its
`TickIncoming` callback is active. Separate development data and actor-only
coverage/match checks will follow. Final seeds remain unused.

The training fixture batch completed 640 cases in 150.7 seconds: 36,490
decisions, 18,205 teacher actions, 18,285 actor actions, 302 physical contacts,
141 legal landings. Separate development `incoming-20260906-190937.json`
completed 128 cases: 7,096 decisions, 59 contacts and 32 landings. These are
mixed-control training outcomes, not actor-only acceptance evidence.

Fine-tuned the saved corrective actor on these 36,490 incoming decisions plus
the earlier 26,214 corrective match decisions. Settings: 120 epochs, hidden
256, batch 1024, learning rate 0.0003, neutral-paddle probability 0.8. Fitting
took 65.5 seconds. New model: `imitation-20260906-191112/actor.json`, hash
`216a02d9f007a45cb127f90aaaef82a72ccae21e87d9149ea6354e1f2b2fb8be`.
Its parent is `88858b3d81eabe52ac80b4f22d30dbd6817effd4eb6af4ab8cb9d1fd6c074061`.
Unity parity passed.

Actor-only coverage `coverage-20260906-191237.json` completed all 48 cases.
The learned actor made 9/16 legal contacts and 5/16 legal landings. Its disabled-
movement ablation made 0/16 contacts and 0/16 landings. The privileged teacher
remains at 12/16 and 10/16. This is a real development coverage improvement,
not final match acceptance. A 64-requested-rally actor-only match check started
at 19:12:54 UTC, development seed 1122000, against the frozen sampled baseline.
No model has been promoted or installed.

### Competitive updates and final runner — 2026-09-06 19:28 UTC

The 19:12 development match finished: `competition-20260906-191254.json`.
The incoming-curriculum actor made 106 legal non-serve hits in 64 rallies,
but lost all four games: 2–11, 0–11, 0–11, 0–11 in candidate-relative order.
There were 32 failed live paddle guard steps. This is not accepted physical
or match performance. Broad phase-specific motor tracing remains necessary.

Completed two local, team-game-win PPO updates against the saved older actor
`imitation-20260906-185656/actor.json`. Driver record:
`training-loop-20260906-191821/progress.json`. The first training batch used
seed 1016000: 160 rallies, 18,288 decisions, five completed games, one candidate
win, 83.6 seconds. The second used seed 1017000: 135 rallies, 15,156 decisions,
five completed games, one candidate win, 68.6 seconds. These wins belong to
stochastic training collection, not a held-out comparison.

Saved checkpoints: `ppo-20260906-191950/actor.json` and
`ppo-20260906-192151/actor.json`. Both passed Unity output parity under runtime
source `1459f288708b9e580d0bef43dbda99a130e847fd263b415e8d3dd271fcd9b82e`.
The second actor hash is
`d64e735ff448981e10a1baace5dd5bca80dd73764d0c19899e03908be3683b0b`.
Development reports `competition-20260906-191952.json` and
`competition-20260906-192153.json` still lost every baseline game. They made
74 returns in 44 rallies and 56 returns in 36 rallies, respectively. No
checkpoint was installed or promoted.

Added `scripts/player-final-evaluate.cs`. It defaults to an eight-game
development rehearsal. Final mode requires the frozen 80-game schedule.
It reserves the full seed block before play, rejects reuse of a reserved
final block, retains incomplete games, emits no training data, and saves
the collector source, schedule and terminal report hashes. It checks current
actor provenance and parity before a final run. Final seeds remain unused.

Added optional within-team identity maps to `PlayerDecisionLoop` and
`PlayerMatch`. Default maps preserve the old random streams. The runner
constructs separate policy instances by identity, assigns them to seats, and
moves each private RNG stream with its identity. Observations still belong
to the current body. Shared deterministic policy weights can produce identical
behaviour after a swap; this is explicitly disclosed and is not a substitute
for a different-partner-model comparison. This runtime change requires a new
source-tracked training update before final acceptance.

The final verifier now checks real identity maps, RNG seeds, observation
ownership, decision latency, saved schedule, collector snapshot and terminal
report integrity. Seven new Python checks pass, for 55 total Python tests.
All 63 frozen baseline files remain unchanged. Unity runtime regression tests
and a development-only runner rehearsal are the next verification steps.

Verification completed under new runtime source
`d726ace1efb07fb3c2530750e5a66ae31112d5c70955f3149045e3f1c7e2fe9b`:
39/39 runtime tests passed in 64.21 seconds, and 15/15 Editor tests passed in
0.8 seconds. Reports: `identity-runtime-green-20260906-1928.json` and
`identity-editor-green-20260906-1930.json`. The Python suite has 55 passing
tests. These focused tests do not prove all match states respect motor limits.

The new runner completed its eight-game development rehearsal at
`development-evaluation-20260906-193022/`. Seeds 1126000–1126007 exercised
both baseline modes, both court ends and actual within-team identity maps.
The saved PPO checkpoint was explicitly recorded as historical after the
identity API change; it was not relabelled as current-source training.
All eight real collector/schedule/report artifacts and their player identity,
RNG, observation ownership and latency records passed the new validator.
The baseline acceptance function correctly rejected them as development data.
The callback was absent at completion. No final seed was used.

The rehearsal lost all eight games. Phase-specific measurements found 75
failed candidate guard steps during ServeFlight, ReturnFlight or Rally. Peak
candidate paddle acceleration was 1052.532 m/s² in ServeFlight, far above the
100 m/s² configured motor limit. Separate Rally failures also exist, so this
cannot be attributed only to the unchanged serve controller. The runner saves
uncapped violation counts and maxima, plus capped controller/phase-specific
failure states. Baseline and serve violations are recorded separately.

Next work: correct the independent paddle motor's pre-step feasibility and
serve-to-live transition, using these retained development states. The current
soft-braking fallback can leave a later step without a feasible combination
of hand reach and acceleration. Do not conceal this with a larger limit or
post-contact ball adjustment. Keep the frozen baseline unchanged. Then rerun
low-contact, movement and full-match physical checks before larger training.
New source-tracked training, older/mixed-partner comparisons, final 80-game
acceptance and the accepted playable scene remain unfinished. The goal is
active, with no external blocker and no model promotion.

### Motor feasibility experiments — 2026-09-06 19:42 UTC

Tested a stopping-envelope motor that reserved a straight braking path inside
the hand-reach sphere, plus a guard on the independent scripted serve. The
saved doubles baseline was not changed. The first proposal failed 5/39 runtime
tests (`stopping-envelope-red-20260906-1939.json`): short returns and a 620.83
m/s² spike at a numerical reach boundary. Its low-contact diagnostic is
`low-contact-20260906-193917.json`.

The second proposal corrected that boundary tolerance and used an 80 m/s²
braking reserve within the unchanged 100 m/s² motor limit. In
`low-contact-20260906-194035.json`, all 16 contacts stayed below 100.011 m/s²,
but none landed across the net. This is not a useful substitute for the goal.
Full development run `development-evaluation-20260906-194056/` then failed
in group 2 with a non-finite player observation. The retained motor traces
show invalid paddle velocity during a serve. Both failed motor sources were
saved in `motor-before-20260906-1937/stopping-envelope-v1.cs` and `v2.cs`.

Removed the rejected stopping-envelope implementation. Restored the original
`PlayerPaddleMotor.cs` from the exact pre-experiment source snapshot, using a
patch. The independent `PlayerMatch.StepServe` guard is being tested alone.
It keeps the explicit scripted drop-serve plan, constrains its foot and paddle
commands, and does not change the saved baseline or the ball after contact.
The evaluation runner now records `guardFeasible: null` for controllers whose
guard state it does not directly observe; it does not imply a successful guard.
No training or final evaluation was run on either rejected motor proposal.

The isolated serve guard completed all eight development comparison games in
`development-evaluation-20260906-194451/` (145.8 seconds). Runtime source:
`8165da15f78d31fdf18edba0603b66a9f8106ce181f07b7c7226348d9f12194c`.

### Exact moving-body motor replay — 2026-09-06 20:01 UTC

Tested posture-first ordering for the relaxed paddle solve. Low contact stayed
at 16 contacts / 8 legal landings, but the eight-game comparison had 29 live
guard failures instead of 18 (`development-evaluation-20260906-195340/`).
That ordering was rejected and saved as
`motor-before-20260906-1937/posture-first-rejected.cs`.

Added `scripts/player-paddle-command-trace.cs` and
`scripts/player-paddle-command-replay.cs`. The trace retains 120 raw scripted
paddle commands before a live-rally failure, with initial body state and the
recorded partner trajectory. It does not supply training data or control a
visible scene. The replay restores only diagnostic initial state and partner
motion; it then runs the actual motor on every recorded command.

Trace `paddle-commands-20260906-195710.json` captured player 1, rally 15,
tick 2380, seed 1126000. Under the matching source, reconstruction had exactly
zero position and velocity error (`paddle-replay-20260906-195844.json`). It
reproduced the 187.820 m/s² spike at the last frame. Trace hash:
`1c2ab9f6b0f6be2074fcc0104deab73e0ea255996c31996c1180c182caafd90e`.

The recorded crouch stops at its target while paddle velocity still points
outward relative to the translating body. The old reserve relied on continued
crouch motion to offset that outward velocity. Added a second radial braking
constraint that assumes crouch and grip motion can stop. It also applies in
the relaxed fallback. Existing speed, acceleration and reach limits remain
unchanged. Current proposed source:
`13198f1b11508b27c5d6709a76ba52300b3a0a68d38e24b5f82fc07cbf3c6e4c`.

The same command window now has zero infeasible steps, maximum acceleration
90.120 m/s² and reach 0.600536 m (`paddle-replay-20260906-200005.json`).
Low-contact report `low-contact-20260906-200010.json` preserves all 16 contacts
and 8 legal landings, with maximum acceleration 100.0119 m/s² and no guard
failures. Eight-game comparison `development-evaluation-20260906-200031/`
is running. No training, promotion or final seeds were used for this change.
It used the same checkpoint and development seed schedule as the earlier
rehearsal. The candidate had zero measured serve motor-limit violations;
peak serve paddle acceleration was 100.0131 m/s², within the 100.1 numerical
test tolerance. Live guard failures fell from 75 to 18. Peak live paddle
acceleration remains 608.978 m/s², so broad motor acceptance still fails.
The candidate made 268 legal returns in 152 rallies and lost all eight games.
This is a physical refinement, not an accepted playing policy.

The isolated serve change passed 38/39 original runtime tests. The one failure
was a swing-commitment test that relied on a stationary actor reaching the old
serve trajectory. Replaced that test's setup with the existing explicit
incoming-ball rule fixture. Its commitment, movement and cancellation
assertions are unchanged. Added twelve separate serve/release regressions:
all four service seats, each at central and extreme prescribed serve jitter.
They require real legal paddle contact and check speed, acceleration, angular
speed and reach through the handoff to actor control. This does not relax the
full-match evaluation or the existing low-contact landing assertions.

Expanded runtime regression result: 51/51 passed in 64.97 seconds, saved as
`guarded-serve-runtime-green-20260906-1951.json`. The Python suite remains
55/55. All eight real comparison report/schedule/snapshot artifacts and their
identity traces validated. The isolated serve guard is retained; the rejected
stopping-envelope motor is not in the runtime. Next work is the remaining
live-rally guard failure, especially moving-body reach and posture transitions.
Do not resume large training until those failure states have a verified motor
correction that preserves useful physical returns. Final acceptance and the
trained playable scene remain incomplete. No external blocker is present.

The final Editor contract run also passed 15/15 in 0.8 seconds, saved as
`guarded-serve-editor-green-20260906-1951.json`. Runtime source remains
`8165da15f78d31fdf18edba0603b66a9f8106ce181f07b7c7226348d9f12194c`.

### Posture-stop constraint follow-up — 2026-09-06 20:12 UTC

The strict posture-stop proposal did not pass full matches. Report
`development-evaluation-20260906-200031/` has 281 live guard failures,
15 measured acceleration violations, and a peak of 1394.844 m/s².
It has 273 returns in 135 rallies across eight games. The exact command
replay alone was not sufficient evidence. The rejected motor remains in
`motor-before-20260906-1937/posture-stop-strict.cs`.

The current proposal applies the posture-stop reserve only in the preferred
solve. The hard fallback retains the original speed, acceleration and reach
constraints. It does not yet have full-match acceptance.

Added a permanent 120-command regression fixture and replay tests on both
court ends. Both tests pass. The full runtime result was 52/53 passed,
retained as `posture-stop-runtime-red-20260906-2007.json`. The sampled frozen
baseline adapter comparison failed at tick 2126 with 0.054845 m ball error.
Its cause is under investigation. Do not relax its tolerance or change the
frozen baseline to hide this failure. No candidate was installed, no further
training was run, and final seeds remain unused.

### Retraction fallback experiment — 2026-09-06 20:22 UTC

The baseline repeat passed both eight-rally modes without a code change.
Result: `posture-stop-baseline-repeat-green-20260906-2013.json` (2/2).
A separate instrumented sampled comparison also passed all 19,016 steps
and eight rallies, with no actor decisions or clearance steps:
`baseline-parity-20260906-201444.json`. The original isolated test failure
remains unexplained. The baseline and tolerance have not been changed.
The first synchronous diagnostic exceeded the CLI request timeout and did
not save a result. The retained probe uses bounded Editor update callbacks.

The soft-only posture reserve still failed broad motion acceptance:
`development-evaluation-20260906-201529/`, source
`4ce9d9f8b5577f8c8814cf9e09fec04d36c3ff214f87d8f8242303a842dae7c4`.
Eight games completed in 145.34 seconds, with 135 rallies and 13 live guard
failures. Peak live paddle acceleration was 1393.752 m/s². Serve violations
were zero. All games were losses. Its source snapshot is retained as
`motor-before-20260906-1937/posture-stop-soft.cs`.

Trace `paddle-commands-20260906-201812.json` captured a ServeFlight failure
for player 0 at rally 9, tick 588. Hash:
`57b5a0ba19a4737b25e79bff1ecc3ae082a85bba51e40f202fd6d3ea19ff1a89`.
Matching-source replay `paddle-replay-20260906-201849.json` had zero position
and velocity error and reproduced the 485.713 m/s² spike.

The old fallback continued toward the shot target when the preferred braking
reserve was infeasible. It could therefore increase outward velocity before
the hard reach limit. The new proposal changes only that fallback objective:
retract the hand at a requested 2 m/s relative to its moving shoulder/grip
frame, through the existing speed, acceleration and reach constraints.
No foot commands or frozen body code change. Current proposed source:
`eee4ff1f50b86766bd12415a9ee8dc7e62ff46e06aea98a3c83c5323d7336445`.

The captured replay now passes all physical bounds, with zero infeasible
steps, 100.0096 m/s² maximum acceleration and 0.611656 m maximum reach:
`paddle-replay-20260906-202033.json`. A full eight-game development comparison
is running in `development-evaluation-20260906-202058/`. Do not infer broad
acceptance from the single replay. All 55 Python tests pass and all 63 frozen
baseline files are unchanged. No model promotion or final evaluation occurred.

### Radial-priority fallback — 2026-09-06 20:27 UTC

The 2 m/s retraction fallback completed eight development games in 149.57
seconds. It made 282 candidate legal returns in 139 rallies and lost all
eight games. Live guard failures fell to nine, with peak acceleration
648.456 m/s². There were no candidate serve violations. This remains failed
physical acceptance, not a promoted policy. Report:
`development-evaluation-20260906-202058/`.

Seed 1126001 yielded another exact 120-command failure:
`paddle-commands-20260906-202402.json`, player 1, rally 4, tick 1114.
Matching-source replay `paddle-replay-20260906-202447.json` had zero position
and velocity error and reproduced 259.801 m/s². Trace hash:
`4f4f9299f17207ebca0a1d573fc67bf1f02b300c7f15f3c7dbfa57198a471ac6`.

The retraction objective spent acceleration on reducing tangential speed.
The current proposal instead requests maximum radial braking in the fallback,
then projects that request onto the unchanged hard motor constraints. This
prioritizes outward stopping while the curved hand path needs centripetal
acceleration. The previous proposal is retained as
`motor-before-20260906-1937/retract-fallback-v1.cs`.
Current source:
`3594ac62bdd1fd5785f8ed0f66d12387665fcc11261611cc6c3aec460930c20b`.

The curved replay now passes with 100.006 m/s² maximum acceleration and
0.606936 m reach, with no infeasible steps:
`paddle-replay-20260906-202515.json`. Low-contact report
`low-contact-20260906-202527.json` still has 16 contacts, eight legal landings,
zero infeasible steps, and 100.0119 m/s² maximum acceleration.

Added immutable low-recovery and curved-recovery fixtures through the Unity
asset database. The runtime suite now includes six replay cases: each of
the three recorded windows on both court ends. Every case checks the original
speed, acceleration, angular-speed and reach limits. It also checks that the
paddle guard does not change the recorded foot motion. The 57-case runtime
suite is running. Full-match acceptance of radial-priority braking is pending.

### Stopped-posture curvature reserve — 2026-09-06 20:34 UTC

Radial-priority braking passed all 57 runtime tests in 65.29 seconds and all
15 Editor tests in 0.81 seconds. Reports:
`radial-braking-runtime-green-20260906-2028.json` and
`radial-braking-editor-green-20260906-2028.json`.
However, `development-evaluation-20260906-202857/` still had ten live guard
failures in eight games, with peak acceleration 560.549 m/s². The candidate
made 271 legal returns in 137 rallies and lost all eight games. Unit tests
did not establish full-match acceptance. This version is retained as
`motor-before-20260906-1937/radial-fallback-v1.cs`.

Trace `paddle-commands-20260906-203139.json` captured the next player-1
failure at rally 4, tick 1118. Hash:
`1d3cad07859c2522ae22f34168580160036d1bfc2ab1640d8da6791dbb97a980`.
Replay `paddle-replay-20260906-203222.json` matched positions and velocities
exactly and reproduced 343.017 m/s². Fast tangential paddle motion relative
to the translating body remained possible when crouch and grip motion partly
cancelled it in the existing moving-hand-frame speed check.

The current proposal also limits the tangential component relative to body
translation to 6 m/s, in every solver trial. It does not limit inward radial
speed to 6 m/s or change the 12 m/s world-space limit. This reserves curvature
acceleration even when crouch and grip motion stop. The projection and final
validation both enforce the new constraint. Current source:
`fdd640a2b8772336adf9d69b2717d4e2b0099cd096005b53f971ab4cc005f419`.

Replay `paddle-replay-20260906-203247.json` has no infeasible steps,
100.005 m/s² maximum acceleration, and 0.600482 m maximum reach. Low-contact
report `low-contact-20260906-203252.json` preserves 16 contacts and eight
legal landings, with zero infeasible steps and 100.0119 m/s² maximum
acceleration. Full development comparison
`development-evaluation-20260906-203310/` is running. No source was relabelled
as a trained model, and no final seeds or model promotion were used.

### Reach-dependent curvature reserve — 2026-09-06 20:43 UTC

The fixed stopped-posture tangential cap completed eight development games
without any measured candidate physical-limit violation, across all phases.
It had 14 guard failures in one inner-reach swing, although those steps stayed
within the actual speed, acceleration and reach limits. The candidate made
207 legal returns in 136 rallies and lost all games. Report:
`development-evaluation-20260906-203310/`.

Captured that reserve failure against the sampled baseline, seed 1126005:
`paddle-commands-20260906-203955.json`, player 0, rally 16, tick 3287.
Hash: `b3bb4363ad062cfbacb500a7a9d4f1bf5465589f7b95e09fb7b5c54e3f374013`.
Matching replay `paddle-replay-20260906-204056.json` had zero position and
velocity error. The failing step had reach 0.343 m and acceleration
99.998 m/s². The fixed 6 m/s cap constrained an inward pass too far from the
reach boundary. Retained source: `motor-before-20260906-1937/stopped-tangent-v1.cs`.

The current proposal bounds radius times tangential speed at 3.6 m²/s.
Straight relative hand travel preserves this quantity. Thus 6 m/s at 0.60 m
reach does not require the same speed cap close to the shoulder. The limit
uses the proposed next posture and body translation, and it applies in both
projection and validation. World-space speed, acceleration and hard reach
limits are unchanged. The earlier stopping-envelope experiments were
inspected but not reinstated. Current proposed source:
`85ba36035c9e845fee26f7d6971c16eb602b582ea103a24df4f5e46b48de0b35`.

Replay `paddle-replay-20260906-204134.json` passes, with no infeasible steps,
100.0055 m/s² maximum acceleration and 9.242 m/s maximum paddle speed.
Full-match check `development-evaluation-20260906-204149/` is running.
This remains a development motor proposal, not an accepted playing policy.

### Inner-reach braking recovery — 2026-09-06 20:50 UTC

The reach-dependent curvature proposal was not accepted. Its eight-game
report, `development-evaluation-20260906-204149/`, had two live acceleration
and guard failures for player 2 in group 6, with peak acceleration
747.641 m/s². It made 279 candidate legal returns in 159 rallies, with eight
losses. Retained source:
`motor-before-20260906-1937/reach-dependent-tangent-v1.cs`.

Restored the fixed stopped-posture 6 m/s tangential reserve that had no
measured physical-limit violations in its eight-game check. Added a third
solver stage only when the current hand is within 0.45 m of the shoulder.
If the preferred and radial-braking stages cannot satisfy their reserve,
this stage requests zero velocity relative to body translation. It still
projects and validates the original world-speed, acceleration and reach
limits. It brakes rather than continuing toward the shot target. Outside
that inner region, the fixed tangential reserve remains required.

This separates an infeasible conservative reserve from an infeasible hard
physical step, without changing test tolerances or declaring an unchecked
legacy step feasible. Current source:
`4b1ddba0940486e60a11c0fb9ac3eb6be2105846a246a8b73918c437bfe716e9`.

### New-seed motor check and training restart — 2026-09-06 21:01 UTC

The separate seed block 1127000–1127007 also passed every candidate motor
check in all eight games, including zero infeasible guard steps:
`development-evaluation-20260906-205450/`. It had 227 candidate legal returns
in 141 rallies. Both controller modes, both court ends, and both identity
assignments were included. All games were losses. All schedule, snapshot,
completion, report-hash and player-identity checks passed for both runs.

Thus this motor version has 61 passing runtime tests and 16 completed
development games with zero candidate motor violations or infeasible steps.
It is retained for the next training stage. This is not calibration, proof
of global safety, competitive improvement, or final goal acceptance.

Added explicit `--allow-historical-initial` support to the imitation trainer.
The default still rejects older-runtime parents. Opt-in preserves the parent
file, exact initial weights, parent source hash and parent actor hash, while
requiring matching physics, contact, protocol and frozen-baseline identities.
Training data must still pass current-runtime source checks. A child is
exported only after real optimizer updates. Trainer and runtime source
snapshots are retained in each new imitation folder. All 58 Python tests pass.

Started fresh current-runtime incoming-ball teacher data:
`incoming-20260906-210016.json`, training seed 1020000, 640 fixtures, teacher
probability 1. These are injected skill fixtures, not completed games or
learned-policy results. The next step is a separate development dataset and
an explicitly recorded corrective fit from the saved coverage-capable actor.
No accepted scene model has been installed, and final seeds remain unused.

### Current-runtime policy fits — 2026-09-06 21:15 UTC

The incoming training collection completed 640 fixtures and 42,466 rows in
151.63 seconds, with 554 teacher legal contacts and 357 legal landings.
The separate development collection, `incoming-20260906-210348.json`, used
seed 1128000 and completed 128 fixtures and 8,956 rows in 32.47 seconds,
with 108 teacher contacts and 76 legal landings. Both collections had zero
infeasible motor steps. Maximum paddle accelerations were 100.0209 and
100.0136 m/s². These remain injected teacher skill results, not policy matches.

Match collection `curriculum-20260906-210445.json` used training seed
1021000, 128 rallies, the historical coverage actor, teacher probability 0.5,
all nine shot choices, and a frozen sampled baseline opponent. It retained
35,266 labels from 17,730 teacher and 17,536 actor decisions, six completed
games, and 271 learner-side returns in 173.19 seconds. It had zero infeasible
steps and candidate peak acceleration 100.0323 m/s². Mixture results are not
learned-policy match results. All three datasets passed source, ownership,
split and data-integrity checks.

First fit: `imitation-20260906-210721/actor.json`, 80 epochs on incoming data,
hidden width 256, batch 1024, learning rate 0.0003, 22.48 seconds. It used
the explicit historical-parent option with the unchanged 191112 coverage
checkpoint. Actor hash:
`d287a6c891db7b0b97aa3fa7b069044f0e50ab283ece5d0f510fed0fd77d91d9`.
Unity/Python parity passed 32 cases, maximum error 0.0000038147.
Coverage `coverage-20260906-210928.json`: learned 9/16 legal contacts and
7/16 legal landings; movement disabled 0/16; teacher 12/16 and 10/16.

Second fit: `imitation-20260906-210920/actor.json`, 40 epochs on all 77,732
current-runtime rows, initialized from the first fit, learning rate 0.0002,
21.05 seconds. Actor hash:
`cede769eec2cae432fe66178074840d9c450efe9c17677d9131fb9c6acad24c2`.
Unity/Python parity passed 32 cases, maximum error 0.0000019073.
Coverage `coverage-20260906-211038.json`: learned 8/16 contacts and 7/16
landings; movement disabled 0/16; teacher 12/16 and 10/16. Coverage had zero
infeasible motor steps. The second fit is not automatically better.

Both models record current runtime source
`4b1ddba0940486e60a11c0fb9ac3eb6be2105846a246a8b73918c437bfe716e9`,
actual optimizer updates, parent hashes, and source snapshots. Neither parent
file was relabelled or overwritten. These are supervised warm starts, not
new competitive-RL results. The second fit is now being evaluated without
teacher control on development seeds starting at 1129000. Final seeds and
scene-model promotion remain unused.

### Competitive training exposed a serve failure — 2026-09-06 21:22 UTC

The current-source second-fit match check,
`development-evaluation-20260906-211436/`, completed eight games and 134
rallies with 154 candidate legal returns and zero candidate motor violations.
All games were losses. Artifact and identity checks passed.

The two-update competitive driver then stopped before its first PPO update:
`training-loop-20260906-211831/progress.json`. Candidate was the second fit;
opponent was the first fit, both sampled, using team game-win reward.
Training collection `competition-20260906-211832.json` reached its unchanged
300-rally safety cap with score 0–0. All 300 rallies had one serve contact,
no legal returns, and fault `WrongSide`. It had zero infeasible motor steps
and maximum paddle acceleration 100.0357 m/s². The failed collection and
12,602 rows are retained. They were not used for a PPO update.

This is a serve delivery defect, not evidence that the two policies played
300 full rallies without scoring. The constrained scripted serve can make
legal paddle contact but does not deliver a legal first bounce. The existing
serve test checked contact and motor bounds, but not the required landing.
This also limits interpretation of earlier baseline losses: baseline-owned
serves use the preserved original controller, while candidate serves use the
constrained serve. Do not attribute all those losses to policy strength.

Extended all twelve service-seat/jitter tests to require a legal first bounce
in the opposite service court, while retaining all motor assertions. Correct
the scripted serve end to end before more competitive training. Do not raise
the game safety cap, alter scoring, use the incomplete game for PPO, or relax
the frozen baseline. No external blocker is present.

### Serve delivery repair in validation — 2026-09-06 21:36 UTC

The strengthened landing tests failed all 12 original cases. Saved result:
`serve-landing-red-20260906-2126.json`. The default diagnostic,
`serve-delivery-20260906-213216.json`, confirmed low delivered ball speed.
All first bounces remained on the serving side. A 48-case pitch, timing,
and speed residual sweep also produced no legal serve. The motor constraints
were not relaxed.

A first forward-step experiment produced only one legal default serve.
Its source snapshot and diagnostics are retained. The second experiment
starts forward body movement 0.20 seconds before planned contact. The
requested foot target is 6.50 metres from the net, but this is not a teleport
or a permitted contact position. Body acceleration and speed remain bounded;
the existing rules check the actual feet at contact. Actor movement resumes
after contact. This is part of the disclosed scripted serve, not live-rally
foot assistance. The frozen baseline and ball response are unchanged.

`serve-delivery-20260906-213526.json` passed all 12 default server/jitter
cases. First bounces were 3.07–3.76 metres into the opposite court. There
were no infeasible motor steps, and peak paddle acceleration was 100.0134
m/s², below the unchanged 100.1 test tolerance. The additional residual
sweep passed 36 of 48 intentionally varied cases; it is retained as a
diagnostic, not a claim that every altered serve parameter is valid.

Added the 12 opposite-service-position cases to the permanent regression
test. Full runtime, Editor, and Python checks must pass before training.
Existing models retain their original source hashes. No model is promoted.

The repair passed all 73 runtime tests, including all 24 serve cases, in
69.03 seconds. Result: `serve-step-runtime-green-20260906-2139.json`.
All 15 Editor tests passed in 0.8 seconds:
`serve-step-editor-green-20260906-2140.json`. All 58 Python tests passed.
The baseline manifest check confirmed all 63 files are unchanged.
Retained runtime source:
`7a04ba2e95066440b9c5f0bb1d2c3454dd04e5c172028de8921194d5f16ad9d2`.

Restarted two local competitive updates from the second imitation fit,
against the unchanged first imitation fit. Requested 160 rallies per update,
starting at training seed 1024000; development seeds start at 1134000.
This uses the existing game-win objective and complete-game checks. Both
parents are explicitly historical under the serve repair. Only actual new
optimizer updates can create a current-source child. Final seeds remain
unused, and the playable scene has no promoted candidate.

### Two competitive updates and return curriculum — 2026-09-06 21:47 UTC

The driver `training-loop-20260906-214002/progress.json` completed both
iterations. Training reports `competition-20260906-214003.json` and
`competition-20260906-214154.json` contain 161 and 163 rallies, respectively,
with 11 complete games each. They contain 14,408 and 14,068 training rows.
Both collections had zero infeasible motor steps. Training took 69.16 and
64.72 seconds. Candidate training wins were 9/11 and 8/11, against the
saved older imitation policy. These are training outcomes, not held-out
improvement evidence. Most rallies still had no legal return.

Saved children:
- `ppo-20260906-214121/actor.json`, SHA-256
  `394be1a5d21ad05f8a3121416576b787b5ef895d9dabf65ad99ca1d4cd80f98a`;
- `ppo-20260906-214311/actor.json`, SHA-256
  `0eb4cef42472d2eb581e3a98ea710026164f9a9f5f518b13c0b7d880e20f6d6f`.

Both passed 32-case Unity/Python parity, maximum error 0.0000038147.
Each then lost both sampled-baseline development games. The second child
scored one point across its two games. All four training/development reports
passed the new candidate motor gate. No candidate is accepted or promoted.

The Python PPO loader now rejects missing, non-finite, or out-of-limit
candidate motor measurements and any infeasible independent paddle steps
before optimization. Frozen-opponent measurements remain separate. Three
new regression tests cover both candidate seats/ends, opponent separation,
and invalid measurements. All 61 Python tests passed.

Started a 256-rally four-teacher curriculum at training seed 1026000, with
all nine shot choices and the corrected physical serve. The first 59 rallies
contained 595 legal returns. These are privileged training-only controllers,
not learned-policy results. A new paired older-partner development protocol
and external runner are prepared; they still need executable verification.

### Current-serve four-player dataset — 2026-09-06 21:56 UTC

`curriculum-20260906-214420.json` completed 256 rallies with 302,948 separate
player labels and 2,402 legal returns. Collection took 646.15 seconds. It
finished eight complete games and retained one partial game at the requested
curriculum limit. This is allowed for imitation labels, not terminal-reward
PPO. Per-seat legal returns were 409, 786, 300, and 907. All eight completed
teacher games were near-team wins; do not treat that teaching-controller
asymmetry as learned-policy or balanced-match evidence.

The dataset had zero infeasible motor steps and maximum paddle acceleration
100.0342 m/s². Runtime source remains `7a04ba2e95066440b9c5f0bb1d2c3454dd04e5c172028de8921194d5f16ad9d2`.
Started a separate 64-rally development-label collection at seed 1136000.

The four-player label loader now checks separate, simultaneous decisions
for all four players, game ownership, timing, and decision counts. Three
tests reject duplicates, missing players, and wrong game/team/tick values.
There are now 68 passing Python tests, including the paired partner checker.
The mixed-partner runner itself is not yet executed. No accepted model or
final-seed evaluation exists.

The separate development dataset, `curriculum-20260906-215536.json`,
completed 64 rallies with 66,980 labels and 526 legal returns in 145.22
seconds. It completed one game and retained the requested-limit partial
game. Both training and development datasets passed the new four-player
ownership checks and all-player motor checks. Development peak paddle
acceleration was 100.0289 m/s², with zero infeasible steps.

Started a 40-epoch, 256-wide corrective fit, batch 1024, learning rate
0.0002, initialized from the unchanged first imitation fit (210721), with
explicit historical-parent consent in the command. All fit data is from
the current serve runtime. Validation labels do not enter gradient updates.
The prepared mixed-partner runner compiled and started successfully on the
saved current-source PPO checkpoint 214311. Its paired 16-game rehearsal is
`mixed-partner-20260906-215903.json`; executable result verification remains
pending. Reserved final seeds are still unused.

### Four-teacher-only fit rejected — 2026-09-06 22:07 UTC

The fit `imitation-20260906-215930/actor.json` completed 40 epochs and
11,840 optimizer updates in 79.02 seconds. Actor SHA-256:
`4984b9426a1754ca071a42f46187fdea01289da29bddb31a8e7e9af53cd95245`.
It passed 32-case Unity parity with maximum error 0.0000019073. Prediction
loss improved, but play regressed. Coverage `coverage-20260906-220135.json`
had only 2/16 learned contacts and 0/16 legal landings, compared with the
parent's earlier 9/16 and 7/16. Movement-disabled control stayed at zero;
teacher control remained 12/16 and 10/16. There were no infeasible steps.

`development-evaluation-20260906-220230/` completed all eight scheduled
games in 38.81 seconds. All were losses. The candidate made one legal
return across 92 rallies and had no infeasible motor steps. This fit is
rejected for promotion. Low teaching-state prediction error did not transfer
to the incoming-ball or baseline-opponent state distributions.

The mixed-partner rehearsal on the earlier PPO policy completed all 16
games and passed the independent artifact, schedule, ownership, and motor
checker. Report: `mixed-partner-20260906-215903.json`, SHA-256
`10b768ed8b0a20178ec2f007d256393379a725ff558c6e11e91cecdcbad43c3d`.
Both partner conditions won 7/8 against the older policy, but made only
seven combined team legal returns per condition. These mostly serve-ended
games do not establish useful sustained play or final acceptance.

Started new current-source incoming data: 640 training fixtures, seed
1027000, `incoming-20260906-220500.json`. Rebuild the training mixture with
incoming, baseline-opponent, and four-player states. The imitation trainer
now has explicit equal-source training sampling and multiple development
sources with equal-source checkpoint selection. It records sampled counts
and per-source metrics. Duplicate datasets and configuration mismatches
are rejected. Three sampler/aggregation tests pass; total Python tests: 71.
The new balanced fit has not yet been executed. Runtime source and frozen
baseline are unchanged. The goal is active; no external blocker exists.

### Balanced rehearsal restores coverage — 2026-09-06 22:14 UTC

New incoming data passed source, ownership and candidate motor checks:
- training `incoming-20260906-220500.json`: 640 fixtures, 42,758 rows,
  143.42 seconds, no infeasible steps;
- development `incoming-20260906-220827.json`: 128 fixtures, 8,694 rows,
  28.58 seconds, no infeasible steps.

The first balanced fit combines incoming data with the current-serve
four-player data, with equal-source sampling and equal-source validation
selection. Parent remains the unchanged first imitation fit (210721), with
explicit historical initialization. It completed 40 epochs in about 83
seconds and saved `imitation-20260906-220959/actor.json`, SHA-256
`f567c151751e835f0b8a3e5d6a9e01af5b216dc84915267e3500043f86ad61de`.
The recorded sampled counts confirm approximately equal mass per source.
Unity parity passed all 32 cases, maximum error 0.0000038147.

Coverage `coverage-20260906-221256.json`: learned 12/16 contacts and 9/16
legal landings; movement disabled 0/16; privileged teacher 12/16 and 10/16.
All cases had zero infeasible motor steps. This is the best measured
coverage so far, but not baseline match acceptance. Preserve this checkpoint.

The mixed teacher/learner baseline-opponent training collection,
`curriculum-20260906-220947.json`, completed 128 rallies, 26,718 labels,
and 181 learner-side returns in 137.01 seconds. It completed seven games
and retained the requested-limit partial game. Teacher probability was
0.5; the learner was the unchanged PPO 214311, and all nine shot choices
were available. It passed ownership and candidate motor checks with zero
infeasible steps. A separate 32-rally validation collection at seed 1139000
is running. Add these data as a third balanced source, retain the two-source
checkpoint, then measure match performance.

### Three-source fit and paired match check — 2026-09-06 22:20 UTC

The baseline-mixture validation set `curriculum-20260906-221358.json`
completed 32 rallies, 6,154 labels, and 37 learner-side returns in 28.20
seconds. It passed source, ownership and candidate motor checks.

The three-source fit uses incoming, four-player, and baseline-mixture data
with equal sampling mass and equal-source validation selection. It starts
from the preserved two-source checkpoint 220959. Learning rate is 0.0001;
40 epochs, 256-wide model, batch 1024. It used 372,424 training labels and
81,828 validation labels, with 14,560 actual optimizer updates in 103.52
seconds. Saved actor `imitation-20260906-221506/actor.json`, SHA-256
`6f957e3d91e6d98c8243acf054fbf262f1e48b3cdc4ac43f1f0853a2333ed579`.
Unity parity passed 32 cases, maximum error 0.0000038147.

Coverage `coverage-20260906-221804.json`: learned 12/16 contacts and
10/16 legal landings; movement disabled 0/16; teaching controller 12/16
and 10/16. No infeasible motor steps occurred. This matches the teacher's
coverage counts, not its broader playing strength.

The two-source policy's paired baseline evaluation,
`development-evaluation-20260906-221505/`, lost all eight games. It made
34 legal returns in 98 rallies. All artifact, identity and candidate motor
checks passed. The three-source policy is now evaluated on exactly the
same development seed schedule, 1141000–1141007, in
`development-evaluation-20260906-221844/`. Preserve both reports and all
failures. No model is promoted, and no reserved final seed has been used.

The paired three-source evaluation completed all eight games and 125
rallies. Candidate legal returns increased from 34 (two-source) to 245
(three-source) on the same seed schedule. Both lost all eight games. The
three-source policy scored one point in each of two far-end games; all
other candidate game scores were zero. All three-source artifact, identity,
and candidate motor checks passed. There were no infeasible paddle steps.
This is improved return performance, not a passed competitive objective.

Started two local PPO curriculum updates from the preserved three-source
checkpoint, 160 requested rallies each, versus the frozen sampled baseline.
Training seeds start at 1030000; development seeds start at 1143000.
This stage uses shared team rally-win rewards so successful rallies provide
learning signal before the policy can win whole baseline games. The final
game-win objective and frozen 80-game acceptance protocol are unchanged.
Both older imitation checkpoints and all failed fits remain available.

Added stopped-curvature and inner-recovery fixtures, each tested on both
court ends. There are now ten recorded-command replay cases in the 61-case
runtime suite. The asset-import request timed out during a domain reload;
readback confirmed both exact fixture hashes and loaded TextAssets. The
Editor returned ready with compilation complete before tests were started.
The runtime suite is running. Full-match acceptance is still pending.

The inner-reach recovery passed all 61 runtime tests in 65.34 seconds:
`inner-recovery-runtime-green-20260906-2051.json`. Its eight-game development
check, `development-evaluation-20260906-205124/`, then completed with zero
candidate motor-limit violations and zero infeasible guard steps across all
phases. Peak candidate paddle acceleration was 100.0369 m/s², within the
unchanged 100.1 numerical test tolerance. It had 207 candidate legal returns
in 136 rallies and took 115.07 seconds. The candidate lost all eight games.

This establishes a motor improvement on the diagnosis schedule, not playing
strength or final acceptance. A new development seed block starting at
1127000 is being checked before further training. Reserved final seeds remain
unused. The runtime source is still
`4b1ddba0940486e60a11c0fb9ac3eb6be2105846a246a8b73918c437bfe716e9`.

### Rally-win PPO and paired comparison — 2026-09-06 22:37 UTC

Driver `training-loop-20260906-222210/progress.json` completed both updates.
The unchanged runtime source is
`7a04ba2e95066440b9c5f0bb1d2c3454dd04e5c172028de8921194d5f16ad9d2`.
Each collection completed 165 rallies and 11 games against the frozen
sampled baseline. Both collections lost all games. Reports are
`competition-20260906-222210.json` and `competition-20260906-222528.json`.
They contain 35,492 and 35,078 player decisions. Each took about 134 seconds.

The first update saved `ppo-20260906-222434/actor.json`, SHA-256
`4d2578c0f364c461cfa5f05df0e62d245ca059a72712a79b8874dd0656f89955`.
The second saved `ppo-20260906-222751/actor.json`, SHA-256
`028f67fe6dbdb6289d464675bd210eeb5f9b75e3cd3397149eb369b4f35d7b00`.
Each applied 140 optimizer updates. Both Unity export checks passed all 32
cases, with maximum error 0.0000076294. Both short development checks lost
all three games. All four collection reports passed candidate motor checks.

The second update retained the coverage result in
`coverage-20260906-223248.json`: 12/16 contacts and 10/16 legal landings.
The movement-disabled cases had no contacts. No infeasible motor steps
occurred. The teaching controller had the same contact and landing counts.

Paired baseline test `development-evaluation-20260906-223322/` used the same
development seeds 1141000–1141007 as the two imitation parents. It completed
eight games and 124 rallies. It made 296 candidate legal returns, compared
with 245 in 125 rallies for imitation 221506. Both models lost all games.
Candidate rally wins were 16/124 versus 17/125. More returns do not establish
better competitive performance. All artifact, player identity and candidate
motor checks passed. Final evaluation seeds remain unused.

Started the 16-game paired partner test
`mixed-partner-20260906-223638.json`. The candidate is PPO 222751; the older
opponent and alternate partner are imitation 221506. Both models trained
under the current runtime source. This test uses independent player models
with the same physical constraints on all four players.

The training driver now checks candidate motor measurements immediately
after both training and development collection. An unsafe development test
stops the sequence before another training update. Two regression tests
cover safe and unsafe results for both data splits. All 73 Python tests
passed. No runtime source or frozen baseline file changed in this step.

### Partner result and larger game-win stage — 2026-09-06 22:42 UTC

Partner report `mixed-partner-20260906-223638.json` completed all 16 games
and 453 rallies in 254.49 seconds. Its SHA-256 is
`ca28ee6cbd87b338284a0e964481819d112e9d5daec01c67e59f46bda88d6833`.
The checker verified model and collector hashes, schedule, player ownership,
decision timing, complete games, and all four players' physical limits.

With the same-policy partner, the candidate team won 4/8 games. The designated
candidate made 65 legal returns; its teammate made 64. With the older-policy
partner, the team won 4/8. The candidate made 51 returns; its teammate made 56.
These counts show independent participation. They do not prove better play
than the older model. Most rallies still ended after one return or fewer.
There were no motor failures or incomplete games.

The temporary visible preview used PPO 222751 and interactive seed 1300000.
All four full-body player renders were visible in the camera image
`preview-ppo222751-20260906-2239.png`. Each player made a non-serve hit during
the preview. Replay had 322 frames. Moving through replay did not advance
the simulation or move its live ball. Exiting replay succeeded. Evidence is
in `preview-ppo222751-20260906-2241.json`. This is not a keyboard or HUD test.
The preview uses an unsaved TextAsset in Play mode and is paused. The saved
scene is unchanged and still has no accepted model assigned.

Started `training-loop-20260906-224141/progress.json`: four game-win PPO
updates, 256 requested rallies each. Initial candidate is PPO 222751. The
fixed opponent is imitation 221506. Training seeds start at 1032000;
baseline development seeds start at 1145000. Each iteration saves a child,
checks Unity output parity, and evaluates it against the frozen baseline.
The value model starts fresh because the objective changed from rally wins
to game wins. All heads train; no teacher or new physics change is used.
The live driver process must be observed, not restarted after a wait timeout.

### Contact diagnosis and partner reporting — 2026-09-06 22:55 UTC

Added `scripts/player-contact-outcomes.cs`. It records selected candidate
shots, planned contact details, measured paddle and ball velocities, and the
actual rule-event sequence. Four short cases alternate court ends against
the frozen sampled baseline. It retains partial games as diagnostics, not
match-strength evidence. It supplies no actions, labels or ball corrections.
The script compiled in the live Editor and correctly refused to start over
the active training job. Its full collection still needs to run.

The read-only classifier `scripts/player_contact_outcomes.py` distinguishes
legal landings, opponent volleys, faults before landing, and missing or
truncated outcomes. It measures target error only for planned shots that
actually land. Six tests cover event ownership, missing or duplicate traces,
fault ownership, accidental contacts, truncation, and later rally losses.

Partner reports now include both court-end and player-seat breakdowns.
The earlier 4/8 same-policy result was 0/4 near-end wins and 4/4 far-end wins.
The mixed-partner result was 2/4 at each end. This small sample does not
establish the cause of the difference. One new test prevents the aggregate
report from hiding this split. All 80 Python tests passed.

The computer-use keyboard check could not start because the Mac was locked.
No keyboard or HUD test is claimed. Local training remained active through
Unity CLI. The lock does not block the remaining training and diagnostics.

### Game-win stage and contact trials — 2026-09-06 23:05 UTC

Driver `training-loop-20260906-224141/progress.json` completed and its process
exited normally. Four training batches completed 274, 267, 286, and 294
rallies. Wins against the older model were 7/10, 4/7, 4/8, and 4/9 games.
Collection times were 157.41, 155.02, 161.42, and 167.28 seconds. All eight
training/development reports passed candidate motor checks. All four Unity
export checks passed. These training wins are not held-out proof.

The four saved children are `ppo-20260906-224426`, `224754`, `225132`, and
`225510`. Their exact hashes and parent chain are in the driver report.
The last actor's SHA-256 is
`acc0cee5f6bf9ec1cff5bb1c184fd4c635dc3e34fe73f94dc30677425078e000`.
Its coverage `coverage-20260906-225823.json` remained 12/16 contacts and
10/16 legal landings. Movement-disabled cases had no contacts. The baseline
development checks lost 3/3, 3/3, 3/3, and 2/2 games. No model was promoted.

Contact report `contact-outcomes-20260906-225638.json` completed 55 rallies
in 55.93 seconds under retained source `7a04ba2e...`. Its SHA-256 is
`2f1b47f1b398f308289b2300a5aee914be6aeacb12edd617f0ea6a075a262a8a`.
It recorded 111 candidate shots: 79 legal landings, 18 opponent interceptions,
eight candidate WrongSide faults, four candidate body contacts, and two
opponent body contacts before landing. All motor checks passed. Mean target
error on legal landings was 1.956 metres. For 54 landed deep flat shots,
mean depth error was -2.341 metres, measured paddle-normal speed was
5.029 m/s, and planned swing speed was 6.992 m/s.

Rejected trial one extended only upright flat run-up from 0.06 to 0.10
seconds. Source:
`691503bc18a84da8ed5b2da4ad7534996189f595b3ce16718278d93f4aa1d1c5`.
Report `contact-outcomes-20260906-230136.json` recorded 94 shots and 66
legal landings in 59 rallies, with 16 WrongSide faults. Mean legal-landing
error was 1.866 metres. Motor checks passed, but contact and fault results
regressed. Its exact source is retained in the sibling `.PlayerSwing.cs`.

Trial two restores the 0.06-second path and uses a 1.3 velocity-command
gain only for upright flat strokes. All speed, acceleration and reach limits
remain unchanged. Low grips and spin strokes are unchanged. Source:
`d0099cffdd9b2847e1692fd29c552ace44a66ddd97e0770fe0d245611490331d`.
Report `contact-outcomes-20260906-230454.json` is running. Both trials use
unchanged PPO 225510 and development seeds 1150000–1150003. The actor's
older training source is disclosed, not rewritten. No training runs during
these trials. The collector now snapshots the exact swing source as well as
its own code. The original runtime is preserved in the training driver.

Trial two completed 54 rallies with 107 candidate shots, 74 legal landings,
20 opponent interceptions, eight WrongSide faults, three candidate body
contacts and two DoubleHit faults before landing. Mean target error was
2.090 metres. Its report hash is
`529b8ed4494b571573736a7f7439b2b76013595c372bd287aed5cbccd971720b`.
All motor checks passed. Target accuracy did not improve; reject this trial.

Trial three scaled the upright flat path speed and feed together by 1.3,
with the original 0.06-second timing. Source was
`864e76af24e0c9dbfd97b5ca29ff8154f3b711a896510b1542cc928cc466a31a`.
Report `contact-outcomes-20260906-230748.json` completed 51 rallies with 108
candidate shots, 79 legal landings, 17 opponent interceptions, 11 WrongSide
faults and one Out fault before landing. Mean target error was 2.107 metres.
Its report hash is
`91aa3fbaea5de6014fb64fed3106cf6a07bec4d60a1ac42c3175a6c2dc8f195a`.
All motor checks passed, but target accuracy did not improve. Reject it.
Both later trials saved and hashed their exact `.PlayerSwing.cs` snapshots.

The original `PlayerSwing` was restored with a source patch. The Python
source hash is again exactly
`7a04ba2e95066440b9c5f0bb1d2c3454dd04e5c172028de8921194d5f16ad9d2`.
All 63 frozen files remain unchanged. A fresh 73-case runtime regression run
started after restoration. The first live source read timed out; no write
was retried. The following test command returned an active test handle.
No trial is retained in the runtime, and no new model was relabelled.

The next curriculum stage will optimize only shot logits against the saved
baseline. This holds the current movement/hit outputs and shared feature
layers fixed. Use team rally-win rewards for this curriculum stage, then
return to the game-win objective. This is still independent actor control,
not a central hitter selector or a scripted foot controller.

### Restored runtime verified; shot training active — 2026-09-06 23:15 UTC

Fresh runtime tests passed 73/73 in 67.29 seconds. Saved evidence:
`swing-restore-runtime-green-20260906-2313.json`. Editor tests passed 15/15
in 0.81 seconds, saved as `swing-restore-editor-green-20260906-2314.json`.
Python tests passed 80/80. The live Editor and Python source hashes both
match retained source `7a04ba2e...`; all 63 baseline files are unchanged.

Started `training-loop-20260906-231444/progress.json` from PPO 225510:
six updates, 256 requested rallies each, frozen sampled baseline opponent,
shot logits only, and team rally-win curriculum rewards. Training seeds start
at 1036000; development seeds start at 1151000. The driver saves every child,
checks output parity and protected-parameter invariance, and checks baseline
development games after each update. It is live in process session 38477.
Do not restart it merely because a wait expires.

The temporary visible trained preview was cleared when Play mode stopped for
the trials and tests. The saved independent-player scene remains unchanged,
with no accepted actor assigned. It is open in Play mode with the untrained
visible probe paused. Keyboard/HUD verification remains pending because the
Mac was locked. The goal is active, with no blocker to continued local work.

### Shot-only learning checked on fixed states — 2026-09-06 23:27 UTC

The six-update driver remains active in process session 38477. The first two
updates are complete. The third update is collecting. Do not start another
Unity collector or change the runtime/trainer during this job.

Update 1 saved `ppo-20260906-231813/actor.json`, SHA-256
`898aacfbb7ae992007f40531e94692e3a094cd15f5b25d88a95a9420edf16857`.
Training report `competition-20260906-231445.json` contains 256 rallies,
17 complete games, 32 rally wins, 343 candidate legal returns, and no game
wins. Collection took 195.56 seconds. The optimizer made 200 updates in
2.37 seconds. Development report `competition-20260906-231814.json`
contains 32 rallies, two game losses, five rally wins, and 74 legal returns.

Update 2 saved `ppo-20260906-232257/actor.json`, SHA-256
`e9d81b25bbc105685049164d955eb8741fcc0e58689b697e4333fc536ff149dc`.
Training report `competition-20260906-231857.json` contains 270 rallies,
17 complete games, 40 rally wins, 409 legal returns, and no game wins.
Collection took 224.03 seconds. Development report
`competition-20260906-232259.json` contains 32 rallies, two game losses,
five rally wins, and 54 legal returns. The development seeds differ between
updates; these short results are not a paired comparison.

Both updates passed 32-case Unity/Python parity checks with maximum error
0.0000038147. All four training/development reports passed motor checks and
matched the driver's saved hashes. Both trainers reported exactly zero
change to protected non-shot parameters. Runtime source remains
`7a04ba2e95066440b9c5f0bb1d2c3454dd04e5c172028de8921194d5f16ad9d2`.
All 63 frozen baseline files are unchanged.

Added read-only `scripts/player_shot_audit.py` and five tests. The audit uses
one fixed training observation bank. It compares shot probabilities and
maximum-probability choices, separately from protected parameters/outputs.
The nearby-ball filter uses current ground distance below 1.5 metres and
the expected team. It does not predict contact or provide training labels.
Serve-flight, return-flight, and rally results are reported separately.

Saved `shot-audit-first-two-20260906-2326.json`, SHA-256
`942f4b4ef2e16f73d6c7b8954bd47ceade32e8b57cdf17557fcd3394c6c82a3b`.
It selects 2,178 observations from 50,232 recorded training decisions.
All nine shots were sampled in this subset. Against the unchanged parent,
update 1 changed 68 maximum-probability shot choices; update 2 changed 61.
Both had zero non-shot parameter and output change. These are repeated
training states, not independent games or held-out performance evidence.
The new audit and full Python suite passed 85/85 tests. `git diff --check`
passed. No runtime source, scene, or saved demo actor changed this turn.

Next: finish the existing six updates, audit the full sequence, and run
paired development games and coverage on the retained candidate. Keep the
final evaluation seeds unused until a candidate is ready. The goal remains
active. No model has been accepted or promoted.

### Six updates complete; paired reward comparison active — 2026-09-06 23:45 UTC

Process session 38477 ended successfully. Driver
`training-loop-20260906-231444/progress.json` is complete. Do not restart it.
All six actor/rollout/development hashes matched. Each child passed 32-case
Unity/Python parity. All twelve game reports passed the candidate motor
checks. Every shot-only update preserved the protected parameters exactly.

| Update | Training rallies | Training games | Training legal returns | Development games | Development legal returns |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 256 | 17 | 343 | 2 | 74 |
| 2 | 270 | 17 | 409 | 2 | 54 |
| 3 | 264 | 16 | 399 | 3 | 60 |
| 4 | 256 | 18 | 385 | 3 | 75 |
| 5 | 259 | 17 | 376 | 3 | 78 |
| 6 | 259 | 17 | 397 | 2 | 70 |

There were no game wins in either split. Training had 207 rally wins in
1,564 rallies. The six collections took about 21.3 minutes in total. Each
optimizer update took less than three seconds. The simulator, not the
optimizer, dominates this local run. These are current measured timings,
not a cloud-cost estimate. No cloud job was started.

Last child: `ppo-20260906-234059/actor.json`, SHA-256
`91813ce6809d5c22b26ec16dd57941552dad8249effaa68992ce1cef220a2b4a`.
Its training report is `competition-20260906-233710.json`; its development
report is `competition-20260906-234101.json`.

The first fresh critic starts at zero. In the fixed nearby-ball observation
bank, serve-flight decisions had a median 3.1 seconds to the terminal
reward. The direct reward term under the current .995/.95 return settings
had a median weight of 0.03047. About 79.8% had weight below 0.1. Later
fitted critic values can carry earlier information, so this is not proof
that PPO has no learning signal. It motivates a controlled credit trial.

After the six-update process ended, added `--credit-assignment full_episode`
to the PPO trainer and bounded training driver. It uses gamma=1 and lambda=1
within each recorded episode. The default rally settings remain unchanged.
The game-win objective retains its existing full-game return settings.
Three added tests check defaults, long-trajectory positive/negative credit,
and invalid options. Full Python suite: 92/92 passed.

The controlled trial uses the same first rollout, parent, 200 optimizer
updates, learning rate, shot-only heads, and fresh critic as update 1. Only
the return calculation changes. Trial `ppo-20260906-234237/actor.json`,
SHA-256 `42a63361377116b73a1851405145a93673f75fded8e0e0ede284d5a2ec70aa7c`,
took 2.29 seconds to optimize. It preserves all protected parameters and
passes 32-case Unity parity at maximum error 0.0000038147. Its data hash is
`b913fe808486b083ee0aa2e9b4016ed73656801c16a63da764e6198b29da9056`.

Fixed-state audit `shot-audit-six-and-full-20260906-2343.json`, SHA-256
`b28876d9c4417d5de57030e0686730dc57db18ea49e8115092e71399f202d7cc`,
compares all six children and the trial against their parent on the same
2,178 states. Changed maximum-probability shot choices were 68, 61, 71,
123, 163, and 188 for updates 1–6, and 43 for the full-rally trial.
All non-shot parameters and outputs are identical to the parent. These
counts show learning changes, not improved playing strength.

Added `scripts/player-compare-models.py` and four schedule tests. It runs
the same eight development seeds for up to four actors, retains all game
results, checks artifact/identity/motor evidence, and stops on an incomplete
or changed run. It cannot select final seeds or automatically promote a
model. Its verifier reproduced the existing PPO 222751 result: eight losses,
124 rallies, and 296 legal returns, with all evidence checks passed.

The new comparison is active in process session **42729**:
`model-comparison-20260906-234348/progress.json`. It uses seeds
1141000–1141007 for each of PPO 225510, PPO 231813, PPO 234059, and PPO
234237, in that order. These are deliberately reused development seeds.
The first live run is `development-evaluation-20260906-234350`.
Poll this exact process. Do not start another collector or change runtime
or comparison code until it ends. The final 80-game protocol is unused.

The external contact diagnostic now records shoulder, hand, reach, paddle
position/angular velocity, and planned impact. These fields are for a future
live diagnostic; this edited collector has not yet been executed. No runtime
source or physical behavior changed. Current runtime remains `7a04ba2e...`,
and all 63 baseline files remain unchanged. `git diff --check` passed.

Next: complete the paired comparison, then check coverage and the recorded
contacts of the relevant retained candidate. Do not claim a better model
from shot changes or return count alone. No actor is accepted or installed
in the saved demo. Keyboard/HUD proof remains pending. The goal is active.

At 23:46 UTC, the comparison completed its first eight games for parent
PPO 225510: zero game wins, 17 rally wins in 125 rallies, and 262 legal
returns. All artifact, ownership, and motor checks passed. The driver has
started PPO 231813 in `development-evaluation-20260906-234615` and remains
live in session 42729. Three actor comparisons are still pending.

### Comparison complete; larger teacher refinement active — 2026-09-07 00:06 UTC

Comparison session 42729 ended successfully. All four actors completed the
same eight development games with verified artifacts, independent identities,
and motor limits. Driver `model-comparison-20260906-234348/progress.json`
has SHA-256 `7c9035fccbb3f21cc85da499395769467de90bf2729792996cff4bf7df26d84f`.

| Actor | Game wins | Rally wins / rallies | Legal returns | Seconds |
| --- | ---: | ---: | ---: | ---: |
| PPO 225510 parent | 0/8 | 17/125 | 262 | 139.81 |
| PPO 231813 first shot update | 0/8 | 9/109 | 245 | 126.46 |
| PPO 234059 sixth shot update | 0/8 | 14/123 | 269 | 139.94 |
| PPO 234237 full-rally-credit trial | 0/8 | 7/108 | 254 | 128.38 |

The latter three actors are not selected as better training parents. The
sixth child's extra returns did not improve rally wins. The controlled
full-rally trial also failed to improve this paired sample. This does not
prove that the method can never work; it rejects this saved trial as an
improvement. Keep the parent and all failed reports.

Contact diagnosis `contact-outcomes-20260906-235421.json` reproduced the
same 55 rallies and 111 shots as the earlier parent trace. It passed source,
artifact, ownership, and motor checks. SHA-256:
`409d3a104c3d828e0d5dcb19e0b4605060ad1873c173bcf260d7e03ef3fef828`.
Outcomes were 79 legal landings, 18 opponent interceptions, eight candidate
WrongSide faults, four candidate BodyContact faults, and two opponent
BodyContact faults before landing. Mean planned landing error: 1.956 metres.

For 54 legally landing deep-right flat shots, mean reach was 0.551 metres;
none exceeded 0.61 metres. Mean normal paddle speed was 5.029 m/s, versus
planned swing speed 6.992 m/s. Contact-point angular motion did not explain
the difference. Mean contact delay was 0.02327 seconds. This rules out an
already fully extended arm at these hits as the main explanation. The motor
also has a 6 m/s shoulder-relative reserve and an outward braking constraint,
so the nominal 12 m/s paddle limit is not the whole execution envelope.

A higher-angle contact trial was considered but **deferred before any
runtime edit**. The next teacher result showed that the current bounded
controller can win a baseline game. Improving learned control now has
priority over changing the environment again. Runtime source is still
`7a04ba2e95066440b9c5f0bb1d2c3454dd04e5c172028de8921194d5f16ad9d2`.

Diagnostic teacher report `curriculum-20260906-235647.json` used development
seed 1166000, all nine shots, teacher probability 1, and the frozen sampled
baseline opponent. It made 237 legal returns against 250 baseline returns
in 64 rallies and 132.96 seconds. The near-side teacher won 11–8. The
far-side game stopped at the requested diagnostic limit with score [7,6];
it is not counted as a win or loss. All 31,946 decisions came from the
privileged teacher. There were no learned actor decisions. All ownership
and physical-limit checks passed. Report SHA-256:
`2bb65980f17711c3b7aafec593057c2c8c31c7658b2fc11db815d7c8407ddc38`;
data SHA-256 `fdc57ff63f332da49765b8761291c63576a5132722a44bc600ac4962a57ab30a`.

Started a new 256-rally teacher-only training collection at seed 1042000,
with all nine shots and the frozen sampled baseline. Exact active report:
`curriculum-20260907-000417.json`. This is disclosed supervised curriculum
data, not competitive actor results. The independent control interface,
20 Hz decisions, 25 ms latency, and bounded motor remain in use.

Extended `scripts/player-agents-refresh.py` to support all-shot curricula,
an existing held-out development report, initial actor weights, balanced
additional sources, and recorded optimizer settings. It now rejects unsafe
teacher motor data before fitting. Four-player teacher sources check both
teams; baseline sources check only the candidate seats. Four added tests
passed, bringing the Python suite to 96/96. All seven existing input reports
also passed the new motor gate. The process snapshots its driver sources.

Active process session **34819**, driver
`refresh-20260907-000509/progress.json`, will:

1. Wait for the exact active training report. Do not restart the collection.
2. Validate its source, ownership, and motor measurements.
3. Fine-tune PPO 225510 for 40 epochs at learning rate 0.0001, hidden width
   256, batch 1024, with equal expected sampling mass from four sources:
   the new baseline teacher data, four-teacher curriculum 214420, incoming
   drills 220500, and the older baseline mixture 220947.
4. Use the new development teacher report 235647 plus validation sources
   215536, incoming 220827, and mixture 221358. Development selection gives
   each source equal weight. These data do not enter training.
5. Check Unity/Python export parity and run actor-only baseline development
   games at seed 1167000. No automatic promotion occurs.

The driver was confirmed live at 56/256 rallies, 19,022 labels, and 143
teacher-side legal returns. Do not edit the runtime or the refresh/imitation
trainer code while it runs. After completion, check coverage, movement
ablation, paired baseline games, and partner performance before further
team-win reinforcement learning or final evaluation.

The Mac was checked again with the Computer Use skill and remains locked.
Keyboard/HUD verification cannot run until it is manually unlocked. This
does not block the local simulation work. Play was briefly stopped and
restarted after the completed diagnostics; no scene was saved or changed.
The untrained visible probe is paused. All 63 baseline files are unchanged.
No actor is accepted or installed. Final seeds remain unused. The goal is
active and incomplete.

### Four-source fit checked; learner-controlled correction active — 2026-09-07 00:25 UTC

Refresh session 34819 completed successfully. Driver
`refresh-20260907-000509/progress.json` has SHA-256
`f2a1268cddad3334603a4cd34a3a94c8e9dc124569eb36b2ca851d3ef8f18f43`.
The teacher training collection `curriculum-20260907-000417.json` completed
256 rallies and 97,678 labels in 428.70 seconds. It made 724 legal returns
against 718 baseline returns. The teacher won one of eight complete games;
one additional game was partial at the requested collection limit. These
are privileged teacher outcomes, not learned-player strength. Report hash:
`4699d02dca6461b2177249f624ceea66e355c4e104000736ede541557ce1bc26`.

Saved actor `imitation-20260907-001146/actor.json`, SHA-256
`bfdddcdfbf0723767ea9c881343c13dcad34d4baad99a212005ae7045595f561`.
The fit used 470,102 training rows and 113,774 separate development rows
across four balanced sources. Forty epochs made 18,400 optimizer updates
in 132.80 seconds. Development selection retained the checkpoint at update
17,940. It passed 32-case Unity parity with maximum error 0.0000038147.
Its initial actor was PPO 225510. This is supervised corrective fitting,
not a new competitive-reward run or an accepted model.

Actor-only smoke report `competition-20260907-001400.json` completed two
game losses in 33 rallies, with six rally wins and 61 legal returns.
Scores were [2,11] for the near candidate and [11,0] for the far candidate.
The report passed hash and motor checks. SHA-256:
`cc162403b57595d88eb5750186b97d14e2d13cbecc0e971bb1e1d021c27f8716`.

Coverage report `coverage-20260907-001520.json` completed all 48 cases in
8.82 seconds. The learned actor made 12/16 contacts and 10/16 legal landings,
matching the diagnostic teacher. Movement-disabled controls made no contacts
or landings. All cases passed motor checks with zero infeasible steps.
Source, actor, and collector hashes matched. Report SHA-256:
`64843b0a15f96fee936c57e42e1961ce70c50a4044fafde2d28334fd42dcec5f`.

Paired development session 22680 completed successfully. Driver
`model-comparison-20260907-001712/progress.json`, SHA-256
`9154d60c746d95917301c6496a78723fd069fca0a26bb2983a92d29768241146`,
used the unchanged eight seeds 1141000–1141007. All identity, artifact,
and motor checks passed. The new actor lost all eight games. It won
23/135 rallies with 218 legal returns; PPO 225510 had won 17/125 with
262 legal returns on these paired conditions. New actor rally wins split
3 near and 20 far. This small, uneven result is not proof of improved
match performance across court ends. Retain it only as an experimental
training parent, with the previous parent and all failures preserved.

The next correction stage records the current actor's own play. The
privileged teacher only produces labels. It cannot move a player or select
the executed hitter when teacher probability is zero. This targets states
created by learner mistakes rather than only expert-controlled trajectories.

Extended the refresh driver with explicit teacher probability and a check
that mixed/learner-only data names the expected collection actor hash. Two
new tests reject missing or wrong collection actors. All 98 Python tests
passed. This does not change Unity runtime code, observations, or limits.

Active collection: `curriculum-20260907-002215.json`, 256 requested rallies,
training seed 1043000, all nine shot labels, frozen sampled baseline,
collection actor `imitation-20260907-001146`, teacher probability **zero**.
A live Editor read confirmed 10,336 actor decisions and zero teacher control
decisions. The teacher still writes training labels. This is not a final
or independent held-out evaluation.

Active process session **11611**, driver
`refresh-20260907-002306/progress.json`, will wait for this exact collection,
validate ownership/motor data, collect 64 separate development rallies at
seed 1168000 under the same learner-only control, and fine-tune for 32 epochs
at learning rate 0.0001. Training has three equal-mass sources: the new
learner-state labels, teacher baseline collection 000417, and incoming drills
220500. Validation uses the new learner-state development report, teacher
report 235647, and incoming validation 220827. It then checks export parity
and actor-only baseline games at seed 1169000. There is no automatic promotion.

The process was confirmed live at 61/256 rallies, 15,516 labels, and 105
actor-side legal returns. Poll session 11611; do not restart its collection
or modify the runtime/refresh/imitation code while it runs. After completion,
repeat coverage and paired games, then check partners and resume the team-win
reinforcement stage if the candidate merits it.

Current runtime is still `7a04ba2e...`. All 63 baseline files are unchanged.
`git diff --check` passed. The scene is unchanged, with no accepted actor
installed. The Mac lock still leaves keyboard/HUD verification pending.
Final evaluation seeds remain unused. The goal remains active and incomplete.

### Learner correction checked; fixed-opponent pool training — 2026-09-07 00:44 UTC

Refresh session 11611 and comparison session 64989 both completed successfully.
Correction training report `curriculum-20260907-002215.json` contains 64,382
actor decisions and zero teacher control decisions. Development report
`curriculum-20260907-002802.json` contains 15,132 actor decisions and zero
teacher control decisions. The privileged teacher supplied labels only.

New actor `imitation-20260907-002944/actor.json` has SHA-256
`781ebc598ccc02a5ca7dd1d910443a8470a9ccea1100defa9556e5fcff7aa53f`.
The fit used 204,818 training rows and 55,772 development rows from three
balanced sources. It ran 32 epochs in 55.60 seconds. Unity parity passed
32 cases with maximum error 0.0000076294. This is supervised fitting.

Coverage report `coverage-20260907-003217.json` passed source, model,
collector, and motor checks. Its SHA-256 is
`b981342b27b3ecc8ce83c01d80680f40142ce684d99f01b007f5d163053d0df0`.
Learned players made 11 contacts and nine legal landings in 16 cases.
The teacher made 12 contacts and 10 legal landings. Movement-disabled
controls made no contact. The one-contact and one-landing regression from
the parent remains a recorded failure.

Paired development folder `development-evaluation-20260907-003410` passed
all identity, artifact, and motor checks. It used seeds 1141000–1141007.
The actor lost all eight games, with 38/159 rally wins and 382 legal returns.
Its parent had 23/135 rally wins and 218 legal returns on the same seeds.
New rally wins split 34 near and four far. Thus the aggregate improvement
does not establish improvement across both court ends. Completion hash:
`10d2532818a5155bf03c2100dcd3ba684b5eac5ed4f866bc901322437e7ffbee`.
The actor is retained only as an experimental starting point for game-win
training. Neither it nor its parent is accepted for final delivery.

The training driver now supports an ordered fixed-opponent pool. It keeps
the previous single-opponent behavior, rejects ambiguous or duplicate
pools, snapshots all opponent files, and checks all hashes before each
stage. Each stage records its actual opponent and hash. Four new tests
passed; the full Python suite passed 102 tests. Runtime C# was not changed.

Active process session **12287** runs
`training-loop-20260907-004331/progress.json`. Initial actor is 002944.
There are eight stages of 512 requested rallies. The opponent order is
PPO 225510, imitation 001146, then the frozen sampled doubles baseline,
repeated. All actor outputs are trainable. The reward is team game wins,
with a fresh initial critic and no teacher control. Training seeds start
at 1044000 with a 1000 stride. Development seeds start at 1170000 with
the same stride. Each stage checks export parity and baseline games.

The Editor is ready in Play mode. The last disk check showed 16 GiB free.
All 63 baseline files remain unchanged. Current runtime source remains
`7a04ba2e95066440b9c5f0bb1d2c3454dd04e5c172028de8921194d5f16ad9d2`.
Poll the existing process. Do not restart it or edit its dependencies while
it runs. Final evaluation seeds remain unused. No model is installed.
Keyboard and HUD checks remain pending after the earlier Mac lock.

### First two pool stages checked — 2026-09-07 00:59 UTC

Session 12287 remains live. The first two stages passed report identity,
source, motor, and 32-case export-parity checks. The initial model made
eight wins in 18 training games against PPO 225510: four wins in nine
games from each court end. Collection completed 520 rallies and 60,598
rows in 290.24 seconds. Its update made 240 optimizer steps in 3.28 seconds.
Actor `ppo-20260907-004837/actor.json` has SHA-256
`f2a16a031db8f68c661ce902033bba0ad3c639946e1042cb04bdc8817418048c`.
Training report `competition-20260907-004331.json` has SHA-256
`9327a082c8045fa983805014e02f2a7a245f1084760cca5a7a80a263c57d6102`.
Its baseline development report `competition-20260907-004839.json`
contains two losses in 36 rallies, with scores [0,11] and [11,3].

The next collection won 12/19 games against imitation 001146: seven of
10 near-end games and five of nine far-end games. It completed 540 rallies
and 62,600 rows in 296.61 seconds. Its update made 248 optimizer steps in
3.58 seconds. Actor `ppo-20260907-005436/actor.json` has SHA-256
`f66d8fdc3163d5a08d1334c24198fc21ee54808ee05cda2b70ad23619a8c0ae3`.
Training report `competition-20260907-004921.json` has SHA-256
`d96ef2775068460946baac0decbc5e206e4f31cb2d3fdf3bd971da2e182f98b3`.
Baseline development report `competition-20260907-005438.json` contains
two losses in 33 rallies, with scores [1,11] and [11,0]. Its SHA-256 is
`e0da9c4a5fab83ec734ebc644fe7a29335dc0fac36f5616d6878d0254f60e56c`.

These training results do not prove improvement against the baseline.
Development uses different seeds at each stage; compare saved models on
the same paired schedule after the run. Stage three is now collecting
against the frozen sampled baseline at training seed 1046000.

A read-only data check found 15,382 learner-state rows for each near-end
seat and 16,809 for each far-end seat in correction collection 002215.
Teacher baseline collection 000417 has 29,279 rows per near-end seat and
19,560 per far-end seat. The modest learner-state count difference does
not establish a cause for the observed end-specific performance difference.
No training code or data was changed during this check.

The Computer Use check again reported a locked Mac. No keyboard or HUD
test was performed. The local training process is unaffected. The goal
remains active and incomplete, with no accepted or installed model.

### First direct-baseline pool stage checked — 2026-09-07 01:05 UTC

Stage three completed 513 rallies and 131,992 rows in 489.05 seconds.
It lost all 31 training games against the frozen sampled baseline: 16
near-end games and 15 far-end games. Report
`competition-20260907-005521.json` passed completion, source, and motor
checks. Its SHA-256 is
`35ea0536257afdba767836cd4cbf0610020f4f809622e2b10a3fe33fca126bc4`.

The update used 516 optimizer steps in 7.01 seconds. Actor
`ppo-20260907-010356/actor.json` has SHA-256
`19bebf092d6291f545485dbf7841b52f3fd44a82cd6af6111c0419cd01b59f09`.
Its 32-case export parity passed with maximum error 0.0000038147.
Baseline development `competition-20260907-010358.json` lost two games
in 46 rallies, with scores [1,11] and [11,0]. The report passed motor and
hash checks. Its SHA-256 is
`6dfae1304e74ff7ca872fe04e5c0b62fe18bb2a4bb75b158b797f1bc1f835629`.

No baseline improvement is established. Session **12287** remains live;
stage four is collecting against frozen PPO 225510 at seed 1047000.
Finish the existing eight-stage schedule, then compare retained models
on the same paired development seeds. Do not restart the job or edit its
dependencies while it runs. Final seeds remain unused. No model is accepted.

The planned paired comparison for this pool run is fixed before its end:
the starting imitation actor 002944, stage three, stage six, and stage eight.
Stages three and six each complete one pass through all three opponents.
Stage eight is the final checkpoint. Use development seeds 1141000–1141007
for each model, with both court ends, both baseline action modes, and the
existing player-identity swaps. This comparison is not final acceptance.

### Pool stopped on a physical failure; motor repair under test — 2026-09-07 01:36 UTC

Stage four completed 534 training rallies in 328.98 seconds, with 62,654
rows and 10/20 game wins against frozen PPO 225510. Wins split three of
10 near games and seven of 10 far games. The report passed motor checks:
`competition-20260907-010501.json`, SHA-256
`163c5c537eeebc8ec43a87c9a836a298b1d0caf414cc801f34629ea620281a1a`.
Actor `ppo-20260907-011052/actor.json`, SHA-256
`b44e89ae2797571fd2b6a314308ed1d46f3522ae7c711d403bf865fdf83a99cc`,
passed 32-case parity. Baseline development 011054 lost two games in
32 rallies, both with zero candidate points.

Process **12287 is terminal, exit 1**. Driver
`training-loop-20260907-004331/progress.json` is stopped. The fifth
collection completed 537 rallies, 21 games, and 60,524 rows, but failed
the motor gate before optimization. Do not restart this driver or use
that collection for training. The four existing model updates remain saved.
The planned stage-six/eight comparison cannot run because those models
were never produced.

Failed report: `competition-20260907-011137.json`. Game seed 1048016,
candidate team zero, recorded one infeasible paddle step for player zero
and maximum paddle acceleration 1002.218 m/s². The limit is 100 m/s².
Both candidate and opponent actors used the unchanged source `7a04ba2e...`.

The command-trace tool now supports an exact saved training-game diagnostic.
It checks source-report and actor identities, starts the actor random stream
at the recorded game seed, and advances the original serve random stream
past earlier rallies. This is not new training data or a relabelled test.
For the failed game it skipped 430 earlier rallies. Trace
`paddle-commands-20260907-012038.json` captured rally 21, tick 941, in
ReturnFlight. Its SHA-256 is
`37ee0667403f26ab778c530a012cedad2b29363d567ed36e5735dbe58e5a0d12`.
Replay `paddle-replay-20260907-012146.json` reproduced all 120 frames
with zero position and velocity error, including the 1002.218 m/s² failure.

The trace showed crouch motion reversing from downward to upward while
the paddle returned from a low swing. The recovery solver accepted a
one-step reachable hand pose but consumed its remaining stopping distance.
The first proposal applied both preferred radial reserves to every fallback.
It passed the new trace but failed the older low-recovery fixture on both
court ends. Source `1e26727f...` is rejected and retained in
`motor-before-20260907-0123/rejected-all-reserves.cs`.

The narrower proposal leaves the original preferred solve and hard limits
unchanged. During fallback only, it rejects shoulder/grip posture changes
that add outward radial hand motion, then tries slower posture fractions.
It does not change the actor's foot command. Current proposed runtime hash:
`b7f3c9c8bce17bd0e5b072f7e3053dbff3f04ff72c21f0b7776081b0b08d5c13`.
The original motor is retained in
`motor-before-20260907-0123/PlayerPaddleMotor.cs`.

The captured failure is now a permanent fixture,
`paddle-rising-recovery-v1.json`, with tests for both court ends. All 12
recorded recovery tests pass, including the five older fixtures. Evidence:
`rising-recovery-fixtures-green-20260907-0136.json`. The full 75-test
runtime suite is running. All 102 Python tests pass; all 63 baseline files
remain unchanged. Full-game and broader physical checks are still required.

One test attempt failed before execution because it started in Play mode;
the Pipeline status remained stale. The log confirmed the failed run,
which was cancelled before restarting from Edit mode. The first completed
75-test run had two low-recovery failures and one sampled-baseline mismatch.
The baseline mismatch exactly matches the earlier intermittent tick-2126
failure. No baseline code or tolerance was changed. The separate instrumented
repeat `baseline-parity-20260907-013321.json` passed all 19,016 steps and
eight rallies, with zero actor decisions, zero clearance steps, and no
position or velocity difference. Its original failure remains unexplained.

Training is stopped while the motor proposal is tested. No model is accepted
or installed. Final seeds remain unused. The Mac lock still prevents the
separate keyboard and HUD checks. The goal is active and incomplete.

### Narrow recovery proposal passes tests and the full failure game — 2026-09-07 01:42 UTC

Current proposed source remains
`b7f3c9c8bce17bd0e5b072f7e3053dbff3f04ff72c21f0b7776081b0b08d5c13`.
The full runtime suite passed 75/75 tests, including the new fixture on
both court ends and both original-baseline comparison modes. Saved result:
`rising-recovery-runtime-green-20260907-0138.json`. Editor tests passed
15/15: `rising-recovery-editor-green-20260907-0139.json`. Python remains
102/102. No baseline source or tolerance was changed.

The complete failure game was repeated with the original two actor files,
game seed 1048016, root serve seed 1048000, and 430 prior rallies skipped.
Report `paddle-commands-20260907-013940.json` completed all 27 rallies,
with the same 11–8 score and hit counts. All four players passed motor
checks. Infeasible steps fell from one to zero; maximum paddle acceleration
was 100.0332 m/s² and maximum reach was 0.60928 m. The report preserves
both the old source-report hash and the revised runtime hash. SHA-256:
`091c6e119eff9fcb1bf1a6066279a19042c46c655e340e1232543018717f917d`.
This is physical-regression evidence, not improved learned performance.

The eight-game physical development check is running in
`development-evaluation-20260907-014140`, using seeds 1178000–1178007.
It uses actor 011052 with an explicit historical-candidate flag, both court
ends, both baseline action modes, and identity swaps. No training rows or
final seeds are used. Poll `Picklebot.Final.Status` and the live `TickFinal`
callback. The initial eval-file command completed successfully; session
99495 is terminal. Do not start another collector until this one finishes.

The old training process 12287 remains stopped. Do not optimize its unsafe
fifth collection. Broader motor checks must pass before starting a new,
source-tracked training run. No model is accepted or installed. The goal
remains active and incomplete.

### Broader motor check passed; training resumed with new source — 2026-09-07 01:47 UTC

Development folder `development-evaluation-20260907-014140` completed all
eight games. Current source, artifact hashes, scheduled identities, game
completion, and candidate motor checks passed. Completion SHA-256:
`92c044d40790163b9bd8dec52f9dba38641aa37f56422d3b15a218cec0995387`.
It had 159 rallies, 39 candidate rally wins, and 365 legal returns in
200.35 seconds. It still lost all eight games. These seeds differ from
the earlier paired comparison, so this is not proof of better playing
strength. It supports retaining the motor repair with the exact-game and
75/75 runtime, 15/15 Editor test results. All 63 baseline files are unchanged.

The training driver now accepts an explicit fixed-pool starting index.
Two tests verify ordered resumption and reject out-of-range indices. The
full Python suite passed 104/104. The driver also records the initial
critic hash. This does not change PPO rewards, limits, or evaluation seeds.

New live process **13004**, driver
`training-loop-20260907-014628/progress.json`, starts from actor and critic
`ppo-20260907-011052`. Both hashes were checked against their saved training
report before launch. Runtime source is
`b7f3c9c8bce17bd0e5b072f7e3053dbff3f04ff72c21f0b7776081b0b08d5c13`.
Historical weights are transferred explicitly; all newly collected rows
must use this current runtime before optimization.

Four stages request 512 rallies each. The fixed opponent order resumes at
index one: imitation 001146, frozen sampled baseline, PPO 225510, then
imitation 001146. This preserves the unfinished opponent sequence from
the stopped run. Training seeds are 1049000–1052000 at a 1000 stride;
development seeds are 1180000–1183000 at the same stride. The objective
is team game wins and all actor outputs are trainable. Export parity,
motor checks, and baseline development remain mandatory at every stage.

Keep the original process 12287 stopped and its unsafe collection unused.
Poll process 13004; do not restart it or edit its dependencies while active.
After completion, the planned paired checkpoints are the original imitation
002944, old-run stage three (PPO 010356), new-run stage two, and new-run
stage four. The first two require explicit historical-policy development
evaluation on the repaired runtime. Do not relabel their old source hashes.
Use the same paired development seeds for all four. Final seeds remain
unused. No model is accepted or installed. The goal is active and incomplete.

### First repaired-runtime model saved; matched comparison prepared — 2026-09-07 01:56 UTC

Process **13004** remains live. Its first collection completed 517 rallies,
18 games, and 57,938 rows in 312.57 seconds. It won 16/18 games against
imitation 001146. Report `competition-20260907-014629.json` passed source,
identity, and motor checks. SHA-256:
`068bc3092704fc4990c0098f178f3fb636a30a218683e5b644f60c17eb3744ea`.

The 228-step game-win PPO update saved
`ppo-20260907-015159/actor.json`, SHA-256
`60f004464cd763c2e612bf009a874b04ac325c13a2c2ae42c1f9c02ab864f6a0`.
It records the repaired runtime source `b7f3c9c8...` and passed 32-case
Unity export parity, with maximum error 0.0000038147. This is a new
current-source checkpoint, not a relabelled historical actor.

Baseline development `competition-20260907-015201.json` completed three
losses in 49 rallies. Scores were [1,11], [11,0], and [2,11]. It took
73.37 seconds. SHA-256:
`23789d3ae99c8bdb37640a77027ada6d2c884da68cf70b0e96aba580f9f3bc9c`.
The completed driver stage passed its export, provenance, and motor gates.
Training wins against the older policy do not establish baseline strength.

The second resumed stage is collecting 512 requested rallies against the
frozen sampled baseline at seed 1050000. It has not yet produced a model.
Do not restart process 13004 or change its dependencies while it runs.

The separate comparison driver now supports an explicit development-only
historical-candidate flag. The default rejects old-source policies before
launch. Opt-in records both the original training source and the current
evaluation source. Completed group reports must agree with those fields.
Three new tests cover default rejection, retained old hashes, and missing
provenance. All 107 Python tests passed. The completed eight-game physical
report 014140 also passed the strengthened source-field checks. No running
training dependency was changed. The final-seed and final-acceptance rules
remain unchanged.

After the four-stage run completes, compare original imitation 002944,
old-run stage three (PPO 010356), and new-run stages two and four with the
same eight development seeds. Use explicit historical-policy permission
for the first two. Do not claim learned improvement from different-seed
training or smoke tests. The goal remains active and incomplete.

### Second resumed model and exact solver rejection — 2026-09-07 02:25 UTC

Process 13004 stopped with exit code 1. Its second update completed before
the stop. Actor `ppo-20260907-020226/actor.json` has SHA-256
`55ade118d55267d265f675356edab684e6ec4e52d808964c5a8c3243366ab916`.
Its critic hash is
`6ca4ea94cc768864837d3e3f3f8609abec58745c99ae05d290b7fc4622f6e0e0`.
The 521-rally training collection lost all 31 baseline games. Its two
development games also lost, with 44 rallies and scores [0,11] and [11,5].
Export parity passed 32 cases, with maximum error 0.0000076294.

The next collection, `competition-20260907-020333.json`, completed 542
rallies, 17 games, and 67,588 rows in 369.95 seconds. It won 12 games against
PPO 225510. Its motor gate rejected one independent paddle step in game
1051014. No optimizer ran on this data. The fourth stage did not start.
Report SHA-256:
`48028199dfa32a2d8a1ac9bf9af3e4faa7f66a7d14ff819053e5dc305a31226d`.

Trace `paddle-commands-20260907-021406.json` reproduced player 0's rejected
step in rally 17, tick 896. It checks all four independent players and uses
the recorded root seed and exact preceding serve draws. Trace SHA-256:
`ca12cc8f232d955ef2680ee4668db4cc5820b113459e0542a24cb3944507ccb6`.
Replay `paddle-replay-20260907-022035.json` reconstructed all 120 frames
with zero position and velocity error under runtime `b7f3c9c8...`.
Maximum acceleration was 100.008286 m/s²; reach was 0.6002594 m. This is
a solver rejection, not the earlier 1002 m/s² physical violation.

The isolated constraint diagnostic found slow convergence where the
acceleration sphere meets the tangential-speed cylinder. After 64
projections, the velocity change was 0.41680956 m/s. The unchanged check
permits 0.41676667 m/s, including its numerical tolerance. With 128
projections, the change was 0.4166788 m/s. The physical limits were not
relaxed. A permanent fixture failed on both ends before this change; all
14 fixture tests passed afterward. The full runtime suite is now running.
The Python suite passed 107 tests, and all 63 baseline files are unchanged.
The prior motor and the red and green fixture reports are retained.

The Game window became readable during the preceding turn. The visible
court had four full-body IK players and a readable per-player HUD. The
scene correctly said UNTRAINED and labelled the physics as provisional.
An actual `I` key press changed `ShowIntent` from true to false while the
paused match stayed at tick 98. Coordinate clicks failed with
`noWindowsAvailable`; direct keyboard input worked. A later input attempt
was interrupted by an external Game-window change. No Space press was
sent, and the later unpause is not attributed to this agent. Space, N,
and R still need actual keyboard checks. No model has been installed.

### Solver repair verified; training and keyboard checks resumed — 2026-09-07 02:34 UTC

Current runtime source:
`85da5a215dfe47d48e1ab3cf1af4efc30a0fcbd1890e1a973b349bd4eb3bc6cf`.
Only the projection iteration cap changed, from 64 to 128. All constraints,
the early exit, movement commands, and acceptance thresholds are unchanged.
All 77 runtime tests and 15 Editor tests passed. Reports are
`inward-convergence-runtime-green-20260907-0229.json` and
`inward-convergence-editor-green-20260907-0228.json`. Report contents carry
the actual test timestamps; the runtime report filename minute is approximate.

Full diagnostic game `paddle-commands-20260907-022829.json` completed 38
rallies with no rejected steps, score [11,7], and winner 0. It used the same
training game seed 1051014 and recorded serve stream. Maximum acceleration
was 100.030075 m/s², paddle speed 8.98434 m/s, and reach 0.609304547 m.
All four players had bounded steps. SHA-256:
`4c07f08a0b6f15bf7ec17ca1aa136742a3f05c513b80d5ceb9c537cff8fc8e67`.
This changed-runtime diagnostic is not held-out strength evidence. The
historical replay flag was reset to false after completion.

New local training process 16802 is active. Its driver is
`training-loop-20260907-023200/progress.json`. It starts from the checked
actor and critic of PPO 020226. Two 512-rally stages use saved PPO 225510
and imitation 001146 in that order. Training seeds are 1051000 and 1052000;
development seeds are 1182000 and 1183000. The earlier rejected collection
is preserved and is not optimized. The new source and opponent snapshots
are stored with the driver. The objective remains all-heads game-win PPO.
No final evaluation seeds have been used and no policy has been accepted.

Actual keyboard checks now pass with the Game view focused. Space paused
the match at tick 393 and world time 1.63750768. R entered the saved
216-frame replay. Space advanced replay time to 5.95594835 seconds without
changing the live tick or world time. R exited replay. N created a new
match and advanced the interactive seed from 1300001 to 1300002. I hid
the intent display and a second I restored it. An R press made while the
Scene view had focus did not affect the game. This is a focus requirement,
not proof that the replay control failed.

Audit: `game-controls-20260907-0233.json`. Screenshot:
`game-controls-20260907-0233.jpeg`, SHA-256
`9c3ce28ead9cf33608ec8ae8053cde27cb2f6e2497a6b5b67dfc0a3546653d19`.
The screenshot has a readable HUD, four full-body IK players, and the
UNTRAINED/provisional labels. It shows the control probe at game end, not
an accepted trained model. Repeat the visual check after final installation.

### Two repaired-runtime updates complete; paired comparison active — 2026-09-07 02:50 UTC

Process 16802 completed with exit code 0. Its driver
`training-loop-20260907-023200/progress.json` records two completed stages.
Runtime source remains `85da5a215dfe47d48e1ab3cf1af4efc30a0fcbd1890e1a973b349bd4eb3bc6cf`.

First collection: `competition-20260907-023201.json`, 538 rallies,
18 games, 12 wins, and 66,330 rows in 384.20 seconds. It used saved PPO
225510 as the opponent. SHA-256:
`f745b183f139e96c10adcfdfebfea2edf396b8bdc6074ec492b4207c5714bea1`.
Its 260 optimizer updates saved `ppo-20260907-023841/actor.json`, SHA-256
`4f438e79d27600486fd6409c79880d2228407dc9ccf93fb70f17656209c04a58`.
The 32-case export check passed with maximum error 0.0000038147.
Development report `competition-20260907-023843.json` lost both games,
scores [0,11] and [11,1], in 35 rallies. Report SHA-256:
`c4d16ef34ed92b80bc8bcb3de4cc906b256a7a5fd00259f089d4fdaa35ab02ac`.

Second collection: `competition-20260907-023937.json`, 539 rallies,
19 games, 15 wins, and 62,390 rows in 355.14 seconds. It used imitation
001146 as the opponent. SHA-256:
`4cc3a2b51cf2987bf8ac705d0e045ee4f05088b00a0535653a5b3aa693f3790d`.
Its 244 optimizer updates saved `ppo-20260907-024551/actor.json`, SHA-256
`da2544573e7130279592b9d03e3ba4b219484095e5ba5e828ac1ac90a9701e8d`.
The 32-case export check passed with maximum error 0.0000038147.
Development `competition-20260907-024553.json` lost both games, scores
[1,11] and [11,5], in 42 rallies. SHA-256:
`617625f284cfb649276c51f65a093fb9c2148bcdcebea8366ccfe1523fd88a07`.

An audit found that the training-data validator checked candidate motor
metrics but omitted saved-actor opponent metrics. A new test reproduced
20 unsafe-opponent cases that were not rejected. After process 16802
finished, the validator was changed to check all four independent players
for the `older actor / sampled` mode. The two original baseline modes still
check only the candidate; their original motor is unchanged. All 109 Python
tests pass. The four completed reports above pass the strengthened validator.
No running training code was changed. The prior validator is preserved at
`player_ppo-before-opponent-gate-20260907-0247.py`; the updated file hash is
`e37664a67d247de653d176bb9d59d990101c83a71ce3f53f44ef536d0dfb9298`.
All 63 baseline files and the Unity runtime source are unchanged.

Coverage `coverage-20260907-024809.json` completed all 48 cases and passed
source, actor, script, and four-player motor checks. PPO 024551 made 11/16
contacts and eight legal landings. The teacher made 12 contacts and 10
landings. Movement-disabled controls made no contact or legal landing.
Coverage report SHA-256:
`6b8bdc6680aa704b51b1db92ea9c0e7cb5d3fa781ef1d073dc7f0df438bfa35c`.
This is useful coverage evidence, not proof of winning match play.

Comparison process 95740 is active. Driver:
`model-comparison-20260907-024859/progress.json`. It compares imitation
002944, PPO 010356, PPO 020226, and PPO 024551 under the same eight seeds,
1141000–1141007. The first three explicitly retain historical training
source hashes; all are evaluated under current runtime source 85da5a21.
Each actor plays both court ends, both baseline modes, and swapped player
identities. The first run is `development-evaluation-20260907-024901`.
Do not start another collector or change its dependencies while it runs.

No final evaluation plan exists. The 80-game final block remains unused.
No policy is accepted or installed. If matched baseline performance remains
poor, use the comparison to choose the next curriculum parent. More training
wins against an older opponent alone do not meet the goal.

### Matched comparison complete; rally curriculum and temporary preview — 2026-09-07 03:07 UTC

Process 95740 completed with exit code 0. All 32 scheduled development
games completed. Each model played seeds 1141000–1141007 under runtime
source 85da5a21, across both ends and both baseline modes, with identity
swaps. The completed reports passed a second provenance, identity, and
motor verification. Driver progress SHA-256:
`988d036410882ec7d441bd859a660871ac7b15343757e08621b567deb2c0b560`.
Historical training source hashes are retained, not replaced.

| Model | Game wins | Rally wins | Near-end rally wins | Far-end rally wins | Legal returns |
| --- | --- | --- | --- | --- | --- |
| Imitation 002944 | 0/8 | 33/153 | 29/98 | 4/55 | 391 |
| PPO 010356 | 0/8 | 51/174 | 32/99 | 19/75 | 380 |
| PPO 020226 | 0/8 | 29/138 | 13/67 | 16/71 | 275 |
| PPO 024551 | 0/8 | 36/156 | 16/74 | 20/82 | 314 |

Completion reports, in table order, are in development-evaluation folders
024901, 025251, 025639, and 025948 on 20260907. Their completion hashes are:

- `da75e931f0b34096c59e5903ec1815ed7d42b0cf36914fd51f3393b205070b1a`
- `c94116ba6daba3667e445e1b9deef098c63cc7734765f8bfb8799ce9213afa13`
- `067a2ff1c1123fb75c66786d00f4a954804e393343b8c48858a1652bd852faef`
- `5050777c3896d2896c737cf6eba66e725d88dca0d5a6da8c80c4ec4894b1c48f`

PPO 010356 is the next training parent. Its overall rally-win rate is
29.3%, and its weaker-end rate is 25.3%, the highest of these four models.
This is model selection from development data, not final acceptance.
Its current-runtime coverage report `coverage-20260907-030419.json`
completed 48 cases: 11 learned contacts and nine legal landings in 16
fixtures, versus no contact with movement disabled. The teacher made 12
contacts and 10 landings. Original actor source 7a04ba2e is recorded as
historical; evaluation uses source 85da5a21.

New local process 34958 is active. Driver:
`training-loop-20260907-030543/progress.json`. The run requests four
256-rally updates against the frozen sampled baseline, with all action
heads enabled. Training seeds are 1053000, 1054000, 1055000, and 1056000.
Development seeds are 1184000, 1185000, 1186000, and 1187000. Each collection
still finishes a complete game. No previous development data is used for
optimization. The source and training files are snapshotted by the driver.

This is an explicit rally-win curriculum step with full-rally credit
(gamma and lambda both 1), not a change to final acceptance. The value
model starts fresh because the target is now a rally result, not a game
result. The actor starts from the selected PPO weights. It gives the actor
positive and negative feedback from individual baseline rallies, instead
of only the all-loss complete-game outcomes observed so far. Return to
game-win training after this curriculum shows useful progress. The frozen
80-game final game-win test and all physical limits remain unchanged.

The visible Game view now uses a temporary, deterministic PPO 010356
preview, with four independent runtime players. The runtime TextAsset is
named `EXPERIMENTAL PPO 010356 - not accepted` and has `DontSave` flags.
The saved scene file hash is unchanged. Interactive game seed 1300002 is
in use; the next seed field is 1300003. Snapshot
`experimental-preview-20260907-0306.json` records distinct player actions,
identities [0,1,2,3], six rallies, score [0,5], and no infeasible motor step.
Maximum body acceleration is 14.0138292 m/s², paddle acceleration
100.011726 m/s², and reach 0.6092755 m. This is a short preview, not a
complete match acceptance test.

Image `experimental-preview-20260907-0306.png` shows the court, net, four
full-body IK players, paddles, and intent lines. The Unity camera capture
does not include the HUD, so it is not new HUD proof. The earlier actual
keyboard/HUD audit remains separate. No accepted model has been installed
or saved into the scene. The goal remains active and incomplete.

### Rally curriculum complete; fixed comparison active — 2026-09-07 03:30 UTC

Process 34958 ended with exit code 0. Its four-stage driver is complete:
`training-loop-20260907-030543/progress.json`, SHA-256
`0b4903b8a755a73c2fb3f090985f71deb6157527e6a95bbb9f7a30c6f120a58e`.
Do not restart this training run. Runtime source remains `85da5a21...`.

| Stage / saved PPO | Training rally wins / rallies | Training games | Development rally wins / rallies | Development games |
| --- | ---: | ---: | ---: | ---: |
| 1 / 031111 | 46/258 | 15 | 10/37 | 2 |
| 2 / 031633 | 57/256 | 14 | 5/45 | 3 |
| 3 / 032230 | 46/258 | 15 | 15/48 | 2 |
| 4 / 032812 | 50/266 | 16 | 7/32 | 2 |

All games in this table were losses. Collection ends at a complete game,
so the requested rally count can be exceeded. The four training collections
contain 263,808 decision rows and took 1,100.23 seconds in total. These are
local collection measurements, not evidence of improved playing strength.
No cloud run was started.

All eight report hashes and four actor hashes match the completed driver.
All reports passed a repeated current-source, completion, and motor check.
Each saved actor passed 32 Unity/Python parity cases. Maximum output error
was at most 0.0000076294. The Python suite passed 109/109 tests again.
All 63 baseline files are unchanged. No runtime code changed in this turn.

The new fixed comparison is active in process session **14117**:
`model-comparison-20260907-033013/progress.json`. It evaluates PPO 031111,
031633, 032230, and 032812 in that order. Each model uses development seeds
1141000–1141007, both court ends, both baseline modes, and identity swaps.
The first run is `development-evaluation-20260907-033015`. The models all
have the current source hash; historical-candidate permission is not used.

The parent reference was verified again with the same comparison verifier:
`development-evaluation-20260907-025251`. PPO 010356 lost all eight games,
won 51/174 rallies, and made 380 legal returns. Its original training source
is retained. Its completion hash is
`c94116ba6daba3667e445e1b9deef098c63cc7734765f8bfb8799ce9213afa13`.
Reuse this current-runtime reference. Do not repeat its games without cause.

The contact-controller review made no changes. The old residual fit is for
the baseline motor, and the low-contact fallback uses neutral residuals.
Earlier speed and run-up trials failed to improve contact accuracy. Do not
repeat those trials or increase physical limits without new evidence.

Next: finish session 14117 and compare all four results with the verified
parent. Then select the next training or contact-diagnosis step from those
results. Keep runtime and collector code fixed while the comparison runs.
Final acceptance seeds remain unused. The temporary learned preview is
not a permanently installed or accepted model. The goal remains active.

### Comparison and contact diagnostics — 2026-09-07 03:52 UTC

Process 14117 ended with exit code 0. Driver
`model-comparison-20260907-033013/progress.json` is complete, SHA-256
`b294a1af6bdb731c12ea2c0d012774aec08a019fc1f6db0b301e0c9866df2b7e`.
All four runs passed a second artifact, identity, schedule, and motor audit.
The runtime and comparison dependencies stayed unchanged throughout.

| Model | Game wins | Rally wins | Near end | Far end | Legal returns |
| --- | --- | --- | --- | --- | --- |
| PPO 010356 parent reference | 0/8 | 51/174 | 32/99 | 19/75 | 380 |
| PPO 031111 | 0/8 | 45/171 | 27/92 | 18/79 | 372 |
| PPO 031633 | 0/8 | 40/160 | 20/81 | 20/79 | 331 |
| PPO 032230 | 0/8 | 55/184 | 28/97 | 27/87 | 352 |
| PPO 032812 | 0/8 | 52/178 | 37/110 | 15/68 | 406 |

PPO 032230 is retained for the next contact diagnosis. Its rally-win rate
is 29.9%, versus the parent's 29.3%. Its weaker-end rate is 28.9%, versus
25.3%. These small development differences do not establish improved
match performance. The final child made more returns but had poorer
far-end results. No model is accepted or permanently installed.

The four new evaluation folders end in 033015, 033404, 033732, and 034122
on 20260907. Their completion hashes are:

- `d3fa7dcbacad8c6aa103bdb100f26a6fccf4dcd090c18042d836adab8f16a142`
- `827021a20402226b259fcf3354bbf58fc0687fe96e46c6c7bdcdfdc15e5d9f90`
- `b4d51381f361600a9e099f70d7f8ae25a3ce6dbbc05ed808ca7f70f9083034d3`
- `f245961dc81286ac175e797d6a42eb3401e085a650299ec1d93bcc97f2c00c27`

Added a read-only execution summary to `scripts/player_contact_outcomes.py`.
It separates physical contact surfaces from legal shots, reports signed
spin using the existing diagnostic thresholds, and measures contact delay,
normal speed, and landing depth error. Missing trace fields are not zero
measurements. Mirror, surface, missing-data, and finite-value tests pass.

Added `scripts/player-contact-fit-probe.cs` and its Python verifier. The
48 paired cases use fixed feet, three shot types, four starting depths,
and both court ends. They compare the original fit with neutral residuals.
Player colliders are disabled only after a legal hit to isolate its flight.
These are injected fixtures, not learned-player or match-strength evidence.
The test does not edit a scene, train a model, or replace an asset.

Report `contact-fit-probe-20260907-034600.json` has SHA-256
`4618c4ac36e04c58ee7beae03d69837997fa5b41d4b026588f146d1b098264ed`.
All 48 cases passed speed, acceleration, reach, angular speed, and no-foot-
movement checks. The frozen fit made 10/24 legal landings; neutral settings
made 8/24. Both made 14 legal hits. Neutral residuals are not selected.
The sibling `.audit.json` retains the verified summary. The collector
snapshot is also retained. Python tests reached 121/121 at this point.

Fresh learned-player trace `contact-outcomes-20260907-034700.json` used PPO
032230 and development seeds 1150000–1150003. It completed 63 diagnostic
rallies in 69.68 seconds. Two games were losses; two stopped at the stated
16-rally limit and are not scored as wins or losses. Its source, artifact,
ownership, and motor checks passed. Report SHA-256:
`3725f62bef37d01910291f5ae834385b973f649fb864397913ba42190df34e96`.

It recorded 144 legal shots: 99 legal landings, 24 opponent interceptions,
10 candidate WrongSide faults, nine BodyContact faults, one Carry fault,
and one DoubleHit fault before landing. Mean planned landing error was
1.566 metres. The 38 landed deep-right flat shots averaged 2.314 metres
short. Across all 64 deep-right flat hits, mean planned normal speed was
6.834 m/s, actual normal speed was 5.105 m/s, and contact delay was 0.02224
seconds. Of 67 deep flat hits, 63 used the upright plan and four used the
low-contact fallback. These measurements do not alone prove a cause.

The next trial tests an upright flat-face pitch correction of -3 degrees.
This rotates the face upward relative to the frozen fit. The external
contact collector now uses a separate candidate contact object and retains
the original object for the baseline. It records every candidate parameter
and marks nonzero offsets as experimental. The verifier allows only the
reported flat-pitch change; four new tests reject hidden changes, missing
labels, and invalid offsets. All 125 Python tests pass.

Active diagnostic: `contact-outcomes-20260907-035228.json`, PPO 032230,
seeds 1150000–1150003, offset -3 degrees. Its callback is `TickContactOutcome`;
status is in `Picklebot.ContactOutcome.Status`. Poll this same callback.
Do not change the active collector or runtime until it ends. Restore the
SessionState flat-pitch offset to zero after the trial. No runtime change
or accepted contact fit has been made. Final seeds remain unused.

### Angle trials complete; full-game correction test active — 2026-09-07 04:01 UTC

Both angle diagnostics completed and passed source, artifact, contact-
parameter, and motor checks. They used the same PPO 032230 weights and
development seeds 1150000–1150003 as the unmodified contact reference.
The games diverge after contacts, so landing averages are not measurements
of identical incoming shots. No causal or match-strength claim follows
from the aggregate contact counts alone.

| Flat pitch offset | Legal shots | Legal landings | Opponent interceptions | Candidate faults before landing | Mean planned landing error | Deep-right flat depth error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 degrees | 144 | 99 | 24 | 21 | 1.566 m | -2.314 m (38 landings) |
| -3 degrees | 139 | 95 | 38 | 6 | 1.473 m | -2.164 m (26 landings) |
| -6 degrees | 101 | 72 | 10 | 19 | 1.501 m | -2.125 m (25 landings) |

Negative pitch offset rotates the upright flat face upward. The -3-degree
trial recorded six WrongSide faults and no other candidate fault after a
legal hit. The -6-degree trial recorded 12 WrongSide, four BodyContact,
two Out, and one Lost fault. Both trials stopped after 16 rallies in all
four games. None of those partial games is counted as a win or loss.

The -3-degree report is `contact-outcomes-20260907-035228.json`, SHA-256
`dc45fa12572886a7d795fcce6e74632446df1a909c2fe3c54ec8007d48426dee`.
The -6-degree report is `contact-outcomes-20260907-035505.json`, SHA-256
`2e24259a10dea128fad130867d2e1c17b3504fab853bba1c84f44096ac090c58`.
Both have retained `.audit.json` summaries and collector snapshots. The
contact-diagnosis SessionState offset was restored to zero after each run.
No temporary contact object was saved into the game scene or baseline.

Added a bounded development-only contact option to the full-game runner
and comparison driver. The frozen baseline retains its own unmodified
contact object. The candidate correction and every candidate contact
parameter are frozen into the schedule and copied into each report. The
verifier requires the reported correction to match the requested value.
The driver explicitly sets zero when no correction is requested and
restores zero after a completed experiment.

Final evaluation rejects a nonzero contact correction before it reserves
seeds or starts simulation. A live negative check at 04:00 UTC returned
the expected error: `Contact overrides are bounded development experiments,
never final evaluation.` The callback remained absent. Development mode
and zero offset were restored. The independent final verifier also rejects
experimental corrections. All 128 Python tests pass. All four completed
unmodified-contact references still verify identically with the new checks.
The final protocol and all physical limits are unchanged. No final plan
exists, and all 63 frozen baseline files still match their manifest.

Active process: **86820**. Driver:
`model-comparison-20260907-040114/progress.json`. Active full-game report
folder: `development-evaluation-20260907-040117`. It uses PPO 032230,
offset -3 degrees, and development seeds 1141000–1141007. Both court ends,
both baseline modes, identity swaps, and complete-game caps are unchanged.
The comparison reference is the same actor's unmodified-contact run
`development-evaluation-20260907-033732`: zero wins in eight games,
55/184 rally wins, and 352 legal returns.

Poll this exact process. Do not edit the active runner, its Python
dependencies, or runtime code until it ends. This run cannot train,
promote, or install a model. If it improves full-game results, verify that
result before implementing a controller correction and collecting fresh
training data. If it fails, retain the failure and use the measured contact
limits to choose the next change. The goal is active and incomplete.

### Angle correction rejected; kitchen contact repair — 2026-09-07 04:15 UTC

Process 86820 ended with exit code 0. The complete eight-game correction
test passed the repeated source, artifact, identity, motor, and explicit
override checks. Driver progress SHA-256:
`af3d0ad96faf3e3310f2f84150170bdb231d319c13849dcf0953cae1aa8039ad`.
Completion SHA-256:
`e372778272883f84041a5842de3e4f5a3e6e127668401a2e4f85cfdb81279352`.

| PPO 032230 contact setting | Game wins | Rally wins | Near end | Far end | Legal returns |
| --- | --- | --- | --- | --- | --- |
| Unmodified | 0/8 | 55/184 | 28/97 | 27/87 | 352 |
| Temporary -3-degree flat pitch | 0/8 | 40/163 | 18/77 | 22/86 | 329 |

Reject this correction. The short contact diagnostic did not transfer to
better full-game results. No angle correction was added to runtime code.
The driver restored the final-runner development offset to zero. All
angle trials and their failed full-game comparison remain retained.

Code review then found a different limitation. Both the original planner
and the independent low-contact fallback required contact at least 2.65 m
from the net. The fallback kept that limit after a bounce. However, the
existing game rules permit groundstrokes in the kitchen after a bounce.
Their existing `KitchenVolleyIsFault` and `KitchenGroundstrokeIsLegal`
tests keep the two cases separate. The baseline rules are not changed.

New isolated probe `scripts/player-kitchen-contact-probe.cs` uses both ends,
fixed feet at depths 1.7, 2.1, 2.3, and 2.7 m, three shots, and fitted versus
neutral contact settings. The ball starts at canonical [1.2,1.2,0.4] with
velocity [0,1.2,-3] and zero spin. The report records physical bounce
events and whether the player's feet are in the kitchen at the legal hit.
It is an injected diagnostic, not policy training or match acceptance.

Before repair, `kitchen-contact-probe-20260907-040750.json` completed all
48 cases: four legal hits and zero legal landings. Every case selected a
plan, but the planner waited for a contact outside the kitchen region.
All physical limits and the no-foot-movement check passed. Report hash:
`46b8819087207bd6b1abe31a0465934c7237926403833d988396860c1aede407`.

Added `BouncedKitchenBallHasAReachableLowContactPlan` for players 0 and 2.
Both failed on the old code: the chosen depth was 2.65397382 m, not inside
the 2.1336 m kitchen. The exact failures are retained in
`kitchen-contact-red-20260907-0411.json`. The old planner and privileged
teacher source files are also retained with the `before-kitchen` name.

The low-contact planner now allows a minimum contact depth of 0.4 m after
an observed or forecast bounce. Its reach estimate uses the corresponding
0.38 m body-depth bound. The unbounced volley region is unchanged. The
planner still supplies no movement action. The privileged diagnostic
teacher uses the new reachable feet target only for these kitchen plans;
runtime actors must still choose their own movement.

Both new plan tests pass, as recorded in
`kitchen-contact-plan-green-20260907-0413.json`. Current runtime source is
`7a998e12dc7353359861a12f5197842cf24a0f62dc61baa5dc22858cd9fad845`.
All previous actor training hashes remain unchanged and are now historical.
No fresh policy or final evaluation has run on the new source.

The full `Picklebot.PlayerAgents.PlayTests` run started at 04:13:50 UTC
and is still active in `Temp/pipeline_test_status.json`. Do not start a
second test runner or edit runtime files until it ends. After that, run
the Editor/rule tests and repeat the physical kitchen probe. Actual legal
returns, full regressions, and fresh training remain unverified. Stopping
Play for the tests removed the temporary live preview; it must be restored
after validation. No saved scene or baseline model was changed.
