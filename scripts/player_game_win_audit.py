"""Audit one complete-game single-actor PPO cycle without running Unity or training."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import torch

from player_actor import Actor, ROOT, file_hash, source_hash
from player_ppo import log_probability, validate_episodes, validate_motor_metrics, clipped_loss, prepare_advantages
from player_skill_retention import validate_replayed_action


def game_outcomes(report):
    if report.get("status") != "complete" or report.get("rewardMode") != "game_win":
        raise ValueError("Complete game-win collection required")
    if not report.get("games"):
        raise ValueError("No completed games")
    seen = set(); result = []; rally_count = 0
    for game in report["games"]:
        seed, team, winner = game["gameSeed"], game["candidateTeam"], game["winner"]
        score = game["score"]
        if (seed in seen or not game["complete"] or winner not in (0, 1) or team not in (0, 1)
                or len(score) != 2 or any(type(s) is not int or s < 0 for s in score)
                or score[winner] < 11 or score[winner]-score[1-winner] < 2):
            raise ValueError("Invalid complete game")
        seen.add(seed)
        rallies = [r for r in report["rallies"] if r["gameSeed"] == seed]
        if len(rallies) != game["rallies"] or not rallies or rallies[-1]["score"] != score:
            raise ValueError("Rally ledger differs from game")
        previous = [0, 0]; truncations = 0; hits = [0]*4
        for rally in rallies:
            if rally["candidateTeam"] != team or rally["winner"] not in (-1, 0, 1):
                raise ValueError("Rally reward ownership mismatch")
            if rally["winner"] == -1:
                if rally["fault"] != "None" or not 30 <= rally["seconds"] <= 35 or rally["score"] != previous:
                    raise ValueError("Invalid no-point truncation")
                truncations += 1
            previous = rally["score"]
            for i, n in enumerate(rally["legalHits"]):
                if type(n) is not int or n < 0:
                    raise ValueError("Invalid hit count")
                hits[i] += n
        if hits != game["metrics"]["legalHits"]:
            raise ValueError("Rally hit ledger mismatch")
        rally_count += len(rallies)
        result.append(dict(seed=seed, candidateTeam=team, score=score, won=winner == team,
                           rallies=len(rallies), truncatedRallies=truncations,
                           legalReturns=sum(hits[team*2:team*2+2])))
    if rally_count != len(report["rallies"]):
        raise ValueError("Unowned rally records")
    return result


def audit(folder):
    torch.set_num_threads(2)
    progress = json.loads((folder/"progress.json").read_text())
    config = progress["configuration"]
    if (progress["status"] != "complete" or len(progress["iterations"]) != 1
            or config["iterations"] != 1 or config["reward_mode"] != "game_win"
            or config["credit_assignment"] != "full_episode" or config["heads"] != "all"
            or progress["sourceHash"] != source_hash() or progress["initialCriticHash"] is not None):
        raise ValueError("Expected one current-source game-win cycle with a new critic")
    run = progress["iterations"][0]
    if run["status"] != "complete":
        raise ValueError("Training iteration is not complete")
    parent_path, actor_path = Path(run["parentActor"]), Path(run["actor"])
    report_path, dev_path = Path(run["rollout"]), Path(run["development"])
    for path, digest in ((parent_path, run["parentActorHash"]), (actor_path, run["actorHash"]),
                         (report_path, run["rolloutHash"]), (dev_path, run["developmentHash"])):
        path.resolve().relative_to(ROOT)
        if file_hash(path) != digest:
            raise ValueError("Changed cycle artifact")
    report, dev = json.loads(report_path.read_text()), json.loads(dev_path.read_text())
    parent, parent_meta = Actor.load_export(parent_path)
    actor, metadata = Actor.load_export(actor_path)
    training = json.loads((actor_path.parent/"training.json").read_text())
    for record in (report, dev, metadata, training, parent_meta):
        if record["sourceHash"] != source_hash():
            raise ValueError("Source provenance mismatch")
        for key, path in (("contactModelHash", "Assets/Picklebot/Doubles/Models/contact.json"),
                          ("protocolHash", "config/player-agents/evaluation-v1.json"),
                          ("baselineManifestHash", "artifacts/player-agents/baseline-manifest.json")):
            if record[key] != file_hash(ROOT/path):
                raise ValueError("Changed frozen input: " + key)
    if (report["actorHash"] != file_hash(parent_path) or dev["actorHash"] != file_hash(actor_path)
            or metadata["parentActorHash"] != file_hash(parent_path) or training["actorHash"] != file_hash(actor_path)
            or report["opponentMode"] != "older actor / sampled" or report["split"] != "training"
            or not report["sampledActor"] or dev["split"] != "development" or dev["sampledActor"]
            or report["seed"] != config["seed"] or dev["seed"] != config["development_seed"]):
        raise ValueError("Actor, opponent, or split ownership mismatch")
    opponent = progress["opponentPool"][0]
    if (report["opponentHash"] != opponent["sha256"] or file_hash(opponent["file"]) != opponent["sha256"]
            or file_hash(folder/"opponents/0.json") != opponent["sha256"]
            or dev["opponentHash"] != file_hash(ROOT/"Assets/Picklebot/Doubles/Models/teams.json")):
        raise ValueError("Opponent changed")
    trainer_names = ("player-agents-ppo.py", "player_ppo.py", "player_actor.py")
    trainer_hash = hashlib.sha256(b"".join((folder/"trainer-source"/name).read_bytes() for name in trainer_names)).hexdigest()
    if metadata["trainerHash"] != trainer_hash or progress["driverHash"] != file_hash(folder/"trainer-source/player-agents-train-loop.py"):
        raise ValueError("Trainer snapshot mismatch")
    train_games, dev_games = game_outcomes(report), game_outcomes(dev)
    if (any(not 1000000 <= g["seed"] < 1100000 for g in train_games)
            or any(not 1100000 <= g["seed"] < 1200000 for g in dev_games)):
        raise ValueError("Seed partition mismatch")
    validate_motor_metrics(report); validate_motor_metrics(dev)
    data = ROOT/report["dataPath"]
    if file_hash(data) != metadata["dataHash"] or file_hash(report_path) != training["rolloutReportHash"]:
        raise ValueError("Rollout changed after fitting")
    records = [json.loads(line) for line in data.read_text().splitlines()]
    if not records or len(records) != report["rows"] or len(records) != training["rows"]:
        raise ValueError("Training record count mismatch")
    groups = validate_episodes(records, report)
    obs = torch.tensor([r["observation"] for r in records])
    raw = torch.tensor([[r["sample"]["rawX"], r["sample"]["rawZ"]] for r in records])
    hit = torch.tensor([float(r["sample"]["action"]["attempt"]) for r in records])
    shot = torch.tensor([r["sample"]["action"]["shot"] for r in records])
    old_logp = torch.tensor([r["sample"]["logProbability"] for r in records])
    with torch.no_grad():
        logp, _ = log_probability(parent, obs, raw, hit, shot)
        replay_error = float((logp-old_logp).abs().max())
    if not math.isfinite(replay_error) or replay_error > .001:
        raise ValueError("Sample likelihood does not replay")
    for i, row in enumerate(records):
        validate_replayed_action(row["sample"]["action"], Actor.movement(raw[i]), bool(hit[i]), int(shot[i]))
    # The first critic's output layer is zero. With gamma=lambda=1, each
    # initial advantage is its player's final team-game reward.
    outcome_by_seed = {g["seed"]: 1 if g["won"] else -1 for g in train_games}
    returns = torch.tensor([float(outcome_by_seed[r["gameSeed"]]) for r in records])
    advantage = (returns-returns.mean())/returns.std(unbiased=False).clamp_min(1e-6)
    signal = bool(advantage.abs().max() > 0)
    parity = json.loads((actor_path.parent/"unity-parity.json").read_text())
    if (not parity["passed"] or parity["actorHash"] != file_hash(actor_path)
            or parity["inputHash"] != file_hash(actor_path.parent/"parity-input.json")
            or training["gamma"] != 1 or training["gaeLambda"] != 1
            or metadata["trainingSteps"] != parent_meta["trainingSteps"]+training["updates"]):
        raise ValueError("Export or complete-game training contract mismatch")
    return dict(folder=str(folder), sourceHash=source_hash(), parentActorHash=file_hash(parent_path),
                actorHash=file_hash(actor_path), trainingReport=str(report_path), trainingReportHash=file_hash(report_path),
                developmentReport=str(dev_path), developmentReportHash=file_hash(dev_path),
                trainGames=train_games, developmentGames=dev_games, rows=len(records), playerTrajectories=len(groups),
                terminalRewards=dict(Counter(r["reward"] for r in records if r["terminal"])),
                sampledLogProbabilityMaximumError=replay_error, nonzeroGameWinPolicyGradientSignal=signal,
                positiveAdvantageRows=int((advantage > 0).sum()), negativeAdvantageRows=int((advantage < 0).sum()),
                updates=training["updates"], history=training["history"], stoppedForKL=training["stoppedForKL"],
                finalMeasuredKL=training["history"][-1]["kl"], targetKL=training["targetKL"],
                trainingCollectionSeconds=report["wallSeconds"], optimizerSeconds=training["elapsedSeconds"],
                developmentCollectionSeconds=dev["wallSeconds"], parity=parity,
                limitation="Verified game-win-labelled optimizer cycle. Training games are pre-update outcomes. Development here is a small sampled-baseline check, not final acceptance or proof of improvement.")


def audit_correction(folder, plan_path):
    """Verify the alternative raw-return update, not the rejected loop checkpoint."""
    torch.set_num_threads(2)
    plan = json.loads(plan_path.read_text())
    training = json.loads((folder / "training.json").read_text())
    actor_path = folder / "actor.json"
    parent_path, report_path = ROOT / plan["parentActor"], ROOT / plan["rollout"]
    report = json.loads(report_path.read_text())
    actor, metadata = Actor.load_export(actor_path)
    parent, parent_meta = Actor.load_export(parent_path)
    for key in ("sourceHash", "rewardMode", "epochs", "learningRate", "clip", "targetKL",
                "entropyCoefficient", "advantageNormalization", "creditAssignment",
                "trainHeads", "postUpdateKLRollback"):
        if training[key] != plan[key]:
            raise ValueError("Correction differs from plan: " + key)
    if (plan["initialCritic"] != "new zero-output critic" or training["gamma"] != 1
            or training["gaeLambda"] != 1 or training["entropyCoefficient"] != 0
            or training["advantageNormalization"] != "none" or training["entropyOnlyUpdate"]
            or not training["postUpdateKLRollback"] or training["updates"] <= 0):
        raise ValueError("Expected raw complete-game returns without entropy bonus")
    for path, digest in ((parent_path, plan["parentActorHash"]), (report_path, plan["rolloutHash"]),
                         (actor_path, training["actorHash"]), (folder/"critic.pt", training["criticHash"])):
        if file_hash(path) != digest: raise ValueError("Changed correction artifact")
    for record in (training, metadata, parent_meta, report):
        if record["sourceHash"] != source_hash(): raise ValueError("Source changed")
        for key, path in (("contactModelHash", "Assets/Picklebot/Doubles/Models/contact.json"),
                          ("protocolHash", "config/player-agents/evaluation-v1.json"),
                          ("baselineManifestHash", "artifacts/player-agents/baseline-manifest.json")):
            if record[key] != file_hash(ROOT/path): raise ValueError("Frozen input changed")
        if record["configurationHash"] != training["configurationHash"]:
            raise ValueError("Physics configuration differs")
    if (report["split"] != "training" or not report["sampledActor"]
            or report["actorHash"] != file_hash(parent_path)
            or training["parentActorHash"] != file_hash(parent_path)
            or metadata["parentActorHash"] != file_hash(parent_path)
            or training["rolloutReportHash"] != file_hash(report_path)
            or metadata["trainingSteps"] != parent_meta["trainingSteps"] + training["updates"]):
        raise ValueError("On-policy parent or training ownership mismatch")
    names = ("player-agents-ppo.py", "player_ppo.py", "player_actor.py")
    for name in names:
        if file_hash(folder/"trainer-source"/name) != training["trainerSources"][name]:
            raise ValueError("Trainer snapshot changed")
    digest = hashlib.sha256(b"".join((folder/"trainer-source"/n).read_bytes() for n in names)).hexdigest()
    if digest != training["trainerHash"] or digest != metadata["trainerHash"]:
        raise ValueError("Trainer digest differs")
    games = game_outcomes(report); validate_motor_metrics(report)
    if any(not 1000000 <= g["seed"] < 1100000 for g in games):
        raise ValueError("Not training seeds")
    data = ROOT/report["dataPath"]
    if file_hash(data) != training["dataHash"] or file_hash(data) != metadata["dataHash"]:
        raise ValueError("Training data changed")
    records = [json.loads(line) for line in data.read_text().splitlines()]
    if len(records) != report["rows"] or len(records) != training["rows"]:
        raise ValueError("Training row count differs")
    trajectories = validate_episodes(records, report)
    obs = torch.tensor([r["observation"] for r in records])
    raw = torch.tensor([[r["sample"]["rawX"], r["sample"]["rawZ"]] for r in records])
    hit = torch.tensor([float(r["sample"]["action"]["attempt"]) for r in records])
    shot = torch.tensor([r["sample"]["action"]["shot"] for r in records])
    old_logp = torch.tensor([r["sample"]["logProbability"] for r in records])
    outcomes = {g["seed"]: 1. if g["won"] else -1. for g in games}
    advantage = prepare_advantages(torch.tensor([outcomes[r["gameSeed"]] for r in records]), "none")
    with torch.no_grad():
        replay, _ = log_probability(parent, obs, raw, hit, shot)
        current, _ = log_probability(actor, obs, raw, hit, shot)
        _, kl = clipped_loss(current, old_logp, advantage, training["clip"])
    error = float((replay-old_logp).abs().max())
    if (not math.isfinite(error) or error > .001 or not math.isfinite(float(kl))
            or float(kl) > training["targetKL"]
            or abs(float(kl)-training["history"][-1]["kl"]) > 1e-6
            or training["negativeAdvantageRows"] != int((advantage < 0).sum())
            or training["positiveAdvantageRows"] != int((advantage > 0).sum())):
        raise ValueError("Return signal or likelihood replay differs")
    parity = json.loads((folder/"unity-parity.json").read_text())
    if (not parity["passed"] or parity["actorHash"] != file_hash(actor_path)
            or parity["sourceHash"] != source_hash() or parity["cases"] < 1
            or not 0 <= parity["maximumError"] < .0001
            or parity["inputHash"] != file_hash(folder/"parity-input.json")):
        raise ValueError("Unity parity changed or failed")
    return dict(folder=str(folder), planHash=file_hash(plan_path), actorHash=file_hash(actor_path),
                parentActorHash=file_hash(parent_path), sourceHash=source_hash(), rows=len(records),
                playerTrajectories=len(trajectories), games=games, updates=training["updates"],
                negativeAdvantageRows=int((advantage < 0).sum()), entropyCoefficient=0,
                finalMeasuredKL=float(kl), sampledLogProbabilityMaximumError=error, parity=parity,
                optimizerSeconds=training["elapsedSeconds"], rejectedUpdates=training["rejectedUpdates"],
                limitation="Raw all-loss returns give a high-variance reward-derived update. No match improvement is established. Snapshot checks and final KL replay do not replay every optimizer step.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("folder", type=Path)
    parser.add_argument("--correction-plan", type=Path)
    args = parser.parse_args()
    result = audit_correction(args.folder, args.correction_plan) if args.correction_plan else audit(args.folder)
    print(json.dumps(result, indent=2))
