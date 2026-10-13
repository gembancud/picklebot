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


@needs
def test_refeeds_keep_the_curriculum_unit_of_feeds_still_in_flight():
    """Regression (h4-12): _refeed computes a feed for every env and keeps it only where `fire`; the unit of the
    other envs' in-flight feeds must be kept too, or outcomes are credited to random units."""
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg("Picklebot-Latent-Drill3-LP-G1")
    cfg.actions["ball"].move_prob, cfg.actions["ball"].swing_prob = 0.0, 0.0
    cfg.scene.num_envs = 128
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    L = cfg.actions["ball"].lp_levels
    before = t.feed_unit.clone()
    fire = torch.zeros(128, dtype=torch.bool, device="cuda")
    fire[:16] = True
    t._refeed(fire)
    assert torch.equal(t.feed_unit[16:], before[16:])
    assert torch.equal(t.feed_unit // L, t.family)  # every env's unit matches its feed's family
    env.close()


def test_mastered_units_keep_full_weight_when_asked():
    unit = torch.tensor([0] * 300 + [1] * 300 + [2] * 300)
    g = torch.Generator().manual_seed(1)
    succ = torch.cat([torch.zeros(300, dtype=torch.bool), torch.rand(300, generator=g) < 0.5,
                      torch.ones(300, dtype=torch.bool)])
    old, new = LPSampler([1.0, 1.0, 1.0]), LPSampler([1.0, 1.0, 1.0], mastered_weight=1.0)
    for _ in range(80):
        old.update(unit, succ)
        new.update(unit, succ)
    wo, wn = old.weights(), new.weights()
    assert wn[2] > 2 * wo[2]  # the mastered unit is rehearsed far more
    assert wn[0] < wn[2]  # hopeless units stay low


def test_rehearse_mask_limits_full_weight_to_the_listed_units():
    unit = torch.tensor([0] * 300 + [1] * 300)
    succ = torch.ones(600, dtype=torch.bool)  # both units mastered
    s = LPSampler([1.0, 1.0], mastered_weight=1.0, rehearse_mask=[False, True])
    for _ in range(80):
        s.update(unit, succ)
    w = s.weights()
    assert w[1] > 2 * w[0]  # only the listed (top-level) unit is rehearsed at full weight
