# The footwork target: call-and-set (user, 2026-11-09; D-251; numbers frozen by panel round 110, D-252)

**Goal (the user's words):** "agility and explosiveness mixed with footwork thats also able to do ready positions in certain directions [...] sprint then split step to prepare for a stroke", the best footwork the robot's body can reach, proven by a hill-climbable metric.

**One rep = one coach call.** A ghost ball (ShadowSwing's paddle-free ball, visible to the policy as a ball) is launched to arrive at a contact point on the robot's half at a set time T, on the called side (forehand or backhand). The swing is not required (recorded only).

| Item | Definition |
|---|---|
| Call types | wide forehand, wide backhand, deep, short: 25 % each; wide calls take their natural side, deep and short calls forehand or backhand 50 / 50 |
| Distance | 1.0-3.0 m from the pelvis at the call, the contact point inside the drill's spot box |
| Deadline (headline) | T = 0.5 s + d / 2.5 m/s (2 m -> 1.3 s, 3 m -> 1.7 s); 2.5 m/s = human court-foot p90 2.9 m/s x 0.85 for size |
| Chains | 6 calls per chain; one third of calls are issued at the previous call's arrival time (early: change of direction under pressure), the rest 1.5 s after it |
| SET (split step) | at T: pelvis ground speed averaged over the last 0.1 s < 0.3 m/s; both feet down (ankle links below 0.12 m, the ReadyTracker contact proxy); trunk tilt < 20 deg |
| READY | at T: MoveDrill's ready_mask (paddle face 0.3-0.5 m ahead of the pelvis, 0.9-1.2 m high) with the paddle >= 0.10 m toward the called side in the pelvis frame |
| REACH | at T: the ghost ball within 0.8 m of the pelvis horizontally, on the called side |
| Falls | a fall fails its rep (and ends the chain); falls stay in the count |
| **Pass (rep)** | SET and READY and REACH at T, no fall |
| Read | deterministic (mean actions), >= 4,000 reps from >= 600 chains |
| **Target** | pass share >= **0.80** with Wilson 95 % lower bound >= **0.78**, and every call type >= 0.70 |
| Also required for the target read | rally feeder-ball legal within 5 points of Q (0.8848) on the frozen set-start read |
| Reported, not gating | pace ladder (the share passing by 0.5 + d / p for p = 1.5, 2.0, 2.5 m/s, from each rep's first time all of SET / READY / REACH hold); start time (pelvis 0.10 m toward the spot); first step to 1.5 m; top speed; per call type, side and early / normal; the swing |
| Seeds | development block 4220451-4220499; target-read block **4220500-4220509 unread, one look**, only for a candidate that passed on a fresh development seed |

**The ceiling claim** (the user's "convince me"): levers are climbed one change per run (damping, facing freedom, action range, effort, a base retrain on the drill, agile reference motion, length / size) and kept when the paired gain's lower bound is above 0; a lever is "flat" when its gain's upper bound is below +2 points. The phase ends at the target, or with a table showing every lever tried and flat.

This file is frozen. A change to its bars needs a D-entry that names the changed premise, and a bar is never loosened.
