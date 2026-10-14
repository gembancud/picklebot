"""Stage 5C court-wide drill (D-076): zones, zone-valid feeds, volley rally phase, kitchen state from the feet,
volley interception hint (Picklebot-Latent-Court-G1)."""

from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
LATENT = ROOT / "artifacts" / "train" / "latent" / "latent-07" / "latent_10651.pt"
needs = pytest.mark.skipif(not (torch.cuda.is_available() and LATENT.exists()),
                           reason="needs CUDA and the H1 latent controller")


def _env(n=1024, **ball):
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.tasks.registry import load_env_cfg

    cfg = load_env_cfg("Picklebot-Latent-Court-G1")
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob = 0.0, 0.0
    for k, v in ball.items():
        setattr(b, k, v)
    cfg.scene.num_envs = n
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    return env


@needs
def test_feeds_cover_every_zone_and_only_valid_families():
    env = _env()
    t = env.action_manager.get_term("ball")
    assert t.cfg.court_wide and t.lp_zone_samplers is not None
    zones = torch.bincount(t.zone, minlength=3)
    assert (zones > 50).all()  # back, mid and front starts all occur
    assert t._zone_valid[t.zone, t.family].all()  # never a family outside its zones (e.g. no drop from the front)
    env.close()


@needs
def test_volley_feeds_start_in_rally_phase_and_others_must_bounce():
    from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
    from picklebot_mj.rules import Phase

    env = _env(256, lp_curriculum=False, feed_mix=FeedMix({"volley_forehand": 1.0, "easy_forehand": 1.0}))
    t = env.action_manager.get_term("ball")
    vol = t._is_volley[t.family]
    assert vol.any() and (~vol).any()
    assert (t.rules.phase[vol] == int(Phase.RALLY)).all()
    assert (t.rules.phase[~vol] == int(Phase.SERVE_FLIGHT)).all()
    env.close()


@needs
def test_feet_in_the_kitchen_mark_the_robot_as_in_the_kitchen():
    from picklebot_mj.tasks.return_stand import ROBOT_PLAYER

    env = _env(16)
    t = env.action_manager.get_term("ball")
    robot = env.scene["robot"]
    pose = robot.data.root_link_pose_w.clone()
    pose[:8, 0] = env.scene.env_origins[:8, 0] - 1.5  # pelvis 1.5 m from the net: feet in the kitchen
    pose[8:, 0] = env.scene.env_origins[8:, 0] - 5.5  # near the baseline
    robot.write_root_link_pose_to_sim(pose)
    env.sim.forward()
    env.step(torch.zeros(16, 35, device="cuda"))
    occ = t.rules.kitchen_occupied[:, ROBOT_PLAYER]
    assert occ[:8].all() and not occ[8:].any()
    env.close()


def test_volley_hint_is_where_the_ball_passes_one_metre_before_its_bounce():
    import importlib.util

    from picklebot_mj.ball_sim import BallSim
    from picklebot_mj.feeds import FAMILY_NAMES, only
    from picklebot_mj.tasks.shadow_swing import VOLLEY_Z, predict_intercept

    spec = importlib.util.spec_from_file_location("tune_feed", ROOT / "scripts" / "tune_feed.py")
    tf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tf)
    for name in ("volley_forehand", "volley_backhand"):
        t = tf._FakeTerm(only(name), 256, seed=3)
        t._feed(torch.arange(256))
        xi, _ = predict_intercept(t.ball.pos, t.ball.vel, t.family, "top")
        s, sim = t.ball, BallSim()
        xs = torch.full((256,), float("nan"))
        bounced = torch.zeros(256, dtype=torch.bool)
        for _ in range(400):
            prev = s.pos[:, 2].clone()
            s, ev = sim.step(s, 0.005, 1)
            bounced |= ev.court_contact
            cross = ~bounced & (prev > VOLLEY_Z) & (s.pos[:, 2] <= VOLLEY_Z) & torch.isnan(xs)
            xs = torch.where(cross, s.pos[:, 0], xs)
        ok = torch.isfinite(xs)
        assert ok.float().mean() > 0.9
        assert float((xi[ok] - xs[ok]).abs().median()) < 0.3, name


def test_zone_table_matches_the_offline_feed_check():
    from picklebot_mj.feeds import COURT_ZONE_FAMILIES

    assert COURT_ZONE_FAMILIES["drop"] == {"back", "mid"} and COURT_ZONE_FAMILIES["reach_short"] == {"back", "mid"}
    assert COURT_ZONE_FAMILIES["lob"] == {"mid", "front"}
    assert COURT_ZONE_FAMILIES["volley_forehand"] == {"mid", "front"}
    assert COURT_ZONE_FAMILIES["short"] == {"back", "mid", "front"}  # valid from the front (0.16 m travel)
