using System;
using System.Linq;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerMovementRehearsalV3Tests
 {
  private static PlayerMlDrillsV3 Setup(GameObject root)
  {
   root.SetActive(false);var r=root.AddComponent<PlayerMlDrillsV3>();r.Task="movement-maintenance";r.FixedServeSides="both";r.FirstSeed=1304000;r.SeedCount=128;r.ArenaCount=4;r.RequireTrainer=false;r.AutoRun=false;r.MovementPattern="lateral";r.MovementRange=.1f;r.MaximumReturnDifficulty=.25f;return r;
  }
  [Test] public void EnabledMixtureCoversEachTaskRangeAndSeatWithoutChangingRetainedResets()
  {
   var root=new GameObject("rehearsal mixture");var baseline=new GameObject("prior court schedule");
   try {
    var r=Setup(root);r.MovementRehearsalRange=.1f;r.MovementTiming=.1f;r.MovementStartVariation=.1f;r.MovementPositionReward=.15f;
    var old=Setup(baseline);old.MovementPattern="court";
    var counts=new Dictionary<string,int>();
    for(int i=0;i<128;i++) {
     bool prior=i>=96;bool focus=i>=32&&i<64;
     using(var d=r.CreateDrillForEpisode(i,out _)) {
      Assert.AreEqual(prior,r.MovementRehearsalForEpisode(i));Assert.AreEqual(focus?"lateral":"court",d.MovementPattern);
      Assert.AreEqual(focus?.1f:0,d.MovementTiming);Assert.AreEqual(focus?.1f:0,d.MovementStartVariation);Assert.AreEqual(focus?.15f:0,d.MovementPositionRewardScale);
      var key=(focus?"focus":prior?"prior":"basic")+"/"+d.Task+"/"+d.Player;counts[key]=counts.TryGetValue(key,out int n)?n+1:1;
      if(!focus)using(var expected=old.CreateDrillForEpisode(i,out _)) {
       Assert.AreEqual(expected.MovementRange,d.MovementRange);Assert.AreEqual(expected.Match.World.Ball.position,d.Match.World.Ball.position);Assert.AreEqual(expected.Match.World.Ball.linearVelocity,d.Match.World.Ball.linearVelocity);
       CollectionAssert.AreEqual(PlayerObservationV3.Capture(expected.Match,d.Player,0).ToArray(),PlayerObservationV3.Capture(d.Match,d.Player,0).ToArray());
      }
     }
    }
    Assert.AreEqual(64,counts.Where(x=>x.Key.StartsWith("basic/")).Sum(x=>x.Value));Assert.AreEqual(32,counts.Where(x=>x.Key.StartsWith("prior/")).Sum(x=>x.Value));Assert.AreEqual(32,counts.Where(x=>x.Key.StartsWith("focus/")).Sum(x=>x.Value));
    foreach(var c in counts)Assert.AreEqual(4,c.Value,c.Key);
   }finally{UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(baseline);}
  }
  [Test] public void DisabledScheduleAndIndependentRehearsalRangeRemainStable()
  {
   var root=new GameObject("disabled rehearsal");try {
    var r=Setup(root);
    for(int i=0;i<256;i++){Assert.IsFalse(r.MovementRehearsalForEpisode(i));Assert.AreEqual(i/4%16>=8?"lateral":"court",r.MovementPatternForEpisode(i));}
    r.MovementRange=.15f;r.MovementRehearsalRange=.1f;
    for(int i=32;i<64;i++)Assert.AreEqual(.15f*(1+i/4%4)*.25f,r.MovementRangeForEpisode(i),1e-6);
    for(int i=96;i<128;i++)Assert.AreEqual(.1f*(1+i/4%4)*.25f,r.MovementRangeForEpisode(i),1e-6);
   }finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  [Test] public void WorkerManifestRejectsUnsupportedOrIncompleteRehearsal()
  {
   var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="movement-maintenance",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/rehearsal-fixture",basePort=5400,workerCount=2,firstSeed=1000000,seedsPerWorker=128,arenasPerWorker=4,ticksPerFrame=48,fixedServeSides="both",movementRange=.1f,movementPattern="lateral",movementRehearsalRange=.1f};
   var root=new GameObject("worker rehearsal");try {
    root.SetActive(false);var r=root.AddComponent<PlayerMlDrillsV3>();PlayerWorkerPlanV3.Create(m,1).Configure(r,null);Assert.AreEqual(.1f,r.MovementRehearsalRange);Assert.AreEqual(1000128,r.FirstSeed);
    m.seedsPerWorker=64;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
    foreach(float bad in new[]{float.NaN,-.1f,1.1f})Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidateMovementRehearsal("movement-maintenance",bad));
    Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidateMovementRehearsal("paired-movement-maintenance",.1f));Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidateMovementRehearsal("stationary-serve",.1f));
   }finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  [Test] public void MixedLifecycleKeepsPrivateDecisionsAndUnshapedRewards()
  {
   var root=new GameObject("rehearsal lifecycle");try {
    var r=Setup(root);r.MovementRehearsalRange=.1f;root.SetActive(true);r.InitializeRun();
    for(int t=0;t<70000&&r.Report.status=="running";t++)r.StepOneTick();
    Assert.AreEqual("seed_budget_complete",r.Report.status);Assert.AreEqual(128,r.Episodes.Count);
    foreach(var e in r.Episodes){int i=e.seed-r.FirstSeed;Assert.AreEqual(i>=32&&i<64?"lateral":"court",e.movementPattern);Assert.AreEqual(0,e.movementPositionReward);for(int p=0;p<4;p++)Assert.AreEqual(p==e.player,e.decisionsByPlayer[p]>0);}
   }finally{UnityEngine.Object.DestroyImmediate(root);if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();}
  }
 }
}
