"""Agility screen tasks (docs/research/footwork-route-2026-10-29.md section 6). Registered when this module is imported;
picklebot_mj/tasks/__init__.py (the `mjlab.tasks` entry point) does NOT import it, so nothing here reaches other runs.
`train` cannot see these tasks on its own: launch them through scripts/diag/agility_train.py (imports this module,
then calls mjlab's train entry point) or scripts/diag/agility_train_run.sh.

Tasks (each built from a deep copy of an existing registered task; only the ball term and the yaw reward change):
- TASK_AGILITY_RES: rally run 14's task (P = run 18b model_29000 trained on it), lam_r 2 residual, move-only
  (move_prob 1.0, swing_prob 0) with the deadline drill. Arms A0 and A.
- TASK_AGILITY_RES_L3: the same at lam_r 3. Arm B (only if triggered).
- TASK_AGILITY_TEACHER: the flat walking teacher's own task (Picklebot-Teacher-Move-G1) with the deadline drill. Arm F.
- TASK_AGILITY_BALL: rally run 14's task unchanged plus the feeder-ball direction tally (logging only). Ball-side arm.
Second screen (D-172; scripts/diag/agility_screen2.sh): the same three deadline tasks with one change, the drill's
first-entry deadline arrival (deadline_arrival_mode "first_entry"; command law unchanged, it passes the coded positive
control picklebot_mj/agility_control.py):
- TASK_AGILITY2_RES (arms A0, A), TASK_AGILITY2_RES_L3 (arm B), TASK_AGILITY2_TEACHER (arm F).
Ball-index diagnostic (scripts/diag/ballidx51.sh): TASK_AGILITY_BALLIDX, rally run 22b's training task plus the handed-ball
tally (tasks/ball_index.py; PICKLEBOT_BALLIDX_LOG=path, every PICKLEBOT_BALLIDX_LOG_EVERY env steps, default 240).
TASK_AGILITY_BALLIDX_SPLIT (scripts/diag/ballidx52.sh): the same with the split variables (ball_index_split).
TASK_AGILITY_BALLIDX_IDLEREC (D-177, scripts/diag/idlerec53.sh): the ballidx task plus pair_idle_recovery.

Logging: PICKLEBOT_AGILITY_LOG=path appends the cumulative counters every PICKLEBOT_AGILITY_LOG_EVERY env steps
(default 240 = 10 iterations at 24 steps per env; one host sync each time), as PICKLEBOT_PAIR_LOG does.
"""

from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass

import picklebot_mj.tasks as _tasks  # registers the existing tasks (no-op if already imported)
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls, register_mjlab_task

from picklebot_mj.tasks import deadline_drill as dd
from picklebot_mj.tasks.return_stand import BallPhysicsAction, BallPhysicsActionCfg

SRC_RES = _tasks.TASK_LATENT_COURT_V2_RES_PPO_CLEAN_MIX_KA_PAIRS_COOP_MOVES_WEAK_PACE25_LAMR2  # run 14's task
SRC_TEACHER = _tasks.TASK_TEACHER_MOVE

TASK_AGILITY_RES = "Picklebot-Agility-Deadline-LamR2-G1"
TASK_AGILITY_RES_L3 = "Picklebot-Agility-Deadline-LamR3-G1"
TASK_AGILITY_TEACHER = "Picklebot-Agility-Deadline-Teacher-Move-G1"
TASK_AGILITY_BALL = "Picklebot-Agility-DirTally-LamR2-G1"
TASK_AGILITY2_RES = "Picklebot-Agility-Deadline2-LamR2-G1"
TASK_AGILITY2_RES_L3 = "Picklebot-Agility-Deadline2-LamR3-G1"
TASK_AGILITY2_TEACHER = "Picklebot-Agility-Deadline2-Teacher-Move-G1"
LOG_EVERY = 240


