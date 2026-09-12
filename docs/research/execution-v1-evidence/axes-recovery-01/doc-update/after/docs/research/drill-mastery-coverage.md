# Drill-mastery coverage audit

12 September 2026. Read-only audit during the smooth-placement experiment. No new rollouts, training, thresholds or final-seed allocations. This is a bounded review of the most directly relevant saved evidence, not a search for the maximum historical score.

## Current 256-reset screen

The screen contains 16 fixed serves, 16 required-bounce receiving feeds, 112 airborne rally feeds and 112 bounced rally feeds. It replays each reset with target A, target B and random targets. These are 256 base resets, not 768 independent situations. The first 124 observation values identify only 150 distinct initial observation vectors in the saved initializer inputs.

- Fixed serves cover all four player seats and both service sides, with two repeats per seat/side. Different seeds repeat the fixed geometry; this is not 16 randomized serving situations.
- The 32 familiar rally cases have movement range zero. The 64 court-pattern rehearsal cases use range fractions .025/.05/.075/.1 of the displacement from the initial paddle face toward the nine-point court grid.
- The 128 focused cases use local lateral range fractions .00625/.0125/.01875/.025. The local-pattern extent is 4 m, so these specify only 2.5/5/7.5/10 cm of nominal feed displacement. There are 80 left and 48 right cases. A nominal feed displacement is not measured player travel or proof that footwork was required.
- Incoming timing and initial body-position variation are zero. The current screen cannot establish broad movement generalization.
- Initializer legality is 228/256: serve 16/16, receive 13/16, air 96/112, bounced rally 103/112. All 96 legal airborne-feed returns were recorded as actual volleys; 102/112 airborne attempts made volley contact. An airborne reset label should still be checked against actual contact mode in future candidates.

Source: `PlayerRecoveryScheduleV3.For`, `PlayerInterleavedRecoveryV3.Index`, `PlayerMovementPatternV3`, and the saved `two-regions-01/evaluation/ExecutionV1Initial/A` records.

## Requirement-to-evidence map

| Mastery requirement | Existing physical mechanism | Most useful saved baseline/reference | Coverage gap |
|---|---|---|---|
| Fixed-ball legal serves on both sides | `stationary-serve`, `FixedServeSides=both`; service landing remains rule-checked | Current initializer 16/16 on eight seat/side combinations. Historical `rally-feed-02-final-dev` also records 64/64 legal serves, but its source/model differ. | Current fixed poses establish repeatability, not robustness to varied initial body or ball arrangements. Keep the user-approved fixed-ball convention; do not reintroduce release timing. |
| Receive after the required bounce | `receive-feed` calls `InitializeReceiveFeed`; an incoming ball starts before its physical bounce. `StepReceiveServe` accepts contact only after the rules reach return flight. | Current initializer 13/16. Historical `receive-varied-selection-01/verification.json` has 53/72 varied successes for selected checkpoint 2818023; `rally-feed-02-final-dev` reports 145/200 quarter-difficulty returns and 200/200 easy returns. | Very few cases here, mostly familiar/easy geometry. Need varied lateral/depth/speed feeds and receiver/service contexts. A rally-bounce feed is not a substitute for the mandatory-bounce rule situation. |
| Legal airborne rally returns, including kitchen restrictions | `rally-air-feed` establishes volley eligibility through reset history; incoming trajectory is physical. `StepRallyFeed` waits for outstanding volley momentum to settle and rejects learner faults. | Current initializer 96/112 legal volleys. Historical `rally-feed-02-final-dev`: 64/64 familiar, 51/64 varied legal volleys. | Kitchen enforcement exists in code, but the current reset distribution does not deliberately challenge kitchen-line contact, entering the kitchen after a volley, or opting to let the ball bounce. Rule tests prove enforcement, not learned avoidance. |
| Lateral, deep and shallow movement with positioning | `InitializeMovementRallyFeed`; patterns `lateral-left/right`, `depth`, `axes`, `local`, and nine-region `court`; optional timing/start variation | Same-lineage `swing-recovery-selection-01/selection.json` selected parent 8415374. Legal air/bounce counts: focus 121/128 and 128/128; bridge 72/128 and 102/128; lateral 27/128 and 50/128; court legacy 90/128 and 99/128. These demonstrate difficulty dependence, not mastery. | Current local focus stops at 10 cm. Broader left/right, explicit shallow/deep axes, diagonal court locations, independent start positions and flight times remain underrepresented. Success on a shifted feed may come entirely from arm adjustment. |
| Follow requested target regions | Execution goal observations, legal-landing target feedback, matched A/B evaluation with recorded landing coordinates | `two-regions-01/audit/analysis.json`: parent A/B/random hits 117/4/75; candidate 100/26/66 out of 256 each. Candidate assignment gain -0.02148, 95% interval [-0.046875, .00390625]. | Positive useful target-directed response is unproven. Aggregate B improvement alone does not establish conditioning. The later smooth-distance screen also failed target following; see the smooth-distance report. Neither result establishes physical infeasibility. |

