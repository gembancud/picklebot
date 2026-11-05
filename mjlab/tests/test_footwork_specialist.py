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


# ------------------------------------------------------------------------------------------ D-181: pay "settled"
def _settle_case(pay, deadline, speed=0.0, steps=80):
    """Two envs placed 0.1 m from their spot (inside ARRIVE_RADIUS); returns (drill, bonus pays per env), reading and
    clearing arrive_now once per control step as move_arrival does."""
    t, dr = _drill(2, pay=pay)
    t.recover_xy = torch.tensor([[-6.3, 0.0]] * 2)
    dr.deadline[:] = torch.tensor(deadline)
    dr.limit[:] = 100.0
    dr.elapsed[:], dr.hold[:], dr.entered[:] = 0.0, 0.0, False
    t._entity.data.root_link_lin_vel_b[:, 0] = speed
    t._entity.data.root_link_lin_vel_w[:, 0] = speed
    pays = torch.zeros(2, dtype=torch.long)
    for i in range(steps):
        dr.update(0.005)
        if i % 4 == 3:
            pays += dr.arrive_now.long()
            dr.arrive_now[:] = False
    return dr, pays


def test_settled_pays_once_only_for_an_in_time_entry_then_hold():
    dr, pays = _settle_case("settled", [10.0, 0.0])  # env 0 enters in time, env 1 after its deadline
    c = dr.counters()
    assert pays.tolist() == [1, 0]
    assert sum(c["settled"]) == 1 and sum(c["arrived"]) == 2 and sum(c["deadline"]) == 1
    assert sum(c["short"]) == 2 and sum(c["booked"]) == 0  # resolved after 15 control steps < a full 1-s window
    assert 0.25 < sum(c["settle_time_sum"]) < 0.4 and abs(sum(c["overshoot_sum"]) - 0.1) < 1e-3


def test_run_through_pays_in_entry_mode_but_not_in_settled_mode():
    _, pe = _settle_case("entry", [10.0, 10.0], speed=2.0, steps=8)
    dr, ps = _settle_case("settled", [10.0, 10.0], speed=2.0, steps=8)
    assert pe.tolist() == [1, 1] and ps.tolist() == [0, 0]
    assert sum(dr.counters()["settled"]) == 0 and dr.entered.all()


def test_settled_bonus_survives_until_read_and_reset_pays_nothing():
    t, dr = _drill(2, pay="settled")
    t.recover_xy = torch.tensor([[-6.3, 0.0]] * 2)
    dr.deadline[:], dr.limit[:] = 10.0, 100.0
    dr.elapsed[:], dr.hold[:], dr.entered[:] = 0.0, 0.0, False
    fired = None
    for i in range(80):
        dr.update(0.005)
        if dr.arrive_now.any() and fired is None:
            fired = i
    assert fired is not None and dr.arrive_now.all()  # never cleared here: still set many physics steps later
    t2, d2 = _drill(1, pay="settled")
    t2.recover_xy = torch.tensor([[-6.3, 0.0]])
    d2.deadline[:], d2.limit[:] = 10.0, 100.0
    d2.elapsed[:], d2.hold[:], d2.entered[:] = 0.0, 0.0, False
    for _ in range(40):  # 0.2 s of hold, not yet an arrival
        d2.update(0.005)
    d2.arrive_now[:] = False
    d2.reset(torch.tensor([0]))
    assert not d2.arrive_now.any() and sum(d2.counters()["settled"]) == 0


def test_partial_window_books_no_speed():
    n = 2
    t, dr = _drill(n)
    t.recover_xy = torch.tensor([[-2.4, 0.0]] * n)
    t._entity.data.root_link_lin_vel_w[:, 0] = 2.0
    for _ in range(4 * 10):  # 10 control steps (0.2 s) at 2 m/s, then the spot times out
        dr.update(0.005)
    assert (dr.best < 0).all()
    dr.limit[:] = 0.0
    dr.update(0.005)
    c = dr.counters()
    assert sum(c["short"]) == n and sum(c["booked"]) == 0 and sum(map(sum, c["best_hist"])) == 0


