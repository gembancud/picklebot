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
from picklebot_mj.ball_sim import BallSim, BallState, PaddleState
from picklebot_mj.g1_paddle import PADDLE_BODY, get_g1_paddle_cfg
from picklebot_mj.rules import Fault, Phase, RallyRules, in_bounds

ROBOT_START = (-5.6, 0.35)  # court-local pelvis position, facing +x (the net)
ROBOT_PLAYER = 0  # near team, player 0
FEEDER_PLAYER = 2  # far team
EPISODE_S = 3.0
BODY_RADIUS = 0.17  # ball within this of the pelvis/torso origins counts as body contact


@dataclass
class FeedCfg:
    """Ballistic aim (no drag) for the feed; aerodynamics then shortens it slightly."""

    # Tuned with scripts/tune_feed.py (analytic ball alone): 100% bounce exactly once
    # before the contact plane; 80% pass it at 0.55-1.15 m (p10-p90 height 0.52-0.66 m).
    start_x: tuple[float, float] = (0.8, 1.2)
    start_z: tuple[float, float] = (1.2, 1.6)
    bounce_x: tuple[float, float] = (-4.6, -4.2)
    # Forehand side (the robot's right is -y): clear of the hip (body-contact radius ~0.21 m)
    # and inside the measured 0.86 m reach.
    lateral_y: tuple[float, float] = (-0.65, -0.30)
    flight_time: tuple[float, float] = (0.8, 0.95)
    topspin: tuple[float, float] = (0.0, 30.0)  # rad/s; applied about -y (topspin for travel toward -x)


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
    feed: FeedCfg = field(default_factory=FeedCfg)
    seed: int = 0

    def build(self, env) -> "BallPhysicsAction":
        return BallPhysicsAction(self, env)


class BallPhysicsAction(ActionTerm):
    cfg: BallPhysicsActionCfg

    def __init__(self, cfg: BallPhysicsActionCfg, env):
        super().__init__(cfg, env)
        n, dev = env.num_envs, env.device
        self.sim = BallSim()
        z = lambda: torch.zeros(n, 3, device=dev)
        self.ball = BallState(z(), z(), z())
        self.rules = RallyRules(n, dev)
        self.gen = torch.Generator(device=dev).manual_seed(int(cfg.seed) + 7919)
        self.paddle_id = int(self._entity.find_bodies(PADDLE_BODY)[0][0])
        self.body_ids = [int(i) for i in self._entity.find_bodies(("pelvis", "torso_link"))[0]]
        self.all_ids = torch.arange(n, device=dev)
        # Per-episode flags read by rewards/observations/terminations.
        b = lambda: torch.zeros(n, dtype=torch.bool, device=dev)
        self.hit_done, self.hit_now = b(), b()
        self.return_done, self.return_now = b(), b()
        self.lost_now = b()
        self.wrench = torch.zeros(n, 6, device=dev)
        self._empty = torch.zeros(n, 0, device=dev)
        # Diagnostics: how rallies end (fault code histogram) and legal returns.
        self.fault_counts = torch.zeros(len(Fault), dtype=torch.long, device=dev)
        self.return_count = torch.zeros((), dtype=torch.long, device=dev)
        self.hit_count = torch.zeros((), dtype=torch.long, device=dev)
        self._prev_dead = b()

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
        self._feed(env_ids)
        self.rules.begin_from_feed(env_ids, torch.full_like(env_ids, FEEDER_PLAYER), must_bounce=True)
        for f in (self.hit_done, self.hit_now, self.return_done, self.return_now, self.lost_now, self._prev_dead):
            f[env_ids] = False
        self.wrench[env_ids] = 0.0
        self._write_mocap(env_ids)

    def _u(self, rng, k):
        lo, hi = rng
        return lo + (hi - lo) * torch.rand(k, generator=self.gen, device=self.device)

    def _feed(self, env_ids):
        f, k = self.cfg.feed, len(env_ids)
        x0, z0 = self._u(f.start_x, k), self._u(f.start_z, k)
        y = ROBOT_START[1] + self._u(f.lateral_y, k)
        bx, t = self._u(f.bounce_x, k), self._u(f.flight_time, k)
        vx = (bx - x0) / t
        vz = (BALL_RADIUS - z0 + 0.5 * 9.81 * t * t) / t
        self.ball.pos[env_ids] = torch.stack([x0, y, z0], -1)
        self.ball.vel[env_ids] = torch.stack([vx, torch.zeros_like(vx), vz], -1)
        # Topspin for travel toward -x is spin about -y.
        self.ball.spin[env_ids] = torch.stack([torch.zeros_like(vx), -self._u(f.topspin, k), torch.zeros_like(vx)], -1)

    def apply_actions(self) -> None:
        env = self._env
        dt = env.physics_dt
        origins = env.scene.env_origins
        data = self._entity.data
        pose = data.body_link_pose_w[:, self.paddle_id]
        vel = data.body_link_vel_w[:, self.paddle_id]
        paddle = PaddleState(pose[:, :3] - origins, _quat_to_matrix(pose[:, 3:7]), vel[:, :3], vel[:, 3:6])
        live = ~self.rules.dead
        before = self.ball
        self.ball, ev = self.sim.step(self.ball, dt, 1, paddle)
        # Freeze balls of finished rallies (they are reset with the episode).
        keep = (~live).unsqueeze(-1)
        self.ball = BallState(torch.where(keep, before.pos, self.ball.pos), torch.where(keep, before.vel, self.ball.vel),
                              torch.where(keep, before.spin, self.ball.spin))
        # Rules events (court-local).
        hit = ev.paddle_contact & live
        was_hit = self.hit_done.clone()
        self.rules.hit(hit, torch.full_like(self.all_ids, ROBOT_PLAYER))
        legal_hit = hit & ~self.rules.dead & (self.rules.last_hitter == ROBOT_PLAYER)
        self.hit_now |= legal_hit & ~was_hit
        self.hit_done |= legal_hit
        bounce = ev.court_contact & live & ~self.rules.dead
        self.rules.bounce(bounce, ev.court_point[..., :2].nan_to_num(0.0))
        ret = bounce & self.hit_done & ~self.rules.dead & self.rules.bounced & (self.rules.expected_team == 1)
        self.return_now |= ret & ~self.return_done
        self.return_done |= ret
        self.rules.permanent_object(ev.post_contact & live)
        # Ball touching the robot body (approximate: pelvis/torso spheres).
        body = data.body_link_pose_w[:, self.body_ids, :3] - origins.unsqueeze(1)
        near_body = ((body - self.ball.pos.unsqueeze(1)).norm(dim=-1) < BODY_RADIUS + BALL_RADIUS).any(-1)
        self.rules.body_contact(near_body & live, torch.full_like(self.all_ids, ROBOT_PLAYER))
        # Lost: behind the robot, wide, or long past the far baseline.
        p = self.ball.pos
        lost = live & ~self.rules.dead & ((p[:, 0] < -court.HALF_LENGTH - 0.5) | (p[:, 1].abs() > court.HALF_WIDTH + 2.0)
                                          | (p[:, 0] > court.HALF_LENGTH + 2.0))
        self.rules.lost(lost)
        self.lost_now |= lost
        newly_dead = self.rules.dead & ~self._prev_dead
        self.fault_counts += torch.bincount(self.rules.fault[newly_dead], minlength=len(Fault))
        self.return_count += ret.sum()
        self.hit_count += (legal_hit & ~was_hit).sum()
        self._prev_dead = self.rules.dead.clone()
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


