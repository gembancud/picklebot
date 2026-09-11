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
 public sealed class PlayerServeContextV3Tests
 {
  [UnityTest]
  public IEnumerator FullCycleHasBothServesAndPrivateReturnContexts()
  {
   var root=new GameObject("Combined serve and return fixture");root.SetActive(false);
   var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;
   // Reused interactive fixture seeds; these are not independent evaluation data.
   run.FirstSeed=1306630;run.SeedCount=256;run.ArenaCount=8;run.AlignDrillDecisions=true;
   run.Task="serve-context-return";run.FixedServeSides="both";run.StationaryFlightDifficulty=1;run.MaximumReturnDifficulty=.5f;
   var seen=new HashSet<int>();var contexts=new HashSet<string>();root.SetActive(true);run.InitializeRun();
   try{
    foreach(var arena in run.ActiveArenas){var captured=arena;foreach(var agent in arena.Agents)agent.Received+=(current,actions)=>{
     var d=captured.Drill;Assert.AreEqual(d.Player,current.Seat);Assert.AreEqual(0,current.LastCommand.ToArray()[16]);
     if(current.ObservedTick!=0)return;Assert.IsTrue(seen.Add(d.Seed));
     if(d.Task=="stationary-flight"){
      Assert.IsTrue(contexts.Add(d.RallyServer+"/"+d.RallyServerOnRight+"/"+d.Player+"/"+d.FeedDifficulty));
      using(var reference=new PlayerLearningMatchV3(false,d.RallyServer.Value,0,d.RallyServerOnRight)){
       reference.InitializeContactDrill(d.Player,d.Seed,"stationary-flight",d.FeedDifficulty,generalizedRallyContext:true);
       CollectionAssert.AreEqual(PlayerObservationV3.Capture(reference,d.Player,0).ToArray(),current.LastObservation.ToArray());
      }
     }else{
      Assert.IsNull(d.RallyServer);
      using(var reference=new PlayerContactDrillV3(d.Seed,d.Player,d.Task,d.Task=="stationary-serve"?1:.5f,serveFromLeft:d.ServeFromLeft))
       CollectionAssert.AreEqual(PlayerObservationV3.Capture(reference.Match,d.Player,0).ToArray(),current.LastObservation.ToArray());
     }
    };}
    for(int tick=0;tick<50000&&run.Report.status!="seed_budget_complete";tick++)run.StepOneTick();
    Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(256,seen.Count);Assert.AreEqual(64,contexts.Count);
    foreach(int seat in Enumerable.Range(0,4)){
     Assert.AreEqual(16,run.Episodes.Count(e=>e.player==seat&&e.task=="stationary-serve"&&e.serveFromLeft));
     Assert.AreEqual(16,run.Episodes.Count(e=>e.player==seat&&e.task=="stationary-serve"&&!e.serveFromLeft));
     Assert.AreEqual(16,run.Episodes.Count(e=>e.player==seat&&e.task=="varied-return"));
     foreach(float distance in new[]{0f,1f})Assert.AreEqual(8,run.Episodes.Count(e=>e.player==seat&&e.task=="stationary-flight"&&e.feedDifficulty==distance));
    }
    Assert.IsFalse(run.Episodes.Any(e=>e.outcome=="exception"||e.outcome=="infeasible"));
    Assert.AreEqual(run.Report.decisions,run.Episodes.Sum(e=>e.decisions));Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));
   }finally{UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
   yield return null;
  }
  [Test]
  public void WorkersRequireCompleteCombinedCycles()
  {
   var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="serve-context-return",fixedServeSides="both",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/combined-worker-fixture",basePort=5005,workerCount=4,firstSeed=1000000,seedsPerWorker=256,arenasPerWorker=8,ticksPerFrame=48,maximumReturnDifficulty=.5f,stationaryFlightDifficulty=1};
   Assert.AreEqual(256,PlayerWorkerPlanV3.CycleLength(m.task,m.fixedServeSides));
   var plans=Enumerable.Range(0,4).Select(i=>PlayerWorkerPlanV3.Create(m,i)).ToArray();
   CollectionAssert.AreEqual(Enumerable.Range(1000000,1024),plans.SelectMany(p=>Enumerable.Range(p.FirstSeed,p.SeedCount)));
   m.seedsPerWorker=128;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
  }
 }
}
