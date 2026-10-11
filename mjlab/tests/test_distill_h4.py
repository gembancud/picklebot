"""Stage 5B H4 distillation (scripts/distill_h4.py): the teacher is rebuilt exactly and sees its own observation."""

import copy
import importlib.util
from dataclasses import asdict
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
TEACHER = ROOT / ("artifacts/train/logs/picklebot_return_stand/2026-10-08_22-42-14_student-drill3-style-c/"
                  "model_10400.pt")
LATENT = ROOT / "artifacts" / "train" / "latent" / "latent-07" / "latent_10651.pt"
needs = pytest.mark.skipif(not (torch.cuda.is_available() and TEACHER.exists() and LATENT.exists()),
                           reason="needs CUDA, the S-D3-style-c checkpoint and the H1 latent controller")


def _distill():
    spec = importlib.util.spec_from_file_location("distill_h4", ROOT / "scripts" / "distill_h4.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@needs
def test_teacher_matches_the_runner_policy_and_observation_layouts_agree():
    import mjlab.tasks  # noqa: F401
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
    from mjlab.tasks.registry import load_env_cfg, load_rl_cfg
    from tensordict import TensorDict

    d = _distill()
    flat = "Picklebot-Student-Drill3-Style-NoWrist-G1"
    cfg = load_env_cfg(flat)
    cfg.rewards.pop("style")
    cfg.scene.num_envs = 8
    env = ManagerBasedRlEnv(cfg, device="cuda")
    venv = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(flat).clip_actions)
    rl = asdict(load_rl_cfg(flat))
    runner = MjlabOnPolicyRunner(venv, copy.deepcopy(rl), device="cuda")
    runner.load(str(TEACHER), load_cfg={"actor": True}, strict=True, map_location="cuda")
    policy = runner.get_inference_policy(device="cuda")
    env.reset()
    obs = venv.get_observations()
    for _ in range(5):
        obs, *_ = venv.step(policy(obs))
    teacher = d.build_teacher(str(TEACHER), obs["actor"].shape[1], 29, rl["actor"], "cuda")
    with torch.no_grad():
        mine = teacher(TensorDict({"actor": obs["actor"]}, batch_size=[8]))
        assert torch.allclose(mine, policy(obs), atol=1e-5)
    flat_terms = list(zip(env.observation_manager.active_terms["actor"],
                          env.observation_manager.group_obs_term_dim["actor"]))
    env.close()

    hcfg = load_env_cfg("Picklebot-Latent-Drill3-G1")
    hcfg.scene.num_envs = 8
    henv = ManagerBasedRlEnv(hcfg, device="cuda")
    h_terms = list(zip(henv.observation_manager.active_terms["actor"],
                       henv.observation_manager.group_obs_term_dim["actor"]))
    assert [n for n, _ in h_terms] == [n for n, _ in flat_terms]
    for (n, dh), (_, df) in zip(h_terms, flat_terms):
        assert tuple(dh) == ((35,) if n == "actions" else tuple(df))
    sl = d.actions_slice(henv)
    assert sl.stop - sl.start == 35
    # The differentiable mapping reproduces the action term's joint targets.
    henv.reset()
    term = henv.action_manager.get_term("latent")
    a = torch.randn(8, 35, device="cuda")
    ctrl = term.controller_obs()
    q = d.predict_joint_action(term, a, ctrl)
    henv.step(a)
    assert torch.allclose(q, d.executed_joint_action(term), atol=1e-4)
    henv.close()
