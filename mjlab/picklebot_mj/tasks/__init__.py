"""mjlab task registrations (discovered through the `mjlab.tasks` entry point)."""

from mjlab.tasks.registry import register_mjlab_task
from mjlab.tasks.velocity.config.g1.rl_cfg import unitree_g1_ppo_runner_cfg

from picklebot_mj.feeds import FAMILY_NAMES, FeedMix
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

ALL_MIX = FeedMix({name: 1.0 for name in FAMILY_NAMES})
TASK_AIM_ALL = "Picklebot-Aim-All-G1"  # Stage 4 run C: all ten feed families (equal weights) + landing targets
register_mjlab_task(
    task_id=TASK_AIM_ALL,
    env_cfg=_with_mix(return_stand_env_cfg(targets=True), ALL_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, targets=True), ALL_MIX),
    rl_cfg=_rl_cfg(),
)
