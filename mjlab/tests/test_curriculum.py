"""Adaptive curriculum sampler (D-044): moves toward failing units, keeps a floor, respects the support."""

import torch

from picklebot_mj.curriculum import AdaptiveSampler


def _feed(s, unit_rates, rounds=200, n=64, seed=0):
    g = torch.Generator().manual_seed(seed)
    k = len(unit_rates)
    for _ in range(rounds):
        unit = torch.randint(0, k, (n,), generator=g)
        p = torch.tensor(unit_rates)[unit]
        s.update(unit, torch.rand(n, generator=g) < p)


def test_weights_shift_toward_failing_units_with_a_floor():
    s = AdaptiveSampler([1.0, 1.0, 1.0, 1.0])
    _feed(s, [0.99, 0.99, 0.99, 0.6])  # unit 3 is the weak one
    w = s.weights()
    assert abs(float(w.sum()) - 1.0) < 1e-6
    assert w[3] > 2.0 * w[:3].max()  # practise the weak unit most
    assert (w >= 0.25 / 4 - 1e-6).all()  # floor: mastered units are still rehearsed


def test_inactive_units_never_sampled_and_uniform_at_start():
    s = AdaptiveSampler([1.0, 0.0, 1.0])
    w0 = s.weights()
    assert w0[1] == 0 and abs(float(w0[0] - w0[2])) < 1e-6
    _feed(s, [0.5, 0.5, 0.9])
    assert s.weights()[1] == 0


def test_masked_rows_ignored():
    s = AdaptiveSampler([1.0, 1.0])
    unit = torch.tensor([0, 0, 1, 1])
    s.update(unit, torch.tensor([False, False, True, True]), mask=torch.tensor([False, False, True, True]))
    assert float(s.fast[0]) == 0.5 and float(s.fast[1]) > 0.5


import pytest  # noqa: E402


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_task_mix_adapts_and_logs():
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.feeds import FAMILY_NAMES, STAGE4_FAMILIES, FeedMix
    from picklebot_mj.tasks.return_stand import return_stand_env_cfg

    cfg = return_stand_env_cfg(targets=True, start_box=True, recovery=True, free_feet=True, move_prob=0.5)
    cfg.actions["ball"].feed_mix = FeedMix({f: 1.0 for f in STAGE4_FAMILIES})
    cfg.actions["ball"].adaptive_curriculum = True
    cfg.scene.num_envs = 64
    cfg.actions["ball"].compile_ball = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    assert t.fam_sampler is not None and t.drill.sampler is not None
    bs = FAMILY_NAMES.index("backspin")
    # Pretend every finished feed except backspin succeeds: backspin's share must grow.
    n = 512
    fam = torch.arange(n, device="cuda") % len(STAGE4_FAMILIES)
    fam = torch.tensor([FAMILY_NAMES.index(STAGE4_FAMILIES[int(i)]) for i in fam], device="cuda")
    for _ in range(20):
        t.fam_sampler.update(fam, fam != bs)
    w = t.fam_sampler.weights()
    assert w[bs] > 2.0 * w[[FAMILY_NAMES.index(f) for f in STAGE4_FAMILIES if f != "backspin"]].max()
    assert all(w[i] == 0 for i, f in enumerate(FAMILY_NAMES) if f not in STAGE4_FAMILIES)
    env.step(torch.zeros(64, 29, device="cuda"))  # runs the term with the sampler active
