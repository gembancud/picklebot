#!/usr/bin/env bash
# D-187 diagnostic (panel round 56, (d)): does a footwork-trained H0 lift the rally composite's travel cap? Diagnostic
# only: no gate is consumed, h0-fw-02 stays H0F-FAIL, and nothing here can promote h0-fw-02 or amend a D-185 / D-186 line.
#   1. H1' = latent-07's DECODER re-distilled by DAgger from h0-fw-02's endpoint (2026-10-31_07-51-57_h0-fw-02b /
#      model_66298) on its own motion set (Picklebot-Tracking-TennisLafan3FF-Root1-Huge-G1: tennis-lafan3 + footwork-fast);
#      input normaliser, encoder and prior frozen (--decoder-only; RES_BASE and rally 22b live in latent-07's z-space),
#      as scripts/h5f_c2_h1decoder.sh: lr 1e-4, beta 1 -> 0 over the first 5 %, KL 0, prior BC 0.5, smoothness 0.005,
#      1,400 iterations or the 6,900-s cap, training seed 177. Frozen parts asserted bit-identical to latent-07.
#   2. Fidelity guard: tracking_eval --latent --per-stroke on TennisLafan3-Huge, H1' vs latent-07 paired on dev 4220234:
#      if any stroke type is > 3 points below latent-07, the bridge read is labelled CONFOUNDED. Reported with it: H1'
#      travel D on LAFAN1 (same read) and on the held-out footwork clips (FootworkFastHO, dev 4220241, H1' and latent-07).
#   3. Bridge, paired on dev 4220233: rally 22b model_30200 on Picklebot-Footwork-Measure60-RallyLamR2-G1 (mean actions,
#      1,024 envs, 120 s) with latent-07 and with H1' (PICKLEBOT_CONTROLLER); R as scripts/diag/footwork_bridge.sh
#      (mean of left / back sustained p50 over the specialist's on fw1d-C). dR = R(H1') - R(latent-07):
#      CAP-MOVES if dR >= +0.10; NO-MOVE if dR <= +0.03; else MIXED.
#   Qualifiers: CONFOUNDED (fidelity guard), DECODER-NOT-COPIED (H1' held-out footwork D < 0.85, RL); reported only: R(H1')
#   >= 0.85 TRANSMITS / <= 0.70 NOT-TRANSMITTED (coach, RL). Then (D-187): NO-MOVE -> stop the H0 route, re-ask the panel;
#   otherwise the panel picks the next H0 run (round 57).
set -uo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name |distill_latent" > /dev/null && { echo "a trainer is running: not started"; exit 1; }
TEACHER=artifacts/train/logs/picklebot_tracking/2026-10-31_07-51-57_h0-fw-02b/model_66298.pt
LAT=artifacts/train/latent/latent-07/latent_10651.pt
RUN=h1-fwdec-01; D=artifacts/train/latent/$RUN; R=results/h1fwdec
[ -f $TEACHER ] || { echo "missing teacher"; exit 1; }
if [ ! -f artifacts/train/$RUN.exit.json ]; then
  bash scripts/latent_run.sh $RUN --teacher $TEACHER --task Picklebot-Tracking-TennisLafan3FF-Root1-Huge-G1 --init $LAT \
    --decoder-only --iterations 1400 --beta-frac 0.05 --lr 1e-4 --kl-start 0 --kl-end 0 --prior-bc 0.5 --smooth 0.005 \
    --seed 177 --max-seconds 6900
