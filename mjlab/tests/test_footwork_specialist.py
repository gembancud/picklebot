"""Footwork specialist (tasks/footwork_specialist.py, D-179). The drill and rewards run on CPU against test_agility's fake
term; the task test checks the registered config differs from the walking teacher's only where the docstring says."""

import dataclasses
import os
import sys
from types import SimpleNamespace

import torch

sys.path.insert(0, os.path.dirname(__file__))
from test_agility import FakeTerm  # noqa: E402

from picklebot_mj import bodyspeed_rule as bsr  # noqa: E402


def _drill(n=256, xy=(-6.4, 0.0), **kw):
    from picklebot_mj.tasks.footwork_specialist import FootworkDrill
    t = FakeTerm(n, xy=xy)
    dr = FootworkDrill(t, 1.0, seed=7, **kw)
    dr.reset(torch.arange(n))
    return t, dr


def test_spots_box_and_first_entry():
    from picklebot_mj.tasks import footwork_specialist as fs
    t, dr = _drill(4096)
    d = (t.recover_xy - dr.start_xy).norm(dim=-1)
    assert (d <= 5.0 + 1e-4).all() and (d >= 1.0 - 1e-4).float().mean() > 0.95
    lo, hi = torch.tensor([fs.SPOT_BOX[0][0], fs.SPOT_BOX[1][0]]), torch.tensor([fs.SPOT_BOX[0][1], fs.SPOT_BOX[1][1]])
    assert ((t.recover_xy >= lo - 1e-5) & (t.recover_xy <= hi + 1e-5)).all()
    assert ((dr.v_req >= 1.2) & (dr.v_req <= 2.2)).all() and dr.arrival_mode == "first_entry"
    assert set(dr.sector.tolist()) == set(range(8)) and dr.live.all()


def test_command_fixed_cap_braking_radius_and_free_heading():
    from picklebot_mj.tasks import move_drill as md
    t, dr = _drill(4)
    assert abs(dr.gain - 3.0) < 1e-9 and abs(dr.cap / dr.gain - md.CMD_MAX_SPEED / md.CMD_GAIN) < 1e-9
    dr.v_req[:] = 1.2  # the deadline speed does not change the command
    t._entity.data.root_link_pose_w[:, 3:7] = torch.tensor([0.0, 0.0, 0.0, 1.0])  # facing away from the net (yaw pi)
    for d, want, free in ((4.0, 2.5, True), (0.5, 1.5, False)):
        t.recover_xy = torch.tensor([[-6.4 + d, 0.0]] * 4)
        v, wz = dr.command()
        assert torch.allclose(v.norm(dim=-1), torch.full((4,), want), atol=1e-5)
        assert (wz.abs() < 1e-6).all() if free else (wz.abs() > 0.1).all()


def test_sustained_speed_is_booked_with_bodyspeed_rule_keys():
    n = 6
    t, dr = _drill(n)
    t.recover_xy = torch.tensor([[-2.4, 0.0]] * n)  # 4 m toward the net
    t._entity.data.root_link_lin_vel_w[:, 0] = torch.tensor([2.0, 2.0, 1.0, 1.0, 0.0, 0.0])
    for _ in range(4 * 60):  # 60 control steps (1.2 s)
        dr.update(0.005)
    assert torch.allclose(dr.best, torch.tensor([2.0, 2.0, 1.0, 1.0, 0.0, 0.0]), atol=1e-4)
    dr.limit[:] = 0.0  # all time out -> booked
    dr.update(0.005)
    c = dr.counters()
    assert sum(c["booked"]) == n and sum(c["timed_out"]) == n
    h = torch.tensor(c["best_hist"]).sum(0)
    assert int(h[19]) + int(h[20]) == 2 and int(h[9]) + int(h[10]) == 2 and int(h[0]) == 2
    s = bsr.sectors(c)  # the rule module reads these counters as they are
    assert sum(x["spots"] for x in s) == n


