from pathlib import Path
root=Path('F:/dev/picklebot')
p=root/'Assets/Picklebot/PlayerLearning/PlayerExecutionDrillsV1.cs'
s=p.read_text();a='            Completed++; if(legal)LegalLandings++; if(row.targetHit)TargetsHit++;'
assert s.count(a)==1
s=s.replace(a,a+'''
            var stats=Unity.MLAgents.Academy.Instance.StatsRecorder;
            stats.Add("PicklebotExecution/LegalLanding",legal?1:0);
            if(row.assigned)
            {
                stats.Add("PicklebotExecution/TargetHitPerAttempt",row.targetHit?1:0);
                if(legal){stats.Add("PicklebotExecution/TargetHitGivenLegal",row.targetHit?1:0);stats.Add("PicklebotExecution/LandingDistanceGivenLegal",row.distance);}
            }''')
p.write_text(s,encoding='utf-8')
p=root/'Assets/Picklebot/PlayerLearning/Tests/PlayerExecutionGoalV1Tests.cs'
s=p.read_text();anchor='        private static (string[] episodes,float[] trace) Run'
new='''        [Test]
        public void WorkerRequiresAnExplicitCompatibleGoalContract()
        {
            var m=new PlayerWorkerManifestV3 {version=PlayerWorkerPlanV3.Version,mode="training",task="rally-maintenance",
                sourceIdentity=new string('a',64),buildIdentity=new string('b',64),evidenceRoot="F:/dev/picklebot/artifacts/hierarchy-fixture",
                basePort=5205,workerCount=1,firstSeed=1000000,seedsPerWorker=32,arenasPerWorker=4,ticksPerFrame=48,sampleShotTargets=true};
            Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m.executionContract=PlayerExecutionGoalV1.Contract;
            var plan=PlayerWorkerPlanV3.Create(m,0);
            var root=new GameObject("Execution worker contract");root.SetActive(false);
            try
            {
                var run=root.AddComponent<PlayerMlDrillsV3>();plan.Configure(run,null);
                Assert.IsTrue(root.GetComponent<PlayerExecutionDrillsV1>().SampleShotTargets);
                Assert.IsNull(run.Report);
            }
            finally{Object.DestroyImmediate(root);}
            m.executionContract="wrong-version";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m.executionContract=PlayerExecutionGoalV1.Contract;m.task="paired-maintenance";
            Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m.task="rally-maintenance";m.targetRadius=float.NaN;
            Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
        }

'''
assert s.count(anchor)==1;s=s.replace(anchor,new+anchor);p.write_text(s,encoding='utf-8')
print('Added explicit worker-contract validation coverage and outcome metrics.')
