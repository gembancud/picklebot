"""Second agility screen (D-172): first-entry deadline arrival, the coded CPU positive control, the rule's validity gates
and the Deadline2 task cfgs. CPU only: the drill runs against small fakes (no simulator)."""

import dataclasses
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest
import torch

from picklebot_mj import agility_control as ac
from picklebot_mj import agility_rule as ar

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ------------------------------------------------------------------------------------------
class _Data:
    def __init__(self, n):
        self.root_link_pose_w = torch.zeros(n, 7)
        self.root_link_pose_w[:, 3] = 1.0
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
    def __init__(self, n=4, xy=(-4.4, 0.0)):
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
        self.fell = torch.zeros(n, dtype=torch.bool)
        self._env = SimpleNamespace(common_step_counter=0, num_envs=n, device="cpu",
                                    termination_manager=_Terms({"fell_over": self.fell}), action_manager=_Terms({}))

    def pelvis_xy(self, env_ids=None):
        return self._entity.data.root_link_pose_w[:, :2].clone()


def _drill(mode, n=4):
    from picklebot_mj.tasks.deadline_drill import DeadlineMoveDrill
    t = FakeTerm(n)
    dr = DeadlineMoveDrill(t, 1.0, seed=3, arrival_mode=mode)
    dr.reset(torch.arange(n))
    return t, dr


def _moving(t, speed=1.5):
    t._entity.data.root_link_lin_vel_b[:, 0] = speed
    t._entity.data.root_link_lin_vel_w[:, 0] = speed


DT = 0.005


# ------------------------------------------------------------------------------------------
def test_default_mode_is_hold_and_unknown_mode_rejected():
    from picklebot_mj.tasks.deadline_drill import DeadlineMoveDrill
    _, dr = _drill("hold")
    assert DeadlineMoveDrill(FakeTerm(2), 1.0, seed=1).arrival_mode == "hold"
    with pytest.raises(AssertionError):
        DeadlineMoveDrill(FakeTerm(2), 1.0, seed=1, arrival_mode="nope")


def test_first_entry_without_stopping_counts_in_time_only():
    t, dr = _drill("first_entry")
    t.recover_xy = t.pelvis_xy() + torch.tensor([0.1, 0.0])  # inside 0.25 m
    _moving(t)  # passing through at 1.5 m/s: never a held arrival
    dr.deadline[:] = torch.tensor([10.0, 10.0, 0.001, 0.001])  # two in time, two already late at the first step
    dr.limit[:] = 20.0
    dr.update(DT)
    assert dr.arrive_now.tolist() == [True, True, False, False]  # bonus at the in-time entry
    assert dr.entered.tolist() == [True, True, False, False]
    assert int(dr.stats["deadline"].sum()) == 0 and int(dr.stats["arrived"].sum()) == 0  # booked at resolution
    dr.arrive_now[:] = False  # move_arrival reads and clears
    dr.update(DT)
    assert not dr.arrive_now.any()  # paid once per spot
    dr.limit[:] = 0.0  # untimed time-out: the spots resolve
    dr.update(DT)
    assert int(dr.stats["timed_out"].sum()) == 4 and int(dr.stats["arrived"].sum()) == 0
    assert int(dr.stats["deadline"].sum()) == 2  # entry without stopping counted; untimed arrival not
    assert not dr.entered.any()  # new spots


def test_first_entry_late_entry_not_counted_and_held_arrival_kept():
    t, dr = _drill("first_entry")
    t.recover_xy = t.pelvis_xy() + torch.tensor([1.0, 0.0])
    dr.deadline[:] = 0.02
    dr.limit[:] = 20.0
    for _ in range(10):  # outside until after the deadline (elapsed 0.05 s)
        dr.update(DT)
    t.recover_xy = t.pelvis_xy() + torch.tensor([0.1, 0.0])  # now inside, stopped
    a0 = int(dr.stats["arrived"].sum())
    for _ in range(80):
        dr.update(DT)
        assert not dr.arrive_now.any()  # no bonus for a late entry, nor for the held arrival
        if int(dr.stats["arrived"].sum()) > a0:
            break
    assert int(dr.stats["arrived"].sum()) - a0 == 4  # untimed arrival is MoveDrill's held arrival
    assert int(dr.stats["deadline"].sum()) == 0


