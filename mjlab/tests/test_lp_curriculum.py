"""Learning-progress feed curriculum (D-066): picklebot_mj/curriculum.py LPSampler and the ball term's levels."""

from pathlib import Path

import pytest
import torch

from picklebot_mj.curriculum import LPSampler

ROOT = Path(__file__).resolve().parents[1]
LATENT = ROOT / "artifacts" / "train" / "latent" / "latent-07" / "latent_10651.pt"
needs = pytest.mark.skipif(not (torch.cuda.is_available() and LATENT.exists()),
                           reason="needs CUDA and the H1 latent controller")


def test_learnable_units_get_more_weight_than_hopeless_or_mastered_ones():
    s = LPSampler([1.0, 1.0, 1.0, 0.0])
    unit = torch.tensor([0] * 200 + [1] * 200 + [2] * 200)
    succ = torch.cat([torch.zeros(200, dtype=torch.bool),            # never succeeds
                      torch.rand(200, generator=torch.Generator().manual_seed(0)) < 0.5,  # learnable
                      torch.ones(200, dtype=torch.bool)])             # mastered
    for _ in range(50):
        s.update(unit, succ)
    w = s.weights()
    assert w[3] == 0  # inactive unit
    assert w[1] > w[0] and w[1] > w[2]
    assert (w[:3] >= 0.2 / 3 - 1e-6).all()  # the floor keeps every active unit rehearsed


@needs
def test_levels_interpolate_from_the_easy_end_and_evaluation_uses_full_families():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    from picklebot_mj.feeds import FAMILIES, FAMILY_NAMES, FeedMix, LP_EASY

    cfg = load_env_cfg("Picklebot-Latent-Drill3-LP-G1")
    b = cfg.actions["ball"]
    assert b.lp_curriculum and not b.adaptive_curriculum and not b.reach_curriculum
    b.move_prob, b.swing_prob, b.feed_mix = 0.0, 0.0, FeedMix({"backhand": 1.0})
    cfg.scene.num_envs = 256
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    L = b.lp_levels
    fam = torch.full((256,), FAMILY_NAMES.index("backhand"), device="cuda")
    for level, want in ((0.0, LP_EASY["backhand"].lateral_y), (1.0, FAMILIES["backhand"].lateral_y)):
        t._lp_s = torch.full((256,), level, device="cuda")
        lo, hi = t._range("lateral_y", fam)
        assert torch.allclose(lo, torch.full_like(lo, want[0])) and torch.allclose(hi, torch.full_like(hi, want[1]))
    assert ((t.feed_unit // L) == FAMILY_NAMES.index("backhand")).all()  # only backhand units are active
    env.close()
    # Evaluation (stage2_eval.py) turns the curriculum off: full ranges, no level state.
    b.lp_curriculum = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    assert t.lp_sampler is None and t._lp_s is None
    lo, hi = t._range("lateral_y", fam)
    assert torch.allclose(lo, torch.full_like(lo, 0.30)) and torch.allclose(hi, torch.full_like(hi, 0.65))
    env.close()
