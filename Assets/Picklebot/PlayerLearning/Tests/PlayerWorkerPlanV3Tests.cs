using System;
using System.Linq;
using NUnit.Framework;
using Unity.InferenceEngine;
using Unity.MLAgents;
using UnityEngine;

namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerWorkerPlanV3Tests
    {
        private static PlayerWorkerManifestV3 Manifest()=>new PlayerWorkerManifestV3{
            version=PlayerWorkerPlanV3.Version,mode="evaluation",task="lateral-practice-return",
            sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),
            evidenceRoot="F:/dev/picklebot/artifacts/player-v3/worker-plan-fixture",
            basePort=5005,workerCount=4,firstSeed=1101141,seedsPerWorker=32,arenasPerWorker=2,ticksPerFrame=48,
            maximumReturnDifficulty=.5f,feedLowering=.2f,feedLateralOffset=-.2f,alignedDecisions=true,recordDecisions=true};
        [Test] public void WorkersHaveDistinctPathsAndCompleteNonOverlappingSeatAndPlacementCycles()
        {
            var m=Manifest();var plans=Enumerable.Range(0,4).Select(i=>PlayerWorkerPlanV3.Create(m,i)).ToArray();
            Assert.AreEqual(4,plans.Select(p=>p.EvidenceDirectory).Distinct().Count());
            var seeds=plans.SelectMany(p=>Enumerable.Range(p.FirstSeed,p.SeedCount)).ToArray();
            CollectionAssert.AreEqual(Enumerable.Range(1101141,128).ToArray(),seeds);
            foreach(var p in plans)
            for(int local=0;local<32;local++)
            {
                int global=p.FirstSeed-m.firstSeed+local;
                Assert.AreEqual(global%4,local%4);Assert.AreEqual(global/8%4,local/8%4);
                Assert.AreEqual(global/4%2,local/4%2);
            }
        }
        [Test] public void RejectsWholeAllocationCrossingSeedSplitsInvalidCyclesAndInvalidParameters()
        {
            var m=Manifest();m.firstSeed=1199900;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.mode="training";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m.firstSeed=1000000;Assert.IsTrue(PlayerWorkerPlanV3.Create(m,3).RequireTrainer);
            m.seedsPerWorker=31;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.task="mixed-height-return";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m.seedsPerWorker=40;Assert.AreEqual(40,PlayerWorkerPlanV3.Create(m,0).SeedCount);
            m=Manifest();m.feedLowering=.85f;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.feedLateralOffset=float.NaN;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.evidenceRoot="relative";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.workerCount=int.MaxValue;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.seedsPerWorker=int.MaxValue-31;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,4));
        }
        [Test] public void FrameworkPortSelectsTrainingWorkerAndEvaluationCannotConnect()
        {
            var m=Manifest();m.mode="training";m.firstSeed=1000000;
            Assert.AreEqual(2,PlayerWorkerPlanV3.WorkerFromArguments(m,new[]{"--mlagents-port","5007"}));
            Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.WorkerFromArguments(m,new[]{"--mlagents-port","5007","--picklebot-worker-index","2"}));
            Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.WorkerFromArguments(m,new[]{"--mlagents-port","5007","--mlagents-port","5008"}));
            Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.WorkerFromArguments(m,new[]{"--mlagents-port"}));
            m.mode="evaluation";
            Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.WorkerFromArguments(m,new[]{"--mlagents-port","5007"}));
            Assert.AreEqual(3,PlayerWorkerPlanV3.WorkerFromArguments(m,new[]{"--picklebot-worker-index","3"}));
        }
        [Test] public void FocusedWorkerAllocationPreservesCompleteWeightedCycles()
        {
            var m=Manifest();m.task="focused-lateral-return";m.arenasPerWorker=8;
            Assert.AreEqual(32,PlayerWorkerPlanV3.CycleLength(m.task));
            for(int i=0;i<4;i++)Assert.AreEqual(m.firstSeed+i*32,PlayerWorkerPlanV3.Create(m,i).FirstSeed);
            m.seedsPerWorker=48;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m.seedsPerWorker=32;m.feedLowering=.81f;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
        }
        [Test] public void ServePracticeWorkersRetainWholeSeatAndTaskCycles()
        {
            var m=Manifest();m.task="serve-practice-return";m.arenasPerWorker=8;
            Assert.AreEqual(32,PlayerWorkerPlanV3.CycleLength(m.task));
            for(int i=0;i<4;i++)Assert.AreEqual(m.firstSeed+i*32,PlayerWorkerPlanV3.Create(m,i).FirstSeed);
            m.seedsPerWorker=48;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m.seedsPerWorker=32;m.feedLowering=.81f;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
        }
        [Test] public void HeadlessHoldResetIsBoundedAndConfiguredBeforeAgents()
        {
            var m=Manifest();m.task="drop-contact";m.initialHoldLift=90;
            var root=new GameObject("hold reset worker configuration");root.SetActive(false);
            var model=ScriptableObject.CreateInstance<ModelAsset>();
            try
            {
                var run=root.AddComponent<PlayerMlDrillsV3>();PlayerWorkerPlanV3.Create(m,0).Configure(run,model);
                Assert.AreEqual(90,run.InitialHoldLift);Assert.IsNull(run.Report);Assert.AreEqual(0,run.ActiveArenas.Count);
                foreach(float value in new[]{-1f,141f,float.NaN,float.PositiveInfinity})
                {m.initialHoldLift=value;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));}
                m.initialHoldLift=90;m.task="low-return";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
                m.initialHoldLift=0;PlayerWorkerPlanV3.Create(m,0).Configure(run,model);Assert.AreEqual(0,run.InitialHoldLift);
            }
            finally{UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(model);}
        }
        [Test] public void ConfigurationPrecedesAgentsAndCannotEnableHeuristicFallback()
        {
            var root=new GameObject("inactive worker configuration fixture");root.SetActive(false);
            var model=ScriptableObject.CreateInstance<ModelAsset>();
            bool academyBefore=Academy.IsInitialized;
            try
            {
                var run=root.AddComponent<PlayerMlDrillsV3>();var m=Manifest();var plan=PlayerWorkerPlanV3.Create(m,2);
                Assert.Throws<ArgumentException>(()=>plan.Configure(run,null));
                plan.Configure(run,model);
                Assert.AreEqual(1101205,run.FirstSeed);Assert.AreEqual(32,run.SeedCount);Assert.AreEqual(2,run.ArenaCount);
                Assert.AreEqual("lateral-practice-return",run.Task);Assert.AreEqual(.2f,run.FeedLowering);Assert.AreEqual(-.2f,run.FeedLateralOffset);
                Assert.AreEqual(plan.EvidenceDirectory,run.EvidenceDirectory);Assert.IsFalse(run.RequireTrainer);
                Assert.AreSame(model,run.InferenceModel);Assert.IsNull(run.Report);Assert.AreEqual(0,run.ActiveArenas.Count);
                Assert.AreEqual(academyBefore,Academy.IsInitialized);
                m.mode="training";m.firstSeed=1000000;PlayerWorkerPlanV3.Create(m,0).Configure(run,model);
                Assert.IsTrue(run.RequireTrainer);Assert.IsNull(run.InferenceModel);
            }
            finally{UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(model);}
        }
    }
}
