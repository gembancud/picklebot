#!/usr/bin/env python3
"""One source-tracked local PPO update from complete Unity player episodes."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time

import torch
from player_actor import Actor, ROOT, file_hash, source_hash
from player_ppo import Critic, advantages, clipped_loss, log_probability, validate_episodes, validate_motor_metrics, freeze_nonshot_heads, nonshot_parameters, return_parameters, prepare_advantages, bounded_optimizer_step


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rollout_report", type=Path)
    parser.add_argument("actor", type=Path)
    parser.add_argument("--critic", type=Path)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=.0001)
    parser.add_argument("--entropy", type=float, default=.001)
    parser.add_argument("--clip", type=float, default=.1)
    parser.add_argument("--target-kl", type=float, default=.01)
    parser.add_argument("--heads", choices=("all", "shots"), default="all")
    parser.add_argument("--credit-assignment", choices=("default", "full_episode"), default="default")
    parser.add_argument("--advantage-normalization", choices=("standard", "none"), default="standard",
                        help="Explicit advantage baseline choice; zero policy-gradient signal always rejects the update")
    args = parser.parse_args()
    if args.epochs < 1 or args.batch < 1 or args.learning_rate <= 0 or not 0 < args.clip < 1 or args.entropy < 0 or args.target_kl <= 0:
        parser.error("Invalid PPO parameters")
    trainer_names = ("player-agents-ppo.py", "player_ppo.py", "player_actor.py")
    trainer_bytes = {name: (ROOT / "scripts" / name).read_bytes() for name in trainer_names}
    torch.set_num_threads(2); torch.manual_seed(1000000)
    report = json.loads(args.rollout_report.read_text())
    if report["status"] != "complete" or report["split"] != "training" or report["sourceHash"] != source_hash() or not report["sampledActor"]:
        raise ValueError("PPO requires current-source training rollouts")
    if not report["games"] or any(not game["complete"] for game in report["games"]):
        raise ValueError("Fix incomplete games before a PPO update")
    validate_motor_metrics(report)
    checks = {"actorHash": args.actor, "protocolHash": ROOT / "config/player-agents/evaluation-v1.json",
              "contactModelHash": ROOT / "Assets/Picklebot/Doubles/Models/contact.json",
              "baselineManifestHash": ROOT / "artifacts/player-agents/baseline-manifest.json"}
    for field, path in checks.items():
        if report[field] != file_hash(path): raise ValueError(f"Rollout {field} mismatch")
    if report["rewardMode"] not in ("rally_win", "game_win"):
        raise ValueError("Unknown reward objective")
    actor, parent = Actor.load_export(args.actor)
    protected = nonshot_parameters(actor)
    if args.heads == "shots": freeze_nonshot_heads(actor)
    critic = Critic()
    initial_critic_hash = file_hash(args.critic) if args.critic else None
    if args.critic:
        # This is a local checkpoint produced by this trainer, not a downloaded file.
        critic.load_state_dict(torch.load(args.critic, map_location="cpu", weights_only=True))
    else:
        with torch.no_grad(): critic.layers[-1].weight.zero_(); critic.layers[-1].bias.zero_()
    data_path = ROOT / report["dataPath"]
    frozen_inputs = {str(path): file_hash(path) for path in [*checks.values(), args.rollout_report, data_path]}
    if args.critic: frozen_inputs[str(args.critic)] = initial_critic_hash
    records = [json.loads(line) for line in data_path.read_text().splitlines()]
    if not records or len(records) != report["rows"]: raise ValueError("Incomplete rollout records")
    groups = validate_episodes(records, report)
    for i, row in enumerate(records):
        if not 1000000 <= row["gameSeed"] < 1100000 or row["player"] not in range(4):
            raise ValueError("Invalid training seed or player")
        if row["player"] // 2 != row["candidateTeam"]:
            raise ValueError("Opponent action included in candidate training")
        if row["reward"] not in (-1, 0, 1): raise ValueError("Unexpected reward shaping")
    obs = torch.tensor([r["observation"] for r in records])
    joint = torch.tensor([r["criticObservation"] for r in records])
    raw = torch.tensor([[r["sample"]["rawX"], r["sample"]["rawZ"]] for r in records])
    hit = torch.tensor([float(r["sample"]["action"]["attempt"]) for r in records])
    shot = torch.tensor([r["sample"]["action"]["shot"] for r in records], dtype=torch.long)
    old_logp = torch.tensor([r["sample"]["logProbability"] for r in records])
    reward = torch.tensor([r["reward"] for r in records], dtype=torch.float32)
    terminal = torch.tensor([r["terminal"] for r in records], dtype=torch.bool)
    if obs.shape != (len(records), 54) or joint.shape != (len(records), 108) or not all(torch.isfinite(x).all() for x in (obs, joint, raw, old_logp)):
        raise ValueError("Invalid rollout tensors")
    with torch.no_grad():
        recomputed, _ = log_probability(actor, obs, raw, hit, shot)
        logp_error = (recomputed - old_logp).abs().max().item()
        if logp_error > .001: raise ValueError(f"Unity/Python sampled log probabilities differ: {logp_error}")
        old_value = critic(joint)
    # The game objective values a win equally regardless of game duration.
    # Complete-game Monte Carlo advantages also reach early rally decisions.
    gamma, gae_lambda = return_parameters(report["rewardMode"], args.credit_assignment)
    advantage = torch.zeros(len(records)); target = torch.zeros(len(records))
    for indices in groups.values():
        index = torch.tensor(indices)
        gae, returns = advantages(reward[index], old_value[index], terminal[index], gamma=gamma, gae_lambda=gae_lambda)
        advantage[index] = gae; target[index] = returns
    advantage = prepare_advantages(advantage, args.advantage_normalization)
    actor_optimizer = torch.optim.Adam((p for p in actor.parameters() if p.requires_grad), lr=args.learning_rate, weight_decay=0)
    critic_optimizer = torch.optim.Adam(critic.parameters(), lr=.0003)
    started = time.perf_counter(); updates = 0; stopped = False; history = []; rejected_updates = []
    for epoch in range(args.epochs):
        for index in torch.randperm(len(records)).split(args.batch):
            logp, entropy = log_probability(actor, obs[index], raw[index], hit[index], shot[index])
            policy_loss, kl = clipped_loss(logp, old_logp[index], advantage[index], args.clip)
            if kl.item() > args.target_kl: stopped = True; break
            value = critic(joint[index]); clipped_value = old_value[index] + (value - old_value[index]).clamp(-.2, .2)
            value_loss = .5 * torch.maximum((value - target[index]).square(), (clipped_value - target[index]).square()).mean()
            loss = policy_loss - args.entropy * entropy.mean() + value_loss
            def measure_kl():
                candidate_logp, _ = log_probability(actor, obs, raw, hit, shot)
                _, candidate_kl = clipped_loss(candidate_logp, old_logp, advantage, args.clip)
                return candidate_kl
            accepted, candidate_kl = bounded_optimizer_step(actor, critic, actor_optimizer,
                critic_optimizer, loss, measure_kl, args.target_kl)
            if not accepted:
                rejected_updates.append(dict(epoch=epoch+1, afterAcceptedUpdates=updates, kl=candidate_kl))
                stopped = True; break
            updates += 1
        with torch.no_grad():
            new_logp, entropy = log_probability(actor, obs, raw, hit, shot)
            _, measured_kl = clipped_loss(new_logp, old_logp, advantage, args.clip)
            history.append(dict(epoch=epoch + 1, kl=measured_kl.item(), entropy=entropy.mean().item(),
                                valueMSE=(critic(joint) - target).square().mean().item(), updates=updates))
        if stopped: break
    if source_hash() != report["sourceHash"]: raise RuntimeError("Source changed during PPO update")
    if any(file_hash(path) != digest for path, digest in frozen_inputs.items()):
        raise RuntimeError("An input artifact changed during PPO update")
    if any((ROOT / "scripts" / name).read_bytes() != content for name, content in trainer_bytes.items()):
        raise RuntimeError("Trainer source changed during PPO update")
    if not updates: raise RuntimeError("No PPO update was applied")
    protected_change = max((after - before).abs().max().item() for before, after in zip(protected, nonshot_parameters(actor)))
    if args.heads == "shots" and protected_change != 0:
        raise RuntimeError("Shot-only training changed movement or hit parameters")
    folder = ROOT / "artifacts/player-agents" / ("ppo-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False)
    snapshot = folder / "trainer-source"; snapshot.mkdir()
    for name in trainer_names: shutil.copy2(ROOT / "scripts" / name, snapshot / name)
    trainer_hash = hashlib.sha256(b"".join(trainer_bytes.values())).hexdigest()
    metadata = dict(sourceHash=report["sourceHash"], configurationHash=report["configurationHash"], protocolHash=report["protocolHash"],
                    contactModelHash=report["contactModelHash"], baselineManifestHash=report["baselineManifestHash"],
                    trainerHash=trainer_hash, dataHash=file_hash(data_path), createdUtc=datetime.now(timezone.utc).isoformat(),
                    parentActorHash=report["actorHash"], parentTrainingSourceHash=parent.get("sourceHash"),
                    method="shared independent actor PPO / centralized training-only critic / " + report["rewardMode"] + " / " + args.heads + " heads / " + args.credit_assignment + " credit",
                    trainingSteps=parent.get("trainingSteps", 0) + updates,
                    advantageNormalization=args.advantage_normalization, postUpdateKLRollback=True,
                    initialCriticPath=str(args.critic) if args.critic else None, initialCriticHash=initial_critic_hash,
                    trainerSources={name: hashlib.sha256(content).hexdigest() for name, content in trainer_bytes.items()})
    (folder / "actor.json").write_text(json.dumps(actor.export(metadata)))
    torch.save(critic.state_dict(), folder / "critic.pt")
    with torch.no_grad(): outputs = actor(obs[:32]).tolist()
    (folder / "parity-input.json").write_text(json.dumps({"observations": [{"values": row.tolist()} for row in obs[:32]], "expected": [{"values": row} for row in outputs]}))
    training = dict(metadata, actorHash=file_hash(folder / "actor.json"), criticHash=file_hash(folder / "critic.pt"),
                    rolloutReport=str(args.rollout_report), rolloutReportHash=file_hash(args.rollout_report), rows=len(records),
                    rewardMode=report["rewardMode"], creditAssignment=args.credit_assignment,
                    gamma=gamma, gaeLambda=gae_lambda, epochs=args.epochs, updates=updates,
                    batch=args.batch, optimizerSeed=1000000,
                    trainHeads=args.heads, protectedParameterMaximumChange=protected_change,
                    learningRate=args.learning_rate, entropyCoefficient=args.entropy, clip=args.clip, targetKL=args.target_kl,
                    stoppedForKL=stopped, sampledLogProbabilityMaximumError=logp_error, history=history,
                    rejectedUpdates=rejected_updates, advantageNormalization=args.advantage_normalization,
                    advantageMinimum=advantage.min().item(), advantageMaximum=advantage.max().item(),
                    positiveAdvantageRows=int((advantage > 0).sum()), negativeAdvantageRows=int((advantage < 0).sum()),
                    postUpdateKLRollback=True, entropyOnlyUpdate=False,
                    elapsedSeconds=time.perf_counter() - started, limit="Optimizer update evidence only; evaluate playing strength separately.")
    (folder / "training.json").write_text(json.dumps(training, indent=2))
    print(json.dumps({"folder": str(folder), "updates": updates, "logProbabilityError": logp_error, "history": history}), flush=True)


if __name__ == "__main__": main()
