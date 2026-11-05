"""D-229: the set-start read's drill reset places both robots of a restarting court on their spots (GPU)."""
import os
import sys

import pytest
import torch


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_drill_reset_places_both_robots_on_their_spots_before_the_feeder_ball():
    sys.path.insert(0, os.path.dirname(__file__))
    from test_drill_v2 import LATENT, _env
    if not LATENT.exists():
        pytest.skip("needs the H1 latent controller")
    task = "Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1"
    env = _env(task, n=64, pair_drill_reset=True, pair_reset_parks=True, court_feed_prob=1.0)
    t = env.action_manager.get_term("ball")
    pc = t.pairs
    orig = pc.step
    seen = {"placed": 0, "fires_after": []}
    starts = torch.full((pc.h,), -1, dtype=torch.long, device=t.device)
    k = {"i": 0}

    def step(*a, **kw):
        fire, recv = orig(*a, **kw)
        starts[pc.start_now] = k["i"]
        f = fire[: pc.h] | fire[pc.h:]
        for c in f.nonzero().squeeze(-1).tolist():
            if starts[c] >= 0:
                seen["fires_after"].append(k["i"] - int(starts[c]))
        k["i"] += 1
        return fire, recv

    pc.step = step
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    with torch.inference_mode():
        for _ in range(3):
            env.step(act)
            d = (t.pelvis_xy() - t.recover_xy).norm(dim=-1)
            if getattr(t, "drill_places", 0) > seen["placed"]:
                seen["placed"] = t.drill_places
                assert float(d.max()) < 0.15, float(d.max())  # all courts restart together after the first reset
        for _ in range(200):
            env.step(act)
    summ = t.launch_summary()
    env.close()
    assert summ["drill_places"] >= 64, summ["drill_places"]
    dt = env.physics_dt if hasattr(env, "physics_dt") else 0.005
    # the feeder ball comes refeed_delay_s after the placement
    lag = sorted(seen["fires_after"])
    assert lag and abs(lag[len(lag) // 2] * dt - t.cfg.refeed_delay_s) < 0.05, (lag[:5], dt)


def test_drill_reset_is_off_by_default():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg("Picklebot-Latent-Court-Res-G1")
    assert getattr(cfg.actions["ball"], "pair_drill_reset", False) is False
    assert getattr(cfg.actions["ball"], "pair_set_timeout_s", 0.0) == 0.0