def test_first_entry_then_held_arrival_books_one_deadline_arrival():
    t, dr = _drill("first_entry")
    t.recover_xy = t.pelvis_xy() + torch.tensor([0.1, 0.0])
    dr.deadline[:] = 10.0
    dr.limit[:] = 20.0
    for _ in range(80):
        dr.update(DT)
        if int(dr.stats["arrived"].sum()):
            break
    assert int(dr.stats["arrived"].sum()) == 4 and int(dr.stats["deadline"].sum()) == 4


def test_first_entry_falls_book_the_entry_censored_does_not():
    t, dr = _drill("first_entry")
    t.recover_xy = t.pelvis_xy() + torch.tensor([0.1, 0.0])
    _moving(t)
    dr.deadline[:] = 10.0
    dr.limit[:] = 20.0
    dr.update(DT)
    assert dr.entered.all()
    t._env.common_step_counter = 10
    t.fell[:] = torch.tensor([True, True, False, False])
    dr.reset(torch.arange(4))
    assert int(dr.stats["fell"].sum()) == 2 and int(dr.stats["censored"].sum()) == 2
    assert int(dr.stats["deadline"].sum()) == 2  # falls resolve (and count); censored spots stay out
    assert not dr.entered.any()


def test_hold_mode_unchanged_entry_without_stopping_not_counted():
    t, dr = _drill("hold")
    t.recover_xy = t.pelvis_xy() + torch.tensor([0.1, 0.0])
    _moving(t)
    dr.deadline[:] = 10.0
    dr.limit[:] = 20.0
    for _ in range(80):
        dr.update(DT)
        assert not dr.arrive_now.any()
    t._entity.data.root_link_lin_vel_b[:] = 0.0
    for _ in range(80):
        dr.update(DT)
        if dr.arrive_now.any():
            break
    assert dr.arrive_now.all() and int(dr.stats["deadline"].sum()) == 4  # held arrival before the deadline


# ------------------------------------------------------------------------------------------
def test_positive_control_passes_in_first_entry_mode():
    r = ac.positive_control(arrival_mode="first_entry")
    assert r["pass"], r
    assert all(x["resolved"] >= 500 and x["da"] >= ac.DA_MIN for x in r["sectors"])


def test_same_control_fails_in_hold_mode():
    r = ac.positive_control(arrival_mode="hold")
    assert not r["pass"]
    assert all(x["da"] < ac.HOLD_DA_MAX for x in r["sectors"]), r  # the defect D-172 names
    assert ac.hold_reference()["pass"]


def test_positive_control_drives_the_drills_own_command(monkeypatch):
    from picklebot_mj.tasks import deadline_drill as dd
    calls = []
    orig = dd.DeadlineMoveDrill.command

    def spy(self):
        calls.append(1)
        v, w = orig(self)
        return 0.5 * v, w  # a slower command: the control must follow it and miss deadlines

    monkeypatch.setattr(dd.DeadlineMoveDrill, "command", spy)
    r = ac.positive_control(arrival_mode="first_entry", n=128, seconds=6.0)
    assert calls and len(calls) == int(round(6.0 / ac.PHYSICS_DT)) // ac.DECIMATION
    assert not r["pass"]


def test_positive_control_cli_on_the_deadline2_tasks(tmp_path):
    import picklebot_mj.tasks.agility as ag
    for task in (ag.TASK_AGILITY2_RES, ag.TASK_AGILITY2_RES_L3, ag.TASK_AGILITY2_TEACHER):
        st = ac.task_settings(task)
        assert st["arrival_mode"] == "first_entry"
        assert (st["physics_dt"], st["decimation"]) == (ac.PHYSICS_DT, ac.DECIMATION)  # the env's control dt
    out = tmp_path / "control.json"
    assert ac.main(["--task", ag.TASK_AGILITY2_RES, "--json", str(out)]) == 0
    assert json.loads(out.read_text())["pass"]
    assert ac.main(["--task", ag.TASK_AGILITY_RES]) == 1  # the first screen's (hold) task is refused


# ------------------------------------------------------------------------------------------
def _counts(da, untimed=None, n=1000, sat=0.0, censored=0):
    untimed = untimed or [max(x, 0.95) for x in da]
    c = {k: [0] * 8 for k in ("issued", "arrived", "deadline", "timed_out", "fell", "censored", "time_sum", "peak_sum",
                              "sat_steps", "move_steps", "ready")}
    c["peak_hist"] = [[0] * 50 for _ in range(8)]
    for i in range(8):
        c["issued"][i] = n + censored
        c["censored"][i] = censored
        c["arrived"][i] = round(untimed[i] * n)
        c["deadline"][i] = round(da[i] * n)
        c["timed_out"][i] = n - c["arrived"][i]
        c["move_steps"][i] = 100
        c["sat_steps"][i] = round(sat * 100)
    return c


