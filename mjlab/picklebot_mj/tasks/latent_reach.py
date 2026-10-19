"""Stage 5B H3 (D-050, D-053): steer the frozen latent controller through its latent; paddle-reach check.

Action term (`LatentJointPositionAction`), used here and by the H4 executor:
    action a = [a_lat (32), a_wrist (3)]
    z = mu_p(s) + lam * sigma_p(s) * tanh(a_lat)                  (LATENT's "latent action barrier")
    joint targets = D(s, z) * scale + default  (+ wrist_residual * tanh(a_wrist) on the right wrist joints)
where the prior (mu_p, sigma_p) and decoder D are the frozen H1 controller, and s is the controller's own 93-dim
proprioception, rebuilt exactly as in the tracking task (IMU linear and angular velocity, biased joint positions and
joint velocities relative to default, and the decoder's previous raw output as "last action").

Task (`latent_reach_env_cfg`): from a standing start, the paddle centre must reach a target 0.3-0.7 m from the right
shoulder and the pelvis a ground target within 1 m, both resampled every 2 s. A target counts as reached if it comes
within 10 cm at any time in its window (the H3 gate, D-053). Falls (torso below 0.5 m or tilt above 60 deg) end the
episode.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field

import torch
from mjlab.envs.mdp.actions.actions import JointPositionAction, JointPositionActionCfg
from mjlab.managers.command_manager import CommandTerm, CommandTermCfg
from mjlab.managers.event_manager import EventTermCfg
from mjlab.managers.observation_manager import ObservationGroupCfg, ObservationTermCfg
from mjlab.managers.reward_manager import RewardTermCfg
from mjlab.managers.scene_entity_config import SceneEntityCfg
from mjlab.managers.termination_manager import TerminationTermCfg
from mjlab.envs import mdp

from picklebot_mj.latent import GOAL_DIM, LatentController

RIGHT_WRIST = ("right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint")
REACH_TOL = 0.10
REACH_TOL_WIDE = 0.25  # reported for information only (D-055)
FALL_Z, FALL_TILT = 0.5, math.radians(60)


def controller_proprio(robot, lin_sensor, ang_sensor, joint_ids, last_action):
    """The tracking actor observation's proprioceptive part (dims GOAL_DIM:), noise-free, in its term order:
    base_lin_vel, base_ang_vel, joint_pos_rel (biased), joint_vel_rel, last action."""
    d = robot.data
    return torch.cat([lin_sensor.data, ang_sensor.data,
                      d.joint_pos_biased[:, joint_ids] - d.default_joint_pos[:, joint_ids],
                      d.joint_vel[:, joint_ids] - d.default_joint_vel[:, joint_ids], last_action], dim=-1)


@dataclass(kw_only=True)
class LatentJointPositionActionCfg(JointPositionActionCfg):
    checkpoint: str = ""
    lam: float = 0.5
    wrist_residual: float = 0.3
    latent: int = 32

    def build(self, env):
        return LatentJointPositionAction(self, env)


class LatentJointPositionAction(JointPositionAction):
    cfg: LatentJointPositionActionCfg

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self.n_joint = self._action_dim
        self._action_dim = cfg.latent + len(RIGHT_WRIST)
        self._raw_actions = torch.zeros(self.num_envs, self._action_dim, device=self.device)
        self.dec = torch.zeros(self.num_envs, self.n_joint, device=self.device)  # decoder's last raw output
        self.wrist = torch.tensor([self._target_names.index(j) for j in RIGHT_WRIST], device=self.device)
        self.model = LatentController(latent=cfg.latent).to(self.device)
        # Stage 5F (D-109 item 7): PICKLEBOT_CONTROLLER swaps the frozen H1 controller for evaluation only (the zero-shot
        # compatibility check of a re-distilled decoder); training tasks never set it.
        self.controller_path = os.environ.get("PICKLEBOT_CONTROLLER") or cfg.checkpoint
        self.model.load_state_dict(torch.load(self.controller_path, map_location=self.device, weights_only=False)["model"])
        self.model.eval()
        for p in self.model.parameters():
            p.requires_grad_(False)
        self.lin = env.scene["robot/imu_lin_vel"]
        self.ang = env.scene["robot/imu_ang_vel"]

    def controller_obs(self) -> torch.Tensor:
        """The tracking task's 160-dim actor observation with the goal part zeroed (prior and decoder ignore it)."""
        proprio = controller_proprio(self._entity, self.lin, self.ang, self._target_ids, self.dec)
        return torch.cat([torch.zeros(self.num_envs, GOAL_DIM, device=self.device), proprio], dim=-1)

    def process_actions(self, actions: torch.Tensor):
        self._raw_actions[:] = actions
        with torch.no_grad():
            obs = self.controller_obs()
            mu, logstd = self.model.prior_dist(obs)
            z = mu + self.cfg.lam * logstd.exp() * torch.tanh(actions[:, :self.cfg.latent])
            dec = self.model.decode(obs, z)
        self.dec = dec.clone()
        self._processed_actions = dec * self._scale + self._offset
        self._processed_actions[:, self.wrist] += self.cfg.wrist_residual * torch.tanh(actions[:, self.cfg.latent:])

    def reset(self, env_ids=None):
        self._raw_actions[env_ids] = 0.0
        self.dec[env_ids] = 0.0
        if getattr(self, "_cmd_fresh", None) is not None:
            self._cmd_fresh[env_ids] = True

    def apply_actions(self):
        """Stage 5E run 4 (D-105): when the ball term draws a per-episode command delay (cmd_lag, physics steps), each
        env's joint targets are the command of cmd_lag physics steps ago; otherwise mjlab's apply, unchanged."""
        ball = getattr(self, "_ball_term", None)
        if ball is None:
            try:
                ball = self._env.action_manager.get_term("ball")
            except Exception:
                ball = False
            self._ball_term = ball
        lag = getattr(ball, "cmd_lag", None) if ball else None
        if lag is None:
            self.applied_delta = None
            return super().apply_actions()
        cur = self._processed_actions
        if getattr(self, "_cmd_hist", None) is None:
            k = int(ball.cfg.episode_cmd_lag[1]) + 1
            self._cmd_hist = cur.unsqueeze(0).repeat(k, 1, 1)
            self._cmd_ar = torch.arange(self.num_envs, device=self.device)
            self._cmd_fresh = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        # A reset env's history starts at its first command (no command from before the reset).
        hist = torch.where(self._cmd_fresh.view(1, -1, 1), cur.unsqueeze(0), self._cmd_hist)
        self._cmd_fresh = torch.zeros_like(self._cmd_fresh)
        self._cmd_hist = torch.cat([cur.unsqueeze(0), hist[:-1]], 0)
        self._processed_actions = self._cmd_hist[lag, self._cmd_ar]
        self.applied_delta = self._processed_actions - cur  # Stage 5F: what the delay changed (critic only)
        try:
            super().apply_actions()
        finally:
            self._processed_actions = cur


