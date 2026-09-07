"""Verify and summarize isolated bounded-contact diagnostics. Never promote a fit."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path


def summarize(report):
    if (report.get("version") != "player-contact-fit-probe-v1" or report.get("status") != "complete"
            or report.get("error") is not None or report.get("split") != "diagnostic"
            or report.get("expectedCases") != 48 or len(report.get("rows", [])) != 48
            or report.get("depths") != [3.5, 4.5, 5.5, 6.5] or report.get("shots") != [4, 6, 8]):
        raise ValueError("Incomplete or changed contact fixture schedule")
    limits = dict(maxSpeed=12.01, maxAcceleration=100.1, maxReach=.6201,
                  maxAngularSpeed=12.01, movement=.0001)
    unsafe = []
    for index, row in enumerate(report["rows"]):
        fixture = index // 2
        expected = dict(index=index, fixture=fixture, player=fixture//12*2, shot=[4, 6, 8][fixture%3],
                        depth=[3.5, 4.5, 5.5, 6.5][fixture//3%4], fitted=index%2 == 0)
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError("Contact fixture identity or pairing changed")
        violations = []
        if row.get("infeasible") != 0: violations.append("infeasible")
        for key, bound in limits.items():
            value = row.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= bound:
                violations.append(key)
        if violations: unsafe.append(dict(index=index, violations=violations))
        if row["legalLanding"] and (not row["hit"] or not row["landed"]):
            raise ValueError("Landing without a legal hit or recorded floor contact")
        error = row["targetError"]
        if row["landed"]:
            if not isinstance(error, (int, float)) or not math.isfinite(error) or error < 0:
                raise ValueError("Invalid landing error")
        elif error is not None:
            raise ValueError("Missing landing must not have a target error")
    groups = []
    for fitted in (True, False):
        for shot in (4, 6, 8):
            rows = [r for r in report["rows"] if r["fitted"] == fitted and r["shot"] == shot]
            errors = [r["targetError"] for r in rows if r["legalLanding"]]
            surfaces = Counter(c["surface"] for r in rows for c in r["contacts"])
            groups.append(dict(mode="frozen fit" if fitted else "neutral", shot=shot, cases=len(rows),
                hits=sum(r["hit"] for r in rows), legalLandings=sum(r["legalLanding"] for r in rows),
                meanLegalLandingError=sum(errors)/len(errors) if errors else None,
                contactSurfaces=dict(surfaces),
                failures=[dict(index=r["index"], player=r["player"], depth=r["depth"], fault=r["fault"])
                          for r in rows if not r["legalLanding"]]))
    return dict(cases=48, motorChecksPassed=not unsafe, unsafeCases=unsafe, groups=groups,
                limitation="Paired isolated contact diagnostic, not a policy comparison or fitted model. "
                           "Physical failures are retained and cannot be used as an accepted improvement.")


def main():
    from player_actor import ROOT, file_hash, source_hash
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path); args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report["sourceHash"] != source_hash(): raise ValueError("Runtime source changed")
    for path_key, hash_key in (("collectorSnapshotPath", "collectorHash"), ("contactPath", "contactHash")):
        path = (ROOT / report[path_key]).resolve(); path.relative_to(ROOT)
        if file_hash(path) != report[hash_key]: raise ValueError("Diagnostic artifact changed")
    result = summarize(report)
    print(json.dumps(dict(reportHash=file_hash(args.report), **result), indent=2))
    if not result["motorChecksPassed"]: raise SystemExit(1)


if __name__ == "__main__": main()
