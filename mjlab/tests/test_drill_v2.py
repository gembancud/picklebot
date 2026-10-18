"""Stage 5E (D-097..D-101): rally drill v2 (feed groups, no two extremes in a row, failure weighting, recovery rule),
the stance-spot planner and the sim-to-real settings of Picklebot-Latent-Court-V2-*-G1."""

from pathlib import Path

import pytest
import torch

from picklebot_mj.drill_v2 import (DRILL_V2_GROUPS, EXTREME_CAP, GROUP_SHARES, DrillV2Sampler, base_weights,
                                   group_index, recovery_spot)
from picklebot_mj.feeds import COURT_ZONE_FAMILIES, FAMILIES, FAMILY_NAMES, VOLLEY_FAMILIES

ROOT = Path(__file__).resolve().parents[1]
LATENT = ROOT / "artifacts" / "train" / "latent" / "latent-07" / "latent_10651.pt"
needs = pytest.mark.skipif(not (torch.cuda.is_available() and LATENT.exists()),
                           reason="needs CUDA and the H1 latent controller")


def test_groups_are_the_d097_mix():
    fams = [f for g in DRILL_V2_GROUPS.values() for f in g]
    assert len(fams) == len(set(fams)) == 17
    assert "lob" not in fams and not set(VOLLEY_FAMILIES) & set(fams)
    assert all("back" in COURT_ZONE_FAMILIES[f] for f in fams)  # court-anchored feeds come from the back zone
    w = base_weights()
    assert abs(sum(w) - 1.0) < 1e-9
    g = group_index()
    for gi, name in enumerate(DRILL_V2_GROUPS):
        assert abs(sum(wi for wi, gg in zip(w, g) if gg == gi) - GROUP_SHARES[name]) < 1e-9


def test_never_two_extremes_in_a_row_and_long_run_shares():
    gen = torch.Generator().manual_seed(0)
    n = 4000
    s = DrillV2Sampler(n, "cpu", gen)
    ids = torch.arange(n)
    prev = torch.zeros(n, dtype=torch.bool)
    counts = torch.zeros(3)
    for i in range(60):
        fam = s.sample(ids)
        ext = s.is_ext[fam]
        assert not (ext & prev).any()
        assert s.in_v2[fam].all()
        prev = ext
        if i >= 10:
            counts += torch.bincount(s.group[fam], minlength=3).float()
    share = counts / counts.sum()
    p_e = 0.15 / 1.15  # stationary extreme share
    expect = torch.tensor([(1 - p_e) * 0.60 + p_e * 0.60 / 0.85, (1 - p_e) * 0.25 + p_e * 0.25 / 0.85, p_e])
    assert (share - expect).abs().max() < 0.01


def test_failure_weighting_caps_the_extreme_share():
    s = DrillV2Sampler(8, "cpu", torch.Generator().manual_seed(1), fail_weighting=True)
    s.fail_ema = torch.where(s.is_ext, torch.ones_like(s.fail_ema), torch.zeros_like(s.fail_ema))
    w = s.weights()
    assert abs(float(w.sum()) - 1.0) < 1e-6
    assert abs(float(w[s.is_ext].sum()) - EXTREME_CAP) < 1e-5
    assert (w[~s.in_v2] == 0).all()
    s2 = DrillV2Sampler(8, "cpu", torch.Generator().manual_seed(1), fail_weighting=False)
    assert torch.equal(s2.weights(), s2.base)


def test_failure_ema_moves_toward_the_failure_rate():
    s = DrillV2Sampler(64, "cpu", torch.Generator().manual_seed(2), fail_weighting=True)
    f = FAMILY_NAMES.index("backspin")
    fam = torch.full((64,), f)
    for _ in range(50):
        s.update(fam, torch.zeros(64, dtype=torch.bool), torch.ones(64, dtype=torch.bool))
    assert float(s.fail_ema[f]) > 0.95
    assert float(s.fail_ema[FAMILY_NAMES.index("deep")]) == 0.5  # untouched


def test_recovery_rule():
    p = torch.tensor([[-6.5, 2.0], [-5.0, -1.0], [-3.0, 4.0], [-4.9, 0.5]])
    r = recovery_spot(p)
    assert torch.allclose(r, torch.tensor([[-5.6, 0.8], [-5.0, -0.4], [-4.5, 1.2], [-4.9, 0.2]]))


