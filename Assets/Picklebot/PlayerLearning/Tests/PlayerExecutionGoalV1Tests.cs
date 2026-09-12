using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Picklebot.PlayerControlsIntegration;
using Unity.MLAgents;
using Unity.MLAgents.Policies;
using UnityEngine;
using UnityEngine.TestTools;
using Object = UnityEngine.Object;

namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerExecutionGoalV1Tests
    {
        [Test]
        public void AppendsPrivateGoalAndPreservesEveryLegacyField()
        {
            var values=Enumerable.Range(0,124).Select(i=>i/100f).ToArray();
            var obs=new PlayerObservationV3(2,12,values);
            var goal=new PlayerExecutionGoalV1(2,6,PlayerIntentV1.Cover,new Vector2(1,-3),.5f,new Vector2(-1,4),1);
            var encoded=goal.Observe(obs);
            Assert.AreEqual(136,encoded.Length);CollectionAssert.AreEqual(values,encoded.Take(124));
            Assert.AreEqual(1,encoded[126]);Assert.AreEqual(1,encoded[128]);Assert.AreEqual(1,encoded[132]);
            Assert.AreEqual((1-values[0]*4.2f)/8.4f,encoded[129]);
            encoded[0]=99;Assert.AreEqual(values[0],obs.ToArray()[0]);
            Assert.Throws<InvalidOperationException>(()=>goal.Observe(new PlayerObservationV3(1,12,values)));
            Assert.Throws<InvalidOperationException>(()=>goal.Observe(new PlayerObservationV3(2,5,values)));
        }

        [Test]
        public void MissingTargetsAreMaskedAndTeamsShareTheSameCanonicalGoal()
        {
            var values=new float[124];values[0]=.2f;values[1]=-.5f;
            var near=new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(1,4));
            var far=new PlayerExecutionGoalV1(2,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(1,4));
            CollectionAssert.AreEqual(near.Observe(new PlayerObservationV3(0,0,values)),far.Observe(new PlayerObservationV3(2,0,values)));
            Assert.AreEqual(0,near.LandingDistance(new Vector3(1,0,4)));
            Assert.AreEqual(0,far.LandingDistance(new Vector3(-1,0,-4)));
            var neutral=new PlayerExecutionGoalV1(0,0,PlayerIntentV1.Yield).Observe(new PlayerObservationV3(0,0,values));
            Assert.IsTrue(neutral.Skip(128).All(v=>v==0));
        }

        [Test]
        public void InvalidGoalsCannotReachTheActor()
        {
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(4,0,PlayerIntentV1.PlayBall));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,-1,PlayerIntentV1.PlayBall));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,(PlayerIntentV1)99));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(float.NaN,4)));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,movementTarget:new Vector2(0,2)));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(0,-2)));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotRadius:0));
        }

        [Test]
        public void PlacementBonusCannotRewardAnIllegalHitOrMiss()
        {
            var goal=new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(1,4));
            Assert.AreEqual(0,PlayerExecutionDrillsV1.TargetBonus(goal,false,new Vector3(1,0,4),.25f));
            Assert.AreEqual(.25f,PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(1,0,4),.25f));
            Assert.AreEqual(.125f,PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(1.5f,0,4),.25f));
            Assert.AreEqual(0,PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(3,0,4),.25f));
            Assert.AreEqual(0,PlayerExecutionDrillsV1.TargetBonus(new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall),true,Vector3.zero,.25f));
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.TargetBonus(goal,true,Vector3.zero,1));
        }

        [Test]
        public void LegacyBehaviorCannotSilentlyLoadNewObservations()
        {
            var root=new GameObject("Contract fixture");root.SetActive(false);
            try
            {
                var behavior=root.AddComponent<BehaviorParameters>();
                behavior.BehaviorName=PlayerMlAgentV3.BehaviorName;behavior.BrainParameters.VectorObservationSize=124;
                var agent=root.AddComponent<PlayerMlAgentV3>();
                Assert.Throws<InvalidOperationException>(()=>agent.BindGoal(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall)));
            }
            finally{Object.DestroyImmediate(root);}
        }

        [Test]
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

        [Test]
        public void TwoRegionsRemainSeparatedInsideTheLegalCourt()
        {
            foreach(bool serve in new[]{false,true})foreach(int sign in new[]{-1,1})
            {
                var a=PlayerExecutionDrillsV1.RegionTarget(serve,sign,0);
                var b=PlayerExecutionDrillsV1.RegionTarget(serve,sign,1);
                Assert.Greater(Vector2.Distance(a,b),2f);
                foreach(var p in new[]{a,b})
                {
                    Assert.Less(Mathf.Abs(p.x)+1,3.048f);Assert.Less(p.y+1,6.7056f);
                    Assert.Greater(p.y-1,serve?2.1336f:0);
                    if(serve)Assert.Greater(p.x*sign-1,0);
                }
            }
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.ValidateLayout("wrong",true,1));
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.ValidateLayout("two-regions",false,1));
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.ValidateLayout("two-regions",true,1.5f));
        }

        [UnityTest]
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
                var episodes=run.Episodes.ToArray();Object.DestroyImmediate(root);
                var records=System.IO.File.ReadAllLines(file).Select(x=>JsonUtility.FromJson<PlayerExecutionDrillsV1.Result>(x)).ToArray();
                Assert.AreEqual(32,records.Length);Assert.IsTrue(records.Any(x=>x.hasLanding));
                var observed=new HashSet<string>();
                foreach(var row in records)
                {
                    Assert.AreEqual("two-regions",row.targetLayout);Assert.AreEqual(1,row.radius);Assert.IsTrue(row.assigned);
                    var ep=episodes.Single(e=>e.seed==row.seed);bool serve=PlayerContactDrillV3.IsServeTask(ep.task);
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

        private static (string[] episodes,float[] trace) Run(bool execution, bool learned=false)
        {
            var root=new GameObject("Execution parity fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;
            run.FirstSeed=learned?1109497:1304000;run.SeedCount=32;run.ArenaCount=4;run.Task="rally-maintenance";
            run.MaximumReturnDifficulty=0;run.AlignDrillDecisions=true;
            PlayerExecutionDrillsV1 goals=null;
            if(execution){goals=root.AddComponent<PlayerExecutionDrillsV1>();goals.SampleShotTargets=true;goals.LegalTargetReward=0;}
#if UNITY_EDITOR
            if(learned)run.InferenceModel=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>(execution?
                "Assets/Picklebot/PlayerLearning/Models/ExecutionV1Initial.onnx":"Assets/Picklebot/PlayerLearning/Models/LocalMovement_movement-bridge-01_8415374.onnx");
            if(learned)Assert.IsNotNull(run.InferenceModel);
#endif
            var trace=new List<float>();var seats=new HashSet<int>();
            try
            {
                root.SetActive(true);run.InitializeRun();
                foreach(var arena in run.ActiveArenas)foreach(var agent in arena.Agents)
                {
                    agent.Received+=(current,actions)=>
                    {
                        var input=current.LastPolicyObservation;seats.Add(current.Seat);
                        Assert.AreEqual(execution?136:124,input.Length);
                        CollectionAssert.AreEqual(current.LastObservation.ToArray(),input.Take(124));
                        if(execution){Assert.AreEqual(current.Seat,current.LastGoal.Seat);Assert.IsTrue(current.LastGoal.HasShotTarget);}
                        trace.AddRange(input.Take(124));trace.AddRange(current.LastCommand.ToArray());
                    };
                }
                for(int i=0;i<100000&&run.Report.status!="seed_budget_complete";i++)run.StepOneTick();
                Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(32,run.Episodes.Count);
                Assert.AreEqual(4,seats.Count);Assert.IsTrue(run.Episodes.All(e=>e.outcome!="exception"&&e.outcome!="infeasible"));
                if(execution){Assert.AreEqual(32,goals.Completed);Assert.AreEqual(PlayerExecutionGoalV1.Contract,run.Report.contract);}
                return (run.Episodes.Select(e=>JsonUtility.ToJson(e)).ToArray(),trace.ToArray());
            }
            finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
        }

        [UnityTest]
        public IEnumerator ExportedWarmStartRetainsLearnedDrillOutcomes()
        {
            var old=Run(false,true);var next=Run(true,true);
            CollectionAssert.AreEqual(old.episodes,next.episodes);
            Assert.AreEqual(old.trace.Length,next.trace.Length);
            for(int i=0;i<old.trace.Length;i++)Assert.That(next.trace[i],Is.EqualTo(old.trace[i]).Within(2e-5));
            yield return null;
        }

        [UnityTest]
        public IEnumerator GoalSamplingPreservesFeedsActionsAndEpisodeResetsAcrossAllSeats()
        {
            var old=Run(false);var next=Run(true);
            CollectionAssert.AreEqual(old.episodes,next.episodes);
            CollectionAssert.AreEqual(old.trace,next.trace);
            yield return null;
        }
    }
}

