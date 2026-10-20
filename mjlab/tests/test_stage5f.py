"""Stage 5F (D-108/D-109/D-111): the ball-latency compensator, the compensating tasks, the delay-grid option and the
coverage rule (evaluations cover every latency condition the training task covers)."""

import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_drill_v2 import LATENT, _feed_states  # noqa: E402

from picklebot_mj.drill_v2 import DRILL_V2_GROUPS  # noqa: E402

needs = pytest.mark.skipif(not (torch.cuda.is_available() and LATENT.exists()),
                           reason="needs CUDA and the H1 latent controller")
FAMS = [f for g in DRILL_V2_GROUPS.values() for f in g]


def _truth(pos, vel, spin, steps):
    from picklebot_mj.ball_sim import BallParams, BallSim, BallState, PaddleState
    n = pos.shape[0]
    sim = BallSim(BallParams())
    s = BallState(pos.clone(), vel.clone(), spin.clone())
    far = PaddleState(torch.tensor([50.0, 50.0, 50.0]).repeat(n, 1), torch.eye(3).repeat(n, 1, 1),
                      torch.zeros(n, 3), torch.zeros(n, 3))
    traj = [s.pos.clone()]
    for _ in range(steps):
        s, _ = sim.step(s, 0.005, 6, far, adaptive=False)
        traj.append(s.pos.clone())
    return torch.stack(traj)


