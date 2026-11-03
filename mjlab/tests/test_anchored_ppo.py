"""D-207: AnchoredScheduledPPO (ScheduledPPO plus RegPPO's fixed pull-back to a frozen reference actor)."""

import json

import pytest
import torch
from tensordict import TensorDict

N_ENV, N_STEP, OBS, ACT = 64, 8, 6, 3


def _models(seed=0):
    from rsl_rl.models import MLPModel
    torch.manual_seed(seed)
    obs = TensorDict({"actor": torch.randn(N_ENV, OBS), "critic": torch.randn(N_ENV, OBS)}, batch_size=[N_ENV])
    groups = {"actor": ["actor"], "critic": ["critic"]}
    actor = MLPModel(obs, groups, "actor", ACT, hidden_dims=(16, 16), obs_normalization=True,
                     distribution_cfg={"class_name": "GaussianDistribution", "init_std": 0.5, "std_type": "scalar"})
    critic = MLPModel(obs, groups, "critic", 1, hidden_dims=(16, 16), obs_normalization=True)
    return obs, actor, critic


def _alg(cls, monkeypatch, tmp_path, coef=None, ckpt=None, seed=0):
    from rsl_rl.storage import RolloutStorage
    monkeypatch.setenv("PICKLEBOT_LR_PEAK", "1e-3")
    monkeypatch.setenv("PICKLEBOT_LR_WARMUP", "0")
    monkeypatch.setenv("PICKLEBOT_STD_MIN", "0.1")
    monkeypatch.setenv("PICKLEBOT_SCHED_LOG", str(tmp_path / f"sched-{cls.__name__}-{coef}.jsonl"))
    if coef is not None:
        monkeypatch.setenv("PICKLEBOT_REF_COEF", str(coef))
        monkeypatch.setenv("PICKLEBOT_REF_CKPT", str(ckpt))
    obs, actor, critic = _models(seed)
    storage = RolloutStorage("rl", N_ENV, N_STEP, obs, [ACT], "cpu")
    return obs, cls(actor, critic, storage, device="cpu", num_learning_epochs=2, num_mini_batches=2)


def _rollout(alg, obs, seed=1):
    g = torch.Generator().manual_seed(seed)
    for _ in range(N_STEP):
        alg.act(obs)
        nobs = TensorDict({k: torch.randn(N_ENV, OBS, generator=g) for k in ("actor", "critic")}, batch_size=[N_ENV])
        alg.process_env_step(nobs, torch.randn(N_ENV, generator=g), torch.zeros(N_ENV, dtype=torch.bool), {})
        obs = nobs
    alg.compute_returns(obs)
    return obs


def _ckpt(tmp_path, actor):
    p = tmp_path / "ref.pt"
    torch.save({"actor_state_dict": actor.state_dict()}, p)
    return p


def test_anchor_loss_is_zero_at_the_reference_and_the_gaussian_kl_after_a_perturbation(monkeypatch, tmp_path):
    from picklebot_mj.rl.sched_ppo import AnchoredScheduledPPO
    _, actor0, _ = _models()
    ck = _ckpt(tmp_path, actor0)
    obs, alg = _alg(AnchoredScheduledPPO, monkeypatch, tmp_path, coef=1.0, ckpt=ck)
    batch = type("B", (), {"observations": obs})()
    alg.actor(obs, stochastic_output=True)
    assert float(alg.symmetry.compute_loss(alg.actor, batch, N_ENV)) == pytest.approx(0.0, abs=1e-10)
    with torch.no_grad():
        alg.actor.mlp[-1].bias.add_(0.3)
    alg.actor(obs, stochastic_output=True)
    mu = alg.actor.output_mean
    alg.ref_actor(obs, stochastic_output=True)
    want = (0.5 * ((mu - alg.ref_actor.output_mean) / alg.ref_actor.output_std) ** 2).sum(-1).mean()
    assert float(alg.symmetry.compute_loss(alg.actor, batch, N_ENV)) == pytest.approx(float(want), rel=1e-6)
    assert alg.symmetry.mirror_loss_coeff == 1.0 and alg.symmetry._lr_hold is None


def test_coef_zero_update_equals_scheduled_ppo(monkeypatch, tmp_path):
    from picklebot_mj.rl.sched_ppo import AnchoredScheduledPPO, ScheduledPPO
    _, actor0, _ = _models()
    ck = _ckpt(tmp_path, actor0)
    outs = []
    for cls, coef in ((ScheduledPPO, None), (AnchoredScheduledPPO, 0.0)):
        torch.manual_seed(5)
        obs, alg = _alg(cls, monkeypatch, tmp_path, coef=coef, ckpt=ck)
        torch.manual_seed(7)
        _rollout(alg, obs)
        torch.manual_seed(9)
        alg.update()
        outs.append({k: v.clone() for k, v in alg.actor.state_dict().items()})
    for k in outs[0]:
        assert torch.allclose(outs[0][k], outs[1][k], atol=1e-6), k


def test_anchor_pulls_back_keeps_the_reference_frozen_and_logs(monkeypatch, tmp_path):
    from picklebot_mj.rl.sched_ppo import AnchoredScheduledPPO
    _, actor0, _ = _models()
    ck = _ckpt(tmp_path, actor0)
    obs, alg = _alg(AnchoredScheduledPPO, monkeypatch, tmp_path, coef=1.0, ckpt=ck)
    ref_before = {k: v.clone() for k, v in alg.ref_actor.state_dict().items()}
    with torch.no_grad():
        alg.actor.mlp[-1].bias.add_(0.5)  # move the policy off the reference

    def gap():
        alg.actor(obs, stochastic_output=True)
        alg.ref_actor(obs, stochastic_output=True)
        return float((alg.actor.output_mean - alg.ref_actor.output_mean).abs().mean())

    g0 = gap()
    torch.manual_seed(3)
    _rollout(alg, obs)
    out = alg.update()
    assert gap() < g0  # the pull-back term moved the means back toward the reference
    assert out["pullback"] is not None and out["pullback"] > 0 and out["pullback_coef"] == 1.0
    for k, v in alg.ref_actor.state_dict().items():
        assert torch.equal(v, ref_before[k]), k  # weights and normaliser untouched
    assert set(alg._raw_actor.state_dict()) == set(ref_before)  # saved actor keys unchanged
    row = json.loads(open(tmp_path / "sched-AnchoredScheduledPPO-1.0.jsonl").read().splitlines()[-1])
    assert row["pullback"] > 0 and row["pullback_coef"] == 1.0
    assert float(alg._raw_actor.distribution.std_param.min()) >= 0.1 - 1e-9  # the std floor still applies


def test_reference_load_is_strict(monkeypatch, tmp_path):
    from rsl_rl.models import MLPModel
    from picklebot_mj.rl.sched_ppo import AnchoredScheduledPPO
    obs = TensorDict({"actor": torch.randn(N_ENV, OBS + 1), "critic": torch.randn(N_ENV, OBS)}, batch_size=[N_ENV])
    wrong = MLPModel(obs, {"actor": ["actor"], "critic": ["critic"]}, "actor", ACT, hidden_dims=(16, 16), obs_normalization=True,
                     distribution_cfg={"class_name": "GaussianDistribution", "init_std": 0.5, "std_type": "scalar"})
    ck = _ckpt(tmp_path, wrong)
    with pytest.raises(RuntimeError):
        _alg(AnchoredScheduledPPO, monkeypatch, tmp_path, coef=1.0, ckpt=ck)