def test_settle_and_measure60_tasks():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    import picklebot_mj.tasks.footwork_specialist as fs
    a, s, m = load_env_cfg(fs.TASK_FW), load_env_cfg(fs.TASK_FW_SETTLE), load_env_cfg(fs.TASK_FW_MEASURE60)
    ab, sb, mb = a.actions["ball"], s.actions["ball"], m.actions["ball"]
    diff = [f.name for f in dataclasses.fields(ab) if getattr(ab, f.name) != getattr(sb, f.name)]
    assert diff == ["footwork_pay"] and sb.footwork_pay == "settled" and ab.footwork_pay == "entry"
    assert s.episode_length_s == a.episode_length_s == 20.0 and m.episode_length_s == 60.0
    assert mb.footwork_dist == (3.0, 5.0) and mb.footwork_pay == "settled"
    for k in a.rewards:
        assert a.rewards[k].func is s.rewards[k].func is m.rewards[k].func and a.rewards[k].weight == s.rewards[k].weight


def _rows(arrival, speed, its=400):
    rows = []
    for k in range(0, its + 1, 10):
        n = k  # spots resolved per sector so far
        c = {"arrived": [round(n * arrival)] * 8, "timed_out": [n - round(n * arrival)] * 8, "fell": [0] * 8,
             "best_hist": [[0] * 50 for _ in range(8)]}
        for i in range(8):
            c["best_hist"][i][int(round(speed / 0.1))] = n
        rows.append({"step": k * 24, "move": c})
    return rows


def test_watch_window_lines():
    from picklebot_mj import footwork_watch as fw
    assert fw.window_lines(_rows(0.4, 2.0, its=290)) is None  # no full window starting at >= 200 yet
    assert fw.window_lines(_rows(0.4, 2.0))["kill"] == "KILL-no-settle"
    assert fw.window_lines(_rows(0.8, 1.1))["kill"] == "KILL-speed-traded"
    w = fw.window_lines(_rows(0.8, 2.0))
    assert w["kill"] is None and abs(w["untimed_arrival"] - 0.8) < 0.02 and w["from_it"] == 300 and w["to_it"] == 400


def test_mid_move_heading_counter():
    import math
    t, dr = _drill(2)
    t.shadow = None
    t.recover_xy = torch.tensor([[-2.4, 0.0], [-2.4, 0.0]])  # 4 m toward the net
    dr.d0[:] = 4.0
    dr.limit[:] = 100.0
    # env 0 faces the net (yaw 0); env 1 faces away (yaw pi): both cross the half-way point
    t._entity.data.root_link_pose_w[1, 3:7] = torch.tensor([0.0, 0.0, 0.0, 1.0])
    t.place([[-4.3, 0.0], [-4.3, 0.0]])  # 1.9 m left: inside half of 4 m
    dr.update(0.005)
    assert dr.mid_done.all() and abs(float(dr.mid_yaw[0])) < 1e-3 and abs(float(dr.mid_yaw[1]) - 180.0) < 1e-3
    dr.limit[:] = 0.0  # resolve both
    dr.update(0.005)
    h = torch.tensor(dr.counters()["mid_heading_hist"]).sum(0)
    assert int(h[0]) == 1 and int(h[17]) == 1 and not dr.mid_done.any()
    assert math.isclose(dr.counters()["mid_heading_bin_deg"], 10.0)


def test_rally_train_task_changes_only_the_drill_and_the_speed_kernel():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    import picklebot_mj.tasks.agility as ag
    import picklebot_mj.tasks.footwork_specialist as fs
    src, a = load_env_cfg(ag.SRC_RES), load_env_cfg(fs.TASK_FW_RALLY_TRAIN)
    assert isinstance(a.actions["ball"], fs.FootworkBallActionCfg)
    b = a.actions["ball"]
    assert b.move_prob == 1.0 and b.footwork_pay == "settled" and b.footwork_dist == fs.DIST
    changed = sorted(k for k in src.rewards if src.rewards[k].func is not a.rewards[k].func
                     or src.rewards[k].weight != a.rewards[k].weight)
    assert changed == ["move_track_lin_vel", "move_track_yaw"], changed
    assert a.rewards["move_track_lin_vel"].func is fs.fw_track_lin_vel
    assert [k for k in src.actions if k != "ball" and src.actions[k] != a.actions[k]] == []
    assert a.episode_length_s >= 20.0


