"""Footwork specialist (footwork phase step 1, D-179): a flat joint-space walking teacher built for speed.

Registered when this module is imported (scripts/diag/footwork_train.py); picklebot_mj/tasks/__init__.py does not import
it, so nothing here reaches other runs. Built from a deep copy of the flat walking teacher's task
(Picklebot-Teacher-Move-G1, whose model_15900 is the warm start), observations unchanged.

Why the walking teacher cannot run (bodyspeed54 VOID: forward sustained 1.06 m/s at a 2.5 m/s command; D-179):
1. move_track_lin_vel scores the internal command with exp(-|v_cmd - v|^2 / 0.5^2): at a 2.5 m/s command and 1.0 m/s the
   reward is exp(-9) ~ 1e-4, so there is no gradient toward the faster speed.
2. `pose` (mjlab variable_posture) picks its standing / walking / running tolerance from the *twist command*, which the
   picklebot tasks hold at zero (the move command is internal), so every step is scored with the standing tolerance.
The specialist fixes both and changes the drill:
- FootworkDrill (a DeadlineMoveDrill, first-entry deadline arrival): spots 1-5 m away in the 8 sectors inside the
  widened Fast25 box (court + runoff), deadline 0.3 s + d / v_req with v_req ~ U(1.2, 2.2) m/s (the move_arrival bonus
  pays only in time), untimed limit as MoveDrill. Internal command toward the spot at min(CMD_CAP, k d), CMD_CAP 2.5 m/s,
  k = 1.2 CMD_CAP (braking radius 0.83 m, as the deadline drill); heading free beyond 1 m of the spot (turn-and-run,
  crossovers), toward the net inside it. The policy never observes the command (only the spot), as before.
- fw_track_lin_vel: the same kernel with std = 0.5 max(1, |v_cmd|) m/s.
- fw_posture: variable_posture with the regime chosen from the drill's internal command (|v_cmd| + |w_z|).
- 20 s episodes (8 s would censor long spots).
- Instrument (as tasks/body_speed.py): per spot the best 1-s mean pelvis ground speed toward the spot, booked when the
  spot resolves; histogram per sector. Its counters use bodyspeed_rule's keys, so the same coded rule reads them.
Style arm (TASK_FW_STYLE): plus an AMP-style discriminator reward (picklebot_mj/style.py, weight 0.5, wrists excluded as
Drill3-Style-NoWrist) against LAFAN1 (original + mirrored) and the AMASS-G1 lateral / backward footwork clips
(artifacts/motion/tracking/amass-footwork.npz; selection in scripts/motion/amass_footwork_npz.sh).
Measure task (TASK_FW_MEASURE): the specialist task with spots 3-5 m away (long enough for a 1-s sustained window at
speed), read at learning rate 0.
"""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from pathlib import Path

import torch
from mjlab.managers.reward_manager import RewardTermCfg
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls, register_mjlab_task
from mjlab.tasks.velocity.mdp import rewards as vr

from picklebot_mj.tasks import agility as ag
from picklebot_mj.tasks import deadline_drill as dd
from picklebot_mj.tasks import move_drill as md

TASK_FW = "Picklebot-Footwork-Specialist-G1"
TASK_FW_STYLE = "Picklebot-Footwork-Specialist-Style-G1"
TASK_FW_MEASURE = "Picklebot-Footwork-Measure-G1"
CMD_CAP = 2.5  # m/s
V_REQ = (1.2, 2.2)  # deadline speed, m/s
DIST = (1.0, 5.0)
MEASURE_DIST = (3.0, 5.0)
SPOT_BOX = ag.FAST25["move_spot_box"]  # ((-10.4, -2.4), (-5.5, 5.5)): court + runoff
EPISODE_S = 20.0
TRACK_STD = 0.5
STYLE_WEIGHT = 0.5
WINDOW_S = 1.0
SPEED_BIN, SPEED_BINS = 0.1, 50  # m/s (last bin: >= 4.9 m/s), as tasks/body_speed.py
_MOTION_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "motion" / "tracking"
STYLE_FILES = ("lafan-g1.npz", "lafan-g1-mirror.npz", "amass-footwork.npz")


