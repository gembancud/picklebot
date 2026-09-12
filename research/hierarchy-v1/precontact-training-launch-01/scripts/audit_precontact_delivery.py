from pathlib import Path
import json,collections,hashlib
P=Path("F:/dev/picklebot/artifacts/hierarchy-v1/precontact-alignment-01/delivery-probe-02")
def rows(p):return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert (P/"run-complete.json").exists()
a=collections.defaultdict(list);done=[]
for r in rows(P/"received-rewards.jsonl"):
 if r["kind"]!="reward":continue
 k=(r["worker"],r["agent"]);a[k].append(r)
 if r["terminal"]:
  seq=a.pop(k);assert abs(seq[0]["reward"])<1e-7
  done.append(dict(worker=k[0],agent=k[1],decisions=len(seq)-1,reward=sum(z["reward"] for z in seq)))
e=rows(P/"worker-00/episodes.jsonl")
assert len(done)>100 and 0<=len(e)-len(done)<=16
shutdown_tail=e[len(done):]
e=e[:len(done)]
edges=[[k for k,y in enumerate(done) if x["decisions"]==y["decisions"] and abs(x["reward"]-y["reward"])<1e-5] for x in e]
matched={}
def assign(i,seen):
 for k in edges[i]:
  if k in seen:continue
  seen.add(k)
  if k not in matched or assign(matched[k],seen):matched[k]=i;return True
 return False
assert all(assign(i,set()) for i in range(len(e)))
j=list(matched);errors=[abs(e[i]["reward"]-done[k]["reward"]) for k,i in matched.items()]
shaped=[x for x in e if x["precontactAlignmentRewardEnabled"]]
assert shaped and all(x["precontactSettled"] and x["precontactTransitions"]==x["decisions"] for x in shaped)
accounting=max(abs(x["precontactDiscountedReward"]+x["precontactInitialPotential"]) for x in shaped)
assert accounting<1e-7
assert all(x["precontactShapingReward"]==0 and x["precontactTransitions"]==0 for x in e if not x["precontactAlignmentRewardEnabled"])
assert all(not x["movementForwardProgressRewardEnabled"] and x["movementPositionReward"]==0 for x in e)
unmatched=[v for k,v in enumerate(done) if k not in set(j)]
assert len(unmatched)+len(a)<=16
out=dict(status="passed_transport_multiset_audit",episodes=len(e),unityEpisodesAfterLastCollectedTerminal=[dict(seed=x["seed"],reward=x["reward"]) for x in shutdown_tail],shapedEpisodes=len(shaped),maxRewardError=float(max(errors)),maxTelescopingError=accounting,terminalSamples=len(done),unmatchedTerminalSamples=unmatched,openAgentCount=len(a),oneToOneRewardAndDecisionCountMatch=True,seedIdentityAttribution=False,limitation="Completed episode totals and transition counts match as a multiset; no claim of seed-to-agent identity or per-transition timing beyond separately verified scheduler tests. Final Unity completions after the last collected terminal and partial trajectories excluded.",inputs={f:sha(P/f) for f in ["received-rewards.jsonl","worker-00/episodes.jsonl","run-complete.json"]})
with (P/"reward-delivery-verification.json").open("x") as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
