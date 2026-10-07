"""Stage 5B tracking teacher: mjlab's G1 motion tracking (BeyondMimic-style) on the paddle G1 and many clips.

Differences from `Mjlab-Tracking-Flat-Unitree-G1`:
- the robot is the paddle G1, and the paddle face collides (with the body, the left arm and the floor), on top of the
  G1's full self-collision, so poses the retargeting could not make collision-free cost tracking error instead of
  passing through (results/stage5b-penetration.md);
- the motion file holds many clips back to back (scripts/motion/csv_to_npz_local.py writes `clip_starts`), and the
  multi-clip command never plays across a clip boundary: reaching the end of a clip resamples, as the stock command
  does at the end of its single motion. Adaptive sampling still works on the whole timeline.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, fields

import numpy as np
import torch
from mjlab.tasks.tracking.config.g1.env_cfgs import unitree_g1_flat_tracking_env_cfg
from mjlab.tasks.tracking.mdp import MotionCommandCfg
from mjlab.tasks.tracking.mdp.commands import MotionCommand
from mjlab.utils.spec_config import CollisionCfg

from picklebot_mj.g1_paddle import get_g1_paddle_cfg

# Joint order of the retargeted CSVs (GMR's G1 = mjlab's csv_to_npz order).
GMR_JOINTS = [
    "left_hip_pitch_joint", "left_hip_roll_joint", "left_hip_yaw_joint", "left_knee_joint", "left_ankle_pitch_joint",
    "left_ankle_roll_joint", "right_hip_pitch_joint", "right_hip_roll_joint", "right_hip_yaw_joint",
    "right_knee_joint", "right_ankle_pitch_joint", "right_ankle_roll_joint", "waist_yaw_joint", "waist_roll_joint",
    "waist_pitch_joint", "left_shoulder_pitch_joint", "left_shoulder_roll_joint", "left_shoulder_yaw_joint",
    "left_elbow_joint", "left_wrist_roll_joint", "left_wrist_pitch_joint", "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint", "right_shoulder_roll_joint", "right_shoulder_yaw_joint", "right_elbow_joint",
    "right_wrist_roll_joint", "right_wrist_pitch_joint", "right_wrist_yaw_joint",
]

# Applied after the G1's FULL_COLLISION (which zeroes every geom not named *_collision): turn the paddle face back on.
PADDLE_FACE_COLLISION = CollisionCfg(geom_names_expr=(r"^paddle_face$",), contype=1, conaffinity=1, condim=1,
                                     priority=0, disable_other_geoms=False)


def paddle_robot_cfg_collidable():
    cfg = copy.copy(get_g1_paddle_cfg())
    cfg.collisions = tuple(cfg.collisions) + (PADDLE_FACE_COLLISION,)
    return cfg


class MultiClipMotionCommand(MotionCommand):
    cfg: "MultiClipMotionCommandCfg"

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        data = np.load(cfg.motion_file)
        starts = data["clip_starts"] if "clip_starts" in data else np.array([0])
        total = self.motion.time_step_total
        self.clip_starts = torch.tensor(starts, dtype=torch.long, device=self.device)
        self.clip_ends = torch.tensor(np.r_[starts[1:], total], dtype=torch.long, device=self.device)
        self.clip_names = [str(n) for n in data["clip_names"]] if "clip_names" in data else ["motion"]
        self.clip_end = torch.full((self.num_envs,), total, dtype=torch.long, device=self.device)
        self.clip_index = torch.zeros(self.num_envs, dtype=torch.long, device=self.device)
        self.clip_end[:] = self._end_of(self.time_steps)

    def clip_of(self, t: torch.Tensor) -> torch.Tensor:
        return torch.searchsorted(self.clip_starts, t, right=True) - 1

    def _end_of(self, t: torch.Tensor) -> torch.Tensor:
        return self.clip_ends[self.clip_of(t)]

    def _resample_command(self, env_ids: torch.Tensor):
        super()._resample_command(env_ids)
        if self.cfg.sampling_mode == "start" and self.cfg.play_clip is not None:
            # Play/eval: start a named clip from its first frame (no randomisation in play mode).
            self.time_steps[env_ids] = self.clip_starts[self.cfg.play_clip]
            self._write_reference_state_to_sim(
                env_ids, self.body_pos_w[env_ids, 0].clone(), self.body_quat_w[env_ids, 0].clone(),
                self.body_lin_vel_w[env_ids, 0].clone(), self.body_ang_vel_w[env_ids, 0].clone(),
                self.joint_pos[env_ids].clone(), self.joint_vel[env_ids].clone())
        # A sample on a clip's last frame would play straight into the next clip; step it back one frame.
        last = self.time_steps[env_ids] >= self._end_of(self.time_steps[env_ids]) - 1
        self.time_steps[env_ids] = torch.where(last, self.time_steps[env_ids] - 1, self.time_steps[env_ids])
        self.clip_index[env_ids] = self.clip_of(self.time_steps[env_ids])
        self.clip_end[env_ids] = self.clip_ends[self.clip_index[env_ids]]

    def _update_command(self, env_ids: torch.Tensor | None = None):
        # As MotionCommand._update_command, but wrapping at the end of each env's clip, not of the whole file.
        if env_ids is None:
            self.time_steps += 1
        else:
            self.time_steps[env_ids] += 1
        wrap_ids = torch.where(self.time_steps >= self.clip_end)[0]
        if wrap_ids.numel() > 0:
            self._resample_command(wrap_ids)
        if self._pending_forward:
            self._pending_forward = False
            self._env.sim.forward()
        self.update_relative_body_poses()
        if env_ids is None and self.cfg.sampling_mode == "adaptive":
            self.bin_failed_count = (self.cfg.adaptive_alpha * self._current_bin_failed
                                     + (1 - self.cfg.adaptive_alpha) * self.bin_failed_count)
            self._current_bin_failed.zero_()


@dataclass(kw_only=True)
class MultiClipMotionCommandCfg(MotionCommandCfg):
    play_clip: int | None = None  # play mode ("start" sampling): which clip to start

    def build(self, env):
        return MultiClipMotionCommand(self, env)


def paddle_tracking_env_cfg(motion_file: str, play: bool = False, play_clip: int | None = None):
    cfg = unitree_g1_flat_tracking_env_cfg(play=play)
    cfg.scene.entities = {"robot": paddle_robot_cfg_collidable()}
    old = cfg.commands["motion"]
    kw = {f.name: getattr(old, f.name) for f in fields(old) if f.init}
    kw["motion_file"] = motion_file
    cfg.commands["motion"] = MultiClipMotionCommandCfg(**kw, play_clip=play_clip)
    return cfg
