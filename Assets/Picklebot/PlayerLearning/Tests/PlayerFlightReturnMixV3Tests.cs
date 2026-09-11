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
    public sealed class PlayerFlightReturnMixV3Tests
    {
        [UnityTest]
        public IEnumerator MixedAgentsKeepPrivateObservationsAndIndependentDifficulty()
        {
            var root=new GameObject("Flight return mix fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;
            run.FirstSeed=1306502;run.SeedCount=32;run.ArenaCount=8;run.AlignDrillDecisions=true;
            run.Task="flight-return-mix";run.StationaryFlightDifficulty=.25f;run.MaximumReturnDifficulty=.5f;
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
                            var d=captured.Drill;Assert.AreEqual(d.Player,current.Seat);Assert.AreEqual(0,current.LastCommand.ToArray()[16]);
                            if(current.ObservedTick!=0)return;
                            Assert.IsTrue(seen.Add(d.Seed));int index=d.Seed-run.FirstSeed;bool flight=index/4%2==0;
                            Assert.AreEqual(flight?"stationary-flight":"varied-return",d.Task);
                            using(var reference=new PlayerContactDrillV3(d.Seed,d.Player,d.Task,flight?.25f:.5f))
                                CollectionAssert.AreEqual(PlayerObservationV3.Capture(reference.Match,current.Seat,0).ToArray(),current.LastObservation.ToArray());
                            Assert.AreEqual(flight,d.Match.StationarySupportActive);
                            if(flight){Assert.AreEqual(.25f,d.FeedDifficulty);Assert.AreEqual(3.2f+4.45f*.25f,Mathf.Abs(current.LastObservation.ToArray()[1]*8.1f),1e-5f);}
                            else Assert.That(d.FeedDifficulty,Is.InRange(0,.5f));
                        };
                    }
                }
                for(int tick=0;tick<12000&&run.Report.status!="seed_budget_complete";tick++)run.StepOneTick();
                Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(32,seen.Count);
                Assert.AreEqual(.25f,run.Report.stationaryFlightDifficulty);Assert.AreEqual(.5f,run.Report.maximumReturnDifficulty);
                foreach(int seat in Enumerable.Range(0,4))foreach(string task in new[]{"stationary-flight","varied-return"})Assert.AreEqual(4,run.Episodes.Count(e=>e.player==seat&&e.task==task));
                Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));Assert.AreEqual(run.Report.decisions,run.Episodes.Sum(e=>e.decisions));
                Assert.IsFalse(run.Episodes.Any(e=>e.outcome=="exception"||e.outcome=="infeasible"||e.serveAccepted));
            }
            finally{UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }
        [Test]
        public void WorkerConfigurationKeepsDistancesSeparateAndRejectsIgnoredSettings()
        {
            var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="flight-return-mix",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/worker-plan-fixture",basePort=5005,workerCount=4,firstSeed=1000000,seedsPerWorker=32,arenasPerWorker=8,ticksPerFrame=48,maximumReturnDifficulty=.5f,stationaryFlightDifficulty=.25f};
            var plan=PlayerWorkerPlanV3.Create(m,0);Assert.AreEqual(8,PlayerWorkerPlanV3.CycleLength(m.task));
            var root=new GameObject("Inactive worker fixture");root.SetActive(false);
            try
            {
                var run=root.AddComponent<PlayerMlDrillsV3>();plan.Configure(run,null);
                Assert.AreEqual(.25f,run.DifficultyForEpisode(0));Assert.AreEqual(.5f,run.DifficultyForEpisode(4));
                run.MaximumReturnDifficulty=.8f;Assert.AreEqual(.25f,run.DifficultyForEpisode(0));Assert.AreEqual(.8f,run.DifficultyForEpisode(4));
                run.StationaryFlightDifficulty=.75f;Assert.AreEqual(.75f,run.DifficultyForEpisode(0));Assert.AreEqual(.8f,run.DifficultyForEpisode(4));
                run.Task="stationary-flight";run.StationaryFlightDifficulty=0;Assert.AreEqual(.8f,run.DifficultyForEpisode(0));
            }
            finally{UnityEngine.Object.DestroyImmediate(root);}
            foreach(float invalid in new[]{float.NaN,float.PositiveInfinity,-.1f,1.1f}){m.stationaryFlightDifficulty=invalid;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));}
            m.stationaryFlightDifficulty=.25f;m.task="varied-return";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m.task="flight-return-mix";m.seedsPerWorker=36;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
        }
    }
}
