using System;
using System.Linq;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using Unity.MLAgents;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;

namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerMovementFeedV3Tests
 {
  [Test] public void ZeroVariationPreservesOriginalPhysicalFeedAndObservations()
  {
   for(int seat=0;seat<4;seat++)foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"})
   using(var original=new PlayerContactDrillV3(1301200,seat,task,0))
   using(var movement=new PlayerContactDrillV3(1301200,seat,task,0,movementRange:0)) {
    for(int tick=0;tick<160&&!original.Match.World.Rules.Dead;tick++) {
     Assert.Less(Vector3.Distance(original.Match.World.Ball.position,movement.Match.World.Ball.position),1e-6);
     CollectionAssert.AreEqual(PlayerObservationV3.Capture(original.Match,seat,tick).ToArray(),PlayerObservationV3.Capture(movement.Match,seat,tick).ToArray());
     Assert.IsTrue(original.Match.Step(new PlayerActionV3[4]));Assert.IsTrue(movement.Match.Step(new PlayerActionV3[4]));
    }
   }
  }
  [Test] public void WideShortAndDeepDestinationsCoverBothCourtEndsWithoutSupport()
  {
   for(int seat=0;seat<4;seat++) {
    var regions=new HashSet<int>();
    for(int seed=1301200;seed<1301240;seed++)
    using(var d=new PlayerContactDrillV3(seed,seat,"rally-air-feed",0,movementRange:1,movementTiming:1,movementStartVariation:1)) {
     var m=d.Match;regions.Add(m.MovementRegion);
     Assert.IsFalse(m.BallHeld||m.StationarySupportActive||m.World.Ball.isKinematic);
     Assert.IsTrue(m.World.Rules.CanVolley);Assert.AreEqual(seat/2,m.World.Rules.ExpectedTeam);
     Assert.Less(Mathf.Abs(m.MovementNominalPoint.x),DoublesRules.HalfWidth);
     Assert.Less(Mathf.Abs(m.MovementNominalPoint.z),DoublesRules.HalfLength);
     Assert.AreEqual(124,PlayerObservationV3.Capture(m,seat,0).ToArray().Length);
     Assert.Throws<InvalidOperationException>(()=>{m.Step(new PlayerActionV3[4]);m.InitializeMovementRallyFeed(seat,seed,true,false,1,1,1);});
    }
    Assert.AreEqual(9,regions.Count);
   }
  }
  [Test] public void InvalidMovementParametersCannotLeakIntoOtherDrills()
  {
   Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1301200,0,"stationary-serve",0,movementRange:.5f));
   Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1301200,0,"rally-air-feed",0,movementTiming:.5f));
   Assert.Throws<ArgumentOutOfRangeException>(()=>new PlayerContactDrillV3(1301200,0,"rally-air-feed",0,movementRange:float.NaN));
   Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidateMovement("paired-maintenance",.1f,0,0));
  }
  [Test] public void MovementScheduleRetainsSkillsAndBalancesSeatsAtEachRange()
  {
   var root=new GameObject("Movement schedule");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="movement-maintenance";run.FixedServeSides="both";run.MaximumReturnDifficulty=.25f;run.MovementRange=1;
    var tasks=Enumerable.Range(0,64).Select(run.TaskForEpisode).ToArray();
    Assert.AreEqual(8,tasks.Count(x=>x=="stationary-serve"));Assert.AreEqual(8,tasks.Count(x=>x=="receive-feed"));
    Assert.AreEqual(24,tasks.Count(x=>x=="rally-air-feed"));Assert.AreEqual(24,tasks.Count(x=>x=="rally-bounce-feed"));
    for(int i=0;i<64;i++) {
     Assert.AreEqual(i>=4&&i<8,run.ServeFromLeftForEpisode(i));
     if(i>=32)Assert.AreEqual((1+i/4%4)*.25f,run.MovementRangeForEpisode(i));
    }
    Assert.AreEqual(64,PlayerWorkerPlanV3.CycleLength(run.Task,"both"));
   }finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  [Test] public void BothPartnersKeepPrivateActionsAndMovementMetricsThroughReset()
  {
   var root=new GameObject("Movement group lifecycle");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="paired-movement-maintenance";run.RequireTrainer=false;run.AutoRun=false;
    run.FirstSeed=1301240;run.SeedCount=64;run.ArenaCount=4;run.MovementRange=.15f;run.MovementTiming=.15f;
    root.SetActive(true);run.InitializeRun();
    for(int tick=0;tick<35000&&run.Report.status=="running";tick++)run.StepOneTick();
    Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(64,run.Episodes.Count);
    foreach(var e in run.Episodes) {
     for(int p=0;p<4;p++)Assert.AreEqual(p/2==e.player/2,e.decisionsByPlayer[p]>0);
     if(e.movementFeed){Assert.AreEqual(4,e.travelBeforeContact.Length);Assert.IsTrue(e.travelBeforeContact.All(v=>v>=0&&float.IsFinite(v)));}
    }
    Assert.AreEqual(48,run.Episodes.Count(e=>e.movementFeed));
   }finally{UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
  }
  [Test] public void WorkerConfigurationCarriesMovementFractionsAndRejectsPartialCycles()
  {
   var manifest=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="evaluation",task="paired-movement-maintenance",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/movement-worker-fixture",basePort=5005,workerCount=2,firstSeed=1104000,seedsPerWorker=64,arenasPerWorker=4,ticksPerFrame=48,fixedServeSides="both",movementRange=.4f,movementTiming=.3f,movementStartVariation=.2f};
   var root=new GameObject("Movement worker config");root.SetActive(false);
   var model=ScriptableObject.CreateInstance<Unity.InferenceEngine.ModelAsset>();
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();var plan=PlayerWorkerPlanV3.Create(manifest,1);plan.Configure(run,model);
    Assert.AreEqual(1104064,run.FirstSeed);Assert.IsTrue(run.CooperativePairs);Assert.AreEqual(.4f,run.MovementRange);Assert.AreEqual(.3f,run.MovementTiming);Assert.AreEqual(.2f,run.MovementStartVariation);
    Assert.IsFalse(run.RequireTrainer);Assert.AreSame(model,run.InferenceModel);
    manifest.seedsPerWorker=32;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(manifest,0));
    manifest.seedsPerWorker=64;manifest.movementRange=float.NaN;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(manifest,0));
    manifest.movementRange=.4f;manifest.task="paired-maintenance";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(manifest,0));
   }finally{UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(model);}
  }
  [Test] public void EveryFullRangeRegionHasABoundedFootworkContactOpportunity()
  {
   // Feasibility fixture only. Its nominal-point controller never runs in training
   // and does not demonstrate a learned or legally successful stroke.
   var failures=new List<string>();
   for(int seat=0;seat<4;seat++)foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"}) {
    var regions=new HashSet<int>();
    for(int seed=1301200;seed<1301260&&regions.Count<9;seed++) {
     int region;using(var probe=new PlayerContactDrillV3(seed,seat,task,0,movementRange:1,movementTiming:1,movementStartVariation:1))region=probe.Match.MovementRegion;
     if(!regions.Add(region))continue;
     using(var d=new PlayerContactDrillV3(seed,seat,task,0,movementRange:1,movementTiming:1,movementStartVariation:1)) {
      var m=d.Match;float closest=999;bool bounce=false;float bestTime=0;
      for(int tick=0;tick<900&&!m.World.Rules.Dead;tick++) {
       var paddle=m.World.Players[seat].Paddle;var face=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint;
       var delta=m.MovementNominalPoint-face;float sign=seat<2?1:-1;
       var local=new Vector2(delta.x*sign/3,delta.z*sign/(delta.z*sign>=0?3.8f:2.3f));
       local=Vector2.ClampMagnitude(local*5,1);
       var a=new float[18];a[0]=local.x;a[1]=local.y;a[5]=1;
       var actions=new PlayerActionV3[4];actions[seat]=new PlayerActionV3(a);
       Assert.IsTrue(m.Step(actions),m.Failure);
       face=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint;
       bool bounced=m.World.Rules.Events.Any(e=>e.kind=="bounce"&&e.time>0);
       float gap=Vector3.Distance(face,m.World.Ball.position);
       if(bounced==(task=="rally-bounce-feed")&&gap<closest){closest=gap;bounce=bounced;bestTime=m.World.Time;}
      }
      if(closest>=.30f||bounce!=(task=="rally-bounce-feed"))failures.Add(task+" seat="+seat+" region="+region+" closest="+closest+" bounce="+bounce+" time="+bestTime);
     }
    }
    Assert.AreEqual(9,regions.Count);
   }
   Assert.IsEmpty(failures,string.Join("\n",failures));
  }
 }
}
