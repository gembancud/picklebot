# Active drill-mastery goal — longer training produces partial target response

The unchanged continuation completed at **1,048,609 total experiences**. The predeclared midpoint and final models each completed 768 frozen evaluation attempts. Compared with the 262,179-experience parent, final A/B/random target hits changed **109/18/65 → 103/35/71** out of 256 per condition. Final legal counts were **229/231/229**; the per-drill legal-retention screen passed against both the initializer and immediate parent.

The requested-versus-opposite-region assignment gain improved from **−0.04883 to +0.0625**, final paired 95% interval **[0.03125, 0.09570]**. This is early target responsiveness on a reused development anchor. The full screen still failed because A accuracy did not exceed the initializer. B-air remains 0/112 and B-required-bounce receiving 0/16; no reset succeeds at both requested regions. No promotion or mastery acceptance.

No training or task-owned Editor is active. The next action is a fresh, predeclared frozen-model development comparison, including a count of genuinely new physical resets and separate drill/region results. More training or architecture changes depend on that evidence. Wide/deep/shallow positioning, varied rule contexts, paired teamwork and learned strategy remain unfinished.

[Latest result](research/execution-v1-smooth-continued.md) · [Remaining coverage](research/drill-mastery-coverage.md) · [Active goal](DRILL_MASTERY_GOAL.md)

---
# Active drill-mastery goal — smooth placement screen complete

The smooth-distance experiment completed at **262,179 experiences**, with 20 Unity checks passing and 768 frozen-policy attempts. It preserved legal returns but failed the predeclared aiming screen. On the same 256 resets, initializer → candidate target hits were A **117 → 109**, B **4 → 18**, and random **75 → 65**. Legal landings were **228 → 228/229/229** respectively.

Changing the requested region produced a negative assignment gain of **−0.04883** (paired 95% interval **[−0.078125, −0.021484]**). This is one short training run on reused development cases; no model was promoted and mastery is not accepted. Both target instructions appeared in all 440 recorded training reset-descriptor cells, so gross assignment imbalance does not explain the result.

The input diagnostic passed for recorded first decisions. A bounded unchanged continuation, `execution-smooth-continued-01`, is now running toward 1,048,576 total experiences on 128 courts. The installed loader matched the complete saved state and the trainer confirmed resume at step 262,179. Midpoint and final checkpoint selection are fixed before evaluation. The task-owned evaluation Editor is closed. Wide/deep/shallow positioning, varied mandatory-bounce receiving and kitchen-boundary behavior remain separate coverage gaps.

[Experiment and evidence](research/execution-v1-smooth-distance.md) · [Coverage audit](research/drill-mastery-coverage.md) · [Active goal](DRILL_MASTERY_GOAL.md)

---

# Active drill-mastery goal — two-region screen complete

The goal is active. Two-region layout and canonical legal landing diagnostics are implemented; 19 Unity checks passed. The final two-region model trained for262,165 experiences over128courts. Matched256-reset evaluation: A targets117→100, B4→26, unchanged random75→66. Legal landings228→231/230/229 respectively. Requested-versus-opposite-region assignment gain−0.02148, paired95% interval[−0.046875,0.00390625]: useful target following was not demonstrated. The legal-retention point-estimate screen passed, but placement screening failed. No promotion or mastery acceptance.

No training or task-owned Editor remains active. The next experiment must address goal-directed placement while preserving legal returns; geometry alone has not established every target/feed pair is feasible. Learned strategy and movement-goal training remain pending.

[Latest results and full evidence](research/execution-v1-two-regions.md) · [Active goal](DRILL_MASTERY_GOAL.md)

---
# Execution placement evaluation — 12 September 2026

Completed target-response checks and a 262,147-experience run (8 workers × 16 courts). Goal inputs affect actions, but varied-target hits did not improve: initializer 20/64, short run 21/64, longer run 19/64. Legal landings were 53/54/55 respectively. No promotion, no active training. Strategy policy and movement-goal training remain pending. Next: simpler two-region placement with familiar-skill rehearsal and actual landing-coordinate diagnostics.

[Latest experiment and evidence](research/execution-v1-placement.md)

---
# Execution-goal stage implemented

12 September 2026, branch `feat/hierarchical-control`. The executor now accepts movement and shot goals. The initial shot-goal training check completed (32,776 experiences); its 64-attempt development screen changed from 53 to 54 legal landings and 20 to 21 target hits. This is an integration result, not a demonstrated aiming breakthrough. No new model is promoted.

The strategy actor and movement/recover/cover/yield training remain unimplemented. [Design](HIERARCHICAL_CONTROL.md) · [Tests and measurements](research/execution-v1-integration.md)

The previous published baseline follows for comparison.

---
# Checkpoint before hierarchical control

Snapshot: **11 September 2026**. Current implementation: one actor per player instance, shared player weights, ML-Agents PPO. The proposed strategy/execution hierarchy has not been implemented.

## Demonstrated

- Learned fixed-ball serves, easy opening receives, central airborne and bounced returns.
- Constrained grip, wrist, elbow, shoulder and body control; no authored V3 stroke sequence.
- Up to 128 independent practice courts in the last comparison (8 workers Ã— 16 courts).
- Paired practice and competitive self-play infrastructure, model exports, recordings and outcome-based evaluation.

## Latest measurement

Four matched 500,000-experience branches and 10,752 evaluation episodes completed. Every compared model kept 64/64 serves and 64/64 on each central-return test. The corrected critic-buffer key averaged 3.9 percentage points below the original trainer on earlier varied airborne returns and failed the predeclared improvement screen. All branches failed at least one directional movement-retention check. No candidate was promoted.

These are finite development tests with repeated simple setups. They do not establish full-court generalization, complete human biomechanics or competent 2v2. [Detailed results](research/critic-key-comparison.md)

## Next design

Two actor policies are proposed: a strategy policy chooses an intention and target; an execution policy coordinates movement, preparation, contact and recovery. All four players may share both policies' weights and act independently. Serving and returning may remain capabilities of one execution policy; no bank of experts is required by this proposal.

The next motor milestone is a return policy that accepts a target area and handles varied incoming balls and continuous shot transitions. Broader placement, timing, teammate coordination and reliable sustained rallies remain open. No architecture migration or new training run is included in this snapshot.

## Archive boundaries

Source, scenes, all existing ONNX exports, five full comparison checkpoints, training configuration and compact evaluation evidence are committed. Local virtual environments, generated executable builds, raw rollouts, TensorBoard events, credentials and bulk frame collections remain local. Older specifications and reports describe earlier stages; their historical conclusions are preserved.

The original repository README is preserved in [the archive](archive/README-before-2026-09-11.md). The current setup is [here](TRAINING_SETUP.md).


