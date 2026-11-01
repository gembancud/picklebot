# Panel round 64 brief: FEED-STATE, so review the readiness run (D-199 draft) before launch, 2026-11-01

Read first:
- D-198 in docs/DECISIONS.md;
- mjlab/results/ballidx63-summary.txt;
- round 63 in mjlab/results/footwork-review.md;
- picklebot_mj/tasks/footwork_specialist.py (TASK_RALLY_READY, ready_at_event, install_ready_latch);
- tests/test_footwork_specialist.py::test_rally_ready_adds_only_the_ready_term_and_pays_once_per_event.

## Result (ballidx63, D-198's pre-registered rule): **FEED-STATE**

Config was valid in all three arms (base_checkpoint checked). Matched band: 1,047 / 978 feeder balls.

| | C (d1s3, dev 4220303) | C2 (d1s3, 4220304) | P (22b, 4220303) |
|---|---|---|---|
| feeder legal / contact (all) | 0.714 / 0.798 | 0.711 / 0.789 | 0.728 / 0.807 |
| matched band: k=0 contact vs k>=3 contact | 0.882 vs 0.996 | 0.857 vs 0.994 | 0.904 vs 0.995 |
| k = 1 / 2 / 3+ legal | 0.680 / 0.851 / 0.959 | 0.683 / 0.857 / 0.962 | 0.695 / 0.830 / 0.930 |

- Contact gap: +0.114, against a noise of 0.047.
- Receiver state at the feeder fire, C, matched band, by tercile:

| variable | p50 at the fire | failure by tercile |
|---|---|---|
| pelvis speed | 0.28 m/s | 0.092 / 0.175 / 0.371 (PASS) |
| recovery distance | 0.94 m | 0.048 / 0.213 / 0.352 (PASS) |
| yaw | — | FAIL |
| idle | — | FAIL |

- Reported, the C child's pairs read (dev 4220305): refeed 0.5 s against 3 s gives feeder 0.624 vs 0.739 and P(5+) open 0.366 vs 0.514.
- **The D-198 route for FEED-STATE:** a readiness lever at rally start (motion's `ready_at_handoff`, keyed at fire or receive), on the d1s3 child.

## Draft D-199 (coded task, not yet launched)

**One change against d1s3:** task Picklebot-Rally22b-FastMove-Ready-G1 = d1s3's task plus one reward term, `ready_at_event`.
- **Value:** exp(-(|v_xy| / 0.3)^2) x exp(-(|pelvis - recover_xy| / 0.5)^2).
- **When it pays:** on the control step after the env is given a ball, only. The trigger is the feeder fire or the partner's contact, latched from PairCourts.step, which runs every substep. It pays nothing while the ball is in flight.
- **Weight:** READY_W 50, the same as paddle_contact. Event terms here are scaled by weight x dt: paddle_contact 50, legal_return 250, partner_return 150, move_arrival 100. So a fully set robot earns 1.0 per event, like a paddle contact. Motion's round-63 "w = 2.0" would be negligible on this scale. **Rule on the weight.**
- **Ball term:** its class changes only to carry the latch; the field values are unchanged (tested).
- **Run settings:**
  - parent: the d1s3 child (rally-d1s3 model_31399) on the d1 base;
  - optimizer as before: 1e-4 constant, KL 0.05, std floor 0.1, warm-up 0, 12,288 envs, 1,200 iterations;
  - training seed 191, smoke 192.

**Draft lines**
- **Kill at +360:**
  - D-194's training-log KILL-UNSTABLE / KILL-NO-HIT, against 22b's 30100-30199;
  - D-196's KILL-SLOWED / KILL-NO-ARRIVE on Measure60, against the parent read on the same seed;
  - **KILL-NO-DOSE**, new: the logged Episode_Reward/ready_at_event over +341-360 is not above its +1-20 mean. This is cheap and from the log; the D-177 lesson.
- **Endpoint** (paired with the parent on the same seeds):
  - **F-UP:** feeder legal >= parent + 5.0 pt, with the court-bootstrap low above the parent's point;
  - **rally:** d1s2-gate against the parent, unchanged. Court falls stay <= 0.04 absolute; falls paired against the parent are reported;
  - **AGILE-KEPT** against the parent's Measure60;
  - **dose read:** a feeder-tally LR-0 read of the child and the parent on one paired dev seed. NO-DOSE if the child's k = 0 pelvis-speed p50 at the fire is not >= 0.05 m/s below the parent's. k >= 3 legal must not drop more than 1 pt;
  - **reported:** absolute feeder legal against 0.80 (the target implies about 0.96); the refeed-3 s pairs read.
- **Verdicts:**
  - **READY-PASS:** F-UP + rally + AGILE-KEPT + dose;
  - **READY-F:** F-UP + AGILE-KEPT + dose, rally not met;
  - **NO-DOSE;**
  - otherwise **READY-FAIL** (to the panel).

**Seeds (draft):**
- dev: pairs 4220306, direction 4220307, Measure60 4220308, +360 Measure60 4220309, h5f 4220310-4220325, dose read 4220326;
- training: 191-192.

## Questions

1. A correction check of the FEED-STATE reading and the draft code.
2. The weight (50) and the two stds (0.3 m/s, 0.5 m).
3. The kill and endpoint lines: amend, add, or remove; never loosen.
4. Anything that would make the result uninterpretable. For example, could the robot "game" the term by standing at its spot instead of chasing feeds? The term pays only at fire or receive, when the ball has just been put in play for that env.
