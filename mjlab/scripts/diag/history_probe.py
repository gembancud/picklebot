"""Stage 5F step 0 (D-109 item 2): 4 vs 8 executor history steps, without training.

Rolls out Stage 5D run 1 on the training-latency task (half the episodes with ball lag 1-2 control steps and command
lag 0-4 physics steps, held for the whole episode here), records what the actor would see in a K-step history (its
issued actions, joint positions and velocities, its ball estimate) and fits a ridge probe from the K-step window to
the episode's command lag and ball lag (one-hot, least squares), on train envs, scored on held-out envs.
Rule, written before the run (stage5f.md): choose the smallest K in {1, 2, 4, 8} whose held-out accuracy is within
1 point of K = 8 for both lags; 4 is the D-108 default, so 8 is adopted only if 4 misses that bar.
Usage: python scripts/diag/history_probe.py --checkpoint CK [--envs 1024] [--steps 400] [--seed 4210012] [--json OUT]
"""
import argparse
import json
from dataclasses import asdict

import torch

import mjlab.tasks  # noqa: F401
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg

import picklebot_mj.tasks  # noqa: F401
from picklebot_mj import seeds

ap = argparse.ArgumentParser()
ap.add_argument("--checkpoint", required=True)
ap.add_argument("--task", default="Picklebot-Latent-Court-V2-Res-PPO-Comp-G1")
ap.add_argument("--envs", type=int, default=1024)
ap.add_argument("--steps", type=int, default=400)
ap.add_argument("--seed", type=int, default=4210012)
ap.add_argument("--json", default=None)
a = ap.parse_args()
assert a.seed in seeds.DEV_EVAL_SEEDS
cfg = load_env_cfg(a.task)
cfg.scene.num_envs, cfg.seed = a.envs, a.seed
b = cfg.actions["ball"]
b.seed, b.obs_lag_period = a.seed, 0  # one lag pair per episode: clean labels
cfg.observations["actor"].enable_corruption = False
env = ManagerBasedRlEnv(cfg=cfg, device="cuda")
agent = load_rl_cfg(a.task)
venv = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
rl = asdict(agent)
sd = torch.load(a.checkpoint, map_location="cpu", weights_only=False)
for part in ("actor", "critic"):
    ws = sorted((int(k.split(".")[1]), v.shape[0]) for k, v in sd[f"{part}_state_dict"].items()
                if k.startswith("mlp.") and k.endswith(".weight"))
    rl[part]["hidden_dims"] = tuple(n for _, n in ws[:-1])
runner = MjlabOnPolicyRunner(venv, rl, device="cuda")
runner.load(a.checkpoint, load_cfg={"actor": True}, strict=True, map_location="cuda")
policy = runner.get_inference_policy(device="cuda")
env.reset()
om = env.observation_manager
names = om.active_terms["actor"]
dims = om.group_obs_term_dim["actor"]
sl, i = {}, 0
for n, d in zip(names, dims):
    k = int(torch.tensor(d).prod())
    sl[n] = slice(i, i + k)
    i += k
keep = ("actions", "joint_pos", "joint_vel", "ball_pos", "ball_vel")
term = env.action_manager.get_term("ball")
obs = venv.get_observations()
F, LC, LO, DN = [], [], [], []
with torch.no_grad():
    for _ in range(a.steps):
        x = obs["actor"]
        F.append(torch.cat([x[:, sl[n]] for n in keep], -1).clone())
        LC.append(term.cmd_lag.clone())
        LO.append(term.obs_lag.clone())
        obs, _, dones, _ = venv.step(policy(obs))
        DN.append(dones.bool().clone())
F, LC, LO, DN = torch.stack(F), torch.stack(LC), torch.stack(LO), torch.stack(DN)  # [T, N, ...]
T, N, D = F.shape
mu, sdv = F.reshape(-1, D).mean(0), F.reshape(-1, D).std(0).clamp(min=1e-3)
F = (F - mu) / sdv
train_env = torch.arange(N, device="cuda") < int(0.7 * N)
out = {"checkpoint": a.checkpoint, "task": a.task, "envs": N, "steps": T, "seed": a.seed, "features": list(keep),
       "accuracy": {}}
for K in (1, 2, 4, 8):
    X, Yc, Yo, E = [], [], [], []
    for t in range(K - 1 + 8, T):  # skip each episode's first steps (no full window yet) via the done mask below
        ok = ~DN[t - K:t].any(0)  # the window holds no reset
        X.append(F[t - K + 1:t + 1].permute(1, 0, 2).reshape(N, -1)[ok])
        Yc.append(LC[t][ok]); Yo.append(LO[t][ok]); E.append(train_env[ok])
    X, Yc, Yo, E = torch.cat(X), torch.cat(Yc), torch.cat(Yo), torch.cat(E)
    X = torch.cat([X, torch.ones(len(X), 1, device="cuda")], -1)
    res = {}
    for lab, Y, ncls in (("cmd_lag", Yc, 5), ("obs_lag", Yo, 3)):
        oh = torch.nn.functional.one_hot(Y, ncls).float()
        Xt, Yt = X[E], oh[E]
        W = torch.linalg.solve(Xt.T @ Xt + 1.0 * torch.eye(X.shape[1], device="cuda"), Xt.T @ Yt)
        pred = (X[~E] @ W).argmax(-1)
        res[lab] = round(float((pred == Y[~E]).float().mean()), 4)
        res[f"{lab}_majority"] = round(float(torch.bincount(Y[~E], minlength=ncls).max() / (~E).sum()), 4)
    res["samples_test"] = int((~E).sum())
    out["accuracy"][K] = res
    print(K, res, flush=True)
acc = out["accuracy"]
pick = next(K for K in (1, 2, 4, 8) if all(acc[K][l] >= acc[8][l] - 0.01 for l in ("cmd_lag", "obs_lag")))
out["rule_pick"] = pick
out["adopted"] = 4 if pick <= 4 else 8
print(json.dumps({"rule_pick": pick, "adopted": out["adopted"]}))
if a.json:
    json.dump(out, open(a.json, "w"), indent=1)
