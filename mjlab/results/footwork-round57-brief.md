# Panel round 57 brief: the H1' diagnostic (D-187), 2026-10-31

Read first: D-187 and its addendum in docs/DECISIONS.md, mjlab/results/footwork-review.md (round 56), scripts/diag/h1_fwdec.sh, results/h1fwdec-summary.txt and results/h1fwdec-*.json.

## H1' (decoder-only re-distil from latent-07, teacher h0-fw-02 model_66298)

- Run: 1,400 iterations on the TennisLafan3FF-Root1 motion set, training seed 177 (artifacts/train/latent/h1-fwdec-01/latent_1400.pt).
- Frozen parts (normaliser, encoder, prior) are bit-identical to latent-07.
- Tracking on its own, through the encoder:

| read | H1' | latent-07 |
|---|---|---|
| held-out footwork D (dev 4220241) | **0.956** | 0.582 (that read failed the instrument check) |
| LAFAN1 FAST D (dev 4220234) | 0.859 | 0.782 |
| success by source: tennis / LAFAN1 / mirrored LAFAN1 | 0.874 / 0.851 / 0.828 | 0.934 / 0.888 / 0.831 |
| tracking fall rate | 0.0062 | 0.0066 |
| strokes vs latent-07 | serve **-23.3**, smash -8.0, backhand volley -4.8, forehand volley -3.5, forehand -2.4, backhand 0.0 points | |

- The fidelity guard (any stroke > 3 points) fired, so the result is **CONFOUNDED**.
- The decoder copied the teacher's travel (held-out D 0.956 >= 0.85).
- The decoder did not keep the teacher's strokes. The teacher itself lost only 3.3-3.8 points against s5c-03b.
- The distillation rollouts ran on TL3FF's collapsed sampler (about 94 % of tennis on one serve window).

## Paired zero-shot rally bridge (dev 4220233)

Rally 22b model_30200 on Measure60-RallyLamR2, mean actions, latent-07 vs H1':

| | latent-07 | H1' |
|---|---|---|
| R (left / back vs the specialist) | 0.636 | **0.824** |
| sustained p50 by sector (m/s) | 1.16-1.45 | 1.54-1.84 |
| peak p50 (m/s) | 1.40-1.66 | 2.12-2.44 |
| **falls per 1,000 env-s** | 7.1 | **202** |
| spots: arrived / timed out / fell / censored | 25,486 / 1,394 / 871 / 2,408 | **125 / 8,638 / 24,848** / 1,024 |
| untimed arrival | 0.87-0.97 | **0.00-0.006** |
| settled spots | 1,102 | 24 |

- The frozen rule prints **dR = +0.188 -> CAP-MOVES, CONFOUNDED**. As reported: R(H1') = 0.824, MIXED.
- What the rule does not see: zero-shot, the composite falls about 28x as often and almost never arrives. Fallen spots are not booked, so the sustained speeds come mostly from spots that ran to their time-out without stopping.
- H1' on its own does not fall (0.0062). The collapse is the composite's mismatch: RES_BASE and the residual were trained on latent-07's decoder dynamics.

## Questions for round 57

1. **Correction check** on D-187 and the diagnostic. The rule had no falls or arrival line for the bridge. Should D-188 record that as a pre-registration gap, without relabelling?
2. **What does this show?** Faster leg motion transmits through the frozen prior into the composite: peak speed went from 1.5 to 2.3 m/s. The composite cannot balance or stop with the new decoder zero-shot. Is the travel cap therefore in the motion layer? And is the remaining question only adaptation, i.e. RES_BASE / residual re-training on H1'?
3. **Next single step**, with coded lines. Options:
   - (a) Fix H1' stroke fidelity first. Re-distil with stroke protection, e.g. a per-source uniform floor in the tracking sampler (picklebot_mj/tasks/tracking.py:117), or distil on tennis-lafan3 + footwork-fast with balanced sampling. Gate: strokes within 3 points of latent-07 and held-out D >= 0.85.
   - (b) A short adaptation probe: fine-tune the rally residual on H1' (rally run 22b's task, PICKLEBOT_CONTROLLER = H1', learning rate 1e-4, a few hundred iterations). Measure whether falls return to the latent-07 level while speed stays up. This is evaluation-grade only.
   - (c) The full route-D chain on H1': RES_BASE kickstart rebuild (s5c-14 / 15 / 17 / 18 pattern, about 8 GPU-h), then the rally re-climb.
   - (d) Stop route D: the composite rebuild cost is too high. Pick another route to faster footwork, e.g. the leg-joint residual or a specialist kickstart.
4. **Order and costs.** Fixing strokes before any rebuild seems necessary. Is (b) worth doing before (a) to learn whether adaptation is easy?

Seeds: dev 4220242 onward (spares 4220227-4220229, 4220235-4220240). Training seeds from 178.
