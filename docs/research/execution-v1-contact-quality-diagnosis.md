# Collision-quality diagnosis

The second instrumented replay matches all512 original episodes, goal/landing records and first observations/actions byte-for-byte. It adds actual contact point, normal, incoming/outgoing velocity and per-tick observations for the same five selected cases.

The failed rightward contact (seed1109964) is an edge graze: the absolute dot product of its actual collision normal with the broad-face normal is **0.0093**. Successful reference contacts are **1.0000** (1109881) and **0.9783** (1109963). Alignment uses the next pre-step paddle pose, so minor rotation may occur between the actual collision and measured face normal; the near-perpendicular failed case is unambiguous.

The existing `FaceContact` metric checks the name `RoundedHittingFace`, whose closed mesh includes front, back and side surfaces. It does not mean a broad-face strike. This is a diagnostic/reward distinction, not a reason to make physical edge hits illegal or to change collision impulses. The observed failed hit still earns the existing contact bonus, even though it barely redirects the ball forward. One trace does not establish the prevalence of edge hits in training.

The actor receives canonical lateral ball position at observation index4, scaled by8.4m, plus ball velocity and facing sine/cosine. Locomotion actions are intentionally body-local. An offline initial-state probe changed only ball-relative x by ±0.25/0.5m. Actions respond, but remain strongly leftward in these cases; one remains clipped at -1. The unmodified first-three actions match Unity within2.6e-7. This proves a connected input path, not adequate trajectory adaptation or an observation bug. Do not conclude that every initial backswing-related lateral movement should reverse immediately.

Next implementation should add contact-quality telemetry alongside existing contact counts, preserving historical meanings. Before another optimizer run, compare pre-contact ball-to-striking-surface error and actual broad-face contact quality on the lateral training stages. A post-contact-only reward cannot address no-contact misses. Keep skill-retention and full directional evaluation mandatory; do not promote the latest model.

No source, physical limits, action semantics or trainer settings were changed. The same checkpoint remains unpromoted. Evidence and losslessly compressed traces are in `research/hierarchy-v1/movement-progress-trace-02`.