def applied_cmd_obs(env, action_name: str = "latent") -> torch.Tensor:
    """Stage 5F (D-109 item 4), critic only: the joint targets applied this physics step minus the ones issued now
    (zero without a command delay). The actor sees only what it issued (its last actions and their history)."""
    t = env.action_manager.get_term(action_name)
    d = getattr(t, "applied_delta", None)
    return torch.zeros(env.num_envs, t.n_joint, device=env.device) if d is None else d


def latency_obs(env) -> torch.Tensor:
    """Stage 5F, critic only: this episode's ball-observation lag and command lag, each as a fraction of its maximum."""
    b = env.action_manager.get_term("ball")
    if getattr(b, "lat_on", None) is None:
        return torch.zeros(env.num_envs, 2, device=env.device)
    c = b.cfg
    return torch.stack([b.obs_lag.float() / max(1, int(c.episode_obs_lag[1])),
                        b.cmd_lag.float() / max(1, int(c.episode_cmd_lag[1]))], -1)


def _yaw_frame(quat):
    w, x, y, z = quat.unbind(-1)
    yaw = torch.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return torch.cos(yaw), torch.sin(yaw)


def _to_heading(vec, c, s):
    """World xy(z) vector into the pelvis heading frame."""
    out = vec.clone()
    out[..., 0] = c * vec[..., 0] + s * vec[..., 1]
    out[..., 1] = -s * vec[..., 0] + c * vec[..., 1]
    return out


