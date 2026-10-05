"""Stage 5 Drill 1 (D-041): move-to-spot episodes, teacher command, arrival, ready stance, metrics."""

import math

import pytest
import torch


def test_drill_task_config():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.tasks import TASK_DRILL_MOVE, TASK_FOOTWORK_WIDE

    d1, f2 = load_env_cfg(TASK_DRILL_MOVE), load_env_cfg(TASK_FOOTWORK_WIDE)
    assert d1.actions["ball"].move_prob == 0.75
    assert set(d1.rewards) - set(f2.rewards) == {"move_track_lin_vel", "move_track_yaw", "move_arrival", "ready_stance"}
    for g in ("actor", "critic"):  # same inputs as F2, so model_12000 warm-starts directly
        assert list(d1.observations[g].terms) == list(f2.observations[g].terms)
    tw = d1.commands["twist"].ranges  # the robot never sees a movement command
    assert tw.lin_vel_x == (0.0, 0.0) and tw.lin_vel_y == (0.0, 0.0) and tw.ang_vel_z == (0.0, 0.0)


@pytest.fixture(scope="module")
def drill_env():
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.feeds import STAGE4_FAMILIES, FeedMix
    from picklebot_mj.tasks.return_stand import return_stand_env_cfg

    cfg = return_stand_env_cfg(targets=True, start_box=True, recovery=True, free_feet=True, wide_shaping=True,
                               move_prob=0.75)
    cfg.actions["ball"].feed_mix = FeedMix({f: 1.0 for f in STAGE4_FAMILIES})
    cfg.scene.num_envs = 256
    cfg.actions["ball"].compile_ball = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    return env


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_move_episodes_park_the_ball_and_issue_balanced_spots(drill_env):
    from picklebot_mj.tasks.move_drill import DIST_RANGE, N_SECTORS, PARK_POS, SPOT_BOX

    env = drill_env
    t = env.action_manager.get_term("ball")
    dr = t.drill
    frac = float(dr.move_ep.float().mean())
    assert 0.6 < frac < 0.9  # ~75 % move episodes
    mv = dr.move_ep
    assert torch.allclose(t.ball.pos[mv], torch.tensor(PARK_POS, device="cuda").expand(int(mv.sum()), 3))
    assert t.rules.dead[mv].all() and t.tallied[mv].all() and not t.rules.dead[~mv].any()
    ep0 = int(t.ep["episodes"])
    act = torch.zeros(256, 29, device="cuda")
    for _ in range(10):
        env.step(act)
    assert torch.allclose(t.ball.pos[dr.move_ep], torch.tensor(PARK_POS, device="cuda").expand(int(dr.move_ep.sum()), 3))
    assert int(t.ep["episodes"]) == ep0  # move episodes add no feed tallies
    # Spots inside the half-court box, within the distance range from where they were issued.
    sp = t.recover_xy[dr.move_ep]
    assert (sp[:, 0] >= SPOT_BOX[0][0] - 1e-5).all() and (sp[:, 0] <= SPOT_BOX[0][1] + 1e-5).all()
    assert (sp[:, 1].abs() <= SPOT_BOX[1][1] + 1e-5).all()
    d0 = (sp - dr.start_xy[dr.move_ep]).norm(dim=-1)
    assert (d0 <= DIST_RANGE[1] + 1e-4).all()
    # Every sector is issued (balanced sampling; reversal only near the box walls).
    issued = dr.stats["issued"]
    assert issued.shape == (N_SECTORS,) and (issued > 0).all()
    assert float(issued.max()) / float(issued.float().mean()) < 2.0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_teacher_command_points_at_the_spot_and_faces_the_net(drill_env):
    from picklebot_mj.tasks.move_drill import CMD_MAX_SPEED

    env = drill_env
    t = env.action_manager.get_term("ball")
    dr = t.drill
    v_b, wz = dr.command()
    assert (v_b.norm(dim=-1) <= CMD_MAX_SPEED + 1e-5).all()
    # Rotate back to the court frame: the command points at the spot.
    q = t._entity.data.root_link_pose_w[:, 3:7]
    w, x, y, z = q.unbind(-1)
    yaw = torch.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    c, s = torch.cos(yaw), torch.sin(yaw)
    v_w = torch.stack([c * v_b[:, 0] - s * v_b[:, 1], s * v_b[:, 0] + c * v_b[:, 1]], -1)
    delta = t.recover_xy - t.pelvis_xy()
    far = delta.norm(dim=-1) > 0.1
    cos = (v_w[far] * delta[far]).sum(-1) / (v_w[far].norm(dim=-1) * delta[far].norm(dim=-1))
    assert (cos > 0.999).all()
    assert ((torch.sign(wz) == torch.sign(-torch.sin(yaw))) | (wz.abs() < 1e-6)).all()  # turn back toward the net


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_arrival_ready_stance_and_metrics(drill_env):
    from picklebot_mj.tasks.move_drill import ARRIVE_HOLD_S, move_arrival, ready_stance

    env = drill_env
    t = env.action_manager.get_term("ball")
    dr = t.drill
    mv = dr.move_ep.clone()
    # Put every move-episode spot under the robot: it arrives after the hold time if it is slow enough.
    t.recover_xy = torch.where(mv.unsqueeze(-1), t.pelvis_xy(), t.recover_xy)
    issued0 = dr.stats["issued"].clone()
    arrived0 = int(dr.stats["arrived"].sum())
    dt = env.physics_dt
    still = torch.ones(256, dtype=torch.bool, device="cuda")
    for _ in range(int(ARRIVE_HOLD_S / dt) + 2):
        dr.update(dt)
        still &= t._entity.data.root_link_lin_vel_b[:, :2].norm(dim=-1) < 0.2
    n_arr = int(dr.stats["arrived"].sum()) - arrived0
    assert n_arr >= int((mv & still).sum()) and n_arr > 0
    assert int(dr.stats["issued"].sum() - issued0.sum()) >= n_arr  # a new spot after each arrival
    r = move_arrival(env)
    assert int((r > 0).sum()) >= 1 and not dr.arrive_now.any()  # one-shot, cleared on read
    # Ready stance is zero away from the spot and outside move episodes.
    t.recover_xy = torch.where(mv.unsqueeze(-1), t.pelvis_xy() + 2.0, t.recover_xy)
    assert torch.equal(ready_stance(env), torch.zeros(256, device="cuda"))
    s = dr.summary()
    assert len(s["sectors"]) == 8 and s["all"]["finished"] >= n_arr
