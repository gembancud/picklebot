using System;
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
    public sealed class PlayerContextRangeV3Tests
    {
        [UnityTest]
        public IEnumerator CompleteDistanceContextCyclePreservesPrivateObservationsAndMovingReturns()
        {
            var root=new GameObject("Context mix fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;run.FirstSeed=1306630;run.SeedCount=128;run.ArenaCount=8;run.AlignDrillDecisions=true;run.Task="context-range-return";run.StationaryFlightDifficulty=.25f;run.MaximumReturnDifficulty=.5f;
            var seen=new HashSet<int>();var contexts=new HashSet<string>();root.SetActive(true);run.InitializeRun();
            try
            {
                foreach(var arena in run.ActiveArenas)
                {
                    var captured=arena;
                    foreach(var agent in arena.Agents)agent.Received+=(current,actions)=>
                    {
                        var d=captured.Drill;Assert.AreEqual(d.Player,current.Seat);Assert.AreEqual(0,current.LastCommand.ToArray()[16]);
                        if(current.ObservedTick!=0)return;Assert.IsTrue(seen.Add(d.Seed));int index=d.Seed-run.FirstSeed;bool flight=index/4%2==0;
                        Assert.AreEqual(flight?"stationary-flight":"varied-return",d.Task);
                        if(flight)
                        {
                            int server=index/16%4;bool right=index/8%2==0;float difficulty=index/64%2==0?0:.25f;Assert.AreEqual(difficulty,d.FeedDifficulty);Assert.AreEqual(server,d.RallyServer);Assert.AreEqual(right,d.RallyServerOnRight);
                            Assert.IsTrue(contexts.Add(server+"/"+right+"/"+d.Player+"/"+difficulty));
                            using(var reference=new PlayerLearningMatchV3(false,server,0,right))
                            {reference.InitializeContactDrill(d.Player,d.Seed,"stationary-flight",difficulty,generalizedRallyContext:true);CollectionAssert.AreEqual(PlayerObservationV3.Capture(reference,d.Player,0).ToArray(),current.LastObservation.ToArray());}
                        }
                        else
                        {
                            Assert.IsNull(d.RallyServer);
                            using(var reference=new PlayerContactDrillV3(d.Seed,d.Player,"varied-return",.5f))CollectionAssert.AreEqual(PlayerObservationV3.Capture(reference.Match,d.Player,0).ToArray(),current.LastObservation.ToArray());
                        }
                    };
                }
                for(int tick=0;tick<25000&&run.Report.status!="seed_budget_complete";tick++)run.StepOneTick();
                Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(128,seen.Count);Assert.AreEqual(64,contexts.Count);
                foreach(int seat in Enumerable.Range(0,4))foreach(string task in new[]{"stationary-flight","varied-return"})Assert.AreEqual(16,run.Episodes.Count(e=>e.player==seat&&e.task==task));
                foreach(var e in run.Episodes){Assert.IsFalse(e.outcome=="exception"||e.outcome=="infeasible");Assert.AreEqual(e.task=="stationary-flight",e.rallyServer>=0);var saved=JsonUtility.FromJson<MlDrillEpisodeV3>(JsonUtility.ToJson(e));Assert.AreEqual(e.rallyServer,saved.rallyServer);Assert.AreEqual(e.rallyServerOnRight,saved.rallyServerOnRight);}
                Assert.AreEqual(run.Report.decisions,run.Episodes.Sum(e=>e.decisions));Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));
            }
            finally{UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }
        [Test]
        public void WorkerAllocationsRequireWholeContextCycles()
        {
            var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="context-range-return",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/context-worker-fixture",basePort=5005,workerCount=4,firstSeed=1000000,seedsPerWorker=128,arenasPerWorker=8,ticksPerFrame=48,maximumReturnDifficulty=.5f,stationaryFlightDifficulty=.25f};
            Assert.AreEqual(128,PlayerWorkerPlanV3.CycleLength(m.task));var plans=Enumerable.Range(0,4).Select(i=>PlayerWorkerPlanV3.Create(m,i)).ToArray();CollectionAssert.AreEqual(Enumerable.Range(1000000,512),plans.SelectMany(x=>Enumerable.Range(x.FirstSeed,x.SeedCount)));
            m.seedsPerWorker=64;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1306630,0,"varied-return",rallyServer:0));
            Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1306630,0,"stationary-flight",rallyServer:4));
            Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1306630,0,"stationary-flight",rallyServerOnRight:false));
        }
    }
}


