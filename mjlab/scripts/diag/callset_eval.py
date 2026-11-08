"""D-252: the call-and-set read. scripts/stage2_eval.py (deterministic policy, development seeds) on the call-and-set
task, then the target's lines from CallSetDrill's counters (picklebot_mj/callset_rule.py).

Usage: python scripts/diag/callset_eval.py --task Picklebot-Footwork-CallSet-RallyLamR2-G1 --checkpoint PATH --envs 1024
       --seconds 120 --seed 42204xx --move-prob 1.0 --json OUT.json   (any stage2_eval.py flag; --json required)
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mjlab.tasks  # noqa: F401,E402

import picklebot_mj.tasks.footwork_specialist  # noqa: F401,E402  (registers the tasks)
import stage2_eval  # noqa: E402

from picklebot_mj import callset_rule as cr  # noqa: E402


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


if __name__ == "__main__":
    out_path = arg("--json")
    assert out_path, "--json is required"
    stage2_eval.main()
    out = json.load(open(out_path))
    c = out["move_drill"]["call_set"]
    r = cr.read(c)
    falls = 1000.0 * out["robot_falls"] / (out["envs"] * out["sim_seconds"])
    ok, lines = cr.target_lines(r)
    for line in lines:
        print(line)
    print(f"(reported) falls per 1,000 env-s {falls:.3f}")
    out["call_set_read"] = {"pass": r["pass"], "wilson": r["wilson"], "judged": r["judged"], "types": r["types"],
                            "set": r["set"], "ready": r["ready"], "reach": r["reach"], "ladder": r["ladder"],
                            "start_s": r["start_s"], "falls_per_1000_env_s": falls, "target_lines_met": ok}
    json.dump(out, open(out_path, "w"), indent=1)
