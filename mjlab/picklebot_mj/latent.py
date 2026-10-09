"""Latent motion controller (Stage 5B H1, D-050): PULSE / LATENT-style encoder, prior and decoder.

Distilled from the tracking teacher with DAgger (scripts/distill_latent.py):
- encoder q(z | s, g): sees the whole tracking observation, i.e. the robot's proprioception s plus the goal g
  (reference joint command and the anchor's pose error);
- prior p(z | s): proprioception only;
- decoder a = D(s, z): proprioception plus a latent, giving the 29 joint-position actions.

The prior and decoder never see reference information, so after distillation they form a controller that can only
produce teacher-like (human-like) motion, steered through z (H3/H4). Loss (PULSE):
MSE(D(s, z_q), a_teacher) + w_smooth * |D(s_t, mu_q,t) - D(s_t-1, mu_q,t-1)|^2 + beta * KL(q || p).

Observation layout: the tracking task's actor group, 160 dims in this order. The first GOAL_DIM entries (command 58,
motion_anchor_pos_b 3, motion_anchor_ori_b 6) are the goal; the remaining 93 (base_lin_vel 3, base_ang_vel 3,
joint_pos 29, joint_vel 29, actions 29) are proprioception.
"""

from __future__ import annotations

import torch
from torch import nn

GOAL_DIM = 67
OBS_DIM = 160
PROPRIO_DIM = OBS_DIM - GOAL_DIM
LATENT_DIM = 32
ACTION_DIM = 29


def mlp(dims, act=nn.ELU):
    layers = []
    for i in range(len(dims) - 1):
        layers.append(nn.Linear(dims[i], dims[i + 1]))
        if i < len(dims) - 2:
            layers.append(act())
    return nn.Sequential(*layers)


class RunningNorm(nn.Module):
    """Per-feature running mean/std (frozen once `frozen` is set)."""

    def __init__(self, dim, eps=1e-2):
        super().__init__()
        self.register_buffer("mean", torch.zeros(dim))
        self.register_buffer("var", torch.ones(dim))
        self.register_buffer("count", torch.tensor(1e-4))
        self.eps = eps

    @torch.no_grad()
    def update(self, x):
        b = x.shape[0]
        m, v = x.mean(0), x.var(0, unbiased=False)
        tot = self.count + b
        d = m - self.mean
        self.mean += d * b / tot
        self.var = (self.var * self.count + v * b + d.pow(2) * self.count * b / tot) / tot
        self.count = tot

    def forward(self, x):
        return (x - self.mean) / (self.var + self.eps).sqrt()


class LatentController(nn.Module):
    def __init__(self, hidden=(1024, 512), dec_hidden=(1024, 512, 256), latent=LATENT_DIM):
        super().__init__()
        self.latent = latent
        self.norm = RunningNorm(OBS_DIM)
        self.encoder = mlp([OBS_DIM, *hidden, 2 * latent])
        self.prior = mlp([PROPRIO_DIM, *hidden, 2 * latent])
        self.decoder = mlp([PROPRIO_DIM + latent, *dec_hidden, ACTION_DIM])

    @staticmethod
    def split(obs):
        return obs[..., GOAL_DIM:]

    def _gauss(self, net, x):
        mu, logstd = net(x).chunk(2, dim=-1)
        return mu, logstd.clamp(-5.0, 2.0)

    def encode(self, obs):
        return self._gauss(self.encoder, self.norm(obs))

    def prior_dist(self, obs):
        return self._gauss(self.prior, self.split(self.norm(obs)))

    def decode(self, obs, z):
        return self.decoder(torch.cat([self.split(self.norm(obs)), z], dim=-1))

    def forward(self, obs, sample=False):
        """Teacher-replacing student: encoder -> decoder (mean latent unless `sample`)."""
        mu, logstd = self.encode(obs)
        z = mu + torch.randn_like(mu) * logstd.exp() if sample else mu
        return self.decode(obs, z)

    def prior_action(self, obs, eps=None, scale=1.0):
        """Prior-only control: z = mu_p + scale * sigma_p * eps (eps ~ N(0, 1) if None)."""
        mu, logstd = self.prior_dist(obs)
        eps = torch.randn_like(mu) if eps is None else eps
        return self.decode(obs, mu + scale * logstd.exp() * eps)


def kl_diag_gauss(mu_q, logstd_q, mu_p, logstd_p):
    """KL(q || p) for diagonal Gaussians, summed over the latent."""
    vq, vp = (2 * logstd_q).exp(), (2 * logstd_p).exp()
    return (logstd_p - logstd_q + (vq + (mu_q - mu_p) ** 2) / (2 * vp) - 0.5).sum(-1)
