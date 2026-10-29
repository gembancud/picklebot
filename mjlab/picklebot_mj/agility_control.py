"""Coded CPU positive control for the deadline move drill (D-172, the second agility screen). Pure torch on the CPU, no
simulator: a kinematic point mass whose ground velocity follows the drill's OWN command (DeadlineMoveDrill.command,
called every control step) through a first-order lag (tau 0.2 s), driven through the drill's own spot draw
(_new_spot: 1.0-3.0 m, 8 uniform sectors, v_req ~ U(1.2, 2.0)), bookkeeping (update, every physics step) and counters,
read with agility_rule.arm_stats. It stands for an ideal, lagged tracker of the teacher command: if it cannot make the
deadlines, the drill measures no policy.

- positive_control(...): the drill in the given mode (default first_entry); passes when deadline arrival (DA) is
  >= DA_MIN (90 %) in EVERY sector.
- hold_reference(...): the same control under the first screen's drill (arrival_mode "hold"); passes when DA is
  < HOLD_DA_MAX (10 %) in every sector, i.e. it reproduces the defect D-172 names (a negative control).

CLI (agility_screen2.sh runs it before launching any arm and refuses on a failure):
    CUDA_VISIBLE_DEVICES= python -m picklebot_mj.agility_control --task Picklebot-Agility-Deadline2-LamR2-G1 \\
        [--task ...] [--json results/agility2-control.json]
Each task's drill settings (arrival mode, distance and v_req ranges, heading radius) and its control dt (physics
timestep x decimation) are read from the registered env cfg (no simulator is built).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from types import SimpleNamespace

import torch

from picklebot_mj import agility_rule as ar
from picklebot_mj.tasks import deadline_drill as dd

TAU_S = 0.2
DA_MIN = 0.90  # positive control: every sector at or above
HOLD_DA_MAX = 0.10  # hold reference (first screen's drill): every sector below
PHYSICS_DT, DECIMATION = 0.005, 4  # the agility tasks' (checked against the task cfgs in tests/test_agility2.py)
START_XY = (-4.4, 0.0)  # middle of move_drill.SPOT_BOX


class _Data:
    def __init__(self, n, xy):
        self.root_link_pose_w = torch.zeros(n, 7)
        self.root_link_pose_w[:, 3] = 1.0  # identity quaternion: facing the net, so body frame = world frame
        self.root_link_pose_w[:, 0], self.root_link_pose_w[:, 1] = xy
        self.root_link_lin_vel_b = torch.zeros(n, 3)
        self.root_link_lin_vel_w = torch.zeros(n, 3)
        self.root_link_ang_vel_b = torch.zeros(n, 3)
        self.body_link_pose_w = torch.zeros(n, 1, 7)


class PointMassTerm:
    """What DeadlineMoveDrill reads from the ball term, for a point mass (no env: no falls, no censoring, no residual)."""

    def __init__(self, n: int, xy=START_XY):
        self.num_envs, self.device = n, "cpu"
        self.cfg = SimpleNamespace(adaptive_curriculum=False)
        self._entity = SimpleNamespace(data=_Data(n, xy))
        self._env = None
        self.paddle_id = 0
        self.recover_xy = torch.zeros(n, 2)
        self._prev_dead = torch.zeros(n, dtype=torch.bool)
        self.tallied = torch.zeros(n, dtype=torch.bool)
        self.rules = SimpleNamespace(fail=lambda *a: None)
        self.ball = SimpleNamespace(pos=torch.zeros(n, 3), vel=torch.zeros(n, 3), spin=torch.zeros(n, 3))
        self.drill_scale = None

    def pelvis_xy(self, env_ids=None):
        return self._entity.data.root_link_pose_w[:, :2].clone()


def run(arrival_mode: str = "first_entry", dist_range=dd.DIST_RANGE, v_req_range=dd.V_REQ_RANGE,
        heading_free_m: float = dd.HEADING_FREE_M, tau_s: float = TAU_S, physics_dt: float = PHYSICS_DT,
        decimation: int = DECIMATION, n: int = 1024, seconds: float = 30.0, seed: int = 0) -> dict:
    """Run the point mass through the drill; returns the drill's counters and agility_rule.arm_stats of them."""
    with torch.no_grad():
        t = PointMassTerm(n)
        dr = dd.DeadlineMoveDrill(t, 1.0, seed, None, dist_range=dist_range, v_req_range=v_req_range,
                                  deadline_ends_spot=False, heading_free_m=heading_free_m, arrival_mode=arrival_mode)
        dr.reset(torch.arange(n))
        data = t._entity.data
        v = torch.zeros(n, 2)  # at rest
        cmd = torch.zeros(n, 2)
        alpha = 1.0 - math.exp(-physics_dt / tau_s)  # exact first-order lag over one physics step (command held)
        for k in range(int(round(seconds / physics_dt))):
            if k % int(decimation) == 0:  # the command is a control-step quantity
                cmd, _ = dr.command()  # body frame; yaw stays 0, so this is also the world frame
            v = v + alpha * (cmd - v)
            data.root_link_pose_w[:, :2] += v * physics_dt
            data.root_link_lin_vel_w[:, :2] = v
            data.root_link_lin_vel_b[:, :2] = v
            dr.update(physics_dt)
        c = dr.counters()
    return {"counters": c, "stats": ar.arm_stats(c)}


