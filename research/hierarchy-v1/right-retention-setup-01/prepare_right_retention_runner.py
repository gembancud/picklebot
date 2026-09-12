from pathlib import Path
W=Path(__file__).resolve().parent
s=(W/'run_right_acquisition.py').read_text(encoding='utf-8')
s=s.replace('execution-right-acquisition-01','execution-right-retention-01').replace('hierarchy-v1/right-acquisition-01','hierarchy-v1/right-retention-01')
s=s.replace('task="right-return-acquisition",movementPattern="lateral-right",movementRange=.0625,movementRecoveryMix=False,movementRehearsalRange=0,interleavedRecovery=False,maximumReturnDifficulty=0','task="movement-maintenance",movementPattern="lateral-right",movementRange=.0625,movementRecoveryMix=True,movementRehearsalRange=.1,interleavedRecovery=True,maximumReturnDifficulty=.25')
s=s.replace('Concentrated25cm right-return acquisition from common parent1048609 to2097152; no extra reward shaping; both rallyfeeds/allseats; no final seeds; acquisition and all5 development batteries required before any promotion.','Mixed fixed25cm right acquisition plus familiar/prior maintenance from common parent1048609 to2097152;50/25/25 episode-start allocation, unchanged rewards; acquisition and all5 retention batteries required; no final seeds.')
needle='   assert row["movementPattern"]=="lateral-right" and row["movementRegion"]==5 and row["movementRange"]==.0625 and row["task"] in ("rally-air-feed","rally-bounce-feed")'
assert needle in s
s=s.replace(needle,'''   index=(row["seed"]-(1000000+worker*12288))%256;block=index//4
   if index>=128:
    assert row["movementPattern"]=="lateral-right" and row["movementRegion"]==5 and row["movementRange"]==.0625 and row["task"]==("rally-air-feed" if index<192 else "rally-bounce-feed")
   elif index>=64:
    assert row["movementPattern"]=="court" and abs(row["movementRange"]-.1*(1+block%4)*.25)<1e-7 and row["task"]==("rally-air-feed" if index<96 else "rally-bounce-feed")
   else:
    basic=block%8;expected="stationary-serve" if basic<2 else "receive-feed" if basic<4 else "rally-air-feed" if basic<6 else "rally-bounce-feed"
    assert row["task"]==expected and row["movementPattern"]=="court" and row["movementRange"]==(-1 if basic<4 else 0)
    if basic<2:assert row["serveFromLeft"]==(basic==1)
   assert not row["movementForwardProgressRewardEnabled"] and row["movementPositionReward"]==0''')
needle=' assert enabled==0'
s=s.replace(needle,needle+'''
 helper.TARGET=TARGET;helper.BUFFER=8192
 verified_step,changes=helper.audit_final_states(torch.load(checkpoint,map_location="cpu",weights_only=False),final)
 workers,goals,inputs=helper.audit_workers(A,manifest,source,build)
 assert verified_step==step and len(goals)==episodes
 write(A/"extended-verification.json",dict(step=step,stateChanges=changes,workers=workers,episodes=episodes,inputHashes=inputs,parentUnchanged=True,finalSeedsConsumed=False,promoted=False))''')
s=s.replace('Concentrated right-return acquisition','Mixed right-return acquisition and retention').replace('Right-return acquisition trainer','Right-return retention trainer')
(W/'run_right_retention.py').write_bytes(s.encode())
print('Prepared bounded mixed-training runner')
