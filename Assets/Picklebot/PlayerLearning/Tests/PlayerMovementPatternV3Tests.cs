using System;
using System.Linq;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerMovementPatternV3Tests
 {
  [Test] public void DefaultCourtPatternPreservesOriginalDynamicsAndObservations()
  {
   for(int seat=0;seat<4;seat++)foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"})
   using(var a=new PlayerContactDrillV3(1302000,seat,task,0,movementRange:.1f))
   using(var b=new PlayerContactDrillV3(1302000,seat,task,0,movementRange:.1f,movementPattern:"court"))
    for(int t=0;t<160&&!a.Match.World.Rules.Dead;t++) {
     CollectionAssert.AreEqual(PlayerObservationV3.Capture(a.Match,seat,t).ToArray(),PlayerObservationV3.Capture(b.Match,seat,t).ToArray());
     Assert.IsTrue(a.Match.Step(new PlayerActionV3[4]));Assert.IsTrue(b.Match.Step(new PlayerActionV3[4]));
    }
  }
  [Test] public void LocalPatternsShiftOnlyPlacementAndCoverBothDirections()
  {
   foreach(string pattern in new[]{"lateral","depth","axes","local"}) {
    var regions=new HashSet<int>();
    for(int seat=0;seat<4;seat++)foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"})
    foreach(int seed in Enumerable.Range(1302000,64).GroupBy(s=>PlayerMovementPatternV3.Region(pattern,s,new System.Random(unchecked(s^0x6d41b23)).Next(9))).Select(g=>g.First()))
    using(var zero=new PlayerContactDrillV3(seed,seat,task,0,movementRange:0))
    using(var moved=new PlayerContactDrillV3(seed,seat,task,0,movementRange:.1f,movementPattern:pattern)) {
     regions.Add(moved.Match.MovementRegion);float sign=seat<2?1:-1;
     var offset=moved.Match.MovementNominalPoint-zero.Match.MovementNominalPoint;
     Assert.AreEqual(0,offset.y,1e-6);Assert.AreEqual(0,Vector3.Distance(zero.Match.World.Ball.linearVelocity,moved.Match.World.Ball.linearVelocity),1e-6);
     Assert.Less(Vector3.Distance(offset,moved.Match.World.Ball.position-zero.Match.World.Ball.position),1e-5);
     Assert.LessOrEqual(Mathf.Abs(offset.x),.40001f);Assert.LessOrEqual(Mathf.Abs(offset.z),.40001f);
     if(pattern=="lateral"){Assert.AreEqual(0,offset.z,1e-6);Assert.AreEqual(.4f,Mathf.Abs(offset.x),1e-5);}
     if(pattern=="depth"){Assert.AreEqual(0,offset.x,1e-6);Assert.AreEqual(.4f,Mathf.Abs(offset.z),1e-5);}
     if(pattern=="axes")Assert.IsTrue(Mathf.Abs(offset.x)<1e-5||Mathf.Abs(offset.z)<1e-5);
     Assert.IsFalse(moved.Match.World.Ball.isKinematic||moved.Match.BallHeld||moved.Match.StationarySupportActive);
     Assert.AreEqual(0,moved.MovementPositionRewardScale);
    }
    CollectionAssert.AreEquivalent(pattern=="lateral"?new[]{3,5}:pattern=="depth"?new[]{1,7}:pattern=="axes"?new[]{1,3,5,7}:Enumerable.Range(0,9).ToArray(),regions);
   }
  }
  [Test] public void PatternCannotLeakIntoOtherTasksOrExceedTheLocalExtent()
  {
   Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1302000,0,"stationary-serve",movementPattern:"lateral"));
   Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1302000,0,"rally-air-feed",0,cooperative:true,movementRange:.1f,movementPattern:"axes"));
   Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1302000,0,"rally-air-feed",0,movementRange:.26f,movementPattern:"lateral"));
   Assert.Throws<ArgumentException>(()=>PlayerMovementPatternV3.Validate("unknown",.1f,true));
   Assert.Throws<ArgumentException>(()=>PlayerMovementPatternV3.Validate("lateral",float.NaN,true));
  }
  [Test] public void WorkerAndEpisodeRoutingPreserveTheMaintenanceHalf()
  {
   var root=new GameObject("Local movement schedule");root.SetActive(false);var model=ScriptableObject.CreateInstance<Unity.InferenceEngine.ModelAsset>();
   try {
    var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="evaluation",task="movement-maintenance",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/local-pattern-fixture",basePort=5400,workerCount=1,firstSeed=1104000,seedsPerWorker=64,arenasPerWorker=4,ticksPerFrame=48,fixedServeSides="both",movementRange=.1f,movementPattern="lateral"};
    var run=root.AddComponent<PlayerMlDrillsV3>();PlayerWorkerPlanV3.Create(m,0).Configure(run,model);run.FirstSeed=1302000;
    Assert.AreEqual("lateral",run.MovementPattern);
    for(int i=0;i<64;i++)using(var d=run.CreateDrillForEpisode(i,out _)) {
     Assert.AreEqual(i<32?"court":"lateral",d.MovementPattern);Assert.AreEqual(0,d.MovementPositionRewardScale);
     if(i>=32)Assert.AreEqual(.025f*(1+i/4%4),d.MovementRange,1e-6);
    }
    m.task="paired-movement-maintenance";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
   }finally{UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(model);}
  }
  [Test] public void LocalMovementLifecycleRetainsPrivateDecisionsAndRewardDefaults()
  {
   var root=new GameObject("Local movement lifecycle");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="movement-maintenance";run.FixedServeSides="both";run.RequireTrainer=false;run.AutoRun=false;run.FirstSeed=1302000;run.SeedCount=64;run.ArenaCount=4;run.MovementRange=.1f;run.MovementPattern="axes";
    root.SetActive(true);run.InitializeRun();
    for(int t=0;t<35000&&run.Report.status=="running";t++)run.StepOneTick();
    Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(64,run.Episodes.Count);
    foreach(var e in run.Episodes){Assert.AreEqual((e.seed-run.FirstSeed)/4%16<8?"court":"axes",e.movementPattern);Assert.AreEqual(0,e.movementPositionReward);for(int p=0;p<4;p++)Assert.AreEqual(p==e.player,e.decisionsByPlayer[p]>0);}
   }finally{UnityEngine.Object.DestroyImmediate(root);if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();}
  }
 }
}