def _feed_states(fams, n_each=64, seed=0):
    """Launch states as BallPhysicsAction._feed builds them, court-anchored at ROBOT_START."""
    from picklebot_mj.ball import BALL_RADIUS
    from picklebot_mj.feeds import BOUNCE_AIM_MIN
    from picklebot_mj.tasks.return_stand import FEED_Y_MAX, ROBOT_START
    g = torch.Generator().manual_seed(seed)
    P, V, W, F = [], [], [], []
    for f in fams:
        c = FAMILIES[f]
        u = lambda r: r[0] + (r[1] - r[0]) * torch.rand(n_each, generator=g)
        x0, z0, t = u(c.start_x), u(c.start_z), u(c.flight_time)
        y = (ROBOT_START[1] + u(c.lateral_y)).clamp(-FEED_Y_MAX, FEED_Y_MAX)
        bx = u(c.bounce_x).clamp(min=BOUNCE_AIM_MIN)
        vx, vz = (bx - x0) / t, (BALL_RADIUS - z0 + 0.5 * 9.81 * t * t) / t
        P.append(torch.stack([x0, y, z0], -1))
        V.append(torch.stack([vx, torch.zeros_like(vx), vz], -1))
        W.append(torch.stack([torch.zeros_like(vx), -u(c.spin_y), torch.zeros_like(vx)], -1))
        F += [f] * n_each
    return torch.cat(P), torch.cat(V), torch.cat(W), F


def _true_top(pos, vel, spin):
    """The interception point by the planner's rule, from the full ball simulation (no paddle in reach)."""
    from picklebot_mj.ball_sim import BallParams, BallSim, BallState, PaddleState
    from picklebot_mj.tasks.shadow_swing import HINT_TOP_Z
    n = pos.shape[0]
    sim = BallSim(BallParams())
    s = BallState(pos.clone(), vel.clone(), spin.clone())
    far = PaddleState(torch.tensor([50.0, 50.0, 50.0]).repeat(n, 1), torch.eye(3).repeat(n, 1, 1),
                      torch.zeros(n, 3), torch.zeros(n, 3))
    bounced = torch.zeros(n, dtype=torch.bool)
    found = torch.zeros(n, dtype=torch.bool)
    out = torch.zeros(n, 2)
    for _ in range(500):
        s, ev = sim.step(s, 0.005, 6, far, adaptive=False)
        newb = ev.court_contact & ~bounced
        bounced |= ev.court_contact
        hit = bounced & ~newb & ~found & ((s.vel[:, 2] <= 0) | (s.pos[:, 2] >= HINT_TOP_Z))
        out = torch.where(hit.unsqueeze(-1), s.pos[:, :2], out)
        found |= hit
    return out, found


def test_clean_planner_matches_the_ball_simulation():
    from picklebot_mj.planner import PlannerCfg, predict_top
    fams = [f for g in DRILL_V2_GROUPS.values() for f in g]
    pos, vel, spin, F = _feed_states(fams, 16)
    truth, ok = _true_top(pos, vel, spin)
    pred, found = predict_top(pos, vel, spin, PlannerCfg(know_spin=True))
    assert ok.all() and found.all()
    err = (pred - truth).norm(dim=-1)
    assert float(err.median()) < 0.03 and float(err.max()) < 0.25, (float(err.median()), float(err.max()))


def test_noisy_planner_errs_but_stays_useful():
    from picklebot_mj.planner import PlannerCfg, plan_stance
    fams = [f for g in DRILL_V2_GROUPS.values() for f in g]
    pos, vel, spin, F = _feed_states(fams, 32, seed=3)
    pel = torch.tensor([-5.6, 0.35]).repeat(pos.shape[0], 1)
    clean = plan_stance(pos, vel, spin, pel, clean=True)
    noisy = plan_stance(pos, vel, spin, pel, PlannerCfg(), torch.Generator().manual_seed(4))
    err = (noisy - clean).norm(dim=-1)
    assert 0.05 < float(err.median()) < 0.6, float(err.median())
    # Spin that the planner cannot see costs most on the heavily spun families.
    spun = torch.tensor([f in ("topspin", "backspin") for f in F])
    assert float(err[spun].median()) > float(err[~spun].median())
    # With no noise and the spin known, the noisy path is the clean planner.
    same = plan_stance(pos, vel, spin, pel, PlannerCfg(pos_noise=0.0, vel_noise=0.0, know_spin=True),
                       torch.Generator().manual_seed(5))
    assert torch.allclose(same, clean)


def _env(task="Picklebot-Latent-Court-V2-Res-G1", n=256, **ball):
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg(task)
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob = 0.0, 0.0
    for k, v in ball.items():
        setattr(b, k, v)
    cfg.scene.num_envs = n
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    return env


def test_sim2real_settings_are_on_the_actor_only_and_do_not_leak():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg("Picklebot-Latent-Court-V2-Res-G1")
    for name in ("ball_pos", "ball_vel", "ball_from_paddle"):
        a, c = cfg.observations["actor"].terms[name], cfg.observations["critic"].terms[name]
        assert (a.delay_min_lag, a.delay_max_lag) == (1, 2) and a.params.get("noisy")
        assert c.delay_max_lag == 0 and not (c.params or {}).get("noisy")
    acts = cfg.scene.entities["robot"].articulation.actuators
    assert all(a.delay_min_lag == 0 and a.delay_max_lag == 4 for a in acts)
    b = cfg.actions["ball"]
    assert b.drill_v2 and b.planner_mode == "noisy" and not b.hit_hint and b.feed_anchor == "start"
    old = load_env_cfg("Picklebot-Latent-Court-Res-G1")  # the Stage 5C/5D task keeps its exact, undelayed inputs
    assert all(a.delay_max_lag == 0 for a in old.scene.entities["robot"].articulation.actuators)
    assert old.observations["actor"].terms["ball_pos"].delay_max_lag == 0
    assert not old.actions["ball"].drill_v2


