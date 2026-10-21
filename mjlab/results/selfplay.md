# Rally target: run log (D-134 onward)

**Target** (`rally-target.md`, frozen): in two-robot pair play, P(5+ good shots in a row) >= 0.80 (Wilson low >= 0.78, >= 1,000 rallies, development seeds), sides within 3 points, court falls <= 4 % per episode. Every target read uses the contact hand-off (D-135). The old crossing read is reported alongside.

Panel rounds: `selfplay-review.md`. Seeds: `seed-ledger.json` (allocation_rally_target, 4218000-4218999).

## Baseline: Stage 5H run 4's endpoint (s5h-04-pairs/model_3398)

R4 protocol, 2,048 envs (1,024 courts), 120 s. `scripts/rally_baseline.sh`. Results: `rally-baseline-{crossing,contact}.json`.

(pending)

## Run 1: pair self-play with the contact hand-off (D-135)

`scripts/rally_run01.sh`. Parent s5h-04-pairs/model_3398, 900 iterations, training seed 79, 12,288 envs. Early kill at model_3700 (`scripts/rally_check.py early`).

(pending)