def test_first_step_time_is_booked():
    t, dr = _drill(2)
    t.shadow = None
    t.recover_xy = torch.tensor([[-2.4, 0.0], [-2.4, 0.0]])  # 4 m toward the net
    dr.d0[:], dr.limit[:], dr.elapsed[:] = 4.0, 100.0, 0.0
    for _ in range(100):  # 0.5 s, no progress
        dr.update(0.005)
    assert (dr.first_t < 0).all()
    t.place([[-4.8, 0.0], [-6.0, 0.0]])  # env 0 is 1.6 m closer, env 1 only 0.4 m
    dr.update(0.005)
    assert abs(float(dr.first_t[0]) - 0.500) < 1e-3 and float(dr.first_t[1]) < 0  # elapsed before this step
    dr.limit[:] = 0.0
    dr.update(0.005)
    h = torch.tensor(dr.counters()["first_step_hist"]).sum(0)
    assert int(h.sum()) == 1 and int(h[9]) + int(h[10]) == 1  # 0.500 s at a 0.05-s bin edge (float)


def test_fast4_tasks():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    import picklebot_mj.tasks.footwork_specialist as fs
    a, f, m = load_env_cfg(fs.TASK_FW), load_env_cfg(fs.TASK_FW_FAST4), load_env_cfg(fs.TASK_FW_MEASURE_FAST4)
    fb, mb = f.actions["ball"], m.actions["ball"]
    assert fb.footwork_cmd_cap == 4.0 and fb.deadline_v_req == (1.5, 3.5) and fb.footwork_dist == (2.0, 6.0)
    assert fb.footwork_pay == "settled" and mb.footwork_dist == (4.0, 6.0) and m.episode_length_s == 60.0
    assert a.actions["ball"].footwork_cmd_cap == 2.5
    for k in a.rewards:
        assert a.rewards[k].func is f.rewards[k].func and a.rewards[k].weight == f.rewards[k].weight


def test_rally_fastmove_only_changes_move_speed_reward():
    """D-196: the d1s3 task equals 22b's except move_track_lin_vel's function; the function equals 22b's outside move
    episodes and scores the 2.5-m/s-capped command with the widened kernel inside them."""
    import dataclasses as dc
    from types import SimpleNamespace
    import torch
    from mjlab.tasks.registry import load_env_cfg
    from picklebot_mj.tasks import agility as ag
    import mjlab.tasks  # noqa: F401
    from picklebot_mj.tasks import footwork_specialist as fs
    from picklebot_mj.tasks import move_drill as md
    a, b = load_env_cfg(ag.SRC_22B), load_env_cfg(fs.TASK_RALLY_FASTMOVE)
    assert type(a.actions["ball"]) is type(b.actions["ball"]) and dc.asdict(a.actions["ball"]) == dc.asdict(b.actions["ball"])
    assert list(a.rewards) == list(b.rewards)
    diff = [k for k in a.rewards if a.rewards[k] != b.rewards[k]]
    assert diff == ["move_track_lin_vel"] and b.rewards["move_track_lin_vel"].func is fs.rally_fast_track_lin_vel
    assert a.episode_length_s == b.episode_length_s and list(a.observations) == list(b.observations)
    # function: 4 envs, spot 3 m ahead along x, robot facing +x (yaw 0), moving at 1.9 m/s
    n = 4
    quat = torch.tensor([[1.0, 0, 0, 0]] * n)
    data = SimpleNamespace(root_link_pose_w=torch.cat([torch.zeros(n, 3), quat], -1),
                           root_link_lin_vel_b=torch.tensor([[1.9, 0.0]] * n))
    t = SimpleNamespace(_entity=SimpleNamespace(data=data), recover_xy=torch.tensor([[3.0, 0.0]] * n),
                        pelvis_xy=lambda: torch.zeros(n, 2), shadow=None, cfg=SimpleNamespace())
    dr = SimpleNamespace(t=t, move_ep=torch.tensor([True, True, False, False]))
    dr.command = lambda: md.MoveDrill.command(dr)
    env = SimpleNamespace(num_envs=n, device="cpu", action_manager=SimpleNamespace(get_term=lambda name: SimpleNamespace(drill=dr)))
    new, old = fs.rally_fast_track_lin_vel(env), md.move_track_lin_vel(env)
    assert torch.allclose(new[2:], old[2:])  # outside move episodes (zero here: no walk mask) identical
    assert float(old[0]) < 0.05 and float(new[0]) > 0.75  # 1.9 m/s toward a 3-m spot: 22b pays 0.04, d1s3 0.79