@dataclass(kw_only=True)
class ReachCommandCfg(CommandTermCfg):
    entity_name: str = "robot"
    paddle_body: str = "paddle"
    shoulder_body: str = "right_shoulder_pitch_link"
    reach: tuple[float, float] = (0.3, 0.7)
    root_radius: float = 1.0
    root_min: float = 0.0  # > 0: root targets uniform in distance over [root_min, root_radius] (agility, D-075)
    resampling_time_range: tuple[float, float] = (2.0, 2.0)
    debug_vis: bool = False

    def build(self, env):
        return ReachCommand(self, env)


class ReachCommand(CommandTerm):
    cfg: ReachCommandCfg

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self.robot = env.scene[cfg.entity_name]
        self.paddle = list(self.robot.body_names).index(cfg.paddle_body)
        self.shoulder = list(self.robot.body_names).index(cfg.shoulder_body)
        n = self.num_envs
        self.paddle_target = torch.zeros(n, 3, device=self.device)
        self.root_target = torch.zeros(n, 2, device=self.device)
        self.min_paddle = torch.full((n,), 1e9, device=self.device)
        self.min_root = torch.full((n,), 1e9, device=self.device)
        self.started = torch.zeros(n, dtype=torch.bool, device=self.device)
        self.tally = {"windows": 0, "paddle_reached": 0, "root_reached": 0, "paddle_reached_25": 0,
                      "root_reached_25": 0}
        self.metrics["paddle_dist"] = torch.zeros(n, device=self.device)
        self.metrics["root_dist"] = torch.zeros(n, device=self.device)

    @property
    def command(self):
        d = self.robot.data
        c, s = _yaw_frame(d.root_link_quat_w)
        pad = d.body_link_pos_w[:, self.paddle]
        sh = d.body_link_pos_w[:, self.shoulder]
        root = d.root_link_pos_w
        rel_p = _to_heading(self.paddle_target - pad, c, s)
        rel_sh = _to_heading(self.paddle_target - sh, c, s)
        rel_r = torch.zeros(self.num_envs, 3, device=self.device)
        rel_r[:, :2] = self.root_target - root[:, :2]
        rel_r = _to_heading(rel_r, c, s)[:, :2]
        return torch.cat([rel_p, rel_sh, rel_r, self.time_left.unsqueeze(-1)], dim=-1)

    def distances(self):
        d = self.robot.data
        dp = (d.body_link_pos_w[:, self.paddle] - self.paddle_target).norm(dim=-1)
        dr = (d.root_link_pos_w[:, :2] - self.root_target).norm(dim=-1)
        return dp, dr

    def _update_metrics(self):
        dp, dr = self.distances()
        self.min_paddle = torch.minimum(self.min_paddle, dp)
        self.min_root = torch.minimum(self.min_root, dr)
        self.metrics["paddle_dist"] = dp
        self.metrics["root_dist"] = dr

    def _resample_command(self, env_ids):
        done = env_ids[self.started[env_ids]]
        if len(done):
            self.tally["windows"] += len(done)
            self.tally["paddle_reached"] += int((self.min_paddle[done] < REACH_TOL).sum())
            self.tally["root_reached"] += int((self.min_root[done] < REACH_TOL).sum())
            self.tally["paddle_reached_25"] += int((self.min_paddle[done] < REACH_TOL_WIDE).sum())
            self.tally["root_reached_25"] += int((self.min_root[done] < REACH_TOL_WIDE).sum())
        self.started[env_ids] = True
        d = self.robot.data
        n = len(env_ids)
        c, s = _yaw_frame(d.root_link_quat_w[env_ids])
        # Root target: uniform in a disc of radius root_radius around the current pelvis position.
        if self.cfg.root_min > 0.0:  # annulus, uniform in distance: far targets are as common as near ones
            r = self.cfg.root_min + (self.cfg.root_radius - self.cfg.root_min) * torch.rand(n, device=self.device)
        else:
            r = self.cfg.root_radius * torch.rand(n, device=self.device).sqrt()
        a = 2 * math.pi * torch.rand(n, device=self.device)
        self.root_target[env_ids] = d.root_link_pos_w[env_ids, :2] + torch.stack([r * a.cos(), r * a.sin()], -1)
        # Paddle target: from the right shoulder, a direction in the forward/right/up hemisphere (heading frame:
        # x forward, y left), at 0.3-0.7 m, at least 0.3 m above the ground.
        dist = torch.empty(n, device=self.device).uniform_(*self.cfg.reach)
        az = torch.empty(n, device=self.device).uniform_(-math.pi / 2, math.pi / 3)  # right side to front-left
        el = torch.empty(n, device=self.device).uniform_(-math.pi / 3, math.pi / 3)
        local = torch.stack([el.cos() * az.cos(), el.cos() * az.sin(), el.sin()], -1) * dist.unsqueeze(-1)
        world = local.clone()
        world[:, 0] = c * local[:, 0] - s * local[:, 1]
        world[:, 1] = s * local[:, 0] + c * local[:, 1]
        tgt = d.body_link_pos_w[env_ids, self.shoulder] + world
        tgt[:, 2] = tgt[:, 2].clamp(min=0.3)
        self.paddle_target[env_ids] = tgt
        self.min_paddle[env_ids] = 1e9
        self.min_root[env_ids] = 1e9

    def _update_command(self, env_ids):
        pass