class FootworkDrill(dd.DeadlineMoveDrill):
    def __init__(self, term, move_prob: float, seed: int, sector_weights=None, dist_range=DIST, v_req_range=V_REQ,
                 heading_free_m: float = dd.HEADING_FREE_M, cmd_cap: float = CMD_CAP, spot_box=SPOT_BOX):
        super().__init__(term, move_prob, seed, sector_weights, dist_range=dist_range, v_req_range=v_req_range,
                         heading_free_m=heading_free_m, arrival_mode="first_entry")
        n, dev = self.n, self.dev
        self.cap = float(cmd_cap)
        self.gain = md.CMD_GAIN * self.cap / md.CMD_MAX_SPEED
        self._lo = torch.tensor([spot_box[0][0], spot_box[1][0]], dtype=torch.float32, device=dev)
        self._hi = torch.tensor([spot_box[0][1], spot_box[1][1]], dtype=torch.float32, device=dev)
        env = getattr(term, "_env", None)
        self.decimation = int(getattr(getattr(env, "cfg", None), "decimation", 1)) if env is not None else 1
        dt = float(getattr(env, "physics_dt", 0.005)) if env is not None else 0.005
        self.K = max(1, int(round(WINDOW_S / (dt * self.decimation))))
        self.buf, self.wsum = torch.zeros(n, self.K, device=dev), torch.zeros(n, device=dev)
        self.cnt = torch.zeros(n, dtype=torch.long, device=dev)
        self.best = torch.full((n,), -1e3, device=dev)
        self.live = torch.zeros(n, dtype=torch.bool, device=dev)  # a spot is in progress (booked when it resolves)
        self.stats["booked"] = torch.zeros(md.N_SECTORS, dtype=torch.long, device=dev)
        self.best_hist = torch.zeros(md.N_SECTORS, SPEED_BINS, dtype=torch.long, device=dev)
        self.best_sum = torch.zeros(md.N_SECTORS, device=dev)
        self._ar = torch.arange(n, device=dev)
        self._calls = 0

    def reset(self, env_ids: torch.Tensor) -> None:
        self.live[env_ids] = False  # a spot cut by the episode end is counted (fell / censored) by DeadlineMoveDrill
        super().reset(env_ids)

    def _new_spot(self, mask: torch.Tensor) -> None:
        """Book the resolved spot's sustained speed, then DeadlineMoveDrill._new_spot; the instrument restarts."""
        b = mask & self.live & self.move_ep
        sec = self.sector
        self.stats["booked"].index_add_(0, sec, b.long())
        best = self.best.clamp(min=0.0).nan_to_num(0.0)
        k = (best / SPEED_BIN).clamp(0, SPEED_BINS - 1).long()
        self.best_hist.view(-1).index_add_(0, sec * SPEED_BINS + k, b.long())
        self.best_sum.index_add_(0, sec, best * b.float())
        super()._new_spot(mask)
        m = mask.unsqueeze(-1)
        self.buf = torch.where(m, torch.zeros_like(self.buf), self.buf)
        self.wsum = torch.where(mask, torch.zeros_like(self.wsum), self.wsum)
        self.cnt = torch.where(mask, torch.zeros_like(self.cnt), self.cnt)
        self.best = torch.where(mask, torch.full_like(self.best, -1e3), self.best)
        self.live = self.live | (mask & self.move_ep)

    def update(self, dt: float) -> None:
        """Once per control step: the 1-s running mean of pelvis ground velocity toward the spot; then the drill."""
        if self._calls % self.decimation == 0:
            t = self.t
            mv = self.move_ep & self.live
            v = t._entity.data.root_link_lin_vel_w[:, :2]
            to = t.recover_xy - t.pelvis_xy()
            vt = (v * to / to.norm(dim=-1, keepdim=True).clamp(min=1e-6)).sum(-1)
            pos = self.cnt % self.K
            old = self.buf[self._ar, pos]
            self.buf[self._ar, pos] = torch.where(mv, vt, old)
            self.wsum = self.wsum + torch.where(mv, vt - old, torch.zeros_like(vt))
            self.cnt = self.cnt + mv.long()
            mean = self.wsum / self.cnt.clamp(min=1, max=self.K).float()
            self.best = torch.where(mv, torch.maximum(self.best, mean), self.best)
        self._calls += 1
        super().update(dt)

    def command(self):
        """DeadlineMoveDrill's law with a fixed cap CMD_CAP (not v_req): the policy cannot see v_req, so the command
        asks for the cap and the deadline sets only when the bonus pays. Heading free beyond heading_free_m."""
        t, robot = self.t, self.t._entity
        yaw = md._yaw(robot.data.root_link_pose_w[:, 3:7])
        delta = t.recover_xy - t.pelvis_xy()
        d = delta.norm(dim=-1, keepdim=True)
        v_w = delta / d.clamp(min=1e-6) * (self.gain * d).clamp(max=self.cap)
        c, s = torch.cos(yaw), torch.sin(yaw)
        v_b = torch.stack([c * v_w[:, 0] + s * v_w[:, 1], -s * v_w[:, 0] + c * v_w[:, 1]], -1)
        heading_err = torch.atan2(torch.sin(-yaw), torch.cos(-yaw))
        wz = (md.HEADING_STIFFNESS * heading_err).clamp(-md.CMD_MAX_YAW_RATE, md.CMD_MAX_YAW_RATE)
        wz = torch.where(d.squeeze(-1) > self.heading_free_m, torch.zeros_like(wz), wz)
        return v_b, wz

    def counters(self) -> dict:
        out = super().counters()
        out["best_hist"] = self.best_hist.tolist()
        out["best_sum"] = [round(x, 4) for x in self.best_sum.tolist()]
        return out