def test_rally_ready_adds_only_the_ready_term_and_pays_once_per_event():
    """D-199: the ready task equals d1s3's (Rally22b-FastMove) except the ball class (same field values) and one added
    reward term; the latch marks the envs given a ball (fire | receive); the term pays exp(-(v/0.3)^2) exp(-(d/0.5)^2)
    on the next reward step only."""
    import dataclasses as dc
    import math
    from types import SimpleNamespace
    import torch
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    from picklebot_mj.tasks import footwork_specialist as fs
    a, b = load_env_cfg(fs.TASK_RALLY_FASTMOVE), load_env_cfg(fs.TASK_RALLY_READY)
    assert type(b.actions["ball"]) is fs.ReadyBallActionCfg
    assert dc.asdict(a.actions["ball"]) == dc.asdict(b.actions["ball"])
    assert list(b.rewards) == list(a.rewards) + ["ready_at_event"]
    assert all(a.rewards[k] == b.rewards[k] for k in a.rewards)
    assert b.rewards["ready_at_event"].weight == fs.READY_W and b.rewards["ready_at_event"].func is fs.ready_at_event
    n = 4
    fire, recv = torch.tensor([True, False, False, False]), torch.tensor([False, True, False, False])
    data = SimpleNamespace(root_link_lin_vel_w=torch.tensor([[0.0, 0, 0], [0.3, 0, 0], [0.0, 0, 0], [0.0, 0, 0]]))
    t = SimpleNamespace(ready_due=torch.zeros(n, dtype=torch.bool), ready_val=torch.zeros(n), _entity=SimpleNamespace(data=data),
                        recover_xy=torch.tensor([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [1.0, 0.0]]),
                        pelvis_xy=lambda: torch.zeros(n, 2))

    def pair_step(*a, **k):
        return fire, recv
    t.pairs = SimpleNamespace(step=pair_step)
    ages = torch.tensor([5.0, 5.0, 5.0, 5.0])
    fs.install_ready_latch(t, age_fn=lambda: ages)
    t.pairs.step()
    # _refeed then redraws the new ball's recovery spot for the fired envs: the paid value must not change
    t.recover_xy = torch.tensor([[3.0, 3.0], [3.0, 3.0], [0.0, 0.0], [1.0, 0.0]])
    t.pairs.step()  # a second physics substep: already latched, the stored value holds
    env = SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: t))
    r = fs.ready_at_event(env)
    assert abs(float(r[0]) - 1.0) < 1e-6 and abs(float(r[1]) - math.exp(-1.0)) < 1e-6 and float(r[2]) == 0.0
    assert float(fs.ready_at_event(env).sum()) == 0.0  # paid once: the latch is cleared
    # an event within READY_MIN_AGE_S of the episode start is not paid
    ages[:] = 0.5
    t.pairs.step()
    assert float(fs.ready_at_event(env).sum()) == 0.0
    # d_std 1.0: 1 m from the spot, still -> exp(-1)
    t.recover_xy = torch.tensor([[1.0, 0.0], [0.0, 0.0], [0.0, 0.0], [1.0, 0.0]])
    ages[:] = 5.0
    t.pairs.step()
    assert abs(float(fs.ready_at_event(env)[0]) - math.exp(-1.0)) < 1e-6


