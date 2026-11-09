# Panel round 111 brief: call-and-set baseline (Q = 0 %) and the first lever's form, 2026-11-09

Read first: mjlab/results/footwork-target.md (frozen, D-252); D-251, D-252 and the damping read at the end of docs/DECISIONS.md; round 110 in mjlab/results/footwork-review.md; the drill mjlab/picklebot_mj/tasks/call_set.py and its lines picklebot_mj/callset_rule.py; results/cs-base-summary.txt, results/cs-diag-summary.txt; docs/PANEL.md. Training code to reuse: footwork_specialist.py (FootworkDrill rewards: fw_track_lin_vel, settled pay, fw_first_step), return_stand.py (rally composite, drill courts, pair courts), scripts/diag/lc109.sh (the latest rally driver), scripts/diag/qk84.sh (the footwork-specialist driver).

## Baseline (Q zero-shot, mean actions, 1,024 envs x 120 s)

| | dev 4220451 | dev 4220452 |
|---|---|---|
| pass (headline, 2.5 m/s) | 0.0000 of 52,031 | 0.0000 of 51,950 |
| SET / READY / REACH at T | 0.108 / 0.008 / 0.058 | 0.106 / 0.008 / 0.056 |
| pace ladder 1.5 / 2.0 / 2.5 m/s | 0.003 / 0.001 / 0.001 | 0.003 / 0.001 / 0.001 |
| falls per 1,000 env-s | 21.3 | 22.2 (Q on the Measure60 move drill: 3.55) |

At T (dev 4220452): pelvis still moving 0.89, feet down 0.75, upright 0.90; paddle forward in box 0.45, high in box 0.07 (mean height 0.64 m, box 0.9-1.2), on the called side 0.52; pelvis within 0.25 m of the stance spot 0.006 (ever since the call 0.006); mean pelvis-to-spot distance 1.22 m. Start (0.10 m toward the spot) 0.46 s. The prediction written before the read (pass <= 0.05; ladder 1.5 m/s 0.05-0.30; SET 0.3-0.7; READY <= 0.3; REACH 0.3-0.7) was right on the headline and too high on the parts.

Also: the damping premise read (zero-shot damping x0.5) gave no faster first step and 3x falls, so by D-252's rule the first lever is the call drill in Q's training.

## Questions

1. **Correction check** on D-252, the drill as built (call_set.py: kinematic ghost ball, spot input = the stance spot, judged at T) and the baseline. Is anything mis-built or mis-read? (Note: falls are 6x the move drill's.)
2. **The first lever's form:** parent (Q), the one change (the call drill in training), how it is rewarded (which of SET / READY / REACH / reaching the spot, paid when; the teacher command's cap; how the reward reaches a residual on a frozen base), where it trains (drill courts only, share of envs), what keeps the rally skill (the guard: feeder-ball legal within 5 points of Q), length, seeds (training from 263, dev from 4220453), smoke / kill / gate lines (the gate is a call-and-set read on fresh dev seeds; the ladder is the climbable signal while the headline is near 0).
3. **Estimate**: what this lever can reach on the ladder and the headline, and which lever is next if it is flat.

Under 300 words.
