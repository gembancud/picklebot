"""Validate the paired, development-only older-partner experiment."""
from collections import Counter
from player_ppo import validate_motor_metrics


def partner_schedule(seed, per_seat):
    if type(seed) is not int or type(per_seat) is not int or not 1 <= per_seat <= 10 or not 1100000 <= seed < seed + 4 * per_seat < 1200000:
        raise ValueError("Invalid development partner schedule")
    return [dict(index=i, pair=i // 2, seed=seed + i // 2,
                 candidateTeam=i // (4 * per_seat), candidateSeat=(i // (2 * per_seat)) % 4,
                 mixedPartner=bool(i % 2)) for i in range(8 * per_seat)]


def audit_partner_games(report, plan, protocol):
    expected = partner_schedule(protocol["seedBase"], protocol["seedsPerCourtEndAndSeat"])
    if plan.get("schedule") != expected or len(report.get("games", [])) != len(expected):
        raise ValueError("Missing, repeated, or changed partner schedule")
    def empty_counts():
        return dict(games=0, completed=0, wins=0, candidateReturns=0, partnerReturns=0)
    groups = {mixed: empty_counts() for mixed in (False, True)}
    ends = {(team, mixed): empty_counts() for team in (0, 1) for mixed in (False, True)}
    seats = {(seat, mixed): empty_counts() for seat in range(4) for mixed in (False, True)}
    failures = []
    for game, entry in zip(report["games"], expected):
        for field in ("index", "pair", "candidateTeam", "candidateSeat", "mixedPartner"):
            if game.get(field) != entry[field]: raise ValueError("Partner assignment differs from schedule")
        if game.get("gameSeed") != entry["seed"]: raise ValueError("Paired seed changed")
        seat, team, mixed = entry["candidateSeat"], entry["candidateTeam"], entry["mixedPartner"]
        policy_hashes = [report["olderHash"] if i // 2 != team or (mixed and i != seat) else report["candidateHash"] for i in range(4)]
        if game.get("policyHashBySeat") != policy_hashes: raise ValueError("Wrong saved policy in a seat")
        counts, first = game.get("decisionCounts", []), game.get("firstDecisions", [])
        if len(counts) != 4 or len(first) != 4 or game.get("ownershipFailures") != [0] * 4:
            raise ValueError("Missing or invalid independent player evidence")
        for player, row in enumerate(first):
            if type(counts[player]) is not int or counts[player] <= 0 or not isinstance(row, dict):
                raise ValueError("Missing independent player decisions")
            tick = row.get("observationTick")
            if row.get("player") != player or row.get("observationPlayer") != player or type(tick) is not int or tick < 0 or tick % 12 or row.get("applyTick") != tick + 6:
                raise ValueError("Player observation ownership or latency changed")
        if type(game.get("complete")) is not bool: raise ValueError("Missing game completion flag")
        if game["complete"]:
            winner, score = game.get("winner"), game.get("score", [])
            if winner not in (0, 1) or len(score) != 2 or score[winner] < 11 or score[winner] - score[1-winner] < 2:
                raise ValueError("Invalid completed game score")
        elif game.get("winner") != -1:
            raise ValueError("Incomplete game has a declared winner")
        angular = game.get("angularViolations")
        if not isinstance(angular, list) or len(angular) != 4 or any(type(n) is not int or n < 0 for n in angular):
            raise ValueError("Missing angular motor measurements")
        if any(angular): failures.append(dict(index=entry["index"], reason="angular speed limit"))
        for measured_team in (0, 1):
            try: validate_motor_metrics(dict(games=[game | {"candidateTeam": measured_team}]))
            except ValueError as error: failures.append(dict(index=entry["index"], team=measured_team, reason=str(error)))
        hits = game.get("metrics", {}).get("legalHits")
        if not isinstance(hits, list) or len(hits) != 4 or any(type(n) is not int or n < 0 for n in hits):
            raise ValueError("Missing legal return measurements")
        for group in (groups[mixed], ends[team, mixed], seats[seat, mixed]):
            group["games"] += 1; group["completed"] += int(game["complete"])
            group["wins"] += int(game["complete"] and game["winner"] == team)
            group["candidateReturns"] += hits[seat]; group["partnerReturns"] += hits[seat ^ 1]
    actual = Counter(row.get("index") for row in report.get("rallies", []))
    if actual != Counter({g["index"]: g["rallies"] for g in report["games"]}):
        raise ValueError("Missing or extra rally records")
    return dict(samePolicyPartner=groups[False], olderPolicyPartner=groups[True], motorFailures=failures,
                byCourtEnd=[dict(candidateTeam=team, mixedPartner=mixed, **value) for (team, mixed), value in ends.items()],
                byPlayerSeat=[dict(candidateSeat=seat, mixedPartner=mixed, **value) for (seat, mixed), value in seats.items()],
                allGamesComplete=all(g["complete"] for g in report["games"]),
                acceptance="Paired development evidence only. This does not satisfy final model acceptance.")