@dataclass(kw_only=True)
class AgilityBallActionCfg(BallPhysicsActionCfg):
    deadline_drill: bool = False  # replace MoveDrill by DeadlineMoveDrill (needs move_prob > 0)
    deadline_dist: tuple = dd.DIST_RANGE
    deadline_v_req: tuple = dd.V_REQ_RANGE
    deadline_ends_spot: bool = False  # True: a spot ends at its deadline (as MoveDrill's limit); False: untimed limit
    heading_free_m: float = dd.HEADING_FREE_M
    deadline_arrival_mode: str = "hold"  # "first_entry": deadline arrival = first entry within 0.25 m (D-172)
    direction_tally: bool = False  # feeder-ball outcomes by direction (pair mode)
    ball_index_tally: bool = False  # handed-ball outcomes by rally index, speed, direction, distance (pair mode)
    ball_index_split: bool = False  # + shot-quality and receiver-state variables by k and distance (needs the tally)
    pair_idle_recovery: bool = False  # D-177: spot_progress also while this env has no ball in play (pairs.parked)
    # Body-speed test (tasks/body_speed.py): None keeps MoveDrill exactly; a value swaps in FastMoveDrill with this
    # command cap (gain scaled, braking radius 0.83 m), and optionally its spot distance range / spot box.
    move_cmd_max_speed: float | None = None
    move_dist_range: tuple | None = None
    move_spot_box: tuple | None = None

    def build(self, env) -> "AgilityBallAction":
        return AgilityBallAction(self, env)


class AgilityBallAction(BallPhysicsAction):
    cfg: AgilityBallActionCfg

    def __init__(self, cfg: AgilityBallActionCfg, env):
        super().__init__(cfg, env)
        if cfg.deadline_drill:
            assert self.drill is not None, "the deadline drill needs move_prob > 0"
            self.drill = dd.DeadlineMoveDrill(self, cfg.move_prob, cfg.seed, cfg.move_sector_weights,
                                              dist_range=cfg.deadline_dist, v_req_range=cfg.deadline_v_req,
                                              deadline_ends_spot=cfg.deadline_ends_spot,
                                              heading_free_m=cfg.heading_free_m,
                                              arrival_mode=cfg.deadline_arrival_mode)
        if cfg.move_cmd_max_speed is not None:
            assert self.drill is not None and not cfg.deadline_drill, "the fast move drill needs move_prob > 0"
            from picklebot_mj.tasks.body_speed import FastMoveDrill
            self.drill = FastMoveDrill(self, cfg.move_prob, cfg.seed, cfg.move_sector_weights,
                                       cmd_max_speed=cfg.move_cmd_max_speed, dist_range=cfg.move_dist_range,
                                       spot_box=cfg.move_spot_box)
        self._bs_path = os.environ.get("PICKLEBOT_BODYSPEED_LOG") if cfg.move_cmd_max_speed is not None else None
        self._bs_every = int(os.environ.get("PICKLEBOT_BODYSPEED_LOG_EVERY", str(LOG_EVERY)))
        self._bs_last = -1
        self.dir_tally = dd.DirectionTally(self, env) if cfg.direction_tally else None
        self.ballidx = None
        if cfg.ball_index_tally:
            from picklebot_mj.tasks.ball_index import BallIndexTally
            self.ballidx = BallIndexTally(self, env, split=cfg.ball_index_split)
        assert cfg.ball_index_tally or not cfg.ball_index_split, "ball_index_split needs ball_index_tally"
        self._log_path = os.environ.get("PICKLEBOT_AGILITY_LOG")
        self._log_every = int(os.environ.get("PICKLEBOT_AGILITY_LOG_EVERY", str(LOG_EVERY)))
        self._log_last = -1
        self._bi_path = os.environ.get("PICKLEBOT_BALLIDX_LOG") if self.ballidx is not None else None
        self._bi_every = int(os.environ.get("PICKLEBOT_BALLIDX_LOG_EVERY", str(LOG_EVERY)))
        self._bi_last = -1

    def _ballidx_log(self) -> None:
        """PICKLEBOT_BALLIDX_LOG: the ball-index tally's cumulative counters every PICKLEBOT_BALLIDX_LOG_EVERY env steps
        (one host sync each time)."""
        step = int(self._env.common_step_counter)  # host-side int: no sync
        if step % self._bi_every or step == self._bi_last:
            return
        self._bi_last = step
        from picklebot_mj.tasks.ball_index import META
        with open(self._bi_path, "a") as f:
            f.write(json.dumps({"step": step, "ballidx": self.ballidx.counters(), "ballidx_meta": META}) + "\n")

    def apply_actions(self) -> None:
        super().apply_actions()
        if self._bi_path:
            self._ballidx_log()
        if self._bs_path:  # PICKLEBOT_BODYSPEED_LOG: FastMoveDrill's cumulative per-sector counters
            step = int(self._env.common_step_counter)  # host-side int: no sync
            if step % self._bs_every == 0 and step != self._bs_last:
                self._bs_last = step
                with open(self._bs_path, "a") as f:
                    f.write(json.dumps({"step": step, "body": self.drill.counters()}) + "\n")
        if not self._log_path:
            return
        step = int(self._env.common_step_counter)  # host-side int: no sync
        if step % self._log_every or step == self._log_last:
            return
        self._log_last = step
        row = {"step": step}
        if isinstance(self.drill, dd.DeadlineMoveDrill):
            row["move"] = self.drill.counters()
        if self.dir_tally is not None:
            row["dir"] = self.dir_tally.counters()
        with open(self._log_path, "a") as f:
            f.write(json.dumps(row) + "\n")


