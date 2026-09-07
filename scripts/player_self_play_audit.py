"""Audit a bounded full-game self-play loop, including the carried critic signal."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import torch
from player_actor import Actor, ROOT, file_hash, source_hash
from player_game_win_audit import game_outcomes
from player_ppo import Critic, clipped_loss, log_probability, prepare_advantages, validate_episodes, validate_motor_metrics


def complete_game_signal(records, games, critic):
    """With gamma=lambda=1, advantage is the final team reward minus old value."""
    outcomes = {g["seed"]: 1. if g["won"] else -1. for g in games}
    joint = torch.tensor([r["criticObservation"] for r in records], dtype=torch.float32)
    with torch.no_grad(): values = critic(joint)
    returns = torch.tensor([outcomes[r["gameSeed"]] for r in records])
    return prepare_advantages(returns-values, "none")


def audit(folder, plan_path):
    torch.set_num_threads(2)
    plan = json.loads(plan_path.read_text())
    progress = json.loads((folder/"progress.json").read_text())
    source = source_hash(); config = progress["configuration"]
    if (progress["status"] != "complete" or progress["sourceHash"] != source
            or plan["sourceHash"] != source or len(progress["iterations"]) != plan["iterations"]
            or config["iterations"] != plan["iterations"] or config["rallies"] != plan["ralliesPerCollection"]
            or config["entropy"] != 0 or config["advantage_normalization"] != "none"
            or config["reward_mode"] != "game_win" or config["heads"] != "all"
            or config["credit_assignment"] != "full_episode"):
        raise ValueError("Incomplete or different self-play plan")
    parent = ROOT/plan["initialActor"]; critic_path = ROOT/plan["initialCritic"]
    if (file_hash(parent) != plan["initialActorHash"] or file_hash(critic_path) != plan["initialCriticHash"]
            or progress["initialActorHash"] != file_hash(parent)
            or progress["initialCriticHash"] != file_hash(critic_path)):
        raise ValueError("Initial model changed")
    if progress["driverHash"] != file_hash(folder/"trainer-source/player-agents-train-loop.py"):
        raise ValueError("Driver snapshot changed")
    if progress["opponentPoolHash"] != file_hash(folder/"opponents/manifest.json"):
        raise ValueError("Opponent manifest changed")
    results = []
    for i, run in enumerate(progress["iterations"]):
        opponent = plan["opponents"][i]
        if (run["status"] != "complete" or run["parentActorHash"] != file_hash(parent)
                or run["opponentPoolIndex"] != i or run["opponentHash"] != opponent["sha256"]
                or file_hash(ROOT/opponent["path"]) != opponent["sha256"]
                or file_hash(folder/f"opponents/{i}.json") != opponent["sha256"]):
            raise ValueError("Iteration model ownership differs")
        actor_path = Path(run["actor"]); actor, metadata = Actor.load_export(actor_path)
        old_actor, parent_meta = Actor.load_export(parent)
        training = json.loads((actor_path.parent/"training.json").read_text())
        report_path, dev_path = Path(run["rollout"]), Path(run["development"])
        report, dev = json.loads(report_path.read_text()), json.loads(dev_path.read_text())
        for path, digest in ((actor_path, run["actorHash"]), (report_path, run["rolloutHash"]),
                             (dev_path, run["developmentHash"]), (actor_path, training["actorHash"]),
                             (actor_path.parent/"critic.pt", training["criticHash"])):
            if file_hash(path) != digest: raise ValueError("Loop artifact changed")
        for record in (report, dev, training, metadata):
            if record["sourceHash"] != source: raise ValueError("Source changed")
            for key, path in (("contactModelHash", "Assets/Picklebot/Doubles/Models/contact.json"),
                              ("protocolHash", "config/player-agents/evaluation-v1.json"),
                              ("baselineManifestHash", "artifacts/player-agents/baseline-manifest.json")):
                if record[key] != file_hash(ROOT/path): raise ValueError("Frozen input changed")
        if (report["seed"] != plan["trainingSeedBases"][i] or report["split"] != "training"
                or not report["sampledActor"] or report["actorHash"] != file_hash(parent)
                or report["opponentHash"] != opponent["sha256"]
                or report["opponentMode"] != "older actor / sampled"
                or dev["seed"] != plan["developmentSeedBases"][i] or dev["split"] != "development"
                or dev["sampledActor"] or dev["actorHash"] != file_hash(actor_path)
                or dev["opponentHash"] != file_hash(ROOT/"Assets/Picklebot/Doubles/Models/teams.json")):
            raise ValueError("Wrong policy, split, or opponent")
        games, dev_games = game_outcomes(report), game_outcomes(dev)
        if (any(not 1000000 <= g["seed"] < 1100000 for g in games)
                or any(not 1100000 <= g["seed"] < 1200000 for g in dev_games)):
            raise ValueError("Seed partition differs")
        validate_motor_metrics(report); validate_motor_metrics(dev)
        for key, expected in (("rewardMode", "game_win"), ("trainHeads", "all"), ("gamma", 1),
                              ("gaeLambda", 1), ("entropyCoefficient", 0), ("advantageNormalization", "none"),
                              ("postUpdateKLRollback", True), ("batch", plan["batch"]),
                              ("learningRate", plan["learningRate"]), ("targetKL", plan["targetKL"]),
                              ("epochs", plan["epochsPerUpdate"]), ("initialCriticHash", file_hash(critic_path))):
            if training[key] != expected: raise ValueError("Optimizer contract differs: " + key)
        if (metadata["parentActorHash"] != file_hash(parent) or training["updates"] <= 0
                or metadata["trainingSteps"] != parent_meta["trainingSteps"]+training["updates"]):
            raise ValueError("Update lineage differs")
        names = ("player-agents-ppo.py", "player_ppo.py", "player_actor.py")
        for name in names:
            if (file_hash(actor_path.parent/"trainer-source"/name) != training["trainerSources"][name]
                    or file_hash(folder/"trainer-source"/name) != training["trainerSources"][name]):
                raise ValueError("Trainer snapshot differs")
        digest = hashlib.sha256(b"".join((folder/"trainer-source"/n).read_bytes() for n in names)).hexdigest()
        if training["trainerHash"] != digest: raise ValueError("Trainer digest differs")
        data = ROOT/report["dataPath"]
        if file_hash(data) != training["dataHash"] or training["rolloutReportHash"] != file_hash(report_path):
            raise ValueError("Training data changed")
        records = [json.loads(line) for line in data.read_text().splitlines()]
        if len(records) != training["rows"] or len(records) != report["rows"]:
            raise ValueError("Training rows differ")
        groups = validate_episodes(records, report)
        critic = Critic(); critic.load_state_dict(torch.load(critic_path, map_location="cpu", weights_only=True))
        advantage = complete_game_signal(records, games, critic)
        for key, measured in (("advantageMinimum", float(advantage.min())), ("advantageMaximum", float(advantage.max())),
                              ("negativeAdvantageRows", int((advantage < 0).sum())),
                              ("positiveAdvantageRows", int((advantage > 0).sum()))):
            if abs(training[key]-measured) > 1e-5: raise ValueError("Critic-derived signal differs")
        obs = torch.tensor([r["observation"] for r in records])
        raw = torch.tensor([[r["sample"]["rawX"], r["sample"]["rawZ"]] for r in records])
        hit = torch.tensor([float(r["sample"]["action"]["attempt"]) for r in records])
        shot = torch.tensor([r["sample"]["action"]["shot"] for r in records])
        old_logp = torch.tensor([r["sample"]["logProbability"] for r in records])
        with torch.no_grad():
            replay, _ = log_probability(old_actor, obs, raw, hit, shot)
            current, _ = log_probability(actor, obs, raw, hit, shot)
            _, kl = clipped_loss(current, old_logp, advantage, training["clip"])
        error = float((replay-old_logp).abs().max())
        if not math.isfinite(error) or error > .001 or not 0 <= float(kl) <= plan["targetKL"]:
            raise ValueError("Policy likelihood or final KL check failed")
        parity = json.loads((actor_path.parent/"unity-parity.json").read_text())
        if (not parity["passed"] or parity["actorHash"] != file_hash(actor_path)
                or parity["sourceHash"] != source or parity["cases"] < 1
                or not 0 <= parity["maximumError"] < .0001
                or parity["inputHash"] != file_hash(actor_path.parent/"parity-input.json")):
            raise ValueError("Unity parity failed")
        results.append(dict(iteration=i+1, actor=str(actor_path), actorHash=file_hash(actor_path),
            parentActorHash=file_hash(parent), criticHash=file_hash(critic_path), games=games, developmentGames=dev_games,
            rows=len(records), playerTrajectories=len(groups), updates=training["updates"],
            positiveAdvantageRows=training["positiveAdvantageRows"], negativeAdvantageRows=training["negativeAdvantageRows"],
            finalKL=float(kl), likelihoodReplayError=error, parity=parity,
            trainingSeconds=report["wallSeconds"], optimizerSeconds=training["elapsedSeconds"],
            developmentSeconds=dev["wallSeconds"]))
        parent, critic_path = actor_path, actor_path.parent/"critic.pt"
    return dict(folder=str(folder), planHash=file_hash(plan_path), sourceHash=source, iterations=results,
                limitation="Verified reward-derived independent-player updates and small development checks. Self-play training outcomes precede each update. Not final acceptance or proof of baseline wins.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path); parser.add_argument("plan", type=Path)
    args = parser.parse_args(); print(json.dumps(audit(args.folder, args.plan), indent=2))