def test_rally_parked_adds_one_term_paid_only_while_parked_on_a_dead_court():
    """D-202: the parked task equals d1s3's except one added reward term; the term pays ready_value only for envs parked
    on a dead court, not busy, not young; never at a live court."""
    import math
    from types import SimpleNamespace
    import torch
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    from picklebot_mj.tasks import footwork_specialist as fs
    a, b = load_env_cfg(fs.TASK_RALLY_FASTMOVE), load_env_cfg(fs.TASK_RALLY_PARKED)
    assert type(a.actions["ball"]) is type(b.actions["ball"])
    assert list(b.rewards) == list(a.rewards) + ["parked_ready"]
    assert all(a.rewards[k] == b.rewards[k] for k in a.rewards)
    assert b.rewards["parked_ready"].weight == fs.PARKED_W and b.rewards["parked_ready"].func is fs.parked_ready
    n = 6  # envs 0-2 on courts 0-2 side A, 3-5 their partners
    pairs = SimpleNamespace(court_dead=torch.tensor([True, True, False]), parked=torch.tensor([True, True, True, True, False, True]),
                            partner=(torch.arange(n) + 3) % n)
    data = SimpleNamespace(root_link_lin_vel_w=torch.zeros(n, 3))
    t = SimpleNamespace(pairs=pairs, _entity=SimpleNamespace(data=data), recover_xy=torch.zeros(n, 2),
                        pelvis_xy=lambda: torch.zeros(n, 2), drill=SimpleNamespace(move_ep=torch.tensor([False, True, False, False, False, False])),
                        shadow=None)
    env = SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: t), episode_length_buf=torch.tensor([500, 500, 500, 500, 500, 10]),
                          step_dt=0.02)
    r = fs.parked_ready(env)
    # env 0: dead court 0, parked, set -> 1; env 1: busy (move episode) -> 0; env 2: court 2 live -> 0;
    # env 3: court 0 dead, parked -> 1; env 4: not parked -> 0; env 5: court 2 live (and young) -> 0
    assert r.tolist() == [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    data.root_link_lin_vel_w[0, 0] = 0.3
    assert abs(float(fs.parked_ready(env)[0]) - math.exp(-1.0)) < 1e-6


def test_parked_mask_young_alone_and_on_real_pair_courts():
    """D-202 (architecture, round 66): young is tested alone (dead court, parked, 0.2 s old -> 0); on a real PairCourts the
    mask is true only from the rally's end to the feeder fire, false on the fire step and on hand-off steps, and false
    for a robot reset within READY_MIN_AGE_S. Rewards are computed after the step's pair update."""
    from types import SimpleNamespace
    import torch
    from picklebot_mj.pairs import PairCourts
    from picklebot_mj.tasks import footwork_specialist as fs
    F = lambda *i: torch.tensor([k in i for k in range(4)])  # noqa: E731
    Z = F()
    pc = PairCourts(4, "cpu", handoff="contact")  # courts (0, 2) and (1, 3)
    t = SimpleNamespace(pairs=pc, drill=None, shadow=None)
    env = SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: t), episode_length_buf=torch.full((4,), 10),
                          step_dt=0.02)
    pc.on_reset(torch.arange(4))
    assert pc.court_dead.all() and pc.parked.all()
    assert not fs.parked_mask(env).any()  # dead, parked, but 0.2 s old
    env.episode_length_buf[:] = 500
    assert fs.parked_mask(env).all()
    fired = None
    for _ in range(30):  # restart delay 0.1 s at dt 0.01
        fire, _ = pc.step(Z, Z, Z, Z, 0.01, 0.1, contact=Z)
        m = fs.parked_mask(env)
        if fire.any():
            fired = fire.clone()
            assert not m.any()  # the fire step: both courts live
            break
        assert m.all()
    a = 2 if fired[2] else 0
    b = 2 - a
    _, recv = pc.step(Z, Z, Z, Z, 0.01, 0.1, contact=F(a))  # a's legal contact hands the ball to b
    assert bool(recv[b]) and not fs.parked_mask(env)[[a, b]].any()
    pc.step(F(a), F(a), Z, Z, 0.01, 0.1, contact=Z)  # a's own copy lands legally: a parked, court live
    assert bool(pc.parked[a]) and not fs.parked_mask(env)[[a, b]].any()
    pc.step(F(b), Z, Z, Z, 0.01, 0.1, contact=Z)  # b misses: the rally ends, both parked on a dead court
    assert fs.parked_mask(env)[[a, b]].all()
    pc.on_reset(torch.tensor([a]))
    env.episode_length_buf[a] = 0  # a robot reset: young
    m = fs.parked_mask(env)
    assert not bool(m[a]) and bool(m[b])


def test_parked_mask_needs_both_robots_idle():
    """D-202 (RL, round 66): on a dead court a parked robot is not paid while its partner still has a ball in play."""
    from types import SimpleNamespace
    import torch
    from picklebot_mj.pairs import PairCourts
    from picklebot_mj.tasks import footwork_specialist as fs
    pc = PairCourts(4, "cpu", handoff="contact")
    pc.on_reset(torch.arange(4))
    t = SimpleNamespace(pairs=pc, drill=None, shadow=None)
    env = SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: t), episode_length_buf=torch.full((4,), 500),
                          step_dt=0.02)
    assert fs.parked_mask(env).all()
    pc.parked[2] = False  # env 2 (court 0's side B) still has a ball in play
    assert fs.parked_mask(env).tolist() == [False, True, False, True]