def paddle_track(env, command_name="reach", std=0.15):
    dp, _ = env.command_manager.get_term(command_name).distances()
    return torch.exp(-(dp / std) ** 2)


def root_track(env, command_name="reach", std=0.3):
    _, dr = env.command_manager.get_term(command_name).distances()
    return torch.exp(-(dr / std) ** 2)


def root_progress(env, command_name="reach", asset_name="robot", max_speed=1.0):
    """Pelvis velocity toward the root target (m/s), clamped (H3 extension E1, D-055)."""
    cmd = env.command_manager.get_term(command_name)
    d = env.scene[asset_name].data
    to = cmd.root_target - d.root_link_pos_w[:, :2]
    dist = to.norm(dim=-1, keepdim=True).clamp(min=1e-3)
    v = (d.root_link_lin_vel_w[:, :2] * (to / dist)).sum(-1)
    return v.clamp(-max_speed, max_speed) * (dist.squeeze(-1) > 0.05)


def latent_action_l2(env, action_name="latent", latent=32):
    """L2 of the latent part of the high-level action (H3 extension E2, D-055)."""
    return env.action_manager.get_term(action_name).raw_action[:, :latent].pow(2).sum(-1)


def latent_prior_nll(env, action_name="latent"):
    """Prior-likelihood penalty (H4, D-072): sum over latent dims of (lam * tanh(a_lat))^2, i.e. the squared distance
    of the chosen latent from the prior mean in prior-std units (-2 log p(z|s) up to a constant), as in PULSE/ASE.
    Unlike latent_action_l2 on the raw action, it stays informative when tanh saturates."""
    term = env.action_manager.get_term(action_name)
    a = term.raw_action[:, :term.cfg.latent]
    return (term.cfg.lam * torch.tanh(a)).pow(2).sum(-1)


def fell(env, asset_name="robot"):
    d = env.scene[asset_name].data
    torso = list(env.scene[asset_name].body_names).index("torso_link")
    tilt = torch.acos((-d.projected_gravity_b[:, 2]).clamp(-1, 1))
    return (d.body_link_pos_w[:, torso, 2] < FALL_Z) | (tilt > FALL_TILT)


