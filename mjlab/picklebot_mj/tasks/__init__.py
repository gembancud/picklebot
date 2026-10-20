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


# Drill 3 follow-up S-D3b (stage5-run-sd3.md): gentler reach curriculum start (REACH_NEAR_V2); everything else as S-D3.
TASK_STUDENT_DRILL3_GENTLE = "Picklebot-Student-Drill3-Gentle-G1"


def _drill3_gentle(play=False):
    cfg = _drill3(play)
    cfg.actions["ball"].reach_near_set = "v2"
    return cfg


register_mjlab_task(task_id=TASK_STUDENT_DRILL3_GENTLE, env_cfg=_drill3_gentle(), play_env_cfg=_drill3_gentle(True),
                    rl_cfg=_student_finetune_rl_cfg())


# Stage 5B tracking teacher (D-044/D-046): mjlab G1 motion tracking on the paddle G1, all accepted Tennis-MoCap clips.
from pathlib import Path  # noqa: E402

from mjlab.tasks.tracking.config.g1.rl_cfg import unitree_g1_tracking_ppo_runner_cfg  # noqa: E402
from mjlab.tasks.tracking.rl import MotionTrackingOnPolicyRunner  # noqa: E402

from picklebot_mj.tasks.tracking import paddle_tracking_env_cfg  # noqa: E402

TASK_TRACKING_TENNIS = "Picklebot-Tracking-Tennis-G1"
TENNIS_MOTION = str(Path(__file__).resolve().parents[2] / "artifacts" / "motion" / "tracking" / "tennis-v5.npz")


def _tracking_rl_cfg():
    cfg = unitree_g1_tracking_ppo_runner_cfg()
    cfg.experiment_name = "picklebot_tracking"
    return cfg


