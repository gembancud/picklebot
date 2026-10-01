# Wider movement diagnostic

The frozen 1,048,609-experience executor can return some wider feeds, but the progression remains incomplete. All four model/target conditions completed 512 attempts. The same 512 base resets were reused under A/B instructions; they are not 2,048 independent situations. No training or simulation changes occurred.

| Cases | Initializer A | Current A | Current B |
|---|---:|---:|---:|
| All cases | 275/512 | 285/512 | 288/512 |
| Familiar and retained skills | 251/256 | 247/256 | 248/256 |
| Movement challenges | 24/256 | 38/256 | 40/256 |

The initializer ignores target inputs, so its A/B physical outcomes match exactly. Both conditions remain archived. The movement subset retains all 256 attempts, including contact failures.

| Nominal feed shift | Initializer A | Current A | Current B |
|---|---:|---:|---:|
| 25 cm | 21/64 | 31/64 | 33/64 |
| 50 cm | 3/64 | 7/64 | 7/64 |
| 75 cm | 0/64 | 0/64 | 0/64 |
| 100 cm | 0/64 | 0/64 | 0/64 |

| Direction | Initializer A | Current A | Current B |
|---|---:|---:|---:|
| Left | 5/66 | 3/66 | 5/66 |
| Right | 0/64 | 0/64 | 0/64 |
| Shallow | 5/62 | 19/62 | 17/62 |
| Deep | 14/64 | 16/64 | 18/64 |

Directions and distances are marginal counts. Full drill/direction/distance/player cells are preserved; two player-specific cells are empty. No cases were substituted based on outcomes.

## Retained skills and actual movement

| Drill | Initializer A | Current A | Current B |
|---|---:|---:|---:|
| stationary-serve | 64/64 | 64/64 | 64/64 |
| receive-feed | 59/64 | 55/64 | 56/64 |
| rally-air-feed | 69/192 | 76/192 | 78/192 |
| rally-bounce-feed | 83/192 | 90/192 | 90/192 |

Under A, the current executor made accepted paddle contact on **69/256** movement attempts. Its mean root path before those contacts was **0.439 m**, with mean net displacement **0.296 m**. In the **187** attempts without accepted contact, mean root path through termination was **0.978 m**.

This is movement, but distance travelled does not prove useful positioning. Misses can last longer and accumulate more travel. A nominal feed shift is measured from the initial paddle face, not a required footwork distance. These results do not establish a physical control limit or prove every feed is reachable within its contact window.

## Target instructions

| Cases | Paired assignment gain [pointwise 95% interval] |
|---|---:|
| All cases | 0.02637 [0.00977, 0.04395] |
| Familiar and retained | 0.05859 [0.02734, 0.08984] |
| Movement challenges | -0.00586 [-0.01562, 0.00195] |

The aggregate target response comes from familiar cases. A useful directional target response is not established on the movement challenges. Actual legal landing coordinates determine success; nonzero distance reward does not count as a target hit.

## What this supports next

The next candidate curriculum is graded axes practice: 6.25/12.5/18.75/25 cm focus shifts while retaining the existing interleaved 25% familiar, 25% prior-court and 50% focus schedule. Keep the body, PPO, full checkpoint state, A/B goals and smooth reward unchanged. The opt-in scheduler needs a small implementation change; it is not yet applied or trained.

Inspect representative recorded misses before deciding whether flight timing also needs adjustment. A bounded continuation can then reuse the narrow and wide frozen batteries; 50–100cm remain transfer probes. Do not keep extending the unchanged narrow recipe merely because its familiar scores remain high.

## Evidence limits

The reset-only fixture inspected all 512 cases with zero policy actions, zero physics ticks and no initial overlaps. It found 174 distinct initial physical observations and covered all 32 direction/distance/feed cells. Sparse repetitions, one training lineage, zero start/timing variation and this reset recipe do not establish full-court generalization. A passed geometry inspection does not prove contact feasibility.

No new mastery threshold, model promotion, or final-seed use occurred. Varied mandatory-bounce receiving, kitchen-boundary decisions, broader movement and reliable targeting remain requirements of the active goal.

[Full analysis](execution-v1-evidence/wide-movement-01/audit/analysis.json) · [Reset fixture](execution-v1-evidence/wide-movement-01/fixture-summary.json) · [Frozen plan](execution-v1-evidence/wide-movement-01/plan.json) · [Archive manifest](execution-v1-evidence/wide-movement-01/archive-manifest.json)
