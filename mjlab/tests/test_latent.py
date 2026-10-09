"""Stage 5B H1 latent controller (picklebot_mj/latent.py)."""

import torch

from picklebot_mj.latent import (ACTION_DIM, GOAL_DIM, LATENT_DIM, OBS_DIM, LatentController, kl_diag_gauss)


def test_shapes_and_the_prior_and_decoder_ignore_the_goal():
    torch.manual_seed(0)
    m = LatentController(hidden=(64,), dec_hidden=(64,))
    obs = torch.randn(16, OBS_DIM)
    assert m(obs).shape == (16, ACTION_DIM)
    mu, logstd = m.encode(obs)
    assert mu.shape == logstd.shape == (16, LATENT_DIM)
    other = obs.clone()
    other[:, :GOAL_DIM] = torch.randn(16, GOAL_DIM)  # change only the goal part
    z = torch.randn(16, LATENT_DIM)
    assert torch.allclose(m.decode(obs, z), m.decode(other, z))
    assert torch.allclose(m.prior_dist(obs)[0], m.prior_dist(other)[0])
    assert not torch.allclose(m.encode(obs)[0], m.encode(other)[0])  # the encoder does use it


def test_kl_is_zero_for_equal_gaussians_and_positive_otherwise():
    mu, ls = torch.randn(8, 4), torch.randn(8, 4) * 0.3
    assert torch.allclose(kl_diag_gauss(mu, ls, mu, ls), torch.zeros(8), atol=1e-6)
    assert (kl_diag_gauss(mu + 1.0, ls, mu, ls) > 0).all()


def test_distillation_step_fits_a_teacher():
    torch.manual_seed(0)
    m = LatentController(hidden=(128,), dec_hidden=(128,))
    w = torch.randn(OBS_DIM, ACTION_DIM) * 0.1
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)
    obs = torch.randn(2048, OBS_DIM)
    m.norm.update(obs)
    first = None
    for _ in range(300):
        mu_q, ls_q = m.encode(obs)
        z = mu_q + torch.randn_like(mu_q) * ls_q.exp()
        mu_p, ls_p = m.prior_dist(obs)
        loss = ((m.decode(obs, z) - obs @ w) ** 2).mean() + 1e-3 * kl_diag_gauss(mu_q, ls_q, mu_p, ls_p).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        first = first if first is not None else loss.item()
    assert loss.item() < 0.2 * first
