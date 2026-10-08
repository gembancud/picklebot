# Stage 5B tracking teacher: chain result and rule-8 follow-ups (2026-10-08)

**Task:** `Picklebot-Tracking-Tennis-G1`, mjlab's G1 motion tracking on the paddle G1 (full self-collision plus paddle face), with the multi-clip command. Motion file `tennis-v5.npz` (90 clips, 41.8 min). Network: mjlab stock 512-256-128 actor and critic, 4096 envs.

**Evaluation:** `scripts/motion/tracking_eval.py`. Every clip is played start to end 4 times (360 episodes); no pushes, start-state randomisation or observation noise. Success = the whole clip with no termination.

**Gate** (set before tracking-03): success ≥ 90 % overall and ≥ 80 % for every stroke type; root-relative MPKPE ≤ 6 cm; falls ≤ 1 %.

## Chain (rule 9: up to 4 chained ≤ 2 h runs; stop when the gain is < 1 point)
| Run | Endpoint | Dev seed | Success | FH / BH / FH-v / BH-v / serve / smash | Always-succeeding clips | r-MPKPE | Falls |
|---|---|---|---:|---|---:|---:|---:|
| tracking-02 | model_4300 | 4,200,300 | 40.8 % | 56 / 54 / 55 / 38 / 18 / 9 | 23 | 8.7 cm | 0 % |
| tracking-03 | model_8600 | 4,200,301 | 44.7 % | 72 / 43 / 55 / 54 / 15 / 13 | 28 | 8.4 cm | 0.3 % |
| tracking-04 | model_13000 | 4,200,302 | 57.8 % | 78 / 69 / 72 / 52 / 38 / 21 | 36 | 7.6 cm | 0 % |
| tracking-05 | **model_17300** | 4,200,303 | 51.9 % | 74 / 67 / 64 / 45 / 23 / 20 | 31 | 7.6 cm | 0.3 % |

tracking-01 (v4 clips, wrong paddle orientation) was stopped and is not part of the chain.

- **The chain ends** after its fourth run, which lost 5.9 points. Per rule 9 the teacher's fixed endpoint is `tracking-05/model_17300` (the better tracking-04 checkpoint is not picked after the fact).
- **Gate: not met.** Success is 51.9 % (needs 90 %), and serve, smash and backhand volley are far below 80 %. Root-relative MPKPE is 7.6 cm (needs ≤ 6 cm).
- **Failures:** almost all are end-effector or anchor tracking terminations, not falls.

## Failure analysis
- Success rose quickly to about 58 % by 13k iterations, then plateaued or regressed.
- The network is the stock size for tracking a **single** clip (BeyondMimic). Here it holds 42 minutes of varied, fast strokes; multi-motion trackers in the literature use larger networks.
- The adaptive sampler already concentrates on the failing segments (serves and smashes), so sampling is not the obvious limit.
- **Conclusion:** capacity is the most likely bottleneck.

## Follow-up 1 (rule 8), decided before launch: tracking-06-wide
**One change:** a wider network, 1024-512-256 for the actor and critic (task `Picklebot-Tracking-Tennis-Big-G1`).
- **Warm start:** from the fixed endpoint, widened function-preservingly (`scripts/widen_checkpoint.py`: new units have zero outgoing weights, Adam moments are zero-padded; tested). It starts exactly at model_17300's behaviour.
- **Unchanged:** data (`tennis-v5.npz`), rewards, terminations, PPO settings, 4096 envs.
- **Run:** ≤ 2 h; evaluated as above on a fresh dev seed.

**Candidate for follow-up 2** if needed: the LAFAN1 footwork clips (D-047) join the motion set. That is a separate variable and only if follow-up 1 leaves the gate missed. Otherwise they join with the style-prior step.