def to_agility_ball(cfg, **flags):
    """Swap the env cfg's ball term for an AgilityBallActionCfg with the same field values plus flags."""
    b = cfg.actions["ball"]
    vals = {f.name: getattr(b, f.name) for f in dataclasses.fields(b) if f.init}
    vals.update(flags)
    cfg.actions["ball"] = AgilityBallActionCfg(**vals)
    return cfg


def deadline_task(cfg):
    """Move-only deadline drill (move_prob 1.0, swing_prob 0) on any move-drill task; free-heading yaw reward."""
    to_agility_ball(cfg, deadline_drill=True)
    b = cfg.actions["ball"]
    b.move_prob, b.swing_prob, b.move_sector_weights, b.adaptive_curriculum = 1.0, 0.0, None, False
    assert "move_track_yaw" in cfg.rewards, "not a move-drill task"
    cfg.rewards["move_track_yaw"] = dataclasses.replace(cfg.rewards["move_track_yaw"], func=dd.agility_track_yaw)
    return cfg


def _lam_r(cfg, lam_r: float):
    cfg.actions["latent"] = dataclasses.replace(cfg.actions["latent"], lam_r=lam_r)
    return cfg


def _register(task_id: str, src: str, build):
    register_mjlab_task(task_id=task_id, env_cfg=build(load_env_cfg(src)), play_env_cfg=build(load_env_cfg(src, play=True)),
                        rl_cfg=load_rl_cfg(src), runner_cls=load_runner_cls(src))


_register(TASK_AGILITY_RES, SRC_RES, deadline_task)
_register(TASK_AGILITY_RES_L3, SRC_RES, lambda c: _lam_r(deadline_task(c), _tasks.LAM_R_3))
_register(TASK_AGILITY_TEACHER, SRC_TEACHER, deadline_task)
_register(TASK_AGILITY_BALL, SRC_RES, lambda c: to_agility_ball(c, direction_tally=True))


def first_entry(cfg):
    """D-172: the deadline drill with first-entry deadline arrival (the only change from the first screen's task)."""
    assert cfg.actions["ball"].deadline_drill
    cfg.actions["ball"].deadline_arrival_mode = "first_entry"
    return cfg


_register(TASK_AGILITY2_RES, SRC_RES, lambda c: first_entry(deadline_task(c)))
_register(TASK_AGILITY2_RES_L3, SRC_RES, lambda c: first_entry(_lam_r(deadline_task(c), _tasks.LAM_R_3)))
_register(TASK_AGILITY2_TEACHER, SRC_TEACHER, lambda c: first_entry(deadline_task(c)))

TASK_AGILITY_BALL_S2 = "Picklebot-Agility-DirTally-Stance2-LamR2-G1"
STANCE2_MAX_SPEED = 2.0


