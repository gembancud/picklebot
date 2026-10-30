#!/usr/bin/env bash
# Footwork phase step 2 premise checks (D-183; panel rounds 51-52, motion and architecture). Evaluation only, no training.
# Teacher: fw1b-S model_16600, BODY-OK(mean-action) by the frozen read C (D-182). Heading gate: STEP-2-CLIPS (0 % of back
# moves > 90 deg at mid-move).
#   1. Videos (for review and the user): scripts/stage2_eval.py --video through footwork_eval.py, mean actions, 1 env,
#      20 s, Picklebot-Footwork-Measure60-G1, spots in sector 4 (back; box flips give forward) and sector 2 (left; flips
#      give right); dev seeds 4220215 / 4220216.
#   2. Clips: scripts/motion/record_policy_clips.py, mean actions, task Picklebot-Footwork-Specialist-Settle-G1 (spots
#      1-5 m, 8 sectors uniform), 128 envs x 30 s, segments >= 6 s, fallen segments dropped, training seed 171.
#   3. Acceptance: each CSV saved as raw/g1/<stem>_50_jpos.npy and run through scripts/motion/amass_g1_import.py UNCHANGED
#      (>= 1 s; no joint within 2 deg of its limit in > 25 % of frames; skate median <= 0.15 m/s; grounded >= 95 %).
#   4. Encoder path: accepted clips -> footwork-fast.npz (clip_source 1) -> scripts/motion/tracking_eval.py --per-stroke
#      (4-s windows, 4 repeats) for H0 (s5c-03b model_63300) and --latent latent-07 (latent_10651), dev seed 4220214,
#      paired.
# Frozen rule (printed by the summary):
#   FAST windows = windows whose reference pelvis speed >= 1.0 m/s (above the old walking teacher's 0.72 m/s median, D-081).
#   latent-07 success on FAST windows >= 0.95 -> DECODER-OK (route D not needed; the gap is the prior's selection);
#   < 0.90 -> DECODER-GAP (route D's premise: H0 / H1 must learn these clips); else MIXED.
#   H0 success on FAST windows >= 0.95 -> H0-OK (H0 can teach them), else H0-GAP (H0 fine-tune first). Reported with
#   both: overall success, clips kept / accepted, reject reasons, fast_lateral_back_s before and after acceptance
#   (STRIPPED if after < 0.5 x before), and the frozen amass_footwork_npz.sh direction rule's pass share.
set -euo pipefail
cd /mnt/f/dev/picklebot-mjlab/mjlab; source ~/envs/picklebot-mj/bin/activate; export PYTHONWARNINGS=ignore
unset PICKLEBOT_LAM_R PICKLEBOT_RES_BASE PICKLEBOT_LEG_R PICKLEBOT_TEACHER PICKLEBOT_TEACHER_GAIN PICKLEBOT_CONTROLLER
pgrep -f "run-name " > /dev/null && { echo "a trainer is running: not started"; exit 1; }
CK=artifacts/train/logs/picklebot_return_stand/2026-10-31_01-16-15_fw1b-S/model_16600.pt
H0=artifacts/train/logs/picklebot_tracking/2026-10-14_18-52-53_s5c-03b-h0mirror/model_63300.pt
LAT=artifacts/train/latent/latent-07/latent_10651.pt
O=artifacts/motion/footwork-fast; R=results/fw2p; V=artifacts/videos/footwork
mkdir -p $V
for v in "4 4220215 back" "2 4220216 left"; do
  set -- $v
  [ -s $V/fw-$3.mp4 ] && continue
  python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-G1 --checkpoint $CK --envs 1 --seconds 20 \
    --seed $2 --move-prob 1.0 --sector $1 --view behind_close --video $V/fw-$3.mp4 --json $R-video-$3.json > $R-video-$3.log 2>&1 \
    || echo "video $3 failed (see $R-video-$3.log)"
done
if [ ! -d $O/csv ]; then
  python scripts/motion/record_policy_clips.py --checkpoint $CK --out $O/csv --task Picklebot-Footwork-Specialist-Settle-G1 \
    --envs 128 --seconds 30 --min-seconds 6 --seed 171 --prefix fwfast 2>&1 | tail -1 | tee $R-record.txt
fi
python -I - $O <<'PY'
import sys, pathlib, numpy as np
o = pathlib.Path(sys.argv[1]); raw = o / "raw" / "g1"; raw.mkdir(parents=True, exist_ok=True)
for f in sorted((o / "csv").glob("*.csv")):
    np.save(raw / f"{f.stem}_50_jpos.npy", np.loadtxt(f, delimiter=","))
