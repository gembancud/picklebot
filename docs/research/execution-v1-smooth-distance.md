# Smooth-distance placement experiment

This experiment changes only the added placement reward. A legal landing receives 0.25 × exp(−distance / 2 m); attempts without a legal landing receive zero placement bonus. Legal landings outside the target still receive graded feedback. The 1 m target-hit criterion, target centers, body controls, base legal rewards, physical drill mix, initializer and 262,144-step budget remain the same as the prior two-region recipe.

20 Unity integration checks passed. A frozen-policy linear-versus-smooth comparison preserved observations, actions, physical episode outcomes, target hits and landing coordinates. It verified positive feedback on legal misses without converting them into successes.

Training completed at **262,179 experiences** across 8 workers × 16 courts. The actual worker records passed the formula audit: 4966/7469 completed attempts were legal target misses receiving the new feedback. Nonzero bonus is not a target-success metric.

The new candidate was evaluated in Unity on 256 paired development resets under A, B and unchanged random targets. Evaluation used the old linear reward mode; reward cannot influence this frozen-policy evaluation. Initializer and earlier linear-trained results were reused with verified file hashes and their original source identities; they were not rerun.

| Model | A legal / target hits | B legal / target hits | Random legal / target hits |
|---|---:|---:|---:|
| Initializer | 228 / 117 | 228 / 4 | 228 / 75 |
| Linear trained | 231 / 100 | 230 / 26 | 229 / 66 |
| Smooth trained | 228 / 109 | 229 / 18 | 229 / 65 |

The candidate requested-versus-opposite-region assignment gain was **-0.0488**, paired-bootstrap 95% interval **[-0.0781, -0.0215]**. Illegal attempts contribute zero; identical target-blind shots cancel.
Predeclared promising screen: **False**. Checks: `{"assignmentGainCiLowerAboveZero": false, "bothRegionTargetRatesImprove": false, "noDrillLegalDropGreaterThanFivePercentagePoints": true}`. No promotion or mastery acceptance.

Per-drill, service-side, region, movement and player results, plus paired differences against both the initializer and the earlier linear-trained policy, are recorded in the analysis. This is one training run per recipe and a reused development cohort with repeated geometries. It does not establish robust recipe superiority, broad movement mastery, or final acceptance. Final evaluation seeds remain unused.

[Analysis and paired comparisons](execution-v1-evidence/smooth-distance-01/analysis.json) · [Frozen plan](execution-v1-evidence/smooth-distance-01/plan.json) · [Actual reward audit](execution-v1-evidence/smooth-distance-01/training-bonus.json) · [Prior baseline evidence](execution-v1-evidence/two-regions-01/analysis.json)

Training coverage audit: all 440 recorded reset-descriptor cells saw both instructions (3,722 A and 3,747 B attempts). 157 cells produced at least one legal landing in each region across the changing stochastic policies. Descriptor cells do not establish exact physical-state identity, and this is not frozen-policy competence. [Coverage data and input hashes](execution-v1-evidence/smooth-distance-01/training-target-coverage.json).

The checkpoint/observation diagnostic found correct target encodings, nonzero learned actor/critic goal weights and retained normalized target separation. CPU commands matched recorded Unity commands within 6 × 10⁻⁷. Every first-state pair retained some goal sensitivity after clipping; the median largest per-channel change was 0.00594 for smooth versus 0.00425 for linear. These first-decision checks do not diagnose later swing decisions or establish correct PPO credit assignment. [Raw diagnostic](execution-v1-evidence/smooth-distance-01/goal-path-diagnostic.json). The next bounded experiment extends the same smooth recipe with full checkpoint resume to roughly 1M total experiences.