def ball_spin(env) -> torch.Tensor:
    return _term(env).ball.spin * 0.01


# --------------------------------------------------------------------------------------
# Rewards (mjlab multiplies by step_dt; one-shot events use weight/step_dt scaling)


def paddle_contact(env) -> torch.Tensor:
    return _term(env).hit_now.float()


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


def return_stand_env_cfg(play: bool = False) -> ManagerBasedRlEnvCfg:
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
    cfg.events.pop("push_robot", None)
    # Posture: keep legs and waist near standing, leave the hitting arm free.
    cfg.rewards["pose"].params["std_standing"] = {
        r".*hip.*": 0.15, r".*knee.*": 0.2, r".*ankle.*": 0.1,
        r".*waist_yaw.*": 0.4, r".*waist_(roll|pitch).*": 0.15,
        r"left_.*(shoulder|elbow|wrist).*": 0.3,
        r"right_.*(shoulder|elbow|wrist).*": 3.0,
    }
    # Ball physics term after the joint-position term (both run every physics step).
    cfg.actions["ball"] = BallPhysicsActionCfg(seed=0)
    for group in ("actor", "critic"):
        terms = cfg.observations[group].terms
        terms["ball_pos"] = ObservationTermCfg(func=ball_pos_b)
        terms["ball_vel"] = ObservationTermCfg(func=ball_vel_b)
        terms["ball_from_paddle"] = ObservationTermCfg(func=ball_from_paddle_b)
        terms["rally_flags"] = ObservationTermCfg(func=rally_flags)
    cfg.observations["critic"].terms["ball_spin"] = ObservationTermCfg(func=ball_spin)
    step_dt = cfg.sim.mujoco.timestep * cfg.decimation
    cfg.rewards["approach_ball"] = RewardTermCfg(func=approach_ball, weight=2.0)
    cfg.rewards["paddle_contact"] = RewardTermCfg(func=paddle_contact, weight=1.0 / step_dt)
    cfg.rewards["legal_return"] = RewardTermCfg(func=legal_return, weight=5.0 / step_dt)
    cfg.terminations["drill_over"] = TerminationTermCfg(func=drill_over)
    cfg.episode_length_s = EPISODE_S if not play else 1e9
    cfg.viewer.body_name = "torso_link"
    return cfg
