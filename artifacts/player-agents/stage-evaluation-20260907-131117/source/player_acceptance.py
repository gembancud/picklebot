"""Fail-closed checks for the frozen player baseline evaluation.

Passing these checks is not full goal acceptance. Coverage, movement ablation,
older-opponent comparison, physical tests and scene verification are separate.
"""
from collections import Counter
import json
import math
from pathlib import Path


def validate_player_identities(game, swapped, protocol):
    """Check the seat assignment and RNG ownership, not just a swap label."""
    team = game["candidateTeam"]
    identities = list(range(4))
    if swapped:
        identities[2 * team], identities[2 * team + 1] = identities[2 * team + 1], identities[2 * team]
    actual = game.get("identityBySeat")
    if actual != identities or any(type(i) is not int for i in actual):
        raise ValueError("Player identities were not assigned to the expected seats")
    seeds = [(game["gameSeed"] * 397 + i * 7919 + 2**31) % 2**32 - 2**31 for i in identities]
    if game.get("randomSeedBySeat") != seeds:
        raise ValueError("Independent RNG streams did not follow player identities")
    counts = game.get("decisionCounts", [])
    first = game.get("firstDecisions", [])
    if len(counts) != 4 or len(first) != 4 or any(type(n) is not int or n < 0 for n in counts):
        raise ValueError("Missing per-player decision evidence")
    for seat in range(4):
        if seat // 2 != team and counts[seat] != 0:
            raise ValueError("Candidate actor controlled a baseline seat")
        if counts[seat] == 0:
            if first[seat] is not None:
                raise ValueError("Decision trace exists without a decision")
        else:
            row = first[seat]
            if (not isinstance(row, dict) or row.get("player") != seat or row.get("observationPlayer") != seat
                    or row.get("identity") != identities[seat] or type(row.get("observationTick")) is not int
                    or row["observationTick"] < 0 or row["observationTick"] % protocol["decisionTicks"] != 0
                    or row.get("applyTick") != row["observationTick"] + protocol["actionLatencyTicks"]):
                raise ValueError("Player decision ownership or latency mismatch")


def validate_runner_artifacts(report_path, report, root, file_hash):
    """Verify the reserved schedule, collector snapshot and terminal run record."""
    artifact_root = (Path(root) / "artifacts/player-agents").resolve()
    def artifact(path):
        value = (Path(root) / path).resolve()
        value.relative_to(artifact_root)
        return value
    snapshot = artifact(report["collectorSnapshotPath"])
    plan_path = artifact(report["evaluationPlanPath"])
    if file_hash(snapshot) != report["collectorHash"] or file_hash(plan_path) != report["evaluationPlanHash"]:
        raise ValueError("Evaluation collector or frozen schedule changed")
    plan = json.loads(plan_path.read_text())
    completion = json.loads((plan_path.parent / "completion.json").read_text())
    actual_path = artifact(report_path)
    if (actual_path.parent != plan_path.parent or snapshot.parent != plan_path.parent
            or completion.get("status") != "complete" or completion.get("evaluationPlanHash") != report["evaluationPlanHash"]
            or completion.get("reportHashes", {}).get(actual_path.name) != file_hash(actual_path)):
        raise ValueError("Evaluation run is not terminal or a report changed")
    for field in ("split", "sourceHash", "actorHash", "protocolHash", "baselineManifestHash", "contactModelHash",
                  "opponentHash", "collectorHash", "sampledActor"):
        if plan.get(field) != report.get(field):
            raise ValueError("Report differs from its reserved schedule: " + field)
    for field in ("sourceHash", "actorHash"):
        if completion.get(field) != report.get(field):
            raise ValueError("Completion provenance differs from report")
    for field in ("flatPitchOffsetDegrees", "experimentalContactOverride", "candidateContactParameters"):
        if plan.get(field) != report.get(field):
            raise ValueError("Contact correction differs from the reserved schedule")
    group = report["group"]
    if type(group) is not int or not 0 <= group < 8 or len(plan["groups"]) != 8:
        raise ValueError("Invalid evaluation group")
    entry = plan["groups"][group]
    if (entry["group"] != group or entry["swapPartnerIdentities"] != report["swapPartnerIdentities"]
            or entry["candidateTeam"] != report["initialCandidateTeam"]
            or entry["sampleBaseline"] != (report["opponentMode"] == "baseline / sampled")
            or entry["seeds"] != [g["gameSeed"] for g in report["games"]]
            or any(g["candidateTeam"] != entry["candidateTeam"] for g in report["games"])):
        raise ValueError("Played games differ from the reserved group")
    scheduled = [seed for entry in plan["groups"] for seed in entry["seeds"]]
    if scheduled != plan["seedList"] or len(set(scheduled)) != len(scheduled) or completion.get("games") != len(scheduled):
        raise ValueError("Reserved schedule is incomplete or repeats seeds")
    return report["evaluationPlanHash"]


def wilson_lower(wins, total, z):
    if total <= 0 or not 0 <= wins <= total:
        raise ValueError("Invalid win count")
    p = wins / total
    z2 = z * z
    return (p + z2 / (2 * total) - z * math.sqrt(p * (1 - p) / total + z2 / (4 * total * total))) / (1 + z2 / total)


