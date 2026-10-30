"""scripts/stage2_eval.py (deterministic policy, development seeds) with the footwork specialist tasks registered, then
the drill counters routed through bodyspeed_rule (D-182 diagnostic: is held arrival limited by action noise?).

Usage: python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-G1 --checkpoint PATH --envs 1024
       --seconds 120 --seed 42202xx --move-prob 1.0 --json OUT.json   (any stage2_eval.py flag)
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mjlab.tasks  # noqa: F401,E402

import picklebot_mj.tasks.footwork_specialist  # noqa: F401,E402  (registers the footwork tasks)
import stage2_eval  # noqa: E402

from picklebot_mj import bodyspeed_rule as bsr  # noqa: E402

if __name__ == "__main__":
    stage2_eval.main()
    out_path = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    if out_path:
        out = json.load(open(out_path))
        c = out["move_drill"]["footwork"]
        r = bsr.route(c, None, [])
        fin = [s["arrived"] + s["timed_out"] + s["fell"] for s in r["sectors"]]
        for s, f in zip(r["sectors"], fin):
            i = s["sector"]
            print(f"{s['name']:13s} sustained {s['sustained_p50']} untimed {s['arrival']} "
                  f"deadline {c['deadline'][i] / max(1, f):.3f} settled {c['settled'][i] / max(1, f):.3f} "
                  f"settle_s {c['settle_time_sum'][i] / max(1, c['settled'][i]):.2f} fell {s['fell']} cens {s['censored']}")
        print("censored share", r["censored_share"])
        out["footwork_route_no_falls"] = r
        json.dump(out, open(out_path, "w"), indent=1)
