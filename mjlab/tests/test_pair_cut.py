"""D-217: pair_cut_prob cuts received hand-offs on half of the live pair courts (training only)."""
import os
import sys

import pytest
import torch


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_pair_cut_cuts_only_received_balls_on_cut_courts():
    sys.path.insert(0, os.path.dirname(__file__))
    from test_drill_v2 import LATENT, _env
    if not LATENT.exists():
        pytest.skip("needs the H1 latent controller")
    from picklebot_mj.tasks.return_stand import PAIR_CUT_T
    task = "Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-KeepAlive-Pairs-Coop-Moves-Weak-Pace25-LamR2-G1"
    env = _env(task, n=256, pair_cut_prob=1.0, court_feed_prob=1.0)
    t = env.action_manager.get_term("ball")
    assert t._cut_court is not None
    h = t.pairs.h
    court = torch.arange(t.num_envs, device=t.device) % h
    assert bool((t._cut_court == (court % 2 == 1)).all())  # no drill courts here: every odd court is a cut court
    pc = t.pairs
    orig = pc.step
    st = {"armed": False}

    def step(*a, **k):  # force hand-offs on parked envs (zero actions rarely make contact)
        fire, recv = orig(*a, **k)
        if st["armed"]:
            st["armed"] = False
            force = pc.parked & ~fire & ~recv
            pc.parked &= ~force
            recv = recv | force
        return fire, recv

    pc.step = step
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    cut_envs = torch.zeros(t.num_envs, dtype=torch.bool, device=t.device)
    with torch.inference_mode():
        for i in range(300):
            st["armed"] = i % 50 == 5
            env.step(act)
            if hasattr(t, "_cut_now"):
                cut_envs |= t._cut_now
    summ = t.launch_summary()
    env.close()
    assert summ["cuts"] > 20, summ["cuts"]
    assert bool(cut_envs.any()) and not bool((cut_envs & ~t._cut_court).any())
    assert summ["outcome_after_cut"][0] > 0, summ["outcome_after_cut"]  # feeder balls followed the cuts
    assert PAIR_CUT_T[0] < PAIR_CUT_T[1]


def test_pair_cut_is_off_by_default():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    import picklebot_mj.tasks.footwork_specialist  # noqa: F401
    cfg = load_env_cfg("Picklebot-Rally22b-FastMove-G1")
    assert cfg.actions["ball"].pair_cut_prob == 0.0
