"""Agility screen (footwork-route-2026-10-29.md section 6): deadline move drill, direction tally, coded rule, task cfgs.
CPU only: the drill and the tally run against a small fake term (no simulator)."""

import math
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest
import torch

from picklebot_mj import agility_rule as ar


# ------------------------------------------------------------------------------------------
# A fake ball term: just what MoveDrill / DeadlineMoveDrill / DirectionTally read.
class _Data:
    def __init__(self, n):
        self.root_link_pose_w = torch.zeros(n, 7)
        self.root_link_pose_w[:, 3] = 1.0  # identity quaternion: facing the net (+x)
        self.root_link_lin_vel_b = torch.zeros(n, 3)
        self.root_link_lin_vel_w = torch.zeros(n, 3)
        self.root_link_ang_vel_b = torch.zeros(n, 3)
        self.body_link_pose_w = torch.zeros(n, 1, 7)


class _Terms:
    def __init__(self, terms):
        self.terms = terms

    def get_term(self, name):
        return self.terms[name]


class FakeTerm:
    def __init__(self, n=8, xy=(-4.4, 0.0), latent=None):
        self.num_envs, self.device = n, "cpu"
        self.cfg = SimpleNamespace(adaptive_curriculum=False)
        self._entity = SimpleNamespace(data=_Data(n))
        self._entity.data.root_link_pose_w[:, 0], self._entity.data.root_link_pose_w[:, 1] = xy
        self.paddle_id = 0
        self.recover_xy = torch.zeros(n, 2)
        self._prev_dead = torch.zeros(n, dtype=torch.bool)
        self.tallied = torch.zeros(n, dtype=torch.bool)
        self.rules = SimpleNamespace(fail=lambda *a: None)
        self.ball = SimpleNamespace(pos=torch.zeros(n, 3), vel=torch.zeros(n, 3), spin=torch.zeros(n, 3))
        self.drill_scale = None
        self.hit_done = torch.zeros(n, dtype=torch.bool)
        self.fell = torch.zeros(n, dtype=torch.bool)
        terms = {"latent": latent} if latent is not None else {}
        self._env = SimpleNamespace(common_step_counter=0, num_envs=n, device="cpu",
                                    termination_manager=_Terms({"fell_over": self.fell}),
                                    action_manager=_Terms(terms), physics_dt=0.005,
                                    cfg=SimpleNamespace(decimation=4),
                                    scene=SimpleNamespace(env_origins=torch.zeros(n, 3)))

    def pelvis_xy(self, env_ids=None):
        return self._entity.data.root_link_pose_w[:, :2].clone()

    def place(self, xy):
        self._entity.data.root_link_pose_w[:, :2] = torch.as_tensor(xy, dtype=torch.float32)


def _drill(n=256, **kw):
    from picklebot_mj.tasks.deadline_drill import DeadlineMoveDrill
    t = FakeTerm(n, **kw)
    dr = DeadlineMoveDrill(t, 1.0, seed=3)
    dr.reset(torch.arange(n))
    return t, dr


# ------------------------------------------------------------------------------------------
def test_spots_speeds_and_deadlines():
    from picklebot_mj.tasks import move_drill as md
    t, dr = _drill(4096)
    assert dr.move_ep.all()
    d0 = (t.recover_xy - dr.start_xy).norm(dim=-1)
    assert (d0 <= 3.0 + 1e-4).all() and (d0 >= 1.0 - 1e-4).float().mean() > 0.95  # only box-wall clamps go below 1 m
    assert ((dr.v_req >= 1.2) & (dr.v_req <= 2.0)).all()
    assert torch.allclose(dr.deadline, 0.3 + d0 / dr.v_req, atol=1e-5)
    assert torch.allclose(dr.limit, torch.maximum(md.TIME_BASE_S + md.TIME_PER_M * d0, dr.deadline), atol=1e-5)
    # the sector label is the direction of the spot from the start (0 toward the net, counter-clockwise)
    rel = t.recover_xy - dr.start_xy
    ang = torch.atan2(rel[:, 1], rel[:, 0])
    k = torch.round(ang / (2 * math.pi / 8)).long() % 8
    assert (k == dr.sector).float().mean() > 0.99
    iss = dr.stats["issued"]
    assert (iss > 0).all() and float(iss.max()) / float(iss.float().mean()) < 1.6  # uniform up to box reversals


