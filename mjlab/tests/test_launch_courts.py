"""D-235: launcher courts inside the drill-reset rally task play the court read's own episodes (GPU)."""
from pathlib import Path

import pytest
import torch

BASE = (Path(__file__).resolve().parents[1] / "artifacts" / "train" / "logs" / "picklebot_return_stand"
        / "2026-10-31_18-24-20_s5c-d1-fw1bS" / "model_32854.pt")
TASK = "Picklebot-Rally22b-FastMove-DrillReset-Launch-G1"


def test_launch_courts_are_off_by_default_and_on_in_the_task():
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist as fs
    from mjlab.tasks.registry import load_env_cfg
    assert getattr(load_env_cfg("Picklebot-Latent-Court-Res-G1").actions["ball"], "pair_launch_court_frac", 0.0) == 0.0
    assert getattr(load_env_cfg(fs.TASK_RALLY_FASTMOVE_DR).actions["ball"], "pair_launch_court_frac", 0.0) == 0.0
    cfg = load_env_cfg(TASK)
    b = cfg.actions["ball"]
    assert b.pair_launch_court_frac == 0.25 and b.pair_drill_court_frac == 0.5 and b.pair_drill_reset
    assert cfg.terminations["launch_time_out"].time_out


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_launch_courts_feed_their_own_robots_and_never_rally(monkeypatch):
    if not BASE.exists():
        pytest.skip("needs the d1 base")
    monkeypatch.setenv("PICKLEBOT_RES_BASE", str(BASE))
    monkeypatch.setenv("PICKLEBOT_LAM_R", "2")
    import mjlab.tasks  # noqa: F401
    import picklebot_mj.tasks.footwork_specialist  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg(TASK)
    cfg.scene.num_envs = 64
    b = cfg.actions["ball"]
    b.court_feed_prob, b.recovery_mode, b.refeed_delay_s = 1.0, "fixed", 0.5
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    le, h = t.launch_env, t.pairs.h
    court = torch.arange(64, device=t.device) % h
    assert int(le.sum()) == 16 and bool((le == ((court >= 8) & (court < 16))).all())
    assert bool((t.drill_scale[le] == 0).all()) and bool((t.drill_scale[court < 8] == 2).all())
    assert int(t.pairs.solo.sum()) == 8
    seen = {"lfire": 0, "court_feed": 0, "busy": 0}
    orig = t._refeed

    def refeed(fire):
        seen["lfire"] += int((fire & le).sum())
        orig(fire)
        seen["court_feed"] += int((t.court_feed & le).sum())

    t._refeed = refeed
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    with torch.inference_mode():
        for _ in range(450):  # 9 s: every launcher robot's first episode has ended
            env.step(act)
            seen["busy"] += int((t.drill.move_ep & le).sum()) + int((t.shadow.swing_ep & le).sum())
    summ = t.launch_summary()["launch_courts"]
    started = t.pairs.started.clone()
    env.close()
    assert summ["envs"] == 16 and summ["episodes_falls"][0] >= 16, summ
    assert seen["lfire"] > 0 and seen["court_feed"] == 0 and seen["busy"] == 0, seen
    assert not bool(started[8:16].any())
