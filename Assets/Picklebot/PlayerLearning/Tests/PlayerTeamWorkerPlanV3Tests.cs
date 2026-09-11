using System;
using System.Linq;
using NUnit.Framework;
using Unity.InferenceEngine;
using Unity.MLAgents;
using UnityEngine;

namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerTeamWorkerPlanV3Tests
    {
        private static PlayerWorkerManifestV3 Manifest()=>new PlayerWorkerManifestV3 {
            version=PlayerWorkerPlanV3.Version,mode="training",task="fixed-team-match",
            sourceIdentity=new string('a',64),buildIdentity=new string('b',64),
            evidenceRoot="F:/dev/picklebot/artifacts/player-v3/team-worker-plan-fixture",
            basePort=5005,workerCount=4,firstSeed=1000000,seedsPerWorker=32,
            arenasPerWorker=8,ticksPerFrame=48,maximumRallies=300,maximumGameTicks=864000
        };
        [Test] public void TeamWorkersAllocateDisjointGamesAndCompleteStartingServerCycles()
        {
            var m=Manifest();var plans=Enumerable.Range(0,4).Select(i=>PlayerWorkerPlanV3.Create(m,i)).ToArray();
            CollectionAssert.AreEqual(Enumerable.Range(1000000,128),plans.SelectMany(p=>Enumerable.Range(p.FirstSeed,p.SeedCount)));
            Assert.AreEqual(4,plans.Select(p=>p.EvidenceDirectory).Distinct().Count());
            foreach(var p in plans){Assert.IsTrue(p.IsTeamMatch);Assert.IsTrue(p.RequireTrainer);Assert.AreEqual(0,(p.FirstSeed-m.firstSeed)%4);}
        }
        [Test] public void TeamManifestRejectsDrillParametersUnsupportedRecordingAndUnboundedGames()
        {
            var m=Manifest();m.feedLowering=.1f;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.feedLateralOffset=.1f;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.initialHoldLift=1;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.maximumReturnDifficulty=.5f;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.recordDecisions=true;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.maximumRallies=0;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.maximumRallies=301;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.maximumGameTicks=864001;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.maximumGameTicks=0;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.workerCount=1;m.arenasPerWorker=17;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m=Manifest();m.firstSeed=1200000;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
        }
        [Test] public void ConfigureTeamsBeforeActivationPinsLimitsAndCannotFallBackOrCreateDrills()
        {
            bool before=Academy.IsInitialized;
            var root=new GameObject("Inactive team worker fixture");root.SetActive(false);
            var model=ScriptableObject.CreateInstance<ModelAsset>();
            try
            {
                var run=root.AddComponent<PlayerMlTeamsV3>();var drill=root.AddComponent<PlayerMlDrillsV3>();
                var m=Manifest();var plan=PlayerWorkerPlanV3.Create(m,2);plan.Configure(run,model);
                Assert.IsTrue(run.RequireTrainer);Assert.IsNull(run.InferenceModel);Assert.IsTrue(run.AutoRun);
                Assert.AreEqual(1000064,run.FirstSeed);Assert.AreEqual(32,run.SeedCount);Assert.AreEqual(8,run.ArenaCount);
                Assert.AreEqual(300,run.MaximumRallies);Assert.AreEqual(864000,run.MaximumGameTicks);
                Assert.AreEqual(plan.EvidenceDirectory,run.EvidenceDirectory);Assert.AreEqual(m.sourceIdentity,run.SourceIdentity);
                Assert.Throws<InvalidOperationException>(()=>plan.Configure(drill,model));
                m.mode="evaluation";m.firstSeed=1100000;m.modelHash=new string('c',64);plan=PlayerWorkerPlanV3.Create(m,1);
                Assert.Throws<ArgumentException>(()=>plan.Configure(run,null));plan.Configure(run,model);
                Assert.IsFalse(run.RequireTrainer);Assert.AreSame(model,run.InferenceModel);Assert.AreEqual(1100032,run.FirstSeed);
                Assert.IsNull(run.Report);Assert.AreEqual(0,run.ActiveArenas.Count);Assert.AreEqual(before,Academy.IsInitialized);
            }
            finally{UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(model);}
        }
    }
}