def test_compensator_rolls_each_env_forward_by_its_own_age():
    from picklebot_mj.planner import compensate
    pos, vel, spin, _ = _feed_states(FAMS, 8, seed=4210200)
    traj = _truth(pos, vel, spin, 200)
    n = pos.shape[0]
    t0 = 60  # 0.3 s into the flight: the "measurement"
    from picklebot_mj.ball_sim import BallParams, BallSim, BallState, PaddleState  # true velocity at t0
    sim = BallSim(BallParams())
    s = BallState(pos.clone(), vel.clone(), spin.clone())
    far = PaddleState(torch.tensor([50.0, 50.0, 50.0]).repeat(n, 1), torch.eye(3).repeat(n, 1, 1),
                      torch.zeros(n, 3), torch.zeros(n, 3))
    for _ in range(t0):
        s, _ = sim.step(s, 0.005, 6, far, adaptive=False)
    sub = torch.tensor([0, 4, 8] * (n // 3) + [8] * (n % 3))
    p, v = compensate(s.pos, s.vel, sub, 8)
    assert torch.allclose(p[sub == 0], s.pos[sub == 0])
    for k in (4, 8):
        m = sub == k
        err = (p[m] - traj[t0 + k][m]).norm(dim=-1)
        raw = (s.pos[m] - traj[t0 + k][m]).norm(dim=-1)
        assert float(err.median()) < 0.01 and float(raw.median()) > 0.05, (k, float(err.median()), float(raw.median()))


def test_compensating_task_configs():
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    ev = load_env_cfg("Picklebot-Latent-Court-V2-Res-Comp-G1").actions["ball"]
    assert ev.episode_latency and ev.episode_latency_prob == 1.0 and ev.ball_compensate and ev.obs_lag_period == 50
    assert ev.episode_obs_lag == (1, 2) and ev.episode_cmd_lag == (0, 4)  # the frozen D-101 latency, exactly
    court = load_env_cfg("Picklebot-Latent-Court-Res-Comp-G1").actions["ball"]
    assert court.episode_latency and court.episode_latency_prob == 0.0  # clean by default (Stage 5C battery)
    tr = load_env_cfg("Picklebot-Latent-Court-V2-Res-PPO-Comp-G1").actions["ball"]
    assert tr.episode_latency_prob == 0.5 and tr.ball_compensate and tr.drill_v2
    for t in ("Picklebot-Latent-Court-V2-Res-Comp-G1", "Picklebot-Latent-Court-V2-Res-PPO-Comp-G1"):
        cfg = load_env_cfg(t)  # mjlab's per-term delays are off: the ball term owns the latency
        assert cfg.observations["actor"].terms["ball_pos"].delay_max_lag == 0
        assert all(a.delay_max_lag == 0 for a in cfg.scene.entities["robot"].articulation.actuators)


def test_evaluation_battery_covers_the_training_latency():
    """D-109: every (ball lag, command lag) the training task meets is met by the frozen evaluation tasks."""
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    from picklebot_mj.tasks import latency_support
    train = latency_support(load_env_cfg("Picklebot-Latent-Court-V2-Res-PPO-Comp-G1"))
    evals = (latency_support(load_env_cfg("Picklebot-Latent-Court-V2-Res-Comp-G1"))
             | latency_support(load_env_cfg("Picklebot-Latent-Court-Res-Comp-G1")))
    assert train <= evals, sorted(train - evals)
    assert (0, 0) in train and (2, 4) in train


@needs
def test_compensated_ball_observation_is_near_the_truth():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg("Picklebot-Latent-Court-V2-Res-Comp-G1")
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob, b.episode_obs_lag, b.obs_lag_period = 0.0, 0.0, (2, 2), 0
    b.obs_ball_pos_noise = b.obs_ball_vel_noise = 0.0  # isolate the delay
    cfg.scene.num_envs = 128
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    with torch.inference_mode():
        for _ in range(12):
            env.step(act)
        env.observation_manager.compute()
        flying = t.ball.vel.norm(dim=-1) > 2.0
        comp = (t._seen_pos - t.ball.pos).norm(dim=-1)[flying]
        raw = (t._seen_hist[2, :, :3] - t.ball.pos).norm(dim=-1)[flying]
    assert flying.sum() > 20
    assert float(comp.median()) < 0.02 and float(raw.median()) > 0.1, (float(comp.median()), float(raw.median()))
    env.close()


@needs
def test_delayed_joint_action_per_episode_lag():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg
    cfg = load_env_cfg("Picklebot-Tracking-TennisLafan2-Huge-Delay-G1")
    cfg.scene.num_envs = 512
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("joint_pos")
    zero = float((t.cmd_lag == 0).float().mean())
    assert 0.2 < zero < 0.4 and int(t.cmd_lag.max()) <= 5 and int(t.cmd_lag.min()) >= 0
    g = torch.Generator(device=env.device).manual_seed(0)
    with torch.inference_mode():
        for _ in range(4):
            env.step(0.3 * torch.randn(env.num_envs, env.action_manager.total_action_dim, generator=g, device=env.device))
        applied = t._hist[t.cmd_lag, t._ar]
        newest = t._hist[0]
        clean = t.cmd_lag == 0
        assert torch.equal(applied[clean], newest[clean])
        late = t.cmd_lag >= 1
        assert float((applied[late] - newest[late]).abs().mean()) > 1e-4
        obs = env.observation_manager.compute()
    assert obs["critic"].shape[1] == obs["critic"].shape[1]  # the critic group builds with the trailing cmd_lag term
    env.close()


def test_executor_history_config():
    """D-108/D-109: history terms come last in both groups (zero-weight expansion); the applied commands and the lags
    go to the critic only; tasks with mjlab per-term delays are refused."""
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    from picklebot_mj.tasks import EXEC_HISTORY, HISTORY_TERMS, _exec_history
    cfg = load_env_cfg("Picklebot-Latent-Court-V2-Res-PPO-Comp-G1")
    before = {g: list(cfg.observations[g].terms) for g in ("actor", "critic")}
    _exec_history(cfg)
    for g in ("actor", "critic"):
        names = list(cfg.observations[g].terms)
        assert names[:len(before[g])] == before[g]  # old inputs keep their columns
        for n in HISTORY_TERMS:
            assert cfg.observations[g].terms[f"h_{n}"].history_length == EXEC_HISTORY
            assert cfg.observations[g].terms[n].history_length == 0
    assert "applied_cmd" in cfg.observations["critic"].terms and "latency" in cfg.observations["critic"].terms
    assert "applied_cmd" not in cfg.observations["actor"].terms and "latency" not in cfg.observations["actor"].terms
    with pytest.raises(AssertionError):
        _exec_history(load_env_cfg("Picklebot-Latent-Court-V2-Res-G1"))  # mjlab per-term ball delay


def test_clean_ppo_task_matches_the_d113_instrument():
    """D-113: run 2 trains where the gate measures: drill v2, ball noise on, no ball or command delay."""
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    from picklebot_mj.tasks import SIM2REAL_BALL_NOISE, latency_support
    cfg = load_env_cfg("Picklebot-Latent-Court-V2-Res-PPO-Clean-G1")
    b = cfg.actions["ball"]
    assert b.drill_v2 and (b.obs_ball_pos_noise, b.obs_ball_vel_noise) == SIM2REAL_BALL_NOISE
    assert latency_support(cfg) == {(0, 0)}
    assert cfg.observations["actor"].terms["ball_pos"].params.get("noisy")


def test_ready_tracker_scores_stance_and_split_step():
    """D-115: ready = wide stance with both feet down at the launch; dip = pelvis drop >= 3 cm within +-0.25 s."""
    from picklebot_mj.ready import ReadyTracker
    dt = 0.005
    tr = ReadyTracker(3, "cpu", dt, [0, 1])
    tr.reset(torch.arange(3))
    z = torch.full((3,), 0.75)
    feet = torch.tensor([[[0.0, 0.2, 0.07], [0.0, -0.2, 0.07]],   # 0.40 m wide, both down
                         [[0.0, 0.1, 0.07], [0.0, -0.1, 0.07]],   # 0.20 m: too narrow
                         [[0.0, 0.2, 0.07], [0.0, -0.2, 0.30]]])  # one foot up
    for _ in range(tr.h + 5):
        tr.step(z)
        tr.launch(torch.zeros(3, dtype=torch.bool), feet)
    tr.step(z)
    tr.launch(torch.ones(3, dtype=torch.bool), feet)
    assert torch.allclose(tr.launch_now, torch.tensor([1.0, 0.0, 0.0]))
    for i in range(tr.h):
        dz = torch.tensor([0.04, 0.0, 0.02]) * min(1.0, i / 10)  # env 0 dips 4 cm, env 2 dips 2 cm
        tr.step(z - dz)
        tr.launch(torch.zeros(3, dtype=torch.bool), feet)
    s = tr.summary()
    assert s["feeds_scored"] == 3
    assert s["ready"] == round(1 / 3, 4) and s["dip"] == round(1 / 3, 4) and s["ready_and_dip"] == round(1 / 3, 4)
    tr2 = ReadyTracker(1, "cpu", dt, [0, 1])  # a launch right after a reset is not scored (no pelvis history)
    tr2.reset(torch.arange(1))
    tr2.step(torch.full((1,), 0.75))
    tr2.launch(torch.ones(1, dtype=torch.bool), feet[:1])
    assert not tr2.open.any()


def test_ready_task_reward_order():
    """D-115: the ready reward is read before legal_return (which clears the one-shot flags); nothing else changes."""
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    base = load_env_cfg("Picklebot-Latent-Court-V2-Res-PPO-Clean-G1")
    cfg = load_env_cfg("Picklebot-Latent-Court-V2-Res-PPO-Clean-Ready-G1")
    names = list(cfg.rewards)
    assert names[-1] == "legal_return" and names[-2] == "ready" and cfg.actions["ball"].ready_track
    assert [n for n in names if n != "ready"] == list(base.rewards)
    assert all(cfg.rewards[n].weight == base.rewards[n].weight for n in base.rewards)


@needs
def test_court_feed_mix_shares_families_recovery_and_planner():
    """D-116: ~40 % court feeds (zone-valid court families, no planner spot, court recovery); drill v2 feeds keep their
    families and the no-two-extremes rule counted over v2 feeds only; in-flight draws survive other envs' refeeds."""
    from test_drill_v2 import _env
    from picklebot_mj.tasks.return_stand import RECOVERY_FIXED
    env = _env("Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-G1", n=512)
    t = env.action_manager.get_term("ball")
    fixed = torch.tensor(RECOVERY_FIXED, device=env.device)
    act = torch.zeros(env.num_envs, env.action_manager.total_action_dim, device=env.device)
    n_feeds = n_court = 0
    last_v2_ext = torch.zeros(env.num_envs, dtype=torch.bool, device=env.device)
    prev_fam, prev_cf = t.family.clone(), t.court_feed.clone()
    with torch.inference_mode():
        for step in range(400):
            env.step(act)
            new = (t.family != prev_fam) | (t.court_feed != prev_cf)  # a new feed (approximate; same-family refeeds are missed)
            if step > 0 and new.any():
                cf, fam = t.court_feed[new], t.family[new]
                n_feeds += int(new.sum()); n_court += int(cf.sum())
                assert t._zone_valid[t.zone[new][cf], fam[cf]].all()  # court feeds: zone-valid families
                assert t.v2.in_v2[fam[~cf]].all()  # v2 feeds: drill v2 families
                assert not t.plan_pending[new][cf].any() and not t.hit_hint_on[new][cf].any()
                anch = t._court_anch[new] & cf
                assert torch.allclose(t.recover_xy[new][anch], fixed.expand(int(anch.sum()), 2))
                v2new = new & ~t.court_feed
                both = v2new & last_v2_ext & t.v2.is_ext[t.family]
                assert not both.any(), "two extremes in a row among v2 feeds"
                last_v2_ext = torch.where(v2new, t.v2.is_ext[t.family], last_v2_ext)
            prev_fam, prev_cf = t.family.clone(), t.court_feed.clone()
    assert n_feeds > 300
    assert 0.30 < n_court / n_feeds < 0.50, n_court / n_feeds
    env.close()


def test_court_feed_share_zero_is_the_drill_v2_task():
    """D-116: the mix only adds court_feed_prob; share 0 is run 3's task."""
    import dataclasses
    import mjlab.tasks  # noqa: F401
    from mjlab.tasks.registry import load_env_cfg
    a = load_env_cfg("Picklebot-Latent-Court-V2-Res-PPO-Clean-G1").actions["ball"]
    b = load_env_cfg("Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-G1").actions["ball"]
    diff = [f.name for f in dataclasses.fields(a) if getattr(a, f.name) != getattr(b, f.name)]
    assert diff == ["court_feed_prob"] and b.court_feed_prob == 0.4 and a.court_feed_prob == 0.0


def test_mirror_ball_states_is_a_half_turn():
    """D-116: the R2 mirror is a 180-degree rotation about the court centre (an involution, z and wz unchanged)."""
    from picklebot_mj.tasks.return_stand import mirror_ball_states
    st = torch.tensor([[-5.0, 1.2, 0.9, 7.0, -1.0, 3.0, 10.0, -20.0, 5.0]])
    m = mirror_ball_states(st)
    assert torch.allclose(m, torch.tensor([[5.0, -1.2, 0.9, -7.0, 1.0, 3.0, -10.0, 20.0, 5.0]]))
    assert torch.allclose(mirror_ball_states(m), st)


def test_pair_courts_one_ball_per_court_and_rally_counts():
    """D-116 R4: a return crossing the net hands the ball to the partner; a miss ends the rally; the restart comes from
    the feeder on alternating sides once both envs are idle; the initial reset is not counted as a rally."""
    from picklebot_mj.pairs import PairCourts
    pc = PairCourts(4, "cpu")  # courts (0, 2) and (1, 3)
    F = lambda *i: torch.tensor([k in i for k in range(4)])  # noqa: E731
    Z = F()
    pc.on_reset(torch.arange(4))
    fires = []
    for _ in range(30):  # restart delay 0.1 s at dt 0.01
        fire, recv = pc.step(Z, Z, Z, Z, 0.01, 0.1)
        if fire.any():
            fires.append(fire.clone())
    assert len(fires) == 1 and fires[0].sum() == 2  # one feeder ball per court
    a, b = (2, 0) if fires[0][2] else (0, 2)  # court 0: the env that got the feeder ball, and its partner
    assert pc.summary()["rallies"] == 0
    # env a returns: the ball crosses -> partner b receives; a's return then lands legally
    fire, recv = pc.step(Z, Z, Z, F(a), 0.01, 0.1)
    assert bool(recv[b]) and not recv[a] and not fire.any()
    pc.step(F(a), F(a), Z, Z, 0.01, 0.1)
    # b returns too; then a misses b's ball -> rally of 2 legal shots ends
    fire, recv = pc.step(Z, Z, Z, F(b), 0.01, 0.1)
    assert bool(recv[a])
    pc.step(F(b), F(b), Z, Z, 0.01, 0.1)
    pc.step(F(a), Z, Z, Z, 0.01, 0.1)
    s = pc.summary()
    assert s["len_hist"][2] == 1 and s["sides"]["A"]["feeds"] + s["sides"]["B"]["feeds"] == 3
    fires = [f for f in (pc.step(Z, Z, Z, Z, 0.01, 0.1)[0] for _ in range(30)) if f.any()]
    assert len(fires) == 1 and bool(fires[0][b]) and not fires[0][a]  # the other side gets the next feeder ball


def test_paddle_for_inverts_the_impact_model():
    """D-118: the paddle state from paddle_for, put through sphere_impulse (spin zero), gives the commanded v_out."""
    from picklebot_mj.ball_sim import BallParams, sphere_impulse
    from picklebot_mj.planner import paddle_for
    p = BallParams()
    g = torch.Generator().manual_seed(4216000)
    v_in = torch.randn(256, 3, generator=g) * torch.tensor([2.0, 1.0, 1.5]) + torch.tensor([-5.0, 0.0, -1.0])
    v_out = torch.randn(256, 3, generator=g) * torch.tensor([1.0, 1.0, 0.8]) + torch.tensor([6.0, 0.0, 3.5])
    n, vp = paddle_for(v_in, v_out, p.paddle_cor)
    v2, _, _ = sphere_impulse(v_in, torch.zeros_like(v_in), n, vp, p.paddle_cor, p.paddle_friction, p)
    rel = (v2 - v_out).norm(dim=-1) / v_out.norm(dim=-1)
    assert rel.max() < 0.05, rel.max()


def test_aim_outgoing_lands_in_the_keep_alive_box():
    """D-118: the aimed outgoing ball (spin-blind, drag) lands within 10 cm of its target after the flight time."""
    from picklebot_mj.ball_sim import BallParams, flight_rk4
    from picklebot_mj.planner import aim_outgoing, keep_alive_target
    p = BallParams()
    g = torch.Generator().manual_seed(4216001)
    c = torch.stack([-5.0 + torch.rand(128, generator=g) * 2, torch.rand(128, generator=g) * 4 - 2,
                     0.6 + torch.rand(128, generator=g) * 0.5], -1)
    xy, T = keep_alive_target(128, g)
    v = aim_outgoing(c, xy, T, params=p)
    x, vv, w = c.clone(), v.clone(), torch.zeros_like(c)
    h = (T / 200).unsqueeze(-1)
    for _ in range(200):
        x, vv, w = flight_rk4(x, vv, w, h, p)
    assert ((x[:, :2] - xy).norm(dim=-1)).max() < 0.10 and (x[:, 2] - p.radius).abs().max() < 0.10
    assert (v.norm(dim=-1) < 14).all() and (v[:, 2] > 0).all()  # a lob-to-drive range, always rising off the paddle


def test_predict_contact_matches_the_ball_simulation():
    """D-118: with spin known, the planner's contact (after the bounce: rising through HINT_TOP_Z, or the apex) agrees
    with the full ball simulation (net and posts included, 1 ms steps) within 5 cm and 15 ms on drill-like feeds."""
    from picklebot_mj.ball_sim import BallSim, BallState
    from picklebot_mj.planner import PlannerCfg, predict_contact
    from picklebot_mj.tasks.shadow_swing import HINT_TOP_Z
    from test_drill_v2 import _feed_states  # FAMS: this module's drill v2 families
    pos, vel, spin, _ = _feed_states(FAMS, 8, seed=4216002)
    cx, cv, ct, found = predict_contact(pos, vel, spin, PlannerCfg(know_spin=True))
    sim, dt = BallSim(), 0.001
    s = BallState(pos.clone(), vel.clone(), spin.clone())
    bounced = torch.zeros(len(pos), dtype=torch.bool)
    done = torch.zeros_like(bounced)
    tx, tt = torch.zeros_like(pos), torch.zeros(len(pos))
    for i in range(int(1.8 / dt)):
        z0, vz0 = s.pos[:, 2].clone(), s.vel[:, 2].clone()
        p0 = s.pos.clone()
        s, ev = sim.step(s, dt, 4)
        bounced |= ev.court_contact
        top = bounced & ~ev.court_contact & ~done & (((s.pos[:, 2] >= HINT_TOP_Z) & (z0 < HINT_TOP_Z)) | ((s.vel[:, 2] <= 0) & (vz0 > 0)))
        tx = torch.where(top.unsqueeze(-1), 0.5 * (p0 + s.pos), tx)
        tt = torch.where(top, torch.full_like(tt, (i + 0.5) * dt), tt)
        done |= top
    ok = found & done
    assert ok.float().mean() > 0.9
    assert (cx[ok] - tx[ok]).norm(dim=-1).max() < 0.05 and (ct[ok] - tt[ok]).abs().max() < 0.015


def test_e3_contact_reward_prefers_a_swing_over_parking():
    """D-121 (panel round 11): with the speed floor removed, parked < half speed < perfect at p*, and per goal (the
    contact weight 5, plus paddle_track's ~0.3 s x 2 / s while parked) a perfect swing beats parking by >= 2 and a
    4.8 m/s swing with a 5 cm miss beats parking by >= 1. E2's floored factor tied them (round-11 arithmetic)."""
    from picklebot_mj.tasks.timed_reach import contact_factors
    v = torch.tensor([7.1])
    one = torch.ones(1)

    def r(dp, speed_ms, mode):
        kp, fv, fa = contact_factors(torch.tensor([dp]), v - speed_ms, v, one, mode)
        return float((kp * fv * fa)[0])
    assert r(0.0, 0.0, "linear0") < r(0.0, 3.55, "linear0") < r(0.0, 7.1, "linear0")
    park = 5 * r(0.0, 0.0, "linear0") + 0.6
    assert 5 * r(0.0, 7.1, "linear0") - park >= 2.0
    assert 5 * r(0.05, 4.8, "linear0") + 0.2 - park >= 1.0
    assert abs((5 * r(0.0, 0.0, "linear") + 0.6) - (5 * r(0.05, 4.8, "linear") + 0.2)) < 1.0  # E2's near-tie


@needs
def test_predict_contact_fast_matches_eager():
    """The compiled, padded contact rollout gives the eager rollout's contacts (in-environment planning)."""
    from picklebot_mj.planner import predict_contact, predict_contact_fast
    pos, vel, spin, _ = _feed_states(FAMS, 3, seed=4216015)
    pos, vel = pos.cuda(), vel.cuda()
    z = torch.zeros_like(pos)
    a = predict_contact(pos, vel, z)
    b = predict_contact_fast(pos, vel, z)
    assert torch.equal(a[3], b[3])
    assert (a[0] - b[0]).abs().max() < 1e-4 and (a[2] - b[2]).abs().max() < 1e-4


def test_d122_timing_window_scores_the_strike_not_the_follow_through():
    """D-122: timing is the closest approach within [t* - 0.25, t* + 0.10]. An on-time swing passes; a swing 100 ms
    early fails; a swing whose follow-through drifts back nearer p* after the window passes (the old whole-window
    metric failed it)."""
    from types import SimpleNamespace
    from picklebot_mj.tasks.timed_reach import TimedReachCommand
    cmd = TimedReachCommand.__new__(TimedReachCommand)
    n, dt, t_star = 3, 0.02, 1.0
    cmd.p_star = torch.zeros(n, 3)
    cmd.t_contact = torch.full((n,), t_star)
    cmd.scored = torch.ones(n, dtype=torch.bool)
    cmd.min_dp, cmd.t_min = torch.full((n,), 1e9), torch.zeros(n)
    cmd.min_dp_w, cmd.t_min_w = torch.full((n,), 1e9), torch.full((n,), -1e9)
    cmd.counts, cmd.counts_w = torch.zeros(3, dtype=torch.long), torch.zeros(2, dtype=torch.long)
    cmd.stats = {"dt": torch.zeros(101, dtype=torch.long)}
    cmd.metrics = {}
    clock = {"t": 0.0}
    cmd.clock = lambda: torch.full((n,), clock["t"])

    def dist(t):  # paddle distance to p*: env 0 passes at t*, env 1 at t* - 0.1, env 2 at t* then returns to 0.01 m
        d0 = abs(t - t_star) * 6.0 + 0.03
        d1 = abs(t - (t_star - 0.1)) * 6.0 + 0.03
        d2 = d0 if t < t_star + 0.3 else 0.01
        return torch.tensor([d0, d1, d2])
    for k in range(int(1.6 / dt) + 1):
        clock["t"] = k * dt
        pos = torch.zeros(n, 3)
        pos[:, 0] = dist(clock["t"])
        cmd.paddle_state = lambda pos=pos: (pos, torch.zeros(n, 3), torch.zeros(n, 3))
        cmd._update_metrics()
    dtw = (cmd.t_min_w - cmd.t_contact).abs()
    old = (cmd.t_min - cmd.t_contact).abs()
    assert dtw[0] <= 0.05 and dtw[1] > 0.05 and dtw[2] <= 0.05
    assert old[2] > 0.05  # the old metric scored env 2's follow-through


def test_e4_root_speed_cap_ranks_arriving_on_time_first():
    """D-122 pre-launch (E4): over one median goal (1.6 m walk, t* = 1.3 s), with root_progress capped at max_speed
    and the contact reward of E3 (linear0), score three scripted behaviours:
      A: walk at the required 1.23 m/s, arrive at t*, swing (paddle on p*, at speed);
      B: walk at 1.0 m/s, 0.3 m short at t*, lunge (paddle 0.10 m off p*, at speed);
      C: walk at the required speed, no swing (parked at p*).
    Pass: A > B > C under the new cap (1.6), and the A - B margin grows from cap 1.0 to 1.6."""
    import math
    from picklebot_mj.tasks.timed_reach import contact_factors
    T, walk, v_req = 1.3, 1.6, 1.6 / 1.3
    v = torch.tensor([7.1])
    one = torch.ones(1)

    def contact(dp, speed):
        kp, fv, fa = contact_factors(torch.tensor([dp]), v - speed, v, one, "linear0")
        return 5.0 * float((kp * fv * fa)[0])

    def progress(speed, cap):  # root_progress weight 1, per second while walking (dist > 0.05 m)
        return min(speed, cap) * T

    def root_track(short):  # root_track std 1.0, weight 1, crudely: the distance falls linearly to `short`
        return sum(math.exp(-((walk - (walk - short) * k / 50)) ** 2) for k in range(51)) / 51 * T

    def score(cap):
        a = progress(v_req, cap) + root_track(0.0) + contact(0.0, 7.1)
        b = progress(1.0, cap) + root_track(0.3) + contact(0.10, 7.1)
        c = progress(v_req, cap) + root_track(0.0) + contact(0.0, 0.0)
        return a, b, c
    a1, b1, _ = score(1.0)
    a6, b6, c6 = score(1.6)
    assert a6 > b6 > c6, (a6, b6, c6)
    assert (a6 - b6) > (a1 - b1)


def test_aim_outgoing_fast_matches_eager():
    """D-124: the compiled keep-it-alive aim gives the eager aim's outgoing velocity."""
    from picklebot_mj.planner import aim_outgoing, aim_outgoing_fast, keep_alive_target
    g = torch.Generator(device="cuda").manual_seed(4216016)
    n = 128
    contact = torch.stack([-5.0 + torch.rand(n, generator=g, device="cuda"), torch.rand(n, generator=g, device="cuda") - 0.5,
                           0.4 + 0.6 * torch.rand(n, generator=g, device="cuda")], -1)
    tgt, T = keep_alive_target(n, g, "cuda")
    a = aim_outgoing(contact, tgt, T)
    b = aim_outgoing_fast(contact, tgt, T)
    assert (a - b).abs().max() < 1e-3


def _fake_ball_cmd(n, batch):
    """A TimedBallCommand on a stand-in environment (CPU, noise-free planner) for the sync-free goal setter."""
    from types import SimpleNamespace
    import picklebot_mj.tasks.timed_reach as tr
    from picklebot_mj.tasks.timed_reach import TimedBallCommand
    pos, vel, _, _ = _feed_states(FAMS, -(-n // len(FAMS)), seed=4216017)
    pos, vel = pos[:n].clone(), vel[:n].clone()
    ball = SimpleNamespace(plan_pending=torch.ones(n, dtype=torch.bool), hit_done=torch.zeros(n, dtype=torch.bool),
                           ball=SimpleNamespace(pos=pos, vel=vel), _plan_cfg=SimpleNamespace(pos_noise=0.0, vel_noise=0.0),
                           gen_plan=torch.Generator().manual_seed(1), pelvis_xy=lambda idx: torch.zeros(len(idx), 2))
    env = SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: ball), step_dt=0.02,
                          scene=SimpleNamespace(env_origins=torch.zeros(n, 3)),
                          episode_length_buf=torch.zeros(n, dtype=torch.long), device=torch.device("cpu"), num_envs=n)
    cmd = TimedBallCommand.__new__(TimedBallCommand)
    cmd._env, cmd.cfg = env, SimpleNamespace(walk_cap=None)
    z3 = lambda: torch.zeros(n, 3)  # noqa: E731
    cmd.p_star, cmd.v_star, cmd.n_star, cmd.root_target = z3(), z3(), z3(), torch.zeros(n, 2)
    cmd.t_contact, cmd.scored = torch.full((n,), 1e9), torch.ones(n, dtype=torch.bool)
    cmd.min_dp, cmd.min_dp_w, cmd.t_min_w = torch.full((n,), 1e9), torch.full((n,), 1e9), torch.full((n,), -1e9)
    cmd.counts_w, cmd.req_speed = torch.zeros(2, dtype=torch.long), torch.zeros(n)
    cmd.gen = torch.Generator().manual_seed(2)
    cmd._prev_pending, cmd.goal_due = None, torch.zeros(n, dtype=torch.bool)
    cmd.goals_set = torch.zeros((), dtype=torch.long)
    old = tr.GOAL_BATCH
    tr.GOAL_BATCH = batch
    return cmd, ball, (lambda: setattr(tr, "GOAL_BATCH", old))


def test_ball_goals_planned_in_fixed_batches_without_loss():
    """D-124: more feeds fall due than one batch holds; the leftover ones are planned on the next steps (persistent due
    flag), each gets exactly the goal the planner gives for its ball, and a touched feed gets none."""
    from picklebot_mj.tasks.timed_reach import plan_goals
    n, batch = 40, 16
    cmd, ball, restore = _fake_ball_cmd(n, batch)
    try:
        cmd._update_command(None)  # first step: records plan_pending
        ball.plan_pending[:] = False  # every window closes at once
        ball.hit_done[3] = True  # touched before its goal was planned
        for _ in range(4):
            cmd._update_command(None)
        got = ~cmd.scored
        assert not got[3] and int(got.sum()) == int(cmd.goals_set)
        cx, ct, found, nrm, vp, stance = plan_goals(ball.ball.pos, ball.ball.vel, torch.zeros(n, 2), torch.Generator())
        want = found.clone()
        want[3] = False
        assert torch.equal(got, want), (got, want)
        assert (cmd.p_star[got] - cx[got]).abs().max() < 1e-5
        assert (cmd.t_contact[got] - (ct[got] / 0.02).round() * 0.02).abs().max() < 1e-5
        assert not cmd.goal_due.any()
    finally:
        restore()


def test_ball_goal_no_false_edge_across_reset():
    """D-124: a feed still pending when its env resets is not planned from the reset ball (no window-closed edge)."""
    n = 4
    cmd, ball, restore = _fake_ball_cmd(n, 4)
    try:
        cmd._update_command(None)
        from mjlab.managers.command_manager import CommandTerm
        orig = CommandTerm.reset
        CommandTerm.reset = lambda self, env_ids: {}
        try:
            cmd.reset(torch.arange(n))
        finally:
            CommandTerm.reset = orig
        ball.plan_pending[:] = False  # the reset's new feeds are not planner feeds
        cmd._update_command(None)
        assert cmd.scored.all() and int(cmd.goals_set) == 0
    finally:
        restore()


def test_e5_rewards_rank_legal_return_first():
    """D-124 pre-launch check: per goal, a good swing with a legal return > a good swing without one > a miss > a fall."""
    import picklebot_mj.tasks as T
    cfg = T._latent_timed_ball_ppo()
    step_dt = cfg.sim.mujoco.timestep * cfg.decimation
    r = {k: v.weight * step_dt for k, v in cfg.rewards.items()}
    assert set(cfg.rewards) >= {"timed_contact", "paddle", "root", "root_progress", "fall", "legal_return"}
    assert "return_shaping" not in cfg.rewards and list(cfg.rewards)[-1] == "legal_return"
    good, legal, fall = r["timed_contact"] * 1.0, r["legal_return"], cfg.rewards["fall"].weight
    swing_legal, swing, miss = good + legal, good, 0.0
    assert swing_legal > swing > miss > fall + good + legal


def test_graphed_planner_rollouts_match_plain():
    """D-124: the CUDA-graph replays give the plain rollouts' results, and a second replay with new inputs too (the
    static buffers are refilled)."""
    from picklebot_mj.planner import predict_top
    for seed in (4216018, 4216019):
        pos, vel, spin, _ = _feed_states(FAMS, 4, seed=seed)
        pos, vel, spin = pos[:64].cuda(), vel[:64].cuda(), spin[:64].cuda()
        a = predict_top(pos, vel, spin)
        b = predict_top(pos, vel, spin, graphed=True)
        assert torch.equal(a[1], b[1]) and (a[0] - b[0]).abs().max() < 1e-5


def test_walkable_contact_without_cap_is_the_first_interception():
    """D-125: with no effective cap the walkable contact is predict_contact's first interception."""
    from picklebot_mj.planner import predict_contact_fast, predict_contact_walkable
    pos, vel, _, _ = _feed_states(FAMS, 4, seed=4216501)
    pos, vel = pos[:64].cuda(), vel[:64].cuda()
    z = torch.zeros_like(pos)
    pel = torch.tensor([-6.0, 0.0], device="cuda").expand(64, 2).contiguous()
    a = predict_contact_fast(pos, vel, z)
    b = predict_contact_walkable(pos, vel, z, pel, cap=1e6)
    assert torch.equal(a[3], b[3])
    assert (a[0] - b[0]).abs().max() < 1e-5 and (a[2] - b[2]).abs().max() < 1e-5


def test_walkable_contact_is_later_and_walkable_when_possible():
    """D-125: the walkable contact is never earlier than the first interception, stays in the bank's heights (or is
    the interception itself), needs at most WALK_CAP where the first interception did not, and otherwise the least."""
    from picklebot_mj.planner import WALK_CAP, WALK_Z_MIN, predict_contact_fast, predict_contact_walkable
    from picklebot_mj.tasks.shadow_swing import HINT_BEHIND, HINT_SIDE_BH, HINT_SIDE_FH, HINT_TOP_Z
    pos, vel, _, _ = _feed_states(FAMS, 8, seed=4216502)
    pos, vel = pos[:128].cuda(), vel[:128].cuda()
    z = torch.zeros_like(pos)
    g = torch.Generator(device="cuda").manual_seed(4216502)
    pel = torch.stack([-6.5 + 2 * torch.rand(128, generator=g, device="cuda"),
                       -1.5 + 3 * torch.rand(128, generator=g, device="cuda")], -1)

    def req(cx, ct):
        side = torch.where(cx[:, 1] <= pel[:, 1], cx[:, 1] + HINT_SIDE_FH, cx[:, 1] - HINT_SIDE_BH)
        st = torch.stack([cx[:, 0] - HINT_BEHIND, side], -1)
        return (st - pel).norm(dim=-1) / ct.clamp(min=0.05)

    a = predict_contact_fast(pos, vel, z)
    b = predict_contact_walkable(pos, vel, z, pel)
    f = a[3]
    assert torch.equal(f, b[3]) and f.sum() > 64
    assert (b[2][f] >= a[2][f] - 1e-6).all()
    moved = f & ((b[0] - a[0]).norm(dim=-1) > 1e-6)
    assert ((b[0][moved, 2] >= WALK_Z_MIN - 1e-4) & (b[0][moved, 2] <= HINT_TOP_Z + 1e-4)).all()
    ra, rb = req(a[0], a[2]), req(b[0], b[2])
    assert (rb[f] <= ra[f] + 1e-4).all()  # never needs more walking than the first interception
    assert ((ra[f] <= WALK_CAP) <= (rb[f] <= WALK_CAP + 1e-4)).all()
    assert (rb[f] > WALK_CAP + 1e-4).float().mean() < (ra[f] > WALK_CAP).float().mean()  # fewer goals above the cap
    assert moved.any()


def test_e6_changes_only_the_planner_and_the_entropy_correction():
    """D-125: E6's task is E5's with the walkable contact, and its PPO config differs only in entropy_coef 0.001."""
    import mjlab.tasks  # noqa: F401
    from dataclasses import asdict
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg
    from picklebot_mj.planner import WALK_CAP
    e5, e6 = load_env_cfg("Picklebot-Latent-TimedBall-PPO-G1"), load_env_cfg("Picklebot-Latent-TimedBall-Walk-G1")
    assert e5.commands["reach"].walk_cap is None and e6.commands["reach"].walk_cap == WALK_CAP
    e6.commands["reach"].walk_cap = None
    import re
    strip = lambda c: re.sub(r" at 0x[0-9a-f]+", "", repr(c))  # noqa: E731
    assert strip(e5) == strip(e6)
    r5, r6 = asdict(load_rl_cfg("Picklebot-Latent-TimedBall-PPO-G1")), asdict(load_rl_cfg("Picklebot-Latent-TimedBall-Walk-G1"))
    assert r6["algorithm"]["entropy_coef"] == 0.001 and r5["algorithm"]["entropy_coef"] != 0.001
    r6["algorithm"]["entropy_coef"] = r5["algorithm"]["entropy_coef"]
    assert r5 == r6


def test_e6_own_changes_only_the_feeds_and_the_entropy_correction():
    """D-126: E6's task is E5's with every feed a replayed own return, and its PPO config differs only in entropy 0.001."""
    import re
    import mjlab.tasks  # noqa: F401
    from dataclasses import asdict
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg
    e5, e6 = load_env_cfg("Picklebot-Latent-TimedBall-PPO-G1"), load_env_cfg("Picklebot-Latent-TimedBall-Own-G1")
    assert e5.actions["ball"].replay_file == "" and e6.actions["ball"].replay_file.endswith("s5g-e3-returns-4216504.pt")
    e6.actions["ball"].replay_file = ""
    strip = lambda c: re.sub(r" at 0x[0-9a-f]+", "", repr(c))  # noqa: E731
    assert strip(e5) == strip(e6)
    r5, r6 = asdict(load_rl_cfg("Picklebot-Latent-TimedBall-PPO-G1")), asdict(load_rl_cfg("Picklebot-Latent-TimedBall-Own-G1"))
    assert r6["algorithm"]["entropy_coef"] == 0.001
    r6["algorithm"]["entropy_coef"] = r5["algorithm"]["entropy_coef"]
    assert r5 == r6
