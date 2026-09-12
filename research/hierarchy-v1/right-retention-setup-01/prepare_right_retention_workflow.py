from pathlib import Path
W=Path(__file__).resolve().parent
s=(W/'build_right_acquisition.py').read_text(encoding='utf-8')
s=s.replace('right-acquisition-01','right-retention-01').replace('execution-right-acquisition-build-01','execution-right-retention-build-01')
s=s.replace('precontact-alignment-01/source-records.json','right-acquisition-01/source-records.json')
s=s.replace('("Assets/Picklebot/PlayerLearning/PlayerMlDrillsV3.cs","Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs")','("Assets/Picklebot/PlayerLearning/PlayerRecoveryScheduleV3.cs",)')
s=s.replace('right-acquisition-tests-01.xml','right-retention-tests-01.xml').replace('len(cases)==13','len(cases)==18').replace('totalPassedTestCases=13','totalPassedTestCases=18')
s=s.replace('assert sha(tests)=="ef0e488b4f975050d1d3aed701be9f879c0b7a507661408d138ac7f521c54299"','record=read(Path(__file__).resolve().parent/"right-retention-tests-01-result.json")\n assert record["originalSettingsRestored"] and record["testResultHash"]==sha(tests) and record["exitCode"]==0')
s=s.replace('Build the tested pre-contact experiment','Build the tested fixed-right retention experiment')
(W/'build_right_retention.py').write_bytes(s.encode())
s=(W/'probe_right_acquisition_baseline.py').read_text(encoding='utf-8')
s=s.replace('right-acquisition-01','right-retention-01').replace('execution-right-acquisition-baseline-01','execution-right-retention-baseline-01')
s=s.replace('Verify concentrated25cm rightward reset contract','Verify mixed maintenance plus fixed25cm rightward reset contract')
s=s.replace('task="right-return-acquisition",movementPattern="lateral-right",movementRecoveryMix=False,movementRehearsalRange=0,interleavedRecovery=False,maximumReturnDifficulty=0','task="movement-maintenance",movementPattern="lateral-right",movementRecoveryMix=True,movementRehearsalRange=.1,interleavedRecovery=True,maximumReturnDifficulty=.25')
start=s.index('        assert len(eps)==512 and all(');end=s.index('        write(audit/\'verification.json\'',start)
s=s[:start]+'''        assert len(eps)==512 and all(not e['precontactAlignmentRewardEnabled'] and not e['movementForwardProgressRewardEnabled'] for e in eps)
        focus=[e for e in eps if (e['seed']-1000000)%256>=128]
        assert len(focus)==256 and all(e['movementRegion']==5 and e['movementRange']==.0625 and e['movementPattern']=='lateral-right' for e in focus)
        for task in ['rally-air-feed','rally-bounce-feed']:
            for seat in range(4):assert sum(e['task']==task and e['player']==seat for e in focus)==32
        for seat in range(4):
            assert sum(e['task']=='receive-feed' and e['player']==seat for e in eps)==8
            for left in [False,True]:assert sum(e['task']=='stationary-serve' and e['player']==seat and e['serveFromLeft']==left for e in eps)==4
        assert sum((e['seed']-1000000)%256<64 for e in eps)==128
        assert sum(64<=(e['seed']-1000000)%256<128 for e in eps)==128
'''+s[end:]
(W/'probe_right_retention_baseline.py').write_bytes(s.encode())
print('Prepared build and frozen mixed-worker fixture wrappers')
