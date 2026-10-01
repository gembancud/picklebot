"""Driven-paddle rig on the GPU: court, analytic ball (D-039) and a scripted paddle in mjlab.

No robot and no learning. Each episode tosses a ball above a paddle that swings
forward and upward through it at constant velocity. The paddle is a mocap body
driven by the script; the ball is a mocap body driven by `BallSim`, advanced on
every MuJoCo physics step. The paddle reaction impulse is accumulated for
inspection; applying it to a dynamic body happens with the G1 in Stage 2.
"""

from __future__ import annotations

import math

import mujoco
import torch

from mjlab.entity import EntityCfg
from mjlab.envs import ManagerBasedRlEnv, ManagerBasedRlEnvCfg
from mjlab.envs.mdp import time_out
from mjlab.managers.observation_manager import ObservationGroupCfg, ObservationTermCfg
from mjlab.managers.termination_manager import TerminationTermCfg
from mjlab.scene import SceneCfg
from mjlab.sim import MujocoCfg, SimulationCfg
from mjlab.terrains import TerrainEntityCfg
from mjlab.viewer import ViewerConfig

from picklebot_mj import court
from picklebot_mj.ball import BALL_RADIUS
from picklebot_mj.ball_sim import PADDLE_HALF, BallSim, BallState, PaddleState

CONTACT_X = -5.5  # swing intercept, near court (court-local x)
CONTACT_Z = 0.9
EPISODE_S = 3.0
FOLLOW_THROUGH = 0.12  # s the paddle keeps moving after the intercept
WIND_UP = 0.15  # s of swing before the intercept (the paddle waits at the wind-up point until then)


def _ball_spec() -> mujoco.MjSpec:
    spec = mujoco.MjSpec()
    b = spec.worldbody.add_body(name="ball", mocap=True)
    b.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[BALL_RADIUS, 0, 0], rgba=[0.95, 0.85, 0.1, 1],
               contype=0, conaffinity=0)
    return spec


def _paddle_spec() -> mujoco.MjSpec:
    spec = mujoco.MjSpec()
    b = spec.worldbody.add_body(name="paddle", mocap=True)
    b.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=list(PADDLE_HALF), rgba=[0.1, 0.3, 0.8, 1],
               contype=0, conaffinity=0)
    b.add_geom(type=mujoco.mjtGeom.mjGEOM_CAPSULE, size=[0.015, 0.0635, 0],
               pos=[0, -PADDLE_HALF[1] - 0.0635, 0], quat=[0.7071068, 0.7071068, 0, 0],
               rgba=[0.2, 0.2, 0.2, 1], contype=0, conaffinity=0)
    return spec


def _court_spec() -> mujoco.MjSpec:
    return court.court_entity_spec()


def ball_obs(env: "PickleballRigEnv") -> torch.Tensor:
    return torch.cat([env.ball.pos, env.ball.vel], dim=-1)


def rig_env_cfg(num_envs: int = 64, physics_dt: float = 0.005, decimation: int = 4) -> ManagerBasedRlEnvCfg:
    return ManagerBasedRlEnvCfg(
        scene=SceneCfg(
            terrain=TerrainEntityCfg(terrain_type="plane"),
            entities={
                "court": EntityCfg(spec_fn=_court_spec),
                "ball": EntityCfg(spec_fn=_ball_spec),
                "paddle": EntityCfg(spec_fn=_paddle_spec),
            },
            num_envs=num_envs,
            env_spacing=20.0,
        ),
        observations={"actor": ObservationGroupCfg({"ball": ObservationTermCfg(func=ball_obs)})},
        actions={},
        events={},
        rewards={},
        terminations={"time_out": TerminationTermCfg(func=time_out, time_out=True)},
        viewer=ViewerConfig(origin_type=ViewerConfig.OriginType.ASSET_BODY, entity_name="court", body_name="court",
                            distance=10.0, elevation=-12.0, azimuth=60.0, width=960, height=540,
                            max_extra_envs=0,
                            geom_group=(1, 1, 1, 1, 0, 0)),  # group 3 = court markings
        sim=SimulationCfg(mujoco=MujocoCfg(timestep=physics_dt)),
        decimation=decimation,
        episode_length_s=EPISODE_S,
    )


