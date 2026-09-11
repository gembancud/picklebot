using System.Collections;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Picklebot.PlayerControlsIntegration;
using Unity.MLAgents;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerStationaryAgentV3Tests
    {
        [UnityTest]
        public IEnumerator VariedArenaResetsPreservePrivateObservationsAndMaskRelease()
        {
            var root=new GameObject("Stationary private-agent fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;
            run.FirstSeed=1302049;run.SeedCount=32;run.ArenaCount=8;run.AlignDrillDecisions=true;
            run.Task="stationary-practice";run.FeedLowering=.2f;run.FeedLateralOffset=-.15f;
            var seen=new HashSet<int>();root.SetActive(true);run.InitializeRun();
            try
            {
                foreach(var arena in run.ActiveArenas)
                {
                    var captured=arena;
                    foreach(var agent in arena.Agents)
                    {
                        agent.HeuristicRelease=1;
                        agent.Received+=(current,actions)=>
                        {
                            var drill=captured.Drill;
                            Assert.AreEqual(drill.Player,current.Seat);
                            Assert.AreEqual(0,current.LastCommand.ToArray()[16]);
                            if(current.ObservedTick!=0)return;
                            Assert.IsTrue(seen.Add(drill.Seed));
                            int index=drill.Seed-run.FirstSeed;
                            Assert.AreEqual("stationary-contact",drill.Task);
                            using(var reference=new PlayerContactDrillV3(drill.Seed,drill.Player,drill.Task,run.MaximumReturnDifficulty,run.FeedLoweringForEpisode(index),run.FeedLateralOffsetForEpisode(index)))
                            {
                                CollectionAssert.AreEqual(PlayerObservationV3.Capture(reference.Match,current.Seat,0).ToArray(),current.LastObservation.ToArray());
                                Assert.AreEqual(reference.Match.World.Ball.position,drill.Match.World.Ball.position);
                                Assert.IsTrue(drill.Match.StationarySupportActive);
                            }
                        };
                    }
                }
                for(int tick=0;tick<10000&&run.Report.status!="seed_budget_complete";tick++)run.StepOneTick();
                Assert.AreEqual("seed_budget_complete",run.Report.status);
                Assert.AreEqual(32,seen.Count);Assert.AreEqual(32,run.Episodes.Count);
                Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));
                Assert.AreEqual(run.Report.decisions,run.Episodes.Sum(e=>e.decisions));
                foreach(int seat in Enumerable.Range(0,4))Assert.AreEqual(8,run.Episodes.Count(e=>e.player==seat));
                foreach(var e in run.Episodes){Assert.IsFalse(new[]{"exception","infeasible"}.Contains(e.outcome));Assert.AreEqual("stationary-contact",e.task);}
            }
            finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }
        [Test]
        public void WorkersAcceptStationaryPracticeAndKeepSeedPartitionsDisjoint()
        {
            var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="stationary-practice",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/worker-plan-fixture",basePort=5005,workerCount=4,firstSeed=1000000,seedsPerWorker=32,arenasPerWorker=8,ticksPerFrame=48,maximumReturnDifficulty=.5f,feedLowering=.2f,feedLateralOffset=-.15f,alignedDecisions=true};
            var plans=Enumerable.Range(0,4).Select(i=>PlayerWorkerPlanV3.Create(m,i)).ToArray();
            CollectionAssert.AreEqual(Enumerable.Range(1000000,128).ToArray(),plans.SelectMany(p=>Enumerable.Range(p.FirstSeed,p.SeedCount)).ToArray());
            Assert.IsTrue(plans.All(p=>p.RequireTrainer));
        }
    }
}
