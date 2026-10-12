"""Record a deterministic H4 rollout trace (per-step reward sums, observation checksums, ball-term tallies) so that
throughput refactors can be checked for identical behaviour (D-065).

Usage: python scripts/trace_env.py OUT.pt [--task ...] [--checkpoint ...] [--envs 256] [--steps 300]
       python scripts/trace_env.py --compare A.pt B.pt
"""
import argparse
import copy
from dataclasses import asdict

import torch

ap = argparse.ArgumentParser()
ap.add_argument("out", nargs="?")
ap.add_argument("--compare", nargs=2)
ap.add_argument("--task", default="Picklebot-Latent-Drill3-Footwork-G1")
ap.add_argument("--checkpoint", default="artifacts/train/logs/picklebot_return_stand/2026-10-12_21-41-19_h4-10-footwork/"
                                        "model_13800.pt")
ap.add_argument("--envs", type=int, default=256)
ap.add_argument("--steps", type=int, default=300)
a = ap.parse_args()
if a.compare:
    x, y = (torch.load(p) for p in a.compare)
    for k in x:
        d = (x[k].double() - y[k].double()).abs().max().item()
        print(f"{k:12s} max abs diff {d:.3e}  ({'identical' if d == 0 else 'DIFFERENT'})")
    raise SystemExit
import mjlab.tasks  # noqa: F401,E402
from mjlab.envs import ManagerBasedRlEnv  # noqa: E402
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper  # noqa: E402
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg  # noqa: E402

torch.manual_seed(0)
cfg = load_env_cfg(a.task)
cfg.scene.num_envs, cfg.seed = a.envs, 1
cfg.observations["actor"].enable_corruption = False
env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
venv = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(a.task).clip_actions)
runner = MjlabOnPolicyRunner(venv, copy.deepcopy(asdict(load_rl_cfg(a.task))), device="cuda")
runner.load(a.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
policy = runner.get_inference_policy(device="cuda")
env.reset()
obs = venv.get_observations()
R, O, D = [], [], []
with torch.no_grad():
    for _ in range(a.steps):
        obs, rew, dones, _ = venv.step(policy(obs))
        R.append(rew.clone())
        O.append(obs["actor"].sum(-1).clone())
        D.append(dones.float().clone())
t = env.action_manager.get_term("ball")
out = {"reward": torch.stack(R).cpu(), "obs_sum": torch.stack(O).cpu(), "dones": torch.stack(D).cpu(),
       "tallies": torch.stack([t.ep[k].float() for k in ("episodes", "contact", "legal_return", "fall")]).cpu()}
torch.save(out, a.out)
print("saved", a.out, {k: tuple(v.shape) for k, v in out.items()}, "tallies", out["tallies"].tolist())