def latent_reach_env_cfg(checkpoint: str, motion_file: str, play: bool = False, lam: float = 0.5):
    """H3 task. Built on the paddle tracking scene (robot, collisions, sensors, physics), with the motion parts removed."""
    from mjlab.asset_zoo.robots import G1_ACTION_SCALE

    from picklebot_mj.tasks.tracking import paddle_tracking_env_cfg

    cfg = paddle_tracking_env_cfg(motion_file, play=play)
    cfg.actions = {"latent": LatentJointPositionActionCfg(entity_name="robot", actuator_names=(".*",),
                                                         scale=G1_ACTION_SCALE, checkpoint=checkpoint, lam=lam)}
    cfg.commands = {"reach": ReachCommandCfg()}
    pol = {
        "base_lin_vel": ObservationTermCfg(func=mdp.builtin_sensor, params={"sensor_name": "robot/imu_lin_vel"}),
        "base_ang_vel": ObservationTermCfg(func=mdp.builtin_sensor, params={"sensor_name": "robot/imu_ang_vel"}),
        "projected_gravity": ObservationTermCfg(func=mdp.projected_gravity),
        "joint_pos": ObservationTermCfg(func=mdp.joint_pos_rel),
        "joint_vel": ObservationTermCfg(func=mdp.joint_vel_rel),
        "actions": ObservationTermCfg(func=mdp.last_action),
        "reach": ObservationTermCfg(func=mdp.generated_commands, params={"command_name": "reach"}),
    }
    cfg.observations = {"actor": ObservationGroupCfg(terms=dict(pol), concatenate_terms=True),
                        "critic": ObservationGroupCfg(terms=dict(pol), concatenate_terms=True)}
    cfg.rewards = {
        "paddle": RewardTermCfg(func=paddle_track, weight=2.0),
        "root": RewardTermCfg(func=root_track, weight=1.0),
        "alive": RewardTermCfg(func=mdp.is_alive, weight=0.5),
        "fall": RewardTermCfg(func=mdp.is_terminated, weight=-50.0),
        "action_rate": RewardTermCfg(func=mdp.action_rate_l2, weight=-0.01),
    }
    cfg.terminations = {"time_out": TerminationTermCfg(func=mdp.time_out, time_out=True),
                        "fell": TerminationTermCfg(func=fell)}
    keep = {k: v for k, v in cfg.events.items() if k in ("base_com", "encoder_bias", "foot_friction")}
    keep["reset_base"] = EventTermCfg(func=mdp.reset_root_state_uniform, mode="reset",
                                      params={"pose_range": {"yaw": (-math.pi, math.pi)}, "velocity_range": {}})
    keep["reset_joints"] = EventTermCfg(func=mdp.reset_joints_by_offset, mode="reset",
                                        params={"position_range": (0.0, 0.0), "velocity_range": (0.0, 0.0)})
    cfg.events = keep
    cfg.episode_length_s = 10.0
    return cfg


# Stage 5C run 19 (D-086): a residual executor around a frozen two-skill executor.
#   z = mu_p(s) + lam * sigma_p(s) * tanh(a_ref) + lam_r * sigma_p(s) * tanh(a)
# a_ref is the frozen executor's own (deterministic) action on the same actor observation, with that observation's
# last-action term replaced by the frozen executor's own last action (not the residual's). With a = 0 the term
# reproduces the frozen executor exactly. The wrist residual adds wrist_r * tanh(a_wrist) to the frozen executor's.
@dataclass(kw_only=True)
class ResidualLatentActionCfg(LatentJointPositionActionCfg):
    base_checkpoint: str = ""
    base_actor_cfg: dict = field(default_factory=dict)  # MLPModel kwargs: activation, obs_normalization, distribution_cfg
    lam_r: float = 1.0
    wrist_r: float = 0.1

    def build(self, env):
        return ResidualLatentAction(self, env)