def _da(lb, fr):
    return [fr, 0.5 * (lb + fr), lb, lb, lb, 0.5 * (lb + fr), fr, fr]


def _arm(lb, fr, sat=0.0, untimed=None, censored=0):
    return ar.arm_stats(_counts(_da(lb, fr), untimed=untimed, sat=sat, censored=censored))


def test_gate_a0_void_branches():
    for a0 in (_arm(0.02, 0.05),  # DA(FR) 5 < 10
               _arm(0.60, 0.95),  # DA(FR) 95 > 90
               _arm(0.40, 0.70, untimed=[0.95, 0.95, 0.85, 0.95, 0.95, 0.95, 0.95, 0.95])):  # left 85 % untimed
        r = ar.route_gated(a0, _arm(0.56, 0.66), _arm(0.80, 0.85))
        assert r["route"] == "void" and not r["b_triggered"] and r["a0_valid"] is False
        assert r["lines"][-1] == "VOID: A0 outside validity gates"
        assert not any(l.startswith("ROUTE") for l in r["lines"])  # no route given


def test_gate_a0_boundaries_inclusive():
    for fr in (0.10, 0.90):
        assert ar.a0_gate(_arm(fr - 0.05, fr, untimed=[0.90] * 8))[0]


def test_gate_f_void_only_for_routes_that_need_f():
    a0 = _arm(0.40, 0.70)  # valid, D0 30
    f_bad = _arm(0.80, 0.85, censored=150)  # 150 / 1150 = 13 % censored
    f_edge = _arm(0.80, 0.85, censored=111)  # 111 / 1111 = 9.99 %
    assert not ar.f_gate(f_bad)[0] and ar.f_gate(f_edge)[0]
    r = ar.route_gated(a0, _arm(0.54, 0.66), f_bad)  # A fails: route C needs F
    assert r["route"] == "void-F" and any(l.startswith("VOID (F invalid)") for l in r["lines"])
    r = ar.route_gated(a0, _arm(0.50, 0.70), _arm(0.60, 0.85, censored=150))  # lower-band needs F
    assert r["route"] == "void-F"
    r = ar.route_gated(a0, _arm(0.50, 0.70, sat=0.3), f_bad)  # pending-B needs F
    assert r["route"] == "void-F" and not r["b_triggered"]
    assert ar.route_gated(a0, _arm(0.56, 0.66), f_bad)["route"] == "E"  # A passes: F not needed
    assert ar.route_gated(_arm(0.62, 0.70), None, f_bad)["route"] == "reading"  # rule 1: F not needed


def test_gates_valid_route_as_before():
    a0 = _arm(0.40, 0.70)
    cases = [(_arm(0.62, 0.70), None, None, None), (a0, _arm(0.56, 0.66), None, None),
             (a0, _arm(0.54, 0.66), _arm(0.80, 0.85), None), (a0, _arm(0.50, 0.70), _arm(0.60, 0.85), None),
             (a0, _arm(0.50, 0.70, sat=0.3), _arm(0.80, 0.85), None),
             (a0, _arm(0.50, 0.70, sat=0.3), _arm(0.80, 0.85), _arm(0.60, 0.70)), (a0, None, None, None)]
    for c in cases:
        old, new = ar.route(*c), ar.route_gated(*c)
        assert new["route"] == old["route"] and new["b_triggered"] == old["b_triggered"]
        assert new["lines"][-len(old["lines"]):] == old["lines"] and new["a0_valid"]
    assert ar.route(a0, None, None)["lines"] == ar.route(a0, None, None)["lines"]  # route() itself untouched
    assert "a0_valid" not in ar.route(a0, None, None)


