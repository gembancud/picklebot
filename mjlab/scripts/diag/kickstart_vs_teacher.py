"""Does the kickstarted executor reproduce its starting executor on ball episodes at evaluation? (Stage 5C diagnostic)

Plays the lambda-3 court task with the kickstarted student (deterministic), real balls only, no hint, like the court
evaluation. At every step the starting executor (lambda 1) is queried on the same observation. Reports the joint-target
MSE between the two (teacher units) overall and per joint group, the latent distance |z_s - z_t| / sigma_p, and the
paddle-target difference proxy (right arm + wrist MSE), plus whether actor(obs) is deterministic in train/eval mode.
"""
import copy
import re
import sys
from dataclasses import asdict
from pathlib import Path

import mjlab.tasks  # noqa: F401
import torch
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

sys.path.insert(0, "scripts")
from kickstart_h4 import joint_target  # noqa: E402

STU = "artifacts/train/logs/picklebot_return_stand/2026-10-15_18-22-56_s5c-12-kickstart/model_29585.pt"
SELF = "artifacts/train/logs/picklebot_return_stand/2026-10-14_16-47-02_s5c-02-court/model_28400.pt"
TASK = "Picklebot-Latent-Court-L3-G1"
GROUPS = {"legs": r"(hip|knee|ankle)", "waist": r"waist", "left_arm": r"left_(shoulder|elbow|wrist)",
          "right_arm": r"right_(shoulder|elbow)", "right_wrist": r"right_wrist"}

cfg = load_env_cfg(TASK)
cfg.scene.num_envs, cfg.seed = 512, 4200740
b = cfg.actions["ball"]
b.seed, b.move_prob, b.swing_prob, b.hit_hint, b.lp_curriculum = 4200740, 0.0, 0.0, False, False
b.recovery_mode = "random"
cfg.observations["actor"].enable_corruption = False
env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
venv = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(TASK).clip_actions)
rl = asdict(load_rl_cfg(TASK))
r1 = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
r1.load(STU, load_cfg={"actor": True}, strict=True, map_location="cuda")
r2 = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
r2.load(SELF, load_cfg={"actor": True}, strict=True, map_location="cuda")
stu, teach = r1.get_inference_policy(device="cuda"), r2.get_inference_policy(device="cuda")
term = env.action_manager.get_term("latent")
names = list(term._target_names)
env.reset()
obs = venv.get_observations()
# determinism check on the raw actor
act = r1.alg.actor
act.train()
with torch.no_grad():
    d_train = float((act(obs) - act(obs)).abs().max())
act.eval()
with torch.no_grad():
    d_eval = float((act(obs) - act(obs)).abs().max())
print(f"actor(obs) repeat difference: train mode {d_train:.4f}, eval mode {d_eval:.4f}")
se, zd, n = torch.zeros(len(names), device="cuda"), [], 0
with torch.no_grad():
    for t in range(600):
        ctrl = term.controller_obs()
        a_s, a_t = stu(obs), teach(obs)
        q_s = joint_target(term, a_s, ctrl, 3.0)
        q_t = joint_target(term, a_t, ctrl, 1.0)
        se += ((q_s - q_t) ** 2).sum(0)
        n += len(q_s)
        mu, ls = term.model.prior_dist(ctrl)
        z_s = 3.0 * torch.tanh(a_s[:, :32])
        z_t = 1.0 * torch.tanh(a_t[:, :32])
        zd.append((z_s - z_t).abs().mean(-1))
        obs, *_ = venv.step(a_s)
mse = se / n
print("joint-target MSE student vs starting executor (eval states, ball episodes):", round(float(mse.mean()), 4))
for g, rx in GROUPS.items():
    idx = [i for i, nm in enumerate(names) if re.search(rx, nm)]
    print(f"  {g:12s} {float(mse[idx].mean()):.4f}")
zd = torch.cat(zd)
print(f"mean |z_s - z_t| per dim (prior sigmas): median {float(zd.median()):.3f}, p90 {float(zd.quantile(0.9)):.3f}")