def audit_baseline(reports, protocol, expected):
    """Audit real reports against caller-verified hashes and frozen conditions.

The final collector must explicitly report partner swaps and control timing.
Old development reports lack this evidence and cannot pass this function.
"""
    required_hashes = {"sourceHash", "actorHash", "configurationHash", "contactModelHash", "protocolHash", "baselineManifestHash", "opponentHash"}
    if not required_hashes.issubset(expected) or any(not expected[key] for key in required_hashes):
        raise ValueError("The caller must verify every required provenance hash")
    modes = {"baseline / maximum probability": "maximum_probability", "baseline / sampled": "sampled_policy"}
    counts = Counter(); wins = Counter(); groups = Counter(); seeds = set()
    hits = [0] * 4
    rally_count = truncated = incomplete = 0
    candidate_sampling = None
    for report in reports:
        if report["split"] != "final" or report["status"] not in ("complete", "incomplete_game"):
            raise ValueError("Only retained final game reports are accepted")
        if report.get("flatPitchOffsetDegrees", 0) != 0 or report.get("experimentalContactOverride", False):
            raise ValueError("Experimental contact overrides cannot pass final acceptance")
        for name, value in expected.items():
            if report.get(name) != value:
                raise ValueError("Final provenance mismatch: " + name)
        for name in ("physicsHz", "decisionTicks", "actionLatencyTicks"):
            if report.get(name) != protocol[name]:
                raise ValueError("Missing or changed control timing: " + name)
        if report.get("historicalCandidate") is not False or report["actorTrainingSourceHash"] != expected["sourceHash"]:
            raise ValueError("Final actor was not trained for this source")
        if report.get("dataPath"):
            raise ValueError("Final games must not emit training data")
        mode = modes.get(report["opponentMode"])
        if mode not in protocol["baselineModes"]:
            raise ValueError("Unknown baseline mode")
        swapped = report.get("swapPartnerIdentities")
        if type(swapped) is not bool or type(report["sampledActor"]) is not bool:
            raise ValueError("Missing partner identity or sampling evidence")
        if candidate_sampling is None:
            candidate_sampling = report["sampledActor"]
        if candidate_sampling != report["sampledActor"]:
            raise ValueError("Candidate sampling changed between final games")
        owners = {}
        for game in report["games"]:
            seed = game["gameSeed"]; team = game["candidateTeam"]
            if type(seed) is not int or seed in seeds or not protocol["seedRanges"]["final"][0] <= seed <= protocol["seedRanges"]["final"][1]:
                raise ValueError("Duplicate or non-final game seed")
            if team not in (0, 1) or type(game["complete"]) is not bool:
                raise ValueError("Invalid game ownership or completion")
            validate_player_identities(game, swapped, protocol)
            if game["complete"]:
                if game["winner"] not in (0, 1):
                    raise ValueError("Complete game has no winner")
                score = game["score"]
                if len(score) != 2 or any(type(s) is not int or s < 0 for s in score):
                    raise ValueError("Invalid game score")
                if score[game["winner"]] < 11 or score[game["winner"]] - score[1 - game["winner"]] < 2:
                    raise ValueError("Winner does not have a complete game score")
            else:
                incomplete += 1
                if game["winner"] != -1:
                    raise ValueError("Incomplete game cannot have a winner")
            seeds.add(seed); owners[seed] = team
            counts[mode] += 1; groups[(mode, team, swapped)] += 1
            wins[mode] += int(game["complete"] and game["winner"] == team)
        per_game_rallies = Counter()
        for rally in report["rallies"]:
            seed = rally["gameSeed"]
            if seed not in owners or rally["candidateTeam"] != owners[seed] or rally["winner"] not in (-1, 0, 1):
                raise ValueError("Rally is not owned by a reported game")
            legal = rally["legalHits"]
            if len(legal) != 4 or any(type(n) is not int or n < 0 for n in legal):
                raise ValueError("Invalid non-serve hit counts")
            for player in range(owners[seed] * 2, owners[seed] * 2 + 2):
                hits[player] += legal[player]
            per_game_rallies[seed] += 1; rally_count += 1
            truncated += int(rally["winner"] == -1)
        for game in report["games"]:
            if per_game_rallies[game["gameSeed"]] != game["rallies"]:
                raise ValueError("Missing game rallies")
    if len(seeds) != protocol["baselineGames"] or not rally_count:
        raise ValueError("Incomplete final schedule")
    for mode in protocol["baselineModes"]:
        if counts[mode] != protocol["gamesPerBaselineMode"]:
            raise ValueError("Unequal baseline-mode counts")
        for team in (0, 1):
            for swapped in (False, True):
                if groups[(mode, team, swapped)] != protocol["gamesPerModePerCourtEnd"] // 2:
                    raise ValueError("Unequal court-end or partner-swap counts")
    lower = wilson_lower(sum(wins.values()), len(seeds), protocol["wilsonZ"])
    rates = {mode: wins[mode] / counts[mode] for mode in protocol["baselineModes"]}
    checks = dict(pooledWinLowerBound=lower > protocol["pooledGameWinWilsonLowerBoundMustExceed"],
                  eachModeWinRate=all(rate >= protocol["minimumWinRatePerBaselineMode"] for rate in rates.values()),
                  allSeatsReturn=all(n >= protocol["minimumLegalNonServeHitsPerSeat"] for n in hits),
                  truncation=truncated / rally_count <= protocol["maximumTruncatedRallyFraction"])
    return dict(baselineChecksPassed=all(checks.values()), checks=checks, games=len(seeds), gameWins=sum(wins.values()),
                winRateByMode=rates, pooledWilsonLowerBound=lower, legalNonServeHitsBySeat=hits,
                rallies=rally_count, truncatedRallies=truncated, incompleteGames=incomplete,
                seedList=sorted(seeds), limit="Baseline gates only. This is not full project acceptance.")