def test_summary_gates_flag(tmp_path):
    def scale(v, k):
        return [scale(x, k) for x in v] if isinstance(v, list) else v * k

    rows = lambda c: "".join(json.dumps({"step": 240 * k, "move": {n: scale(v, k) for n, v in c.items()}}) + "\n"
                             for k in range(3))  # cumulative rows: the second half holds one copy of c
    pre = tmp_path / "agility2"
    (tmp_path / "agility2-A0.jsonl").write_text(rows(_counts(_da(0.01, 0.03))))  # DA(FR) 3: void A0
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "diag", "agility_summary.py"), "--prefix", str(pre),
           "--json", str(tmp_path / "s.json")]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONWARNINGS="ignore")
    gated = subprocess.run(cmd + ["--gates"], capture_output=True, text=True, env=env, timeout=600)
    assert "VOID: A0 outside validity gates" in gated.stdout and "route: void" in gated.stdout, gated.stderr[-2000:]
    assert json.loads((tmp_path / "s.json").read_text())["route"]["route"] == "void"
    plain = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    assert "VOID" not in plain.stdout and "route: none" not in plain.stdout and "rule 1" in plain.stdout


# ------------------------------------------------------------------------------------------
def _ball_diff(a, b):
    return [f.name for f in dataclasses.fields(a) if getattr(a, f.name) != getattr(b, f.name)]


def test_deadline2_tasks_differ_only_in_the_arrival_mode():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

    import picklebot_mj.tasks.agility as ag
    for old_id, new_id in ((ag.TASK_AGILITY_RES, ag.TASK_AGILITY2_RES), (ag.TASK_AGILITY_RES_L3, ag.TASK_AGILITY2_RES_L3),
                           (ag.TASK_AGILITY_TEACHER, ag.TASK_AGILITY2_TEACHER)):
        for play in (False, True):
            o, n = load_env_cfg(old_id, play=play), load_env_cfg(new_id, play=play)
            assert o.actions["ball"].deadline_arrival_mode == "hold"
            assert n.actions["ball"].deadline_arrival_mode == "first_entry"
            assert _ball_diff(o.actions["ball"], n.actions["ball"]) == ["deadline_arrival_mode"]
            assert list(o.actions) == list(n.actions)
            for k in o.actions:
                if k != "ball":
                    assert o.actions[k] == n.actions[k], k
            for g in o.observations:
                assert list(o.observations[g].terms) == list(n.observations[g].terms)
            assert list(o.rewards) == list(n.rewards)
            for k in o.rewards:
                assert o.rewards[k].func is n.rewards[k].func and o.rewards[k].weight == n.rewards[k].weight
                assert o.rewards[k].params == n.rewards[k].params
            assert list(o.terminations) == list(n.terminations)
            assert (o.decimation, o.sim.mujoco.timestep, o.episode_length_s) == \
                (n.decimation, n.sim.mujoco.timestep, n.episode_length_s)
        assert load_rl_cfg(old_id) == load_rl_cfg(new_id)
        assert load_runner_cls(old_id) is load_runner_cls(new_id)
    assert load_env_cfg(ag.TASK_AGILITY2_RES).actions["latent"].lam_r == 2.0
    assert load_env_cfg(ag.TASK_AGILITY2_RES_L3).actions["latent"].lam_r == 3.0
    assert "latent" not in load_env_cfg(ag.TASK_AGILITY2_TEACHER).actions


def test_stance2_task_differs_only_in_the_stance_progress_cap():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

    import picklebot_mj.tasks.agility as ag
    for play in (False, True):
        o, n = load_env_cfg(ag.TASK_AGILITY_BALL, play=play), load_env_cfg(ag.TASK_AGILITY_BALL_S2, play=play)
        assert o.rewards["stance_progress"].params.get("max_speed", 1.0) == 1.0
        assert n.rewards["stance_progress"].params["max_speed"] == ag.STANCE2_MAX_SPEED == 2.0
        assert _ball_diff(o.actions["ball"], n.actions["ball"]) == []
        assert list(o.rewards) == list(n.rewards)
        for k in o.rewards:
            assert o.rewards[k].func is n.rewards[k].func and o.rewards[k].weight == n.rewards[k].weight
            if k != "stance_progress":
                assert o.rewards[k].params == n.rewards[k].params, k
        for k in o.actions:
            if k != "ball":
                assert o.actions[k] == n.actions[k], k
        assert o.episode_length_s == n.episode_length_s
    assert load_rl_cfg(ag.TASK_AGILITY_BALL) == load_rl_cfg(ag.TASK_AGILITY_BALL_S2)
    assert load_runner_cls(ag.TASK_AGILITY_BALL) is load_runner_cls(ag.TASK_AGILITY_BALL_S2)


