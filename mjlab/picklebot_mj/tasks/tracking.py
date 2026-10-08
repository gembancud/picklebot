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
import math
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
        # Per-source sampling shares (H0): bins are grouped by the source of their clip; the adaptive (failure-weighted)
        # distribution is renormalised within each source, then scaled to that source's share.
        self.bin_source = None
        if cfg.source_shares is not None and "clip_source" in data:
            src_of_clip = torch.tensor(data["clip_source"], dtype=torch.long, device=self.device)
            centre = ((torch.arange(self.bin_count, device=self.device) + 0.5) / self.bin_count
                      * (total - 1)).long()
            self.bin_source = src_of_clip[self.clip_of(centre)]
            self.source_shares = torch.tensor(cfg.source_shares, dtype=torch.float, device=self.device)
            assert len(self.source_shares) == int(src_of_clip.max()) + 1

    def clip_of(self, t: torch.Tensor) -> torch.Tensor:
        return torch.searchsorted(self.clip_starts, t, right=True) - 1

    def _end_of(self, t: torch.Tensor) -> torch.Tensor:
        return self.clip_ends[self.clip_of(t)]

    def start_clips(self, env_ids: torch.Tensor, clip_ids: torch.Tensor):
        """Put envs at the first frame of the given clips, robot on the reference (play / per-clip evaluation)."""
        self.start_at(env_ids, self.clip_starts[clip_ids])

    def start_at(self, env_ids: torch.Tensor, frames: torch.Tensor):
        """Put envs at the given global frames (e.g. a stroke segment's start), robot on the reference."""
        self.time_steps[env_ids] = frames
        self._write_reference_state_to_sim(
            env_ids, self.body_pos_w[env_ids, 0].clone(), self.body_quat_w[env_ids, 0].clone(),
            self.body_lin_vel_w[env_ids, 0].clone(), self.body_ang_vel_w[env_ids, 0].clone(),
            self.joint_pos[env_ids].clone(), self.joint_vel[env_ids].clone())
        self.clip_index[env_ids] = self.clip_of(frames)
        self.clip_end[env_ids] = self.clip_ends[self.clip_index[env_ids]]
        self._pending_forward = True

    def _resample_command(self, env_ids: torch.Tensor):
        super()._resample_command(env_ids)
        if self.cfg.sampling_mode == "start" and self.cfg.play_clip is not None:
            # Play: start a named clip from its first frame (no randomisation in play mode).
            self.start_clips(env_ids, torch.full_like(env_ids, self.cfg.play_clip))
            return
        # A sample on a clip's last frame would play straight into the next clip; step it back one frame.
        last = self.time_steps[env_ids] >= self._end_of(self.time_steps[env_ids]) - 1
        self.time_steps[env_ids] = torch.where(last, self.time_steps[env_ids] - 1, self.time_steps[env_ids])
        self.clip_index[env_ids] = self.clip_of(self.time_steps[env_ids])
        self.clip_end[env_ids] = self.clip_ends[self.clip_index[env_ids]]

    def _adaptive_sampling(self, env_ids: torch.Tensor):
        if self.bin_source is None:
            return super()._adaptive_sampling(env_ids)
        # As MotionCommand._adaptive_sampling, with the per-source shares applied before sampling.
        episode_failed = self._env.termination_manager.terminated[env_ids]
        if torch.any(episode_failed):
            current_bin = torch.clamp((self.time_steps * self.bin_count) // max(self.motion.time_step_total, 1),
                                      0, self.bin_count - 1)
            self._current_bin_failed[:] = torch.bincount(current_bin[env_ids][episode_failed],
                                                         minlength=self.bin_count)
        p = self.bin_failed_count + self.cfg.adaptive_uniform_ratio / float(self.bin_count)
        p = torch.nn.functional.pad(p.view(1, 1, -1), (0, self.cfg.adaptive_kernel_size - 1), mode="replicate")
        p = torch.nn.functional.conv1d(p, self.kernel.view(1, 1, -1)).view(-1)
        q = torch.zeros_like(p)
        for k, share in enumerate(self.source_shares):
            m = self.bin_source == k
            q[m] = p[m] / p[m].sum() * share
        q = q / q.sum()
        bins = torch.multinomial(q, len(env_ids), replacement=True)
        self.time_steps[env_ids] = ((bins + torch.rand(len(env_ids), device=self.device)) / self.bin_count
                                    * (self.motion.time_step_total - 1)).long()
        h = -(q * (q + 1e-12).log()).sum()
        self.metrics["sampling_entropy"][:] = h / math.log(self.bin_count)
        pmax, imax = q.max(dim=0)
        self.metrics["sampling_top1_prob"][:] = pmax
        self.metrics["sampling_top1_bin"][:] = imax.float() / self.bin_count
        for k in range(len(self.source_shares)):
            self.metrics[f"sampling_share_src{k}"] = torch.full((self.num_envs,), float(q[self.bin_source == k].sum()),
                                                                device=self.device)

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
    source_shares: tuple[float, ...] | None = None  # sampling share per clip source (merged motion files)

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