@needs
def test_v2_env_feeds_recovery_and_planner_spot():
    from picklebot_mj.tasks.return_stand import RECOVERY_FIXED
    env = _env()
    t = env.action_manager.get_term("ball")
    assert t.v2 is not None and t.plan_on
    assert t.v2.in_v2[t.family].all()
    fixed = torch.tensor(RECOVERY_FIXED, device=env.device)
    assert torch.allclose(t.v2_rec, fixed.expand_as(t.v2_rec))
    assert torch.allclose(t.recover_xy, fixed.expand_as(t.recover_xy))  # no spot before the observation window
    assert t.plan_pending.all() and not t.hit_hint_on.any()
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    with torch.inference_mode():
        for _ in range(8):  # 0.16 s > planner_delay_s
            env.step(act)
    shown = t.hit_hint_on & ~t.hit_done
    assert float(shown.float().mean()) > 0.9
    assert torch.allclose(t.recover_xy[shown], t.stance_xy[shown])
    assert not t.plan_pending[shown].any()
    env.close()


@needs
def test_noisy_actor_ball_observation_differs_from_the_critic():
    env = _env(n=64)
    obs = env.observation_manager.compute()
    om = env.observation_manager
    def term(group, name):
        start = 0
        for nm, d in zip(om.active_terms[group], om.group_obs_term_dim[group]):
            w = int(torch.tensor(d).prod())
            if nm == name:
                return obs[group][:, start:start + w]
            start += w
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    with torch.inference_mode():
        for _ in range(4):
            env.step(act)
        obs = env.observation_manager.compute()
    a, c = term("actor", "ball_vel"), term("critic", "ball_vel")
    assert float((a - c).abs().mean()) > 0.01  # noise and a 1-2 step lag
    env.close()


def test_episode_latency_task_config():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg("Picklebot-Latent-Court-V2-Res-PPO-EpLat-G1")
    b = cfg.actions["ball"]
    assert b.episode_latency and b.episode_latency_prob == 0.5 and b.drill_v2
    assert b.obs_ball_pos_noise > 0 and b.obs_ball_vel_noise > 0
    for name in ("ball_pos", "ball_vel", "ball_from_paddle"):  # mjlab's delay buffers are off; the ball term delays
        t = cfg.observations["actor"].terms[name]
        assert t.delay_max_lag == 0 and t.params.get("noisy")
    assert all(a.delay_max_lag == 0 for a in cfg.scene.entities["robot"].articulation.actuators)


@needs
def test_episode_latency_clean_and_delayed_episodes():
    env = _env("Picklebot-Latent-Court-V2-Res-PPO-EpLat-G1", n=512)
    t = env.action_manager.get_term("ball")
    lat = env.action_manager.get_term("latent")
    on = t.lat_on
    assert 0.35 < float(on.float().mean()) < 0.65
    assert ((t.obs_lag[on] >= 1) & (t.obs_lag[on] <= 2)).all() and (t.obs_lag[~on] == 0).all()
    assert ((t.cmd_lag[on] >= 0) & (t.cmd_lag[on] <= 4)).all() and (t.cmd_lag[~on] == 0).all()
    om = env.observation_manager

    def term(obs, group, name):
        start = 0
        for nm, d in zip(om.active_terms[group], om.group_obs_term_dim[group]):
            w = int(torch.tensor(d).prod())
            if nm == name:
                return obs[group][:, start:start + w]
            start += w
    g = torch.Generator(device=env.device).manual_seed(0)
    with torch.inference_mode():
        for _ in range(6):
            act = 0.5 * torch.randn(env.num_envs, env.action_manager.total_action_dim, generator=g, device=env.device)
            env.step(act)
        obs = env.observation_manager.compute()
        a, c = term(obs, "actor", "ball_vel"), term(obs, "critic", "ball_vel")
        same = t.lat_on == False  # noqa: E712  (episodes may have reset; read the current draw)
        assert torch.allclose(a[same], c[same], atol=1e-5)  # clean episodes: exact, undelayed ball
        assert float((a[~same] - c[~same]).abs().mean()) > 0.01  # delayed episodes: lagged and noisy
        # Joint commands: each env applies the command cmd_lag physics steps old (the history's row cmd_lag).
        applied = lat._cmd_hist[t.cmd_lag, lat._cmd_ar]
        newest = lat._cmd_hist[0]
        clean = t.cmd_lag == 0
        assert torch.equal(applied[clean], newest[clean])
        late = t.cmd_lag >= 1
        assert late.any() and float((applied[late] - newest[late]).abs().mean()) > 1e-4
    env.close()