def test_stance_progress_cap_clamps_at_max_speed():
    from types import SimpleNamespace as NS

    from picklebot_mj.tasks.return_stand import stance_progress
    n = 3
    t = NS(stance_xy=torch.tensor([[2.0, 0.0]] * n), hit_done=torch.zeros(n, dtype=torch.bool),
           hit_hint_on=torch.zeros(n, dtype=torch.bool), rules=NS(dead=torch.zeros(n, dtype=torch.bool)),
           drill=None, shadow=None, pelvis_xy=lambda: torch.zeros(n, 2),
           _entity=NS(data=NS(root_link_lin_vel_w=torch.tensor([[0.5, 0, 0], [1.5, 0, 0], [3.0, 0, 0]]))))
    env = NS(action_manager=NS(get_term=lambda name: t))
    import picklebot_mj.tasks.return_stand as rs
    orig = rs._term
    rs._term = lambda e: t
    try:
        assert torch.allclose(stance_progress(env), torch.tensor([0.5, 1.0, 1.0]))
        assert torch.allclose(stance_progress(env, max_speed=2.0), torch.tensor([0.5, 1.5, 2.0]))
    finally:
        rs._term = orig


def test_court_stance_task_differs_only_in_court_feed_stance():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    import picklebot_mj.tasks.agility as ag
    for play in (False, True):
        o, n = load_env_cfg(ag.TASK_AGILITY_BALL, play=play), load_env_cfg(ag.TASK_AGILITY_BALL_CFS, play=play)
        assert o.actions["ball"].court_feed_stance is False and n.actions["ball"].court_feed_stance is True
        assert _ball_diff(o.actions["ball"], n.actions["ball"]) == ["court_feed_stance"]
        for k in o.rewards:
            assert o.rewards[k].params == n.rewards[k].params, k


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_court_feed_stance_sets_each_court_feeds_own_target():
    """D-176: without the flag a court feed leaves stance_xy stale (planner mode gives court feeds no spot); with it,
    every new court feed's stance_xy is its own stance spot."""
    sys.path.insert(0, os.path.dirname(__file__))
    from test_drill_v2 import LATENT, _env
    if not LATENT.exists():
        pytest.skip("needs the H1 latent controller")
    from picklebot_mj.tasks.shadow_swing import stance_spot
    task = "Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1"
    moved = {}
    for flag in (False, True):
        env = _env(task, n=256, court_feed_stance=flag)
        t = env.action_manager.get_term("ball")
        assert t.cfg.court_feed_stance is flag
        act =torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
        n_new = n_moved = n_match = 0
        prev_fam, prev_cf, prev_st = t.family.clone(), t.court_feed.clone(), t.stance_xy.clone()
        with torch.inference_mode():
            for step in range(300):
                env.step(act)
                new = ((t.family != prev_fam) | (t.court_feed != prev_cf)) & t.court_feed
                if t.pairs is not None:  # D-177 fix: launcher feeds only (a received hand-off keeps its stance_xy)
                    new = new & ~t.pairs.handed
                if step > 0 and new.any():
                    d = (t.stance_xy[new] - prev_st[new]).norm(dim=-1)
                    n_new += int(new.sum()); n_moved += int((d > 1e-4).sum())
                    if flag:
                        ref = stance_spot(t, t.cfg.hint_v2)[new]
                        # x only: y picks the forehand / backhand side from the pelvis, which has moved one step later
                        n_match += int(((t.stance_xy[new][:, 0] - ref[:, 0]).abs() < 0.15).sum())
                prev_fam, prev_cf, prev_st = t.family.clone(), t.court_feed.clone(), t.stance_xy.clone()
        env.close()
        assert n_new > 50, n_new
        moved[flag] = n_moved / n_new
        if flag:
            assert n_match / n_new > 0.8, n_match / n_new
    assert moved[False] < 0.2 and moved[True] > 0.8, moved


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_court_feed_stance_leaves_hand_offs_alone():
    """D-177 fix: with court_feed_stance, an env that just received a robot-to-robot hand-off keeps its previous
    stance_xy (only launcher feeds are retargeted), although _feed draws court_feed for it. Hand-offs are forced on
    parked envs through a wrapper on PairCourts.step (zero actions rarely make contact)."""
    sys.path.insert(0, os.path.dirname(__file__))
    from test_drill_v2 import LATENT, _env
    if not LATENT.exists():
        pytest.skip("needs the H1 latent controller")
    from picklebot_mj.tasks.shadow_swing import stance_spot
    task = "Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1"
    env = _env(task, n=256, court_feed_stance=True, court_feed_prob=1.0)
    t = env.action_manager.get_term("ball")
    pc = t.pairs
    orig = pc.step
    st = {"armed": False, "force": None, "prev": None}

    def step(*a, **k):
        fire, recv = orig(*a, **k)
        if st["armed"]:
            st["armed"] = False
            ids = torch.arange(t.num_envs, device=t.device)
            force = pc.parked & ~fire & ~recv & ~t.plan_pending & (ids % 3 == 0)
            st["force"], st["prev"] = force.clone(), t.stance_xy.clone()
            pc.parked &= ~force
            recv = recv | force
        return fire, recv

    pc.step = step
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    checked = moved_if_retargeted = 0
    with torch.inference_mode():
        for i in range(120):
            st["armed"] = i % 20 == 10
            env.step(act)
            f = st["force"]
            if f is not None:
                st["force"] = None
                f = f & ~env.reset_buf.bool()  # an env reset in this step has a new episode's stance
                assert bool(t.court_feed[f].all())  # the hand-off envs were drawn as court feeds
                assert torch.allclose(t.stance_xy[f], st["prev"][f], rtol=0, atol=0, equal_nan=True)  # kept their target
                checked += int(f.sum())
                moved_if_retargeted += int(((stance_spot(t, t.cfg.hint_v2)[f] - st["prev"][f]).norm(dim=-1) > 1e-3).sum())
    env.close()
    assert checked > 20, checked
    assert moved_if_retargeted > 0.5 * checked, (moved_if_retargeted, checked)  # the old code would have moved them


