"""Validate versioned V3 drill trajectories before any optimizer consumes them."""
import argparse
from collections import Counter
import json
from pathlib import Path
import torch
from player_v3_actor import ActorV3, OBS_VERSION, ACTION_VERSION, source_hash
from player_actor import file_hash

def validate(directory, actor_path):
    directory=Path(directory);report=json.loads((directory/'report.json').read_text())
    if report['status']!='complete' or report.get('failure'): raise ValueError('Incomplete rollout')
    if report['sourceHash']!=source_hash() or report['actorHash']!=file_hash(actor_path): raise ValueError('Rollout provenance mismatch')
    if (report['observationVersion'],report['actionVersion']) != (OBS_VERSION,ACTION_VERSION): raise ValueError('Rollout schema mismatch')
    if report['drillVersion'] not in ('player-v3-grounded-contact-drill-1','player-v3-grounded-drills-2','player-v3-grounded-drills-3','player-v3-grounded-drills-4','player-v3-grounded-drills-5'): raise ValueError('Unknown drill version')
    if report['drillVersion'] in ('player-v3-grounded-drills-2','player-v3-grounded-drills-3','player-v3-grounded-drills-4','player-v3-grounded-drills-5'):
        if report.get('task') not in ('contact','reaction-contact','reaction-return','near-return','drop-serve'): raise ValueError('Unknown drill task')
        if not all(report.get(key) for key in ('unityVersion','physicsSettingsHash','configurationHash')): raise ValueError('Missing runtime identity')
        if report['split']=='training' and (not report['sampled'] or report['stationary']): raise ValueError('Training requires sampled active actions')
    lower={'training':1000000,'development':1100000,'interactive':1300000}.get(report['split'])
    if lower is None or not lower<=report['firstSeed']<lower+100000: raise ValueError('Invalid seed split')
    episodes=report['episodes'];rows=[json.loads(line) for line in (directory/'rows.jsonl').read_text().splitlines()]
    if len(episodes)!=report['requestedEpisodes'] or len(rows)!=report['rows']: raise ValueError('Incomplete trajectory inventory')
    if any(r['episode'] not in range(len(episodes)) for r in rows): raise ValueError('Unknown episode')
    model,_=ActorV3.load(actor_path);errors={'mean':0.,'action':0.,'logProbability':0.};attempted=[]
    for index,ep in enumerate(episodes):
        if ep['seed']!=report['firstSeed']+index or not lower<=ep['seed']<lower+100000 or ep['player']!=index%4: raise ValueError('Seed/seat mismatch')
        group=[r for r in rows if r['episode']==index]
        if len(group)!=ep['rows']: raise ValueError('Episode rows mismatch')
        used=[r for r in group if r['attempted']]
        if len(used)!=ep['attemptedRows'] or (used and (sum(r['terminal'] for r in used)!=1 or not used[-1]['terminal'])): raise ValueError('Incomplete terminal trajectory')
        if report.get('task')=='drop-serve':
            if bool(ep['released'])!=(ep['releaseTick']>=0) or ep['releaseTick']>ep['physicsSteps']:raise ValueError('Invalid release record')
            if ep['outcome']=='legal_serve' and not all(ep[k] for k in ('released','dropBounced','serveAccepted','faceContact','netCrossed')):raise ValueError('Serve success missing measured prerequisites')
        if report['drillVersion']=='player-v3-grounded-drills-5' and report.get('task') in ('reaction-return','near-return','drop-serve'):
            serving=report['task']=='drop-serve'
            bonus=.25*bool(ep['serveAccepted'] if serving else ep['faceContact'])
            if serving:bonus+=.05*bool(ep['released'])+.05*bool(ep['dropBounced'])
            terminal_reward=1 if ep['outcome'] in ('legal_return','legal_serve') else -1
            # The pre-contact distance potential can change by at most 0.1.
            if abs(ep['reward']-terminal_reward-bonus)>.1001:raise ValueError('Flight-task reward violates the v5 loss/bonus contract')
        if any(r['terminal'] or r['reward']!=0 for r in group if not r['attempted']): raise ValueError('Unapplied decision received outcome credit')
        if abs(sum(r['reward'] for r in group)+ep['unattributedReward']-ep['reward'])>.0001: raise ValueError('Reward accounting mismatch')
        for k,row in enumerate(group):
            if row['seed']!=ep['seed'] or row['player']!=ep['player'] or row['observationTick']!=12*k or row['applyTick']!=12*k+6: raise ValueError('Decision clock/ownership mismatch')
            last_attempt=ep['physicsSteps'] if ep['outcome'] in ('infeasible','exception') else ep['physicsSteps']-1
            if row['attempted']!=(row['applyTick']<=last_attempt): raise ValueError('Attempted-action flag mismatch')
            sample=row['sample'];x=torch.tensor(row['observation']);raw=torch.tensor(sample['raw']);mask=torch.tensor(sample['mask'])
            if x.shape!=(124,) or raw.shape!=(18,) or mask.shape!=(18,) or not torch.isfinite(x).all() or not torch.isfinite(raw).all(): raise ValueError('Invalid tensors')
            expected=torch.ones(18,dtype=torch.bool);expected[[4,16]]=False
            if report.get('task')=='drop-serve':expected[16]=True
            if report.get('stationary',False):expected[:]=False
            if not torch.equal(mask,expected): raise ValueError('Undisclosed action mask')
            with torch.no_grad():
                errors['mean']=max(errors['mean'],float((model(x)-torch.tensor(sample['mean'])).abs().max()))
                errors['action']=max(errors['action'],float((model.actions(raw,mask)-torch.tensor(sample['action'])).abs().max()))
                errors['logProbability']=max(errors['logProbability'],abs(float(model.raw_logp(x,raw,mask))-sample['logProbability']))
        attempted.extend(used)
    if max(errors.values())>.001: raise ValueError(f'Unity/Python mismatch: {errors}')
    return report,attempted,dict(episodes=len(episodes),rows=len(rows),attemptedRows=len(attempted),pendingRows=len(rows)-len(attempted),
        outcomes=dict(Counter(ep['outcome'] for ep in episodes)),parityMaxErrors=errors,
        physicsSteps=sum(ep['physicsSteps'] for ep in episodes),elapsedSeconds=report['elapsedSeconds'],split=report['split'],
        task=report.get('task','contact'),sampled=report.get('sampled',True),stationary=report.get('stationary',False),
        faceContacts=sum(ep.get('faceContact',ep['outcome']=='face_contact') for ep in episodes),netCrossed=sum(ep.get('netCrossed',False) for ep in episodes),
        released=sum(ep.get('released',False) for ep in episodes),dropBounced=sum(ep.get('dropBounced',False) for ep in episodes),
        serveAccepted=sum(ep.get('serveAccepted',False) for ep in episodes))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('actor',type=Path)
    args=parser.parse_args();torch.set_num_threads(2)
    _,_,summary=validate(args.directory,args.actor)
    path=args.directory/'validation.json'
    if path.exists(): raise ValueError('Validation evidence already exists')
    path.write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__': main()