def _brief(res: dict, mode: str, kw: dict, ok: bool, check: str) -> dict:
    s = res["stats"]["sectors"]
    return {"arrival_mode": mode, "tau_s": kw.get("tau_s", TAU_S), "physics_dt": kw.get("physics_dt", PHYSICS_DT),
            "decimation": kw.get("decimation", DECIMATION), "check": check, "pass": ok,
            "sectors": [{"name": x["name"], "resolved": x["resolved"], "da": x["da"], "untimed": x["untimed"]} for x in s],
            "da_min": min((x["da"] for x in s if x["da"] is not None), default=None),
            "da_max": max((x["da"] for x in s if x["da"] is not None), default=None)}


def positive_control(**kw) -> dict:
    """The drill (keyword arguments as run(); arrival_mode defaults to first_entry) under the lagged point mass. Passes
    when every sector has resolved spots and DA >= DA_MIN."""
    res = run(**kw)
    s = res["stats"]["sectors"]
    ok = all(x["resolved"] > 0 and x["da"] is not None and x["da"] >= DA_MIN for x in s)
    return _brief(res, kw.get("arrival_mode", "first_entry"), kw, ok, f"DA >= {DA_MIN:.2f} in every sector")


def hold_reference(**kw) -> dict:
    """The same control under the first screen's drill (hold arrival): passes when it fails every deadline (DA <
    HOLD_DA_MAX in every sector), i.e. it reproduces the defect D-172 names."""
    kw = {**kw, "arrival_mode": "hold"}
    res = run(**kw)
    s = res["stats"]["sectors"]
    ok = all(x["resolved"] > 0 and x["da"] is not None and x["da"] < HOLD_DA_MAX for x in s)
    return _brief(res, "hold", kw, ok, f"DA < {HOLD_DA_MAX:.2f} in every sector (reproduces the defect)")


def task_settings(task_id: str) -> dict:
    """A registered agility task's drill settings and control dt (env cfg only; no simulator is built)."""
    import picklebot_mj.tasks.agility  # noqa: F401  (registers the agility tasks)
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg(task_id)
    b = cfg.actions["ball"]
    assert getattr(b, "deadline_drill", False), f"{task_id}: not a deadline-drill task"
    return {"arrival_mode": b.deadline_arrival_mode, "dist_range": tuple(b.deadline_dist),
            "v_req_range": tuple(b.deadline_v_req), "heading_free_m": float(b.heading_free_m),
            "physics_dt": float(cfg.sim.mujoco.timestep), "decimation": int(cfg.decimation)}


def _print(tag: str, r: dict) -> None:
    print(f"{tag}: mode {r['arrival_mode']}, tau {r['tau_s']} s, dt {r['physics_dt']} s x {r['decimation']}; "
          f"check {r['check']} -> {'PASS' if r['pass'] else 'FAIL'}")
    for x in r["sectors"]:
        da = "  n/a" if x["da"] is None else f"{100 * x['da']:5.1f}"
        un = "  n/a" if x["untimed"] is None else f"{100 * x['untimed']:5.1f}"
        print(f"  {x['name']:<14} resolved {x['resolved']:6d}  DA {da} %  untimed {un} %")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", action="append", required=True)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    out, ok = {"tasks": {}}, True
    for task in args.task:
        st = task_settings(task)
        if st["arrival_mode"] != "first_entry":
            print(f"{task}: arrival mode {st['arrival_mode']!r}, not first_entry -> FAIL")
            ok = False
            continue
        pos = positive_control(**st)
        neg = hold_reference(**{k: v for k, v in st.items() if k != "arrival_mode"})
        _print(f"{task} positive control", pos)
        _print(f"{task} hold reference", neg)
        out["tasks"][task] = {"settings": st, "positive": pos, "hold_reference": neg}
        ok = ok and pos["pass"] and neg["pass"]
    out["pass"] = ok
    print("positive control: " + ("PASS" if ok else "FAIL"))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(out, f, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
