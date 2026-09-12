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

Current work: The matched **execution-movement-progress-01** experiment is running on **128 courts**, from the preserved 1,048,609-experience parent toward a fixed endpoint near 2.1 million. It keeps the same 6.25–25 cm axes mixture and PPO settings, adding at most 0.25 for measured forward ball travel after an accepted contact in focus drills. Familiar and prior-court rewards remain unchanged. All 50 Unity checks passed, the new worker build passed, and all eight workers started with exact registered trainer-state restoration. The completed no-progress control remains preserved and unpromoted; its rightward returns and target following were insufficient. At the fixed endpoint, compare legal returns, contact, aiming and retention on the same narrow and wide development tests before extending. This is one matched training comparison, with no performance improvement established yet. Final acceptance seeds remain unused. [Running experiment](research/execution-v1-movement-progress.md) · [Completed control](research/execution-v1-axes-recovery-final.md).

App status: active. The earlier paused 2v2 goal was cleared, and this focused drill-mastery goal was created on 12 September 2026.