# ----------------------------------------------------------------------------------------
@dataclass(kw_only=True)
class FootworkBallActionCfg(ag.AgilityBallActionCfg):
    footwork_drill: bool = True
    footwork_dist: tuple = DIST

    def build(self, env) -> "FootworkBallAction":
        return FootworkBallAction(self, env)


class FootworkBallAction(ag.AgilityBallAction):
    cfg: FootworkBallActionCfg

    def __init__(self, cfg: FootworkBallActionCfg, env):
        super().__init__(cfg, env)  # deadline_drill=True builds a DeadlineMoveDrill (and the training log); replaced here
        if cfg.footwork_drill:
            self.drill = FootworkDrill(self, cfg.move_prob, cfg.seed, cfg.move_sector_weights,
                                       dist_range=cfg.footwork_dist, v_req_range=cfg.deadline_v_req,
                                       heading_free_m=cfg.heading_free_m)


def fw_track_lin_vel(env, std: float = TRACK_STD) -> torch.Tensor:
    """move_track_lin_vel with a speed-scaled kernel: std = std * max(1, |v_cmd| / 1 m/s)."""
    dr = md._drill(env)
    if dr is None:
        return torch.zeros(env.num_envs, device=env.device)
    v_cmd, _ = dr.command()
    v = dr.t._entity.data.root_link_lin_vel_b[:, :2]
    s = std * v_cmd.norm(dim=-1).clamp(min=1.0)
    return torch.exp(-((v_cmd - v) ** 2).sum(-1) / s ** 2) * md._walk_mask(dr)


class fw_posture(vr.variable_posture):
    """mjlab variable_posture, with the speed regime read from the move drill's internal command instead of the
    (always zero) twist command. Same per-joint stds, thresholds and formula."""

    def __call__(self, env, std_standing, std_walking, std_running, asset_cfg, command_name=None,
                 walking_threshold: float = 0.5, running_threshold: float = 1.5) -> torch.Tensor:
        dr = md._drill(env)
        asset = env.scene[asset_cfg.name]
        if dr is None:
            total = torch.zeros(env.num_envs, device=env.device)
        else:
            v_cmd, wz = dr.command()
            total = v_cmd.norm(dim=-1) + wz.abs()
        standing = (total < walking_threshold).float().unsqueeze(1)
        walking = ((total >= walking_threshold) & (total < running_threshold)).float().unsqueeze(1)
        running = (total >= running_threshold).float().unsqueeze(1)
        std = self.std_standing * standing + self.std_walking * walking + self.std_running * running
        err = torch.square(asset.data.joint_pos[:, asset_cfg.joint_ids] - self.default_joint_pos[:, asset_cfg.joint_ids])
        return torch.exp(-torch.mean(err / std ** 2, dim=1))


def footwork_task(cfg, dist=DIST):
    """The walking teacher's task -> the footwork specialist (module docstring)."""
    ag.deadline_task(cfg)  # move-only deadline drill, free-heading yaw reward
    b = cfg.actions["ball"]
    vals = {f.name: getattr(b, f.name) for f in dataclasses.fields(b) if f.init}
    vals.update(deadline_arrival_mode="first_entry", deadline_v_req=V_REQ, deadline_dist=dist, footwork_dist=dist,
                move_spot_box=SPOT_BOX)
    cfg.actions["ball"] = FootworkBallActionCfg(**vals)
    r = cfg.rewards
    assert r["move_track_lin_vel"].func is md.move_track_lin_vel and r["pose"].func is vr.variable_posture
    r["move_track_lin_vel"] = dataclasses.replace(r["move_track_lin_vel"], func=fw_track_lin_vel)
    r["pose"] = dataclasses.replace(r["pose"], func=fw_posture)
    cfg.episode_length_s = max(cfg.episode_length_s, EPISODE_S)
    return cfg


def with_style(cfg):
    from picklebot_mj.style import StyleCfg, style_reward
    style = StyleCfg(motion_files=tuple(str(_MOTION_DIR / f) for f in STYLE_FILES),
                     save_path=os.environ.get("PICKLEBOT_STYLE_SAVE"), load_path=os.environ.get("PICKLEBOT_STYLE_LOAD"),
                     exclude_joints=(r".*_wrist_(roll|pitch|yaw)_joint",))
    cfg.rewards["style"] = RewardTermCfg(func=style_reward, weight=STYLE_WEIGHT, params={"cfg": style})
    return cfg


def _register(task_id: str, build):
    src = ag.SRC_TEACHER
    register_mjlab_task(task_id=task_id, env_cfg=build(load_env_cfg(src)), play_env_cfg=build(load_env_cfg(src, play=True)),
                        rl_cfg=load_rl_cfg(src), runner_cls=load_runner_cls(src))


_register(TASK_FW, footwork_task)
_register(TASK_FW_MEASURE, lambda c: footwork_task(c, dist=MEASURE_DIST))
if all((_MOTION_DIR / f).exists() for f in STYLE_FILES):  # the AMP arm needs the expert npz files (git-ignored data)
    _register(TASK_FW_STYLE, lambda c: with_style(footwork_task(c)))
