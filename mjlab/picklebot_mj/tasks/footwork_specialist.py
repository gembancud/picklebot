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
D-181 (panel round 51): fw1b-S ran through spots (first entry paid the bonus; nothing paid stopping). TASK_FW_SETTLE pays
move_arrival at the held arrival (MoveDrill's 0.25 m / 0.2 m/s / 0.3 s) of a spot whose first entry was before the
deadline, once; TASK_FW_MEASURE60 is the measure task with 60-s episodes (at 20 s even a perfect policy censors ~12-14 %
of 3-5 m spots, against the rule's 10 %). Instrument fix (all tasks): the sustained speed counts only full 1-s windows
(spots resolved sooner are counted as `short`, with no speed); new counters settled, settle_time_sum, overshoot_sum.
"""

from __future__ import annotations

import dataclasses
import math
import os
import re
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
TASK_FW_SETTLE = "Picklebot-Footwork-Specialist-Settle-G1"  # D-181: pay "settled"
TASK_FW_MEASURE60 = "Picklebot-Footwork-Measure60-G1"  # D-181: 60-s episodes, pay "settled" (read at rate 0)
PAY_MODES = ("entry", "settled")
MEASURE_EPISODE_S = 60.0
HEADING_BIN, HEADING_BINS = 10.0, 18  # degrees from facing the net, 0-180
FIRST_STEP_M, FIRST_BIN, FIRST_BINS = 1.5, 0.05, 80  # D-191 first-step metric: metres, seconds (last bin >= 3.95 s)
FIRST_PAY_T = 1.6  # D-221: the first-step bonus pays clamp((FIRST_PAY_T - first-step time) / span, 0, 1) (s)
FIRST_PAY_SPAN = 1.0  # D-221's span (s); D-222 (panel round 85): 0.5, saturating at 1.1 s
SAT_GROUPS = {"hip": r"_hip_", "knee": r"_knee_", "ankle": r"_ankle_", "waist": r"^waist_"}  # D-229
SAT_FRAC, SAT_WINDOW_S = 0.95, 1.0
STRONG_EFFORT_X = 2.0  # D-229: leg / waist / ankle effort limits x2 (the user: no realistic motor limits)
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
                 heading_free_m: float = dd.HEADING_FREE_M, cmd_cap: float = CMD_CAP, spot_box=SPOT_BOX,
                 pay: str = "entry", first_bonus: bool = False, first_span: float = FIRST_PAY_SPAN):
        super().__init__(term, move_prob, seed, sector_weights, dist_range=dist_range, v_req_range=v_req_range,
                         heading_free_m=heading_free_m, arrival_mode="first_entry")
        n, dev = self.n, self.dev
        assert pay in PAY_MODES, pay
        self.pay = pay
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
        for k in ("short", "settled"):  # short: resolved before a full 1-s window (no speed booked)
            self.stats[k] = torch.zeros(md.N_SECTORS, dtype=torch.long, device=dev)
        self.settle_time_sum = torch.zeros(md.N_SECTORS, device=dev)  # first entry -> held arrival, settled spots
        self.overshoot_sum = torch.zeros(md.N_SECTORS, device=dev)  # largest distance from the spot after entry
        self.entry_t = torch.zeros(n, device=dev)
        self.post_max = torch.zeros(n, device=dev)
        self._settled = torch.zeros(n, dtype=torch.bool, device=dev)
        # D-182 (coach, round 52): heading at mid-move, |pelvis yaw from facing the net| when the robot first gets
        # within half the spot's start distance; histogram per sector, HEADING_BIN-degree bins, booked at resolution
        self.d0 = torch.ones(n, device=dev)
        self.mid_done = torch.zeros(n, dtype=torch.bool, device=dev)
        self.mid_yaw = torch.zeros(n, device=dev)
        self.mid_hist = torch.zeros(md.N_SECTORS, HEADING_BINS, dtype=torch.long, device=dev)
        # D-191 (the user: agility, first-step quickness): time from the spot's issue until the pelvis is FIRST_STEP_M
        # closer to it, for spots at least that far away; histogram per sector, FIRST_BIN-s bins, booked at resolution
        self.first_t = torch.full((n,), -1.0, device=dev)
        self.first_hist = torch.zeros(md.N_SECTORS, FIRST_BINS, dtype=torch.long, device=dev)
        self._ar = torch.arange(n, device=dev)
        self._calls = 0
        # D-221 (panel round 84b, 5 of 5): the first-step bonus. Once per spot of at least FIRST_STEP_M, on the step its
        # first-step time is set, fw_first_step pays clamp(FIRST_PAY_T - t, 0, 1) (read-and-clear). Off by default.
        self.first_bonus = bool(first_bonus)
        self.first_span = float(first_span)
        self.first_now = torch.zeros(n, device=dev)
        self.first_pay_sum = torch.zeros(md.N_SECTORS, device=dev)
        # D-229 (reads only; PICKLEBOT_FW_SAT=1): actuator saturation in the first SAT_WINDOW_S of each move: per joint
        # group, [samples, samples with |qfrc_actuator| >= SAT_FRAC x the joint's effort limit], once per control step
        self.sat_on = os.environ.get("PICKLEBOT_FW_SAT") == "1"
        self.sat = torch.zeros(len(SAT_GROUPS), 2, dtype=torch.long, device=dev)
        self._sat_lim = None

    def reset(self, env_ids: torch.Tensor) -> None:
        self.live[env_ids] = False  # a spot cut by the episode end is counted (fell / censored) by DeadlineMoveDrill
        super().reset(env_ids)

    def _new_spot(self, mask: torch.Tensor) -> None:
        """Book the resolved spot (sustained speed if it ran a full 1-s window; settled = held arrival after an in-time
        first entry), then DeadlineMoveDrill._new_spot; the instrument restarts. Called before the drill clears
        `entered`, `hold` and `elapsed`; on the reset path `live` is already False, so nothing is booked or paid."""
        res = mask & self.live & self.move_ep
        sec = self.sector
        settled = res & self.entered & (self.hold >= md.ARRIVE_HOLD_S)
        self._settled = self._settled | settled
        self.stats["settled"].index_add_(0, sec, settled.long())
        self.settle_time_sum.index_add_(0, sec, (self.elapsed - self.entry_t) * settled.float())
        self.overshoot_sum.index_add_(0, sec, self.post_max * settled.float())
        full = self.cnt >= self.K
        b = res & full
        self.stats["short"].index_add_(0, sec, (res & ~full).long())
        self.stats["booked"].index_add_(0, sec, b.long())
        best = self.best.clamp(min=0.0).nan_to_num(0.0)
        k = (best / SPEED_BIN).clamp(0, SPEED_BINS - 1).long()
        self.best_hist.view(-1).index_add_(0, sec * SPEED_BINS + k, b.long())
        self.best_sum.index_add_(0, sec, best * b.float())
        h = (self.mid_yaw / HEADING_BIN).clamp(0, HEADING_BINS - 1).long()
        self.mid_hist.view(-1).index_add_(0, sec * HEADING_BINS + h, (res & self.mid_done).long())
        ft = (self.first_t / FIRST_BIN).clamp(0, FIRST_BINS - 1).long()
        self.first_hist.view(-1).index_add_(0, sec * FIRST_BINS + ft, (res & (self.first_t >= 0)).long())
        super()._new_spot(mask)
        m = mask.unsqueeze(-1)
        self.buf = torch.where(m, torch.zeros_like(self.buf), self.buf)
        self.wsum = torch.where(mask, torch.zeros_like(self.wsum), self.wsum)
        self.cnt = torch.where(mask, torch.zeros_like(self.cnt), self.cnt)
        self.best = torch.where(mask, torch.full_like(self.best, -1e3), self.best)
        self.post_max = torch.where(mask, torch.zeros_like(self.post_max), self.post_max)
        self.d0 = torch.where(mask, (self.t.recover_xy - self.t.pelvis_xy()).norm(dim=-1), self.d0)
        self.mid_done = self.mid_done & ~mask
        self.first_t = torch.where(mask, torch.full_like(self.first_t, -1.0), self.first_t)
        self.live = self.live | (mask & self.move_ep)

    def update(self, dt: float) -> None:
        """Once per control step: the 1-s running mean of pelvis ground velocity toward the spot (best kept only over
        full windows); then the drill. pay "settled": the bonus (arrive_now) is the held arrival of a spot first
        entered before its deadline, instead of the first entry."""
        t = self.t
        d = (t.recover_xy - t.pelvis_xy()).norm(dim=-1)
        self.post_max = torch.where(self.entered & self.live, torch.maximum(self.post_max, d), self.post_max)
        mid = self.move_ep & self.live & ~self.mid_done & (d <= 0.5 * self.d0)
        yaw = md._yaw(t._entity.data.root_link_pose_w[:, 3:7])
        self.mid_yaw = torch.where(mid, torch.atan2(torch.sin(yaw), torch.cos(yaw)).abs() * (180.0 / math.pi),
                                   self.mid_yaw)
        self.mid_done = self.mid_done | mid
        first = self.move_ep & self.live & (self.first_t < 0) & (self.d0 >= FIRST_STEP_M) & (self.d0 - d >= FIRST_STEP_M)
        self.first_t = torch.where(first, self.elapsed, self.first_t)
        if self.first_bonus:  # D-221
            pay = ((FIRST_PAY_T - self.elapsed) / self.first_span).clamp(0.0, 1.0) * first.float()
            self.first_now = self.first_now + pay
            self.first_pay_sum.index_add_(0, self.sector, pay)
        if self.sat_on and self._calls % self.decimation == 0:
            self._sat_step(t._entity)
        if self._calls % self.decimation == 0:
            mv = self.move_ep & self.live
            v = t._entity.data.root_link_lin_vel_w[:, :2]
            to = t.recover_xy - t.pelvis_xy()
            vt = (v * to / to.norm(dim=-1, keepdim=True).clamp(min=1e-6)).sum(-1)
            pos = self.cnt % self.K
            old = self.buf[self._ar, pos]
            self.buf[self._ar, pos] = torch.where(mv, vt, old)
            self.wsum = self.wsum + torch.where(mv, vt - old, torch.zeros_like(vt))
            self.cnt = self.cnt + mv.long()
            mean = self.wsum / self.K
            self.best = torch.where(mv & (self.cnt >= self.K), torch.maximum(self.best, mean), self.best)
        self._calls += 1
        was = self.entered.clone()
        keep = self.arrive_now.clone()  # read-and-clear by move_arrival once per control step
        self._settled = torch.zeros_like(self._settled)
        super().update(dt)
        new = self.entered & ~was
        self.entry_t = torch.where(new, self.elapsed, self.entry_t)
        if self.pay == "settled":
            self.arrive_now = keep | self._settled

    def _sat_step(self, robot) -> None:
        if self._sat_lim is None:  # per joint: effort limit and group index (from the entity's actuator configs)
            names = list(robot.joint_names)
            lim = torch.full((len(names),), float("inf"), device=self.dev)
            grp = torch.full((len(names),), -1, dtype=torch.long, device=self.dev)
            for a in robot.cfg.articulation.actuators:
                for i, nm in enumerate(names):
                    if a.effort_limit is not None and any(re.fullmatch(e, nm) for e in a.target_names_expr):
                        lim[i] = float(a.effort_limit)
            for g, rx in enumerate(SAT_GROUPS.values()):
                for i, nm in enumerate(names):
                    if re.search(rx, nm):
                        grp[i] = g
            self._sat_lim, self._sat_grp = lim, grp
        q = robot.data.qfrc_actuator
        q = q[:, -len(self._sat_lim):]  # joint dofs (a free root, if present, comes first)
        m = (self.move_ep & self.live & (self.elapsed < SAT_WINDOW_S)).unsqueeze(-1).expand_as(q)
        hit = (q.abs() >= SAT_FRAC * self._sat_lim) & m
        g = self._sat_grp.unsqueeze(0).expand_as(q)
        ok = g >= 0
        self.sat[:, 0].index_add_(0, g[m & ok], torch.ones_like(g[m & ok]))
        self.sat[:, 1].index_add_(0, g[hit & ok], torch.ones_like(g[hit & ok]))

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
        out["settle_time_sum"] = [round(x, 4) for x in self.settle_time_sum.tolist()]
        out["overshoot_sum"] = [round(x, 4) for x in self.overshoot_sum.tolist()]
        out["mid_heading_hist"] = self.mid_hist.tolist()
        out["mid_heading_bin_deg"] = HEADING_BIN
        out["first_step_hist"] = self.first_hist.tolist()
        out["first_step_bin_s"] = FIRST_BIN
        out["first_pay_sum"] = [round(x, 4) for x in self.first_pay_sum.tolist()]  # D-221 (zero when off)
        if self.sat_on:
            out["saturation"] = {k: self.sat[i].tolist() for i, k in enumerate(SAT_GROUPS)}  # D-229
        return out

    def summary(self) -> dict:
        """For scripts/stage2_eval.py (via scripts/diag/footwork_eval.py): DeadlineMoveDrill's summary plus the
        cumulative counters, which bodyspeed_rule reads."""
        out = super().summary()
        out["footwork"] = self.counters()
        return out


# ----------------------------------------------------------------------------------------
@dataclass(kw_only=True)
class FootworkBallActionCfg(ag.AgilityBallActionCfg):
    footwork_drill: bool = True
    footwork_dist: tuple = DIST
    footwork_pay: str = "entry"  # "settled" (D-181): the bonus pays the held arrival of an in-time first entry
    footwork_cmd_cap: float = CMD_CAP  # D-191: the internal command's speed cap (m/s)
    footwork_first_bonus: bool = False  # D-221: the first-step bonus (fw_first_step)
    footwork_first_span: float = FIRST_PAY_SPAN  # D-222: the bonus's pay span (s)

    def build(self, env) -> "FootworkBallAction":
        return FootworkBallAction(self, env)


class FootworkBallAction(ag.AgilityBallAction):
    cfg: FootworkBallActionCfg

    def __init__(self, cfg: FootworkBallActionCfg, env):
        super().__init__(cfg, env)  # deadline_drill=True builds a DeadlineMoveDrill (and the training log); replaced here
        if cfg.footwork_drill:
            self.drill = FootworkDrill(self, cfg.move_prob, cfg.seed, cfg.move_sector_weights,
                                       dist_range=cfg.footwork_dist, v_req_range=cfg.deadline_v_req,
                                       heading_free_m=cfg.heading_free_m, pay=cfg.footwork_pay,
                                       cmd_cap=cfg.footwork_cmd_cap, spot_box=cfg.move_spot_box or SPOT_BOX,
                                       first_bonus=cfg.footwork_first_bonus, first_span=cfg.footwork_first_span)


def fw_track_lin_vel(env, std: float = TRACK_STD) -> torch.Tensor:
    """move_track_lin_vel with a speed-scaled kernel: std = std * max(1, |v_cmd| / 1 m/s)."""
    dr = md._drill(env)
    if dr is None:
        return torch.zeros(env.num_envs, device=env.device)
    v_cmd, _ = dr.command()
    v = dr.t._entity.data.root_link_lin_vel_b[:, :2]
    s = std * v_cmd.norm(dim=-1).clamp(min=1.0)
    return torch.exp(-((v_cmd - v) ** 2).sum(-1) / s ** 2) * md._walk_mask(dr)


def fw_first_step(env) -> torch.Tensor:
    """D-221: the first-step bonus (FootworkDrill.first_now), read-and-clear once per control step."""
    dr = md._drill(env)
    if dr is None or not getattr(dr, "first_bonus", False):
        return torch.zeros(env.num_envs, device=env.device)
    r = dr.first_now.clone()
    dr.first_now.zero_()
    return r


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


def footwork_task(cfg, dist=DIST, pay="entry", episode_s=EPISODE_S, cmd_cap=CMD_CAP, v_req=V_REQ, spot_box=SPOT_BOX,
                  first_bonus=False, first_span=FIRST_PAY_SPAN):
    """The walking teacher's task -> the footwork specialist (module docstring)."""
    ag.deadline_task(cfg)  # move-only deadline drill, free-heading yaw reward
    b = cfg.actions["ball"]
    vals = {f.name: getattr(b, f.name) for f in dataclasses.fields(b) if f.init}
    vals.update(deadline_arrival_mode="first_entry", deadline_v_req=v_req, deadline_dist=dist, footwork_dist=dist,
                move_spot_box=spot_box, footwork_pay=pay, footwork_cmd_cap=cmd_cap, footwork_first_bonus=first_bonus,
                footwork_first_span=first_span)
    cfg.actions["ball"] = FootworkBallActionCfg(**vals)
    r = cfg.rewards
    assert r["move_track_lin_vel"].func is md.move_track_lin_vel and r["pose"].func is vr.variable_posture
    r["move_track_lin_vel"] = dataclasses.replace(r["move_track_lin_vel"], func=fw_track_lin_vel)
    r["pose"] = dataclasses.replace(r["pose"], func=fw_posture)
    if first_bonus:  # D-221: weighted as the arrival bonus
        r["fw_first_step"] = RewardTermCfg(func=fw_first_step, weight=r["move_arrival"].weight)
    cfg.episode_length_s = max(cfg.episode_length_s, episode_s)
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
_register(TASK_FW_SETTLE, lambda c: footwork_task(c, pay="settled"))
_register(TASK_FW_MEASURE60, lambda c: footwork_task(c, dist=MEASURE_DIST, pay="settled", episode_s=MEASURE_EPISODE_S))
if all((_MOTION_DIR / f).exists() for f in STYLE_FILES):  # the AMP arm needs the expert npz files (git-ignored data)
    _register(TASK_FW_STYLE, lambda c: with_style(footwork_task(c)))


# D-185 bridge (panel round 54): the current rally composite (lam_r 2 residual around RES_BASE; run 14's task, as the
# agility screen's arms A0 / A) read on the Measure60 drill: does the composite inherit the prior's travel cap? Only the
# ball term changes (move-only FootworkDrill, spots 3-5 m, 60-s episodes, pay "settled"); rewards are untouched (read only).
TASK_FW_RALLY_MEASURE = "Picklebot-Footwork-Measure60-RallyLamR2-G1"


def rally_measure(cfg):
    ag.deadline_task(cfg)
    b = cfg.actions["ball"]
    vals = {f.name: getattr(b, f.name) for f in dataclasses.fields(b) if f.init}
    vals.update(deadline_arrival_mode="first_entry", deadline_v_req=V_REQ, deadline_dist=MEASURE_DIST,
                footwork_dist=MEASURE_DIST, move_spot_box=SPOT_BOX, footwork_pay="settled")
    cfg.actions["ball"] = FootworkBallActionCfg(**vals)
    cfg.episode_length_s = max(cfg.episode_length_s, MEASURE_EPISODE_S)
    return cfg


register_mjlab_task(task_id=TASK_FW_RALLY_MEASURE, env_cfg=rally_measure(load_env_cfg(ag.SRC_RES)),
                    play_env_cfg=rally_measure(load_env_cfg(ag.SRC_RES, play=True)), rl_cfg=load_rl_cfg(ag.SRC_RES),
                    runner_cls=load_runner_cls(ag.SRC_RES))


# D-190 P2 (RL's capacity screen, the user's "why not just train for longer?"): the current rally composite (lam_r 2
# residual around RES_BASE on latent-07; run 14's task) trained on the footwork specialist's drill with its working speed
# reward. One change from the specialist's footwork_task on this task: move episodes only (move_prob 1.0) are the
# FootworkDrill (spots 1-5 m, deadline, pay "settled", heading free beyond 1 m) and move_track_lin_vel is fw_track_lin_vel
# (std 0.5 x max(1, |v_cmd|)); the composite's other rewards are untouched. 20-s episodes.
TASK_FW_RALLY_TRAIN = "Picklebot-Footwork-Train-RallyLamR2-G1"


def rally_train(cfg):
    ag.deadline_task(cfg)
    b = cfg.actions["ball"]
    vals = {f.name: getattr(b, f.name) for f in dataclasses.fields(b) if f.init}
    vals.update(deadline_arrival_mode="first_entry", deadline_v_req=V_REQ, deadline_dist=DIST, footwork_dist=DIST,
                move_spot_box=SPOT_BOX, footwork_pay="settled")
    cfg.actions["ball"] = FootworkBallActionCfg(**vals)
    r = cfg.rewards
    assert r["move_track_lin_vel"].func is md.move_track_lin_vel
    r["move_track_lin_vel"] = dataclasses.replace(r["move_track_lin_vel"], func=fw_track_lin_vel)
    cfg.episode_length_s = max(cfg.episode_length_s, EPISODE_S)
    return cfg


register_mjlab_task(task_id=TASK_FW_RALLY_TRAIN, env_cfg=rally_train(load_env_cfg(ag.SRC_RES)),
                    play_env_cfg=rally_train(load_env_cfg(ag.SRC_RES, play=True)), rl_cfg=load_rl_cfg(ag.SRC_RES),
                    runner_cls=load_runner_cls(ag.SRC_RES))


# D-191 body-ceiling test (the user 2026-10-31: beginners 1-2 m/s, intermediates about 3-4, professionals 4-6; "keep
# improving the agility"): the specialist with the command cap raised 2.5 -> 4.0 m/s, deadlines from v_req U(1.5, 3.5)
# and spots 2-6 m so top speed can be reached (training); the measure read uses spots 4-6 m, 60-s episodes. Pay
# "settled" (D-181). Everything else is the specialist's task.
TASK_FW_FAST4 = "Picklebot-Footwork-Specialist-Fast4-G1"
TASK_FW_MEASURE_FAST4 = "Picklebot-Footwork-Measure60-Fast4-G1"
FAST4_CAP, FAST4_V_REQ, FAST4_DIST, FAST4_MEASURE_DIST = 4.0, (1.5, 3.5), (2.0, 6.0), (4.0, 6.0)
_register(TASK_FW_FAST4, lambda c: footwork_task(c, dist=FAST4_DIST, pay="settled", cmd_cap=FAST4_CAP, v_req=FAST4_V_REQ))
_register(TASK_FW_MEASURE_FAST4, lambda c: footwork_task(c, dist=FAST4_MEASURE_DIST, pay="settled",
                                                          episode_s=MEASURE_EPISODE_S, cmd_cap=FAST4_CAP,
                                                          v_req=FAST4_V_REQ))


# D-192 d1 (panel round 59): the base rebuilt by the s5c-18 kickstart recipe with fw1b-S as the move-episode teacher.
# Pre-launch teacher check (experiment design): the kickstart's move episodes draw MoveDrill spots (0.5-3 m inside the
# robot half court, move_drill.SPOT_BOX), so the teacher is read on that geometry: the measure drill with those spots,
# 60-s episodes, pay "settled" (the teacher sees only the spot; the cap and deadlines are never observed).
TASK_FW_MEASURE_COURT = "Picklebot-Footwork-Measure60-Court-G1"
_register(TASK_FW_MEASURE_COURT, lambda c: footwork_task(c, dist=md.DIST_RANGE, pay="settled", episode_s=MEASURE_EPISODE_S,
                                                          spot_box=md.SPOT_BOX))
# Base gate (architecture): a base (a Picklebot-Latent-Court-L3-G1 executor, e.g. RES_BASE model_32874 or the d1
# endpoint) read on its own on the Measure60 drill (spots 3-5 m in the Fast25 box, as the rally composite's bridge read).
TASK_FW_L3BASE_MEASURE = "Picklebot-Footwork-Measure60-L3Base-G1"
_SRC_L3 = "Picklebot-Latent-Court-L3-G1"
register_mjlab_task(task_id=TASK_FW_L3BASE_MEASURE, env_cfg=rally_measure(load_env_cfg(_SRC_L3)),
                    play_env_cfg=rally_measure(load_env_cfg(_SRC_L3, play=True)), rl_cfg=load_rl_cfg(_SRC_L3),
                    runner_cls=load_runner_cls(_SRC_L3))
# d1b (D-193, pre-registered; used only if the d1 base gate reads CAP-HELD with first step <= the parent's): the
# kickstart's own task (Picklebot-Latent-Court-L3-G1) with its move episodes' spot geometry widened to the specialist's
# (1-5 m in the Fast25 box) through FastMoveDrill (body_speed.py), which keeps MoveDrill's episode logic (move_prob,
# held arrival, untimed limit); ball episodes unchanged. The command cap (2.5 m/s) only shapes the move reward, which the
# kickstart's supervised loss does not use. One change against d1: the move-episode geometry.
TASK_L3_FWGEOM = "Picklebot-Latent-Court-L3-FwGeom-G1"


def l3_fwgeom(cfg):
    return ag.to_agility_ball(cfg, move_cmd_max_speed=CMD_CAP, move_dist_range=DIST, move_spot_box=SPOT_BOX)


register_mjlab_task(task_id=TASK_L3_FWGEOM, env_cfg=l3_fwgeom(load_env_cfg(_SRC_L3)),
                    play_env_cfg=l3_fwgeom(load_env_cfg(_SRC_L3, play=True)), rl_cfg=load_rl_cfg(_SRC_L3),
                    runner_cls=load_runner_cls(_SRC_L3))


# D-196 d1s3 (panel round 62: motion, RL, architecture): 22b's rally task with only the move-episode speed reward
# changed. Stage 2 (D-195) trained the d1 base's speed back out: 22b's move_track_lin_vel scores the MoveDrill command,
# capped at 1.0 m/s with a std 0.5 kernel, so 1.9 m/s pays exp(-3.24) = 0.04. Here, in move episodes only, the command is
# MoveDrill's with the cap raised to CMD_CAP (2.5 m/s; gain scaled, braking radius unchanged, heading still to the net)
# and the kernel is fw_track_lin_vel's (std 0.5 x max(1, |v_cmd|)). Everywhere else in the walk mask (S-D2c shadow-swing
# episodes) the command and kernel are 22b's exactly (cap 1.0 -> std 0.5). The drill object, spot sampling, arrival and
# ball episodes are untouched (architecture: FastMoveDrill re-implements spot sampling and was never run in pair mode).
TASK_RALLY_FASTMOVE = "Picklebot-Rally22b-FastMove-G1"


def rally_fast_track_lin_vel(env, std: float = TRACK_STD, cap: float = CMD_CAP) -> torch.Tensor:
    dr = md._drill(env)
    if dr is None:
        return torch.zeros(env.num_envs, device=env.device)
    v_cmd, _ = dr.command()  # MoveDrill's: cap 1.0 m/s
    t = dr.t
    yaw = md._yaw(t._entity.data.root_link_pose_w[:, 3:7])
    delta = t.recover_xy - t.pelvis_xy()
    d = delta.norm(dim=-1, keepdim=True)
    v_w = delta / d.clamp(min=1e-6) * (md.CMD_GAIN * cap / md.CMD_MAX_SPEED * d).clamp(max=cap)
    c, s = torch.cos(yaw), torch.sin(yaw)
    v_fast = torch.stack([c * v_w[:, 0] + s * v_w[:, 1], -s * v_w[:, 0] + c * v_w[:, 1]], -1)
    v_cmd = torch.where(dr.move_ep.unsqueeze(-1), v_fast, v_cmd)
    v = t._entity.data.root_link_lin_vel_b[:, :2]
    k = std * v_cmd.norm(dim=-1).clamp(min=1.0)
    return torch.exp(-((v_cmd - v) ** 2).sum(-1) / k ** 2) * md._walk_mask(dr)


def rally_fastmove(cfg):
    r = cfg.rewards
    assert r["move_track_lin_vel"].func is md.move_track_lin_vel
    r["move_track_lin_vel"] = dataclasses.replace(r["move_track_lin_vel"], func=rally_fast_track_lin_vel)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_FASTMOVE, env_cfg=rally_fastmove(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_fastmove(load_env_cfg(ag.SRC_22B, play=True)), rl_cfg=load_rl_cfg(ag.SRC_22B),
                    runner_cls=load_runner_cls(ag.SRC_22B))

# D-231 (panel round 92, (d) 5 of 5): C's task practised on the frozen set-start read (D-229): the drill reset at
# every pair-court rally start (pair_drill_reset, with pair_reset_parks). The only change from TASK_RALLY_FASTMOVE.
TASK_RALLY_FASTMOVE_DR = "Picklebot-Rally22b-FastMove-DrillReset-G1"


def rally_fastmove_dr(cfg):
    cfg = rally_fastmove(cfg)
    cfg.actions["ball"] = dataclasses.replace(cfg.actions["ball"], pair_drill_reset=True, pair_reset_parks=True)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_FASTMOVE_DR, env_cfg=rally_fastmove_dr(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_fastmove_dr(load_env_cfg(ag.SRC_22B, play=True)), rl_cfg=load_rl_cfg(ag.SRC_22B),
                    runner_cls=load_runner_cls(ag.SRC_22B))

# D-232 (panel round 93, (i) 5 of 5; D-063's term, 4 of 5): the drill-reset task plus the terminating-fall penalty
# (is_terminated, weight -50, placed before legal_return, which clears the step flags). The only change from
# TASK_RALLY_FASTMOVE_DR.
TASK_RALLY_FASTMOVE_DR_FALL = "Picklebot-Rally22b-FastMove-DrillReset-Fall-G1"
FALL_PENALTY_WEIGHT = -50.0


def rally_fastmove_dr_fall(cfg):
    from mjlab.envs import mdp as _mdp
    cfg = rally_fastmove_dr(cfg)
    legal = cfg.rewards.pop("legal_return")
    cfg.rewards["fall"] = RewardTermCfg(func=_mdp.is_terminated, weight=FALL_PENALTY_WEIGHT)
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_RALLY_FASTMOVE_DR_FALL, env_cfg=rally_fastmove_dr_fall(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_fastmove_dr_fall(load_env_cfg(ag.SRC_22B, play=True)),
                    rl_cfg=load_rl_cfg(ag.SRC_22B), runner_cls=load_runner_cls(ag.SRC_22B))


# D-199 (D-198's FEED-STATE route; motion's ready_at_handoff, panel rounds 63-64): the d1s3 task (Rally22b-FastMove) plus
# one reward term for being set at the moment a ball is put in play for this env: the feeder fire or the partner's
# contact (the contact hand-off). ballidx63: at the feeder fire the receiver is still moving (pelvis speed p50 0.28 m/s)
# and about 0.9 m from its recovery spot; failures 0.09 -> 0.37 across pelvis-speed terciles and 0.05 -> 0.35 across
# recovery-distance terciles; refeed 3 s instead of 0.5 s lifts feeder legal 0.62 -> 0.74.
# The value exp(-(|v_xy| / READY_V_STD)^2) exp(-(|pelvis - recover_xy| / READY_D_STD)^2) is computed INSIDE the
# PairCourts.step wrapper, at the event substep, before _refeed draws the next ball's recovery spot (round 64: reading it
# at reward time scored against a spot the robot cannot see), the state ballidx63 measured. It is paid once, on the next
# reward step; never while the ball is in flight. Events within READY_MIN_AGE_S of an episode start are not paid (coach:
# the robot is still on its spawn spot). Weight READY_W as paddle_contact (an event term: weight x dt = 1.0 per event).
# PICKLEBOT_READY_LOG (optional): cumulative per-event sums for the per-event dose line. The ball term's class changes
# only to add the latch (field values unchanged).
TASK_RALLY_READY = "Picklebot-Rally22b-FastMove-Ready-G1"
READY_W, READY_V_STD, READY_D_STD, READY_MIN_AGE_S = 50.0, 0.3, 1.0, 1.0
READY_LOG_EVERY = 240  # env steps (10 iterations of 24)


from picklebot_mj.tasks import return_stand as _rs  # noqa: E402


@dataclass(kw_only=True)
class ReadyBallActionCfg(_rs.BallPhysicsActionCfg):
    def build(self, env) -> "ReadyBallAction":
        return ReadyBallAction(self, env)


class ReadyBallAction(_rs.BallPhysicsAction):
    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        assert self.pairs is not None, "the ready latch hooks PairCourts.step (pair mode)"
        self.ready_due = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        self.ready_val = torch.zeros(self.num_envs, device=self.device)
        self.ready_stats = torch.zeros(4, device=self.device)  # paid sum, events paid, events skipped (young), paid sum of squares
        self._ready_log = os.environ.get("PICKLEBOT_READY_LOG")
        self._ready_last = -1
        install_ready_latch(self, age_fn=self._age)

    def _age(self) -> torch.Tensor:
        env = self._env
        return env.episode_length_buf.float() * env.step_dt

    def reset(self, env_ids=None) -> None:
        super().reset(env_ids)
        if env_ids is None:
            self.ready_due[:] = False
            self.ready_val[:] = 0.0
        else:
            self.ready_due[env_ids] = False
            self.ready_val[env_ids] = 0.0


def ready_value(term, v_std: float = READY_V_STD, d_std: float = READY_D_STD) -> torch.Tensor:
    v = term._entity.data.root_link_lin_vel_w[:, :2].norm(dim=-1)
    d = (term.pelvis_xy() - term.recover_xy).norm(dim=-1)
    return torch.exp(-(v / v_std) ** 2) * torch.exp(-(d / d_std) ** 2)


def install_ready_latch(term, age_fn=None) -> None:
    """Wrap term.pairs.step: for the envs given a ball this physics step (feeder fire | partner contact) and not already
    latched, store the ready value now (before _refeed moves recover_xy) and latch them."""
    orig = term.pairs.step

    def step(*args, **kwargs):
        fire, recv = orig(*args, **kwargs)
        ev = (fire | recv) & ~term.ready_due
        if age_fn is not None:
            young = age_fn() < READY_MIN_AGE_S
            if hasattr(term, "ready_stats"):
                term.ready_stats[2] += (ev & young).sum()
            ev = ev & ~young
        term.ready_val = torch.where(ev, ready_value(term), term.ready_val)
        term.ready_due |= ev
        return fire, recv

    term.pairs.step = step


def ready_at_event(env) -> torch.Tensor:
    t = env.action_manager.get_term("ball")
    m = t.ready_due.float()
    out = t.ready_val * m
    if hasattr(t, "ready_stats"):
        t.ready_stats[0] += out.sum()
        t.ready_stats[1] += m.sum()
        t.ready_stats[3] += (out * out).sum()
        if t._ready_log:
            step = int(env.common_step_counter)
            if step % READY_LOG_EVERY == 0 and step != t._ready_last:
                t._ready_last = step
                import json
                with open(t._ready_log, "a") as f:
                    f.write(json.dumps({"step": step, "ready": [round(x, 4) for x in t.ready_stats.tolist()]}) + "\n")
    t.ready_due.zero_()
    return out


def rally_ready(cfg):
    cfg = rally_fastmove(cfg)
    b = cfg.actions["ball"]
    assert type(b) is _rs.BallPhysicsActionCfg
    cfg.actions["ball"] = ReadyBallActionCfg(**{f.name: getattr(b, f.name) for f in dataclasses.fields(b) if f.init})
    cfg.rewards["ready_at_event"] = RewardTermCfg(func=ready_at_event, weight=READY_W)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_READY, env_cfg=rally_ready(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_ready(load_env_cfg(ag.SRC_22B, play=True)), rl_cfg=load_rl_cfg(ag.SRC_22B),
                    runner_cls=load_runner_cls(ag.SRC_22B))


# D-202 d1s6 (panel rounds 65-66, option (b): parked readiness): d1s3's task (Rally22b-FastMove) plus one reward term for
# being set while the court is dead and this env is parked waiting for the next feeder ball (court_dead & parked), the
# state ballidx63 found failing at the feeder fire. Not while busy (a move or ghost-swing drill episode: the drill's own
# speed terms apply there) and not within READY_MIN_AGE_S of an episode start; nothing is paid at partner contacts (D-200:
# readiness at contacts planted the feet when the first step should load). Value as ready_value (v_std 0.3 m/s, d_std
# 1.0 m, D-199's), against the recover_xy the robot observes; weight PARKED_W per step (2 x dt 0.02 x ~25 parked steps
# = about 1.0 per dead ball, as d1s4's 1.0 per event; the step count is a guess until the dose log measures it).
TASK_RALLY_PARKED = "Picklebot-Rally22b-FastMove-Parked-G1"
PARKED_W = 2.0


def parked_mask(env) -> torch.Tensor:
    t = env.action_manager.get_term("ball")
    pc = t.pairs
    # both robots idle (RL, round 66): a parked robot whose partner still has a ball in play is not paid, so the window
    # is the refeed countdown and cannot be stretched by ending rallies early
    m = pc.court_dead.repeat(2) & pc.parked & pc.parked[pc.partner]
    dr = getattr(t, "drill", None)
    if dr is not None:
        m = m & ~dr.move_ep
    sh = getattr(t, "shadow", None)
    if sh is not None:
        m = m & ~sh.swing_ep
    age = env.episode_length_buf.float() * env.step_dt
    return m & (age >= READY_MIN_AGE_S)


def parked_ready(env) -> torch.Tensor:
    """With PICKLEBOT_READY_LOG set (report only) also appends cumulative [sum of paid values, paid steps, dead-court
    steps, sum of squares] every READY_LOG_EVERY steps (architecture's dose log, round 66)."""
    t = env.action_manager.get_term("ball")
    m = parked_mask(env).float()
    out = ready_value(t) * m
    log = os.environ.get("PICKLEBOT_READY_LOG")
    if log:
        if not hasattr(t, "parked_stats"):
            t.parked_stats, t._parked_last = torch.zeros(4, device=out.device), -1
        t.parked_stats[0] += out.sum()
        t.parked_stats[1] += m.sum()
        t.parked_stats[2] += t.pairs.court_dead.sum() * 2
        t.parked_stats[3] += (out * out).sum()
        step = int(env.common_step_counter)
        if step % READY_LOG_EVERY == 0 and step != t._parked_last:
            t._parked_last = step
            import json
            with open(log, "a") as f:
                f.write(json.dumps({"step": step, "parked": [round(x, 4) for x in t.parked_stats.tolist()]}) + "\n")
    return out


def rally_parked(cfg):
    cfg = rally_fastmove(cfg)
    cfg.rewards["parked_ready"] = RewardTermCfg(func=parked_ready, weight=PARKED_W)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_PARKED, env_cfg=rally_parked(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_parked(load_env_cfg(ag.SRC_22B, play=True)), rl_cfg=load_rl_cfg(ag.SRC_22B),
                    runner_cls=load_runner_cls(ag.SRC_22B))


# D-205 d1s8 (panel round 69, 5 of 5 for (a); diag68 routed STATE): d1s3's task with one change, recovery_reward's mask.
# return_stand.recovery_reward pays exp(-(d / std)^2) to recover_xy only while hit_done (this env's last ball was its own
# legal hit; cleared at its next feed or a reset), so a robot whose last ball ended without a legal contact, or one just
# reset, is unpaid while it waits; it is the k = 1 receiver diag68 found off its spot. Here the term also pays while the
# env is parked on a pair court (no ball in play in it) and not busy (a move or ghost-swing episode, whose recover_xy is
# the drill spot). Same std (1.5 m in this task) and weight 1.0: distance only (d1s6 paid stopping through a speed
# factor); receiving clears parked and a feed clears hit_done, so nothing is paid at or after this env's own contact
# (d1s4 planted the feet there). PICKLEBOT_READY_LOG (report only, the KILL-NO-CLIMB read) appends cumulative [value on
# newly paid steps, newly paid steps, value on hit_done steps, hit_done steps] every READY_LOG_EVERY steps.
TASK_RALLY_IDLEREC = "Picklebot-Rally22b-FastMove-IdleRec-G1"


def idle_recovery_mask(t) -> torch.Tensor:
    pc = getattr(t, "pairs", None)
    if pc is None:
        return torch.zeros_like(t.hit_done)
    m = pc.parked.clone()
    dr = getattr(t, "drill", None)
    if dr is not None:
        m = m & ~dr.move_ep
    sh = getattr(t, "shadow", None)
    if sh is not None:
        m = m & ~sh.swing_ep
    return m


def rally_recovery_reward(env, std: float = _rs.RECOVERY_STD) -> torch.Tensor:
    t = env.action_manager.get_term("ball")
    d = (t.pelvis_xy() - t.recover_xy).norm(dim=-1)
    v = torch.exp(-(d / std) ** 2)
    new = idle_recovery_mask(t) & ~t.hit_done
    out = v * (t.hit_done | new).float()
    log = os.environ.get("PICKLEBOT_READY_LOG")
    if log:
        if not hasattr(t, "idlerec_stats"):
            t.idlerec_stats, t._idlerec_last = torch.zeros(4, device=out.device), -1
        t.idlerec_stats += torch.stack([(v * new).sum(), new.sum().float(), (v * t.hit_done).sum(), t.hit_done.sum().float()])
        step = int(env.common_step_counter)
        if step % READY_LOG_EVERY == 0 and step != t._idlerec_last:
            t._idlerec_last = step
            import json
            with open(log, "a") as f:
                f.write(json.dumps({"step": step, "idlerec": [round(x, 4) for x in t.idlerec_stats.tolist()]}) + "\n")
    return out


def rally_idlerec(cfg):
    cfg = rally_fastmove(cfg)
    r = cfg.rewards["recovery"]
    assert r.func is _rs.recovery_reward, r.func
    cfg.rewards["recovery"] = dataclasses.replace(r, func=rally_recovery_reward)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_IDLEREC, env_cfg=rally_idlerec(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_idlerec(load_env_cfg(ag.SRC_22B, play=True)), rl_cfg=load_rl_cfg(ag.SRC_22B),
                    runner_cls=load_runner_cls(ag.SRC_22B))

# D-221 (panel round 84, (a) stage 1, 5 of 5; round 84b form F2, 5 of 5): the court-scale quickness specialist's
# training task. fw1b-S's task with the read's court geometry (Measure60-Court's spots: md.DIST_RANGE inside
# md.SPOT_BOX), pay "settled", cap 2.5 and deadlines (V_REQ) unchanged, plus the first-step bonus (fw_first_step).
TASK_FW_QUICK = "Picklebot-Footwork-Specialist-Quick-G1"
_register(TASK_FW_QUICK, lambda c: footwork_task(c, dist=md.DIST_RANGE, pay="settled", spot_box=md.SPOT_BOX,
                                                 first_bonus=True))

# D-222 (panel round 85, (i)): the Quick task with the bonus's pay span 1.0 -> 0.5 s (pays 0 at 1.6 s, 50 at 1.35 s,
# saturates at 1.1 s); the only change from TASK_FW_QUICK.
TASK_FW_QUICK2 = "Picklebot-Footwork-Specialist-Quick2-G1"
_register(TASK_FW_QUICK2, lambda c: footwork_task(c, dist=md.DIST_RANGE, pay="settled", spot_box=md.SPOT_BOX,
                                                  first_bonus=True, first_span=0.5))


# D-229 (the user, D-228: "i dont give a fuck about limiting the motors for realistic motors, i want fast humanlike
# movement"): the leg, waist and ankle actuators' effort limits x STRONG_EFFORT_X, in new tasks only. Stiffness, damping
# and armature are unchanged, and so is every policy's action scale (G1_ACTION_SCALE is computed at import from the
# original constants). Arms and wrists are unchanged (paddle contact as before).
def with_strong_legs(cfg, k: float = STRONG_EFFORT_X):
    robot = cfg.scene.entities["robot"]
    acts = []
    for a in robot.articulation.actuators:
        leg = any(re.search(r"(_hip_|_knee_|_ankle_|waist_)", e) for e in a.target_names_expr)
        acts.append(dataclasses.replace(a, effort_limit=a.effort_limit * k) if leg and a.effort_limit is not None else a)
    cfg.scene.entities["robot"] = dataclasses.replace(robot, articulation=dataclasses.replace(robot.articulation,
                                                                                              actuators=tuple(acts)))
    return cfg


TASK_FW_QUICK2_STRONG = "Picklebot-Footwork-Specialist-Quick2-Strong-G1"
TASK_FW_MEASURE_COURT_STRONG = "Picklebot-Footwork-Measure60-Court-Strong-G1"
_register(TASK_FW_QUICK2_STRONG, lambda c: with_strong_legs(footwork_task(c, dist=md.DIST_RANGE, pay="settled",
                                                                          spot_box=md.SPOT_BOX, first_bonus=True,
                                                                          first_span=0.5)))
_register(TASK_FW_MEASURE_COURT_STRONG, lambda c: with_strong_legs(footwork_task(c, dist=md.DIST_RANGE, pay="settled",
                                                                                 episode_s=MEASURE_EPISODE_S,
                                                                                 spot_box=md.SPOT_BOX)))


# The user (2026-11-09) asks what blocks the first step; the damping premise read (motion, round 92/109; RL round 109):
# the leg, waist and ankle actuators' damping x LOOSE_DAMPING_X (mjlab's G1 damping ratio 2.0 -> 1.0, critically
# damped), in new tasks only. Stiffness, effort, armature and every policy's action scale are unchanged. Reads only.
LOOSE_DAMPING_X = 0.5


def with_loose_legs(cfg, k: float = LOOSE_DAMPING_X):
    robot = cfg.scene.entities["robot"]
    acts = []
    for a in robot.articulation.actuators:
        leg = any(re.search(r"(_hip_|_knee_|_ankle_|waist_)", e) for e in a.target_names_expr)
        acts.append(dataclasses.replace(a, damping=a.damping * k) if leg else a)
    cfg.scene.entities["robot"] = dataclasses.replace(robot, articulation=dataclasses.replace(robot.articulation,
                                                                                              actuators=tuple(acts)))
    return cfg


TASK_FW_RALLY_MEASURE_LOOSE = "Picklebot-Footwork-Measure60-RallyLamR2-Loose-G1"
register_mjlab_task(task_id=TASK_FW_RALLY_MEASURE_LOOSE, env_cfg=with_loose_legs(rally_measure(load_env_cfg(ag.SRC_RES))),
                    play_env_cfg=with_loose_legs(rally_measure(load_env_cfg(ag.SRC_RES, play=True))),
                    rl_cfg=load_rl_cfg(ag.SRC_RES), runner_cls=load_runner_cls(ag.SRC_RES))
TASK_RES_LOOSE = "Picklebot-Latent-Court-Res-Loose-G1"
register_mjlab_task(task_id=TASK_RES_LOOSE, env_cfg=with_loose_legs(load_env_cfg("Picklebot-Latent-Court-Res-G1")),
                    play_env_cfg=with_loose_legs(load_env_cfg("Picklebot-Latent-Court-Res-G1", play=True)),
                    rl_cfg=load_rl_cfg("Picklebot-Latent-Court-Res-G1"),
                    runner_cls=load_runner_cls("Picklebot-Latent-Court-Res-G1"))


# D-235 (D-234's FEED route: panel round 95's pre-registered route; motion's mixed form, round 94): C's drill-reset task
# with the top half of the drill courts made launcher courts (pair_launch_court_frac 0.25 of 0.5): each robot there plays
# the court read's own episode (a drill feed in play from the reset at a random start spot, drill v2 recovery, 8-s
# episodes). The only change from TASK_RALLY_FASTMOVE_DR; the other drill courts keep their move / swing chances.
TASK_RALLY_FASTMOVE_DR_LAUNCH = "Picklebot-Rally22b-FastMove-DrillReset-Launch-G1"
LAUNCH_COURT_FRAC = 0.25
LAUNCH_EPISODE_S = 8.0  # the court read's episode (return_stand.EPISODE_S)


def launch_time_out(env):
    """D-235: launcher-court robots end their episode at LAUNCH_EPISODE_S (a time-out, as the court read's)."""
    le = getattr(env.action_manager.get_term("ball"), "launch_env", None)
    if le is None:
        return torch.zeros(env.num_envs, dtype=torch.bool, device=env.device)
    return le & (env.episode_length_buf >= int(round(LAUNCH_EPISODE_S / env.step_dt)))


def rally_fastmove_dr_launch(cfg):
    from mjlab.managers.termination_manager import TerminationTermCfg
    cfg = rally_fastmove_dr(cfg)
    cfg.actions["ball"] = dataclasses.replace(cfg.actions["ball"], pair_launch_court_frac=LAUNCH_COURT_FRAC)
    cfg.terminations["launch_time_out"] = TerminationTermCfg(func=launch_time_out, time_out=True)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_FASTMOVE_DR_LAUNCH, env_cfg=rally_fastmove_dr_launch(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_fastmove_dr_launch(load_env_cfg(ag.SRC_22B, play=True)),
                    rl_cfg=load_rl_cfg(ag.SRC_22B), runner_cls=load_runner_cls(ag.SRC_22B))


# D-237 (panel round 97, (ii) 4 of 5): D-235's launcher-court task with the move drill's spots weighted toward the
# left and back (sectors 2 left, 3 back-left, 4 back doubled; sector 0 = toward the net, counter-clockwise, as
# RIGHT_SIDE_X2 in tasks/__init__.py). The only change from TASK_RALLY_FASTMOVE_DR_LAUNCH.
TASK_RALLY_FASTMOVE_DR_LAUNCH_LB = "Picklebot-Rally22b-FastMove-DrillReset-Launch-LeftBack-G1"
LEFT_BACK_X2 = (1.0, 1.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0)


def rally_fastmove_dr_launch_lb(cfg):
    cfg = rally_fastmove_dr_launch(cfg)
    cfg.actions["ball"] = dataclasses.replace(cfg.actions["ball"], move_sector_weights=LEFT_BACK_X2)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_FASTMOVE_DR_LAUNCH_LB, env_cfg=rally_fastmove_dr_launch_lb(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_fastmove_dr_launch_lb(load_env_cfg(ag.SRC_22B, play=True)),
                    rl_cfg=load_rl_cfg(ag.SRC_22B), runner_cls=load_runner_cls(ag.SRC_22B))


# D-238 (panel round 98, (a) 5 of 5): D-237's smoke failed its sector-share line (0.436 < 0.45; back spots near the
# baseline flip forward), so the weights go to x3 on sectors 2-4 (architecture's round-97 form). The only change from
# TASK_RALLY_FASTMOVE_DR_LAUNCH_LB.
TASK_RALLY_FASTMOVE_DR_LAUNCH_LB3 = "Picklebot-Rally22b-FastMove-DrillReset-Launch-LeftBack3-G1"
LEFT_BACK_X3 = (1.0, 1.0, 3.0, 3.0, 3.0, 1.0, 1.0, 1.0)


def rally_fastmove_dr_launch_lb3(cfg):
    cfg = rally_fastmove_dr_launch(cfg)
    cfg.actions["ball"] = dataclasses.replace(cfg.actions["ball"], move_sector_weights=LEFT_BACK_X3)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_FASTMOVE_DR_LAUNCH_LB3, env_cfg=rally_fastmove_dr_launch_lb3(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_fastmove_dr_launch_lb3(load_env_cfg(ag.SRC_22B, play=True)),
                    rl_cfg=load_rl_cfg(ag.SRC_22B), runner_cls=load_runner_cls(ag.SRC_22B))


# D-241 (panel round 101, 5 of 5): D-235's launcher-court task with the set start (pair_drill_reset) on half the live
# pair courts only (odd court index); the other half restart from where the robots ended, the state the direction
# read (feeder_speed_envelope.py: feed_anchor "start", no drill reset) tests. The only change from
# TASK_RALLY_FASTMOVE_DR_LAUNCH; the training-only pair_rally_cap 8 (D-240) stays a driver override.
TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF = "Picklebot-Rally22b-FastMove-DrillReset-Launch-HalfReset-G1"


def rally_fastmove_dr_launch_half(cfg):
    cfg = rally_fastmove_dr_launch(cfg)
    cfg.actions["ball"] = dataclasses.replace(cfg.actions["ball"], pair_drill_reset_frac=0.5)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF, env_cfg=rally_fastmove_dr_launch_half(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_fastmove_dr_launch_half(load_env_cfg(ag.SRC_22B, play=True)),
                    rl_cfg=load_rl_cfg(ag.SRC_22B), runner_cls=load_runner_cls(ag.SRC_22B))


# D-249 (panel round 108, 5 of 5; the user's direction "lets see if the pickleball videos help with training"): D-241's
# HalfReset task with the move drill's spots drawn from the frozen pro-move table (tasks/pro_move.py: pelvis + a pro
# displacement, unscaled, MoveDrill's box rule, untimed limit and reward). The only change from
# TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF; Q's pair_rally_cap 8 on the reset half stays a driver override.
TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF_PRO = "Picklebot-Rally22b-FastMove-DrillReset-Launch-HalfReset-ProMove-G1"


def rally_fastmove_dr_launch_half_pro(cfg):
    cfg = rally_fastmove_dr_launch_half(cfg)
    cfg.actions["ball"] = dataclasses.replace(cfg.actions["ball"], move_pro_moves=True)
    return cfg


register_mjlab_task(task_id=TASK_RALLY_FASTMOVE_DR_LAUNCH_HALF_PRO,
                    env_cfg=rally_fastmove_dr_launch_half_pro(load_env_cfg(ag.SRC_22B)),
                    play_env_cfg=rally_fastmove_dr_launch_half_pro(load_env_cfg(ag.SRC_22B, play=True)),
                    rl_cfg=load_rl_cfg(ag.SRC_22B), runner_cls=load_runner_cls(ag.SRC_22B))
