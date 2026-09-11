using System.Linq;
using NUnit.Framework;
using UnityEngine;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;

namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerReceiveFeedV3Tests
 {
  private sealed class Still : IPlayerPolicyV3
  {
   public string Name=>"feed measurement only";
   public void Reset(){}
   public PlayerActionV3 Decide(PlayerObservationV3 o,System.Random rng)=>new PlayerActionV3(new float[PlayerActionV3.Count]);
  }
  [Test] public void FullCourtResetPreservesReceiverIdentityAndRequiresAnActualBounce()
  {
   for(int seat=0;seat<4;seat++) for(int i=0;i<4;i++)
   using(var d=new PlayerContactDrillV3(1101773+i,seat,"receive-feed",maximumReturnDifficulty:i/3f))
   {
    var rules=d.Match.World.Rules;
    Assert.AreEqual(seat,rules.DesignatedReceiver);Assert.AreEqual(RallyPhase.ServeFlight,rules.Phase);
    Assert.IsFalse(rules.Bounced);Assert.AreEqual(1,rules.Events.Count);Assert.AreEqual("serve",rules.Events[0].kind);
    Assert.IsFalse(d.Match.BallHeld);Assert.IsFalse(d.Match.StationarySupportActive);
    Assert.AreEqual(6f,Mathf.Abs(d.Match.World.Players[seat].Position.z),1e-5);
    Assert.AreEqual(3.048f,DoublesRules.HalfWidth);Assert.AreEqual(6.7056f,DoublesRules.HalfLength);
    var mask=PlayerContactDrillV3.ActionMask(seat,seat,"receive-feed");
    Assert.IsTrue(mask[0]&&mask[1]);Assert.IsFalse(mask[4]||mask[16]);
    rules.Hit(seat,.01f);Assert.AreEqual(Fault.EarlyVolley,rules.LastFault);
   }
  }
  [Test] public void FeedBouncesPhysicallyAndMissingCannotEarnApproachReward()
  {
   for(int seat=0;seat<4;seat++)
   using(var d=new PlayerContactDrillV3(1101773,seat,"receive-feed",maximumReturnDifficulty:0))
   {
    d.Match.AttachPolicies(Enumerable.Range(0,4).Select(_=>(IPlayerPolicyV3)new Still()).ToArray(),1101773);
    bool bounced=false;float total=0,apex=0,bounceTime=-1;
    for(int t=0;t<720&& !d.Done;t++)
    {
     d.Step();Assert.IsNull(d.Match.Failure);total+=d.Reward;
     if(d.IncomingServeLanded){bounced=true;if(bounceTime<0)bounceTime=d.Match.World.Time;apex=Mathf.Max(apex,d.Match.World.Ball.position.y);}
     if(!d.FaceContact&&!d.Done)Assert.AreEqual(0,d.Reward);
    }
    Assert.IsTrue(bounced,"Seat "+seat);Assert.Greater(bounceTime,.05f);
    Assert.Greater(apex,.4f);Assert.Less(apex,2.5f);
    Assert.IsTrue(d.Done);Assert.AreEqual("receive_fault",d.Outcome);Assert.LessOrEqual(total,0);
   }
  }
  [Test] public void EasyFeedReachesReadyPaddleHeightAndContactDistanceOnEverySeat()
  {
   for(int seat=0;seat<4;seat++)
   using(var d=new PlayerContactDrillV3(1101773,seat,"receive-feed",maximumReturnDifficulty:0))
   {
    var m=d.Match;var body=m.World.Players[seat];var face=body.Paddle.position+body.Paddle.rotation*PlayerStrokeAimV3.FacePoint;
    var actions=Enumerable.Range(0,4).Select(_=>new PlayerActionV3(new float[18])).ToArray();
    float gap=999,apex=0,bounceTime=-1;
    for(int tick=0;tick<720&&!m.World.Rules.Dead;tick++)
    {
     Assert.IsTrue(m.Step(actions),m.Failure);
     if(m.World.Rules.Bounced){if(bounceTime<0)bounceTime=m.World.Time;apex=Mathf.Max(apex,m.World.Ball.position.y);gap=Mathf.Min(gap,Vector3.Distance(face,m.World.Ball.position));}
    }
    Assert.Greater(bounceTime,.2f);Assert.Greater(apex,1.2f);Assert.Less(gap,.22f);
    Assert.IsFalse(m.World.Rules.Events.Any(e=>e.kind=="bounce"&&e.position.z*(seat<2?1:-1)>0),"Idle body must not receive a free legal return");
   }
  }
  [Test] public void MaintenanceCoversBothServeSidesAndBothFeedLevelsForEverySeat()
  {
   var root=new GameObject("Mixed practice fixture");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="receive-maintenance";run.MaximumReturnDifficulty=.25f;run.FixedServeSides="both";
    for(int i=0;i<16;i++) {
     bool serve=i/4%2==0;bool left=i/4==2;
     Assert.AreEqual(serve?"stationary-serve":"receive-feed",run.TaskForEpisode(i));
     Assert.AreEqual(left,run.ServeFromLeftForEpisode(i));
     Assert.AreEqual(serve?1:i/4==1?0:.25f,run.DifficultyForEpisode(i));
     using(var drill=new PlayerContactDrillV3(1101773+i,i%4,run.TaskForEpisode(i),run.DifficultyForEpisode(i),serveFromLeft:run.ServeFromLeftForEpisode(i))) {
      Assert.IsFalse(drill.Match.BallHeld);Assert.AreEqual(serve,drill.Match.StationarySupportActive);Assert.AreEqual(left,drill.ServeFromLeft);
      Assert.AreEqual(serve?RallyPhase.AwaitServe:RallyPhase.ServeFlight,drill.Match.World.Rules.Phase);
      Assert.IsFalse(PlayerContactDrillV3.ActionMask(i%4,i%4,drill.Task)[16]);
      if(!serve) { Assert.IsFalse(drill.Match.World.Rules.Bounced);Assert.AreEqual(i%4,drill.Match.World.Rules.DesignatedReceiver); }
     }
    }
   }finally{Object.DestroyImmediate(root);}
  }
  [Test] public void MaintenanceWorkersRequireFullMixedCycles()
  {
   var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="receive-maintenance",
    sourceIdentity=new string('a',64),buildIdentity=new string('b',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/maintenance-fixture",
    basePort=5005,workerCount=8,firstSeed=1000000,seedsPerWorker=12288,arenasPerWorker=16,ticksPerFrame=48,fixedServeSides="both",maximumReturnDifficulty=.25f};
   Assert.AreEqual(16,PlayerWorkerPlanV3.CycleLength(m.task,m.fixedServeSides));
   for(int i=0;i<8;i++)Assert.AreEqual(1000000+i*12288,PlayerWorkerPlanV3.Create(m,i).FirstSeed);
   m.seedsPerWorker=24;Assert.Throws<System.ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
  }
  [Test] public void VariedMaintenancePreservesBothServeSidesAndAllSeats()
  {
   var root=new GameObject("Varied maintenance fixture");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="receive-varied-maintenance";run.MaximumReturnDifficulty=.25f;run.FixedServeSides="both";
    for(int i=0;i<32;i++) {
     bool serve=i/4%4==0;bool left=serve&&i>=16;
     Assert.AreEqual(serve?"stationary-serve":"receive-feed",run.TaskForEpisode(i));
     Assert.AreEqual(left,run.ServeFromLeftForEpisode(i));
     Assert.AreEqual(serve?1:i/4%4==1?0:.25f,run.DifficultyForEpisode(i));
     using(var d=new PlayerContactDrillV3(1101773+i,i%4,run.TaskForEpisode(i),run.DifficultyForEpisode(i),serveFromLeft:run.ServeFromLeftForEpisode(i))) {
      Assert.AreEqual(serve,d.Match.StationarySupportActive);Assert.IsFalse(d.Match.World.Rules.Bounced);
      Assert.AreEqual(serve?RallyPhase.AwaitServe:RallyPhase.ServeFlight,d.Match.World.Rules.Phase);
     }
    }
   }finally{Object.DestroyImmediate(root);}
  }
  [Test] public void VariedMaintenanceWorkersRejectPartialServiceSideCycles()
  {
   var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="receive-varied-maintenance",
    sourceIdentity=new string('a',64),buildIdentity=new string('b',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/varied-fixture",
    basePort=5005,workerCount=8,firstSeed=1000000,seedsPerWorker=12288,arenasPerWorker=16,ticksPerFrame=48,fixedServeSides="both",maximumReturnDifficulty=.25f};
   Assert.AreEqual(32,PlayerWorkerPlanV3.CycleLength(m.task,m.fixedServeSides));
   for(int i=0;i<8;i++)Assert.AreEqual(1000000+i*12288,PlayerWorkerPlanV3.Create(m,i).FirstSeed);
   m.seedsPerWorker=16;Assert.Throws<System.ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
  }
  [Test] public void DifficultyKeepsEasyPracticeAndCoversAllFourSeats()
  {
   var root=new GameObject("Receive feed curriculum fixture");root.SetActive(false);
   try
   {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="receive-feed";run.MaximumReturnDifficulty=.5f;
    for(int i=0;i<32;i++)
    {Assert.AreEqual("receive-feed",run.TaskForEpisode(i));Assert.AreEqual(i/4%4==0?0:.5f,run.DifficultyForEpisode(i));}
   }finally{Object.DestroyImmediate(root);}
  }
 }
}