class ResidualLatentAction(LatentJointPositionAction):
    cfg: ResidualLatentActionCfg

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self._env_ref = env
        self.base = None  # built on the first step, once the observation manager exists
        self.base_last = torch.zeros(self.num_envs, self._action_dim, device=self.device)
        self.a_ref = torch.zeros(self.num_envs, self._action_dim, device=self.device)

    def _build_base(self, obs_dim: int):
        from rsl_rl.models.mlp_model import MLPModel
        from tensordict import TensorDict

        sd = torch.load(self.cfg.base_checkpoint, map_location=self.device, weights_only=False)["actor_state_dict"]
        ws = sorted((int(k.split(".")[1]), v.shape[0]) for k, v in sd.items()
                    if k.startswith("mlp.") and k.endswith(".weight"))
        kw = dict(self.cfg.base_actor_cfg)
        kw["hidden_dims"] = tuple(n for _, n in ws[:-1])
        base = MLPModel(TensorDict({"actor": torch.zeros(1, obs_dim)}, batch_size=[1]), {"actor": ["actor"]}, "actor",
                        self._action_dim, **kw).to(self.device)
        base.load_state_dict(sd, strict=True)
        base.eval()
        for p in base.parameters():
            p.requires_grad_(False)
        om = self._env_ref.observation_manager
        start = 0
        for n, d in zip(om.active_terms["actor"], om.group_obs_term_dim["actor"]):
            w = int(torch.tensor(d).prod())
            if n == "actions":
                self._act_slice = slice(start, start + w)
            start += w
        self.base = base

    def base_action(self) -> torch.Tensor:
        from tensordict import TensorDict

        x = self._env_ref.obs_buf["actor"]
        if self.base is None:
            self._build_base(x.shape[1])
        x = x.clone()
        x[:, self._act_slice] = self.base_last
        with torch.no_grad():
            return self.base(TensorDict({"actor": x}, batch_size=[x.shape[0]])).clone()

    def process_actions(self, actions: torch.Tensor):
        self._raw_actions[:] = actions
        a_ref = self.base_action()
        self.a_ref = a_ref
        self.base_last = a_ref.clone()
        L = self.cfg.latent
        with torch.no_grad():
            obs = self.controller_obs()
            mu, logstd = self.model.prior_dist(obs)
            sig = logstd.exp()
            z = mu + self.cfg.lam * sig * torch.tanh(a_ref[:, :L]) + self.cfg.lam_r * sig * torch.tanh(actions[:, :L])
            dec = self.model.decode(obs, z)
        self.dec = dec.clone()
        self._processed_actions = dec * self._scale + self._offset
        self._processed_actions[:, self.wrist] += (self.cfg.wrist_residual * torch.tanh(a_ref[:, L:])
                                                   + self.cfg.wrist_r * torch.tanh(actions[:, L:]))

    def reset(self, env_ids=None):
        super().reset(env_ids)
        self.base_last[env_ids] = 0.0  # the action manager zeroes the last action at a reset, as the base was trained


def residual_prior_nll(env, action_name="latent", move_weight=3.0):
    """Residual penalty (D-086): sum over latent dims of (lam_r * tanh(a))^2, the squared distance of the latent from
    the frozen executor's in prior-std units; move_weight times heavier in move-to-spot episodes (protects footwork)."""
    term = env.action_manager.get_term(action_name)
    a = term.raw_action[:, :term.cfg.latent]
    pen = (term.cfg.lam_r * torch.tanh(a)).pow(2).sum(-1)
    ball = env.action_manager.get_term("ball")
    if getattr(ball, "drill", None) is not None:
        pen = pen * (1.0 + (move_weight - 1.0) * ball.drill.move_ep.float())
    return pen


def composite_prior_nll(env, action_name="latent"):
    """Style anchor for residual executors (Stage 5D, D-093): the prior-likelihood penalty of D-072 on the composite
    latent, sum over dims of (lam tanh(a_base) + lam_r tanh(a))^2 = |z - mu_p|^2 / sigma_p^2. Residual tasks had
    replaced it by the penalty toward the base, so nothing pulled the composite towards the prior mean (human-like
    poses); style drifted 4.0 -> 4.2."""
    term = env.action_manager.get_term(action_name)
    L = term.cfg.latent
    off = term.cfg.lam * torch.tanh(term.a_ref[:, :L]) + term.cfg.lam_r * torch.tanh(term.raw_action[:, :L])
    return off.pow(2).sum(-1)


def overspeed(env, vmax: float = 1.2, asset_name: str = "robot"):
    """Falls fix (Stage 5D, D-092 diagnosis): squared pelvis ground speed above vmax (m/s). Run 22's falls happen
    mostly while running for far balls, at a median 1.59 m/s one step before the fall (0.58 m/s otherwise)."""
    v = env.scene[asset_name].data.root_link_lin_vel_w[:, :2].norm(dim=-1)
    return (v - vmax).clamp(min=0.0).pow(2)


