"""Stage 5B tracking teacher task: paddle G1 with a collidable paddle face, multi-clip motion command."""

from pathlib import Path

import numpy as np
import pytest
import torch

MOTION = Path(__file__).resolve().parents[1] / "artifacts" / "motion" / "tracking" / "tennis-v5.npz"
needs = pytest.mark.skipif(not (torch.cuda.is_available() and MOTION.exists()),
                           reason="needs CUDA and artifacts/motion/tracking/tennis-v5.npz")


def _small_motion(tmp_path, n_clips=3, frames=120):
    """The first n clips of the tennis file, each cut to `frames` frames."""
    d = np.load(MOTION)
    starts = d["clip_starts"]
    keep = np.concatenate([np.arange(s, s + frames) for s in starts[:n_clips]])
    out = {k: d[k][keep] for k in ("joint_pos", "joint_vel", "body_pos_w", "body_quat_w", "body_lin_vel_w",
                                   "body_ang_vel_w")}
    out.update(fps=d["fps"], clip_starts=np.arange(n_clips) * frames, clip_names=d["clip_names"][:n_clips])
    path = tmp_path / "small.npz"
    np.savez(path, **out)
    return path


@needs
def test_paddle_face_collides_and_multi_clip_never_crosses_a_boundary(tmp_path):
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.tasks.tracking import paddle_tracking_env_cfg

    cfg = paddle_tracking_env_cfg(str(_small_motion(tmp_path)))
    cfg.scene.num_envs = 64
    env = ManagerBasedRlEnv(cfg, device="cuda")
    m = env.sim.mj_model
    face = m.geom("robot/paddle_face").id if "robot/paddle_face" in [m.geom(i).name for i in range(m.ngeom)] \
        else m.geom("paddle_face").id
    assert m.geom_contype[face] == 1 and m.geom_conaffinity[face] == 1
    assert sum(int(m.geom_contype[g] > 0) for g in range(m.ngeom)) > 30  # full G1 self-collision kept
    env.reset()
    cmd = env.command_manager.get_term("motion")
    assert cmd.clip_starts.tolist() == [0, 120, 240]
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device="cuda")
    for _ in range(300):  # > 2 clip lengths: every env wraps at least twice
        env.step(act)
        t, k = cmd.time_steps, cmd.clip_index
        assert (t >= cmd.clip_starts[k]).all() and (t < cmd.clip_ends[k]).all()
        assert (cmd.clip_of(t) == k).all()
    env.close()
