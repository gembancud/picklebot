"""Aiming targets: observation layout, sampling, placement bonus, checkpoint expansion."""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def test_aim_task_appends_target_last():
    from picklebot_mj.tasks.return_stand import return_stand_env_cfg

    base, aim = return_stand_env_cfg(), return_stand_env_cfg(targets=True)
    for g in ("actor", "critic"):
        names = list(aim.observations[g].terms)
        assert names[-1] == "target" and names[:-1] == list(base.observations[g].terms)
    assert "placement" in aim.rewards and "placement" not in base.rewards
    r = list(aim.rewards)
    assert r.index("placement") < r.index("legal_return")  # legal_return clears the step flags
    assert aim.actions["ball"].targets and not base.actions["ball"].targets


def test_expand_checkpoint_preserves_outputs(tmp_path):
    from expand_checkpoint import expand_net

    torch.manual_seed(0)
    sd = {"mlp.0.weight": torch.randn(512, 110), "obs_normalizer._mean": torch.randn(1, 110),
          "obs_normalizer._var": torch.rand(1, 110) + 0.1}
    sd["obs_normalizer._std"] = sd["obs_normalizer._var"].sqrt()
    x = torch.randn(64, 110)
    f = lambda s, inp: ((inp - s["obs_normalizer._mean"]) / (s["obs_normalizer._std"] + 1e-8)) @ s["mlp.0.weight"].T
    y0 = f(sd, x)
    sd2 = {k: v.clone() for k, v in sd.items()}
    old, extra = expand_net(sd2, 112)
    assert (old, extra) == (110, 2)
    y1 = f(sd2, torch.cat([x, torch.randn(64, 2) * 5], 1))  # any target values
    assert torch.allclose(y0, y1, atol=1e-5)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA")
def test_targets_sampled_and_forced():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.tasks import TASK_AIM_LATERAL

    cfg = load_env_cfg(TASK_AIM_LATERAL)
    cfg.scene.num_envs = 512
    cfg.actions["ball"].compile_ball = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    obs, _ = env.reset()
    term = env.action_manager.get_term("ball")
    frac_b = term.target.float().mean().item()
    assert 0.42 < frac_b < 0.58
    assert obs["actor"].shape[-1] == 112 and obs["critic"].shape[-1] == 127
    # target observation is the last two actor columns
    from picklebot_mj.tasks.return_stand import TARGET_CENTRES
    exp = torch.tensor(TARGET_CENTRES, device="cuda")[term.target] / torch.tensor([6.7056, 3.048], device="cuda")
    assert torch.allclose(obs["actor"][:, -2:], exp, atol=1e-4)
    env.close() if hasattr(env, "close") else None
    cfg.actions["ball"].target_mode = "A"
    env2 = ManagerBasedRlEnv(cfg, device="cuda")
    env2.reset()
    assert (env2.action_manager.get_term("ball").target == 0).all()
