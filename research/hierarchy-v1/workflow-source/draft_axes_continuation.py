"""Workspace-only derivation of the axes drafts from the reviewed2m drafts."""
from pathlib import Path

here = Path(__file__).resolve().parent


def once(text, before, after):
    if text.count(before) != 1:
        raise RuntimeError(f"Expected one adaptation anchor: {before[:120]}")
    return text.replace(before, after)


run = (here / "run_execution_2m.py").read_text()
run = run.replace('RUN = "execution-smooth-2m-01"', 'RUN = "execution-axes-recovery-01"')
run = run.replace('BASE = "artifacts/hierarchy-v1/smooth-2m-01"', 'BASE = "artifacts/hierarchy-v1/axes-recovery-01"')
run = run.replace('SOURCE_BASE = "artifacts/hierarchy-v1/smooth-distance-01"', 'SOURCE_BASE = BASE')
run = run.replace('SOURCE = "5f8c', 'PARENT_SOURCE = "5f8c')
run = run.replace('CONFIG = "config/mlagents/execution-v1-smooth-2m.yaml"', 'CONFIG = "config/mlagents/execution-v1-axes-recovery.yaml"')
run = run.replace('"frozen_after_wide_review"', '"frozen_axes_recovery_after_wide_review"')
source_read = '    source, build = read(root / SOURCE_BASE / "source-records.json"), read(root / SOURCE_BASE / "build-verification.json")\n'
run = once(run, source_read, '')
run = once(run, '    plan = read(plan_path)\n', '    plan = read(plan_path)\n'+source_read+
'''    SOURCE = source["sourceIdentity"]
    require(SOURCE != PARENT_SOURCE and source["parentSourceIdentity"] == PARENT_SOURCE,
            "Axes training requires the verified newly patched source")
    require(build["buildIdentity"] != read(root / "artifacts/hierarchy-v1/smooth-distance-01/build-verification.json")["buildIdentity"],
            "Axes training cannot reuse the old worker build")
''')
run = once(run, '        manifest.update(evidenceRoot=str(audit), basePort=BASE_PORT)\n',
'''        require(manifest["sourceIdentity"] == PARENT_SOURCE, "Parent manifest source differs")
        manifest.update(evidenceRoot=str(audit), basePort=BASE_PORT, sourceIdentity=SOURCE,
                        buildIdentity=build["buildIdentity"], movementPattern="axes", movementRange=.0625)
        require(manifest == plan["trainingManifest"], "Training recipe differs from frozen axes plan")
''')
run = once(run, '        require(manifest["sourceIdentity"] == SOURCE and manifest["buildIdentity"] == build["buildIdentity"]\n',
'''        require(manifest["sourceIdentity"] == PARENT_SOURCE
''')
run = run.replace('unchanged smooth recipe, restarted RNG', 'graded axes focus6.25-25cm with retained familiar/prior mix and unchanged smooth reward, restarted RNG')
run = once(run, '            require(worker_report["nextSeedIndex"] < SEEDS_PER_WORKER,\n',
'''            require(worker_report["movementPattern"] == "axes" and worker_report["movementRange"] == .0625
                    and abs(worker_report["movementRehearsalRange"]-.1) < 1e-7 and worker_report["movementRecoveryMix"]
                    and worker_report["interleavedRecovery"] and worker_report["movementTiming"] == 0
                    and worker_report["movementStartVariation"] == 0 and worker_report["movementPositionReward"] == 0,
                    "Worker axes/rehearsal/interleaving contract differs")
            episodes = helper.rows(audit / f"worker-{worker:02}" / "episodes.jsonl")
            focus = [row for row in episodes if row["movementPattern"] == "axes"]
            require(focus and all(0 < row["movementRange"] <= .0625 and row["movementRegion"] in (1,3,5,7) for row in focus),
                    "Actual graded axes focus resets missing or malformed")
            require(all(row["movementPattern"] in ("court", "axes") for row in episodes), "Unexpected focus pattern in axes training")
            workers[worker]["focusEpisodes"] = len(focus)
            workers[worker]["focusLegalReturns"] = sum(row["outcome"] == "legal_return" for row in focus)
            require(worker_report["nextSeedIndex"] < SEEDS_PER_WORKER,
''')
with (here / "run_axes_recovery.py").open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(run)

prep = (here / "prepare_execution_2m.py").read_text()
prep = prep.replace('import run_execution_2m as campaign', 'import run_axes_recovery as campaign')
prep = prep.replace('campaign.SOURCE', 'campaign.PARENT_SOURCE')
# Source records for the new worker live in the axes campaign, not its parent.
prep = prep.replace('campaign.PARENT_SOURCE_BASE', 'campaign.SOURCE_BASE')
prep = prep.replace('ExecutionV1Smooth2mFinal01', 'ExecutionV1AxesRecoveryFinal01')
prep = prep.replace('; wide physical recipe is assessed but is not added to this training distribution',
                    '; training adds graded axes only through25cm, while50-100cm remain wider transfer probes')
