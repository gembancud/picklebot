# The rally target (user, 2026-10-21; D-134; frozen)

**Goal:** two copies of the robot keep a rally going.

**The bar:** in two-robot pair play, **at least 80 % of rallies reach 5 good shots in a row, robot to robot.**

| Item | Definition |
|---|---|
| Setup | One shared policy on mirrored environment pairs (`picklebot_mj/pairs.py`), one court per pair. A feeder ball starts each rally and is not counted. |
| A good shot | A legal robot return (over the net, lands in): the first one returns the feeder ball, and every one after it returns the other robot's shot. |
| Rally length | Consecutive good shots until a miss, a fault or a fall. |
| **Pass** | P(rally length >= 5) >= **0.80**, with Wilson lower bound >= **0.78**, over >= 1,000 rallies on development seeds. |
| Also required | Sides A and B within 3 points of legal returns; court falls <= 4.0 % per episode (R3). |
| Reported, not gating | P(4+), P(10+), mean rally length, own-ball legal per side, feeder-ball legal. |

**What it implies:** about 96 % legal per shot (0.96^5 is about 0.80). Today (Stage 5H run 4) it is about 13 % per shot on the partner's balls, and P(5+) is about 0.3 %.

**The hand-off:** the R4 protocol hands the ball over when it crosses the net, so the receiver first sees it mid-flight. Moving the hand-off to the partner's contact (the receiver sees the ball leave the paddle) is a measurement correction that the panel may make before the first read, with a D-entry. It must then be frozen and used for every read of this target. The old R4 read is reported alongside.

**Later milestones (not this target):** competitive self-play against a pool of past versions with fixed anchors; then 2v2.

This file is frozen. A change to its bars needs a D-entry that names the changed premise, and a bar is never loosened.