def test_track_kernel_scales_with_command_speed():
    from picklebot_mj.tasks import footwork_specialist as fs
    from picklebot_mj.tasks import move_drill as md
    t, dr = _drill(2)
    t.shadow = None
    t.recover_xy = torch.tensor([[-2.4, 0.0]] * 2)  # 4 m ahead: command 2.5 m/s forward (robot faces +x)
    t._entity.data.root_link_lin_vel_b = torch.tensor([[1.0, 0.0], [2.5, 0.0]])
    env = SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: SimpleNamespace(drill=dr)),
                          num_envs=2, device="cpu")
    old = md.move_track_lin_vel(env)
    new = fs.fw_track_lin_vel(env)
    assert old[0] < 1e-3 and abs(float(new[0]) - torch.exp(torch.tensor(-1.5 ** 2 / 1.25 ** 2)).item()) < 1e-4
    assert abs(float(new[1]) - 1.0) < 1e-6 and abs(float(old[1]) - 1.0) < 1e-6


def test_posture_regime_follows_the_drill_command():
    from picklebot_mj.tasks import footwork_specialist as fs
    t, dr = _drill(3)
    t.recover_xy = torch.tensor([[-2.4, 0.0], [-6.0, 0.0], [-6.4, 0.0]])  # 4 m (2.5 m/s), 0.4 m (1.2 m/s), at the spot
    t._entity.data.root_link_pose_w[:, 3:7] = torch.tensor([1.0, 0.0, 0.0, 0.0])
    q = torch.full((3, 2), 0.3)
    asset = SimpleNamespace(data=SimpleNamespace(joint_pos=q))
    env = SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: SimpleNamespace(drill=dr)),
                          num_envs=3, device="cpu", scene={"robot": asset})
    f = fs.fw_posture.__new__(fs.fw_posture)
    f.default_joint_pos = torch.zeros(3, 2)
    f.std_standing, f.std_walking, f.std_running = torch.full((2,), 0.1), torch.full((2,), 0.2), torch.full((2,), 0.6)
    cfg = SimpleNamespace(name="robot", joint_ids=slice(None))
    r = f(env, None, None, None, cfg, "twist", walking_threshold=0.05, running_threshold=1.5)
    want = torch.exp(-torch.tensor([0.09 / 0.36, 0.09 / 0.04, 0.09 / 0.01]))
    assert torch.allclose(r, want, atol=1e-5)


def test_tasks_differ_from_the_walking_teacher_only_where_documented():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

    import picklebot_mj.tasks.agility as ag
    import picklebot_mj.tasks.footwork_specialist as fs
    for task, dist in ((fs.TASK_FW, (1.0, 5.0)), (fs.TASK_FW_MEASURE, (3.0, 5.0))):
        src, a = load_env_cfg(ag.SRC_TEACHER), load_env_cfg(task)
        sb, ab = src.actions["ball"], a.actions["ball"]
        assert isinstance(ab, fs.FootworkBallActionCfg)
        common = [f.name for f in dataclasses.fields(sb)]
        diff = sorted(k for k in common if getattr(sb, k) != getattr(ab, k))
        assert set(diff) <= {"adaptive_curriculum", "move_sector_weights", "swing_prob"}, diff  # deadline_task
        assert ab.move_prob == 1.0 and ab.swing_prob == 0.0 and ab.deadline_drill and ab.footwork_drill
        assert ab.deadline_arrival_mode == "first_entry" and ab.deadline_v_req == (1.2, 2.2)
        assert ab.footwork_dist == dist and ab.move_spot_box == fs.SPOT_BOX and ab.move_cmd_max_speed is None
        assert [k for k in src.actions if k != "ball" and src.actions[k] != a.actions[k]] == []
        for g in src.observations:
            assert list(src.observations[g].terms) == list(a.observations[g].terms)
        changed = sorted(k for k in src.rewards if src.rewards[k].func is not a.rewards[k].func
                         or src.rewards[k].weight != a.rewards[k].weight or src.rewards[k].params != a.rewards[k].params)
        assert changed == ["move_track_lin_vel", "move_track_yaw", "pose"], changed
        assert set(a.rewards) == set(src.rewards)
        assert a.rewards["pose"].params == src.rewards["pose"].params
        assert list(src.terminations) == list(a.terminations) and src.decimation == a.decimation
        assert a.episode_length_s == 20.0
        assert load_runner_cls(task) is load_runner_cls(ag.SRC_TEACHER)
        assert load_rl_cfg(task) == load_rl_cfg(ag.SRC_TEACHER)
    from mjlab.tasks.registry import list_tasks
    if fs.TASK_FW_STYLE in list_tasks():
        s, a = load_env_cfg(fs.TASK_FW_STYLE), load_env_cfg(fs.TASK_FW)
        assert sorted(set(s.rewards) - set(a.rewards)) == ["style"] and s.rewards["style"].weight == 0.5
