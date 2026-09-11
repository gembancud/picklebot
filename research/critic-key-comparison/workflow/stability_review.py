def cells(es, first):
 es=[e for e in es if (e['seed']-first)//4%16>=8]
 def stat(rr):return dict(attempts=len(rr),contacts=sum(e['faceContact'] for e in rr),crossed=sum(e['netCrossed'] for e in rr),legal=sum(e['outcome']=='legal_return' for e in rr))
 return dict(sideMode={f'{r}/{mode}':stat([e for e in es if e['movementRegion']==r and e['task']==task]) for r in [3,5] for mode,task in [('air','rally-air-feed'),('bounce','rally-bounce-feed')]},
  rangeSideMode={f'{round(eRange*400,3):g}/{r}/{mode}':stat([e for e in es if e['movementRegion']==r and e['task']==task and e['movementRange']==eRange]) for eRange in sorted({e['movementRange'] for e in es}) for r in [3,5] for mode,task in [('air','rally-air-feed'),('bounce','rally-bounce-feed')]})

def judge(v, breakdown):
 rate=lambda x:x['legal']/x['attempts'] if x['attempts'] else 0
 c=v['cases'];retention={}
 for baseline in ['control-legacy','parent-legacy']:
  for mode in ['air','bounce']:retention[baseline+'/'+mode]=rate(c['candidate-legacy'][mode])>=rate(c[baseline][mode])-5/64
  retention[baseline+'/total']=rate(c['candidate-legacy']['challenge'])>=rate(c[baseline]['challenge'])-8/128
 for dist in ['legacy','focus','bridge','lateral']:
  for task,x in c['candidate-'+dist]['retained'].items():
   retention[dist+'/basic/'+task]=rate(x)>=(.7 if task=='receive-feed' else .9) and all(rate(x)>=rate(c[b]['retained'][task])-2/32 for b in ['control-legacy','parent-legacy'])
 for dist in ['bridge','lateral']:
  retention[dist+'/total']=rate(c['candidate-'+dist]['challenge'])>=rate(c['parent-'+dist]['challenge'])-.0625
  for key,x in breakdown['candidate-'+dist]['sideMode'].items():
   y=breakdown['parent-'+dist]['sideMode'][key];retention[dist+'/'+key]=x['attempts']>=8 and y['attempts']>=8 and rate(x)>=rate(y)-.0625
 signal={'focus-total-gain':rate(c['candidate-focus']['challenge'])>=rate(c['parent-focus']['challenge'])+13/256}
 for mode in ['air','bounce']:signal['focus/'+mode]=rate(c['candidate-focus'][mode])>=rate(c['parent-focus'][mode])
 ready={mode:rate(c['candidate-focus'][mode])>=.8 for mode in ['air','bounce']}
 for key,x in breakdown['candidate-focus']['sideMode'].items():
  y=breakdown['parent-focus']['sideMode'][key];signal['focus/'+key]=x['attempts']>=8 and y['attempts']>=8 and rate(x)>=rate(y)-.0625
  ready['sideMode/'+key]=x['attempts']>=8 and rate(x)>=.75 and signal['focus/'+key]
 for key,x in breakdown['candidate-focus']['rangeSideMode'].items():
  if float(key.split('/')[0])>=7.5:ready['rangeSideMode/'+key]=x['attempts']>=8 and rate(x)>=.7
 return dict(status='review_complete',retentionPassed=all(retention.values()),promising=all(retention.values()) and all(signal.values()),readyToWiden=all(retention.values()) and all(ready.values()),retention=retention,signal=signal,readiness=ready,trainingExtended=False,promoted=False,finalSeedsConsumed=False)
