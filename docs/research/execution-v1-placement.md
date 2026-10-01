# Execution target response and longer placement training

12 September 2026. The goal input affects actions, but useful general placement remains unproven. The strategy policy and movement-goal training have not started.

## Matched target test

Replayed the same 64 development resets with two target requests. Non-serve targets were X = -1.8 and +1.8 m; serves used 0.7 and 2.3 m inside the correct service-box side. Both used Z = 4.5 m and radius 1.5 m. Only requested target X changed. The evaluation fixture replaced the private goal before the first decision without changing runtime source or reset physics.

The initializer was a negative control: all recorded physical observations and actions, plus episode physical outcomes, matched exactly across the two targets. Its goal-input weights are zero. The trained policies changed their first actions in all 64 matched states, but only slightly:

| Model | Largest first-action change, -1 to +1 scale | Fixed target A hits / 64 | Fixed target B hits / 64 |
|---|---:|---:|---:|
| Initializer | 0 | 21 | 1 |
| 32,776 experiences | 0.00307 | 22 | 9 |
| 262,147 experiences | 0.00492 | 24 | 14 |

This establishes target sensitivity. Target-hit differences between checkpoints can also result from general changes in hitting; they do not isolate beneficial steering. We have not measured a causal landing-direction response or shown that every requested target is reachable from every feed.

## Longer run

`execution-placement-01` completed at 262,147 experiences on 8 workers × 16 courts. All workers contributed; the trainer exited successfully and exported finite learned weights. It started from the same initializer as the short run, with a fresh optimizer, rather than resuming the short checkpoint. Drill mix, rewards, network and constant learning rate remained the same; only the training budget increased.

The same 64 varied-target development attempts produced:

| Model | Legal landings / 64 | Requested target hits / 64 |
|---|---:|---:|
| Initializer | 53 | 20 |
| Short run | 54 | 21 |
| Longer run | 55 | 19 |

| Drill | Attempts | Initial legal / target | Longer-run legal / target |
|---|---:|---:|---:|
| Fixed serves | 8 | 8 / 6 | 8 / 8 |
| Opening receives | 8 | 6 / 4 | 6 / 4 |
| Airborne rally feeds | 24 | 19 / 4 | 19 / 2 |
| Bounced rally feeds | 24 | 20 / 6 | 22 / 5 |

Rally groups include central feeds and movement feeds; these are not 24 difficult movement tests each. These reused development seeds are a small diagnostic screen, not final acceptance. No checkpoint was promoted. No final evaluation seeds were consumed.

## Next experiment

Use a simpler placement curriculum with two separated, reachable target regions, starting from familiar feeds, and retain serve/return rehearsal. Predeclare per-skill checks and record actual landing coordinates so target-directed motion can be distinguished from general shot drift. Do not add the strategy actor until the executor can follow goals usefully. This experiment does not establish a need for a larger network or a different RL framework.

The source identity stayed `02e964f7c75b2bd39ff209691b9ffdc944465c7030c7497975b6da6165cac9c0`. The trained ONNX is `ExecutionV1Placement01.onnx`, SHA256 `5c759bc6aa13e5d2d8ea3ca25044b7bdc9cc057393edbfb4b22c5b622ef6ac15`. Training is finished; the task-owned evaluation Editor was restored and closed.

[Initial counterfactual evidence](execution-v1-evidence/target-response-01/verification.json) · [Longer-run counterfactual](execution-v1-evidence/target-response-placement-01/verification.json) · [Varied-target results](execution-v1-evidence/placement-dev-02/verification.json) · [Training evidence](execution-v1-evidence/execution-placement-01/verification.json)
