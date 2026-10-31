# Panel round 56 brief: h0-fw-02 endpoint H0F-FAIL (2026-10-31)

Read first:
- D-185 and D-186 in docs/DECISIONS.md;
- mjlab/results/footwork-review.md (rounds 54-55);
- picklebot_mj/h0fw_rule.py and scripts/diag/h0_fw02.sh;
- results/h0fw02-endpoint.txt, results/h0fw02-kill.txt and results/h0fw02-end*-{child,parent}.json.

## h0-fw-02

- **Setup:** O1 weight 2.0, std 1.0. From s5c-03b model_63300, 3,000 iterations at a fixed 1e-5. Data: tennis-lafan3 plus footwork-fast.
- **Kill check at +900:** CONTINUE, with D_fw 0.924 and D_lafan 0.852.
- **Endpoint** (checkpoint 2026-10-31_07-51-57_h0-fw-02b/model_66298): **H0F-FAIL**.

### Endpoint reads

Child vs parent, on dev seeds 4220222 (fw), 4220223 / 4220224 (tl) and 4220232 (fwHO).

| line | value | limit | |
|---|---|---|---|
| D_fw (in-sample) | 0.962 | 0.90-1.10 | ok |
| **D_fwHO (held-out, 57 clips never trained on)** | **0.963** | 0.90-1.10 | ok |
| **D_lafan** (mean of two seeds; parent 0.737) | **0.865** | >= 0.90 | **FAIL** |
| footwork-fast FAST success | 1.000 | >= 0.95 | ok |
| tennis r_mpkpe - parent | +0.002 | <= +0.010 | ok |
| serve / smash / backhand volley - parent | **-3.8 / -3.7 / -3.3 points** | >= -3 | **FAIL** |
| forehand volley / forehand / backhand - parent | +0.7 / -1.6 / -1.2 | >= -3 | ok |
| LAFAN1 / mirrored LAFAN1 success - parent | -1.7 / -0.3 | >= -3 | ok |
| S_fw - S_parent | +0.023 | <= +0.03 | ok |
| tennis \|disp err\| p50 | 0.137 | <= 0.18 | ok |
| tennis end-effector error - parent | +0.003 | <= +0.01 | ok |

Stroke success, child vs parent, by seed (units: serve 75, smash 147, the others 110-136):

| stroke | seed 4220223 | seed 4220224 |
|---|---|---|
| serve | 0.860 vs 0.887 | 0.843 vs 0.893 |
| smash | 0.859 vs 0.895 | 0.852 vs 0.891 |
| backhand volley | 0.943 vs 0.976 | 0.941 vs 0.974 |

### LAFAN1 travel D by family (FAST windows, seed 4220223, child vs parent)

| family | child | parent |
|---|---|---|
| run | 0.896 | 0.769 |
| run, mirrored | 0.898 | 0.778 |
| sprint | 0.835 | 0.734 |
| sprint, mirrored | 0.852 | 0.690 |
| walk | 0.827 | 0.698 |
| walk, mirrored | 0.834 | 0.704 |
| fightAndSports | 0.840 | 0.572 |
| fightAndSports, mirrored | 0.680 | 0.597 |

Tennis slow windows: 0.693 against 0.655.

### Trajectory

| point | D_lafan | D_fw | worst stroke vs parent |
|---|---|---|---|
| +900 | 0.852 | 0.924 | -2.3 points |
| +3,000 | 0.865 | 0.962 | -3.8 points |

Training error_anchor_pos stayed flat at 0.29-0.33 through segment 2. That is a plateau, with slow stroke erosion.

## Questions for round 56

1. **Correction check** on D-186 and the run.
2. **D-186 requires an answer:** is O1, at any weight, the wrong lever for the last 0.035 on LAFAN1? Or is the LAFAN1 0.90 line unreachable for a reason the reference itself explains? For example:
   - LAFAN1 reference skate is about 0.13 m/s, near the 0.15 limit, per motion's round-54 measure;
   - mirrored fightAndSports is at 0.68.

   Cite evidence. Never loosen a line without naming a changed premise.
3. **Next single change, its parent, and the coded lines.** Options:
   - (a) O2 (full-3D anchor termination at 0.5 m) from model_66298. The lag is smaller now, so it is less of a shock than in round 54.
   - (b) Protect the strokes, e.g. tennis share 0.5 -> 0.6 or a lower learning rate, as a separate change.
   - (c) Accept h0-fw-02 as the step-2 teacher on the held-out footwork gate. This is allowed only if a premise change is named and accepted under experiment design's rules; otherwise it is a loosening.
   - (d) Other, e.g. continue the H1 re-distil and zero-shot bridge with h0-fw-02 as a **diagnostic only** (no gate), to learn whether the rally composite's cap moves before spending on further H0 runs.
4. **Expected value toward the rally target.** The rally target needs fast left / back footwork, which the held-out footwork read now shows at 0.963. What is the cheapest next measurement of rally value?

Seeds: dev 4220233 onward (spares 4220227-4220229); training seeds from 177.
