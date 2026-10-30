"""scripts/stage2_eval.py (deterministic policy, development seeds) with the footwork specialist tasks registered, then
the drill counters routed through bodyspeed_rule with falls and a config check computed in code (D-182; round 52: the
first version passed falls=None, so line (e) printed FAIL and the verdict was MIXED).

Falls per 1,000 env-s = 1000 robot_falls / (envs x sim_seconds); robot_falls must equal the drill's fell count (every
episode is a move episode). Config check (on the registered task, which stage2_eval does not change in these fields):
episode_length_s 60, footwork_dist (3, 5), footwork_pay "settled", fw_* reward functions, and --move-prob 1.0.

Usage: python scripts/diag/footwork_eval.py --task Picklebot-Footwork-Measure60-G1 --checkpoint PATH --envs 1024
       --seconds 120 --seed 42202xx --move-prob 1.0 --json OUT.json   (any stage2_eval.py flag; --json required)
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mjlab.tasks  # noqa: F401,E402

import picklebot_mj.tasks.footwork_specialist as fs  # noqa: E402  (registers the footwork tasks)
import stage2_eval  # noqa: E402

from picklebot_mj import bodyspeed_rule as bsr  # noqa: E402


def config_missing(task: str, move_prob: str | None) -> list[str]:
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg(task)
    b = cfg.actions["ball"]
    miss = []
    if cfg.episode_length_s != fs.MEASURE_EPISODE_S:
        miss.append("episode_length_s")
    if tuple(getattr(b, "footwork_dist", ())) != fs.MEASURE_DIST:
        miss.append("footwork_dist")
    if getattr(b, "footwork_pay", None) != "settled":
        miss.append("footwork_pay")
    for k, f in (("move_track_lin_vel", fs.fw_track_lin_vel), ("pose", fs.fw_posture)):  # absent in rally tasks: reported
        if k not in cfg.rewards or cfg.rewards[k].func is not f:
            miss.append(f"{k}.func")
    if move_prob is None or float(move_prob) != 1.0:
        miss.append("move_prob")
    return miss


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


if __name__ == "__main__":
    out_path = arg("--json")
    assert out_path, "--json is required"
    stage2_eval.main()
    out = json.load(open(out_path))
    c = out["move_drill"]["footwork"]
    assert out["robot_falls"] == sum(c["fell"]), (out["robot_falls"], sum(c["fell"]))
    falls = 1000.0 * out["robot_falls"] / (out["envs"] * out["sim_seconds"])
    miss = config_missing(arg("--task"), arg("--move-prob"))
    r = bsr.route(c, falls, miss)
    fin = [s["arrived"] + s["timed_out"] + s["fell"] for s in r["sectors"]]
    for s, f in zip(r["sectors"], fin):
        i = s["sector"]
        h = c["mid_heading_hist"][i]
        over90 = sum(h[9:]) / max(1, sum(h))
        print(f"{s['name']:13s} sustained {s['sustained_p50']} untimed {s['arrival']} "
              f"deadline {c['deadline'][i] / max(1, f):.3f} settled {c['settled'][i] / max(1, f):.3f} "
              f"settle_s {c['settle_time_sum'][i] / max(1, c['settled'][i]):.2f} mid>90deg {over90:.3f} "
              f"fell {s['fell']} cens {s['censored']}")
    print(f"censored share {r['censored_share']:.4f}, falls per 1,000 env-s {falls:.3f}, config missing {miss}")
    for line in r["lines"]:
        print("  " + line)
    print("VERDICT:", r["verdict"])
    out["footwork_route"] = {**r, "falls_per_1000_env_s": falls, "config_missing": miss}
    json.dump(out, open(out_path, "w"), indent=1)
