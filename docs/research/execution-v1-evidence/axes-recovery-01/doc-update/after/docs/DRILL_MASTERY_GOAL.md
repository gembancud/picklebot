# Current milestone: master the existing drills

Develop one shared execution policy that reliably performs the existing constrained-body drills and preserves earlier skills as new skills improve, before adding learned strategy or full 2v2.

Scope:

- Fixed-ball legal serves, on both service sides.
- Receiving after the required bounce.
- Airborne rally returns when permitted, including kitchen legality.
- Varied lateral, deep and shallow movement returns, with effective positioning.
- Returning to requested target areas, starting with two separated regions.

The body controls the stroke and positioning. Targets specify outcomes; no scripted serve, swing or navigation path is introduced.

Evidence required for completion:

- Explicit, attainable acceptance thresholds recorded before final testing, informed by physical feasibility and development baselines. Do not promise 100% on arbitrary feeds.
- Per-skill and per-variation results on repeatable evaluations, including both service sides and all player seats. Do not hide failures in an overall average.
- All skills meeting their criteria in the same selected checkpoint, with repeat evaluations and uncertainty reported.
- Requested targets causing useful changes in landing location on matched feeds, measured through actual landing coordinates.
- Representative successes and misses recorded for human inspection of movement.
- Previous models and experiment evidence retained. Final evaluation seeds remain unused until the candidate is frozen for acceptance.

Current work: the fixed 2,097,159-experience axes endpoint completed all five narrow/wide development evaluations. At nominal 25 cm, previous → final legal returns changed A **31 → 29 / 64**; B **33 → 22 / 64**; target hits changed A **9 → 12 / 64**; B **5 → 3 / 64**. Against the initializer, the existing narrow screen **failed**; 2 drill/condition legal-retention point estimates exceeded the 5 percentage-point loss limit. Against the previous endpoint, the existing narrow screen **failed**; 1 drill/condition legal-retention point estimates exceeded the 5 percentage-point loss limit. These are development checks, not mastery or statistical noninferiority guarantees. Next action: Prepare one reward-only movement experiment from the preserved 1,048,609-experience parent, using the same 6.25–25 cm axes mixture and a fixed endpoint near 2.1 million. Add at most 0.25 for measured forward ball travel after an accepted focus-drill contact; keep familiar and prior-court rewards, body controls, feeds, targets and PPO unchanged. The completed axes run supplies the matched no-progress reference, with only one training lineage per condition. Evaluate legal returns, contact, target following and retention before extending. This new experiment is not launched yet; the latest checkpoint is preserved but not promoted. Balanced targeting, broader movement and mandatory-bounce variations, deliberate kitchen behavior, mastery thresholds and repeated acceptance remain open. No automatic training extension or model promotion; final acceptance seeds remain unused. [Final experiment](research/execution-v1-axes-recovery-final.md) · [Movement evidence](research/execution-v1-wide-movement.md). Movement-goal, paired ownership and strategy training remain later stages. <!-- axes-recovery-final-status -->

App status: active. The earlier paused 2v2 goal was cleared, and this focused drill-mastery goal was created on 12 September 2026.

