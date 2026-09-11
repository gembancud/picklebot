using System;
using System.Linq;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerRecoveryScheduleV3Tests
 {
  private static PlayerMlDrillsV3 Setup(GameObject g)
  {
   g.SetActive(false);var r=g.AddComponent<PlayerMlDrillsV3>();r.AutoRun=false;r.RequireTrainer=false;r.Task="movement-maintenance";r.FixedServeSides="both";
   r.MovementRecoveryMix=true;r.MovementRange=.025f;r.MovementRehearsalRange=.1f;r.MovementPattern="lateral";r.MaximumReturnDifficulty=.25f;r.FirstSeed=1305000;r.SeedCount=256;r.ArenaCount=4;return r;
  }
  [Test] public void MixtureBalancesEverySeatRangeAndExplicitlyOversamplesLeftBounce()
  {
   var es=Enumerable.Range(0,256).Select(i=>new{i,seat=i%4,e=PlayerRecoveryScheduleV3.For(i,.025f,.1f,.25f)}).ToArray();
   Assert.AreEqual(64,es.Count(x=>x.e.Group=="familiar"));Assert.AreEqual(64,es.Count(x=>x.e.Group=="prior"));Assert.AreEqual(128,es.Count(x=>x.e.Group=="focus"));
   foreach(int seat in Enumerable.Range(0,4)) {
    Assert.AreEqual(16,es.Count(x=>x.seat==seat&&x.e.Group=="familiar"));Assert.AreEqual(16,es.Count(x=>x.seat==seat&&x.e.Group=="prior"));
    var f=es.Where(x=>x.seat==seat&&x.e.Group=="focus").ToArray();
    Assert.AreEqual(8,f.Count(x=>x.e.Task=="rally-air-feed"&&x.e.Pattern=="lateral-left"));Assert.AreEqual(8,f.Count(x=>x.e.Task=="rally-air-feed"&&x.e.Pattern=="lateral-right"));
    Assert.AreEqual(12,f.Count(x=>x.e.Task=="rally-bounce-feed"&&x.e.Pattern=="lateral-left"));Assert.AreEqual(4,f.Count(x=>x.e.Task=="rally-bounce-feed"&&x.e.Pattern=="lateral-right"));
    foreach(float range in new[]{.00625f,.0125f,.01875f,.025f})Assert.AreEqual(8,f.Count(x=>Mathf.Abs(x.e.Range-range)<1e-6));
    Assert.AreEqual(2,es.Count(x=>x.seat==seat&&x.e.Task=="stationary-serve"&&x.e.ServeFromLeft));
   }
   for(int i=0;i<256;i++)Assert.AreEqual(PlayerRecoveryScheduleV3.For(i,.025f,.1f,.25f),PlayerRecoveryScheduleV3.For(i+256,.025f,.1f,.25f));
  }
  [Test] public void DirectedPatternsChangeOnlyFeedPlacementAndRemainCanonicallyLeftOrRight()
  {
   foreach(int seat in Enumerable.Range(0,4))foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"})foreach(string p in new[]{"lateral-left","lateral-right"})
   using(var a=new PlayerContactDrillV3(1305001,seat,task,0,movementRange:0))
   using(var b=new PlayerContactDrillV3(1305001,seat,task,0,movementRange:.025f,movementPattern:p)) {
    int region=p=="lateral-left"?3:5;Assert.AreEqual(region,b.Match.MovementRegion);
    var delta=b.Match.World.Ball.position-a.Match.World.Ball.position;Assert.AreEqual(.1f,Mathf.Abs(delta.x),1e-5);Assert.AreEqual(0,delta.z,1e-5);Assert.AreEqual(0,delta.y,1e-5);
    Assert.AreEqual((p=="lateral-left"?-1:1)*(seat<2?1:-1),Mathf.Sign(delta.x));
    Assert.AreEqual(a.Match.World.Ball.linearVelocity,b.Match.World.Ball.linearVelocity);Assert.AreEqual(a.Match.World.Players[seat].Position,b.Match.World.Players[seat].Position);
    Assert.IsFalse(b.Match.World.Ball.isKinematic||b.Match.BallHeld||b.Match.StationarySupportActive);Assert.AreEqual(0,b.MovementPositionRewardScale);
   }
  }
  [Test] public void ScheduledResetMatchesDirectDrillIncludingObservationsAndReward()
  {
   var g=new GameObject("Recovery reset parity");try {
    var r=Setup(g);
    // One instance of each reset type/direction/range, every seat.
    foreach(int i in Enumerable.Range(0,256)) {
     var spec=PlayerRecoveryScheduleV3.For(i,r.MovementRange,r.MovementRehearsalRange,r.MaximumReturnDifficulty);
     using(var actual=r.CreateDrillForEpisode(i,out _))
     using(var expected=new PlayerContactDrillV3(r.FirstSeed+i,i%4,spec.Task,spec.Difficulty,serveFromLeft:spec.ServeFromLeft,movementRange:spec.Range,movementPattern:spec.Pattern)) {
      Assert.AreEqual(spec.Task,actual.Task);Assert.AreEqual(spec.Pattern,actual.MovementPattern);Assert.AreEqual(spec.Range,actual.MovementRange);
      CollectionAssert.AreEqual(PlayerObservationV3.Capture(expected.Match,i%4,0).ToArray(),PlayerObservationV3.Capture(actual.Match,i%4,0).ToArray());Assert.AreEqual(expected.Reward,actual.Reward);
     }
    }
   }finally{UnityEngine.Object.DestroyImmediate(g);}
  }
  [Test] public void WorkerValidationRejectsIncompleteOrIncompatibleRecoveryAndKeepsOldModeOptIn()
  {
   var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="movement-maintenance",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/recovery-test",basePort=5400,workerCount=2,firstSeed=1000000,seedsPerWorker=256,arenasPerWorker=4,ticksPerFrame=48,fixedServeSides="both",movementRange=.025f,movementPattern="lateral",movementRehearsalRange=.1f,movementRecoveryMix=true};
   var g=new GameObject("Recovery manifest");try {
    g.SetActive(false);var r=g.AddComponent<PlayerMlDrillsV3>();Assert.IsFalse(r.MovementRecoveryMix);PlayerWorkerPlanV3.Create(m,1).Configure(r,null);Assert.IsTrue(r.MovementRecoveryMix);Assert.AreEqual(1000256,r.FirstSeed);
    m.seedsPerWorker=128;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));m.seedsPerWorker=256;
    m.movementRehearsalRange=0;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));m.movementRehearsalRange=.1f;
    m.movementTiming=.1f;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));m.movementTiming=0;
    m.task="paired-movement-maintenance";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
   }finally{UnityEngine.Object.DestroyImmediate(g);}
  }
  [Test] public void RecoveryLifecycleRetainsPrivateDecisionsAndUnshapedRewards()
  {
   var g=new GameObject("Recovery lifecycle");try {
    var r=Setup(g);g.SetActive(true);r.InitializeRun();
    for(int t=0;t<140000&&r.Report.status=="running";t++)r.StepOneTick();
    Assert.AreEqual("seed_budget_complete",r.Report.status);Assert.AreEqual(256,r.Episodes.Count);Assert.IsTrue(r.Report.movementRecoveryMix);
    foreach(var e in r.Episodes) {
     var spec=PlayerRecoveryScheduleV3.For(e.seed-r.FirstSeed,.025f,.1f,.25f);Assert.AreEqual(spec.Task,e.task);Assert.AreEqual(spec.Pattern,e.movementPattern);Assert.AreEqual(spec.Range,e.movementRange,1e-6);
     Assert.AreEqual(0,e.movementPositionReward);Assert.AreEqual(0,e.backgroundDecisions);for(int p=0;p<4;p++)Assert.AreEqual(p==e.player,e.decisionsByPlayer[p]>0);
    }
   }finally{UnityEngine.Object.DestroyImmediate(g);if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();}
  }
 }
}
