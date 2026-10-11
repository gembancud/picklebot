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
        self.model.load_state_dict(torch.load(cfg.checkpoint, map_location=self.device, weights_only=False)["model"])
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
