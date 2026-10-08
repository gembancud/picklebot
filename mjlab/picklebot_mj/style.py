"""Adversarial motion prior (AMP-style) for the executor (Stage 5B, D-044/D-046/D-047).

A discriminator D learns to tell the robot's state transitions (phi_t, phi_t+1) from transitions in the retargeted
human clips (Tennis-MoCap strokes + LAFAN1 footwork, `artifacts/motion/tracking/*.npz`). The robot gets a style reward
r = max(0, 1 - 0.25 (D - 1)^2) (least-squares GAN, as in AMP, Peng et al. 2021).

Unlike the original AMP, which updates D inside the PPO update, D lives with the environment and is updated from a
replay buffer of recent robot transitions every `update_every` env steps, so the stock rsl_rl PPO (and RegPPO) are
unchanged. D's own optimisation (LSGAN loss with a gradient penalty on expert samples) follows AMP.

Features phi (heading-invariant, pelvis frame), 80 dims:
joint positions (29), joint velocities (29), pelvis height (1), pelvis linear and angular velocity (6), projected
gravity (3), hands (wrist_yaw_link) and feet (ankle_roll_link) positions relative to the pelvis (12).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
from torch import nn

KEY_BODIES = ("left_wrist_yaw_link", "right_wrist_yaw_link", "left_ankle_roll_link", "right_ankle_roll_link")
ROOT_BODY = "pelvis"


def _quat_rotate_inv(q: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    """Rotate v by the inverse of unit quaternion q (wxyz). q: (..., 4), v: (..., 3)."""
    w, xyz = q[..., :1], q[..., 1:]
    t = 2.0 * torch.cross(xyz, v, dim=-1)
    return v - w * t + torch.cross(xyz, t, dim=-1)


def features(joint_pos, joint_vel, root_pos, root_quat, root_lin_vel_w, root_ang_vel_w, key_pos_w):
    """phi from world-frame quantities. key_pos_w: (..., K, 3)."""
    lin_b = _quat_rotate_inv(root_quat, root_lin_vel_w)
    ang_b = _quat_rotate_inv(root_quat, root_ang_vel_w)
    grav = _quat_rotate_inv(root_quat, torch.tensor([0.0, 0.0, -1.0], device=root_quat.device).expand_as(lin_b))
    q = root_quat.unsqueeze(-2).expand(*key_pos_w.shape[:-1], 4)
    keys = _quat_rotate_inv(q, key_pos_w - root_pos.unsqueeze(-2)).flatten(-2)
    return torch.cat([joint_pos, joint_vel, root_pos[..., 2:3], lin_b, ang_b, grav, keys], dim=-1)


def expert_transitions(files, body_names, device="cpu"):
    """(phi_t, phi_t+1) pairs from tracking npz files, never across a clip boundary."""
    root = body_names.index(ROOT_BODY)
    keys = [body_names.index(b) for b in KEY_BODIES]
    a, b = [], []
    for f in files:
        d = np.load(f)
        t = lambda k: torch.tensor(d[k], dtype=torch.float32, device=device)  # noqa: E731
        bp, bq, bv, bw = t("body_pos_w"), t("body_quat_w"), t("body_lin_vel_w"), t("body_ang_vel_w")
        phi = features(t("joint_pos"), t("joint_vel"), bp[:, root], bq[:, root], bv[:, root], bw[:, root], bp[:, keys])
        n = len(phi)
        starts = d["clip_starts"] if "clip_starts" in d else np.array([0])
        last = np.r_[starts[1:], n] - 1  # each clip's last frame has no successor inside the clip
        ok = np.ones(n - 1, dtype=bool)
        ok[last[last < n - 1]] = False
        idx = torch.tensor(np.nonzero(ok)[0], device=device)
        a.append(phi[idx])
        b.append(phi[idx + 1])
    return torch.cat(a), torch.cat(b)


@dataclass
class StyleCfg:
    motion_files: tuple[str, ...] = ()
    hidden: tuple[int, ...] = (1024, 512)
    lr: float = 5e-5
    gp_weight: float = 5.0
    batch: int = 4096
    buffer: int = 200_000
    update_every: int = 24  # env steps between discriminator updates (one PPO rollout)
    updates: int = 4  # gradient steps per update
    save_path: str | None = None  # discriminator weights are written here at each update (for metrics / resume)
    load_path: str | None = None
    extra: dict = field(default_factory=dict)


class StyleDiscriminator:
    def __init__(self, cfg: StyleCfg, body_names, device):
        self.cfg, self.device = cfg, device
        with torch.inference_mode(False):
            ea, eb = expert_transitions(cfg.motion_files, list(body_names), device)
            self.expert = torch.cat([ea, eb], dim=-1)
            self.mean = self.expert.mean(0)
            self.std = self.expert.std(0).clamp(min=1e-3)
            dims, layers = [self.expert.shape[1], *cfg.hidden], []
            for i in range(len(dims) - 1):
                layers += [nn.Linear(dims[i], dims[i + 1]), nn.ReLU()]
            self.net = nn.Sequential(*layers, nn.Linear(dims[-1], 1)).to(device)
            if cfg.load_path and Path(cfg.load_path).exists():
                self.net.load_state_dict(torch.load(cfg.load_path, map_location=device))
            self.opt = torch.optim.Adam(self.net.parameters(), lr=cfg.lr)
            self.buf = torch.zeros(cfg.buffer, self.expert.shape[1], device=device)
        self.n_buf, self.ptr, self.calls, self.n_updates = 0, 0, 0, 0
        self.stats = {"d_expert": 0.0, "d_agent": 0.0, "loss": 0.0}

    def score(self, pair: torch.Tensor) -> torch.Tensor:
        return self.net((pair - self.mean) / self.std).squeeze(-1)

    def reward(self, pair: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            d = self.score(pair)
        return torch.clamp(1.0 - 0.25 * (d - 1.0) ** 2, min=0.0)

    def add(self, pair: torch.Tensor):
        n = len(pair)
        idx = (self.ptr + torch.arange(n, device=self.device)) % self.cfg.buffer
        self.buf[idx] = pair.detach().clone()
        self.ptr = (self.ptr + n) % self.cfg.buffer
        self.n_buf = min(self.cfg.buffer, self.n_buf + n)

    def step(self):
        """Called once per env step; trains D every `update_every` steps."""
        self.calls += 1
        if self.calls % self.cfg.update_every or self.n_buf < self.cfg.batch:
            return
        with torch.inference_mode(False), torch.enable_grad():
            for _ in range(self.cfg.updates):
                agent = self.buf[torch.randint(0, self.n_buf, (self.cfg.batch,), device=self.device)].clone()
                expert = self.expert[torch.randint(0, len(self.expert), (self.cfg.batch,), device=self.device)]
                expert = expert.clone().requires_grad_(True)
                de, da = self.score(expert), self.score(agent)
                grad = torch.autograd.grad(de.sum(), expert, create_graph=True)[0]
                gp = (grad / self.std).pow(2).sum(-1).mean()  # penalty in the normalised input space
                loss = ((de - 1) ** 2).mean() + ((da + 1) ** 2).mean() + self.cfg.gp_weight * gp
                self.opt.zero_grad()
                loss.backward()
                self.opt.step()
            self.n_updates += 1
            self.stats = {"d_expert": float(de.mean()), "d_agent": float(da.mean()), "loss": float(loss)}
            if self.cfg.save_path and self.n_updates % 50 == 0:
                Path(self.cfg.save_path).parent.mkdir(parents=True, exist_ok=True)
                torch.save(self.net.state_dict(), self.cfg.save_path)


def robot_features(robot, key_ids):
    d = robot.data
    return features(d.joint_pos, d.joint_vel, d.root_link_pos_w, d.root_link_quat_w, d.root_link_lin_vel_w,
                    d.root_link_ang_vel_w, d.body_link_pos_w[:, key_ids])


def style_reward(env, cfg: StyleCfg, asset_name: str = "robot") -> torch.Tensor:
    """mjlab reward term: AMP style reward for the transition from the previous step to now."""
    st = getattr(env, "_picklebot_style", None)
    robot = env.scene[asset_name]
    if st is None:
        key_ids = [list(robot.body_names).index(b) for b in KEY_BODIES]
        st = {"disc": StyleDiscriminator(cfg, robot.body_names, env.device), "keys": key_ids, "prev": None}
        env._picklebot_style = st
    phi = robot_features(robot, st["keys"])
    prev = st["prev"]
    st["prev"] = phi.clone()
    if prev is None:
        return torch.zeros(env.num_envs, device=env.device)
    pair = torch.cat([prev, phi], dim=-1)
    fresh = env.episode_length_buf <= 1  # first step after a reset: prev belongs to the previous episode
    r = torch.where(fresh, torch.zeros_like(phi[:, 0]), st["disc"].reward(pair))
    if (~fresh).any():
        st["disc"].add(pair[~fresh])
    st["disc"].step()
    if hasattr(env, "extras"):
        env.extras.setdefault("log", {}).update({f"Style/{k}": v for k, v in st["disc"].stats.items()})
    return r
