#!/usr/bin/env bash
# Readiness R2 (own-ball) on the start point, run 3 (killed; diagnostic only) and run 4; R4 (pairs) on the start point and
# run 4 (D-116). Waits for run 4's endpoint battery to finish (its summary file) so nothing shares the GPU with it.
cd "$(dirname "$0")/.."
while [ ! -f results/stage5f-s5f04-summary.json ]; do sleep 60; done
bash scripts/h5f_ownball.sh s5d-01-rally model_1800.pt s5d01 0
bash scripts/h5f_ownball.sh s5f-03-v2-clean-hold model_2600.pt s5f03 1
bash scripts/h5f_ownball.sh s5f-04-mix-court40 model_2599.pt s5f04 2
bash scripts/h5f_pairs.sh s5d-01-rally model_1800.pt s5d01 0
bash scripts/h5f_pairs.sh s5f-04-mix-court40 model_2599.pt s5f04 2
