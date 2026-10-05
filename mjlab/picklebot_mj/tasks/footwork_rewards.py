"""Stage 5 stance release: mjlab's foot-quality rewards gated on actual base motion.

mjlab's velocity task gates feet_clearance, feet_swing_height, feet_slip and soft_landing on the
*commanded* speed. The picklebot tasks keep that command at zero, so those terms were always off
(stage5-motion-audit.md). Here the same costs are gated on the robot's own base speed instead:
active when |v_xy| + |w_z| (body frame) exceeds `speed_threshold`, so steps taken to reach the
ball lift cleanly, do not slide and land softly, while standing still costs nothing.
"""

from __future__ import annotations

import torch

from mjlab.managers.scene_entity_config import SceneEntityCfg
from mjlab.tasks.velocity.mdp import rewards as vr

_ROBOT = SceneEntityCfg("robot")
SPEED_THRESHOLD = 0.1  # m/s (+ rad/s), matches the scale of mjlab's command thresholds (0.05)


def base_moving(env, speed_threshold: float = SPEED_THRESHOLD) -> torch.Tensor:
    robot = env.scene["robot"]
    v = robot.data.root_link_lin_vel_b[:, :2].norm(dim=-1) + robot.data.root_link_ang_vel_b[:, 2].abs()
    return (v > speed_threshold).float()


def feet_clearance_moving(env, target_height: float, height_sensor_name: str,
                          speed_threshold: float = SPEED_THRESHOLD, asset_cfg: SceneEntityCfg = _ROBOT):
    cost = vr.feet_clearance(env, target_height, height_sensor_name, command_name=None, asset_cfg=asset_cfg)
    return cost * base_moving(env, speed_threshold)


def soft_landing_moving(env, sensor_name: str, speed_threshold: float = SPEED_THRESHOLD):
    return vr.soft_landing(env, sensor_name, command_name=None) * base_moving(env, speed_threshold)


def feet_slip_moving(env, sensor_name: str, speed_threshold: float = SPEED_THRESHOLD,
                     asset_cfg: SceneEntityCfg = _ROBOT):
    """Foot xy speed squared while in contact (mjlab feet_slip), gated on base motion."""
    asset = env.scene[asset_cfg.name]
    contact = env.scene[sensor_name]
    in_contact = (contact.data.found > 0).float()
    vel = asset.data.site_lin_vel_w[:, asset_cfg.site_ids, :2].norm(dim=-1)
    return torch.sum(vel.square() * in_contact, dim=1) * base_moving(env, speed_threshold)


class feet_swing_height_moving(vr.feet_swing_height):
    """Peak swing height error at landing (mjlab feet_swing_height), gated on base motion."""

    def __call__(self, env, sensor_name: str, height_sensor_name: str, target_height: float,
                 speed_threshold: float = SPEED_THRESHOLD):
        contact = env.scene[sensor_name]
        heights = env.scene[height_sensor_name].data.heights
        in_air = contact.data.found == 0
        self.peak_heights = torch.where(in_air, torch.maximum(self.peak_heights, heights), self.peak_heights)
        first = contact.compute_first_contact(dt=self.step_dt)
        err = self.peak_heights / target_height - 1.0
        cost = torch.sum(err.square() * first.float(), dim=1) * base_moving(env, speed_threshold)
        self.peak_heights = torch.where(first, torch.zeros_like(self.peak_heights), self.peak_heights)
        return cost


GATED = {
    "foot_clearance": feet_clearance_moving,
    "foot_swing_height": feet_swing_height_moving,
    "foot_slip": feet_slip_moving,
    "soft_landing": soft_landing_moving,
}
