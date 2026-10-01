# Execution-goal integration

First stage of the strategy/execution design, 12 September 2026. The strategy actor is not implemented yet.

The executor accepts 12 additional goal features while retaining the original physical controls. A warm start preserved actor and critic outputs exactly across 512 probes; the exported initializer also reproduced the previous model’s 32 paired Unity drill outcomes. New target inputs have a verified gradient path.

Validation: 17 Unity integration tests and 300 Python regression tests passed. An isolated worker build completed. PPO then ran for **32,776 experiences** on **8 workers × 16 courts**; all workers contributed private player episodes, and the shot-coordinate weights changed. The optimizer and experience counter were freshly initialized.

## Fixed development screen

| Model | Legal landings / 64 | Target hits / 64 |
|---|---:|---:|
| Initialized executor | 53 | 20 |
| After short training | 54 | 21 |

Both models saw the same 64 reset/target seeds, covering serves, bounced and airborne returns, and movement returns. Targets used a 1.5 m radius. This small one-seed screen establishes that the trained export runs; the one-attempt difference does not establish better aiming or robust skill retention. No model was promoted.

| Drill | Attempts per model | Initial legal / target | Trained legal / target |
|---|---:|---:|---:|
| rally-air-feed / movement | 24 | 19 / 4 | 20 / 6 |
| rally-bounce-feed / movement | 24 | 20 / 6 | 20 / 5 |
| receive-feed / familiar | 8 | 6 / 4 | 6 / 4 |
| stationary-serve / familiar | 8 | 8 / 6 | 8 / 6 |

The initial build produced a valid binary but failed during empty-scene cleanup. That failed attempt was retained; the helper was corrected and a fresh build completed with matching source hashes. The task-owned evaluation Editor was restored and closed.

Next: evaluate goal responsiveness (changing only the requested target), then train placement with repeated checks of familiar skills. Movement-goal, recovery, cover and yield training remain ahead of learned strategy and paired play.

[Contract and workflow](../HIERARCHICAL_CONTROL.md) · [Evaluation evidence](execution-v1-evidence/evaluation.json) · [Training verification](execution-v1-evidence/training.json)