def _axis_angle_quat(axis, angle: torch.Tensor) -> torch.Tensor:
    a = torch.as_tensor(axis, dtype=angle.dtype, device=angle.device)
    return torch.cat([torch.cos(angle / 2).unsqueeze(-1), torch.sin(angle / 2).unsqueeze(-1) * a], dim=-1)


def _quat_to_matrix(q: torch.Tensor) -> torch.Tensor:
    w, x, y, z = q.unbind(-1)
    return torch.stack([
        1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y),
        2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x),
        2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], dim=-1).reshape(*q.shape[:-1], 3, 3)


class PickleballRigEnv(ManagerBasedRlEnv):
    """mjlab env whose physics step also advances the analytic ball against a scripted paddle."""

    def __init__(self, cfg: ManagerBasedRlEnvCfg, device: str, seed: int = 0, **kwargs):
        n = cfg.scene.num_envs
        self.ball_sim = BallSim()
        self.gen = torch.Generator(device=device).manual_seed(seed)
        z = torch.zeros(n, 3, device=device)
        self.ball = BallState(z.clone(), z.clone(), z.clone())
        self.t = torch.zeros(n, device=device)
        self.swing_c = z.clone()  # intercept point (court-local)
        self.swing_v = z.clone()  # paddle velocity
        self.swing_t = torch.zeros(n, device=device)  # time of intercept
        self.paddle_quat = torch.zeros(n, 4, device=device)
        self.hit = torch.zeros(n, dtype=torch.bool, device=device)
        self.landed = torch.zeros(n, dtype=torch.bool, device=device)
        self.landing = torch.full((n, 3), float("nan"), device=device)
        self.net_touch = torch.zeros(n, dtype=torch.bool, device=device)
        self.reaction = z.clone()
        self.finished: list[dict[str, torch.Tensor]] = []
        self._all_ids = torch.arange(n, device=device)
        super().__init__(cfg, device, **kwargs)
        self._mj_step = self.sim.step
        self.sim.step = self._physics_step

    # Scripted swing -------------------------------------------------------
    def _paddle_state(self, t: torch.Tensor) -> PaddleState:
        """Hold at the wind-up point, swing at constant velocity from WIND_UP s before the
        intercept to FOLLOW_THROUGH s after it, then hold."""
        n = t.shape[0]
        start, end = self.swing_t - WIND_UP, self.swing_t + FOLLOW_THROUGH
        moving = ((t >= start) & (t < end)).unsqueeze(-1)
        te = torch.minimum(torch.maximum(t, start), end)
        pos = self.swing_c + self.swing_v * (te - self.swing_t).unsqueeze(-1)
        rot = _quat_to_matrix(self.paddle_quat)
        vel = torch.where(moving, self.swing_v, torch.zeros_like(self.swing_v))
        return PaddleState(pos, rot, vel, torch.zeros(n, 3, device=t.device))

    def _sample(self, env_ids: torch.Tensor):
        k = len(env_ids)
        dev = self.device
        u = lambda lo, hi: lo + (hi - lo) * torch.rand(k, generator=self.gen, device=dev)
        speed, alpha = u(7.0, 9.0), torch.deg2rad(u(30.0, 40.0))
        toss = u(0.5, 0.8)
        y = u(-0.4, 0.4)
        d = torch.stack([torch.cos(alpha), torch.zeros_like(alpha), torch.sin(alpha)], -1)
        c = torch.stack([torch.full_like(y, CONTACT_X), y, torch.full_like(y, CONTACT_Z)], -1)
        # Face normal along the swing direction: rotate local z about y by (90 deg - alpha).
        self.paddle_quat[env_ids] = _axis_angle_quat([0.0, 1.0, 0.0], math.pi / 2 - alpha)
        self.swing_c[env_ids], self.swing_v[env_ids] = c, d * speed.unsqueeze(-1)
        # Ball dropped from rest above the intercept; it meets the face after ~sqrt(2 h / g).
        gap = BALL_RADIUS + PADDLE_HALF[2]
        self.swing_t[env_ids] = torch.sqrt(2 * toss / 9.81)
        self.ball.pos[env_ids] = c + d * gap + torch.stack([torch.zeros_like(toss), torch.zeros_like(toss), toss], -1)
        self.ball.vel[env_ids] = 0.0
        self.ball.spin[env_ids] = 0.0
        self.t[env_ids] = 0.0
        for buf in (self.hit, self.landed, self.net_touch):
            buf[env_ids] = False
        self.landing[env_ids] = float("nan")
        self.reaction[env_ids] = 0.0

    def _reset_idx(self, env_ids=None):
        if env_ids is None:
            env_ids = torch.arange(self.num_envs, device=self.device)
        if self.common_step_counter > 0 and len(env_ids):
            self.finished.append({"hit": self.hit[env_ids].clone(), "landed": self.landed[env_ids].clone(),
                                  "landing": self.landing[env_ids].clone(), "net": self.net_touch[env_ids].clone()})
        super()._reset_idx(env_ids)
        self._sample(env_ids)
        self._write_poses(env_ids)

    # Physics hook ---------------------------------------------------------
    def _physics_step(self):
        self._mj_step()
        dt = self.physics_dt
        paddle = self._paddle_state(self.t)
        self.ball, ev = self.ball_sim.step(self.ball, dt, 1, paddle)
        self.t += dt
        self.hit |= ev.paddle_contact
        self.reaction += ev.paddle_impulse
        self.net_touch |= ev.net_contact
        first_land = self.hit & ~self.landed & ev.court_contact
        self.landing = torch.where(first_land.unsqueeze(-1), ev.court_point, self.landing)
        self.landed |= first_land
        self._write_poses(None)

    def _write_poses(self, env_ids):
        if env_ids is None:
            env_ids = self._all_ids
        ids = env_ids
        origins = self.scene.env_origins[ids]
        ident = torch.zeros_like(self.paddle_quat[ids]); ident[:, 0] = 1.0
        pad_pos = self._paddle_state(self.t).pos
        self.scene["ball"].write_mocap_pose_to_sim(torch.cat([self.ball.pos[ids] + origins, ident], -1), env_ids=env_ids)
        self.scene["paddle"].write_mocap_pose_to_sim(torch.cat([pad_pos[ids] + origins, self.paddle_quat[ids]], -1), env_ids=env_ids)
        self.scene["court"].write_mocap_pose_to_sim(torch.cat([origins, ident], -1), env_ids=env_ids)

    def outcome_summary(self) -> dict:
        if not self.finished:
            return {}
        cat = {k: torch.cat([f[k] for f in self.finished]) for k in self.finished[0]}
        land = cat["landing"]
        in_far = cat["landed"] & (land[:, 0] > 0) & (land[:, 0] <= court.HALF_LENGTH) & (land[:, 1].abs() <= court.HALF_WIDTH)
        lx = land[cat["landed"], 0]
        return {
            "episodes": int(cat["hit"].numel()),
            "paddle_hit_rate": float(cat["hit"].float().mean()),
            "landed_rate": float(cat["landed"].float().mean()),
            "in_far_court_rate": float(in_far.float().mean()),
            "net_touch_rate": float(cat["net"].float().mean()),
            "landing_x_mean": float(lx.mean()) if lx.numel() else float("nan"),
            "landing_x_min": float(lx.min()) if lx.numel() else float("nan"),
            "landing_x_max": float(lx.max()) if lx.numel() else float("nan"),
        }