def gait_anchor(env, teacher: str, actor_cfg: dict, std: float = 0.22, approach_dist: float = 1.0,
                action_name: str = "latent"):
    """Gait anchor (Stage 5D, D-095): exp(-mean((q - q_walk)^2) / std^2), where q is this step's executed joint action
    (teacher units, (target - default) / scale) and q_walk the flat walking teacher's action on the observation the
    policy acted on (its last-action term replaced by the last executed joint action).
    - Move-to-spot episodes: the teacher sees the observation as is.
    - Ball episodes, while the ball is still incoming and farther than approach_dist from the pelvis: the teacher sees a
      parked ball (as in its move episodes) and the feed's ideal stance spot as its spot input, so it walks there in its
      own gait. Run 12's distilled walking-teacher footwork scored style 3.585; fast poses cost about 4.5 (D-094).
    Zero elsewhere (contact window, after the hit, between feeds)."""
    from rsl_rl.models.mlp_model import MLPModel
    from tensordict import TensorDict

    from picklebot_mj.tasks.move_drill import PARK_POS
    from picklebot_mj.tasks.return_stand import _rotate_inv

    term = env.action_manager.get_term(action_name)
    ball = env.action_manager.get_term("ball")
    robot = env.scene["robot"]
    st = getattr(env, "_picklebot_gait", None)
    x = env.obs_buf.get("actor") if isinstance(env.obs_buf, dict) else None
    if x is None:
        return torch.zeros(env.num_envs, device=env.device)
    if st is None:
        om = env.observation_manager
        cols, start = {}, 0
        for nm, dm in zip(om.active_terms["actor"], om.group_obs_term_dim["actor"]):
            w = term.n_joint if nm == "actions" else int(torch.tensor(dm).prod())
            cols[nm] = slice(start, start + w)
            start += w
        sl, s0 = None, 0
        for nm, dm in zip(om.active_terms["actor"], om.group_obs_term_dim["actor"]):
            w = int(torch.tensor(dm).prod())
            if nm == "actions":
                sl = slice(s0, s0 + w)
            s0 += w
        sd = torch.load(teacher, map_location=env.device, weights_only=False)["actor_state_dict"]
        ws = sorted((int(k.split(".")[1]), v.shape[0]) for k, v in sd.items()
                    if k.startswith("mlp.") and k.endswith(".weight"))
        kw = dict(actor_cfg)
        kw["hidden_dims"] = tuple(n for _, n in ws[:-1])
        tch = MLPModel(TensorDict({"actor": torch.zeros(1, start)}, batch_size=[1]), {"actor": ["actor"]}, "actor",
                       term.n_joint, **kw).to(env.device)
        tch.load_state_dict(sd, strict=True)
        tch.eval()
        for p in tch.parameters():
            p.requires_grad_(False)
        st = {"teacher": tch, "cols": cols, "sl": sl, "last": torch.zeros(env.num_envs, term.n_joint, device=env.device),
              "park": torch.tensor(PARK_POS, device=env.device), "flags": torch.zeros(2, device=env.device)}
        env._picklebot_gait = st
    q = ((term._processed_actions - term._offset) / term._scale).detach()
    move = ball.drill.move_ep if getattr(ball, "drill", None) is not None else torch.zeros_like(ball.hit_done)
    pel = ball.pelvis_xy()
    d_ball = (ball.ball.pos[:, :2] - pel).norm(dim=-1)
    approach = ~move & ~ball.hit_done & ~ball.rules.dead & ~ball.tallied & (d_ball > approach_dist)
    with torch.no_grad():
        tx = torch.cat([x[:, :st["sl"].start], st["last"], x[:, st["sl"].stop:]], dim=-1)
        if move.any():
            st["flags"] = tx[move][:, st["cols"]["rally_flags"]].mean(0).round()
        c = st["cols"]
        root = robot.data.root_link_pose_w
        paddle = robot.data.body_link_pose_w[:, ball.paddle_id, :3]
        pw = st["park"] + env.scene.env_origins
        pv = tx.clone()
        pv[:, c["ball_pos"]] = _rotate_inv(root[:, 3:7], pw - root[:, :3])
        pv[:, c["ball_vel"]] = 0.0
        pv[:, c["ball_from_paddle"]] = _rotate_inv(root[:, 3:7], pw - paddle)
        pv[:, c["rally_flags"]] = st["flags"]
        rel = torch.zeros(env.num_envs, 3, device=env.device)
        rel[:, :2] = ball.stance_xy - pel
        pv[:, c["recovery"]] = _rotate_inv(root[:, 3:7], rel)[:, :2] / 3.0
        tx = torch.where(approach.unsqueeze(-1), pv, tx)
        q_walk = st["teacher"](TensorDict({"actor": tx}, batch_size=[env.num_envs]))
    st["last"] = torch.where((env.episode_length_buf <= 1).unsqueeze(-1), torch.zeros_like(q), q)
    r = torch.exp(-((q - q_walk) ** 2).mean(-1) / std ** 2)
    return r * (move | approach).float()
