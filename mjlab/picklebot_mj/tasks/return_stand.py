"""Stage 2 task: a standing G1 returns a fed ball with a wrist-mounted paddle.

Each episode feeds one ball from the far side. It bounces once in front of the
robot and rises toward its forehand (right side). The robot must keep its
balance, make paddle contact after the bounce (a volley is an early-volley fault
in this receive context) and send a legal return: the first bounce after its hit
lands in the far court. The rules come from `picklebot_mj.rules`; the ball
physics is the analytic `BallSim` (D-039), advanced on every MuJoCo physics step
by `BallPhysicsAction`. That term has no policy outputs; it uses the action
manager's per-physics-step hook. The paddle reaction impulse is applied to the
G1's paddle body through `xfrc_applied`.

Built on mjlab's flat G1 velocity config (proprioception, joint-position
actions, balance rewards, fall termination) with a zero velocity command.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

import mujoco
import torch

from mjlab.entity import EntityCfg
from mjlab.envs import ManagerBasedRlEnvCfg
from mjlab.managers.action_manager import ActionTerm, ActionTermCfg
from mjlab.managers.observation_manager import ObservationTermCfg
from mjlab.managers.reward_manager import RewardTermCfg
from mjlab.managers.termination_manager import TerminationTermCfg
from mjlab.tasks.velocity.config.g1.env_cfgs import unitree_g1_flat_env_cfg
from mjlab.tasks.velocity.mdp import UniformVelocityCommandCfg

from picklebot_mj import court
from picklebot_mj.ball import BALL_RADIUS
from picklebot_mj.ball_sim import (PADDLE_CORNER_RADIUS, BallParams, BallSim, BallState, CompiledBallSim,
                                   PaddleState)
from picklebot_mj.feeds import BOUNCE_AIM_MIN, FAMILIES, FAMILY_NAMES, REACH_NEAR, REACH_NEAR_V2, FeedMix
from picklebot_mj.g1_paddle import PADDLE_BODY, get_g1_paddle_cfg
from picklebot_mj.rules import Fault, Phase, RallyRules, in_bounds

ROBOT_START = (-5.6, 0.35)  # court-local pelvis position, facing +x (the net)
ROBOT_PLAYER = 0  # near team, player 0
FEEDER_PLAYER = 2  # far team
EPISODE_S = 8.0  # several feeds per episode (feeding machine); 3 s until lateral-a01, 4 s in lateral-a02
REFEED_DELAY_S = 0.5  # pause between the end of one rally and the next feed
# Aiming targets (court-local, far court): A = deep left, B = deep right from the robot's view
# (it faces +x, so its left is +y). Hit = legal landing within TARGET_RADIUS of the target.
TARGET_CENTRES = ((4.5, 1.6), (4.5, -1.6))
TARGET_RADIUS = 1.0
PLACEMENT_MAX = 3.0  # bonus at the centre on a legal landing; linear to 0 at PLACEMENT_RANGE
PLACEMENT_RANGE = 2.0
BODY_RADIUS = 0.17  # ball within this of the pelvis/torso origins counts as body contact
# Stage 5 start box (court-local offsets from ROBOT_START): x -6.3..-4.9, y -1.2..1.2, yaw +-0.3 rad.
START_BOX = {"x": (-0.7, 0.7), "y": (-1.55, 0.85), "yaw": (-0.3, 0.3)}
FEED_Y_MAX = court.HALF_WIDTH - 0.15  # anchored feeds are clamped inside the sidelines
# Recovery command (Stage 5): a court spot to reach between the hit and the next feed.
RECOVERY_BOX = ((-6.2, -5.0), (-1.5, 1.5))  # training: sampled per feed (x range, y range)
RECOVERY_FIXED = (-5.6, 0.0)  # evaluation: baseline centre
RECOVERY_STD = 0.5  # reward exp(-(d / std)^2)
RECOVERY_BIN = 0.05  # error histogram bin width (m), 100 bins
REACH_PROMOTE, REACH_MIN_FEEDS, REACH_STEP = 0.7, 300, 0.1  # Drill 3 curriculum: widen at 70 % legal over 300+ feeds
WIDE_SHAPING_STD = 1.5  # run F2: approach_far and recovery kernels (m)


# --------------------------------------------------------------------------------------
# Ball physics action term (0 policy dims; runs every physics step)


def _quat_to_matrix(q: torch.Tensor) -> torch.Tensor:
    w, x, y, z = q.unbind(-1)
    return torch.stack([
        1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y),
        2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x),
        2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], dim=-1).reshape(*q.shape[:-1], 3, 3)


def _rotate_inv(q: torch.Tensor, v: torch.Tensor) -> torch.Tensor:
    """Rotate world vectors v into the frame of quaternion q (wxyz)."""
    return (v.unsqueeze(-2) @ _quat_to_matrix(q)).squeeze(-2)


@dataclass(kw_only=True)
class BallPhysicsActionCfg(ActionTermCfg):
    entity_name: str = "robot"
    feed_mix: FeedMix = field(default_factory=FeedMix)  # default: easy_forehand only (Stage 2 drill)
    seed: int = 0
    # Fixed ball sub-steps per physics step (no host syncs). 6 at dt 5 ms keeps travel per
    # sub-step under 0.9 ball radii at 35 m/s relative speed; the paddle target is 9 cm thick
    # (box + ball diameter), so there is no tunnelling.
    ball_substeps: int = 6
    # torch.compile the fixed-sub-step ball step (9x faster; ~50 s compile once per process).
    compile_ball: bool = True
    # Analytic paddle face corner radius; matches the drawn paddle. 0 = the Stage 2 square face.
    paddle_corner_radius: float = PADDLE_CORNER_RADIUS
    refeed_delay_s: float = REFEED_DELAY_S
    targets: bool = False  # sample a landing target per feed (aiming tasks)
    target_mode: str = "random"  # "random" (50/50 per feed), "A" or "B" (forced; evaluation)
    # Feed geometry reference: "start" = fixed ROBOT_START (Stage 2-4); "pelvis" = the robot's
    # current pelvis position (footwork tasks), read from qpos so it is valid right after a reset.
    feed_anchor: str = "start"
    recovery: bool = False  # sample a recovery spot per feed (footwork tasks)
    recovery_mode: str = "random"  # "random" (RECOVERY_BOX) or "fixed" (RECOVERY_FIXED; evaluation)
    move_prob: float = 0.0  # Drill 1 (D-041): fraction of robot episodes that are move-to-spot episodes
    # Drill 1 spot-direction weights per sector (0 = toward the net, counter-clockwise); None = uniform.
    move_sector_weights: tuple | None = None
    # Adaptive curriculum (D-044): re-weight feed families (by legal return) and move sectors (by arrival)
    # toward what is unmastered or still changing. Training only; evaluation turns it off.
    adaptive_curriculum: bool = False
    # Drill 2 (shadow swing at a ghost ball): fraction of robot episodes, and the family mix they use.
    swing_prob: float = 0.0
    swing_mix: FeedMix | None = None
    swing_hint: bool = False  # S-D2b: show the predicted interception spot through the spot input before the swing
    swing_follow_hint: bool = False  # S-D2c: walking-teacher reward toward the hint until the ghost ball bounces
    # Drill 3 (stage5-sd2c-videos.md):
    hint_v2: bool = False  # interception near the top of the bounce; stance spots may be behind the baseline
    hit_hint: bool = False  # real-ball episodes also show the stance hint until the first contact
    hit_hint_prob: float = 1.0  # share of real-ball feeds that show it (H4 run 5); the rest must read the ball
    hint_forehand_only: bool = False  # stance hint puts every ball on the forehand side (run around; D-059)
    reach_curriculum: bool = False  # reach families start near (REACH_NEAR) and widen on success
    reach_start: float = 0.0  # initial curriculum scale (0 = near version, 1 = full family)
    reach_near_set: str = "v1"  # "v1" (REACH_NEAR, S-D3) or "v2" (REACH_NEAR_V2, gentler, S-D3b)
    lost_back_margin: float = 0.5  # ball lost this far behind the baseline (Drill 3: room to play deep balls)

    def build(self, env) -> "BallPhysicsAction":
        return BallPhysicsAction(self, env)


class BallPhysicsAction(ActionTerm):
    cfg: BallPhysicsActionCfg

    def __init__(self, cfg: BallPhysicsActionCfg, env):
        super().__init__(cfg, env)
        n, dev = env.num_envs, env.device
        params = BallParams(paddle_corner_radius=cfg.paddle_corner_radius)
        self.sim = CompiledBallSim(params, mode="default") if cfg.compile_ball else BallSim(params)
        z = lambda: torch.zeros(n, 3, device=dev)
        self.ball = BallState(z(), z(), z())
        self.rules = RallyRules(n, dev)
        self.gen = torch.Generator(device=dev).manual_seed(int(cfg.seed) + 7919)
        self.paddle_id = int(self._entity.find_bodies(PADDLE_BODY)[0][0])
        self.body_ids = torch.tensor([int(i) for i in self._entity.find_bodies(("pelvis", "torso_link"))[0]],
                                     device=dev, dtype=torch.long)
        self._fault_eye = torch.eye(len(Fault), dtype=torch.long, device=dev)
        self.all_ids = torch.arange(n, device=dev)
        self._mix = torch.tensor(cfg.feed_mix.vector(), device=dev)
        self._ranges = {a: torch.tensor([getattr(FAMILIES[f], a) for f in FAMILY_NAMES], device=dev)
                        for a in ("start_x", "start_z", "bounce_x", "lateral_y", "flight_time", "spin_y")}
        self.family = torch.zeros(n, dtype=torch.long, device=dev)
        self.gen_target = torch.Generator(device=dev).manual_seed(int(cfg.seed) + 104729)  # own stream
        self.target = torch.zeros(n, dtype=torch.long, device=dev)  # 0 = A, 1 = B
        self._target_xy = torch.tensor(TARGET_CENTRES, device=dev)
        self.placement_now = torch.zeros(n, device=dev)
        self.gen_recover = torch.Generator(device=dev).manual_seed(int(cfg.seed) + 130363)  # own stream
        self.gen_hint = torch.Generator(device=dev).manual_seed(int(cfg.seed) + 155921)  # own stream
        self.recover_xy = torch.tensor(RECOVERY_FIXED, device=dev).repeat(n, 1)
        # Recovery error at the next feed's launch, for feeds the robot hit: histogram (no host sync).
        self.recover_hist = torch.zeros(100, dtype=torch.long, device=dev)
        self.fam_sampler = None
        # Drill 3 reach curriculum: per-family scale between the near version and the full family.
        near_set = REACH_NEAR_V2 if getattr(cfg, "reach_near_set", "v1") == "v2" else REACH_NEAR
        self._ranges_near = {a: torch.tensor([getattr(near_set.get(f, FAMILIES[f]), a) for f in FAMILY_NAMES],
                                             device=dev)
                             for a in ("start_x", "start_z", "bounce_x", "lateral_y", "flight_time", "spin_y")}
        self.reach_scale = torch.ones(len(FAMILY_NAMES), device=dev)
        self.reach_ema = torch.full((len(FAMILY_NAMES),), 0.5, device=dev)
        self.reach_since = torch.zeros(len(FAMILY_NAMES), device=dev)
        if cfg.reach_curriculum:
            for f in REACH_NEAR:
                self.reach_scale[FAMILY_NAMES.index(f)] = cfg.reach_start
        self.hit_rec_true = torch.zeros(n, 2, device=dev)
        self.hit_hint_on = torch.zeros(n, dtype=torch.bool, device=dev)
        if cfg.adaptive_curriculum:
            from picklebot_mj.curriculum import AdaptiveSampler
            self.fam_sampler = AdaptiveSampler(self._mix, device=dev)
        self.drill = None
        if cfg.move_prob > 0.0:
            from picklebot_mj.tasks.move_drill import MoveDrill
            self.drill = MoveDrill(self, cfg.move_prob, cfg.seed, cfg.move_sector_weights)
        self.shadow = None
        if cfg.swing_prob > 0.0:
            from picklebot_mj.tasks.shadow_swing import ShadowSwing
            self.shadow = ShadowSwing(self, cfg.swing_prob, cfg.swing_mix or cfg.feed_mix, cfg.seed, cfg.swing_hint,
                                      cfg.hint_v2)
        # Per-family episode tallies [family, (episodes, contact, legal_return, fall)].
        self.ep_family = torch.zeros(len(FAMILY_NAMES), 4, dtype=torch.long, device=dev)
        # Per-family legal-landing tallies [family, (in A, in B, on the assigned target)].
        self.land_family = torch.zeros(len(FAMILY_NAMES), 3, dtype=torch.long, device=dev)
        # Per-episode flags read by rewards/observations/terminations.
        b = lambda: torch.zeros(n, dtype=torch.bool, device=dev)
        self.hit_done, self.hit_now = b(), b()
        # Ball state just after the first legal contact (court-local), read by return_shaping (H4, D-057).
        self.hit_out_pos = torch.zeros(n, 3, device=dev)
        self.hit_out_vel = torch.zeros(n, 3, device=dev)
        self.return_done, self.return_now = b(), b()
        self.lost_now = b()
        self.wrench = torch.zeros(n, 6, device=dev)
        self._empty = torch.zeros(n, 0, device=dev)
        # Diagnostics: how rallies end (fault code histogram) and legal returns.
        self.fault_counts = torch.zeros(len(Fault), dtype=torch.long, device=dev)
        self.return_count = torch.zeros((), dtype=torch.long, device=dev)
        self.hit_count = torch.zeros((), dtype=torch.long, device=dev)
        self._prev_dead = b()
        # Feeding machine: per-env countdown (s) to the next feed after a rally ends; -1 = idle.
        self.refeed_timer = torch.full((n,), -1.0, device=dev)
        self.tallied = b()  # this feed's outcome already counted
        # Per-feed outcome tallies ("episodes" = feeds), recorded when each feed's rally ends, or at the
        # env reset for a feed still in progress (a fall counts against it). Rates are k / n over feeds.
        self.ep = {k: torch.zeros((), dtype=torch.long, device=dev)
                   for k in ("episodes", "contact", "legal_return", "fall", "env_episodes", "env_falls",
                             "censored")}
        # Contact/landing diagnostics (sums for means; kept small and on-device).
        self.diag = {k: torch.zeros((), device=dev) for k in
                     ("n_contact", "paddle_speed", "paddle_speed_sq", "ball_in_speed", "ball_out_speed",
                      "contact_height", "n_cross", "n_land", "land_x", "land_x_sq", "land_y_abs", "net_clear",
                      "land_in_A", "land_in_B", "target_hit", "placement")}

    # ActionTerm API ---------------------------------------------------------------
    @property
    def action_dim(self) -> int:
        return 0

    @property
    def raw_action(self) -> torch.Tensor:
        return self._empty

    def process_actions(self, actions: torch.Tensor) -> None:
        pass

    def reset(self, env_ids=None) -> None:
        if env_ids is None or isinstance(env_ids, slice):
            env_ids = self.all_ids
        if len(env_ids) == 0:
            return
        if self._env.common_step_counter > 0:
            fell = self._env.termination_manager.get_term("fell_over")[env_ids]
            mask = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
            mask[env_ids] = True
            fell_all = torch.zeros_like(mask)
            fell_all[env_ids] = fell
            # A feed still open at the reset has no outcome yet unless the robot fell: the episode time
            # limit cut it off. Count it as censored, not as a miss (2026-10-06 measurement fix, D-043);
            # feeds ended by a fall still count (as falls).
            open_ = mask & ~self.tallied
            self.ep["censored"] += (open_ & ~fell_all).sum()
            self._tally(open_ & fell_all, fell_all)
            self.ep["env_episodes"] += len(env_ids)  # robot episodes (several feeds each)
            self.ep["env_falls"] += fell.sum()  # includes falls between feeds
        if self.shadow is not None:
            self.shadow.assign(env_ids, self.cfg.move_prob)
        self._feed(env_ids)
        self.rules.begin_from_feed(env_ids, torch.full_like(env_ids, FEEDER_PLAYER), must_bounce=True)
        for f in (self.hit_done, self.hit_now, self.return_done, self.return_now, self.lost_now, self._prev_dead,
                  self.tallied):
            f[env_ids] = False
        self.wrench[env_ids] = 0.0
        self.refeed_timer[env_ids] = -1.0
        if self.drill is not None:
            self.drill.reset(env_ids)
        if self.shadow is not None:
            if self.drill is not None:
                self.shadow.drop_moves(self.drill.move_ep)
            self.tallied |= self.shadow.swing_ep  # ghost-ball feeds are never tallied
            m = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
            m[env_ids] = True
            self.shadow.after_feed(m)
        self._write_mocap(env_ids)

    @property
    def num_envs(self) -> int:
        return self.all_ids.shape[0]

    def _tally(self, mask: torch.Tensor, fell: torch.Tensor) -> None:
        """Count one finished feed for each env in mask (masked sums, no host sync)."""
        m = mask.long()
        outcome = torch.stack([m, (self.hit_done & mask).long(), (self.return_done & mask).long(),
                               (fell & mask).long()], -1)
        self.ep["episodes"] += outcome[:, 0].sum()
        self.ep["contact"] += outcome[:, 1].sum()
        self.ep["legal_return"] += outcome[:, 2].sum()
        self.ep["fall"] += outcome[:, 3].sum()
        self.ep_family.index_add_(0, self.family, outcome)
        if getattr(self.cfg, "reach_curriculum", False):  # widen a reach family once it is mastered at its scale
            m = mask.float()
            n_f = torch.zeros_like(self.reach_ema).index_add_(0, self.family, m)
            s_f = torch.zeros_like(self.reach_ema).index_add_(0, self.family, (self.return_done & mask).float())
            has = n_f > 0
            a = (0.02 * n_f).clamp(max=0.5)
            self.reach_ema = torch.where(has, self.reach_ema + a * (s_f / n_f.clamp(min=1) - self.reach_ema),
                                         self.reach_ema)
            self.reach_since = self.reach_since + n_f
            up = (self.reach_ema > REACH_PROMOTE) & (self.reach_since >= REACH_MIN_FEEDS) & (self.reach_scale < 1.0)
            self.reach_scale = torch.where(up, (self.reach_scale + REACH_STEP).clamp(max=1.0), self.reach_scale)
            self.reach_ema = torch.where(up, torch.full_like(self.reach_ema, 0.4), self.reach_ema)
            self.reach_since = torch.where(up, torch.zeros_like(self.reach_since), self.reach_since)
            log = self._env.extras.setdefault("log", {})
            for f in REACH_NEAR:
                log[f"Curriculum/scale_{f}"] = self.reach_scale[FAMILY_NAMES.index(f)]
        if self.fam_sampler is not None:  # finished feeds: success = legal return
            self.fam_sampler.update(self.family, self.return_done & mask, mask)
            self._mix = self.fam_sampler.weights()
            log = self._env.extras.setdefault("log", {})
            for i, name in enumerate(FAMILY_NAMES):
                if self.fam_sampler.active[i]:
                    log[f"Curriculum/{name}"] = self._mix[i]

    def _refeed(self, fire: torch.Tensor) -> None:
        """New feed for envs in `fire` without resetting the robot (computed for all, selected by mask)."""
        if self.cfg.recovery:  # score the recovery of the feed that just ended (hit feeds only)
            err = (self.pelvis_xy() - self.recover_xy).norm(dim=-1)
            idx = (err.nan_to_num(nan=1e3, posinf=1e3, neginf=0.0) / RECOVERY_BIN).clamp(0, self.recover_hist.shape[0] - 1).long()
            self.recover_hist.index_add_(0, idx, (fire & self.hit_done).long())
        rec_old = self.recover_xy.clone()
        hint_old, true_old = self.hit_hint_on.clone(), self.hit_rec_true.clone()
        pos, vel, spin = self.ball.pos.clone(), self.ball.vel.clone(), self.ball.spin.clone()
        fam_old, tgt_old = self.family.clone(), self.target.clone()
        self._feed(self.all_ids)
        m = fire.unsqueeze(-1)
        self.ball = BallState(torch.where(m, self.ball.pos, pos), torch.where(m, self.ball.vel, vel),
                              torch.where(m, self.ball.spin, spin))
        self.family = torch.where(fire, self.family, fam_old)
        self.target = torch.where(fire, self.target, tgt_old)
        self.recover_xy = torch.where(fire.unsqueeze(-1), self.recover_xy, rec_old)
        self.hit_hint_on = torch.where(fire, self.hit_hint_on, hint_old)
        self.hit_rec_true = torch.where(fire.unsqueeze(-1), self.hit_rec_true, true_old)
        self.rules.begin_from_feed_masked(fire, FEEDER_PLAYER, must_bounce=True)
        for name in ("hit_done", "return_done", "tallied", "_prev_dead"):
            setattr(self, name, getattr(self, name) & ~fire)
        self.refeed_timer = torch.where(fire, torch.full_like(self.refeed_timer, -1.0), self.refeed_timer)

    def _range(self, name, fam):
        """(lo, hi) per env for FeedCfg attribute `name`, gathered by family index."""
        t = self._ranges[name][fam]
        if getattr(self.cfg, "reach_curriculum", False):  # interpolate near -> full by the family's scale
            near = self._ranges_near[name][fam]
            t = near + self.reach_scale[fam].unsqueeze(-1) * (t - near)
        return t[:, 0], t[:, 1]

    def _u(self, name, fam):
        lo, hi = self._range(name, fam)
        return lo + (hi - lo) * torch.rand(fam.shape[0], generator=self.gen, device=self.device)

    def pelvis_xy(self, env_ids=None):
        """Court-local pelvis (root) xy from qpos, valid right after a reset write."""
        d = self._entity.data
        ids = self.all_ids if env_ids is None else env_ids
        return d.data.qpos[ids][:, d.indexing.free_joint_q_adr[:2]] - self._env.scene.env_origins[ids, :2]

    def _anchor(self, env_ids):
        """(x, y) court-local reference for feed geometry, per env in env_ids."""
        if self.cfg.feed_anchor == "start":
            k = len(env_ids)
            return (torch.full((k,), ROBOT_START[0], device=self.device),
                    torch.full((k,), ROBOT_START[1], device=self.device))
        q = self.pelvis_xy(env_ids)
        return q[:, 0], q[:, 1]

    def _feed(self, env_ids):
        k = len(env_ids)
        fam = torch.multinomial(self._mix, k, replacement=True, generator=self.gen)
        if self.shadow is not None:
            fam = self.shadow.family(env_ids, fam)
        self.family[env_ids] = fam
        if self.cfg.target_mode == "random":
            tgt = (torch.rand(k, generator=self.gen_target, device=self.device) < 0.5).long()
        else:
            tgt = torch.full((k,), 0 if self.cfg.target_mode == "A" else 1, dtype=torch.long, device=self.device)
        self.target[env_ids] = tgt
        if self.cfg.recovery_mode == "fixed":
            rec = torch.tensor(RECOVERY_FIXED, device=self.device).repeat(k, 1)
        else:
            u = torch.rand(k, 2, generator=self.gen_recover, device=self.device)
            lo = torch.tensor([RECOVERY_BOX[0][0], RECOVERY_BOX[1][0]], device=self.device)
            hi = torch.tensor([RECOVERY_BOX[0][1], RECOVERY_BOX[1][1]], device=self.device)
            rec = lo + (hi - lo) * u
        self.recover_xy[env_ids] = rec
        x0, z0 = self._u("start_x", fam), self._u("start_z", fam)
        ax, ay = self._anchor(env_ids)
        y = (ay + self._u("lateral_y", fam)).clamp(-FEED_Y_MAX, FEED_Y_MAX)
        bx = (self._u("bounce_x", fam) + (ax - ROBOT_START[0])).clamp(min=BOUNCE_AIM_MIN)
        t = self._u("flight_time", fam)
        vx = (bx - x0) / t
        vz = (BALL_RADIUS - z0 + 0.5 * 9.81 * t * t) / t
        self.ball.pos[env_ids] = torch.stack([x0, y, z0], -1)
        self.ball.vel[env_ids] = torch.stack([vx, torch.zeros_like(vx), vz], -1)
        # spin_y > 0 is topspin for travel toward -x, i.e. world angular velocity about -y.
        self.ball.spin[env_ids] = torch.stack([torch.zeros_like(vx), -self._u("spin_y", fam), torch.zeros_like(vx)], -1)
        if getattr(self.cfg, "hit_hint", False):  # real-ball episodes: stance hint until the first contact
            from picklebot_mj.tasks.shadow_swing import stance_spot
            hit_ep = torch.ones(k, dtype=torch.bool, device=self.device)
            if self.shadow is not None:
                hit_ep &= ~self.shadow.swing_ep[env_ids]
            if getattr(self.cfg, "hit_hint_prob", 1.0) < 1.0:
                hit_ep &= torch.rand(k, generator=self.gen_hint, device=self.device) < self.cfg.hit_hint_prob
            spot = stance_spot(self, self.cfg.hint_v2)[env_ids]
            self.hit_rec_true[env_ids] = rec
            self.hit_hint_on[env_ids] = hit_ep
            self.recover_xy[env_ids] = torch.where(hit_ep.unsqueeze(-1), spot, rec)

    def apply_actions(self) -> None:
        env = self._env
        dt = env.physics_dt
        origins = env.scene.env_origins
        data = self._entity.data
        pose = data.body_link_pose_w[:, self.paddle_id]
        vel = data.body_link_vel_w[:, self.paddle_id]
        paddle = PaddleState(pose[:, :3] - origins, _quat_to_matrix(pose[:, 3:7]), vel[:, :3], vel[:, 3:6])
        sim_paddle = paddle
        if self.shadow is not None:  # ghost ball: the paddle cannot touch it in swing episodes
            sim_paddle = PaddleState(self.shadow.paddle_for_sim(paddle.pos), paddle.rot, paddle.lin_vel,
                                     paddle.ang_vel)
        live = ~self.rules.dead
        before = self.ball
        self.ball, ev = self.sim.step(self.ball, dt, self.cfg.ball_substeps, sim_paddle, adaptive=False)
        # Freeze balls of finished rallies (they are reset with the episode).
        keep = (~live).unsqueeze(-1)
        self.ball = BallState(torch.where(keep, before.pos, self.ball.pos), torch.where(keep, before.vel, self.ball.vel),
                              torch.where(keep, before.spin, self.ball.spin))
        # Rules events (court-local).
        hit = ev.paddle_contact & live
        was_hit = self.hit_done.clone()
        self.rules.hit(hit, torch.full_like(self.all_ids, ROBOT_PLAYER))
        legal_hit = hit & ~self.rules.dead & (self.rules.last_hitter == ROBOT_PLAYER)
        first = legal_hit & ~was_hit
        if True:  # no host sync: masked sums
            f = first.float()
            ps = paddle.lin_vel.norm(dim=-1)
            d = self.diag
            d["n_contact"] += f.sum()
            d["paddle_speed"] += (ps * f).sum()
            d["paddle_speed_sq"] += (ps * ps * f).sum()
            d["ball_in_speed"] += (before.vel.norm(dim=-1) * f).sum()
            d["ball_out_speed"] += (self.ball.vel.norm(dim=-1) * f).sum()
            d["contact_height"] += (self.ball.pos[:, 2] * f).sum()
        self.hit_now |= first
        self.hit_out_pos = torch.where(first.unsqueeze(-1), self.ball.pos, self.hit_out_pos)
        self.hit_out_vel = torch.where(first.unsqueeze(-1), self.ball.vel, self.hit_out_vel)
        if getattr(self.cfg, "hit_hint", False):  # after the contact the spot input is the recovery spot again
            back = first & self.hit_hint_on
            self.recover_xy = torch.where(back.unsqueeze(-1), self.hit_rec_true, self.recover_xy)
            self.hit_hint_on &= ~first
        self.hit_done |= legal_hit
        # Height above the net when the returned ball crosses x = 0 (first crossing after the hit).
        crossing = self.hit_done & (before.pos[:, 0] < 0) & (self.ball.pos[:, 0] >= 0)
        if True:
            clear = self.ball.pos[:, 2] - BALL_RADIUS - court.NET_CENTER_HEIGHT
            self.diag["net_clear"] += (clear * crossing.float()).sum()
            self.diag["n_cross"] += crossing.float().sum()
        bounce = ev.court_contact & live & ~self.rules.dead
        self.rules.bounce(bounce, ev.court_point[..., :2].nan_to_num(0.0))
        ret = bounce & self.hit_done & ~self.rules.dead & self.rules.bounced & (self.rules.expected_team == 1)
        self.return_now |= ret & ~self.return_done
        self.return_done |= ret
        if True:
            r = ret.float()
            lp = ev.court_point.nan_to_num(0.0)
            self.diag["n_land"] += r.sum()
            self.diag["land_x"] += (lp[:, 0] * r).sum()
            self.diag["land_x_sq"] += (lp[:, 0] ** 2 * r).sum()
            self.diag["land_y_abs"] += (lp[:, 1].abs() * r).sum()
            dA = (lp[:, :2] - self._target_xy[0]).norm(dim=-1)
            dB = (lp[:, :2] - self._target_xy[1]).norm(dim=-1)
            dT = torch.where(self.target == 0, dA, dB)
            self.diag["land_in_A"] += ((dA <= TARGET_RADIUS).float() * r).sum()
            self.diag["land_in_B"] += ((dB <= TARGET_RADIUS).float() * r).sum()
            self.diag["target_hit"] += ((dT <= TARGET_RADIUS).float() * r).sum()
            lands = torch.stack([dA <= TARGET_RADIUS, dB <= TARGET_RADIUS, dT <= TARGET_RADIUS], -1) & ret.unsqueeze(-1)
            self.land_family.index_add_(0, self.family, lands.long())
            bonus = PLACEMENT_MAX * (1.0 - dT / PLACEMENT_RANGE).clamp(min=0.0) * r  # legal landings only
            self.diag["placement"] += bonus.sum()
            if self.cfg.targets:
                self.placement_now = self.placement_now + bonus
        self.rules.permanent_object(ev.post_contact & live)
        # Ball touching the robot body (approximate: pelvis/torso spheres).
        body = data.body_link_pose_w[:, self.body_ids, :3] - origins.unsqueeze(1)
        near_body = ((body - self.ball.pos.unsqueeze(1)).norm(dim=-1) < BODY_RADIUS + BALL_RADIUS).any(-1)
        self.rules.body_contact(near_body & live, torch.full_like(self.all_ids, ROBOT_PLAYER))
        # Lost: behind the robot, wide, or long past the far baseline.
        p = self.ball.pos
        lost = live & ~self.rules.dead & ((p[:, 0] < -court.HALF_LENGTH - self.cfg.lost_back_margin) | (p[:, 1].abs() > court.HALF_WIDTH + 2.0)
                                          | (p[:, 0] > court.HALF_LENGTH + 2.0))
        self.rules.lost(lost)
        self.lost_now |= lost
        newly_dead = self.rules.dead & ~self._prev_dead
        self.fault_counts += (self._fault_eye[self.rules.fault] * newly_dead.long().unsqueeze(-1)).sum(0)
        self.return_count += ret.sum()
        self.hit_count += (legal_hit & ~was_hit).sum()
        self._prev_dead = self.rules.dead.clone()
        if self.shadow is not None:
            self.shadow.step(dt, ev.court_contact & live, paddle.pos, paddle.lin_vel,
                             data.root_link_lin_vel_b[:, :2].norm(dim=-1))
        # Feeding machine: count the finished rally, wait, then feed the next ball (no robot reset).
        over = (self.rules.dead | self.return_done) & ~self.tallied
        self._tally(over, torch.zeros_like(over))
        self.tallied = self.tallied | over
        self.refeed_timer = torch.where(over, torch.full_like(self.refeed_timer, self.cfg.refeed_delay_s),
                                        self.refeed_timer)
        waiting = self.refeed_timer >= 0.0
        self.refeed_timer = torch.where(waiting, self.refeed_timer - dt, self.refeed_timer)
        fire = waiting & (self.refeed_timer <= 0.0)
        self._refeed(fire)
        if self.shadow is not None:
            self.shadow.after_refeed(fire)
        if self.drill is not None:
            self.drill.update(dt)
        # Reaction on the paddle for the next physics step (impulse -> force over dt).
        force = ev.paddle_impulse / dt
        com = data.body_com_pose_w[:, self.paddle_id, :3] - origins
        torque = (ev.paddle_angular_impulse + torch.cross(paddle.pos - com, ev.paddle_impulse, dim=-1)) / dt
        self._entity.write_external_wrench_to_sim(force.unsqueeze(1), torque.unsqueeze(1),
                                                  body_ids=[self.paddle_id])
        self._write_mocap(self.all_ids)

    def _write_mocap(self, env_ids):
        scene = self._env.scene
        ident = torch.zeros(len(env_ids), 4, device=self.device)
        ident[:, 0] = 1.0
        origins = scene.env_origins[env_ids]
        scene["ball"].write_mocap_pose_to_sim(torch.cat([self.ball.pos[env_ids] + origins, ident], -1), env_ids=env_ids)
        scene["court"].write_mocap_pose_to_sim(torch.cat([origins, ident], -1), env_ids=env_ids)

    def consume_step_events(self):
        """Clear one-shot flags after rewards are computed (called by the reward terms' owner)."""
        self.hit_now[:] = False
        self.return_now[:] = False
        self.lost_now[:] = False
        self.placement_now.zero_()


def _term(env) -> BallPhysicsAction:
    return env.action_manager.get_term("ball")


# --------------------------------------------------------------------------------------
# Observations


def ball_pos_b(env) -> torch.Tensor:
    t, robot = _term(env), env.scene["robot"]
    root = robot.data.root_link_pose_w
    return _rotate_inv(root[:, 3:7], t.ball.pos + env.scene.env_origins - root[:, :3])


def ball_vel_b(env) -> torch.Tensor:
    t, robot = _term(env), env.scene["robot"]
    return _rotate_inv(robot.data.root_link_pose_w[:, 3:7], t.ball.vel)


def ball_from_paddle_b(env) -> torch.Tensor:
    t, robot = _term(env), env.scene["robot"]
    root = robot.data.root_link_pose_w
    paddle = robot.data.body_link_pose_w[:, t.paddle_id, :3]
    return _rotate_inv(root[:, 3:7], t.ball.pos + env.scene.env_origins - paddle)


def rally_flags(env) -> torch.Tensor:
    t = _term(env)
    return torch.stack([t.rules.bounced.float(), t.hit_done.float()], -1)


def target_obs(env) -> torch.Tensor:
    """Requested landing target (court-local, scaled to the court half-size)."""
    t = _term(env)
    xy = t._target_xy[t.target]
    return xy / torch.tensor([court.HALF_LENGTH, court.HALF_WIDTH], device=xy.device)


def court_pose_obs(env) -> torch.Tensor:
    """Own court position and heading (pelvis xy scaled to the court half-size, cos/sin yaw)."""
    t, robot = _term(env), env.scene["robot"]
    xy = t.pelvis_xy() / torch.tensor([court.HALF_LENGTH, court.HALF_WIDTH], device=env.device)
    w, x, y, z = robot.data.root_link_pose_w[:, 3:7].unbind(-1)
    yaw = torch.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return torch.cat([xy, torch.stack([torch.cos(yaw), torch.sin(yaw)], -1)], -1)


def recovery_obs(env) -> torch.Tensor:
    """Commanded recovery spot relative to the pelvis, in the body frame (metres / 3)."""
    t, robot = _term(env), env.scene["robot"]
    rel = torch.zeros(env.num_envs, 3, device=env.device)
    rel[:, :2] = t.recover_xy - t.pelvis_xy()
    return _rotate_inv(robot.data.root_link_pose_w[:, 3:7], rel)[:, :2] / 3.0


def recovery_reward(env, std: float = RECOVERY_STD) -> torch.Tensor:
    """Be near the recovery spot between the hit and the next feed (never before the hit)."""
    t = _term(env)
    d = (t.pelvis_xy() - t.recover_xy).norm(dim=-1)
    return torch.exp(-(d / std) ** 2) * t.hit_done.float()


def placement(env) -> torch.Tensor:
    """Placement bonus paid on legal landings (read before legal_return consumes the flags)."""
    return _term(env).placement_now


def ball_spin(env) -> torch.Tensor:
    return _term(env).ball.spin * 0.01


# --------------------------------------------------------------------------------------
# Rewards (mjlab multiplies by step_dt; one-shot events use weight/step_dt scaling)


def paddle_contact(env) -> torch.Tensor:
    return _term(env).hit_now.float()


RETURN_SPEED_REF = 6.0  # m/s toward the net that earns the full speed half of return_shaping
GRAVITY = 9.81


def return_quality(pos: torch.Tensor, vel: torch.Tensor) -> torch.Tensor:
    """Score in [0, 1] of a ball just after contact (court-local; the robot is at x < 0, the net at x = 0):
    half for its speed toward the net (up to RETURN_SPEED_REF), half if its drag-free ballistic path is still
    above the net when it reaches x = 0. Dense guidance between 'touched the ball' and 'legal return'."""
    vx = vel[:, 0]
    speed = (vx / RETURN_SPEED_REF).clamp(0.0, 1.0)
    t = (-pos[:, 0] / vx.clamp(min=1e-3)).clamp(max=10.0)
    z_net = pos[:, 2] + vel[:, 2] * t - 0.5 * GRAVITY * t * t
    clears = ((vx > 0.1) & (z_net - BALL_RADIUS > court.NET_CENTER_HEIGHT)).float()
    return 0.5 * speed + 0.5 * clears


def return_shaping(env) -> torch.Tensor:
    """One-shot at the first legal contact: return_quality of the outgoing ball (read before legal_return)."""
    t = _term(env)
    return return_quality(t.hit_out_pos, t.hit_out_vel) * t.hit_now.float()


def legal_return(env) -> torch.Tensor:
    t = _term(env)
    r = t.return_now.float()
    t.consume_step_events()  # last reward term to read the one-shot flags
    return r


def approach_ball(env, std: float = 0.25) -> torch.Tensor:
    """Dense shaping before contact: paddle face centre close to a bounced ball."""
    t, robot = _term(env), env.scene["robot"]
    paddle = robot.data.body_link_pose_w[:, t.paddle_id, :3] - env.scene.env_origins
    d = (t.ball.pos - paddle).norm(dim=-1)
    active = t.rules.bounced & ~t.hit_done & ~t.rules.dead
    return torch.exp(-(d / std) ** 2) * active.float()


# --------------------------------------------------------------------------------------
# Terminations


BLOWUP_LIN, BLOWUP_ANG = 8.0, 25.0  # m/s, rad/s: far beyond anything the G1 does on purpose


def blew_up(env) -> torch.Tensor:
    """Simulation blow-up guard: base speed or spin out of range, or non-finite state."""
    d = env.scene["robot"].data
    lin, ang = d.root_link_lin_vel_w.norm(dim=-1), d.root_link_ang_vel_w.norm(dim=-1)
    return (lin > BLOWUP_LIN) | (ang > BLOWUP_ANG) | ~torch.isfinite(lin) | ~torch.isfinite(ang)


def drill_over(env) -> torch.Tensor:
    t = _term(env)
    return t.rules.dead | t.return_done


# --------------------------------------------------------------------------------------
# Env config


def _ball_spec() -> mujoco.MjSpec:
    spec = mujoco.MjSpec()
    b = spec.worldbody.add_body(name="ball", mocap=True)
    b.add_geom(type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[BALL_RADIUS, 0, 0], rgba=[0.95, 0.85, 0.1, 1],
               contype=0, conaffinity=0)
    return spec


# Stance release (Stage 5, stage5-motion-audit.md): leg and waist tolerances from mjlab's own
# walking regime; arms as in the standing task (free right arm).
FREE_FEET_POSE_STD = {
    r".*hip_pitch.*": 0.3, r".*hip_roll.*": 0.15, r".*hip_yaw.*": 0.15, r".*knee.*": 0.35,
    r".*ankle_pitch.*": 0.25, r".*ankle_roll.*": 0.1,
    r".*waist_yaw.*": 0.4, r".*waist_(roll|pitch).*": 0.15,
    r"left_.*(shoulder|elbow|wrist).*": 0.3,
    r"right_.*(shoulder|elbow|wrist).*": 3.0,
}


def _release_stance(cfg) -> None:
    """Remove the stand-still incentives; gate foot-quality costs on actual base motion."""
    from picklebot_mj.tasks.footwork_rewards import GATED, SPEED_THRESHOLD

    # (1) Under the zero command these pay for not moving the base (2 + 2 per step at rest).
    cfg.rewards.pop("track_linear_velocity")
    cfg.rewards.pop("track_angular_velocity")
    # (2) The standing tolerances are always active (command 0); use walking tolerances for the legs.
    cfg.rewards["pose"].params["std_standing"] = dict(FREE_FEET_POSE_STD)
    # (3) Foot-quality terms: same weights and parameters, gated on base speed instead of the command.
    for name, func in GATED.items():
        term = cfg.rewards[name]
        params = {k: v for k, v in term.params.items() if k not in ("command_name", "command_threshold")}
        params["speed_threshold"] = SPEED_THRESHOLD
        term.func, term.params = func, params


def return_stand_env_cfg(play: bool = False, targets: bool = False, start_box: bool = False,
                         recovery: bool = False, free_feet: bool = False,
                         wide_shaping: bool = False, move_prob: float = 0.0,
                         swing_prob: float = 0.0, swing_mix: FeedMix | None = None, swing_hint: bool = False,
                         blowup_guard: bool = False, swing_follow_hint: bool = False, hint_v2: bool = False,
                         hit_hint: bool = False, reach_curriculum: bool = False,
                         lost_back_margin: float = 0.5) -> ManagerBasedRlEnvCfg:
    cfg = unitree_g1_flat_env_cfg(play=play)
    robot = get_g1_paddle_cfg()
    # New InitialStateCfg (the original is mjlab's shared keyframe constant). Court-local;
    # env origins are added by the reset event.
    robot.init_state = dataclasses.replace(
        robot.init_state, pos=(ROBOT_START[0], ROBOT_START[1], robot.init_state.pos[2]),
        joint_pos=dict(robot.init_state.joint_pos), joint_vel=dict(robot.init_state.joint_vel))
    cfg.scene.entities = {
        "robot": robot,
        "ball": EntityCfg(spec_fn=_ball_spec),
        "court": EntityCfg(spec_fn=court.court_entity_spec),
    }
    cfg.scene.env_spacing = 20.0
    # Stand still: zero velocity command for every env.
    twist = cfg.commands["twist"]
    assert isinstance(twist, UniformVelocityCommandCfg)
    twist.rel_standing_envs = 1.0
    twist.ranges.lin_vel_x = (0.0, 0.0)
    twist.ranges.lin_vel_y = (0.0, 0.0)
    twist.ranges.ang_vel_z = (0.0, 0.0)
    twist.heading_command = False
    twist.ranges.heading = None
    # The base config's velocity curriculum widens the command ranges during training
    # (run return-stand-01 logged lin_vel_x_max 1.0, ang_vel_z_min -0.5); remove it so the
    # command stays zero.
    cfg.curriculum.pop("command_vel", None)
    # Small start-pose noise only.
    cfg.events["reset_base"].params["pose_range"] = {"x": (-0.05, 0.05), "y": (-0.05, 0.05), "yaw": (-0.1, 0.1)}
    if start_box:  # Stage 5: random start spot per robot episode; feeds follow the robot
        cfg.events["reset_base"].params["pose_range"] = dict(START_BOX)
    cfg.events.pop("push_robot", None)
    # Posture: keep legs and waist near standing, leave the hitting arm free.
    cfg.rewards["pose"].params["std_standing"] = {
        r".*hip.*": 0.15, r".*knee.*": 0.2, r".*ankle.*": 0.1,
        r".*waist_yaw.*": 0.4, r".*waist_(roll|pitch).*": 0.15,
        r"left_.*(shoulder|elbow|wrist).*": 0.3,
        r"right_.*(shoulder|elbow|wrist).*": 3.0,
    }
    if free_feet:
        _release_stance(cfg)
    # Ball physics term after the joint-position term (both run every physics step).
    cfg.actions["ball"] = BallPhysicsActionCfg(seed=0, feed_anchor="pelvis" if start_box else "start")
    for group in ("actor", "critic"):
        terms = cfg.observations[group].terms
        terms["ball_pos"] = ObservationTermCfg(func=ball_pos_b)
        terms["ball_vel"] = ObservationTermCfg(func=ball_vel_b)
        terms["ball_from_paddle"] = ObservationTermCfg(func=ball_from_paddle_b)
        terms["rally_flags"] = ObservationTermCfg(func=rally_flags)
    cfg.observations["critic"].terms["ball_spin"] = ObservationTermCfg(func=ball_spin)
    if targets:  # appended last in both groups (checkpoint expansion pads the trailing columns)
        cfg.actions["ball"].targets = True
        for group in ("actor", "critic"):
            cfg.observations[group].terms["target"] = ObservationTermCfg(func=target_obs)
    if recovery:  # appended last: own court pose (the robot now moves) and the recovery command
        cfg.actions["ball"].recovery = True
        for group in ("actor", "critic"):
            cfg.observations[group].terms["court_pose"] = ObservationTermCfg(func=court_pose_obs)
            cfg.observations[group].terms["recovery"] = ObservationTermCfg(func=recovery_obs)
    step_dt = cfg.sim.mujoco.timestep * cfg.decimation
    cfg.rewards["approach_ball"] = RewardTermCfg(func=approach_ball, weight=2.0)
    cfg.rewards["paddle_contact"] = RewardTermCfg(func=paddle_contact, weight=1.0 / step_dt)
    if targets:  # one-shot bonus; must come before legal_return, which clears the step flags
        cfg.rewards["placement"] = RewardTermCfg(func=placement, weight=1.0 / step_dt)
    if wide_shaping:  # Stage 5 run F2: distance shaping that still informs at 1-3 m (stage5-run-f1.md)
        cfg.rewards["approach_far"] = RewardTermCfg(func=approach_ball, weight=1.0, params={"std": WIDE_SHAPING_STD})
    if recovery:
        cfg.rewards["recovery"] = RewardTermCfg(
            func=recovery_reward, weight=1.0, params={"std": WIDE_SHAPING_STD if wide_shaping else RECOVERY_STD})
    if move_prob > 0.0:  # Drill 1 (D-041): walking teacher toward the spot, arrival and ready stance
        from picklebot_mj.tasks import move_drill as md
        cfg.actions["ball"].move_prob = move_prob
        cfg.rewards["move_track_lin_vel"] = RewardTermCfg(func=md.move_track_lin_vel, weight=2.0)
        cfg.rewards["move_track_yaw"] = RewardTermCfg(func=md.move_track_yaw, weight=2.0)
        cfg.rewards["move_arrival"] = RewardTermCfg(func=md.move_arrival, weight=2.0 / step_dt)
        cfg.rewards["ready_stance"] = RewardTermCfg(func=md.ready_stance, weight=1.0)
    if swing_prob > 0.0:  # Drill 2: one-shot shadow-swing reward at the close of each ghost-ball window
        from picklebot_mj.tasks.shadow_swing import shadow_swing_reward
        cfg.actions["ball"].swing_prob = swing_prob
        cfg.actions["ball"].swing_mix = swing_mix
        cfg.actions["ball"].swing_hint = swing_hint
        cfg.actions["ball"].swing_follow_hint = swing_follow_hint
        cfg.rewards["shadow_swing"] = RewardTermCfg(func=shadow_swing_reward, weight=3.0 / step_dt)
    cfg.rewards["legal_return"] = RewardTermCfg(func=legal_return, weight=5.0 / step_dt)
    b = cfg.actions["ball"]
    b.hint_v2, b.hit_hint, b.reach_curriculum, b.lost_back_margin = hint_v2, hit_hint, reach_curriculum, lost_back_margin
    if blowup_guard:  # end an episode whose base moves or spins impossibly fast (simulation blow-up, S-D2)
        cfg.terminations["blew_up"] = TerminationTermCfg(func=blew_up, time_out=False)
    # No termination on rally end: a feeding machine serves the next ball 0.5 s after each rally,
    # within 8 s episodes that end only on a fall or the time limit. History: as a true termination
    # (lateral-a01) the policy learned lobs that outlast the episode; as a bootstrapped time-out
    # (lateral-a02) the inherited critic diverged (value loss 64) and the policy collapsed.
    cfg.episode_length_s = EPISODE_S if not play else 1e9
    cfg.viewer.body_name = "torso_link"
    return cfg
