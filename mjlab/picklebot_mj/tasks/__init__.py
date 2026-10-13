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