def test_rally_idlerec_changes_only_the_recovery_function():
    """D-205: the IdleRec task equals FastMove except recovery's function (same weight, same std)."""
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    from picklebot_mj.tasks import footwork_specialist as fs
    from picklebot_mj.tasks import return_stand as rs
    a, b = load_env_cfg(fs.TASK_RALLY_FASTMOVE), load_env_cfg(fs.TASK_RALLY_IDLEREC)
    assert list(a.rewards) == list(b.rewards) and type(a.actions["ball"]) is type(b.actions["ball"])
    for k in a.rewards:
        if k == "recovery":
            assert a.rewards[k].func is rs.recovery_reward and b.rewards[k].func is fs.rally_recovery_reward
            assert a.rewards[k].weight == b.rewards[k].weight and a.rewards[k].params == b.rewards[k].params
        else:
            assert a.rewards[k] == b.rewards[k]


def test_idle_recovery_on_a_real_pair_court():
    """D-205: paid after a reset (parked), the fired env unpaid once its feed is in play, the receiver unpaid from the
    hand-off, hit_done envs paid as before, busy envs unpaid; distance only."""
    import math
    from types import SimpleNamespace
    import torch
    from picklebot_mj.pairs import PairCourts
    from picklebot_mj.tasks import footwork_specialist as fs
    F = lambda *i: torch.tensor([k in i for k in range(4)])  # noqa: E731
    Z = F()
    pc = PairCourts(4, "cpu", handoff="contact")
    move = torch.zeros(4, dtype=torch.bool)
    t = SimpleNamespace(pairs=pc, hit_done=torch.zeros(4, dtype=torch.bool), drill=SimpleNamespace(move_ep=move), shadow=None,
                        recover_xy=torch.zeros(4, 2), pelvis_xy=lambda: torch.tensor([[0.0, 0.0], [1.5, 0.0], [0.0, 0.0], [0.0, 0.0]]))
    env = SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: t), common_step_counter=1)
    pc.on_reset(torch.arange(4))
    r = fs.rally_recovery_reward(env, std=1.5)
    assert r.tolist()[0] == 1.0 and abs(r[1] - math.exp(-1.0)) < 1e-6 and r[2] == 1.0 and r[3] == 1.0  # parked: paid by distance
    move[3] = True
    assert fs.rally_recovery_reward(env, std=1.5)[3] == 0.0  # busy: unpaid
    move[3] = False
    fire = Z
    for _ in range(30):
        fire, _ = pc.step(Z, Z, Z, Z, 0.01, 0.1, contact=Z)
        if fire.any():
            break
    a = int(fire.nonzero()[0])
    b = (a + 2) % 4
    r = fs.rally_recovery_reward(env, std=1.5)
    assert r[a] == 0.0 and r[b] > 0.0  # the fed env has its ball in play; its partner waits parked
    _, recv = pc.step(Z, Z, Z, Z, 0.01, 0.1, contact=F(a))  # a's legal contact hands the ball to b
    t.hit_done[a] = True
    r = fs.rally_recovery_reward(env, std=1.5)
    assert bool(recv[b]) and r[b] == 0.0 and r[a] > 0.0  # b receives: unpaid; a hit: paid as before


def test_first_step_bonus_pays_once_per_spot_and_is_off_by_default():
    from picklebot_mj.tasks import footwork_specialist as fs
    for on in (True, False):
        t, dr = _drill(2, first_bonus=on)
        t.shadow = None
        t.recover_xy = torch.tensor([[-2.4, 0.0], [-2.4, 0.0]])  # 4 m toward the net
        dr.d0[:], dr.limit[:], dr.elapsed[:] = 4.0, 100.0, 0.0
        for _ in range(240):  # 1.2 s, no progress
            dr.update(0.005)
        assert float(dr.first_now.abs().sum()) == 0.0
        t.place([[-4.8, 0.0], [-6.0, 0.0]])  # env 0 is 1.6 m closer, env 1 only 0.4 m
        dr.update(0.005)
        want = (fs.FIRST_PAY_T - 1.2) if on else 0.0
        assert abs(float(dr.first_now[0]) - want) < 2e-3 and float(dr.first_now[1]) == 0.0
        dr.first_now.zero_()  # read-and-clear (fw_first_step)
        t.place([[-3.0, 0.0], [-4.4, 0.0]])  # both further on; env 1 now 1.6 m closer too
        dr.update(0.005)
        assert float(dr.first_now[0]) == 0.0  # once per spot
        assert abs(float(dr.first_now[1]) - (want and fs.FIRST_PAY_T - 1.205)) < 2e-3
        assert abs(sum(dr.counters()["first_pay_sum"]) - float(dr.first_now[1]) - want) < 4e-3


