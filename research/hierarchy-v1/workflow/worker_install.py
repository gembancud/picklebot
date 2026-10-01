from pathlib import Path
import shutil
root=Path('F:/dev/picklebot')
p=root/'Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs'
b=p.read_bytes()
def edit(old,new):
    global b
    a=old.replace('\n','\r\n').encode();z=new.replace('\n','\r\n').encode()
    assert b.count(a)==1,(old,b.count(a));b=b.replace(a,z)
edit('        public string backgroundModelHash;','''        public string backgroundModelHash;
        public string executionContract;
        public bool sampleShotTargets;
        public float targetRadius=1.5f, legalTargetReward=.25f;''')
edit('            if(manifest.mode!="training"&&manifest.mode!="evaluation")','''            bool execution = !string.IsNullOrEmpty(manifest.executionContract);
            if(execution && manifest.executionContract!=PlayerExecutionGoalV1.Contract)throw new ArgumentException("Unknown execution contract.");
            if(!execution && manifest.sampleShotTargets)throw new ArgumentException("Shot targets require the execution contract.");
            if(execution && (manifest.task=="fixed-team-match" || manifest.task=="paired-maintenance" || manifest.task=="paired-movement-maintenance" || manifest.optimizerDiagnostics || !string.IsNullOrEmpty(manifest.backgroundModelHash)))throw new ArgumentException("Execution v1 currently supports solo practice only.");
            if(execution && (!float.IsFinite(manifest.targetRadius)||manifest.targetRadius<=0||manifest.targetRadius>3||!float.IsFinite(manifest.legalTargetReward)||manifest.legalTargetReward<0||manifest.legalTargetReward>.25f))throw new ArgumentException("Invalid execution target parameters.");
            if(manifest.mode!="training"&&manifest.mode!="evaluation")''')
edit('            run.BackgroundModel=string.IsNullOrEmpty(Manifest.backgroundModelHash)?null:model;','''            if(!string.IsNullOrEmpty(Manifest.executionContract))
            {
                var goals=run.gameObject.AddComponent<PlayerExecutionDrillsV1>();
                goals.SampleShotTargets=Manifest.sampleShotTargets;goals.TargetRadius=Manifest.targetRadius;goals.LegalTargetReward=Manifest.legalTargetReward;
            }
            run.BackgroundModel=string.IsNullOrEmpty(Manifest.backgroundModelHash)?null:model;''')
p.write_bytes(b)
test=root/'Assets/Picklebot/PlayerLearning/Tests/PlayerExecutionGoalV1Tests.cs'
s=test.read_text()
s=s.replace('Run(bool execution)','Run(bool execution, bool learned=false)')
s=s.replace('run.FirstSeed=1304000;', 'run.FirstSeed=learned?1109497:1304000;')
s=s.replace('            var trace=new List<float>();','''#if UNITY_EDITOR
            if(learned)run.InferenceModel=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>(execution?
                "Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx":"Assets/Picklebot/PlayerLearning/Models/LocalMovement_movement-bridge-01_8415374.onnx");
            if(learned)Assert.IsNotNull(run.InferenceModel);
#endif
            var trace=new List<float>();''')
s=s.replace('        [UnityTest]\n        public IEnumerator GoalSampling', '''        [UnityTest]
        public IEnumerator ExportedWarmStartRetainsLearnedDrillOutcomes()
        {
            var old=Run(false,true);var next=Run(true,true);
            CollectionAssert.AreEqual(old.episodes,next.episodes);
            Assert.AreEqual(old.trace.Length,next.trace.Length);
            for(int i=0;i<old.trace.Length;i++)Assert.That(next.trace[i],Is.EqualTo(old.trace[i]).Within(2e-5));
            yield return null;
        }

        [UnityTest]
        public IEnumerator GoalSampling''')
test.write_text(s,encoding='utf-8')
shutil.copyfile(root/'artifacts/hierarchy-v1/execution-init-01/PicklebotExecutionV1-0.onnx',root/'Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx')
import json
ledger=root/'artifacts/player-v3/seed-ledger.json';l=json.loads(ledger.read_text())
assert not l['finalSeedsConsumed']
assert max(x['firstSeed']+x['count'] for k in ['developmentBlocks','developmentReuses'] for x in l[k])==1109497
l['developmentBlocks'].append(dict(firstSeed=1109497,count=32,run='artifacts/hierarchy-v1/learned-contract-tests',purpose='Paired old/new exported model parity on identical drill resets, before training.'))
ledger.write_text(json.dumps(l,indent=2),encoding='utf-8')
print('Worker contract and exported-model parity test configured.')
