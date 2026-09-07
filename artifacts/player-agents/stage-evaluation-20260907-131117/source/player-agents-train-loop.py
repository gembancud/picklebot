#!/usr/bin/env python3
"""Run a bounded, local sequence of source-tracked player PPO updates.

Requires the project's connected Editor in Play mode. Does not change scenes,
start paid jobs, select a winning model, or use final evaluation seeds.
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import shutil
import sys
import time

from player_actor import ROOT, file_hash, source_hash
from player_ppo import validate_motor_metrics


def opponent_schedule(opponent=None, pool=None, include_baseline=False, start_index=0):
    """Freeze an ordered pool; None denotes the sampled doubles baseline."""
    if opponent and pool:
        raise ValueError("Use either --opponent or --opponent-pool")
    if include_baseline and not pool:
        raise ValueError("--pool-baseline requires --opponent-pool")
    paths = [Path(path).resolve() for path in (pool or ([opponent] if opponent else []))]
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate saved opponent paths")
    if not paths or include_baseline:
        paths.append(None)
    if len(paths) > 4:
        raise ValueError("At most four fixed opponents are supported")
    if not 0 <= start_index < len(paths):
        raise ValueError("Opponent start index is outside the fixed pool")
    return paths[start_index:] + paths[:start_index]


def check_opponents(manifest):
    for entry in manifest:
        if file_hash(entry["file"]) != entry["sha256"]:
            raise RuntimeError("Saved opponent changed: " + entry["file"])


def unity_value(envelope):
    if not envelope.get("success"):
        raise RuntimeError(f"Unity command failed: {envelope.get('errors')}")
    data = envelope["data"]
    if Path(data["target"]["projectPath"]).resolve() != ROOT.resolve():
        raise RuntimeError("Unity selected a different project")
    result = data["result"]
    if not isinstance(result, dict) or not result.get("success"):
        raise RuntimeError(f"Unity evaluation failed: {result}")
    return result["result"]


def evaluate(code):
    # Never retry a state-changing command after an uncertain response.
    result = subprocess.run(["unity", "command", "eval", code, "--format", "json"],
                            cwd=ROOT, capture_output=True, text=True, timeout=45)
    return unity_value(json.loads(result.stdout))


def collect(actor, opponent, seed, rallies, development, source, reward_mode="game_win"):
    if source_hash() != source:
        raise RuntimeError("Runtime source changed; stop before another collection")
    args = [json.dumps(str(actor)), f"rallies:{rallies}", f"seed:{seed}",
            f"development:{str(development).lower()}",
            f"sampledActor:{str(not development).lower()}", "rewardMode:" + json.dumps(reward_mode),
            "allowHistoricalCandidate:true"]
    if opponent:
        args.append("opponentActorPath:" + json.dumps(str(opponent)))
    print(f"Start {'development' if development else 'training'} seed {seed}", flush=True)
    evaluate("Picklebot.PlayerAgents.Editor.PlayerCompetition.Start(" + ",".join(args)
             + "); return Picklebot.PlayerAgents.Editor.PlayerCompetition.Status;")
    deadline = time.monotonic() + 1800
    last_print = 0
    while time.monotonic() < deadline:
        time.sleep(10)
        state = evaluate("return new { running = Picklebot.PlayerAgents.Editor.PlayerCompetition.Running,"
                         " status = Picklebot.PlayerAgents.Editor.PlayerCompetition.Status };")
        if time.monotonic() - last_print >= 30 or not state["running"]:
            print(state["status"], flush=True); last_print = time.monotonic()
        if state["running"]:
            continue
        if not state["status"].startswith("complete: "):
            raise RuntimeError("Collection did not complete: " + state["status"])
        path = (ROOT / state["status"].removeprefix("complete: ")).resolve()
        path.relative_to(ROOT / "artifacts/player-agents")
        report = json.loads(path.read_text())
        expected_opponent = opponent or ROOT / "Assets/Picklebot/Doubles/Models/teams.json"
        if (report["seed"] != seed or report["actorHash"] != file_hash(actor)
                or report["sourceHash"] != source or report["status"] != "complete"
                or report["opponentHash"] != file_hash(expected_opponent)
                or report["sampledActor"] != (not development) or report["rewardMode"] != reward_mode
                or report["split"] != ("development" if development else "training")
                or not report["games"] or not all(g["complete"] for g in report["games"])):
            raise RuntimeError("Collection identity, provenance or completion mismatch")
        # Development failures must stop this sequence too. Waiting until the
        # next optimizer call would check training data but miss unsafe tests.
        validate_motor_metrics(report)
        return path
    raise RuntimeError("Collection wait expired. Inspect the active job before any restart.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actor", type=Path)
    parser.add_argument("--opponent", type=Path, help="Saved actor; omit for the frozen sampled baseline")
    parser.add_argument("--opponent-pool", type=Path, nargs="+", help="Fixed saved actors, used in round-robin order")
    parser.add_argument("--pool-baseline", action="store_true", help="Append the frozen sampled baseline to the pool")
    parser.add_argument("--opponent-start-index", type=int, default=0, help="Start at this fixed-pool index; preserve order after an interrupted run")
    parser.add_argument("--critic", type=Path)
    parser.add_argument("--heads", choices=("all", "shots"), default="all")
    parser.add_argument("--reward-mode", choices=("rally_win", "game_win"), default="game_win")
    parser.add_argument("--credit-assignment", choices=("default", "full_episode"), default="default")
    parser.add_argument("--entropy", type=float, default=.001)
    parser.add_argument("--advantage-normalization", choices=("standard", "none"), default="standard")
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--rallies", type=int, default=256)
    parser.add_argument("--seed", type=int, default=1003000)
    parser.add_argument("--development-seed", type=int, default=1102000)
    args = parser.parse_args()
    if not math.isfinite(args.entropy) or args.entropy < 0:
        parser.error("Entropy coefficient must be finite and nonnegative")
    if not (1 <= args.iterations <= 20 and 32 <= args.rallies <= 512
            and 1000000 <= args.seed and args.seed + 1000 * args.iterations + 2000 < 1100000
            and 1100000 <= args.development_seed and args.development_seed + 1000 * args.iterations + 2000 < 1200000):
        parser.error("Invalid bounded run size or seed partitions")
    try:
        opponents = opponent_schedule(args.opponent, args.opponent_pool, args.pool_baseline, args.opponent_start_index)
    except ValueError as error:
        parser.error(str(error))
    actor = args.actor.resolve(); opponent = opponents[0]; critic = args.critic
    baseline_file = ROOT / "Assets/Picklebot/Doubles/Models/teams.json"
    manifest = [dict(index=index, actor=str(path) if path else None,
                     file=str(path or baseline_file), sha256=file_hash(path or baseline_file))
                for index, path in enumerate(opponents)]
    source = source_hash()
    folder = ROOT / "artifacts/player-agents" / ("training-loop-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False)
    snapshot = folder / "trainer-source"; snapshot.mkdir()
    opponent_snapshot = folder / "opponents"; opponent_snapshot.mkdir()
    for entry in manifest:
        target = opponent_snapshot / (str(entry["index"]) + ".json")
        shutil.copy2(entry["file"], target)
        if file_hash(target) != entry["sha256"]:
            raise RuntimeError("Opponent changed during snapshot")
    manifest_path = opponent_snapshot / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    for name in ("player_actor.py", "player_ppo.py", "player-agents-ppo.py", "player-agents-train-loop.py"):
        shutil.copy2(ROOT / "scripts" / name, snapshot / name)
    for path in (ROOT / "Assets/Picklebot/PlayerAgents").rglob("*.cs"):
        if "/Tests/" in str(path): continue
        target = folder / "runtime-source" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)
    report = dict(status="running", sourceHash=source, initialActor=str(actor), initialActorHash=file_hash(actor),
                  initialCriticHash=file_hash(critic) if critic else None,
                  opponent=(str(opponent) if opponent else "frozen sampled baseline") if len(opponents) == 1 else "fixed round-robin pool",
                  opponentHash=manifest[0]["sha256"] if len(opponents) == 1 else None,
                  opponentPool=manifest, opponentPoolHash=file_hash(manifest_path), driverHash=file_hash(__file__),
                  configuration=vars(args) | {"actor": str(actor), "opponent": str(args.opponent.resolve()) if args.opponent else None,
                                             "opponent_pool": [str(path.resolve()) for path in args.opponent_pool] if args.opponent_pool else None,
                                             "critic": str(critic) if critic else None},
                  iterations=[], acceptance="Development only. No automatic promotion or final acceptance.")

    def save():
        (folder / "progress.json").write_text(json.dumps(report, indent=2))

    print(folder, flush=True); save()
    try:
        for iteration in range(args.iterations):
            check_opponents(manifest)
            opponent = opponents[iteration % len(opponents)]
            entry = manifest[iteration % len(opponents)]
            record = dict(iteration=iteration + 1, parentActor=str(actor), parentActorHash=file_hash(actor),
                          opponent=entry["actor"] or "frozen sampled baseline", opponentHash=entry["sha256"],
                          opponentPoolIndex=entry["index"], status="collecting")
            report["iterations"].append(record); save()
            rollout = collect(actor, opponent, args.seed + 1000 * iteration, args.rallies, False, source, args.reward_mode)
            record.update(rollout=str(rollout), rolloutHash=file_hash(rollout), status="updating"); save()
            command = [sys.executable, "scripts/player-agents-ppo.py", str(rollout), str(actor),
                       "--epochs", "4", "--batch", "1024", "--learning-rate", "0.00003", "--heads", args.heads,
                       "--credit-assignment", args.credit_assignment, "--entropy", str(args.entropy),
                       "--advantage-normalization", args.advantage_normalization]
            if critic:
                command += ["--critic", str(critic)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=600)
            (folder / f"update-{iteration + 1}.log").write_text(result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError("PPO update failed; inspect its saved log")
            checkpoint = Path(json.loads(result.stdout.strip().splitlines()[-1])["folder"]).resolve()
            checkpoint.relative_to(ROOT / "artifacts/player-agents")
            actor = checkpoint / "actor.json"; critic = checkpoint / "critic.pt"
            record.update(actor=str(actor), actorHash=file_hash(actor), status="parity"); save()
            evaluate("return Picklebot.PlayerAgents.Editor.ActorChecks.Parity(" + json.dumps(str(actor))
                     + "," + json.dumps(str(checkpoint / "parity-input.json")) + ");")
            record["parity"] = json.loads((checkpoint / "unity-parity.json").read_text())
            if not record["parity"]["passed"] or record["parity"]["actorHash"] != file_hash(actor):
                raise RuntimeError("Export parity failed")
            record["status"] = "development"; save()
            dev = collect(actor, None, args.development_seed + 1000 * iteration, 32, True, source)
            record.update(development=str(dev), developmentHash=file_hash(dev), status="complete"); save()
        report["status"] = "complete"; save()
    except BaseException as error:
        report.update(status="stopped", error=str(error)); save()
        raise


if __name__ == "__main__":
    main()
