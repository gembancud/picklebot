from pathlib import Path
p=Path('F:/dev/picklebot/Assets/Picklebot/PlayerLearning/Tests/PlayerExecutionGoalV1Tests.cs')
s=p.read_text(); marker='        private static (string[] episodes,float[] trace) Run('
assert 'TwoRegionWorkerRecordsCanonicalLegalLandings' not in s
test='''        [UnityTest]
        public IEnumerator TwoRegionWorkerRecordsCanonicalLegalLandings()
        {
            string output=System.IO.Path.Combine(System.IO.Path.GetTempPath(),"picklebot-two-regions-"+Guid.NewGuid().ToString("N"));
            var manifest=new PlayerWorkerManifestV3 {version=PlayerWorkerPlanV3.Version,mode="evaluation",task="rally-maintenance",
                sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),evidenceRoot=output,
                basePort=5305,workerCount=1,firstSeed=1109529,seedsPerWorker=32,arenasPerWorker=4,ticksPerFrame=48,
                executionContract=PlayerExecutionGoalV1.Contract,sampleShotTargets=true,targetLayout="two-regions",targetRadius=1,
                maximumReturnDifficulty=0,fixedServeSides="both"};
            var root=new GameObject("Two-region worker integration");root.SetActive(false);
            try
            {
                var run=root.AddComponent<PlayerMlDrillsV3>();
#if UNITY_EDITOR
                var model=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx");
                Assert.IsNotNull(model);
                PlayerWorkerPlanV3.Create(manifest,0).Configure(run,model);
#endif
                run.AutoRun=false;root.SetActive(true);run.InitializeRun();
                for(int i=0;i<100000&&run.Report.status!="seed_budget_complete";i++)run.StepOneTick();
                Assert.AreEqual("seed_budget_complete",run.Report.status);
                string file=System.IO.Path.Combine(run.EvidenceDirectory,"execution-goals.jsonl");
                var records=System.IO.File.ReadAllLines(file).Select(x=>JsonUtility.FromJson<PlayerExecutionDrillsV1.Result>(x)).ToArray();
                Assert.AreEqual(32,records.Length);Assert.IsTrue(records.Any(x=>x.hasLanding));
                var observed=new HashSet<string>();
                foreach(var row in records)
                {
                    Assert.AreEqual("two-regions",row.targetLayout);Assert.AreEqual(1,row.radius);Assert.IsTrue(row.assigned);
                    var ep=run.Episodes.Single(e=>e.seed==row.seed);bool serve=PlayerContactDrillV3.IsServeTask(ep.task);
                    var target=new Vector2(row.targetX,row.targetZ);
                    Assert.IsTrue(new[]{0,1}.Any(region=>PlayerExecutionDrillsV1.RegionTarget(serve,(int)Mathf.Sign(row.targetX),region)==target));
                    observed.Add(ep.task);Assert.AreEqual(row.legalLanding,row.hasLanding);
                    if(row.hasLanding)
                    {
                        Assert.That(row.distance,Is.EqualTo(Vector2.Distance(target,new Vector2(row.landingX,row.landingZ))).Within(1e-5));
                        Assert.Greater(row.landingZ,0);Assert.LessOrEqual(Mathf.Abs(row.landingX),3.048f);
                    }
                    else Assert.AreEqual(0,row.bonus);
                }
                CollectionAssert.AreEquivalent(new[]{"stationary-serve","receive-feed","rally-air-feed","rally-bounce-feed"},observed);
            }
            finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }

'''
p.write_text(s.replace(marker,test+marker))
print('Added full two-region worker/sampler/landing integration test')
