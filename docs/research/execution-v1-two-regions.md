# Two-region placement experiment

The drill-mastery goal is active. This is a development experiment; no model has been promoted and mastery has not been established.

Two separated target choices were added while keeping the existing body, feed schedule and PPO settings. Target radius is 1 m, versus 1.5 m in the unchanged random-target retention test. Serve targets differ in depth inside the correct service box; rally targets differ laterally. The targets are geometrically legal, with feasibility still to be measured per feed.

19 Unity integration checks passed, including worker configuration, sampling and canonical landing evidence. A test initially read evidence before its writer closed; its lifecycle was corrected. The first build audit detected Unity changing an analytics define; a fresh build passed. The first training launch failed before learning because Windows reserved port5426. The unchanged retry used ports5605–5612. All failed records are retained locally.

Training completed at **262,165 experiences**, using 8 workers × 16 courts and the original initializer with fresh optimizer state. The final checkpoint was selected in advance.

Each condition uses the same 256 development resets, spanning one complete recovery cycle. A and B are paired target requests; random retains the previous target distribution. No final evaluation seeds were used.

| Condition | Initial legal / target hits | Trained legal / target hits |
|---|---:|---:|
| A | 228 / 117 | 231 / 100 |
| B | 228 / 4 | 230 / 26 |
| random | 228 / 75 | 229 / 66 |

The requested-versus-opposite-region assignment gain was **-0.0215**, with paired-bootstrap 95% interval **[-0.0469, 0.0039]**. Identical target-blind landings cancel in this measure; illegal attempts contribute zero.
Both requests landed legally in 229/256 pairs. Their mean projected landing shift toward B was 0.0400 m. This conditional shift excludes pairs with an illegal attempt and must be read beside unconditional outcomes.

Predeclared promising-screen result: **False**. Checks: `{"assignmentGainCiLowerAboveZero": false, "bothRegionTargetRatesImprove": false, "noDrillLegalDropGreaterThanFivePercentagePoints": true}`. This is not final acceptance.

Per-drill, region, service-side, movement and player counts and uncertainty are included in the analysis. These are reused development resets from one training lineage; repeated geometries and small subgroups limit inference. Current movement ranges do not demonstrate wide/deep/shallow mastery.

[Analysis and per-skill counts](execution-v1-evidence/two-regions-01/analysis.json) · [Frozen plan](execution-v1-evidence/two-regions-01/plan.json) · [Training verification](execution-v1-evidence/two-regions-01/training-verification.json)

Next planned experiment: test a smooth legal-distance placement bonus, such as0.25×exp(−distance/2m), while keeping illegal attempts at zero, the existing base rewards,1m target-hit criterion, target centers, feed mix, initializer and262,144-experience budget unchanged. This tests a feedback hypothesis; it is not a proven explanation for the failed screen. Retain the same paired development evaluation and success screen. This next reward mode is not implemented in the checkpoint reported here.