fi
echo "distil: $(cat artifacts/train/$RUN.exit.json)"
CK=$(ls $D/latent_*.pt | sort -V | tail -1); echo "H1' endpoint $CK"
python - $LAT $CK <<'PY' | tee $R-frozen.txt
import sys, torch
a, b = (torch.load(p, map_location="cpu", weights_only=False)["model"] for p in sys.argv[1:3])
diff = [k for k in a if not k.startswith("decoder.") and not torch.equal(a[k], b[k])]
print("frozen parts identical:", not diff, diff[:5])
sys.exit(0 if not diff else 1)
PY
[ ${PIPESTATUS[0]} -eq 0 ] || { echo "frozen parts changed: stop"; exit 1; }
TE="python scripts/motion/tracking_eval.py --latent --per-stroke --repeats 4"
for who in new old; do
  c=$CK; [ $who = old ] && c=$LAT
  [ -s $R-tl-$who.json ] || $TE --checkpoint $c --task Picklebot-Tracking-TennisLafan3-Huge-G1 --seed 4220234 --json $R-tl-$who.json > $R-tl-$who.log 2>&1
  [ -s $R-ho-$who.json ] || $TE --checkpoint $c --task Picklebot-Tracking-FootworkFastHO-G1 --seed 4220241 --json $R-ho-$who.json > $R-ho-$who.log 2>&1
done
RALLY=$(ls -d artifacts/train/logs/picklebot_return_stand/*_rally-22b-readcfg | tail -1)/model_30200.pt
for who in old new; do
  [ -s $R-bridge-$who.json ] && continue
  if [ $who = new ]; then export PICKLEBOT_CONTROLLER=$PWD/$CK; else unset PICKLEBOT_CONTROLLER; fi
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-RallyLamR2-G1 --checkpoint $RALLY --envs 1024 \
    --seconds 120 --seed 4220233 --move-prob 1.0 --json $R-bridge-$who.json > $R-bridge-$who.log 2>&1
done
unset PICKLEBOT_CONTROLLER
python - <<'PY' | tee $R-summary.txt
import json
from picklebot_mj import bodyspeed_rule as bsr, h0fw_rule as hr, travel_rule as tr
J = lambda t: json.load(open(f"results/h1fwdec-{t}.json"))  # noqa: E731
sn, so = hr.strokes(J("tl-new")), hr.strokes(J("tl-old"))
worst = min(sn[s] - so[s] for s in sn)
conf = worst < -0.03
print("fidelity: strokes H1' - latent-07", {s: round(sn[s] - so[s], 3) for s in sn}, "-> CONFOUNDED" if conf else "-> ok")
for t in ("tl", "ho"):
    for who in ("new", "old"):
        s = hr.lafan_stats(J(f"{t}-{who}")) if t == "tl" else tr.read_stats(J(f"{t}-{who}"))
        print(f"travel {t} {who}: D {s.get('D', float('nan')):.3f} over {s.get('envs')} envs, instrument_ok {s.get('instrument_ok')}")
spec = json.load(open("results/fw1d-C.json"))["footwork_route"]["sectors"]
R = {}
for who in ("old", "new"):
    comp = bsr.sectors(J(f"bridge-{who}")["move_drill"]["footwork"])
    R[who] = sum(comp[i]["sustained_p50"] / spec[i]["sustained_p50"] for i in (2, 4)) / 2
    print(f"bridge {who}: R {R[who]:.3f}; sustained by sector", [round(x["sustained_p50"], 2) for x in comp],
          "arrival", [round(x["arrival"], 3) for x in comp])
dR = R["new"] - R["old"]
v = "CAP-MOVES" if dR >= 0.10 else "NO-MOVE" if dR <= 0.03 else "MIXED"
d_ho = tr.read_stats(J("ho-new")).get("D", float("nan"))
copied = d_ho >= 0.85  # RL: the decoder copied the teacher's travel
absR = "TRANSMITS" if R["new"] >= 0.85 else "NOT-TRANSMITTED" if R["new"] <= 0.70 else "MIXED"  # reported (coach / RL)
print(f"dR = {dR:+.3f} -> {v}" + (" (CONFOUNDED by the fidelity guard)" if conf else "")
      + ("" if copied else f" (DECODER-NOT-COPIED: H1' held-out D {d_ho:.3f} < 0.85)"))
print(f"reported: R(H1') {R['new']:.3f} -> {absR} (>= 0.85 / <= 0.70)")
json.dump({"dR": dR, "R": R, "verdict": v, "confounded": conf, "worst_stroke": worst, "decoder_copied": copied,
           "d_ho_new": d_ho, "absolute": absR}, open("results/h1fwdec-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/h1fwdec.done