Historical results are useful references for constructing evaluations; they are not current-checkpoint acceptance. Different source identities, feed versions, action contracts and selected checkpoints must stay explicit. The legacy parent's reported `movingReturns=0` means no successful return met that collector's **at least 0.5 m root displacement** criterion; it does not mean the player never moved at all.

## Compact later battery

Use one frozen executor across every part. Preserve the existing 256-reset recovery screen as a regression anchor, and add a deliberately balanced development battery rather than multiplying the same familiar cases.

1. **Serve fixture:** the eight canonical seat/side combinations, with both legal target requests. Count distinct geometry separately from repeats. Any broader initial-position robustness claim requires a separately checked reset-only variation fixture; one was not established by this audit.
2. **Required-bounce receiving:** a balanced 128-reset screen spanning all seats, receiver/service contexts and distinct incoming lateral/depth/speed combinations from the existing supported feed distribution. Record whether the mandatory incoming bounce occurred, actual contact legality and final landing. Choose cases by reset parameters before observing policy success.
3. **Volley and kitchen behavior:** familiar and varied air feeds plus a compact, explicit kitchen-boundary cohort. Include both a volley-eligible situation and a corresponding situation where the player must wait for a bounce. The boundary cohort needs an explicit validated evaluation fixture; existing rule/momentum tests alone do not supply learned-policy evidence. Report actual legal volleys, legal bounced returns and kitchen/momentum faults separately.
4. **Positioning:** a balanced grid over left/right/shallow/deep, airborne/bounced feed, all seats, and declared movement-distance bands. A first bounded screen can use 256 cases, for example four seats × four directions × two contact modes × two distance bands × four distinct resets. Retain known 10 cm cases, but include previously measured 20–40 cm conditions and later feasible wider court-grid cases. These are coverage suggestions, not acceptance thresholds. Verify reset feasibility first, report actual nominal displacement in meters, and record root travel/contact displacement rather than assuming that a range parameter measures footwork. Independently vary starting position and time-to-contact in a subsequent stress subset.
5. **Target conditioning:** apply paired A/B instructions to the selected physical cases instead of inventing extra identical scenarios. Retain random-area checks. Use unconditional legal/target rates and assignment gain across all pairs; report signed landing shifts with the both-legal denominator. Do not count smooth nonzero bonus as a target hit.

This can be staged to avoid an expensive Cartesian product: first inspect a few preselected successes/misses for each new reset family, validate the fixture, then run the frozen compact battery. A fixture-preview run is separate from a performance-based case-selection process. Do not remove hard valid cases after seeing failures.

For eventual mastery, predeclare per-skill and per-variation criteria and non-regression tolerances, then choose sufficient independent development/final coverage for those criteria. Report uncertainty and reset duplication. Independent training replications and fresh development cases are separate from deterministic replay. Only then freeze a candidate and use untouched final seeds. One easy 100% cell, or a high pooled average, cannot close the active mastery goal.

## Audit references

