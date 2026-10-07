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

# Drill 1 follow-up D1c (stage5-run-d1b.md): from D1's endpoint, hitting rehearsal 25 % -> 40 % (move_prob 0.60).
TASK_DRILL_MOVE_REHEARSE = "Picklebot-Drill-Move-Rehearse-G1"
_D1C = dict(_FW, move_prob=0.60)
register_mjlab_task(
    task_id=TASK_DRILL_MOVE_REHEARSE,
    env_cfg=_with_mix(return_stand_env_cfg(**_D1C), ALL_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_D1C), ALL_MIX),
    rl_cfg=_rl_cfg(),
)

# Stage 5 specialist teachers (D-042). Same observations as the footwork tasks, so Drill 1 / F2 endpoints warm-start.
TASK_TEACHER_MOVE = "Picklebot-Teacher-Move-G1"  # move-to-spot episodes only, uniform sectors
_TM = dict(_FW, move_prob=1.0)
register_mjlab_task(
    task_id=TASK_TEACHER_MOVE,
    env_cfg=_with_mix(return_stand_env_cfg(**_TM), ALL_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_TM), ALL_MIX),
    rl_cfg=_rl_cfg(),
)

# Hitting only: Stage 4 families + reach_forehand from random starts, targets, recovery, free feet (no move episodes).
HIT_TEACHER_MIX = FeedMix({name: 1.0 for name in STAGE4_FAMILIES + ("reach_forehand",)})
TASK_TEACHER_HIT = "Picklebot-Teacher-Hit-G1"
register_mjlab_task(
    task_id=TASK_TEACHER_HIT,
    env_cfg=_with_mix(return_stand_env_cfg(**_FW), HIT_TEACHER_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_FW), HIT_TEACHER_MIX),
    rl_cfg=_rl_cfg(),
)

# Hitting teacher follow-up HT-b (stage5-teacher-hit.md): backspin weight x3, everything else unchanged.
HIT_TEACHER_BACKSPIN_MIX = FeedMix({name: (3.0 if name == "backspin" else 1.0)
                                    for name in STAGE4_FAMILIES + ("reach_forehand",)})
TASK_TEACHER_HIT_BACKSPIN = "Picklebot-Teacher-Hit-Backspin-G1"
register_mjlab_task(
    task_id=TASK_TEACHER_HIT_BACKSPIN,
    env_cfg=_with_mix(return_stand_env_cfg(**_FW), HIT_TEACHER_BACKSPIN_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_FW), HIT_TEACHER_BACKSPIN_MIX),
    rl_cfg=_rl_cfg(),
)


# Student fine-tunes (D-042): the 1024-512-256 student network and RegPPO (pull-back + critic warm-up,
# configured through PICKLEBOT_REF_* env vars; see picklebot_mj/rl/reg_ppo.py).
STUDENT_HIDDEN = (1024, 512, 256)


def _student_rl_cfg():
    cfg = _rl_cfg()
    cfg.actor.hidden_dims = STUDENT_HIDDEN
    cfg.critic.hidden_dims = STUDENT_HIDDEN
    cfg.algorithm.class_name = "picklebot_mj.rl.reg_ppo:RegPPO"
    return cfg


TASK_STUDENT_DRILL_MOVE = "Picklebot-Student-Drill-Move-G1"  # Drill 1 mix on the student (smoke/maintenance)
register_mjlab_task(
    task_id=TASK_STUDENT_DRILL_MOVE,
    env_cfg=_with_mix(return_stand_env_cfg(**_D1), ALL_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_D1), ALL_MIX),
    rl_cfg=_student_rl_cfg(),
)


# Stage 5 Drill 2 on the student (D-041/D-042): 25 % move-to-spot, 50 % shadow swing at a ghost ball over all
# fourteen families (reach included), 25 % real hitting on the hitting teacher's families.
TASK_STUDENT_SWING = "Picklebot-Student-Swing-G1"
_SW = dict(_FW, move_prob=0.25, swing_prob=0.5, swing_mix=FOOTWORK_MIX)


def _student_finetune_rl_cfg():
    cfg = _student_rl_cfg()
    cfg.algorithm.learning_rate = 1e-4  # gentle fine-tune (see stage5-finetune notes)
    cfg.algorithm.desired_kl = 0.005
    return cfg


register_mjlab_task(
    task_id=TASK_STUDENT_SWING,
    env_cfg=_with_mix(return_stand_env_cfg(**_SW), HIT_TEACHER_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_SW), HIT_TEACHER_MIX),
    rl_cfg=_student_finetune_rl_cfg(),
)


# Drill 2 follow-up S-D2b (stage5-run-sd2.md): show the predicted interception spot through the spot input during
# swing episodes (footwork hint), plus the simulation blow-up guard (bug fix, applied to every later task).
TASK_STUDENT_SWING_HINT = "Picklebot-Student-Swing-Hint-G1"
_SWH = dict(_SW, swing_hint=True, blowup_guard=True)
register_mjlab_task(
    task_id=TASK_STUDENT_SWING_HINT,
    env_cfg=_with_mix(return_stand_env_cfg(**_SWH), HIT_TEACHER_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_SWH), HIT_TEACHER_MIX),
    rl_cfg=_student_finetune_rl_cfg(),
)


# Drill 2 follow-up S-D2c (stage5-run-sd2.md): the walking-teacher tracking rewards also apply in swing episodes,
# toward the interception hint, until the ghost ball bounces (S-D2b showed the hint alone is ignored).
TASK_STUDENT_SWING_FOLLOW = "Picklebot-Student-Swing-Follow-G1"
_SWF = dict(_SWH, swing_follow_hint=True)
register_mjlab_task(
    task_id=TASK_STUDENT_SWING_FOLLOW,
    env_cfg=_with_mix(return_stand_env_cfg(**_SWF), HIT_TEACHER_MIX),
    play_env_cfg=_with_mix(return_stand_env_cfg(play=True, **_SWF), HIT_TEACHER_MIX),
    rl_cfg=_student_finetune_rl_cfg(),
)

# Stage 5 Drill 3 (D-041/D-045, stage5-sd2c-videos.md): real balls with the near-to-far reach curriculum.
# 60 % real hitting over the Stage 4 + reach families (adaptive family mix, reach curriculum, v2 stance hint until
# contact), 15 % move-to-spot and 25 % ghost-ball swings (v2 hint, follow reward) as maintenance; deep balls may be
# played from behind the baseline (lost margin 2.5 m).
from picklebot_mj.feeds import REACH_FAMILIES  # noqa: E402

DRILL3_MIX = FeedMix({name: 1.0 for name in STAGE4_FAMILIES + REACH_FAMILIES})
TASK_STUDENT_DRILL3 = "Picklebot-Student-Drill3-G1"
_D3 = dict(_FW, move_prob=0.15, swing_prob=0.25, swing_mix=FOOTWORK_MIX, swing_hint=True, swing_follow_hint=True,
           blowup_guard=True, hint_v2=True, hit_hint=True, reach_curriculum=True, lost_back_margin=2.5)


def _drill3(play=False):
    cfg = _with_mix(return_stand_env_cfg(play=play, **_D3), DRILL3_MIX)
    cfg.actions["ball"].adaptive_curriculum = True
    return cfg


register_mjlab_task(task_id=TASK_STUDENT_DRILL3, env_cfg=_drill3(), play_env_cfg=_drill3(True),
                    rl_cfg=_student_finetune_rl_cfg())
