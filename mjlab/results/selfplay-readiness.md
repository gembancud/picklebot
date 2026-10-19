# Ready for self-play: the frozen readiness milestone (panel round 8, D-116; frozen before run 4)

A separate milestone. It is **not** a Stage 5 pass: the Stage 5 gate (falls 1 % per episode, style 3.86, group floors) stays open and unchanged. The milestone is met when **one fixed endpoint** (never a picked checkpoint) passes all four items. Each item is read once per run, on that endpoint, on its pre-allocated seeds.

| # | Item | Measure (unit stated) | Bar |
|---|---|---|---|
| R1 | **Skill without forgetting** | the clean battery (`h5f_clean_eval.sh`): every stage kill rule (D-113), plus drill v2 per-shot p | all kill rules pass, and drill v2 p >= 0.80 |
| R2 | **Own-ball returns** | replay of the endpoint's own legal returns, post-contact (pos, vel, spin), mirrored to the far side. Recorded from the rally evaluation on seeds 4215000-4215049; replayed on seeds 4215100-4215149; 1,000 balls or more | legal returns: point estimate >= 0.70 **and** Wilson lower bound >= 0.65. Falls per shot reported. |
| R3 | **Falls** | court drill, clean, falls per robot episode (about 2.8 feeds each). Per-feed and per-shot rates reported alongside, each labelled with its unit | <= 4.0 % per episode |
| R4 | **Two-robot smoke test**: the acceptance test of the self-play environment, not a training target | two copies of the endpoint on mirrored environment pairs; a feeder ball starts each rally (not counted); 1,000 rallies or more, seeds 4215200-4215249 | P(4 or more consecutive legal robot shots) >= 25 %; side A and side B within 3 points; falls per shot reported |

**Mirror.** (x, y) -> (-x, -y); (vx, vy) -> (-vx, -vy); (wx, wy) -> (-wx, -wy); z, vz and wz unchanged. This is a 180-degree rotation about the court centre, under which the ball physics is symmetric.

**Anti-drift.**
- The evaluation scripts are committed (and their hashes recorded) before first use.
- The readiness seed block 4215000-4215999 is allocated in the ledger now. It is used only for these items, only on fixed endpoints, and never to pick checkpoints.
- A bar changes only through a D-entry that names the changed premise. At most one change, and it never re-judges an earlier run.

**Budget and exit.**
- Readiness must be met by **run 9** (6 runs from run 4).
- Otherwise, or on a third kill in a row (with no new vote), the pre-registered exit is taken: the goal-conditioned controller.
- Plateau: two passing runs in a row, each gaining < 1 point on both drill v2 p and R2, also take the exit.

**Not part of readiness** (reported only): style, the ready / split-step metric, P(rally >= 10) against the feeder (a feeder "rally", not a real one).
