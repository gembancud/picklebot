"""One-line-per-family summary of an h4_eval.sh run against the S-D3-style-c baseline (the H4 gate reference).

Usage: python scripts/h4_summary.py TAG [--baseline results/stage5-sd3stylec]
Main metric (D-056 plateau rule): the no-hint legal-return rate pooled over all 14 families (target A).
"""
import argparse
import json

ap = argparse.ArgumentParser()
ap.add_argument("tag")
ap.add_argument("--baseline", default="results/stage5-sd3stylec")
a = ap.parse_args()
R = f"results/stage5b-h4-{a.tag}"
cur, base = json.load(open(f"{R}-nohint-A.json")), json.load(open(f"{a.baseline}-nohint-A.json"))
gain = json.load(open(f"{R}-nohint-gain.json"))
gain = gain.get("per_family", gain)
style = json.load(open(f"{R}-style.json"))
ret, par = json.load(open(f"{R}-retention-A.json")), json.load(open(f"{R}-retention-parent-A.json"))
print(f"{a.tag}: main metric (no-hint legal, pooled) {cur['legal_return_rate']:.4f} (baseline "
      f"{base['legal_return_rate']:.4f}); robot falls/episode {cur['robot_fall_rate_per_episode']:.4f}; "
      f"recovery median {cur['recovery']['error_median_m']} m; style median {style.get('nearest_clip_distance_median')}")
print(f"{'family':15s} {'legal':>7s} {'base':>7s} {'diff':>7s}  gate(>=base-5)  retention  A/B gain")
for fam, r in cur["per_family"].items():
    b = base["per_family"][fam]["legal_return"]
    d = r["legal_return"] - b
    rt = ret["per_family"].get(fam, {}).get("legal_return")
    rp = par["per_family"].get(fam, {}).get("legal_return")
    rtxt = f"{rt - rp:+.3f}" if rt is not None and rp is not None else "   -  "
    g = gain.get(fam, {})
    g = f"{g.get('assignment_gain', float('nan')):+.3f} {g.get('assignment_gain_ci95')}"
    print(f"{fam:15s} {r['legal_return']:7.3f} {b:7.3f} {d:+7.3f}  {'pass' if d >= -0.05 else 'FAIL':>5s}  {rtxt:>9s}  {g}")