def test_entry_point_does_not_import_the_agility_modules():
    code = ("import sys, mjlab.tasks; print(any(m in sys.modules for m in ('picklebot_mj.tasks.agility', "
            "'picklebot_mj.agility_control')), 'picklebot_mj.tasks' in sys.modules)")
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONWARNINGS="ignore")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=600)
    assert out.stdout.strip().splitlines()[-1] == "False True", out.stderr[-2000:]


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_court_feed_stance_unplanned_retargets_with_the_planner_off():
    """D-215: with the planner off (the rally recipe) and no hit hint, stance_xy is never written; court_feed_stance
    alone leaves it at (0, 0). With court_feed_stance_unplanned too, every new launcher feed's stance_xy is its own
    stance spot (hand-offs still keep theirs, D-177)."""
    sys.path.insert(0, os.path.dirname(__file__))
    from test_drill_v2 import LATENT, _env
    if not LATENT.exists():
        pytest.skip("needs the H1 latent controller")
    from picklebot_mj.tasks.shadow_swing import stance_spot
    task = "Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1"
    moved, zero = {}, {}
    for flag in (False, True):
        env = _env(task, n=256, planner_mode="off", hit_hint=False, court_feed_prob=1.0, court_feed_stance=True,
                   court_feed_stance_unplanned=flag)
        t = env.action_manager.get_term("ball")
        assert not t.plan_on and t.cfg.court_feed_stance_unplanned is flag
        act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
        n_new = n_moved = n_match = 0
        prev_fam, prev_cf, prev_st = t.family.clone(), t.court_feed.clone(), t.stance_xy.clone()
        with torch.inference_mode():
            for step in range(300):
                env.step(act)
                new = ((t.family != prev_fam) | (t.court_feed != prev_cf)) & t.court_feed
                if t.pairs is not None:
                    new = new & ~t.pairs.handed
                if step > 0 and new.any():
                    d = (t.stance_xy[new] - prev_st[new]).norm(dim=-1)
                    n_new += int(new.sum()); n_moved += int((d > 1e-4).sum())
                    if flag:
                        ref = stance_spot(t, t.cfg.hint_v2)[new]
                        n_match += int(((t.stance_xy[new][:, 0] - ref[:, 0]).abs() < 0.15).sum())
                prev_fam, prev_cf, prev_st = t.family.clone(), t.court_feed.clone(), t.stance_xy.clone()
        zero[flag] = float((t.stance_xy.norm(dim=-1) < 1e-6).float().mean())
        env.close()
        assert n_new > 50, n_new
        moved[flag] = n_moved / n_new
        if flag:
            assert n_match / n_new > 0.8, n_match / n_new
    assert moved[False] < 0.2 and moved[True] > 0.8, moved
    assert zero[False] > 0.9 and zero[True] < 0.5, zero
