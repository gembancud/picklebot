using System;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerRightReturnRetentionV1Tests
 {
  [Test] public void FocusIsFixedRightAndMaintenanceIsExactlyPreserved()
  {
   var rows=Enumerable.Range(0,256).Select(i=>new{i,e=PlayerRecoveryScheduleV3.For(i,.0625f,.1f,.25f,"lateral-right")}).ToArray();
   Assert.AreEqual(64,rows.Count(x=>x.e.Group=="familiar"));Assert.AreEqual(64,rows.Count(x=>x.e.Group=="prior"));
   for(int i=0;i<128;i++)Assert.AreEqual(PlayerRecoveryScheduleV3.For(i,.0625f,.1f,.25f,"axes"),rows[i].e);
   foreach(int seat in Enumerable.Range(0,4)) {
    foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"})Assert.AreEqual(16,rows.Count(x=>x.i%4==seat&&x.e.Group=="focus"&&x.e.Task==task));
    foreach(bool left in new[]{false,true})Assert.AreEqual(2,rows.Count(x=>x.i%4==seat&&x.e.Task=="stationary-serve"&&x.e.ServeFromLeft==left));
   }
   foreach(var row in rows.Where(x=>x.e.Group=="focus")){Assert.AreEqual("lateral-right",row.e.Pattern);Assert.AreEqual(.0625f,row.e.Range);Assert.AreEqual(0,row.e.Difficulty);}
   foreach(int worker in Enumerable.Range(0,8)) {
    var order=Enumerable.Range(0,256).Select(i=>PlayerInterleavedRecoveryV3.Index(i,worker,true)).ToArray();
    CollectionAssert.AreEquivalent(Enumerable.Range(0,256),order);
    for(int start=0;start<256;start+=16){var block=order.Skip(start).Take(16).Select(i=>rows[i].e).ToArray();Assert.AreEqual(8,block.Count(x=>x.Group=="focus"));Assert.AreEqual(4,block.Count(x=>x.Group=="prior"));Assert.AreEqual(4,block.Count(x=>x.Group=="familiar"));}
   }
  }
  [Test] public void ScheduledPhysicalResetsMatchIndependentAcquisitionAndMaintenanceFixtures()
  {
   var g=new GameObject("Right retention reset parity");g.SetActive(false);
   try {
    var run=g.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;run.Task="movement-maintenance";run.FixedServeSides="both";run.MovementRecoveryMix=true;run.MovementPattern="lateral-right";run.MovementRange=.0625f;run.MovementRehearsalRange=.1f;run.MaximumReturnDifficulty=.25f;run.FirstSeed=1000000;run.SeedCount=256;
    for(int i=0;i<256;i++) {
     // Expected focus comes from the already-tested pure acquisition contract;
     // expected maintenance comes from the unchanged axes recipe.
     var old=PlayerRecoveryScheduleV3.For(i,.0625f,.1f,.25f,"axes");
     bool focus=i>=128;string task=focus?(i<192?"rally-air-feed":"rally-bounce-feed"):old.Task;
     using(var actual=run.CreateDrillForEpisode(i,out _))
     using(var expected=new PlayerContactDrillV3(run.FirstSeed+i,i%4,task,focus?0:old.Difficulty,serveFromLeft:!focus&&old.ServeFromLeft,movementRange:focus?.0625f:old.Range,movementPattern:focus?"lateral-right":old.Pattern)) {
      CollectionAssert.AreEqual(PlayerObservationV3.Capture(expected.Match,i%4,0).ToArray(),PlayerObservationV3.Capture(actual.Match,i%4,0).ToArray());
      Assert.AreEqual(expected.Reward,actual.Reward);Assert.AreEqual(expected.MovementPattern,actual.MovementPattern);Assert.AreEqual(expected.MovementRange,actual.MovementRange);
      if(focus){Assert.AreEqual(5,actual.Match.MovementRegion);Assert.IsFalse(actual.Match.BallHeld||actual.Match.StationarySupportActive||actual.Match.World.Ball.isKinematic);}
     }
    }
   } finally {UnityEngine.Object.DestroyImmediate(g);}
  }
  [Test] public void WorkerConfiguresMixedRunAndPreservesPureAcquisitionRestrictions()
  {
   var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="movement-maintenance",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/right-retention-test",basePort=5955,workerCount=8,firstSeed=1000000,seedsPerWorker=12288,arenasPerWorker=16,ticksPerFrame=48,fixedServeSides="both",movementRange=.0625f,movementPattern="lateral-right",movementRehearsalRange=.1f,movementRecoveryMix=true,interleavedRecovery=true,maximumReturnDifficulty=.25f};
   var g=new GameObject("Right retention worker configuration");g.SetActive(false);
   try {var run=g.AddComponent<PlayerMlDrillsV3>();PlayerWorkerPlanV3.Create(m,7).Configure(run,null);Assert.IsTrue(run.MovementRecoveryMix&&run.InterleavedRecovery);Assert.AreEqual("lateral-right",run.MovementPattern);Assert.IsFalse(run.PrecontactAlignmentReward||run.MovementForwardProgressReward);Assert.AreEqual("stationary-serve",run.TaskForEpisode(0));Assert.AreEqual("rally-air-feed",run.TaskForEpisode(128));
    m.seedsPerWorker=128;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));m.seedsPerWorker=12288;
    m.task=PlayerRightReturnAcquisitionV1.Task;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
   }finally{UnityEngine.Object.DestroyImmediate(g);}
  }
 }
}