print(len(list(raw.glob("*.npy"))), "npy files")
PY
[ -s $O/accepted/summary.json ] || python -I scripts/motion/amass_g1_import.py --src $O/raw --out $O/accepted | tail -1
if [ ! -s $O/footwork-fast.npz ]; then
  python scripts/motion/csv_to_npz_local.py $O/accepted $O/footwork-fast-src0.npz --input-fps 30 --output-fps 50 2>&1 | tail -1
  python -I - $O <<'PY'
import sys, numpy as np
d = dict(np.load(f"{sys.argv[1]}/footwork-fast-src0.npz"))
d["clip_source"] = np.ones(len(d["clip_starts"]), dtype=int)  # non-tennis: fixed windows in --per-stroke mode
np.savez(f"{sys.argv[1]}/footwork-fast.npz", **d)
print(len(d["clip_starts"]), "clips,", len(d["joint_pos"]), "frames")
PY
fi
[ -s $R-h0.json ] || python scripts/motion/tracking_eval.py --checkpoint $H0 --task Picklebot-Tracking-FootworkFast-G1 \
  --per-stroke --repeats 4 --seed 4220214 --json $R-h0.json > $R-h0.log 2>&1
[ -s $R-lat07.json ] || python scripts/motion/tracking_eval.py --latent --checkpoint $LAT --task Picklebot-Tracking-FootworkFast-G1 \
  --per-stroke --repeats 4 --seed 4220214 --json $R-lat07.json > $R-lat07.log 2>&1
python -I - $O <<'PY' | tee $R-summary.txt
import json, sys, pathlib
o = pathlib.Path(sys.argv[1])
FAST, OK, GAP = 1.0, 0.95, 0.90
summ = json.load(open(o / "accepted" / "summary.json"))
reps = [json.load(open(p)) for p in sorted((o / "accepted").glob("*.json")) if p.name not in ("summary.json", "accepted.json")]
pre = sum(r.get("fast_lateral_back_s", 0.0) for r in reps)
post = sum(r.get("fast_lateral_back_s", 0.0) for r in reps if r.get("accepted"))
acc = [r for r in reps if r.get("accepted")]
dirok = [r for r in acc if r["moving_frames_frac"] >= 0.3 and r["dir_frac"]["left"] + r["dir_frac"]["back"] + r["dir_frac"]["right"] >= 0.5]
print(f"clips {summ['clips']}, accepted {summ['accepted']} ({summ['accepted_seconds']} s), rejects {summ['rejects']}")
print(f"fast_lateral_back_s before {pre:.1f} s, after {post:.1f} s -> {'STRIPPED' if post < 0.5 * pre else 'kept'}")
print(f"direction rule (amass_footwork_npz.sh): {len(dirok)} / {len(acc)} accepted clips pass")
out = {"acceptance": summ, "fast_lateral_back_s": [pre, post], "direction_pass": [len(dirok), len(acc)]}
for tag in ("h0", "lat07"):
    d = json.load(open(f"results/fw2p-{tag}.json"))
    fast = [u for u in d["per_clip"] if u["ref_pelvis_speed"] >= FAST]
    sf = sum(u["success"] for u in fast) / len(fast) if fast else None
    out[tag] = {"success": d["success_rate"], "fast_units": len(fast), "fast_success": sf, "units": d["units"],
                "pelvis_speed": d["pelvis_speed"], "ref_pelvis_speed": d["ref_pelvis_speed"]}
    print(f"{tag}: success {d['success_rate']:.3f} over {d['units']} windows; FAST (ref >= {FAST} m/s) {len(fast)} windows, "
          f"success {sf if sf is None else round(sf, 3)}; pelvis {d['pelvis_speed']:.2f} vs ref {d['ref_pelvis_speed']:.2f} m/s")
lf, hf = out["lat07"]["fast_success"], out["h0"]["fast_success"]
v_lat = "n/a" if lf is None else ("DECODER-OK" if lf >= OK else "DECODER-GAP" if lf < GAP else "MIXED")
v_h0 = "n/a" if hf is None else ("H0-OK" if hf >= OK else "H0-GAP")
print(f"VERDICT latent-07: {v_lat}; H0: {v_h0}")
out.update(verdict_latent=v_lat, verdict_h0=v_h0)
json.dump(out, open("results/fw2p-summary.json", "w"), indent=1)
PY
echo done > artifacts/train/fw2p.done