def stance_cap(cfg, max_speed: float = STANCE2_MAX_SPEED):
    """D-174: stance_progress pays pelvis speed toward the hitting stance up to max_speed (default 1.0 m/s)."""
    r = cfg.rewards["stance_progress"]
    cfg.rewards["stance_progress"] = dataclasses.replace(r, params={**r.params, "max_speed": max_speed})
    return cfg


_register(TASK_AGILITY_BALL_S2, SRC_RES, lambda c: stance_cap(to_agility_ball(c, direction_tally=True)))

TASK_AGILITY_BALL_CFS = "Picklebot-Agility-DirTally-CourtStance-LamR2-G1"  # D-176: court feeds' own stance target
_register(TASK_AGILITY_BALL_CFS, SRC_RES, lambda c: to_agility_ball(c, direction_tally=True, court_feed_stance=True))

# Ball-index diagnostic (scripts/diag/ballidx51.sh): rally run 22b's training task (drill courts, 120 s episodes) with the
# handed-ball tally on (tasks/ball_index.py; logging only, PICKLEBOT_BALLIDX_LOG). The read-like overrides are passed on
# the command line, as run 22b's are.
SRC_22B = _tasks.TASK_LATENT_COURT_V2_RES_PPO_CLEAN_MIX_KA_PAIRS_COOP_MOVES_WEAK_PACE25_LAMR2_DRILLCOURTS_EP120
TASK_AGILITY_BALLIDX = "Picklebot-Agility-BallIdx-ReadCfg-LamR2-G1"
_register(TASK_AGILITY_BALLIDX, SRC_22B, lambda c: to_agility_ball(c, ball_index_tally=True))
# ballidx52 (scripts/diag/ballidx52.sh): the same plus the split variables (receiver state vs shot quality; logging only)
TASK_AGILITY_BALLIDX_SPLIT = "Picklebot-Agility-BallIdx-Split-ReadCfg-LamR2-G1"
_register(TASK_AGILITY_BALLIDX_SPLIT, SRC_22B, lambda c: to_agility_ball(c, ball_index_tally=True, ball_index_split=True))
# D-177 idle recovery (scripts/diag/idlerec53.sh): the ballidx task plus pair_idle_recovery: spot_progress (same function,
# weight and max_speed) is also active while the env has no ball of its own in play (pairs.parked), toward recover_xy.
TASK_AGILITY_BALLIDX_IDLEREC = "Picklebot-Agility-BallIdx-IdleRec-ReadCfg-LamR2-G1"
_register(TASK_AGILITY_BALLIDX_IDLEREC, SRC_22B,
          lambda c: to_agility_ball(c, ball_index_tally=True, pair_idle_recovery=True))

# Body-speed test (panel round 50, motion reviewer's option F; scripts/diag/bodyspeed54.sh): the flat walking teacher's
# own task with the internal command cap raised to 2.5 m/s (gain scaled, braking radius 0.83 m). To cruise at 2-2.5 m/s
# the spots are 3-5 m away (MoveDrill: 0.5-3 m) inside a box widened behind the baseline and past the sidelines, within
# the floor (court + 4 m runoff); MoveDrill's SPOT_BOX, the 4 x 5.6 m half court, leaves no room for 3-5 m back or
# lateral spots. Episodes last 60 s: 8 s would cut about a third of 3-5 m spots at the episode limit, and 60 s keeps the
# censored share near 5 %. Everything else as Picklebot-Teacher-Move-G1.
TASK_TEACHER_MOVE_FAST25 = "Picklebot-Teacher-Move-Fast25-G1"
FAST25 = dict(move_cmd_max_speed=2.5, move_dist_range=(3.0, 5.0), move_spot_box=((-10.4, -2.4), (-5.5, 5.5)))
FAST25_EPISODE_S = 60.0


def fast25(cfg):
    to_agility_ball(cfg, **FAST25)
    cfg.episode_length_s = max(cfg.episode_length_s, FAST25_EPISODE_S)  # play cfg keeps its own (longer) length
    return cfg


_register(TASK_TEACHER_MOVE_FAST25, SRC_TEACHER, fast25)
