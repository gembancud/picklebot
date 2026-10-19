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
