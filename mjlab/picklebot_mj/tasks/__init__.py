"""mjlab task registrations (discovered through the `mjlab.tasks` entry point)."""

from mjlab.tasks.registry import register_mjlab_task
from mjlab.tasks.velocity.config.g1.rl_cfg import unitree_g1_ppo_runner_cfg

from picklebot_mj.feeds import REACH_FAMILIES, STAGE4_FAMILIES, FeedMix
from picklebot_mj.tasks.return_stand import return_stand_env_cfg

TASK_RETURN_STAND = "Picklebot-Return-Stand-G1"
TASK_RETURN_LATERAL = "Picklebot-Return-Lateral-G1"  # Stage 4 run A: easy + wide forehand + backhand


def _rl_cfg():
    cfg = unitree_g1_ppo_runner_cfg()
    cfg.experiment_name = "picklebot_return_stand"
    return cfg


register_mjlab_task(
    task_id=TASK_RETURN_STAND,
    env_cfg=return_stand_env_cfg(),
    play_env_cfg=return_stand_env_cfg(play=True),
    rl_cfg=_rl_cfg(),
)


def _with_mix(cfg, mix: FeedMix):
    cfg.actions["ball"].feed_mix = mix
    return cfg


LATERAL_MIX = FeedMix({"easy_forehand": 1.0, "wide_forehand": 1.0, "backhand": 1.0})
register_mjlab_task(
    task_id=TASK_RETURN_LATERAL,
    env_cfg=_with_mix(return_stand_env_cfg(), LATERAL_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True), LATERAL_MIX),
    rl_cfg=_rl_cfg(),  # same experiment name, so runs can warm-start from return-stand checkpoints
)

TASK_AIM_LATERAL = "Picklebot-Aim-Lateral-G1"  # Stage 4 run B: lateral mix + landing targets (deep left/right)
register_mjlab_task(
    task_id=TASK_AIM_LATERAL,
    env_cfg=_with_mix(return_stand_env_cfg(targets=True), LATERAL_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, targets=True), LATERAL_MIX),
    rl_cfg=_rl_cfg(),
)

ALL_MIX = FeedMix({name: 1.0 for name in STAGE4_FAMILIES})  # the ten Stage 4 families
TASK_AIM_ALL = "Picklebot-Aim-All-G1"  # Stage 4 run C: all ten feed families (equal weights) + landing targets
register_mjlab_task(
    task_id=TASK_AIM_ALL,
    env_cfg=_with_mix(return_stand_env_cfg(targets=True), ALL_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, targets=True), ALL_MIX),
    rl_cfg=_rl_cfg(),
)

FOOTWORK_MIX = FeedMix({name: 1.0 for name in STAGE4_FAMILIES + REACH_FAMILIES})
TASK_FOOTWORK = "Picklebot-Footwork-G1"  # Stage 5: free feet, random starts, reach feeds, targets + recovery
register_mjlab_task(
    task_id=TASK_FOOTWORK,
    env_cfg=_with_mix(return_stand_env_cfg(targets=True, start_box=True, recovery=True, free_feet=True), FOOTWORK_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, targets=True, start_box=True, recovery=True, free_feet=True),
                           FOOTWORK_MIX),
    rl_cfg=_rl_cfg(),
)

TASK_FOOTWORK_WIDE = "Picklebot-Footwork-Wide-G1"  # Stage 5 run F2: Footwork + wide distance shaping (1.5 m)
_FW = dict(targets=True, start_box=True, recovery=True, free_feet=True, wide_shaping=True)
register_mjlab_task(
    task_id=TASK_FOOTWORK_WIDE,
    env_cfg=_with_mix(return_stand_env_cfg(**_FW), FOOTWORK_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_FW), FOOTWORK_MIX),
    rl_cfg=_rl_cfg(),
)

TASK_DRILL_MOVE = "Picklebot-Drill-Move-G1"  # Stage 5 Drill 1 (D-041): 75 % move-to-spot, 25 % Stage 4 hitting
_D1 = dict(_FW, move_prob=0.75)
register_mjlab_task(
    task_id=TASK_DRILL_MOVE,
    env_cfg=_with_mix(return_stand_env_cfg(**_D1), ALL_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_D1), ALL_MIX),
    rl_cfg=_rl_cfg(),
)

# Drill 1 follow-up D1b (stage5-run-d1.md): oversample the right-side sectors (5 back-right, 6 right,
# 7 forward-right) x2 in training. Evaluation is always uniform (stage2_eval.py).
RIGHT_SIDE_X2 = (1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0)
TASK_DRILL_MOVE_RIGHT = "Picklebot-Drill-Move-Right-G1"


def _drill_right(play=False):
    cfg = _with_mix(return_stand_env_cfg(play=play, **_D1), ALL_MIX)
    cfg.actions["ball"].move_sector_weights = RIGHT_SIDE_X2
    return cfg


register_mjlab_task(task_id=TASK_DRILL_MOVE_RIGHT, env_cfg=_drill_right(), play_env_cfg=_drill_right(True),
                    rl_cfg=_rl_cfg())