def test_command_cap_heading_and_free_yaw():
    t, dr = _drill(512)
    v_b, wz = dr.command()
    d = (t.recover_xy - t.pelvis_xy()).norm(dim=-1)
    assert (v_b.norm(dim=-1) <= dr.v_req + 1e-5).all()
    far = d > 1.0
    assert torch.equal(wz[far], torch.zeros(int(far.sum())))  # heading free beyond 1 m
    # beyond the slow-down distance (0.83 m) the command runs at v_req
    cruise = d > 0.9
    assert torch.allclose(v_b[cruise].norm(dim=-1), dr.v_req[cruise], atol=1e-4)
    # inside 1 m, a yawed robot is turned back toward the net
    t.recover_xy = t.pelvis_xy() + torch.tensor([0.5, 0.0])
    yaw = 0.6
    t._entity.data.root_link_pose_w[:, 3:7] = torch.tensor([math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)])
    _, wz = dr.command()
    assert (wz < 0).all()
    assert not dr.yaw_free().any()


def test_arrival_before_and_after_the_deadline():
    from picklebot_mj.tasks import move_drill as md
    t, dr = _drill(4)
    dt = 0.005
    t.recover_xy = t.pelvis_xy().clone()  # every spot under a still robot
    dr.deadline[:] = torch.tensor([10.0, 10.0, 0.1, 0.1])  # two in time, two late
    dr.limit[:] = 20.0
    a0 = int(dr.stats["arrived"].sum())
    for _ in range(int(md.ARRIVE_HOLD_S / dt) + 2):
        dr.update(dt)
        if dr.arrive_now.any():
            break
    assert int(dr.stats["arrived"].sum()) - a0 == 4
    assert int(dr.stats["deadline"].sum()) == 2
    assert dr.arrive_now.tolist() == [True, True, False, False]  # bonus only before the deadline
    # an untimed time-out
    s = dr.stats["timed_out"].sum().item()
    t.recover_xy = t.pelvis_xy() + torch.tensor([2.0, 0.0])
    dr.limit[:] = 0.01
    dr.elapsed[:] = 0.0
    dr.update(dt)
    dr.update(dt)
    dr.update(dt)
    assert dr.stats["timed_out"].sum().item() - s == 4


def test_peak_speed_falls_and_censoring():
    t, dr = _drill(4)
    t._entity.data.root_link_lin_vel_w[:, 0] = 1.75
    t._entity.data.root_link_lin_vel_b[:, 0] = 1.75
    dr.limit[:] = 0.0  # time out on the next step: the peak is booked
    dr.update(0.005)
    sec = dr.stats["timed_out"].nonzero().flatten()
    assert torch.allclose(dr.peak_sum[sec].sum(), torch.tensor(1.75 * 4))
    assert int(dr.peak_hist[:, 17].sum()) == 4  # 1.7-1.8 m/s bin
    # an episode end: falls on envs 0-1, censored on 2-3
    t._env.common_step_counter = 10
    t.fell[:] = torch.tensor([True, True, False, False])
    dr.reset(torch.arange(4))
    assert int(dr.stats["fell"].sum()) == 2 and int(dr.stats["censored"].sum()) == 2


def test_residual_saturation_share():
    lat = SimpleNamespace(a_ref=torch.zeros(4, 35), cfg=SimpleNamespace(lam_r=2.0, latent=32), raw_action=torch.zeros(4, 35))
    lat.raw_action[0, :4] = 5.0  # 4 dims saturated
    lat.raw_action[1, :3] = 5.0  # 3: not
    from picklebot_mj.tasks.deadline_drill import residual_saturated
    t = FakeTerm(4, latent=lat)
    assert residual_saturated(t._env).tolist() == [True, False, False, False]
    assert residual_saturated(FakeTerm(4)._env) is None  # flat policy
    from picklebot_mj.tasks.deadline_drill import DeadlineMoveDrill
    dr = DeadlineMoveDrill(t, 1.0, seed=1)
    dr.reset(torch.arange(4))
    dr.update(0.005)
    assert int(dr.stats["move_steps"].sum()) == 4 and int(dr.stats["sat_steps"].sum()) == 1


def test_counters_round_trip_to_rates():
    t, dr = _drill(64)
    for _ in range(5):
        dr.update(0.005)
    c = dr.counters()
    st = ar.arm_stats(c)
    assert len(st["sectors"]) == 8 and set(c) >= {"issued", "arrived", "deadline", "fell", "peak_hist", "sat_steps"}


def test_agility_track_yaw_free_heading():
    from picklebot_mj.tasks.deadline_drill import agility_track_yaw
    t, dr = _drill(4)
    term = SimpleNamespace(drill=dr, shadow=None)
    env = SimpleNamespace(action_manager=_Terms({"ball": term}), num_envs=4, device="cpu")
    dr.t.shadow, dr.t.cfg.swing_follow_hint = None, False
    t._entity.data.root_link_ang_vel_b[:, 2] = 2.0  # spinning
    t.recover_xy = t.pelvis_xy() + torch.tensor([[2.0, 0], [2.0, 0], [0.5, 0], [0.5, 0]])
    r = agility_track_yaw(env)
    assert torch.allclose(r[:2], torch.ones(2))  # far: yaw rate untracked
    assert (r[2:] < 0.01).all()  # near: tracked toward the net (command 0, spinning at 2 rad/s)


