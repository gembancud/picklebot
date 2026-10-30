# Panel round 54 brief (footwork phase step 2: route D's H0 fine-tune), 2026-10-31

Read first:
- D-183 and D-184 in docs/DECISIONS.md;
- mjlab/results/footwork-review.md (rounds 51-53);
- scripts/diag/footwork_travel_check.sh and picklebot_mj/travel_rule.py;
- results/fw2t-summary.txt and fw2t-summary.json.

## Travel check result (frozen, D-184): **TRAVEL-GAP / OBJECTIVE**

D is the median of robot / reference net pelvis displacement per 4-s window; TR is the summed ratio.

| read | windows | D | D at 1 s | TR [95 % CI] | speed ratio | stance slip p50 | D, friction >= 0.6 |
|---|---|---|---|---|---|---|---|
| T1: H0 on footwork-fast, FAST | 1,587 envs / 397 | 0.495 | 0.675 | 0.511 [0.495, 0.527] | 0.519 | 0.25 m/s | 0.500 |
| T2: latent-07 on footwork-fast, FAST | 1,589 / 398 | 0.569 | 0.633 | 0.572 [0.557, 0.588] | 0.540 | 0.275 | 0.568 |
| T3: H0 on its own LAFAN1 windows, FAST (control) | 3,038 / 775 | 0.736 | 0.826 | 0.718 [0.704, 0.732] | 0.724 | 0.26 | 0.740 |
| T3: LAFAN1, all windows (reported) | 6,878 / 1,748 | 0.726 | 0.824 | 0.719 | 0.772 | 0.199 | 0.727 |

- **The instrument check passed** on T1, T2 and the T3 control.
- **It is not contact.** Grippy-floor envs give the same D.
- **The feet slide** about 0.25 m/s in stance at every friction, against amass_g1_import's skate limit of 0.15.
- **H0 under-travels even on its training data** (0.74). The objective is the cause, not coverage.

## H0's current setup (s5c-03b-h0mirror model_63300)

The task is Picklebot-Tracking-TennisLafan3-Huge-G1 (tennis-lafan3.npz: Tennis-MoCap strokes, LAFAN1 and mirrored LAFAN1). It was trained with stock rsl_rl PPO at a fixed learning rate of 1e-5, 4,096 envs, 5,000 iterations, resumed from tracking-20-decay model_60800 (artifacts/train/s5c-03b-h0mirror.launch.json).

Rewards (artifacts/train/logs/picklebot_tracking/2026-10-14_18-52-53_s5c-03b-h0mirror/params/env.yaml):

| term | std | weight |
|---|---|---|
| motion_global_root_pos | 0.3 | 0.5 |
| motion_global_root_ori | 0.4 | 0.5 |
| motion_body_pos (relative, re-anchored to the robot each step) | 0.3 | 1.0 |
| motion_body_ori (relative) | 0.4 | 1.0 |
| motion_body_lin_vel (global) | 1.0 | 1.0 |
| motion_body_ang_vel | 3.14 | 1.0 |

Penalties: action_rate -0.1, joint_limit -10, self_collisions -10.

Terminations: anchor_pos is bad_anchor_pos_z_only at 0.25; anchor_ori; ee_body_pos is z-only.

Downstream:
- H1 latent-07 (DAgger from H0, D-053);
- RES_BASE s5c-18-merge17 (two-teacher kickstart through H1, D-084/D-085);
- the rally residual (runs 14-23).

A retrained H0 / H1 moves H1's latent space, so RES_BASE and the residual must be rebuilt (route D's cost, footwork-route doc section 5d).

## Candidate objective changes (one change per run)

- **O1** (RL, motion): motion_global_root_pos std 0.3 -> 1.0. The anchor-position reward keeps paying at 0.6-2 m of lag.
- **O2** (architecture): anchor_pos termination z-only -> full 3D (mdp.bad_anchor_pos) at 0.5 m. Drift ends the episode.
- **O3:** motion_body_lin_vel std 1.0 -> 0.5, a sharper velocity kernel. Not proposed by anyone so far.
- **Other:** for example, a foot-slip penalty, given the 0.25 m/s stance slip.

Data mix: tennis-lafan3 plus footwork-fast (the specialist's 117 accepted clips, 58 min). This is part of the same run, since footwork-fast is the target skill. Say whether adding it counts as a second change.

## Questions for round 54

1. **Correction check** on D-184 and the travel check.
2. **The one objective change** (O1 / O2 / O3 / other) and the data mix. Give the parent (model_63300 or another), the learning rate and schedule (H0 was at a fixed 1e-5), the iterations, and the stroke-retention guard. The tennis strokes must stay within 5 points of model_63300 per stroke type (D-048 / D-079).
3. **Kill and endpoint lines**, coded. Proposed in round 53:
   - at 30 %: travel ratio on footwork-fast FAST >= 0.75;
   - endpoint: FAST success >= 0.95, root-relative MPKPE <= model_63300's + 0.01, stroke retention within 5 points;
   - at the endpoint, a travel line: for example D >= 0.90 on footwork-fast FAST and on LAFAN1.

   Use fresh dev seeds for reads (block 3 from 4220220) and training seeds from 172.
4. **The chain after H0.** H1 re-distil (scripts/distill_latent.py), then the RES_BASE rebuild and the rally re-climb. Is there a cheaper bridge that would show the rally gain earlier? For example, measure the travel ratio of the current rally composite on move-drill spots to confirm it inherits the 0.55 cap before paying for the rebuild.
