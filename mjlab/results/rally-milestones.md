# Rally milestones on the way to the target (user, 2026-10-21; D-137; frozen)

**Why:** the frozen target (`rally-target.md`: 80 % of rallies reach 5 good shots) is far away. Today the robot returns 19 % of its partner's balls and 65 % of feeder balls. The user approved adding intermediate milestones, with a panel-approved rally video at M1. **The target itself is unchanged.**

**The read for every milestone:**
- **Protocol:** pair play with the contact hand-off (D-135), on the R4 protocol: `Picklebot-Latent-Court-Res-G1`, every family, no hint, rally, pairs. 2,048 envs (1,024 courts), 120 s.
- **Seeds:** one pre-registered development seed, read **once**, at a run's fixed endpoint. A milestone is never claimed from an early or mid-run read.
- **Rallies:** at least 1,000.
- **Intervals:** lower bounds are court-cluster bootstrap 95 % bounds. Courts are resampled with replacement, 2,000 resamples, generator seed 0 (`scripts/rally_check.py`). Shots inside a court are not independent.

## M1: a cooperative mid-court rally

| Item | Bar |
|---|---|
| Partner-ball legal (returns of the other robot's shots) | >= 50 %, bootstrap lower bound >= 0.49 |
| Feeder-ball legal | >= 85 %, bootstrap lower bound >= 0.84 |
| Sides A and B (all shots legal) | within 3 points |
| Court falls per episode (R3, the endpoint court drill) | <= 4.0 % |
| Reported, not gating | P(3+), P(5+), falls per shot per side, the lowest move arrival, keep-alive-box share and mean \|y\| of legal landings |

**At M1:** the user gets a panel-approved two-robot rally video (GIF plus MP4), and the loop continues to M2.

## M2: three-shot rallies

P(3+) >= 50 %, bootstrap lower bound >= 0.48, with M1's other items (sides, falls). The per-court rally counts that its bootstrap needs are added before the first M2 read.

**Then:** the frozen target.

This file is frozen. A change to a bar needs a D-entry that names the changed premise, and a bar is never loosened.