def test_first_step_bonus_is_clamped_and_skips_short_spots():
    t, dr = _drill(2, first_bonus=True)
    t.shadow = None
    t.recover_xy = torch.tensor([[-2.4, 0.0], [-5.2, 0.0]])
    dr.d0[:], dr.limit[:], dr.elapsed[:] = torch.tensor([4.0, 1.2]), 100.0, 3.0  # late start; env 1 is a short spot
    t.place([[-4.8, 0.0], [-5.2, 0.0]])
    dr.update(0.005)
    assert float(dr.first_now[0]) == 0.0 and float(dr.first_t[0]) > 0  # 3 s: clamped to zero, still booked
    assert float(dr.first_now[1]) == 0.0 and float(dr.first_t[1]) < 0


def test_quick_task_changes_only_the_spots_and_adds_the_bonus():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    import picklebot_mj.tasks.footwork_specialist as fs
    from picklebot_mj.tasks import move_drill as md
    s, q = load_env_cfg(fs.TASK_FW_SETTLE), load_env_cfg(fs.TASK_FW_QUICK)
    sb, qb = s.actions["ball"], q.actions["ball"]
    diff = {f.name for f in dataclasses.fields(sb) if getattr(sb, f.name) != getattr(qb, f.name)}
    assert diff == {"footwork_dist", "deadline_dist", "move_spot_box", "footwork_first_bonus"}, diff
    assert qb.footwork_dist == md.DIST_RANGE and qb.move_spot_box == md.SPOT_BOX and qb.footwork_first_bonus
    assert qb.footwork_pay == "settled" and qb.footwork_cmd_cap == 2.5 and qb.deadline_v_req == (1.2, 2.2)
    assert set(q.rewards) - set(s.rewards) == {"fw_first_step"} and set(s.rewards) <= set(q.rewards)
    assert q.rewards["fw_first_step"].weight == q.rewards["move_arrival"].weight > 0
    for k in s.rewards:
        assert s.rewards[k].func is q.rewards[k].func and s.rewards[k].weight == q.rewards[k].weight
    assert q.episode_length_s == s.episode_length_s and not s.actions["ball"].footwork_first_bonus
    assert "fw_first_step" not in load_env_cfg(fs.TASK_FW_MEASURE_COURT).rewards


def test_quick2_changes_only_the_pay_span():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    import picklebot_mj.tasks.footwork_specialist as fs
    q, q2 = load_env_cfg(fs.TASK_FW_QUICK), load_env_cfg(fs.TASK_FW_QUICK2)
    a, b = q.actions["ball"], q2.actions["ball"]
    diff = {f.name for f in dataclasses.fields(a) if getattr(a, f.name) != getattr(b, f.name)}
    assert diff == {"footwork_first_span"} and a.footwork_first_span == 1.0 and b.footwork_first_span == 0.5
    assert set(q.rewards) == set(q2.rewards)
    for k in q.rewards:
        assert q.rewards[k].func is q2.rewards[k].func and q.rewards[k].weight == q2.rewards[k].weight


def test_steeper_span_pays_double_and_saturates():
    for span, t0, want in ((0.5, 1.2, 0.8), (0.5, 1.0, 1.0), (0.5, 1.7, 0.0), (1.0, 1.2, 0.4)):
        t, dr = _drill(1, first_bonus=True, first_span=span)
        t.shadow = None
        t.recover_xy = torch.tensor([[-2.4, 0.0]])
        dr.d0[:], dr.limit[:], dr.elapsed[:] = 4.0, 100.0, t0
        t.place([[-4.8, 0.0]])
        dr.update(0.005)
        assert abs(float(dr.first_now[0]) - want) < 1e-4, (span, t0, float(dr.first_now[0]))
