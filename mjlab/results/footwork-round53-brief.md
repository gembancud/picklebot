# Panel round 53 brief (footwork phase step 2's route), 2026-10-31

Read first:
- D-182 and D-183 in docs/DECISIONS.md;
- mjlab/results/footwork-review.md;
- scripts/diag/footwork_step2_premise.sh (the frozen rule is in its header);
- results/fw2p-summary.txt, results/fw2p-h0.json and results/fw2p-lat07.json.

## Step 1 (done, D-183)

fw1b-S model_16600 is BODY-OK under mean actions (frozen read C, seed 4220212):
- sustained speed 1.95 F, 2.00 L, 2.10 B, 1.92 R m/s;
- untimed arrival >= 0.990;
- falls 0.36 per 1,000 env-s.

The heading gate printed STEP-2-CLIPS: 0 % of back moves were more than 90 degrees from the net. The robot backpedals and side-shuffles facing the net (videos: artifacts/videos/footwork/fw-back.mp4, fw-left.mp4).

## Step 2 premise checks (frozen, D-183)

- **Clips:** 128 recorded with mean actions (training seed 171; 3,829 s). 117 were accepted by amass_g1_import unchanged (3,499 s); the 11 rejects were all for skate.
- **Fast content:** fast_lateral_back_s was 716 s before acceptance and 671 s after, so it was kept. For comparison, the AMASS subset had 8 s and LAFAN1 about 45 s.
- **Direction rule:** 117 of 117 pass.
- **Tracking:** tracking_eval.py --per-stroke, 4-s windows, 4 repeats, dev seed 4220214, H0 and latent-07 paired. The first attempt crashed on clip-name mapping before writing any result. tracking_eval now maps the `fwfast_` prefix to `footwork_fast`; no scoring changed.

| | H0 (s5c-03b model_63300) | latent-07 through the encoder |
|---|---|---|
| success, all 816 windows | 0.996 | 0.997 |
| success, FAST windows (ref >= 1.0 m/s) | 0.991 (399) | 0.994 (400) |
| **frozen verdict** | **H0-OK** | **DECODER-OK** |

## A finding the frozen rule does not see

Pelvis ground speed, robot against reference, from scratchpad speedratio.py on the per-window JSON:

| windows | H0 robot / ref (m/s) | H0 ratio p50 | latent-07 robot / ref | latent-07 ratio p50 | global MPKPE | root-relative MPKPE |
|---|---|---|---|---|---|---|
| all | 0.53 / 0.99 | 0.52 | 0.54 / 0.99 | 0.53 | 0.83 m | 0.05 m |
| ref >= 1.0 | 0.64 / 1.18 | 0.52 | 0.65 / 1.18 | 0.54 | 0.96 m | 0.05 m |
| ref >= 1.3 | 0.79 / 1.38 | 0.54 | 0.81 / 1.38 | 0.55 | 1.0 m | 0.06 m |

- **The reference speed is correct.** The npz's stored body_lin_vel_w matches finite differences of body_pos_w (ratio 0.999). The same holds for lafan-g1.npz.
- **The ratio is systematic.** The D-175 speed ladder shows the same about 0.5 ratio: H0 0.557 / 1.172, latent-07 0.585 / 1.173. It appears even on slow walks: a Neutral_FW window ran at 0.35 against 0.59 m/s.
- **Success is blind to it.** The tracking task's anchor termination is `bad_anchor_pos_z_only` (threshold 0.25 m), and ee_body_pos is evidently relative.
- **Reading:** the trackers (H0, and the H1 decoder distilled from it) reproduce the pose relative to the pelvis (0.05 m) but cover only about 54 % of the reference's ground travel, at every speed. The specialist itself made these exact clips in the same physics, so they are physically achievable at full speed.
- **Not yet known:** whether this is a real tracking property, a measurement artefact in tracking_eval (robot root_link_lin_vel_w sampled before the step), or how H0 was rewarded. Check the tracking task's reward terms in artifacts/train/logs/picklebot_tracking/2026-10-14_18-52-53_s5c-03b-h0mirror/params/env.yaml, and the motion command in picklebot_mj/tasks/tracking.py and mjlab's tracking mdp.

## Questions for round 53

1. **Correction check** on D-182 / D-183 and the premise script. Was "success" the right premise metric for "the decoder expresses fast footwork"? (D-176 already said "success ignores speed".)
2. **Is the 0.54 ratio real?** Name the cheapest decisive check and the line it must pass. For example: a direct global-displacement comparison over a window; the same measurement on the walking teacher's own clips (footwork-teacher.npz) or on LAFAN1; or reading H0's reward definition. Be concrete about files.
3. **Step 2's route.** Options:
   - (a) Take DECODER-OK at face value (selection gap): re-distil the H1 prior with footwork weighting, or kickstart the rally residual from the specialist.
   - (b) Treat the travel ratio as a decoder / tracker gap, i.e. route D: fine-tune H0 on footwork-fast + LAFAN1 with global travel rewarded, then re-distil H1.
   - (c) Run the decisive check first.
   - (d) Other.

   Give the frozen line that routes between them.
4. **What this implies** for the rally robot's observed left / back slowness (footwork-route doc, about 1.1-1.5 m/s on misses).

Rules: never loosen a threshold or relabel a printed verdict; one change per run; dev seeds only (block 3, next free 4220217); training seeds from 172; ledger every seed.
