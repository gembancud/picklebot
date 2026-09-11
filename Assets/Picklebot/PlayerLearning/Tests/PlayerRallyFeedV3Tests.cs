using System.Linq;
using NUnit.Framework;
using UnityEngine;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;

namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerRallyFeedV3Tests
 {
  [Test] public void RallyFeedsExposeLegalVolleyStateWithNoFabricatedIncomingBounce()
  {
   for(int seat=0;seat<4;seat++)foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"})
   using(var d=new PlayerContactDrillV3(1102837,seat,task,0)) {
    var rules=d.Match.World.Rules;
    Assert.AreEqual(RallyPhase.Rally,rules.Phase);Assert.IsTrue(rules.CanVolley);Assert.IsFalse(rules.Bounced);
    Assert.AreEqual(seat/2,rules.ExpectedTeam);Assert.IsFalse(d.Match.BallHeld||d.Match.StationarySupportActive);
    Assert.AreEqual(3.2f,Mathf.Abs(d.Match.World.Players[seat].Position.z),1e-5);
    Assert.IsTrue(rules.Events.All(e=>e.time==0));
    rules.Feet(seat,false,true,true,.01f);rules.Hit(seat,.02f);
    Assert.IsFalse(rules.Dead);Assert.IsTrue(rules.VolleyMomentumPending(seat));
   }
  }
  [Test] public void KitchenStillForbidsVolleyButAllowsBouncedShot()
  {
   for(int seat=0;seat<4;seat++)for(int bounced=0;bounced<2;bounced++)
   using(var d=new PlayerContactDrillV3(1102837,seat,"rally-air-feed",0)) {
    var rules=d.Match.World.Rules;rules.Feet(seat,true,false,false,.01f);
    if(bounced==1)rules.Bounce(new Vector3(0,0,DoublesRules.Side(seat/2)),.02f);
    rules.Hit(seat,.03f);
    Assert.AreEqual(bounced==0,rules.Dead);
    Assert.AreEqual(bounced==0?Fault.KitchenVolley:Fault.None,rules.LastFault);
   }
  }
  [Test] public void VolleyMomentumRemainsEnforcedAfterOppositeCourtLanding()
  {
   for(int seat=0;seat<4;seat++)using(var d=new PlayerContactDrillV3(1102837,seat,"rally-air-feed",0)) {
    var r=d.Match.World.Rules;r.Feet(seat,false,true,true,.01f);r.Hit(seat,.02f);
    r.Bounce(new Vector3(0,0,-DoublesRules.Side(seat/2)*3),.03f);
    Assert.IsTrue(r.VolleyMomentumPending(seat));r.Feet(seat,true,false,false,.04f);
    Assert.AreEqual(Fault.KitchenMomentum,r.LastFault);Assert.AreEqual(1-seat/2,r.Winner);
   }
  }
  [Test] public void BothEasyFeedStylesReachAReadyPlayerThroughPhysicalFlight()
  {
   for(int seat=0;seat<4;seat++)foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"})
   using(var d=new PlayerContactDrillV3(1102837,seat,task,0)) {
    var m=d.Match;var b=m.World.Players[seat];var face=b.Paddle.position+b.Paddle.rotation*PlayerStrokeAimV3.FacePoint;
    var idle=Enumerable.Range(0,4).Select(_=>new PlayerActionV3(new float[18])).ToArray();
    float gap=999,time=-1;bool bounceBeforeClosest=false;
    for(int tick=0;tick<720&&!m.World.Rules.Dead;tick++) {
     Assert.IsTrue(m.Step(idle),m.Failure);
     float next=Vector3.Distance(face,m.World.Ball.position);
     if(next<gap){gap=next;time=m.World.Time;bounceBeforeClosest=m.World.Rules.Events.Any(e=>e.kind=="bounce"&&e.time>0);}
    }
    Assert.Less(gap,.25f,task+" seat "+seat);Assert.Greater(time,.25f);
    Assert.AreEqual(task=="rally-bounce-feed",bounceBeforeClosest);
   }
  }
  [Test] public void MixedCycleMaintainsServingOpeningReturnsAndBothRallyFeeds()
  {
   var root=new GameObject("Rally curriculum fixture");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="rally-maintenance";run.MaximumReturnDifficulty=.25f;run.StationaryFlightDifficulty=0;run.FixedServeSides="both";
    for(int i=0;i<32;i++) {
     string expected=i/4<2?"stationary-serve":i/4<5?"receive-feed":i/4<7?"rally-air-feed":"rally-bounce-feed";
     Assert.AreEqual(expected,run.TaskForEpisode(i));Assert.AreEqual(i/4==1,run.ServeFromLeftForEpisode(i));
     using(var d=new PlayerContactDrillV3(1102837+i,i%4,expected,run.DifficultyForEpisode(i),serveFromLeft:run.ServeFromLeftForEpisode(i))) {
      Assert.AreEqual(i/4>=5,d.Match.World.Rules.CanVolley);
     }
    }
    PlayerMlDrillsV3.ValidateStationaryFlightDifficulty(.25f,"rally-maintenance");
    var manifest=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="rally-maintenance",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/rally-fixture",basePort=5005,workerCount=8,firstSeed=1000000,seedsPerWorker=12288,arenasPerWorker=16,ticksPerFrame=48,fixedServeSides="both",maximumReturnDifficulty=.25f};
    Assert.IsTrue(PlayerWorkerPlanV3.Create(manifest,7).RequireTrainer);
   }finally{Object.DestroyImmediate(root);}
  }
 }
}

