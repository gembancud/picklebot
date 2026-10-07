"""Stage 5 Drill 3 machinery: reach curriculum, v2 interception hint, real-ball hint, lost margin."""

import sys
from pathlib import Path

import pytest
import torch

from picklebot_mj.ball_sim import BallSim
from picklebot_mj.feeds import FAMILY_NAMES, REACH_FAMILIES, REACH_NEAR, only
from picklebot_mj.tasks.shadow_swing import HINT_TOP_Z, predict_intercept

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tune_feed import _FakeTerm  # noqa: E402


def _top_point(t, n):
    """Simulated post-bounce apex, or the rising crossing of HINT_TOP_Z if the apex is higher."""
    s, sim = t.ball, BallSim()
    bounced = torch.zeros(n, dtype=torch.bool)
    out = torch.full((n, 2), float("nan"))
    prev = s.pos.clone()
    for _ in range(int(4.0 / 0.005)):
        s, ev = sim.step(s, 0.005, 1)
        newly = ev.court_contact & ~bounced
        bounced |= ev.court_contact
        after = bounced & ~newly & torch.isnan(out[:, 0])
        rise_cross = after & (prev[:, 2] < HINT_TOP_Z) & (s.pos[:, 2] >= HINT_TOP_Z)
        apex = after & (s.pos[:, 2] < prev[:, 2])
        hit = rise_cross | apex
        out = torch.where(hit.unsqueeze(-1), torch.where(rise_cross.unsqueeze(-1), s.pos[:, :2], prev[:, :2]), out)
        prev = s.pos.clone()
    return out


@pytest.mark.parametrize("name", FAMILY_NAMES)
def test_v2_hint_close_to_simulated_top_of_bounce(name):
    n = 256
    t = _FakeTerm(only(name), n, seed=13)
    t._feed(torch.arange(n))
    xi, yi = predict_intercept(t.ball.pos.clone(), t.ball.vel.clone(), t.family, "top")
    err = (torch.stack([xi, yi], -1) - _top_point(t, n)).norm(dim=-1)
    ok = torch.isfinite(err)
    assert ok.float().mean() > 0.95
    assert float(err[ok].median()) < 0.3, (name, float(err[ok].median()))


def test_near_versions_are_easier():
    from picklebot_mj.feeds import FAMILIES

    assert set(REACH_NEAR) == set(REACH_FAMILIES)
    assert abs(REACH_NEAR["reach_forehand"].lateral_y[0]) < abs(FAMILIES["reach_forehand"].lateral_y[0])
    assert REACH_NEAR["reach_backhand"].lateral_y[1] < FAMILIES["reach_backhand"].lateral_y[1]
    assert REACH_NEAR["reach_short"].bounce_x[0] < FAMILIES["reach_short"].bounce_x[0]  # bounces less short
    assert REACH_NEAR["reach_deep"].bounce_x[0] > FAMILIES["reach_deep"].bounce_x[0]  # aimed less deep


@pytest.mark.skipif(not torch.cuda.is_available(), reason="needs CUDA (mujoco_warp)")
def test_curriculum_scale_feeds_promotion_hint_and_lost_margin():
    from mjlab.envs import ManagerBasedRlEnv

    from picklebot_mj.feeds import FeedMix
    from picklebot_mj.tasks.return_stand import REACH_MIN_FEEDS, REACH_STEP, return_stand_env_cfg

    n = 64
    cfg = return_stand_env_cfg(targets=True, start_box=True, recovery=True, free_feet=True, hint_v2=True,
                               hit_hint=True, reach_curriculum=True, lost_back_margin=2.5)
    cfg.actions["ball"].feed_mix = FeedMix({"reach_forehand": 1.0})
    cfg.scene.num_envs = n
    cfg.actions["ball"].compile_ball = False
    env = ManagerBasedRlEnv(cfg, device="cuda")
    env.reset()
    t = env.action_manager.get_term("ball")
    rf = FAMILY_NAMES.index("reach_forehand")
    assert float(t.reach_scale[rf]) == 0.0 and float(t.reach_scale[FAMILY_NAMES.index("easy_forehand")]) == 1.0
    lat = t.ball.pos[:, 1] - t.pelvis_xy()[:, 1]
    lo, hi = REACH_NEAR["reach_forehand"].lateral_y
    assert (lat >= lo - 0.05).all() and (lat <= hi + 0.05).all()  # scale 0 -> the near version only
    # Real-ball hint: the spot input shows the stance hint, the true recovery spot is kept aside.
    assert t.hit_hint_on.all() and not torch.allclose(t.recover_xy, t.hit_rec_true)
    # Promotion: sustained success on the family widens it by one step.
    mask = torch.ones(n, dtype=torch.bool, device="cuda")
    t.return_done[:] = True
    for _ in range(REACH_MIN_FEEDS // n + 2):
        t._tally(mask, torch.zeros(n, dtype=torch.bool, device="cuda"))
    assert abs(float(t.reach_scale[rf]) - REACH_STEP) < 1e-6
    assert t.cfg.lost_back_margin == 2.5
