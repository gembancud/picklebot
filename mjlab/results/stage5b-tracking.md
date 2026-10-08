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

## Follow-up 1 result: tracking-06-wide
**Run:** 2026-10-08, 4054 iterations to the 2 h cap. Endpoint `model_21300`, dev seed 4,200,304 (`stage5b-tracking-06-wide.json`).

| Measure | tracking-05 | tracking-06-wide |
|---|---:|---:|
| Success | 51.9 % | **58.9 %** (+7.0) |
| Forehand | 74 % | 68 % |
| Backhand | 67 % | 63 % |
| Forehand volley | 64 % | 78 % |
| Backhand volley | 45 % | 63 % |
| Serve | 23 % | 38 % |
| Smash | 20 % | 32 % |
| Clips that always succeed | 31 | 41 |
| r-MPKPE | 7.6 cm | 7.7 cm |
| Falls | 0.3 % | 0 % |

- **Training reward plateaued from about iteration 18.5k**, so more time alone is unlikely to close the gap.
- **Gate: still not met.** The fast strokes (serve, smash) fail most.

## Follow-up 2 (rule 8, the last), decided before launch: tracking-07-preview
The tentative follow-up 2 (adding LAFAN1) is replaced: it does not address the remaining failure. LAFAN1 joins with the style-prior step instead.

**One change: motion preview** (task `Picklebot-Tracking-Tennis-Big-Preview-G1`).
- The actor and critic also observe the reference joint positions 0.1 s and 0.2 s ahead, as offsets from the current reference frame, clamped to the env's clip end.
- Reason: the policy saw only the current reference frame, and the fastest strokes failed most. Previewing upcoming targets is standard in multi-motion trackers.
- **Warm start:** from tracking-06-wide/model_21300 with the 58 new inputs zero-weighted (`scripts/expand_checkpoint.py`, fixed for 1024-wide first layers; the optimizer state is padded). It starts exactly at model_21300's behaviour.
- **Unchanged:** everything else.
- **Run:** ≤ 2 h, fresh dev seed. **If the gate is still missed, the loop stops for the user** (rule 8).
