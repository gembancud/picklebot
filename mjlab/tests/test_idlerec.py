"""D-177 idle recovery: pair_idle_recovery extends spot_progress's active mask to envs with no ball of their own in play
(pairs.parked). CPU: the task differs from the ballidx task only in the flag; spot_progress on a fake term. GPU: a real
pair-mode env during a feeder ball."""

from types import SimpleNamespace

import pytest
import torch


def _fake_env(flag, parked, hit_done, hint=None):
    n = len(parked)
    t = SimpleNamespace(
        cfg=SimpleNamespace(pair_idle_recovery=flag) if flag is not None else SimpleNamespace(),
        recover_xy=torch.zeros(n, 2), hit_done=torch.tensor(hit_done), drill=None, shadow=None,
        hit_hint_on=torch.tensor(hint or [False] * n), pairs=SimpleNamespace(parked=torch.tensor(parked)))
    pel = torch.tensor([[1.0, 0.0]] * n)
    t.pelvis_xy = lambda env_ids=None: pel
    t._entity = SimpleNamespace(data=SimpleNamespace(root_link_lin_vel_w=torch.tensor([[-0.5, 0.0, 0.0]] * n)))
    return SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: t))


def test_spot_progress_idle_mask_only_behind_the_flag():
    from picklebot_mj.tasks.return_stand import spot_progress
    parked, hit = [True, True, False, False], [False, True, False, True]
    on = spot_progress(_fake_env(True, parked, hit))
    off = spot_progress(_fake_env(False, parked, hit))
    absent = spot_progress(_fake_env(None, parked, hit))  # cfg without the field (every existing task)
    assert on.tolist() == [0.5, 0.5, 0.0, 0.5]  # parked envs paid; a live ball before the hit is not
    assert off.tolist() == [0.0, 0.5, 0.0, 0.5] and absent.tolist() == off.tolist()
    e = _fake_env(True, parked, hit)
    e.action_manager.get_term("ball").pairs = None  # not pair mode: the flag does nothing
    assert spot_progress(e).tolist() == off.tolist()


def test_idlerec_task_differs_from_the_ballidx_task_only_in_the_flag():
    import dataclasses

    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls

    import picklebot_mj.tasks.agility as ag
    for play in (False, True):
        a, s = load_env_cfg(ag.TASK_AGILITY_BALLIDX, play=play), load_env_cfg(ag.TASK_AGILITY_BALLIDX_IDLEREC, play=play)
        ab, sb = a.actions["ball"], s.actions["ball"]
        assert [f.name for f in dataclasses.fields(ab) if getattr(ab, f.name) != getattr(sb, f.name)] == ["pair_idle_recovery"]
        assert sb.pair_idle_recovery and sb.ball_index_tally and not sb.ball_index_split and not ab.pair_idle_recovery
        assert [k for k in a.actions if k != "ball" and a.actions[k] != s.actions[k]] == []
        for g in a.observations:
            assert list(a.observations[g].terms) == list(s.observations[g].terms)
        assert [k for k in a.rewards if a.rewards[k].func is not s.rewards[k].func or a.rewards[k].weight != s.rewards[k].weight
                or a.rewards[k].params != s.rewards[k].params] == [] and list(a.rewards) == list(s.rewards)
        assert s.rewards["spot_progress"].weight == 1.0 and a.episode_length_s == s.episode_length_s
    assert load_runner_cls(ag.TASK_AGILITY_BALLIDX_IDLEREC) is load_runner_cls(ag.SRC_22B)
    assert load_rl_cfg(ag.TASK_AGILITY_BALLIDX_IDLEREC) == load_rl_cfg(ag.SRC_22B)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs the GPU simulator")
def test_idle_env_is_paid_toward_recover_xy_during_the_partners_feeder_ball():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    import picklebot_mj.tasks.agility as ag
    from picklebot_mj.tasks.return_stand import spot_progress
    cfg = load_env_cfg(ag.TASK_AGILITY_BALLIDX_IDLEREC)
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob, b.refeed_delay_s, b.court_feed_prob = 0.0, 0.0, 0.5, 1.0
    cfg.scene.num_envs = 16
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    pc = t.pairs
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    idle = None
    for _ in range(200):
        env.step(act)
        live = ~pc.parked & ~pc.handed  # a feeder ball in play
        cand = pc.parked & live[pc.partner] & ~pc.court_dead.repeat(2)
        if bool(cand.any()):
            idle = cand.clone()
            break
    assert idle is not None, "no feeder ball started"
    # the reward's mask on this real state, with a pelvis 0.67 m off recover_xy moving toward it at 0.5 m/s
    pel = t.recover_xy + torch.tensor([0.6, 0.3], device=env.device)
    to = t.recover_xy - pel
    v = torch.zeros(env.num_envs, 3, device=env.device)
    v[:, :2] = 0.5 * to / to.norm(dim=-1, keepdim=True)
    ent, pfn = t._entity, t.pelvis_xy
    try:
        t._entity = SimpleNamespace(data=SimpleNamespace(root_link_lin_vel_w=v))
        t.pelvis_xy = lambda env_ids=None: pel
        t.cfg.pair_idle_recovery = True
        on = spot_progress(env).clone()
        t.cfg.pair_idle_recovery = False
        off = spot_progress(env).clone()
    finally:
        t._entity, t.pelvis_xy, t.cfg.pair_idle_recovery = ent, pfn, True
    hd = t.hit_done.clone()
    env.close()
    assert torch.allclose(on[idle], torch.full_like(on[idle], 0.5), atol=1e-5)  # every idle env paid with the flag
    assert (off[idle & ~hd] == 0).all()  # without it only those still flagged hit_done from their last ball
    assert torch.allclose(off[idle & hd], torch.full_like(off[idle & hd], 0.5), atol=1e-5)
    assert bool((idle & ~hd).any())  # at rally start (after the reset) no idle env carries hit_done: the contrast