# Stage 5B tracking follow-up 2 (rule 8; stage5b-tracking.md): motion preview. The policy also sees the reference
# joint positions PREVIEW_FRAMES ahead, as offsets from the current reference frame, clamped to the end of the env's
# clip. Fast strokes (serves, smashes) failed most with only the current frame in view.
PREVIEW_FRAMES = (5, 10)  # 0.1 s and 0.2 s at 50 Hz


def motion_preview_joint_pos(env, command_name: str = "motion", frames: tuple[int, ...] = PREVIEW_FRAMES):
    cmd = env.command_manager.get_term(command_name)
    now = cmd.motion.joint_pos[cmd.time_steps]
    out = []
    for k in frames:
        idx = torch.minimum(cmd.time_steps + k, cmd.clip_end - 1)
        out.append(cmd.motion.joint_pos[idx] - now)
    return torch.cat(out, dim=-1)


def add_motion_preview(cfg):
    """Append the preview term (trailing, so scripts/expand_checkpoint.py can widen a trained policy's inputs)."""
    from mjlab.managers.observation_manager import ObservationTermCfg

    for group in ("actor", "critic"):
        cfg.observations[group].terms["motion_preview"] = ObservationTermCfg(
            func=motion_preview_joint_pos, params={"command_name": "motion"})
    return cfg


# Per-stroke scoring (D-048): single-stroke segments around right-hand speed peaks. Fixed before evaluation.
SEG_PEAK_SPEED = 3.0  # m/s, right-hand speed a swing must reach
SEG_MIN_GAP_S = 1.0  # peaks closer than this are one swing (the higher one is kept)
SEG_BEFORE_S, SEG_AFTER_S = 1.5, 1.0  # segment window around the peak
SEG_MIN_LEN_S = 2.0  # windows clipped below this at a clip edge are dropped


def stroke_segments(hand_speed: np.ndarray, clip_starts: np.ndarray, total: int, fps: float):
    """[(clip_index, start_frame, end_frame_exclusive, peak_frame)] in global frames, one per swing."""
    ends = np.r_[clip_starts[1:], total]
    gap, before, after = int(SEG_MIN_GAP_S * fps), int(SEG_BEFORE_S * fps), int(SEG_AFTER_S * fps)
    out = []
    for c, (s0, s1) in enumerate(zip(clip_starts, ends)):
        v = hand_speed[s0:s1]
        cand = [i for i in range(1, len(v) - 1) if v[i] >= SEG_PEAK_SPEED and v[i] >= v[i - 1] and v[i] > v[i + 1]]
        peaks = []
        for i in sorted(cand, key=lambda i: -v[i]):  # greedy non-maximum suppression
            if all(abs(i - j) >= gap for j in peaks):
                peaks.append(i)
        for i in sorted(peaks):
            a, b = max(0, i - before), min(len(v), i + after)
            if b - a >= SEG_MIN_LEN_S * fps:
                out.append((c, s0 + a, s0 + b, s0 + i))
    return out
