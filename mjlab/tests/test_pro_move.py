"""D-249: the pro-move drill (tasks/pro_move.py): frozen table, court -> robot mapping, task wiring (GPU)."""
from pathlib import Path

import pytest
import torch

BASE = (Path(__file__).resolve().parents[1] / "artifacts" / "train" / "logs" / "picklebot_return_stand"
        / "2026-10-31_18-24-20_s5c-d1-fw1bS" / "model_32854.pt")


def test_table_is_frozen_and_filtered():
    from picklebot_mj.tasks import pro_move as pm
    rows = pm.load_table()
    assert len(rows) == 167
    assert all(r["dur"] >= 0.5 and r["dist"] / r["dur"] <= 2.9 + 0.02 for r in rows)


def test_mapping_signs_and_class_counts():
    """The pro's left (dx < 0) is the robot's +y (MoveDrill sectors 1-3); toward the net (dy > 0) is +x."""
    from picklebot_mj.tasks import pro_move as pm
    rows = pm.load_table()
    v = pm.robot_disp(rows)
    u = v / v.norm(dim=-1, keepdim=True)
    cls, sec = pm.pro_class(u), pm.sector(u)
    left = torch.tensor([r["dx"] < 0 and abs(r["dx"]) > abs(r["dy"]) for r in rows])
    fwd = torch.tensor([r["dy"] > 0 and abs(r["dy"]) >= abs(r["dx"]) for r in rows])
    assert bool((cls[left] == 1).all()) and bool(((sec[left] >= 1) & (sec[left] <= 3)).all())
    assert bool((v[left, 1] > 0).all()) and bool((v[fwd, 0] > 0).all())
    n = torch.bincount(cls, minlength=4).tolist()
    assert dict(zip(pm.PRO_CLASSES, n)) == {"forward": 41, "left": 51, "back": 23, "right": 52}
    assert pm.sector(torch.tensor([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0]])).tolist() == [0, 2, 4, 6]


def test_pro_task_only_adds_the_pro_moves():
    import dataclasses
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.tasks.registry import load_env_cfg
    a = dataclasses.asdict(load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF).actions["ball"])
    b = dataclasses.asdict(load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF_PRO).actions["ball"])
    assert {k for k in a if a[k] != b[k]} == {"move_pro_moves"} and b["move_pro_moves"] is True
    assert b["move_sector_weights"] is None and b["move_prob"] > 0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_pro_drill_issues_table_spots_in_the_box(monkeypatch):
    if not BASE.exists():
        pytest.skip("needs the d1 base")
    monkeypatch.setenv("PICKLEBOT_RES_BASE", str(BASE))
    monkeypatch.setenv("PICKLEBOT_LAM_R", "2")
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg
    from picklebot_mj.tasks import move_drill as md
    from picklebot_mj.tasks.pro_move import ProMoveDrill
    cfg = load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF_PRO)
    cfg.scene.num_envs = 64
    b = cfg.actions["ball"]
    b.court_feed_prob, b.recovery_mode, b.refeed_delay_s = 1.0, "fixed", 0.5
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    dr = t.drill
    assert isinstance(dr, ProMoveDrill)
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    with torch.inference_mode():
        for _ in range(600):
            env.step(act)
    mv = dr.move_ep
    sp = t.recover_xy[mv]
    lo, hi = torch.tensor(md.SPOT_BOX[0]), torch.tensor(md.SPOT_BOX[1])
    s = t.launch_summary()["move_pro"]
    env.close()
    assert int(mv.sum()) > 0
    assert bool(((sp[:, 0] >= lo[0] - 1e-5) & (sp[:, 0] <= lo[1] + 1e-5) & (sp[:, 1].abs() <= hi[1] + 1e-5)).all())
    d0 = (sp - dr.start_xy[mv]).norm(dim=-1)
    assert bool((d0 <= float(dr.disp.norm(dim=-1).max()) + 1e-4).all())
    assert sum(s["pro_class"]) == int(dr.stats["issued"].sum()) > 0, s
