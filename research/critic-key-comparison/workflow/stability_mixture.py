from local_movement_sequence import *

def verify_mixture(a):
 l=read(a/'launch.json');m=read(a/'manifest.json');s=source_check();workers=[];allcounts=collections.Counter()
 for i in range(l['workers']):
  d=a/f'worker-{i:02}';start=read(d/'worker-startup.json');rep=read(d/'report.json');es=rows(d/'episodes.jsonl');first=m['firstSeed']+i*m['seedsPerWorker'];counts=collections.Counter()
  assert start['sourceIdentity']==s['sourceIdentity'] and start['manifestHash']==l['manifestHash']
  assert rep['trainerConnected'] and not rep['failure'] and not rep['cooperativePairs']
  assert rep['movementPattern']=='lateral' and abs(rep['movementRehearsalRange']-.1)<1e-6 and rep['movementRecoveryMix']
  assert {e['player'] for e in es}=={0,1,2,3}
  for e in es:
   index=e['seed']-first;assert 0<=index<m['seedsPerWorker'];block=index//4%64
   group='familiar' if block<16 else 'prior' if block<32 else 'focus'
   if group=='focus':
    expected='lateral-left' if block<40 or 48<=block<60 else 'lateral-right'
    task='rally-air-feed' if block<48 else 'rally-bounce-feed'
    assert e['movementPattern']==expected and e['movementRegion']==(3 if expected=='lateral-left' else 5) and e['task']==task
   else:assert e['movementPattern']=='court'
   assert e['movementPositionReward']==0 and e['movementTiming']==0 and e['movementStartVariation']==0
   if group!='familiar':assert abs(e['movementRange']-(m['movementRehearsalRange'] if group=='prior' else m['movementRange'])*.25*(1+block%4))<1e-6
   else:assert e['movementRange']<=0
   assert e['backgroundDecisions']==0 and all((n>0)==(j==e['player']) for j,n in enumerate(e['decisionsByPlayer']))
   counts[group]+=1
  assert set(counts)=={'familiar','prior','focus'},'Wait for actual completed examples from every practice group'
  allcounts.update(counts);workers.append(dict(worker=i,episodes=len(es),mix=dict(counts),privateDecisionsVerified=True))
 return dict(workers=workers,totalCompletedMix=dict(allcounts))
