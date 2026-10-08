"""Stage 5B style prior: AMP-style features, expert transitions and discriminator (picklebot_mj/style.py)."""

import math
from pathlib import Path

import numpy as np
import pytest
import torch

from picklebot_mj.style import KEY_BODIES, ROOT_BODY, StyleCfg, StyleDiscriminator, expert_transitions, features

MOTION = Path(__file__).resolve().parents[1] / "artifacts" / "motion" / "tracking"


def _yaw(theta):
    return torch.tensor([math.cos(theta / 2), 0.0, 0.0, math.sin(theta / 2)])


def _qmul(a, b):
    w1, x1, y1, z1 = a.unbind(-1)
    w2, x2, y2, z2 = b.unbind(-1)
    return torch.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], -1)


def _rot(q, v):
    from picklebot_mj.style import _quat_rotate_inv

    qc = q * torch.tensor([1.0, -1.0, -1.0, -1.0])
    return _quat_rotate_inv(qc.expand(*v.shape[:-1], 4), v)


def test_features_are_heading_invariant():
    torch.manual_seed(0)
    n = 8
    jp, jv = torch.randn(n, 29), torch.randn(n, 29)
    rp = torch.randn(n, 3)
    rq = torch.nn.functional.normalize(torch.randn(n, 4), dim=-1)
    lv, av, keys = torch.randn(n, 3), torch.randn(n, 3), torch.randn(n, 4, 3)
    phi = features(jp, jv, rp, rq, lv, av, keys)
    assert phi.shape == (n, 80)
    yq = _yaw(0.9)
    rq2 = _qmul(yq.expand(n, 4), rq)
    phi2 = features(jp, jv, _rot(yq, rp), rq2, _rot(yq, lv), _rot(yq, av), _rot(yq, keys))
    assert torch.allclose(phi, phi2, atol=1e-5)


def test_expert_transitions_never_cross_a_clip_boundary(tmp_path):
    names = [ROOT_BODY, *KEY_BODIES]
    n = 10
    d = {"joint_pos": np.zeros((n, 29)), "joint_vel": np.zeros((n, 29)),
         "body_pos_w": np.zeros((n, 5, 3)), "body_quat_w": np.tile([1.0, 0, 0, 0], (n, 5, 1)),
         "body_lin_vel_w": np.zeros((n, 5, 3)), "body_ang_vel_w": np.zeros((n, 5, 3)),
         "clip_starts": np.array([0, 4])}
    d["joint_pos"][:, 0] = np.arange(n)  # frame index in the first feature
    np.savez(tmp_path / "m.npz", **d)
    a, b = expert_transitions([tmp_path / "m.npz"], names)
    assert len(a) == n - 2  # 10 frames, 2 clips: 3 + 5 pairs
    assert torch.all(b[:, 0] - a[:, 0] == 1) and not torch.any(a[:, 0] == 3)


def test_discriminator_learns_to_prefer_expert_like_transitions(tmp_path):
    torch.manual_seed(0)
    disc = StyleDiscriminator.__new__(StyleDiscriminator)
    cfg = StyleCfg(hidden=(64, 64), lr=1e-3, batch=256, buffer=4096, update_every=1, updates=5)
    disc.cfg, disc.device = cfg, "cpu"
    disc.expert = torch.randn(4096, 8)
    disc.keep = torch.arange(8)
    disc.mean, disc.std = disc.expert.mean(0), disc.expert.std(0)
    disc.net = torch.nn.Sequential(torch.nn.Linear(8, 64), torch.nn.ReLU(), torch.nn.Linear(64, 64),
                                   torch.nn.ReLU(), torch.nn.Linear(64, 1))
    disc.opt = torch.optim.Adam(disc.net.parameters(), lr=cfg.lr)
    disc.buf = torch.zeros(cfg.buffer, 8)
    disc.n_buf = disc.ptr = disc.calls = disc.n_updates = 0
    disc.stats = {}
    agent = torch.randn(4096, 8) + 2.0
    for _ in range(40):
        disc.add(agent[torch.randint(0, 4096, (512,))])
        disc.step()
    assert disc.n_updates > 0
    assert disc.reward(torch.randn(512, 8)).mean() > disc.reward(torch.randn(512, 8) + 2.0).mean() + 0.2


@pytest.mark.skipif(not (torch.cuda.is_available() and (MOTION / "lafan-g1.npz").exists()),
                    reason="needs CUDA and the motion files")
def test_style_task_gives_bounded_rewards_and_trains_the_discriminator():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg("Picklebot-Student-Drill3-Style-G1")
    cfg.scene.num_envs = 256
    st = cfg.rewards["style"].params["cfg"]
    st.batch, st.update_every = 512, 4
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    assert env.step_dt == pytest.approx(0.02)  # 50 Hz, the motion files' rate
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device="cuda")
    for _ in range(12):
        env.step(act)
    r = env.reward_manager.get_term("style") if hasattr(env.reward_manager, "get_term") else None
    disc = env._picklebot_style["disc"]
    assert disc.n_updates >= 1 and disc.n_buf > 0
    rew = disc.reward(disc.buf[:disc.n_buf])
    assert torch.isfinite(rew).all() and (rew >= 0).all() and (rew <= 1).all()
    env.close()


def test_feature_mask_drops_the_excluded_joints_from_both_halves():
    from picklebot_mj.style import feature_mask

    joints = [f"j{i}" for i in range(26)] + ["right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint"]
    keep = feature_mask(joints, (r".*_wrist_.*",)).tolist()
    assert len(keep) == 2 * (80 - 6)
    for i in (26, 27, 28, 29 + 26, 29 + 27, 29 + 28):  # wrist angles and velocities
        assert i not in keep and 80 + i not in keep
    assert 0 in keep and 58 in keep and 80 + 79 in keep  # other joints, pelvis height, last key-body feature
