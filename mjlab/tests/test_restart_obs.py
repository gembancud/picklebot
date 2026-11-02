"""D-203 (d): the restart-state observation (return_stand.restart_obs) and its trailing actor / critic term."""

import os
import subprocess
import sys
from types import SimpleNamespace

import torch

from picklebot_mj.pairs import PairCourts
from picklebot_mj.tasks.return_stand import restart_obs


def _env(pc, respect=False, move=None):
    t = SimpleNamespace(pairs=pc, cfg=SimpleNamespace(refeed_delay_s=0.1, pair_respect_moves=respect),
                        drill=None if move is None else SimpleNamespace(move_ep=move), shadow=None)
    return SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: t), num_envs=pc.n, device="cpu")


def test_restart_obs_follows_a_real_pair_court():
    F = lambda *i: torch.tensor([k in i for k in range(4)])  # noqa: E731
    Z = F()
    pc = PairCourts(4, "cpu", handoff="contact")  # courts (0, 2) and (1, 3)
    env = _env(pc)
    pc.on_reset(torch.arange(4))
    o = restart_obs(env)
    assert o[:, :3].eq(1).all()  # parked, partner parked, court dead
    assert sorted(o[:, 3].tolist()) == [-1.0, -1.0, 1.0, 1.0] and (o[:, 3][:2] == -o[:, 3][2:]).all()
    seen, fire = [], None
    for _ in range(30):
        pred = restart_obs(env)[:, 3].clone()
        fire, _ = pc.step(Z, Z, Z, Z, 0.01, 0.1, contact=Z)
        if fire.any():
            break
        seen.append(float(restart_obs(env)[0, 4]))
    assert all(a > b for a, b in zip(seen[1:], seen[2:])) and 0.0 < seen[-1] <= 0.15 and max(seen) <= 1.0  # 1 -> 0
    assert ((pred == 1) == fire).all()  # the predicted receiver is the env that gets the feeder ball
    o = restart_obs(env)
    assert o[:, 2:].eq(0).all()  # live courts: no receiver, no countdown
    a = int(fire.nonzero()[0])
    assert o[a, 0] == 0 and o[(a + 2) % 4, 1] == 0  # the receiver is in play, as its partner sees


def test_restart_obs_busy_override_and_no_pairs():
    pc = PairCourts(4, "cpu", handoff="contact")
    pc.on_reset(torch.arange(4))
    for busy_env in range(4):
        move = torch.tensor([k == busy_env for k in range(4)])
        o = restart_obs(_env(pc, respect=True, move=move))
        assert o[busy_env, 3] == -1 and o[(busy_env + 2) % 4, 3] == 1  # never to a busy robot
    t = SimpleNamespace(pairs=None)
    env = SimpleNamespace(action_manager=SimpleNamespace(get_term=lambda name: t), num_envs=3, device="cpu")
    assert restart_obs(env).shape == (3, 5) and not restart_obs(env).any()


def test_restart_obs_is_the_trailing_term_only_when_switched_on():
    code = r"""
import json, sys
import mjlab.tasks  # noqa: F401
import picklebot_mj.tasks.agility, picklebot_mj.tasks.footwork_specialist  # noqa: F401
from mjlab.tasks.registry import load_env_cfg
out = {}
for task in sys.argv[1:]:
    c = load_env_cfg(task)
    out[task] = [list(c.observations[g].terms)[-1] for g in ("actor", "critic")]
print(json.dumps(out))
"""
    tasks = ["Picklebot-Rally22b-FastMove-G1", "Picklebot-Agility-BallIdx-Feeder-ReadCfg-LamR2-G1",
             "Picklebot-Footwork-Measure60-RallyLamR2-G1", "Picklebot-Latent-Court-Res-G1",
             "Picklebot-Latent-Court-V2-Res-G1", "Picklebot-Latent-Drill3-Prior5-Res-G1"]  # stage script + h5f battery
    import json
    res = {}
    for flag in ("0", "1"):
        env = dict(os.environ, PICKLEBOT_RESTART_OBS=flag, CUDA_VISIBLE_DEVICES="", PYTHONWARNINGS="ignore")
        r = subprocess.run([sys.executable, "-c", code, *tasks], env=env, capture_output=True, text=True, timeout=600)
        assert r.returncode == 0, r.stderr[-2000:]
        res[flag] = json.loads(r.stdout.strip().splitlines()[-1])
    for task in tasks:
        assert res["1"][task] == ["restart", "restart"], (task, res["1"][task])
        assert "restart" not in res["0"][task], (task, res["0"][task])


def test_restart_obs_freeze_holds_live_court_values(monkeypatch):
    pc = PairCourts(4, "cpu", handoff="contact")
    pc.on_reset(torch.arange(4))
    assert restart_obs(_env(pc)).any()
    monkeypatch.setenv("PICKLEBOT_RESTART_OBS_FREEZE", "1")
    assert not restart_obs(_env(pc)).any()