# ------------------------------------------------------------------------------------------
class _Pairs:
    def __init__(self, n):
        self.handed = torch.zeros(n, dtype=torch.bool)
        self.court_dead = torch.zeros(n // 2, dtype=torch.bool)
        self.waiting = torch.zeros(n, dtype=torch.bool)
        self.partner = (torch.arange(n) + n // 2) % n
        self.calls = 0

    def step(self, over, legal, fell, crossing, dt, delay, contact=None, busy=None):
        self.calls += 1
        return torch.zeros_like(over), torch.zeros_like(over)


def test_direction_tally_classifies_and_counts_feeder_balls():
    from picklebot_mj.tasks.deadline_drill import DirectionTally
    n = 8
    t = FakeTerm(n, xy=(0.0, 0.0))
    t.pairs = _Pairs(n)
    tally = DirectionTally(t, t._env)
    assert t.pairs.step == tally.step
    # closest approach: forward, left, back, right, x2; envs 4-7 are partner balls
    t.ball.pos[:, :2] = torch.tensor([[1, 0], [0, 1], [-1, 0], [0, -1]] * 2, dtype=torch.float32)
    t.pairs.handed[4:] = True
    # the pelvis runs left at 1 m/s from the 3rd control step on
    o = torch.zeros(n, dtype=torch.bool)
    for i in range(4 * 6):
        if i == 8:
            t._entity.data.root_link_lin_vel_w[:, 1] = 1.0
        t.pairs.step(o, o, o, o, 0.005, 0.5)
    assert (tally.direction() == torch.tensor([0, 1, 2, 3] * 2)).all()
    t.hit_done[:] = torch.tensor([True, True, False, False] * 2)
    legal = torch.tensor([True, False, False, False] * 2)
    t.pairs.step(torch.ones(n, dtype=torch.bool), legal, o, o, 0.005, 0.5)
    c = tally.counters()
    assert c["feeds"] == [1, 1, 1, 1] and c["contact"] == [1, 1, 0, 0] and c["legal"] == [1, 0, 0, 0]
    assert c["handed"]["feeds"] == [1, 1, 1, 1]
    h = torch.tensor(c["onset_hist"])
    assert int(h[1, 2]) == 1  # left: velocity toward the ball from control step 2
    assert int(h[0, -1]) == 1 and int(h[2, -1]) == 1  # forward / back: never
    assert c["approach_steps"][2] > 0 and c["sat_steps"] == [0, 0, 0, 0]


# ------------------------------------------------------------------------------------------
def _counts(da, untimed=None, n=1000, sat=0.0):
    untimed = untimed or [max(x, 0.95) for x in da]
    c = {k: [0] * 8 for k in ("issued", "arrived", "deadline", "timed_out", "fell", "censored", "time_sum", "peak_sum",
                              "sat_steps", "move_steps", "ready")}
    c["peak_hist"] = [[0] * 50 for _ in range(8)]
    for i in range(8):
        c["issued"][i] = n
        c["arrived"][i] = round(untimed[i] * n)
        c["deadline"][i] = round(da[i] * n)
        c["timed_out"][i] = n - c["arrived"][i]
        c["move_steps"][i] = 100
        c["sat_steps"][i] = round(sat * 100)
    return c


def _arm(lb, fr, sat=0.0):
    da = [fr, 0.5 * (lb + fr), lb, lb, lb, 0.5 * (lb + fr), fr, fr]
    return ar.arm_stats(_counts(da, sat=sat))


def test_rule_routes():
    assert ar.route(_arm(0.62, 0.70), None, None)["route"] == "reading"  # D0 8 < 10
    a0 = _arm(0.40, 0.70)  # D0 30
    assert ar.route(a0, _arm(0.56, 0.66), None)["route"] == "E"  # +16, gap 10 <= 15
    assert ar.route(a0, _arm(0.54, 0.66), _arm(0.80, 0.85))["route"] == "C"  # A +14 fails; F within 10
    assert ar.route(a0, _arm(0.60, 0.80), _arm(0.80, 0.85))["route"] == "C"  # A gap 20 > 15 fails
    assert ar.route(a0, _arm(0.50, 0.70), _arm(0.60, 0.85))["route"] == "lower-band"  # F 25 below
    r = ar.route(a0, _arm(0.50, 0.70, sat=0.3), _arm(0.80, 0.85))
    assert r["route"] == "pending-B" and r["b_triggered"]
    assert ar.route(a0, _arm(0.50, 0.70, sat=0.3), _arm(0.80, 0.85), _arm(0.60, 0.70))["route"] == "b"
    assert ar.route(a0, _arm(0.50, 0.70, sat=0.3), _arm(0.80, 0.85), _arm(0.50, 0.70))["route"] == "C"
    assert ar.route(a0, None, None)["route"] == "pending"
    for line in ar.route(a0, _arm(0.56, 0.66), None)["lines"][:3]:
        assert ("PASS" in line or "FAIL" in line) and (">=" in line or "<=" in line)


def test_rule_boundaries_are_inclusive():
    a0 = _arm(0.40, 0.50)  # D0 exactly 10
    assert ar.route(a0, _arm(0.55, 0.60), None)["route"] == "E"  # +15 exactly, gap 5 = 0.5 x 10


def test_windows_and_ball_side():
    rows = []
    for s, k in ((0, 0), (240, 100), (480, 300), (720, 600)):
        rows.append({"step": s, "move": {"x": [k, 2 * k]}, "dir": {"feeds": [k], "onset_bin_s": 0.02,
                                                                 "handed": {"feeds": [k]}}})
    assert ar.window(rows, "move", 0.5)["x"] == [500, 1000]  # 600 - 100 (row nearest step 360 is 240)
    w = ar.window(rows, "dir", 0.5)
    assert w["onset_bin_s"] == 0.02 and w["handed"]["feeds"] == [500]
    c = {"feeds": [100, 100, 100, 100], "contact": [95, 60, 60, 90], "legal": [90, 45, 50, 85],
         "approach_steps": [10] * 4, "sat_steps": [1] * 4, "peak_sum": [100.0] * 4, "onset_bin_s": 0.02,
         "onset_hist": [[0, 10, 80, 10], [0, 0, 50, 50], [0, 0, 50, 50], [10, 80, 10, 0]]}
    b = ar.ball_side(c)
    assert abs(b["lb_legal"] - 0.475) < 1e-9 and abs(b["fr_legal"] - 0.875) < 1e-9 and b["premise"]
    assert b["directions"]["left"]["onset_never_share"] == 0.5


# ------------------------------------------------------------------------------------------
def test_agility_tasks_change_only_the_drill():
    import dataclasses

    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

    import picklebot_mj.tasks.agility as ag
    src, a = load_env_cfg(ag.SRC_RES), load_env_cfg(ag.TASK_AGILITY_RES)
    for g in ("actor", "critic"):
        assert list(src.observations[g].terms) == list(a.observations[g].terms)
    assert list(src.rewards) == list(a.rewards)
    assert [k for k in src.rewards if src.rewards[k].func is not a.rewards[k].func
            or src.rewards[k].weight != a.rewards[k].weight] == ["move_track_yaw"]
    sb, ab = src.actions["ball"], a.actions["ball"]
    assert [f.name for f in dataclasses.fields(sb) if getattr(sb, f.name) != getattr(ab, f.name)] == ["move_prob",
                                                                                                        "swing_prob"]
    assert ab.deadline_drill and ab.move_prob == 1.0 and ab.swing_prob == 0.0 and a.actions["latent"].lam_r == 2.0
    assert load_env_cfg(ag.TASK_AGILITY_RES_L3).actions["latent"].lam_r == 3.0
    assert load_runner_cls(ag.TASK_AGILITY_RES) is load_runner_cls(ag.SRC_RES)
    assert load_rl_cfg(ag.TASK_AGILITY_RES).experiment_name == "picklebot_return_stand"
    tb = load_env_cfg(ag.TASK_AGILITY_BALL).actions["ball"]
    assert tb.direction_tally and not tb.deadline_drill
    assert [f.name for f in dataclasses.fields(sb) if getattr(sb, f.name) != getattr(tb, f.name)] == []
    tt, ts = load_env_cfg(ag.TASK_AGILITY_TEACHER), load_env_cfg(ag.SRC_TEACHER)
    assert list(tt.observations["actor"].terms) == list(ts.observations["actor"].terms)
    assert tt.actions["ball"].deadline_drill and "latent" not in tt.actions


def test_entry_point_does_not_import_the_agility_module():
    """Other runs (rally run 22's reads) import picklebot_mj.tasks through mjlab's entry point: agility stays out."""
    code = "import sys, mjlab.tasks; print('picklebot_mj.tasks.agility' in sys.modules, 'picklebot_mj.tasks' in sys.modules)"
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONWARNINGS="ignore")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=600)
    assert out.stdout.strip().splitlines()[-1] == "False True", out.stderr[-2000:]