register_mjlab_task(task_id=TASK_TRACKING_TENNIS, env_cfg=paddle_tracking_env_cfg(TENNIS_MOTION),
                    play_env_cfg=paddle_tracking_env_cfg(TENNIS_MOTION, play=True), rl_cfg=_tracking_rl_cfg(),
                    runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5B tracking follow-up 1 (rule 8; stage5b-tracking.md): a wider network, 1024-512-256 actor and critic,
# warm-started from the widened tracking-05 endpoint (scripts/widen_checkpoint.py). Everything else as above.
TASK_TRACKING_TENNIS_BIG = "Picklebot-Tracking-Tennis-Big-G1"


def _tracking_big_rl_cfg():
    cfg = _tracking_rl_cfg()
    cfg.actor.hidden_dims = (1024, 512, 256)
    cfg.critic.hidden_dims = (1024, 512, 256)
    return cfg


register_mjlab_task(task_id=TASK_TRACKING_TENNIS_BIG, env_cfg=paddle_tracking_env_cfg(TENNIS_MOTION),
                    play_env_cfg=paddle_tracking_env_cfg(TENNIS_MOTION, play=True), rl_cfg=_tracking_big_rl_cfg(),
                    runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5B tracking follow-up 2 (rule 8; stage5b-tracking.md): motion preview (reference joints 0.1 s and 0.2 s ahead)
# on top of the wide network, warm-started from tracking-06-wide with the new inputs zero-weighted
# (scripts/expand_checkpoint.py).
from picklebot_mj.tasks.tracking import add_motion_preview  # noqa: E402

TASK_TRACKING_TENNIS_PREVIEW = "Picklebot-Tracking-Tennis-Big-Preview-G1"
register_mjlab_task(task_id=TASK_TRACKING_TENNIS_PREVIEW,
                    env_cfg=add_motion_preview(paddle_tracking_env_cfg(TENNIS_MOTION)),
                    play_env_cfg=add_motion_preview(paddle_tracking_env_cfg(TENNIS_MOTION, play=True)),
                    rl_cfg=_tracking_big_rl_cfg(), runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5B style prior (stage5b-style.md): S-D3b's task plus an AMP-style discriminator reward (picklebot_mj/style.py)
# against the Tennis-MoCap strokes (v5) and LAFAN1 footwork (24 clips). One change: the style reward, weight 0.5.
import os  # noqa: E402
from dataclasses import asdict  # noqa: E402

from mjlab.managers.reward_manager import RewardTermCfg  # noqa: E402

from picklebot_mj.style import StyleCfg, style_reward  # noqa: E402

TASK_STUDENT_DRILL3_STYLE = "Picklebot-Student-Drill3-Style-G1"
_MOTION_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "motion" / "tracking"
STYLE_WEIGHT = 0.5


def _drill3_style(play=False):
    cfg = _drill3_gentle(play)
    style = StyleCfg(motion_files=(str(_MOTION_DIR / "tennis-v5.npz"), str(_MOTION_DIR / "lafan-g1.npz")),
                     save_path=os.environ.get("PICKLEBOT_STYLE_SAVE"),
                     load_path=os.environ.get("PICKLEBOT_STYLE_LOAD"))
    cfg.rewards["style"] = RewardTermCfg(func=style_reward, weight=STYLE_WEIGHT, params={"cfg": style})
    return cfg


register_mjlab_task(task_id=TASK_STUDENT_DRILL3_STYLE, env_cfg=_drill3_style(), play_env_cfg=_drill3_style(True),
                    rl_cfg=_student_finetune_rl_cfg())


# Stage 5B style follow-up 2 (stage5b-style.md): the discriminator does not see the wrist joints (the paddle wrist
# aims the paddle for the task; the clips' wrist angles are a heuristic). Everything else as Drill3-Style.
TASK_STUDENT_DRILL3_STYLE_NOWRIST = "Picklebot-Student-Drill3-Style-NoWrist-G1"


def _drill3_style_nowrist(play=False):
    cfg = _drill3_style(play)
    cfg.rewards["style"].params["cfg"].exclude_joints = (r".*_wrist_(roll|pitch|yaw)_joint",)
    return cfg


register_mjlab_task(task_id=TASK_STUDENT_DRILL3_STYLE_NOWRIST, env_cfg=_drill3_style_nowrist(),
                    play_env_cfg=_drill3_style_nowrist(True), rl_cfg=_student_finetune_rl_cfg())


# Stage 5B H0 (D-050): the wide tracking teacher continued on tennis-v5 + LAFAN1 footwork (24 clips), sampled
# half-and-half by source so the shorter tennis set keeps half of the episode starts.
TASK_TRACKING_TENNIS_LAFAN = "Picklebot-Tracking-TennisLafan-Big-G1"
TENNIS_LAFAN_MOTION = str(_MOTION_DIR / "tennis-lafan.npz")
TENNIS_LAFAN_SHARES = (0.5, 0.5)


def _tracking_tennis_lafan(play=False):
    cfg = paddle_tracking_env_cfg(TENNIS_LAFAN_MOTION, play=play)
    cfg.commands["motion"].source_shares = TENNIS_LAFAN_SHARES
    return cfg


register_mjlab_task(task_id=TASK_TRACKING_TENNIS_LAFAN, env_cfg=_tracking_tennis_lafan(),
                    play_env_cfg=_tracking_tennis_lafan(True), rl_cfg=_tracking_big_rl_cfg(),
                    runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5B H0 follow-up 1 (rule 8): the tennis + LAFAN1 tracker widened to 2048-1024-512 (capacity: the same 1024-wide
# network held 90.5 % on tennis alone but about 77 % with LAFAN1 added). Warm-started from the widened endpoint.
TASK_TRACKING_TENNIS_LAFAN_HUGE = "Picklebot-Tracking-TennisLafan-Huge-G1"


def _tracking_huge_rl_cfg():
    cfg = _tracking_rl_cfg()
    cfg.actor.hidden_dims = (2048, 1024, 512)
    cfg.critic.hidden_dims = (2048, 1024, 512)
    return cfg


register_mjlab_task(task_id=TASK_TRACKING_TENNIS_LAFAN_HUGE, env_cfg=_tracking_tennis_lafan(),
                    play_env_cfg=_tracking_tennis_lafan(True), rl_cfg=_tracking_huge_rl_cfg(),
                    runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5B H0 continuation (D-051): LAFAN1 without jumps1 and multipleActions1 (18 clips), same shares and network.
TASK_TRACKING_TENNIS_LAFAN2_HUGE = "Picklebot-Tracking-TennisLafan2-Huge-G1"
TENNIS_LAFAN2_MOTION = str(_MOTION_DIR / "tennis-lafan2.npz")


def _tracking_tennis_lafan2(play=False):
    cfg = paddle_tracking_env_cfg(TENNIS_LAFAN2_MOTION, play=play)
    cfg.commands["motion"].source_shares = TENNIS_LAFAN_SHARES
    return cfg


register_mjlab_task(task_id=TASK_TRACKING_TENNIS_LAFAN2_HUGE, env_cfg=_tracking_tennis_lafan2(),
                    play_env_cfg=_tracking_tennis_lafan2(True), rl_cfg=_tracking_huge_rl_cfg(),
                    runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5B H3 (D-053): steer the frozen H1 latent controller (latent-07/latent_10651) through its latent; paddle reach.
from picklebot_mj.tasks.latent_reach import latent_reach_env_cfg  # noqa: E402

TASK_LATENT_REACH = "Picklebot-Latent-Reach-G1"
LATENT_CONTROLLER = str(Path(__file__).resolve().parents[2] / "artifacts" / "train" / "latent" / "latent-07"
                        / "latent_10651.pt")


def _latent_reach_rl_cfg():
    cfg = _tracking_rl_cfg()
    cfg.experiment_name = "picklebot_latent"
    return cfg


register_mjlab_task(task_id=TASK_LATENT_REACH, env_cfg=latent_reach_env_cfg(LATENT_CONTROLLER, TENNIS_LAFAN2_MOTION),
                    play_env_cfg=latent_reach_env_cfg(LATENT_CONTROLLER, TENNIS_LAFAN2_MOTION, play=True),
                    rl_cfg=_latent_reach_rl_cfg())


# Stage 5B H3 follow-up 1 (rule 8): the root-target reward widened from a 0.3 m to a 1.0 m Gaussian (at 0.3 m it gives no
# gradient from 1 m away; reach-01 reached 2.3 % of root targets). Everything else as Picklebot-Latent-Reach-G1.
TASK_LATENT_REACH_WIDE = "Picklebot-Latent-Reach-WideRoot-G1"


def _latent_reach_wide(play=False):
    cfg = latent_reach_env_cfg(LATENT_CONTROLLER, TENNIS_LAFAN2_MOTION, play=play)
    cfg.rewards["root"].params = {"std": 1.0}
    return cfg


register_mjlab_task(task_id=TASK_LATENT_REACH_WIDE, env_cfg=_latent_reach_wide(), play_env_cfg=_latent_reach_wide(True),
                    rl_cfg=_latent_reach_rl_cfg())


# Stage 5B H3 follow-up 2 (rule 8): the latent barrier widened, lambda 0.5 -> 1.0 (LATENT's value). With 0.5 the policy
# can move z only half a prior std from the prior mean, and root targets stayed at about 3 %. Otherwise as WideRoot.
TASK_LATENT_REACH_WIDE_L1 = "Picklebot-Latent-Reach-WideRoot-L1-G1"


def _latent_reach_wide_l1(play=False):
    cfg = latent_reach_env_cfg(LATENT_CONTROLLER, TENNIS_LAFAN2_MOTION, play=play, lam=1.0)
    cfg.rewards["root"].params = {"std": 1.0}
    return cfg


register_mjlab_task(task_id=TASK_LATENT_REACH_WIDE_L1, env_cfg=_latent_reach_wide_l1(),
                    play_env_cfg=_latent_reach_wide_l1(True), rl_cfg=_latent_reach_rl_cfg())


# Stage 5B H3 extension (D-055): E1 adds a root progress reward; E2 also penalises the latent action's L2 norm.
from picklebot_mj.tasks.latent_reach import latent_action_l2, root_progress  # noqa: E402

TASK_LATENT_REACH_E1 = "Picklebot-Latent-Reach-E1-G1"
TASK_LATENT_REACH_E2 = "Picklebot-Latent-Reach-E2-G1"


def _latent_reach_e1(play=False):
    cfg = _latent_reach_wide_l1(play)
    cfg.rewards["root_progress"] = RewardTermCfg(func=root_progress, weight=1.0)
    return cfg


def _latent_reach_e2(play=False):
    cfg = _latent_reach_e1(play)
    cfg.rewards["latent_l2"] = RewardTermCfg(func=latent_action_l2, weight=-0.01)
    return cfg


register_mjlab_task(task_id=TASK_LATENT_REACH_E1, env_cfg=_latent_reach_e1(), play_env_cfg=_latent_reach_e1(True),
                    rl_cfg=_latent_reach_rl_cfg())
register_mjlab_task(task_id=TASK_LATENT_REACH_E2, env_cfg=_latent_reach_e2(), play_env_cfg=_latent_reach_e2(True),
                    rl_cfg=_latent_reach_rl_cfg())


# Stage 5B H4 (D-050, D-056): a fresh PPO executor on the Drill 3 task (S-D3b's gentle curriculum, the task of the
# S-D3-style-c baseline without its style reward), acting through the frozen latent controller in H3's action space
# (latent-07/latent_10651, lambda 1.0, wrist residual 0.3, latent L2 penalty 0.01 as in reach-06). The posture
# rewards (pose, ready_stance) are removed: style comes from the decoder.
from picklebot_mj.tasks.latent_reach import LatentJointPositionActionCfg  # noqa: E402

TASK_LATENT_DRILL3 = "Picklebot-Latent-Drill3-G1"
H4_LAMBDA = 1.0


def _latent_drill3(play=False):
    cfg = _drill3_gentle(play)
    jp = cfg.actions["joint_pos"]
    latent = LatentJointPositionActionCfg(entity_name=jp.entity_name, actuator_names=jp.actuator_names,
                                          scale=jp.scale, use_default_offset=jp.use_default_offset,
                                          checkpoint=LATENT_CONTROLLER, lam=H4_LAMBDA)
    cfg.actions = {"latent": latent, "ball": cfg.actions["ball"]}  # the ball term stays after the joint term
    cfg.rewards.pop("pose")
    cfg.rewards.pop("ready_stance")
    cfg.rewards["latent_l2"] = RewardTermCfg(func=latent_action_l2, weight=-0.01)
    # The action is now the raw 35-d latent command, as in H3: use H3's action-rate weight (the inherited -0.1
    # gave -5.5 per episode at the initial action std, swamping the task terms in the smoke run).
    cfg.rewards["action_rate_l2"].weight = -0.01
    return cfg


def _latent_drill3_rl_cfg():
    cfg = _rl_cfg()  # same experiment name as the students, so the gate scripts find the runs
    cfg.actor.hidden_dims = STUDENT_HIDDEN
    cfg.critic.hidden_dims = STUDENT_HIDDEN
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3, env_cfg=_latent_drill3(), play_env_cfg=_latent_drill3(True),
                    rl_cfg=_latent_drill3_rl_cfg())


# H4 run 2 (D-057): the run-1 task plus a one-shot return-shaping reward at the first contact (outgoing speed toward
# the net and a drag-free net-clearance check; picklebot_mj/tasks/return_stand.py return_quality). h4-01 touched 18 %
# of balls at 0.8 m/s paddle speed and never crossed the net; contact and legal_return alone give no signal between.
from picklebot_mj.tasks.return_stand import return_shaping  # noqa: E402

TASK_LATENT_DRILL3_SHAPED = "Picklebot-Latent-Drill3-Shaped-G1"
RETURN_SHAPING_WEIGHT = 2.0  # one-shot, like paddle_contact (1.0) and legal_return (5.0), divided by step_dt


def _latent_drill3_shaped(play=False):
    cfg = _latent_drill3(play)
    step_dt = cfg.sim.mujoco.timestep * cfg.decimation
    legal = cfg.rewards.pop("legal_return")  # legal_return clears the step flags, so it must stay last
    cfg.rewards["return_shaping"] = RewardTermCfg(func=return_shaping, weight=RETURN_SHAPING_WEIGHT / step_dt)
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_SHAPED, env_cfg=_latent_drill3_shaped(),
                    play_env_cfg=_latent_drill3_shaped(True), rl_cfg=_latent_drill3_rl_cfg())


# H4 run 3 (stage5b-h4.md): the run-2 task with the PPO entropy coefficient 0.01 -> 0.001. In h4-01/h4-02 the action
# std rose from 1.0 to 1.30: the latent is squashed by tanh, so extra noise costs almost nothing while the entropy
# bonus keeps paying for it, and training rollouts drown any coordinated swing in noise.
TASK_LATENT_DRILL3_SHAPED_LOWENT = "Picklebot-Latent-Drill3-Shaped-LowEnt-G1"


def _latent_drill3_lowent_rl_cfg():
    cfg = _latent_drill3_rl_cfg()
    cfg.algorithm.entropy_coef = 0.001
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_SHAPED_LOWENT, env_cfg=_latent_drill3_shaped(),
                    play_env_cfg=_latent_drill3_shaped(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 5 (stage5b-h4.md): the run-3/4 task with the stance hint shown on only half of the real-ball feeds.
# h4-04 returns 40.9 % legally with the hint but 3.5 % without it (contact 59 % vs 21 %): it follows the hint and
# never learned to read the ball, because every real-ball training feed showed the hint.
TASK_LATENT_DRILL3_HALFHINT = "Picklebot-Latent-Drill3-HalfHint-G1"
HIT_HINT_PROB = 0.5


def _latent_drill3_halfhint(play=False):
    cfg = _latent_drill3_shaped(play)
    cfg.actions["ball"].hit_hint_prob = HIT_HINT_PROB
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_HALFHINT, env_cfg=_latent_drill3_halfhint(),
                    play_env_cfg=_latent_drill3_halfhint(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 6 (stage5b-h4.md): the stance hint on 20 % of the real-ball feeds (run 5: 50 %). Hiding half the hints
# lifted the no-hint legal return 3.5 % -> 15.7 % without hurting hinted play (40.9 % -> 43.0 %).
TASK_LATENT_DRILL3_FEWHINT = "Picklebot-Latent-Drill3-FewHint-G1"


def _latent_drill3_fewhint(play=False):
    cfg = _latent_drill3_shaped(play)
    cfg.actions["ball"].hit_hint_prob = 0.2
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_FEWHINT, env_cfg=_latent_drill3_fewhint(),
                    play_env_cfg=_latent_drill3_fewhint(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 7 (D-059): the run-6 task with the stance hint placing every ball on the forehand side ("run around the
# backhand"). h4-06 returns the forehand-side families at 66-81 % but backhand at 0 % even with the hint: the hint
# assumed a backhand stroke the executor has not learned, and it just stands while the ball passes on its left.
TASK_LATENT_DRILL3_FHHINT = "Picklebot-Latent-Drill3-FhHint-G1"


def _latent_drill3_fhhint(play=False):
    cfg = _latent_drill3_fewhint(play)
    cfg.actions["ball"].hint_forehand_only = True
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_FHHINT, env_cfg=_latent_drill3_fhhint(),
                    play_env_cfg=_latent_drill3_fhhint(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 8 (D-060): the run-7 task plus a spot-progress reward (pelvis speed toward the spot input whenever that spot
# is meant to be followed). h4-01..07 never arrived at a single move-drill spot (move_arrival 0), ignore the
# 0.8-1.15 m hinted sidestep on backhand feeds, and recover worse each run (0.375 -> 0.825 m).
from picklebot_mj.tasks.return_stand import spot_progress  # noqa: E402

TASK_LATENT_DRILL3_PROGRESS = "Picklebot-Latent-Drill3-Progress-G1"


def _latent_drill3_progress(play=False):
    cfg = _latent_drill3_fhhint(play)
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["spot_progress"] = RewardTermCfg(func=spot_progress, weight=1.0)
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_PROGRESS, env_cfg=_latent_drill3_progress(),
                    play_env_cfg=_latent_drill3_progress(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 9 (D-061): the run-8 task with the episode mix shifted from ghost-ball swings to move-to-spot drills
# (move 0.15 -> 0.35, swing 0.25 -> 0.05; real balls stay at 60 %). No H4 run has ever arrived at a move spot;
# the flat student learned to walk to spots in Drill 1 with 75 % move episodes.
TASK_LATENT_DRILL3_MOVEMIX = "Picklebot-Latent-Drill3-MoveMix-G1"


def _latent_drill3_movemix(play=False):
    cfg = _latent_drill3_progress(play)
    cfg.actions["ball"].move_prob, cfg.actions["ball"].swing_prob = 0.35, 0.05
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_MOVEMIX, env_cfg=_latent_drill3_movemix(),
                    play_env_cfg=_latent_drill3_movemix(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 10 (D-062): the run-9 task plus stance_progress, a privileged footwork-shaping reward (pelvis speed toward
# the feed's forehand-side hitting stance) on un-hinted real-ball feeds before the hit. h4-09 moves when the ball pulls
# it to the right (reach forehand 46 %) but never to the left (backhand and reach backhand 0 %) and ignores abstract
# spots (0 of 2,990 move-drill spots reached).
from picklebot_mj.tasks.return_stand import stance_progress  # noqa: E402

TASK_LATENT_DRILL3_FOOTWORK = "Picklebot-Latent-Drill3-Footwork-G1"


def _latent_drill3_footwork(play=False):
    cfg = _latent_drill3_movemix(play)
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["stance_progress"] = RewardTermCfg(func=stance_progress, weight=1.0)
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_FOOTWORK, env_cfg=_latent_drill3_footwork(),
                    play_env_cfg=_latent_drill3_footwork(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 11 (D-063): the run-10 task plus H3's fall penalty (-50 on a terminating fall). The drill task ends an episode
# on a fall but never penalised it; h4-10 falls in 6.0 % of robot episodes (H3, with the penalty: 0.1 %).
from mjlab.envs import mdp as _mdp  # noqa: E402

TASK_LATENT_DRILL3_FALLPEN = "Picklebot-Latent-Drill3-FallPen-G1"


def _latent_drill3_fallpen(play=False):
    cfg = _latent_drill3_footwork(play)
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["fall"] = RewardTermCfg(func=_mdp.is_terminated, weight=-50.0)
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_FALLPEN, env_cfg=_latent_drill3_fallpen(),
                    play_env_cfg=_latent_drill3_fallpen(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 12 (D-066): run 10's task (h4-10, the best endpoint) with the family-level adaptive mix and the reach
# curriculum replaced by a learning-progress curriculum over (family x difficulty level) units: every family's feed
# ranges are interpolated from an easy end (feeds.LP_EASY) to the full family, and units that are learnable now
# (learning progress, intermediate success) are fed most. Evaluations always use the full families.
TASK_LATENT_DRILL3_LP = "Picklebot-Latent-Drill3-LP-G1"


def _latent_drill3_lp(play=False):
    cfg = _latent_drill3_footwork(play)
    b = cfg.actions["ball"]
    b.adaptive_curriculum, b.reach_curriculum, b.lp_curriculum = False, False, True
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_LP, env_cfg=_latent_drill3_lp(), play_env_cfg=_latent_drill3_lp(True),
                    rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 15 (D-067): the curriculum keeps rehearsing mastered units at full weight (h4-14 forgot easy forehand,
# backspin and high while the sampler moved feeds to backhand and reach short).
TASK_LATENT_DRILL3_LP_REHEARSE = "Picklebot-Latent-Drill3-LP-Rehearse-G1"


def _latent_drill3_lp_rehearse(play=False):
    cfg = _latent_drill3_lp(play)
    cfg.actions["ball"].lp_mastered_weight = 1.0
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_LP_REHEARSE, env_cfg=_latent_drill3_lp_rehearse(),
                    play_env_cfg=_latent_drill3_lp_rehearse(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 16 (D-068): rehearse mastered units at full weight only at their top (full-range) level. h4-15 rehearsed
# every mastered unit, so practice spread over mastered easy levels and the evaluated full-range play decayed.
TASK_LATENT_DRILL3_LP_TOP = "Picklebot-Latent-Drill3-LP-Top-G1"


def _latent_drill3_lp_top(play=False):
    cfg = _latent_drill3_lp_rehearse(play)
    cfg.actions["ball"].lp_rehearse_top_only = True
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_LP_TOP, env_cfg=_latent_drill3_lp_top(),
                    play_env_cfg=_latent_drill3_lp_top(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 18 (D-070): the run-16/17 task with return shaping's net check requiring 0.3 m of predicted clearance.
# h4-17 nets backspin (3,017 wrong-side endings vs 428 for h4-13; mean clearance 0.415 -> 0.19 m) by aiming flat at
# the drag-free edge that the margin-free check rewarded.
TASK_LATENT_DRILL3_MARGIN = "Picklebot-Latent-Drill3-Margin-G1"
NET_MARGIN = 0.3


def _latent_drill3_margin(play=False):
    cfg = _latent_drill3_lp_top(play)
    cfg.rewards["return_shaping"].params = {"margin": NET_MARGIN}
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_MARGIN, env_cfg=_latent_drill3_margin(),
                    play_env_cfg=_latent_drill3_margin(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 21 (D-071): the run-18..20 task plus a one-shot reward for the returned ball's real net clearance when it
# crosses (simulated, so drag and spin are included), graded up to 0.3 m. h4-20 nets backspin again (clearance
# 0.315 -> 0.208 m; wrong side 673 -> 2,701) although return_shaping's drag- and spin-free prediction has a margin.
from picklebot_mj.tasks.return_stand import net_clearance  # noqa: E402

TASK_LATENT_DRILL3_NETREAL = "Picklebot-Latent-Drill3-NetReal-G1"
NET_CLEARANCE_WEIGHT = 1.0  # one-shot, divided by step_dt


def _latent_drill3_netreal(play=False):
    cfg = _latent_drill3_margin(play)
    step_dt = cfg.sim.mujoco.timestep * cfg.decimation
    legal = cfg.rewards.pop("legal_return")  # legal_return clears the step flags, so it must stay last
    cfg.rewards["net_clearance"] = RewardTermCfg(func=net_clearance, weight=NET_CLEARANCE_WEIGHT / step_dt,
                                                 params={"margin": NET_MARGIN})
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_NETREAL, env_cfg=_latent_drill3_netreal(),
                    play_env_cfg=_latent_drill3_netreal(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 22 (D-072): the run-21 task plus a prior-likelihood penalty on the latent (style protection). Style drifted
# 3.08 -> 3.69 over runs 16-20 (limit 3.86) through whole-body posture, not the wrist residual.
from picklebot_mj.tasks.latent_reach import latent_prior_nll  # noqa: E402

TASK_LATENT_DRILL3_PRIOR = "Picklebot-Latent-Drill3-Prior-G1"
PRIOR_NLL_WEIGHT = 0.01  # h4-21 averages sum (lam tanh a)^2 = 7.7 of 32 per step: about 0.6 per episode (legal ~0.85)


def _latent_drill3_prior(play=False):
    cfg = _latent_drill3_netreal(play)
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["latent_prior"] = RewardTermCfg(func=latent_prior_nll, weight=-PRIOR_NLL_WEIGHT)
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_PRIOR, env_cfg=_latent_drill3_prior(),
                    play_env_cfg=_latent_drill3_prior(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# H4 run 23 (D-073): the run-22 task with the prior-likelihood penalty 0.01 -> 0.05. At 0.01 it averaged only -0.10
# per episode and style still rose 3.75 -> 3.82 (limit 3.86).
TASK_LATENT_DRILL3_PRIOR5 = "Picklebot-Latent-Drill3-Prior5-G1"


def _latent_drill3_prior5(play=False):
    cfg = _latent_drill3_prior(play)
    cfg.rewards["latent_prior"].weight = -0.05
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_PRIOR5, env_cfg=_latent_drill3_prior5(),
                    play_env_cfg=_latent_drill3_prior5(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5C agility walker (D-075): the H3 E2 reach task with root targets 1-3 m away in every direction (uniform
# angle and distance), still one target per 2 s (H3: within 1 m), so the walker must move up to 1.5 m/s.
TASK_LATENT_REACH_AGILITY = "Picklebot-Latent-Reach-Agility-G1"


def _latent_reach_agility(play=False):
    cfg = _latent_reach_e2(play)
    cfg.commands["reach"].root_min, cfg.commands["reach"].root_radius = 1.0, 3.0
    return cfg


register_mjlab_task(task_id=TASK_LATENT_REACH_AGILITY, env_cfg=_latent_reach_agility(),
                    play_env_cfg=_latent_reach_agility(True), rl_cfg=_latent_reach_rl_cfg())


# Stage 5C run 7 (D-079): the agility walker on the H1 controller distilled with mirrored LAFAN1 (s5c-06-h1mirror,
# latent_12162, from latent-07). Only the controller changes.
LATENT_CONTROLLER_M = str(Path(__file__).resolve().parents[2] / "artifacts" / "train" / "latent" / "s5c-06-h1mirror"
                          / "latent_12162.pt")
TASK_LATENT_REACH_AGILITY_M = "Picklebot-Latent-Reach-Agility-M-G1"


def _latent_reach_agility_m(play=False):
    cfg = _latent_reach_agility(play)
    cfg.actions["latent"].checkpoint = LATENT_CONTROLLER_M
    return cfg


register_mjlab_task(task_id=TASK_LATENT_REACH_AGILITY_M, env_cfg=_latent_reach_agility_m(),
                    play_env_cfg=_latent_reach_agility_m(True), rl_cfg=_latent_reach_rl_cfg())


# Stage 5C run 8 (D-080): run 1's agility walker (latent-07) with the latent barrier widened, lambda 1 -> 3. At lambda 1
# no tracked clip's latent fits inside the barrier (32 dims, each within one prior std); at 3, 63-83 % of steps do.
TASK_LATENT_REACH_AGILITY_L3 = "Picklebot-Latent-Reach-Agility-L3-G1"


def _latent_reach_agility_l3(play=False):
    cfg = _latent_reach_agility(play)
    cfg.actions["latent"].lam = 3.0
    return cfg


register_mjlab_task(task_id=TASK_LATENT_REACH_AGILITY_L3, env_cfg=_latent_reach_agility_l3(),
                    play_env_cfg=_latent_reach_agility_l3(True), rl_cfg=_latent_reach_rl_cfg())


# Stage 5C court-wide drill (D-076): h4-25b's task (Picklebot-Latent-Drill3-Prior5-G1) over the whole half court.
# Start and recovery spots anywhere from the baseline to the kitchen line, the six court families (drop, lob, cross,
# volleys) added to the feed mix, a learning-progress curriculum per court zone (back / mid / front), volley feeds in
# rally phase, and kitchen rules from the robot's feet.
from picklebot_mj.feeds import COURT_FAMILIES  # noqa: E402
from picklebot_mj.tasks.return_stand import ROBOT_START  # noqa: E402

TASK_LATENT_COURT = "Picklebot-Latent-Court-G1"
COURT_START_X, COURT_START_Y = (-6.4, -2.4), (-2.6, 2.6)  # court-local pelvis start box
COURT_RECOVERY_BOX = ((-6.2, -2.4), (-2.5, 2.5))
COURT_MIX = FeedMix({name: 1.0 for name in STAGE4_FAMILIES + REACH_FAMILIES + COURT_FAMILIES})


def _latent_court(play=False):
    cfg = _latent_drill3_prior5(play)
    b = cfg.actions["ball"]
    b.court_wide, b.recovery_box, b.feed_mix = True, COURT_RECOVERY_BOX, COURT_MIX
    cfg.events["reset_base"].params["pose_range"] = {
        "x": (COURT_START_X[0] - ROBOT_START[0], COURT_START_X[1] - ROBOT_START[0]),
        "y": (COURT_START_Y[0] - ROBOT_START[1], COURT_START_Y[1] - ROBOT_START[1]), "yaw": (-0.3, 0.3)}
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT, env_cfg=_latent_court(), play_env_cfg=_latent_court(True),
                    rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5C controller retrain (D-077): the H0 tracking teacher on tennis-v5 + LAFAN1 + left-right mirrored LAFAN1
# (scripts/motion/mirror_g1_csv.py), sampled 0.5 / 0.25 / 0.25 by source, so locomotion keeps its share and gains
# the leftward and backward stepping the original right-handed / forward-heavy data lacked (D-063, stage5c.md).
TASK_TRACKING_TENNIS_LAFAN3_HUGE = "Picklebot-Tracking-TennisLafan3-Huge-G1"
TENNIS_LAFAN3_MOTION = str(_MOTION_DIR / "tennis-lafan3.npz")
TENNIS_LAFAN3_SHARES = (0.5, 0.25, 0.25)


def _tracking_tennis_lafan3(play=False):
    cfg = paddle_tracking_env_cfg(TENNIS_LAFAN3_MOTION, play=play)
    cfg.commands["motion"].source_shares = TENNIS_LAFAN3_SHARES
    return cfg


register_mjlab_task(task_id=TASK_TRACKING_TENNIS_LAFAN3_HUGE, env_cfg=_tracking_tennis_lafan3(),
                    play_env_cfg=_tracking_tennis_lafan3(True), rl_cfg=_tracking_huge_rl_cfg(),
                    runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5C (D-081): the H0 teacher's motion set gains the walking teacher's own footwork (Picklebot-Teacher-Move-G1,
# model_15900, recorded by scripts/motion/record_policy_clips.py: 128 x 30 s of move-to-spot episodes in uniform
# directions, about equal forward / left / right / back stepping). Sources: tennis-v5, LAFAN1, mirrored LAFAN1,
# footwork, sampled 0.5 / 0.15 / 0.1 / 0.25.
TASK_TRACKING_TENNIS_LAFAN4_HUGE = "Picklebot-Tracking-TennisLafan4-Huge-G1"
TENNIS_LAFAN4_MOTION = str(_MOTION_DIR / "tennis-lafan4.npz")
TENNIS_LAFAN4_SHARES = (0.5, 0.15, 0.1, 0.25)


def _tracking_tennis_lafan4(play=False):
    cfg = paddle_tracking_env_cfg(TENNIS_LAFAN4_MOTION, play=play)
    cfg.commands["motion"].source_shares = TENNIS_LAFAN4_SHARES
    return cfg


register_mjlab_task(task_id=TASK_TRACKING_TENNIS_LAFAN4_HUGE, env_cfg=_tracking_tennis_lafan4(),
                    play_env_cfg=_tracking_tennis_lafan4(True), rl_cfg=_tracking_huge_rl_cfg(),
                    runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5C run 11 (D-081): the agility walker at lambda 3 (run 9's task) on the H1 controller distilled with the
# walking teacher's footwork (s5c-10-h1footwork/latent_12135, from latent-07). Only the controller changes from run 9.
LATENT_CONTROLLER_F = str(Path(__file__).resolve().parents[2] / "artifacts" / "train" / "latent" / "s5c-10-h1footwork"
                          / "latent_12135.pt")
TASK_LATENT_REACH_AGILITY_F_L3 = "Picklebot-Latent-Reach-Agility-F-L3-G1"


def _latent_reach_agility_f_l3(play=False):
    cfg = _latent_reach_agility_l3(play)
    cfg.actions["latent"].checkpoint = LATENT_CONTROLLER_F
    return cfg


register_mjlab_task(task_id=TASK_LATENT_REACH_AGILITY_F_L3, env_cfg=_latent_reach_agility_f_l3(),
                    play_env_cfg=_latent_reach_agility_f_l3(True), rl_cfg=_latent_reach_rl_cfg())


# Stage 5C (D-082): the court-wide executor task with the latent barrier widened, lambda 1 -> 3. At lambda 3 latent-07
# reproduces the walking teacher's leg actions to 0.027 MSE (variance 0.389; lambda 1: 0.072), stage5c-floor-move-l07.json.
# The executor is moved onto it by kickstart distillation (scripts/kickstart_h4.py), then PPO.
TASK_LATENT_COURT_L3 = "Picklebot-Latent-Court-L3-G1"


def _latent_court_l3(play=False):
    cfg = _latent_court(play)
    cfg.actions["latent"].lam = 3.0
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT_L3, env_cfg=_latent_court_l3(), play_env_cfg=_latent_court_l3(True),
                    rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5C (D-082): the Stage 5B drill (h4-25b's task) at lambda 3, for the Stage 5B regression check of lambda-3
# executors (h5c_eval.sh's 6th argument).
TASK_LATENT_DRILL3_PRIOR5_L3 = "Picklebot-Latent-Drill3-Prior5-L3-G1"


def _latent_drill3_prior5_l3(play=False):
    cfg = _latent_drill3_prior5(play)
    cfg.actions["latent"].lam = 3.0
    return cfg


register_mjlab_task(task_id=TASK_LATENT_DRILL3_PRIOR5_L3, env_cfg=_latent_drill3_prior5_l3(),
                    play_env_cfg=_latent_drill3_prior5_l3(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5C (D-086): a volley specialist teacher. The lambda-3 court task with volley feeds only, from start and recovery
# spots in the zones where volleys are fed (mid and front, x >= -5.0), no move or ghost-swing episodes. With volleys a
# few per cent of the full mix and their units at the curriculum floor, no executor has touched a volley (contact <= 0.4 %).
from picklebot_mj.feeds import VOLLEY_FAMILIES, ZONE_X_EDGES  # noqa: E402

TASK_LATENT_COURT_VOLLEY_L3 = "Picklebot-Latent-Court-Volley-L3-G1"


def _latent_court_volley_l3(play=False):
    cfg = _latent_court_l3(play)
    b = cfg.actions["ball"]
    b.feed_mix = FeedMix({f: 1.0 for f in VOLLEY_FAMILIES})
    b.move_prob, b.swing_prob = 0.0, 0.0
    x0 = ZONE_X_EDGES[0]
    b.recovery_box = ((x0, COURT_RECOVERY_BOX[0][1]), COURT_RECOVERY_BOX[1])
    cfg.events["reset_base"].params["pose_range"]["x"] = (x0 + 0.1 - ROBOT_START[0], COURT_START_X[1] - ROBOT_START[0])
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT_VOLLEY_L3, env_cfg=_latent_court_volley_l3(),
                    play_env_cfg=_latent_court_volley_l3(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5C run 19 (D-086): the residual executor. The lambda-3 court task with the latent action term replaced by a
# residual around a frozen two-skill executor (RES_BASE, chosen after run 18's evaluation), lam_r 1, wrist_r 0.1, and the
# prior penalty replaced by the residual penalty (same weight 0.05, 3x in move-to-spot episodes). PICKLEBOT_RES_BASE
# overrides the frozen executor for checks only (the zero-residual reproduction test); training runs use RES_BASE.
import os  # noqa: E402

from picklebot_mj.tasks.latent_reach import ResidualLatentActionCfg, residual_prior_nll  # noqa: E402

TASK_LATENT_COURT_RES = "Picklebot-Latent-Court-Res-G1"
RES_BASE = str(Path(__file__).resolve().parents[2] / "artifacts" / "train" / "logs" / "picklebot_return_stand"
               / "2026-10-16_05-35-35_s5c-18-merge17" / "model_32874.pt")


def _residualize(cfg, lam_r: float = 1.0, base: str | None = None):
    """Replace a lambda-3 task's latent action term by the residual around `base` (default RES_BASE, D-086)."""
    lt = cfg.actions["latent"]
    rl = asdict(_latent_drill3_lowent_rl_cfg())["actor"]
    res = ResidualLatentActionCfg(entity_name=lt.entity_name, actuator_names=lt.actuator_names, scale=lt.scale,
                                  use_default_offset=lt.use_default_offset, checkpoint=lt.checkpoint, lam=lt.lam,
                                  wrist_residual=lt.wrist_residual, latent=lt.latent,
                                  base_checkpoint=os.environ.get("PICKLEBOT_RES_BASE", base or RES_BASE),
                                  base_actor_cfg={k: rl[k] for k in ("activation", "obs_normalization", "distribution_cfg")},
                                  lam_r=lam_r, wrist_r=0.1)
    cfg.actions = {"latent": res, "ball": cfg.actions["ball"]}
    cfg.rewards["latent_prior"] = RewardTermCfg(func=residual_prior_nll, weight=-0.05)
    return cfg


def _latent_court_res(play=False):
    return _residualize(_latent_court_l3(play))


# The Stage 5B drill with the same residual action term: the regression check of residual executors (h5c_eval arg 6).
TASK_LATENT_DRILL3_PRIOR5_RES = "Picklebot-Latent-Drill3-Prior5-Res-G1"


def _latent_drill3_prior5_res(play=False):
    return _residualize(_latent_drill3_prior5_l3(play))


register_mjlab_task(task_id=TASK_LATENT_DRILL3_PRIOR5_RES, env_cfg=_latent_drill3_prior5_res(),
                    play_env_cfg=_latent_drill3_prior5_res(True), rl_cfg=_latent_drill3_lowent_rl_cfg())
register_mjlab_task(task_id=TASK_LATENT_COURT_RES, env_cfg=_latent_court_res(), play_env_cfg=_latent_court_res(True),
                    rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5C run 21 (D-088): the volley specialist as a residual around frozen run 18 (RES_BASE), lam_r 2 so it can reach
# volley motions the base lacks (each latent dim up to 2 prior sigmas from the base's), on the volley-only task.
# Run 20 (plain PPO from the kickstarted run 18) collapsed into falls within 60 iterations, as runs 13-14 had.
TASK_LATENT_COURT_VOLLEY_RES2 = "Picklebot-Latent-Court-Volley-Res2-G1"


def _latent_court_volley_res2(play=False):
    return _residualize(_latent_court_volley_l3(play), lam_r=2.0)


register_mjlab_task(task_id=TASK_LATENT_COURT_VOLLEY_RES2, env_cfg=_latent_court_volley_res2(),
                    play_env_cfg=_latent_court_volley_res2(True), rl_cfg=_latent_drill3_lowent_rl_cfg())



# Stage 5C (D-088): the court drill with run 21's residual space (lam_r 2 around RES_BASE), for merging residual
# specialists into one residual executor (scripts/residual_merge.py) and evaluating it.
TASK_LATENT_COURT_RES2 = "Picklebot-Latent-Court-Res2-G1"


def _latent_court_res2(play=False):
    return _residualize(_latent_court_l3(play), lam_r=2.0)


register_mjlab_task(task_id=TASK_LATENT_COURT_RES2, env_cfg=_latent_court_res2(), play_env_cfg=_latent_court_res2(True),
                    rl_cfg=_latent_drill3_lowent_rl_cfg())

TASK_LATENT_DRILL3_PRIOR5_RES2 = "Picklebot-Latent-Drill3-Prior5-Res2-G1"


def _latent_drill3_prior5_res2(play=False):
    return _residualize(_latent_drill3_prior5_l3(play), lam_r=2.0)


register_mjlab_task(task_id=TASK_LATENT_DRILL3_PRIOR5_RES2, env_cfg=_latent_drill3_prior5_res2(),
                    play_env_cfg=_latent_drill3_prior5_res2(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5C run 22 (D-089): run 19's residual executor task with half the training feeds aimed at the court (anchored at
# the start spot, as in the rally evaluation) instead of at the pelvis, so the robot must get to the ball and back.
TASK_LATENT_COURT_RES_RALLY = "Picklebot-Latent-Court-Res-Rally-G1"


def _latent_court_res_rally(play=False):
    cfg = _latent_court_res(play)
    cfg.actions["ball"].court_anchor_prob = 0.5
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT_RES_RALLY, env_cfg=_latent_court_res_rally(),
                    play_env_cfg=_latent_court_res_rally(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5D (D-092): the rally drill. Run 22's residual executor task with three-quarters of the feeds court-anchored
# (as in the rally evaluation), those feeds sending the robot to the fixed baseline-centre recovery spot, 30 s episodes so
# rallies can build, and a rally bonus at each legal return: 2.5 / step_dt x min(streak, 10) / 10.
from picklebot_mj.tasks.return_stand import rally_bonus  # noqa: E402

TASK_LATENT_COURT_RALLY = "Picklebot-Latent-Court-Rally-G1"


def _rally_settings(cfg, play=False):
    b = cfg.actions["ball"]
    b.court_anchor_prob, b.rally_fixed_recovery = 0.75, True
    if not play:
        cfg.episode_length_s = 30.0
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["rally_bonus"] = RewardTermCfg(func=rally_bonus, weight=2.5 / cfg.sim.mujoco.timestep / cfg.decimation)
    cfg.rewards["legal_return"] = legal
    return cfg


def _latent_court_rally(play=False):
    return _rally_settings(_latent_court_res(play), play)


# The rally drill on the plain lambda-3 action term (no residual): the student task of consolidation runs
# (scripts/consolidate.py, D-092) and of evaluating consolidated executors.
TASK_LATENT_COURT_RALLY_L3 = "Picklebot-Latent-Court-Rally-L3-G1"


def _latent_court_rally_l3(play=False):
    return _rally_settings(_latent_court_l3(play), play)


register_mjlab_task(task_id=TASK_LATENT_COURT_RALLY_L3, env_cfg=_latent_court_rally_l3(),
                    play_env_cfg=_latent_court_rally_l3(True), rl_cfg=_latent_drill3_lowent_rl_cfg())
register_mjlab_task(task_id=TASK_LATENT_COURT_RALLY, env_cfg=_latent_court_rally(), play_env_cfg=_latent_court_rally(True),
                    rl_cfg=_latent_drill3_lowent_rl_cfg())



# Stage 5D run 2 (D-093): the rally drill with a style anchor, the D-072 prior-likelihood penalty on the composite
# latent (weight 0.05, Stage 5B's Prior5 value, which held style at 3.81), next to the residual penalty.
from picklebot_mj.tasks.latent_reach import composite_prior_nll  # noqa: E402

TASK_LATENT_COURT_RALLY_STYLE = "Picklebot-Latent-Court-Rally-Style-G1"


def _latent_court_rally_style(play=False):
    cfg = _latent_court_rally(play)
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["composite_prior"] = RewardTermCfg(func=composite_prior_nll, weight=-0.05)
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT_RALLY_STYLE, env_cfg=_latent_court_rally_style(),
                    play_env_cfg=_latent_court_rally_style(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5D falls fix (D-094): the style-anchored rally drill plus a penalty on pelvis ground speed above 1.2 m/s,
# weight 0.5 ((v - 1.2)^2 per step), aimed at the running falls of the D-092 diagnosis.
from picklebot_mj.tasks.latent_reach import overspeed  # noqa: E402

TASK_LATENT_COURT_RALLY_STYLE_SPEED = "Picklebot-Latent-Court-Rally-Style-Speed-G1"


def _latent_court_rally_style_speed(play=False):
    cfg = _latent_court_rally_style(play)
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["overspeed"] = RewardTermCfg(func=overspeed, weight=-0.5, params={"vmax": 1.2})
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT_RALLY_STYLE_SPEED, env_cfg=_latent_court_rally_style_speed(),
                    play_env_cfg=_latent_court_rally_style_speed(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5D run 3 (D-094): run 1's rally drill (no style anchor) plus the overspeed penalty.
TASK_LATENT_COURT_RALLY_SPEED = "Picklebot-Latent-Court-Rally-Speed-G1"


def _latent_court_rally_speed(play=False):
    cfg = _latent_court_rally(play)
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["overspeed"] = RewardTermCfg(func=overspeed, weight=-0.5, params={"vmax": 1.2})
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT_RALLY_SPEED, env_cfg=_latent_court_rally_speed(),
                    play_env_cfg=_latent_court_rally_speed(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5D run 4 (D-095): run 1's rally drill plus the gait anchor: reward 1.0 x exp(-mean((q - q_walk)^2) / 0.22^2) for
# matching the flat walking teacher's joint action while walking (move episodes; ball episodes before the ball is
# within 1 m, with the teacher walking to the feed's ideal stance spot).
from picklebot_mj.tasks.latent_reach import gait_anchor  # noqa: E402

WALK_TEACHER = str(Path(__file__).resolve().parents[2] / "artifacts" / "train" / "logs" / "picklebot_return_stand"
                   / "2026-10-06_10-30-12_teacher-move-01" / "model_15900.pt")
TASK_LATENT_COURT_RALLY_GAIT = "Picklebot-Latent-Court-Rally-Gait-G1"


def _latent_court_rally_gait(play=False):
    cfg = _latent_court_rally(play)
    rl = asdict(_latent_drill3_lowent_rl_cfg())["actor"]
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["gait_anchor"] = RewardTermCfg(func=gait_anchor, weight=1.0, params={
        "teacher": WALK_TEACHER, "actor_cfg": {k: rl[k] for k in ("activation", "obs_normalization", "distribution_cfg")}})
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT_RALLY_GAIT, env_cfg=_latent_court_rally_gait(),
                    play_env_cfg=_latent_court_rally_gait(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5E (D-097..D-101): rally drill v2 with the stance-spot planner, plus sim-to-real latency and ball-state noise.
# Feeds come from picklebot_mj.drill_v2 (feed groups, no two extremes in a row), court-anchored at the start spot. The
# recovery spot follows the robot's contact position, and the next feed comes 0.2 s after the return lands. The noisy
# planner's spot (picklebot_mj.planner) is shown through the spot input until the first contact. The rally bonus is
# Stage 5D's. The actor's ball observations are 1-2 control steps late (20-40 ms) and noisy (3 cm, 0.15 m/s per axis);
# joint commands are 0-4 physics steps late (0-20 ms). The critic's observations stay exact.
import dataclasses as _dc  # noqa: E402

from picklebot_mj.drill_v2 import REFEED_V2_S  # noqa: E402

SIM2REAL_OBS_LAG = (1, 2)  # control steps (20 ms each)
SIM2REAL_ACT_LAG = (0, 4)  # physics steps (5 ms each)
SIM2REAL_BALL_NOISE = (0.03, 0.15)  # m, m/s per axis


def _sim2real(cfg, obs_lag=SIM2REAL_OBS_LAG, act_lag=SIM2REAL_ACT_LAG, noise=SIM2REAL_BALL_NOISE):
    b = cfg.actions["ball"]
    b.obs_ball_pos_noise, b.obs_ball_vel_noise = noise
    for name in ("ball_pos", "ball_vel", "ball_from_paddle"):
        term = cfg.observations["actor"].terms[name]
        term.params = {**(term.params or {}), "noisy": True}
        term.delay_min_lag, term.delay_max_lag, term.delay_update_period = obs_lag[0], obs_lag[1], 50
    robot = cfg.scene.entities["robot"]  # new articulation and actuator configs (the originals may be shared constants)
    art = robot.articulation
    robot.articulation = _dc.replace(art, actuators=tuple(
        _dc.replace(a, delay_min_lag=act_lag[0], delay_max_lag=act_lag[1], delay_update_period=200)
        for a in art.actuators))
    return cfg


def _drill_v2_settings(cfg, play=False):
    b = cfg.actions["ball"]
    b.drill_v2, b.feed_anchor, b.court_anchor_prob, b.rally_fixed_recovery = True, "start", 0.0, False
    b.lp_curriculum, b.adaptive_curriculum, b.reach_curriculum = False, False, False
    b.refeed_delay_s = REFEED_V2_S
    b.hit_hint, b.planner_mode = False, "noisy"
    if not play:
        cfg.episode_length_s = 30.0
    legal = cfg.rewards.pop("legal_return")  # keep legal_return last (it clears the step flags)
    cfg.rewards["rally_bonus"] = RewardTermCfg(func=rally_bonus, weight=2.5 / cfg.sim.mujoco.timestep / cfg.decimation)
    cfg.rewards["legal_return"] = legal
    return _sim2real(cfg)


# Evaluation tasks of the frozen Stage 5E battery (scripts/h5e_eval.sh): residual executors around RES_BASE (run 22,
# Stage 5D run 1) and plain lambda-3 executors (consolidated bases).
TASK_LATENT_COURT_V2_RES = "Picklebot-Latent-Court-V2-Res-G1"
TASK_LATENT_COURT_V2_L3 = "Picklebot-Latent-Court-V2-L3-G1"


def _latent_court_v2_res(play=False):
    return _drill_v2_settings(_latent_court_res(play), play)


def _latent_court_v2_l3(play=False):
    return _drill_v2_settings(_latent_court_l3(play), play)


register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES, env_cfg=_latent_court_v2_res(),
                    play_env_cfg=_latent_court_v2_res(True), rl_cfg=_latent_drill3_lowent_rl_cfg())
register_mjlab_task(task_id=TASK_LATENT_COURT_V2_L3, env_cfg=_latent_court_v2_l3(),
                    play_env_cfg=_latent_court_v2_l3(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5E footwork check (D-097/D-101): tennis-v5 plus the 100STYLE training part (Neutral FW, BW, SW), sources 0 and
# 1, so tracking_eval.py --per-stroke scores tennis strokes and 4 s windows of the 100STYLE clips. Evaluation only.
TASK_TRACKING_TENNIS_STYLE100 = "Picklebot-Tracking-TennisStyle100-G1"
TENNIS_STYLE100_MOTION = str(_MOTION_DIR / "tennis-style100.npz")


def _tracking_tennis_style100(play=False):
    return paddle_tracking_env_cfg(TENNIS_STYLE100_MOTION, play=play)


register_mjlab_task(task_id=TASK_TRACKING_TENNIS_STYLE100, env_cfg=_tracking_tennis_style100(),
                    play_env_cfg=_tracking_tennis_style100(True), rl_cfg=_tracking_huge_rl_cfg(),
                    runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5E runs 2+ (D-102): residual PPO on drill v2 (sim-to-real on) around the consolidated base of run 1
# (s5e-01-consolidate, its checkpoint at the stop). PICKLEBOT_V2_BASE overrides the base for checks only.
def _s5e_base() -> str:
    logs = Path(__file__).resolve().parents[2] / "artifacts" / "train" / "logs" / "picklebot_return_stand"
    runs = sorted(logs.glob("*_s5e-01-consolidate"))
    cks = sorted(runs[-1].glob("model_*.pt"), key=lambda p: int(p.stem.split("_")[1])) if runs else []
    return str(cks[-1]) if cks else str(logs / "s5e-01-consolidate-missing.pt")


TASK_LATENT_COURT_V2_RESC = "Picklebot-Latent-Court-V2-ResC-G1"


def _latent_court_v2_resc(play=False):
    base = os.environ.get("PICKLEBOT_V2_BASE", _s5e_base())
    return _drill_v2_settings(_residualize(_latent_court_l3(play), base=base), play)




# The Stage 5C battery tasks (court drill, Stage 5B drill) for residual executors around the consolidated base (h5e_eval
# arguments 6 and 7 for runs 2+). No sim-to-real: the Stage 5C battery measures as before (D-101).
TASK_LATENT_COURT_RESC = "Picklebot-Latent-Court-ResC-G1"
TASK_LATENT_DRILL3_PRIOR5_RESC = "Picklebot-Latent-Drill3-Prior5-ResC-G1"


def _latent_court_resc(play=False):
    return _residualize(_latent_court_l3(play), base=os.environ.get("PICKLEBOT_V2_BASE", _s5e_base()))


def _latent_drill3_prior5_resc(play=False):
    return _residualize(_latent_drill3_prior5_l3(play), base=os.environ.get("PICKLEBOT_V2_BASE", _s5e_base()))


register_mjlab_task(task_id=TASK_LATENT_COURT_RESC, env_cfg=_latent_court_resc(), play_env_cfg=_latent_court_resc(True),
                    rl_cfg=_latent_drill3_lowent_rl_cfg())
register_mjlab_task(task_id=TASK_LATENT_DRILL3_PRIOR5_RESC, env_cfg=_latent_drill3_prior5_resc(),
                    play_env_cfg=_latent_drill3_prior5_resc(True), rl_cfg=_latent_drill3_lowent_rl_cfg())


# Stage 5E PPO settings for every run (D-097 loop rule): gamma 0.995, and a critic warm-up. The first CRITIC_WARMUP_ITERS
# PPO updates leave the actor (and its action std) frozen, so the inherited critic adapts to drill v2's rewards and
# dynamics before the policy moves. With the actor frozen its KL is 0, which rsl_rl's adaptive schedule ignores, so the
# learning rate does not drift during the warm-up. PICKLEBOT_CRITIC_WARMUP overrides the count (smoke tests).
from mjlab.rl import MjlabOnPolicyRunner as _MjlabRunner  # noqa: E402

CRITIC_WARMUP_ITERS = 50
S5E_GAMMA = 0.995


def _s5e_rl_cfg():
    cfg = _latent_drill3_lowent_rl_cfg()
    cfg.algorithm.gamma = S5E_GAMMA
    return cfg


class CriticWarmupRunner(_MjlabRunner):
    # D-114: Stage 5F run 3 onward hold the learning rate during the warm-up (CriticWarmupHoldLrRunner). Off here, so
    # the Stage 5E and Stage 5F run 2 tasks keep the behaviour they were trained with (their records stay reproducible).
    hold_lr = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.critic_warmup = int(os.environ.get("PICKLEBOT_CRITIC_WARMUP", CRITIC_WARMUP_ITERS))
        self._warm_updates = 0
        update = self.alg.update

        def warm_update(*a, **k):
            frozen = self._warm_updates < self.critic_warmup
            lr0 = self.alg.learning_rate
            if frozen:
                for p in self.alg.actor.parameters():
                    p.requires_grad_(False)
            try:
                return update(*a, **k)
            finally:
                if frozen:
                    for p in self.alg.actor.parameters():
                        p.requires_grad_(True)
                    if self.hold_lr:  # D-114: the frozen actor's tiny KL (> 0) made the adaptive schedule grow the
                        # learning rate x1.5 per warm-up update (1e-3 -> the 1e-2 cap); the first real update then
                        # ran at 1e-2. Hold the learning rate fixed until the warm-up ends.
                        self.alg.learning_rate = lr0
                        for g in self.alg.optimizer.param_groups:
                            g["lr"] = lr0
                self._warm_updates += 1

        self.alg.update = warm_update


register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RESC, env_cfg=_latent_court_v2_resc(), runner_cls=CriticWarmupRunner,
                    play_env_cfg=_latent_court_v2_resc(True), rl_cfg=_s5e_rl_cfg())


# Stage 5E run 2 (D-103): PPO on drill v2 continuing Stage 5D run 1's residual around RES_BASE (run 18), with the Stage 5E
# PPO settings. Same environment as the evaluation task Picklebot-Latent-Court-V2-Res-G1.
TASK_LATENT_COURT_V2_RES_PPO = "Picklebot-Latent-Court-V2-Res-PPO-G1"
register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES_PPO, env_cfg=_latent_court_v2_res(), runner_cls=CriticWarmupRunner,
                    play_env_cfg=_latent_court_v2_res(True), rl_cfg=_s5e_rl_cfg())


# Stage 5E run 3 (D-104, user decision): mixed-latency training. Ball observations 0-2 control steps late (0-40 ms) and
# joint commands 0-4 physics steps late (0-20 ms), so one policy plays both with and without delay (run 2, trained at
# 20-40 ms only, fell to 26.9 % on the undelayed court drill). Training only: every evaluation task is unchanged.
SIM2REAL_OBS_LAG_MIXED = (0, 2)


def _latent_court_v2_res_mix(play=False):
    return _sim2real(_latent_court_v2_res(play), obs_lag=SIM2REAL_OBS_LAG_MIXED)


TASK_LATENT_COURT_V2_RES_PPO_MIX = "Picklebot-Latent-Court-V2-Res-PPO-Mix-G1"
register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES_PPO_MIX, env_cfg=_latent_court_v2_res_mix(),
                    runner_cls=CriticWarmupRunner, play_env_cfg=_latent_court_v2_res_mix(True), rl_cfg=_s5e_rl_cfg())


# Stage 5E run 4 (D-105, user decision): per-episode latency. Half of the robot episodes are clean (no delay, no ball
# noise), half delayed (ball observations 1-2 control steps late, joint commands 0-4 physics steps late, ball noise on),
# drawn at each reset by the ball term and applied by its observation functions and the latent action term. mjlab's
# per-term delay buffers are off in this task. Training only: every evaluation task is unchanged.
def _latent_court_v2_res_eplat(play=False):
    cfg = _sim2real(_latent_court_v2_res(play), obs_lag=(0, 0), act_lag=(0, 0))
    b = cfg.actions["ball"]
    b.episode_latency, b.episode_latency_prob = True, 0.5
    b.episode_obs_lag, b.episode_cmd_lag = (1, 2), (0, 4)
    return cfg


TASK_LATENT_COURT_V2_RES_PPO_EPLAT = "Picklebot-Latent-Court-V2-Res-PPO-EpLat-G1"
register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES_PPO_EPLAT, env_cfg=_latent_court_v2_res_eplat(),
                    runner_cls=CriticWarmupRunner, play_env_cfg=_latent_court_v2_res_eplat(True), rl_cfg=_s5e_rl_cfg())


# Stage 5F (D-108/D-109/D-111): the ball-latency compensator. The ball term's own history path delays the actor's ball
# observations (so their age is known, as with timestamps on hardware) and rolls them forward with the planner's
# spin-blind model; joint commands are delayed by the latent action term. mjlab's per-term delay buffers are off.
def _own_latency(cfg, prob, obs_lag, cmd_lag, period, compensate):
    cfg = _sim2real(cfg, obs_lag=(0, 0), act_lag=(0, 0))  # keeps the noisy actor terms and the ball-noise levels
    b = cfg.actions["ball"]
    b.episode_latency, b.episode_latency_prob = True, prob
    b.episode_obs_lag, b.episode_cmd_lag, b.obs_lag_period, b.ball_compensate = obs_lag, cmd_lag, period, compensate
    return cfg


# Evaluation tasks for compensating executors. The latency reproduces the frozen D-101 evaluation exactly: every episode
# delayed, ball 1-2 control steps and command 0-4 physics steps, both redrawn every 50 control steps. The court task
# variant is clean by default (as the Stage 5C battery); stage2_eval --grid sets a fixed cell on either.
TASK_LATENT_COURT_V2_RES_COMP = "Picklebot-Latent-Court-V2-Res-Comp-G1"
TASK_LATENT_COURT_RES_COMP = "Picklebot-Latent-Court-Res-Comp-G1"


def _latent_court_v2_res_comp(play=False):
    return _own_latency(_latent_court_v2_res(play), 1.0, (1, 2), (0, 4), 50, True)


def _latent_court_res_comp(play=False):
    return _own_latency(_latent_court_res(play), 0.0, (1, 2), (0, 4), 50, True)


register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES_COMP, env_cfg=_latent_court_v2_res_comp(),
                    play_env_cfg=_latent_court_v2_res_comp(True), rl_cfg=_latent_drill3_lowent_rl_cfg())
register_mjlab_task(task_id=TASK_LATENT_COURT_RES_COMP, env_cfg=_latent_court_res_comp(),
                    play_env_cfg=_latent_court_res_comp(True), rl_cfg=_latent_drill3_lowent_rl_cfg())

# Stage 5F run 1 (training): Stage 5E run 4's per-episode latency (half clean, half delayed; D-105) plus the ball
# compensator, so its one change against that sibling is the compensator.
TASK_LATENT_COURT_V2_RES_PPO_COMP = "Picklebot-Latent-Court-V2-Res-PPO-Comp-G1"


def _latent_court_v2_res_ppo_comp(play=False):
    return _own_latency(_latent_court_v2_res(play), 0.5, (1, 2), (0, 4), 0, True)


register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES_PPO_COMP, env_cfg=_latent_court_v2_res_ppo_comp(),
                    runner_cls=CriticWarmupRunner, play_env_cfg=_latent_court_v2_res_ppo_comp(True),
                    rl_cfg=_s5e_rl_cfg())


def latency_support(cfg) -> set:
    """(ball lag in control steps, command lag in physics steps) pairs a task's actor can meet (D-109 coverage rule).
    Own-history latency: (0, 0) for clean episodes plus every delayed pair; mjlab per-term delays: every pair in their
    ranges (from the first ball term and the first actuator)."""
    b = cfg.actions["ball"]
    if getattr(b, "episode_latency", False):
        out = set()
        if b.episode_latency_prob < 1.0:
            out.add((0, 0))
        if b.episode_latency_prob > 0.0:
            out |= {(o, c) for o in range(b.episode_obs_lag[0], b.episode_obs_lag[1] + 1)
                    for c in range(b.episode_cmd_lag[0], b.episode_cmd_lag[1] + 1)}
        return out
    t = cfg.observations["actor"].terms["ball_pos"]
    a = cfg.scene.entities["robot"].articulation.actuators[0]
    return {(o, c) for o in range(t.delay_min_lag, t.delay_max_lag + 1)
            for c in range(a.delay_min_lag, a.delay_max_lag + 1)}


# Stage 5F H0 delay fine-tune (D-108/D-109/D-111): H0's own task (tennis + LAFAN1, the tracking-20-decay task) with a
# per-episode command delay (30 % of episodes clean, the rest 5-25 ms), the lag shown to the critic only (a trailing
# critic term; the checkpoint's critic is widened with scripts/expand_checkpoint.py). Nothing else changes.
from mjlab.managers.observation_manager import ObservationTermCfg as _ObsTerm  # noqa: E402

from picklebot_mj.tasks.delayed_action import DelayedJointPositionActionCfg, cmd_lag_obs  # noqa: E402

TASK_TRACKING_TENNIS_LAFAN2_HUGE_DELAY = "Picklebot-Tracking-TennisLafan2-Huge-Delay-G1"


def _tracking_tennis_lafan2_delay(play=False):
    cfg = _tracking_tennis_lafan2(play)
    old = cfg.actions["joint_pos"]
    kw = {f.name: getattr(old, f.name) for f in _dc.fields(old) if f.init}
    cfg.actions["joint_pos"] = DelayedJointPositionActionCfg(**kw, p_zero=0.3, max_lag=5)
    cfg.observations["critic"].terms["cmd_lag"] = _ObsTerm(func=cmd_lag_obs, params={"action_name": "joint_pos"})
    return cfg


register_mjlab_task(task_id=TASK_TRACKING_TENNIS_LAFAN2_HUGE_DELAY, env_cfg=_tracking_tennis_lafan2_delay(),
                    play_env_cfg=_tracking_tennis_lafan2_delay(True), rl_cfg=_tracking_huge_rl_cfg(),
                    runner_cls=MotionTrackingOnPolicyRunner)


# Stage 5F executor history (D-108 build; D-109 items 4-5). The actor gets the last EXEC_HISTORY control steps of what
# it issued and saw: its own actions, joint positions and velocities, and its ball estimates (mjlab term history; after a
# reset the history is back-filled with the first frame). The critic gets the same, plus the applied-minus-issued joint
# commands and the episode's lags. All new terms come last, so a parent checkpoint expands with zero-weight inputs
# (scripts/expand_checkpoint.py). Only for own-history latency tasks: mjlab's per-term delay buffers would draw a separate
# lag for each copied term.
from picklebot_mj.tasks.latent_reach import applied_cmd_obs, latency_obs  # noqa: E402

EXEC_HISTORY = 4
HISTORY_TERMS = ("actions", "joint_pos", "joint_vel", "ball_pos", "ball_vel")


def _exec_history(cfg, k: int = EXEC_HISTORY):
    for group in ("actor", "critic"):
        terms = cfg.observations[group].terms
        for name in HISTORY_TERMS:
            assert terms[name].delay_max_lag == 0, "history copies need own-history latency, not per-term delay buffers"
            terms[f"h_{name}"] = _dc.replace(terms[name], history_length=k)
    cfg.observations["critic"].terms["applied_cmd"] = _ObsTerm(func=applied_cmd_obs)
    cfg.observations["critic"].terms["latency"] = _ObsTerm(func=latency_obs)
    return cfg


# Stage 5F run 2 (D-113, user choice): plain PPO of Stage 5D run 1 on drill v2 in the clean simulator. As
# Picklebot-Latent-Court-V2-Res-PPO-G1 (Stage 5E run 2) with no ball or command delay; ball-state noise stays on, the
# condition of the D-113 instrument (grid cell 0/0).
TASK_LATENT_COURT_V2_RES_PPO_CLEAN = "Picklebot-Latent-Court-V2-Res-PPO-Clean-G1"


def _latent_court_v2_res_clean(play=False):
    return _sim2real(_latent_court_v2_res(play), obs_lag=(0, 0), act_lag=(0, 0))


register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES_PPO_CLEAN, env_cfg=_latent_court_v2_res_clean(),
                    runner_cls=CriticWarmupRunner, play_env_cfg=_latent_court_v2_res_clean(True), rl_cfg=_s5e_rl_cfg())


# Stage 5F run 3 (D-114): run 2 with the critic warm-up fixed. Run 2's warm-up let the adaptive schedule raise the
# learning rate 1e-3 -> 1e-2 while the actor was frozen; the first actor update at 1e-2 collapsed legal returns
# (0.67 -> 0.13 per episode in 100 iterations) and the early check killed the run. Only the warm-up changes.
class CriticWarmupHoldLrRunner(CriticWarmupRunner):
    hold_lr = True


TASK_LATENT_COURT_V2_RES_PPO_CLEAN_HOLD = "Picklebot-Latent-Court-V2-Res-PPO-Clean-Hold-G1"
register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES_PPO_CLEAN_HOLD, env_cfg=_latent_court_v2_res_clean(),
                    runner_cls=CriticWarmupHoldLrRunner, play_env_cfg=_latent_court_v2_res_clean(True),
                    rl_cfg=_s5e_rl_cfg())


# Stage 5F run 4 (D-115): shot item 1, ready position and split step. Run 3's task plus a one-shot reward at each refeed
# launch: the soft ready score (both feet down x stance width 0.20 -> 0.35 m) and, at the end of the +-0.25 s window,
# the soft split-step dip score (pelvis drop / 3 cm, capped at 1); picklebot_mj/ready.py. Weight READY_WEIGHT / step_dt
# per part, half a paddle contact each. Inserted before legal_return, which clears the step flags.
from picklebot_mj.tasks.return_stand import ready_reward  # noqa: E402

TASK_LATENT_COURT_V2_RES_PPO_CLEAN_READY = "Picklebot-Latent-Court-V2-Res-PPO-Clean-Ready-G1"
READY_WEIGHT = 0.5


def _latent_court_v2_res_clean_ready(play=False):
    cfg = _latent_court_v2_res_clean(play)
    cfg.actions["ball"].ready_track = True
    step_dt = cfg.sim.mujoco.timestep * cfg.decimation
    legal = cfg.rewards.pop("legal_return")
    cfg.rewards["ready"] = RewardTermCfg(func=ready_reward, weight=READY_WEIGHT / step_dt)
    cfg.rewards["legal_return"] = legal
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES_PPO_CLEAN_READY, env_cfg=_latent_court_v2_res_clean_ready(),
                    runner_cls=CriticWarmupHoldLrRunner, play_env_cfg=_latent_court_v2_res_clean_ready(True),
                    rl_cfg=_s5e_rl_cfg())


# Stage 5F run 4 (D-116, review round 7, 4 of 5 reviewers): run 3's task with court-feed rehearsal. 40 % of feeds are
# court-task feeds (court families valid in the zone, 75 % court-anchored with the fixed rally recovery spot, else
# pelvis-anchored with a random court spot; no planner spot), on drill v2 terms (no hint, ball noise, 0.2 s refeed).
TASK_LATENT_COURT_V2_RES_PPO_CLEAN_MIX = "Picklebot-Latent-Court-V2-Res-PPO-Clean-Mix-G1"
COURT_FEED_PROB = 0.4


def _latent_court_v2_res_clean_mix(play=False):
    cfg = _latent_court_v2_res_clean(play)
    cfg.actions["ball"].court_feed_prob = COURT_FEED_PROB
    return cfg


register_mjlab_task(task_id=TASK_LATENT_COURT_V2_RES_PPO_CLEAN_MIX, env_cfg=_latent_court_v2_res_clean_mix(),
                    runner_cls=CriticWarmupHoldLrRunner, play_env_cfg=_latent_court_v2_res_clean_mix(True),
                    rl_cfg=_s5e_rl_cfg())


# Stage 5G E1 (D-118): the timed reach controller. reach-06's task (Picklebot-Latent-Reach-E2-G1: latent-07, lambda
# 1.0, wide root reward, root progress, latent L2) with the timed command (picklebot_mj/tasks/timed_reach.py, goals from
# the Stage 5G goal bank) and the dense paddle reward replaced by the swing guide plus the one-shot contact reward.
from picklebot_mj.tasks.timed_reach import TimedReachCommandCfg, swing_guide, timed_contact  # noqa: E402

TASK_LATENT_TIMED_REACH = "Picklebot-Latent-TimedReach-G1"
GOAL_BANK = str(Path(__file__).resolve().parents[2] / "artifacts" / "goal_bank" / "bank-s5g-01.pt")
CONTACT_WEIGHT = 5.0  # per goal at a perfect contact (one-shot, / step_dt)


def _latent_timed_reach(play=False):
    cfg = _latent_reach_e2(play)
    cfg.commands = {"reach": TimedReachCommandCfg(bank=os.environ.get("PICKLEBOT_GOAL_BANK", GOAL_BANK))}
    step_dt = cfg.sim.mujoco.timestep * cfg.decimation
    cfg.rewards.pop("paddle")
    cfg.rewards["swing_guide"] = RewardTermCfg(func=swing_guide, weight=2.0)
    cfg.rewards["timed_contact"] = RewardTermCfg(func=timed_contact, weight=CONTACT_WEIGHT / step_dt)
    return cfg


register_mjlab_task(task_id=TASK_LATENT_TIMED_REACH, env_cfg=_latent_timed_reach(),
                    play_env_cfg=_latent_timed_reach(True), rl_cfg=_latent_reach_rl_cfg())


# Stage 5G E2 (D-119, panel round 10): E1's task with one paddle-reward redesign: reach-06's paddle_track to p* restored
# while the goal is open, the swing guide removed, and the contact reward's velocity factor linear in |dv| / |v*|.
from picklebot_mj.tasks.timed_reach import paddle_track_open  # noqa: E402

TASK_LATENT_TIMED_REACH_V2 = "Picklebot-Latent-TimedReach-V2-G1"


def _latent_timed_reach_v2(play=False):
    cfg = _latent_timed_reach(play)
    cfg.rewards.pop("swing_guide")
    cfg.rewards["paddle"] = RewardTermCfg(func=paddle_track_open, weight=2.0)
    cfg.rewards["timed_contact"].params = {"speed": "linear"}
    return cfg


register_mjlab_task(task_id=TASK_LATENT_TIMED_REACH_V2, env_cfg=_latent_timed_reach_v2(),
                    play_env_cfg=_latent_timed_reach_v2(True), rl_cfg=_latent_reach_rl_cfg())


# Stage 5G E3 (D-121, panel round 11, 3+ of 5): E2's task with the contact reward's 0.5 speed floor removed
# (speed "linear0"), so a parked paddle earns nothing at contact. Nothing else changes.
TASK_LATENT_TIMED_REACH_V3 = "Picklebot-Latent-TimedReach-V3-G1"


def _latent_timed_reach_v3(play=False):
    cfg = _latent_timed_reach_v2(play)
    cfg.rewards["timed_contact"].params = {"speed": "linear0"}
    return cfg


register_mjlab_task(task_id=TASK_LATENT_TIMED_REACH_V3, env_cfg=_latent_timed_reach_v3(),
                    play_env_cfg=_latent_timed_reach_v3(True), rl_cfg=_latent_reach_rl_cfg())


# Stage 5G zero-shot ball evaluation (D-118): the timed controller in the court ball environment. The court task
# (latent-07 at lambda 1, the ball term, court feeds) with the timed controller's own observations and a command
# built from the live ball by the noisy spin-blind planner (TimedBallCommand). Evaluation task; rewards are the court
# task's (unused by a frozen controller).
from picklebot_mj.tasks.timed_reach import TimedBallCommandCfg  # noqa: E402

TASK_LATENT_TIMED_BALL = "Picklebot-Latent-TimedBall-G1"


def _latent_timed_ball(play=False):
    cfg = _latent_court(play)
    cfg.actions["ball"].planner_mode = "noisy"  # its plan window (delay, noise) times the goal; its spot is unused
    cfg.commands = {**cfg.commands, "reach": TimedBallCommandCfg(bank=GOAL_BANK)}
    ref = _latent_timed_reach_v3(play)
    cfg.observations = ref.observations
    return cfg


register_mjlab_task(task_id=TASK_LATENT_TIMED_BALL, env_cfg=_latent_timed_ball(), play_env_cfg=_latent_timed_ball(True),
                    rl_cfg=_latent_reach_rl_cfg())


# Stage 5G E4 (D-122, panel round 12): D-118's one extension. E3's task with root_progress capped at 1.6 m/s instead
# of 1.0: E3's root misses cluster on goals that need more than 1 m/s (re-evaluation, seed 4216111).
TASK_LATENT_TIMED_REACH_V4 = "Picklebot-Latent-TimedReach-V4-G1"
ROOT_PROGRESS_MAX_SPEED = 1.6


def _latent_timed_reach_v4(play=False):
    cfg = _latent_timed_reach_v3(play)
    cfg.rewards["root_progress"].params = {**(cfg.rewards["root_progress"].params or {}),
                                           "max_speed": ROOT_PROGRESS_MAX_SPEED}
    return cfg


register_mjlab_task(task_id=TASK_LATENT_TIMED_REACH_V4, env_cfg=_latent_timed_reach_v4(),
                    play_env_cfg=_latent_timed_reach_v4(True), rl_cfg=_latent_reach_rl_cfg())


# Stage 5G E5 (D-124, panel round 13): PPO in the ball environment. The timed controller's own task terms (E3's V3 set,
# root_progress capped at 1.0) with goals from the live ball (TimedBallCommand, sync-free), plus a one-shot legal-return
# reward of LEGAL_RETURN_WEIGHT per return (the court task's 250 / step_dt). The court task's pace term and its other
# court terms are not used; no ball-free rehearsal. The critic warms up with the learning rate held (D-114).
from picklebot_mj.tasks.return_stand import legal_return  # noqa: E402

TASK_LATENT_TIMED_BALL_PPO = "Picklebot-Latent-TimedBall-PPO-G1"
LEGAL_RETURN_WEIGHT = 5.0


def _latent_timed_ball_ppo(play=False):
    cfg = _latent_timed_ball(play)
    cfg.rewards = dict(_latent_timed_reach_v3(play).rewards)
    step_dt = cfg.sim.mujoco.timestep * cfg.decimation
    cfg.rewards["legal_return"] = RewardTermCfg(func=legal_return, weight=LEGAL_RETURN_WEIGHT / step_dt)  # reads last
    return cfg


register_mjlab_task(task_id=TASK_LATENT_TIMED_BALL_PPO, env_cfg=_latent_timed_ball_ppo(),
                    play_env_cfg=_latent_timed_ball_ppo(True), runner_cls=CriticWarmupHoldLrRunner,
                    rl_cfg=_latent_reach_rl_cfg())
