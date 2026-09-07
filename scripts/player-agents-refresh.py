#!/usr/bin/env python3
"""Finish one existing curriculum job, fit a warm start, and test it locally.

No scene edits, final evaluation, cloud jobs, or automatic model promotion.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import shutil
import sys
import time

from player_actor import ROOT, file_hash, source_hash, teacher_data
from player_ppo import validate_motor_metrics

spec = importlib.util.spec_from_file_location("player_train_loop", ROOT / "scripts/player-agents-train-loop.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def validate_teacher_motors(report):
    games = report.get("gameResults", [])
    if not games:
        raise ValueError("Missing teacher motor measurements")
    owned = []
    for game in games:
        if game["candidateTeam"] == -1 and not report.get("baselineOpponent"):
            owned.extend({**game, "candidateTeam": team} for team in (0, 1))
        else:
            owned.append(game)
    validate_motor_metrics({"games": owned})


def validate_curriculum(path, seed, split, source, fixed_shot=0, teacher_probability=1, actor_path=None, four_player=False):
    report = json.loads(path.read_text())
    if (report["sourceHash"] != source or report["seed"] != seed or report["split"] != split
            or report["baselineOpponent"] is not (not four_player) or report["teacherProbability"] != teacher_probability or report["fixedShot"] != fixed_shot):
        raise ValueError("Curriculum identity or settings changed")
    if teacher_probability < 1 and (actor_path is None or report.get("actorHash") != file_hash(actor_path)):
        raise ValueError("Curriculum collection actor changed or is missing")
    teacher_data(path, split)
    validate_teacher_motors(report)


def wait_curriculum(expected_path, seed, split, source, fixed_shot=0, teacher_probability=1, actor_path=None, four_player=False):
    deadline = time.monotonic() + 1800
    last_print = 0
    while time.monotonic() < deadline:
        state = driver.evaluate("return new {running=Picklebot.PlayerAgents.Editor.PlayerCurriculum.Running,"
                                "status=Picklebot.PlayerAgents.Editor.PlayerCurriculum.Status};")
        if time.monotonic() - last_print >= 30 or not state["running"]:
            print(state["status"], flush=True)
            last_print = time.monotonic()
        if not state["running"]:
            if not state["status"].startswith("complete: "):
                raise RuntimeError("Curriculum did not complete: " + state["status"])
            path = (ROOT / state["status"].removeprefix("complete: ")).resolve()
            path.relative_to(ROOT / "artifacts/player-agents")
            if expected_path and path != expected_path.resolve():
                raise ValueError("A different curriculum job completed")
            validate_curriculum(path, seed, split, source, fixed_shot, teacher_probability, actor_path, four_player)
            return path
        time.sleep(10)
    raise TimeoutError("Curriculum wait expired; inspect the existing job before any restart")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_report", type=Path)
    parser.add_argument("--training-seed", type=int, required=True)
    parser.add_argument("--development-seed", type=int, required=True)
    parser.add_argument("--match-seed", type=int, required=True)
    parser.add_argument("--fixed-shot", type=int, default=0)
    parser.add_argument("--teacher-probability", type=float, default=1)
    parser.add_argument("--development-report", type=Path)
    parser.add_argument("--initial-actor", type=Path)
    parser.add_argument("--allow-historical-initial", action="store_true",
                        help="Reuse older-runtime weights, while requiring current-runtime collection data")
    parser.add_argument("--additional-training-report", type=Path, action="append", default=[])
    parser.add_argument("--additional-development-report", type=Path, action="append", default=[])
    parser.add_argument("--balance-training-sources", action="store_true")
    parser.add_argument("--four-player", action="store_true", help="Require four teacher/learner policies, not frozen-baseline opponents")
    parser.add_argument("--primary-serve-flight-only", action="store_true")
    parser.add_argument("--neutral-paddle-probability", type=float, default=.8)
    parser.add_argument("--development-rallies", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=160)
    parser.add_argument("--learning-rate", type=float, default=.001)
    args = parser.parse_args()
    if not 0 <= args.neutral_paddle_probability <= 1 or not 1 <= args.development_rallies <= 128:
        parser.error("Invalid paddle augmentation or development collection size")
    if args.allow_historical_initial and not args.initial_actor:
        parser.error("Historical initialization requires --initial-actor")
    if not (1000000 <= args.training_seed < 1099000
            and 1100000 <= args.development_seed < 1199000
            and 1100000 <= args.match_seed < 1198000
            and abs(args.match_seed - args.development_seed) >= 1000):
        parser.error("Use separate training and development seed blocks")
    if not -1 <= args.fixed_shot <= 8 or args.epochs < 1 or not 0 < args.learning_rate < 1:
        parser.error("Invalid shot curriculum or optimizer settings")
    if not 0 <= args.teacher_probability <= 1 or (args.teacher_probability < 1 and not args.initial_actor):
        parser.error("Mixed or learner-only collection requires an initial actor and a valid teacher probability")
    source = source_hash()
    folder = ROOT / "artifacts/player-agents" / ("refresh-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    folder.mkdir(exist_ok=False)
    snapshot = folder / "driver-source"; snapshot.mkdir()
    for name in ("player-agents-refresh.py", "player-agents-train-loop.py", "player_actor.py", "player_ppo.py"):
        shutil.copy2(ROOT / "scripts" / name, snapshot / name)
    report = dict(status="waiting_training_data", sourceHash=source, driverHash=file_hash(__file__),
                  settings={key: [str(p) for p in value] if isinstance(value, list) else str(value) if isinstance(value, Path) else value
                            for key, value in vars(args).items()},
                  acceptance="Development-only imitation warm start. No model promotion.")
    def save():
        (folder / "progress.json").write_text(json.dumps(report, indent=2))
    print(folder, flush=True)
    save()
    try:
        training = wait_curriculum(args.training_report, args.training_seed, "training", source, args.fixed_shot,
                                   args.teacher_probability, args.initial_actor, args.four_player)
        report.update(trainingReport=str(training), trainingReportHash=file_hash(training), status="development_data")
        save()
        if args.development_report:
            development = args.development_report.resolve()
            development.relative_to(ROOT / "artifacts/player-agents")
            validate_curriculum(development, args.development_seed, "development", source, args.fixed_shot,
                                args.teacher_probability, args.initial_actor, args.four_player)
        else:
            driver.evaluate("Picklebot.PlayerAgents.Editor.PlayerCurriculum.Start(rallies:" + str(args.development_rallies) + ",seed:"
                            + str(args.development_seed) + ",development:true,teacherProbability:" + str(args.teacher_probability) + "f,fixedShot:"
                            + str(args.fixed_shot) + ",actorPath:" + json.dumps(str(args.initial_actor) if args.teacher_probability < 1 else "")
                            + ",baselineOpponent:" + str(not args.four_player).lower() + ",sampleBaseline:true); return Picklebot.PlayerAgents.Editor.PlayerCurriculum.Status;")
            development = wait_curriculum(None, args.development_seed, "development", source, args.fixed_shot,
                                         args.teacher_probability, args.initial_actor, args.four_player)
        report.update(developmentReport=str(development), developmentReportHash=file_hash(development), status="fitting")
        save()
        command = [sys.executable, "scripts/player-agents-imitate.py", str(training), str(development),
                   "--epochs", str(args.epochs), "--hidden", "256", "--batch", "1024",
                   "--learning-rate", str(args.learning_rate), "--neutral-paddle-probability", str(args.neutral_paddle_probability)]
        if args.primary_serve_flight_only:
            command += ["--primary-serve-flight-only"]
        if args.initial_actor:
            command += ["--initial-actor", str(args.initial_actor)]
        if args.allow_historical_initial:
            command += ["--allow-historical-initial"]
        if args.balance_training_sources:
            command += ["--balance-training-sources"]
        for option, paths in (("--additional-training-report", args.additional_training_report),
                              ("--additional-development-report", args.additional_development_report)):
            for path in paths:
                validate_teacher_motors(json.loads(path.read_text()))
                command += [option, str(path)]
        with (folder / "fit.log").open("w") as log:
            process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            last_line = ""
            for line in process.stdout:
                log.write(line); log.flush(); print(line, end="", flush=True); last_line = line.strip()
            if process.wait():
                raise RuntimeError("Imitation fitting failed; see fit.log")
        checkpoint = Path(last_line).resolve()
        checkpoint.relative_to(ROOT / "artifacts/player-agents")
        actor = checkpoint / "actor.json"
        report.update(actor=str(actor), actorHash=file_hash(actor), status="parity")
        save()
        driver.evaluate("return Picklebot.PlayerAgents.Editor.ActorChecks.Parity(" + json.dumps(str(actor))
                        + "," + json.dumps(str(checkpoint / "parity-input.json")) + ");")
        report["parity"] = json.loads((checkpoint / "unity-parity.json").read_text())
        if not report["parity"]["passed"] or report["parity"]["sourceHash"] != source:
            raise ValueError("Export parity or source mismatch")
        report["status"] = "actor_only_matches"
        save()
        matches = driver.collect(actor, None, args.match_seed, 32, True, source)
        report.update(matches=str(matches), matchesHash=file_hash(matches), status="complete")
        save()
        print(json.dumps({"refresh": str(folder), "actor": str(actor), "matches": str(matches)}), flush=True)
    except BaseException as error:
        report.update(status="stopped", error=str(error))
        save()
        raise


if __name__ == "__main__":
    main()
