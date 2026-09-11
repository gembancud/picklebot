#!/usr/bin/env python3
"""Fail closed when doubles evidence is missing, stale or below acceptance gates."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def canonical_path(path):
    return str(path).replace("\\", "/")


def canonical_text(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def ordinal_key(path):
    return canonical_path(path).encode("utf-16-be")


def source_record_text(records):
    records = [(canonical_path(path), canonical_text(text)) for path, text in records]
    return "\n".join(path + "\n" + text for path, text in sorted(records, key=lambda item: ordinal_key(item[0])))


def source_records(root, folders, excluded=()):
    records = []
    for folder in folders:
        for path in (root / "Assets/Picklebot" / folder).rglob("*.cs"):
            name = path.relative_to(root).as_posix()
            if "/Tests/" not in name and path.name not in excluded:
                records.append((name, path.read_text(encoding="utf-8-sig")))
    return records


def source_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def contact_source_hash(root=ROOT):
    return source_digest(source_record_text(source_records(root, ("Doubles", "Core", "Simulation"), ("DoublesDemo.cs", "DoublesEditor.cs"))))


def player_source_hash(root):
    return source_digest(contact_source_hash(root) + "\n" + source_record_text(source_records(root, ("PlayerAgents",))))


def team_source_hash(root):
    paths = sorted((root / "Assets/Picklebot/DoublesTraining").rglob("*.cs"), key=lambda p: ordinal_key(p.relative_to(root)))
    return source_digest(contact_source_hash(root) + "\n".join(canonical_text(p.read_text(encoding="utf-8-sig")) for p in paths))


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    model = read("Assets/Picklebot/Doubles/Models/contact.json")
    contact = read("artifacts/doubles/contact-validation.json")
    current_hash = contact_source_hash()
    check(model["sourceHash"] == contact["sourceHash"] == current_hash, "Contact source evidence is stale")
    check(contact["configurationHash"] == model["configurationHash"], "Contact physics hash mismatch")
    check(contact["initialModelHash"] == digest((ROOT / "Assets/Picklebot/Doubles/Models/contact.json").read_text()), "Contact validation used a different checkpoint")
    check(all(t["seed"] >= 930000 for t in contact["trials"]), "Contact validation uses training seeds")
    for kind in range(3):
        trials = [t for t in contact["trials"] if t["kind"] == kind]
        good = sum(t["legal"] and t["spinCorrect"] for t in trials)
        check(len(trials) >= 20, f"Stroke {kind}: too few held-out trials")
        check(good / len(trials) >= .90, f"Stroke {kind}: only {good}/{len(trials)} legal shots with correct spin")
        print(f"Stroke {kind}: {good}/{len(trials)} legal shots with correct spin")

    tests = read("artifacts/doubles/rules-tests.json")
    physics = read("artifacts/doubles/physics-tests.json")
    for result in (tests, physics):
        check(result["status"] == "completed" and result["summary"]["failed"] == 0, "Unity tests are incomplete or failed")
        check(result["summary"]["passed"] > 0, "No tests ran")

    teams = read("Assets/Picklebot/Doubles/Models/teams.json")
    training = read("artifacts/doubles/teams-training.json")
    validation = read("artifacts/doubles/teams-trained.json")
    team_hash = team_source_hash(ROOT)
    check(teams["sourceHash"] == training["sourceHash"] == validation["sourceHash"] == team_hash, "Team source evidence is stale")
    contact_hash = digest((ROOT / "Assets/Picklebot/Doubles/Models/contact.json").read_text())
    check(teams["contactModelHash"] == contact_hash == validation["contactModelHash"], "Team contact model hash mismatch")
    check(validation["teamModelHash"] == digest((ROOT / "Assets/Picklebot/Doubles/Models/teams.json").read_text()), "Validation used a different team checkpoint")
    check(len(training["rallies"]) >= 500 and teams["rallies"] >= 500, "Team training is incomplete")
    check(validation["seed"] >= 940000 and training["seed"] < 920000, "Team seed partitions overlap")
    rallies = validation["rallies"]
    check(len(rallies) >= 100, "Too few held-out doubles rallies")
    check(validation["games"] >= 3, "Fewer than three full validation games")
    check(sum(r["winner"] >= 0 for r in rallies) / len(rallies) >= .9, "Too many truncated rallies")
    for player in range(4):
        count = sum(r["playerHits"][player] for r in rallies)
        check(count >= 10, f"Player {player + 1} has too few contact events: {count}")
    check(min(r["minSeparation"] for r in rallies) >= .559, "Teammate separation limit failed")
    check(max(r["maxReach"] for r in rallies) <= .635, "Arm reach limit failed")
    check(max(r["maxPaddleSpeed"] for r in rallies) <= 12.05, "Paddle speed limit failed")
    print(f"Doubles: {len(rallies)} validation rallies; {validation['games']} complete games")
    sampled = read("artifacts/doubles/teams-random.json")
    check(sampled["sourceHash"] == team_hash and sampled["contactModelHash"] == contact_hash, "Sampled-policy evidence is stale")
    check(sampled["teamModelHash"] == validation["teamModelHash"], "Sampled play used a different team checkpoint")
    points = sampled["rallies"]
    check(len(points) >= 100 and sampled["games"] >= 3, "Sampled-play validation is incomplete")
    check(sum(r["winner"] >= 0 for r in points) / len(points) >= .9, "Sampled play has too many truncated rallies")
    check(min(r["minSeparation"] for r in points) >= .559, "Sampled-play separation limit failed")
    check(max(r["maxReach"] for r in points) <= .635, "Sampled-play reach limit failed")
    check(max(r["maxPaddleSpeed"] for r in points) <= 12.05, "Sampled-play paddle speed limit failed")
    for player in range(4):
        check(sum(r["playerHits"][player] for r in points) >= 10, "Sampled play did not use all four players")
    styles = {0 if d["action"] < 5 else 1 if d["action"] < 7 else 2 for r in points for d in r["decisions"]}
    check(styles == {0, 1, 2}, "Sampled play did not select all three contact styles")
    replay = read("artifacts/doubles/replay-verification.json")
    check(replay["physicsUnchanged"] and replay["poseExact"], "Replay does not preserve the recorded state")
    print(f"Sampled policy: {len(points)} validation rallies; {sampled['games']} complete games")
    print("Doubles acceptance evidence passed. Physics remains provisional.")


if __name__ == "__main__":
    main()