- [Active milestone](F:/dev/picklebot/docs/DRILL_MASTERY_GOAL.md)
- [Current placement analysis](F:/dev/picklebot/artifacts/hierarchy-v1/two-regions-01/audit/analysis.json)
- [Current initializer episodes](F:/dev/picklebot/artifacts/hierarchy-v1/two-regions-01/evaluation/ExecutionV1Initial/A/episodes.jsonl)
- [Recovery schedule](F:/dev/picklebot/Assets/Picklebot/PlayerLearning/PlayerRecoveryScheduleV3.cs)
- [Movement pattern definitions](F:/dev/picklebot/Assets/Picklebot/PlayerControlsIntegration/PlayerMovementPatternV3.cs)
- [Physical feed constructors](F:/dev/picklebot/Assets/Picklebot/PlayerControlsIntegration/PlayerLearningMatchV3.cs)
- [Contact and legality checks](F:/dev/picklebot/Assets/Picklebot/PlayerControlsIntegration/PlayerContactDrillV3.cs)
- [Selected ancestor's movement results](F:/dev/picklebot/artifacts/player-v3/swing-recovery-selection-01/selection.json)
- [Larger historical movement confirmation](F:/dev/picklebot/artifacts/player-v3/movement-progressive-confirm-dev-01/review.json): 2,048-case comparison exposed a moving-air regression (305→279/512), demonstrating why small aggregate screens need confirmation.
- [Historical varied-receiving selection](F:/dev/picklebot/artifacts/player-v3/receive-varied-selection-01/verification.json)
- [Historical rally-feed evaluation](F:/dev/picklebot/artifacts/player-v3/rally-feed-02-final-dev/verification.json)
- [Legacy moving-return metric definition](F:/dev/picklebot/research/critic-key-comparison/workflow/local_movement_sequence.py)

## Fresh placement follow-up

The [fresh comparison](execution-v1-fresh-placement.md) completed both frozen models on a newly reserved 256-reset cohort under the same recipe. It contained 150 unique initial physical observations; 194 resets (90 unique observations) matched the earlier anchor and 62 resets (60 unique observations) differed. Nearest-prior feature differences and both reset-weighted and equal-unique-observation estimates are preserved in the analysis. This does not establish unseen-training generalization.

The candidate's overall assignment gain was positive, but the exact-novel subset interval included zero. The full screen failed: A accuracy remained lower and required-bounce receiving A changed 14/16 to 13/16. All broader coverage gaps above remain open. The next prepared fixture uses existing standalone axes movement at nominal 25/50/75/100 cm, with recovery interleaving disabled; it is a proposal, not completed evaluation evidence or proof that footwork is required.


## Wider movement follow-up

The [512-reset diagnostic](execution-v1-wide-movement.md) completed paired A/B evaluations for both the initializer and current executor. Reset-only inspection covered all 32 direction/distance/feed cells, with 174 distinct initial physical observations. Two of 128 cells including player seat were absent. These are development probes, not final acceptance tests.

The 256 directional challenges use nominal 25/50/75/100 cm feeds in all four directions. Current A legality is 38/256: left 3/66, right 0/64, shallow 19/62 and deep 16/64. Distance results are 31/64, 7/64, 0/64 and 0/64. Only 69/256 attempts made accepted contact. Actual contacts distinguish volleys from bounced returns; the remaining 187 attempts had no accepted contact. Root travel exists but does not establish useful positioning or natural movement.

Wide target assignment gain was -0.00586, interval [-0.015625, 0.001953125]; aggregate target responsiveness came from familiar cases. No wide target-following claim is supported. The next proposed focus spans 6.25–25 cm left/right/shallow/deep while keeping familiar and prior-court rehearsal. Wider probes remain for transfer measurement; mandatory-bounce variations and deliberate kitchen behavior still require separate coverage.

## Graded movement continuation: final follow-up

<!-- axes-recovery-final-status -->

The [fixed 2,097,159-experience endpoint](execution-v1-axes-recovery-final.md) completed the two preserved batteries: narrow 256 base resets under A/B/random and wide 512 under A/B. The new focus trained 6.25–25 cm nominal left/right/shallow/deep shifts; the retained narrow evaluation recipe stays lateral and the standalone wide recipe disables recovery. Full initial physical and goal observations matched the historical comparisons.

Previous endpoint → final narrow legality: A **234 → 234 / 256**; B **235 → 233 / 256**; random **235 → 233 / 256**. Narrow target hits: A **96 → 68 / 256**; B **33 → 28 / 256**; random **77 → 72 / 256**.

Across the 256 axes challenges, legal returns changed A **38 → 41 / 256**; B **40 → 36 / 256**; target hits changed A **9 → 12 / 256**; B **5 → 3 / 256**.

| Nominal 25 cm direction | A: legal; targets (previous → final) | B: legal; targets (previous → final) |
|---|---:|---:|
| Left | 3 → 3; 0 → 0 (each / 19) | 5 → 3; 0 → 0 (each / 19) |
| Right | 0 → 0; 0 → 0 (each / 15) | 0 → 0; 0 → 0 (each / 15) |
| Shallow | 19 → 17; 9 → 10 (each / 19) | 17 → 11; 3 → 0 (each / 19) |
| Deep | 9 → 9; 0 → 2 (each / 11) | 11 → 8; 2 → 3 (each / 11) |

| Wider transfer distance | A legal / targets / attempts: previous → final | B legal / targets / attempts: previous → final |
|---|---:|---:|
| 50 cm | 7 / 0 / 64 → 10 / 0 / 64 | 7 / 0 / 64 → 9 / 0 / 64 |
| 75 cm | 0 / 0 / 64 → 2 / 0 / 64 | 0 / 0 / 64 → 5 / 0 / 64 |
| 100 cm | 0 / 0 / 64 → 0 / 0 / 64 | 0 / 0 / 64 → 0 / 0 / 64 |

| A/B assignment gain, final minus previous endpoint | Reset-weighted estimate [pointwise 95% interval] | Equal-observation-cluster estimate [pointwise 95% interval] |
|---|---:|---:|
| Narrow all | -0.05859 [-0.10547, -0.00977] | -0.03333 [-0.09333, +0.02333] |
| Wide all | -0.04492 [-0.06934, -0.02051] | +0.02874 [-0.00575, +0.06322] |
| Wide axes challenges | +0.01758 [+0.00000, +0.03711] | +0.01587 [-0.00794, +0.04365] |

Against the initializer, the existing narrow screen **failed**; 2 drill/condition legal-retention point estimates exceeded the 5 percentage-point loss limit. Against the previous endpoint, the existing narrow screen **failed**; 1 drill/condition legal-retention point estimates exceeded the 5 percentage-point loss limit. These are development checks, not mastery or statistical noninferiority guarantees.

These counts do not close the coverage gaps above. Nominal shift is not body travel, each A/B condition reuses the same physical cases, and the player/direction/feed joint cells remain sparse. The 50–100 cm tests probe beyond the trained focus. Actual bounce and volley contact flags, accepted-contact root displacement and no-contact travel remain in the complete analysis; a feed name alone does not establish a contact mode.

The same selected checkpoint must still meet predeclared per-skill criteria with repeat evidence before mastery can be considered. Wider starts/timing, varied mandatory-bounce receiving, kitchen decisions, paired cooperation and full 2v2 are not established by this comparison. Final acceptance seeds remain unused. No automatic extension or model promotion.

Next action: Prepare one reward-only movement experiment from the preserved 1,048,609-experience parent, using the same 6.25–25 cm axes mixture and a fixed endpoint near 2.1 million. Add at most 0.25 for measured forward ball travel after an accepted focus-drill contact; keep familiar and prior-court rewards, body controls, feeds, targets and PPO unchanged. The completed axes run supplies the matched no-progress reference, with only one training lineage per condition. Evaluate legal returns, contact, target following and retention before extending. This new experiment is not launched yet; the latest checkpoint is preserved but not promoted.