prep = once(prep, '    campaign.require(not base.exists() and not config.exists() and not (root / "artifacts/mlagents" / campaign.RUN).exists(),\n',
'''    campaign.require(base.is_dir() and not (base / "plan.json").exists() and not (base / "training").exists()
                     and not config.exists() and not (root / "artifacts/mlagents" / campaign.RUN).exists(),
''')
prep = once(prep, '    campaign.require(source["sourceIdentity"] == build["sourceIdentity"] == campaign.PARENT_SOURCE, "Source/build mismatch")\n',
'''    campaign.require(source["sourceIdentity"] == build["sourceIdentity"] and source["sourceIdentity"] != campaign.PARENT_SOURCE
                     and source["parentSourceIdentity"] == campaign.PARENT_SOURCE, "A newly verified axes source/build is required")
    campaign.require(build["buildIdentity"] != campaign.read(root / "artifacts/hierarchy-v1/smooth-distance-01/build-verification.json")["buildIdentity"],
                     "Old build identity cannot be reused")
    helper = campaign.load_helper(root)
    helper.verify_hashes(root, source["files"])
    helper.verify_hashes(Path(build["directory"]), build["files"])
''')
prep = once(prep, '    runner = Path(campaign.__file__).resolve()\n',
'''    parent_manifest = campaign.read(parent / "manifest.json")
    campaign.require(parent_manifest["sourceIdentity"] == campaign.PARENT_SOURCE and parent_manifest["movementPattern"] == "lateral"
                     and parent_manifest["movementRange"] == .025 and parent_manifest["movementRehearsalRange"] == .1
                     and parent_manifest["movementRecoveryMix"] and parent_manifest["interleavedRecovery"], "Parent physical recipe differs")
    training_manifest = copy.deepcopy(parent_manifest)
    training_manifest.update(evidenceRoot=str(base / "training"), basePort=campaign.BASE_PORT,
                             sourceIdentity=source["sourceIdentity"], buildIdentity=build["buildIdentity"],
                             movementPattern="axes", movementRange=.0625)
    runner = Path(campaign.__file__).resolve()
''')
prep = prep.replace('"frozen_after_wide_review", "version": "execution-smooth-2m-01"',
                    '"frozen_axes_recovery_after_wide_review", "version": "execution-axes-recovery-01"')
prep = once(prep, '"hypothesis": "One further fixed training budget tests whether the observed partial target response improves while familiar and wider returns are retained. This unchanged recipe does not teach new wide reset coverage directly.",',
'''"hypothesis": "Adding6.25-25cm axes focus to the retained interleaved25/25/50mixture improves directional returns while preserving familiar skills and target response. Larger50-100cm shifts remain transfer probes.",''')
prep = once(prep, '"parentRun": campaign.PARENT_RUN, "runId": campaign.RUN, "sourceIdentity": campaign.PARENT_SOURCE,',
'''"parentRun": campaign.PARENT_RUN, "runId": campaign.RUN, "sourceIdentity": source["sourceIdentity"],
        "parentSourceIdentity": campaign.PARENT_SOURCE,''')
prep = once(prep, '"parentManifest": campaign.read(parent / "manifest.json"), "runnerHash": campaign.sha(runner),',
'''"parentManifest": parent_manifest, "trainingManifest": training_manifest,
        "curriculumChange": {"groupFractions": {"familiar": .25, "prior": .25, "focus": .5}, "interleaved": True,
                             "focusPattern": "axes", "maximumFocusRange": .0625, "focusNominalShiftCm": [6.25,12.5,18.75,25],
                             "priorRange": .1, "bodyPpoObservationGoalRewardChanges": False},
        "runnerHash": campaign.sha(runner),''')
prep = once(prep, '"evaluation": {"baselineInputs": inputs, "batteries": batteries, "evaluateMidpoint": args.evaluate_midpoint,',
'''"evaluation": {"baselineInputs": inputs, "batteries": batteries, "evaluateMidpoint": args.evaluate_midpoint,
                       "baselineSourceIdentity": campaign.PARENT_SOURCE,
                       "candidateSourceIdentity": source["sourceIdentity"],
                       "baselineReuse": "Original5f evidence retains original identity. Applied change is opt-in focus scheduling only; golden default-reset and integration checks protect narrowlateral parity, and standalonewide disables recovery. Physics/body/rules/policy code are unchanged.",''')
prep = once(prep, '    base.mkdir()\n', '    # Base already contains the freshly verified source/build evidence.\n')
prep = prep.replace('DRAFT: freeze one unchanged-recipe continuation', 'DRAFT: freeze one graded-axes continuation')
prep = prep.replace('Campaign owner chose unchanged continuation', 'Campaign owner chose graded-axes continuation')
with (here / "prepare_axes_recovery.py").open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(prep)
print("Prepared workspace drafts only; no build, source edits, F writes, or training.")
