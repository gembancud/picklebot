# Longer unchanged placement training

The continuation completed at **1,048,609 total experiences**, adding **786,430** to the smooth-distance policy. Body controls, physical drill mixture, target geometry, PPO hyperparameters and reward recipe were unchanged. Eight workers each ran sixteen courts.

The maintained trainer resumed actor, critic, normalizers, Adam and global step from an isolated full checkpoint. The installed-loader preflight restored all registered state exactly, actual logs confirmed step 262,179, final parameter/optimizer counters advanced, and the completed parent files remained unchanged. Processes, unfinished rollouts and RNG progression restarted; training reset IDs were reused.

The midpoint (**524,277**) and final (**1,048,609**) were selected using the predeclared step rule. Each was evaluated on the same 256 A/B/random development resets. The midpoint describes the trajectory; the final checkpoint remains the selection even if an earlier checkpoint scored higher. Initializer and immediate-parent evidence were reused with verified hashes and original source identities.

| Model | A legal / target hits | B legal / target hits | Random legal / target hits |
|---|---:|---:|---:|
| Initializer | 228 / 117 | 228 / 4 | 228 / 75 |
| 262,179 experiences | 228 / 109 | 229 / 18 | 229 / 65 |
| Midpoint: 524,277 | 227 / 75 | 227 / 5 | 228 / 67 |
| Final: 1,048,609 | 229 / 103 | 231 / 35 | 229 / 71 |

Final requested-versus-opposite-region assignment gain: **0.06250**, paired-bootstrap 95% interval **[0.03125, 0.09570]**.
Predeclared promising screen: **False**. Checks: `{"finalAssignmentGainCiLowerAboveZero": true, "bothFinalRegionTargetRatesExceedInitializer": false, "noFinalDrillLegalDropGreaterThanFivePercentagePointsVsEitherReference": true}`. No promotion or mastery acceptance.

The screen checks per-drill legal retention against both the initializer and immediate parent across all three conditions. A pooled success rate cannot substitute for these checks. Actual landing coordinates determine target hits; training bonus is not a target-success metric.

These are reused development cases from one continuing lineage, with repeated geometries and mostly small feed shifts. This does not establish broad court positioning, kitchen-boundary judgment, robust recipe superiority or final mastery. Final acceptance seeds remain unused. The reward/episode inputs are preserved as lossless gzip files with both compressed and uncompressed hashes.

[Full analysis](execution-v1-evidence/smooth-continued-01/analysis.json) · [Plan](execution-v1-evidence/smooth-continued-01/plan.json) · [Training verification](execution-v1-evidence/smooth-continued-01/training-verification.json) · [Worker input archive](execution-v1-evidence/smooth-continued-01/training-input-archive.json) · [Remaining coverage](drill-mastery-coverage.md)

The positive paired response is uneven. Airborne B has 0/112 target hits and mandatory-bounce receiving B has 0/16. Bounced-rally landings hit B 27 times under either instruction. A-goal serves reach A 0/16 while B-goal serves reach B 8/16, despite legal serving remaining intact. No paired reset reaches both requested regions. The model responds to instructions in some situations; it is not a balanced two-region controller. [Instruction-versus-landing matrix](execution-v1-evidence/smooth-continued-01/target-matrix.json).

Next: freeze this checkpoint and compare it with the initializer on separately declared unused development seeds under the same physical mixture and A/B/random instructions. Measure novel physical reset coverage explicitly; new seed IDs alone do not prove novel scenarios. This diagnostic confirmation is justified by the positive target-response component, while the full predeclared screening gate remains failed. No further training, architecture change, or promotion is implied by this result.
