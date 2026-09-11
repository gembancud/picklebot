using System.Linq;
using NUnit.Framework;
using UnityEngine;
using Unity.MLAgents;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;

namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerPairedFeedV3Tests
 {
  private static float[] Commands(float lateral)
  {
   var a=new float[PlayerMlAgentV3.ContinuousCount];
   a[0]=lateral;a[3]=a[4]=a[15]=-1;return a;
  }
  private sealed class IdlePolicy:IPlayerPolicyV3
  {
   public string Name=>"Physical contact test fixture";
   public void Reset(){}
   public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)=>default;
  }
  [Test] public void PhysicalPaddleContactCreditsEitherTeammate()
  {
   // A collision fixture, not a training feed or a demonstrated stroke.
   for(int seat=0;seat<4;seat++)for(int partner=0;partner<2;partner++)
   using(var d=new PlayerContactDrillV3(1301100,seat,"rally-air-feed",0,cooperative:true)) {
    int hitter=seat^partner;var m=d.Match;var paddle=m.World.Players[hitter].Paddle;
    var normal=paddle.rotation*Vector3.forward;
    m.World.Ball.position=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint+normal*.12f;
    m.World.Ball.transform.position=m.World.Ball.position;m.World.Ball.linearVelocity=-normal*4;
    m.World.Ball.WakeUp();m.AttachPolicies(Enumerable.Range(0,4).Select(_=>(IPlayerPolicyV3)new IdlePolicy()).ToArray(),1301100);
    float reward=0;for(int tick=0;tick<40&&!d.Done&&!d.FaceContact;tick++){d.Step();reward+=d.Reward;}
    Assert.IsTrue(d.FaceContact,"No physical face contact for seat "+hitter+": "+d.Outcome+" "+m.Failure);
    Assert.AreEqual(hitter,d.Hitter);Assert.IsTrue(d.ContactWasVolley);Assert.GreaterOrEqual(reward,.25f);
    Assert.IsTrue(m.World.Contacts.Any(c=>c.player==hitter&&c.surface=="RoundedHittingFace"));
   }
  }
  [Test] public void EachPairFeedLaneIsPhysicallyReachableWithBoundedFootwork()
  {
   // Feasibility only: move a ready paddle laterally with the real bounded motor.
   // This fixture is never attached to a trained actor or used as a reward target.
   for(int seat=0;seat<4;seat++)foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"}) {
    var lanes=new System.Collections.Generic.HashSet<int>();
    for(int seed=1301100;seed<1301160&&lanes.Count<3;seed++) {
     int lane;using(var probe=new PlayerContactDrillV3(seed,seat,task,0,cooperative:true))lane=probe.Match.RallyFeedLane;
     if(!lanes.Add(lane))continue;
     float closest=999;bool correctBounce=false;
     for(int partner=0;partner<2;partner++)using(var d=new PlayerContactDrillV3(seed,seat,task,0,cooperative:true)) {
      var m=d.Match;int hitter=seat^partner;float targetX=m.World.Ball.position.x;
      for(int tick=0;tick<600&&!m.World.Rules.Dead;tick++) {
       var paddle=m.World.Players[hitter].Paddle;var face=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint;
       var values=new float[18];values[0]=Mathf.Clamp((targetX-face.x)*(hitter<2?1:-1)*5,-1,1);
       var actions=new PlayerActionV3[4];actions[hitter]=new PlayerActionV3(values);
       Assert.IsTrue(m.Step(actions),m.Failure);
       face=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint;
       float gap=Vector3.Distance(face,m.World.Ball.position);
       if(gap<closest){closest=gap;correctBounce=m.World.Rules.Events.Any(e=>e.kind=="bounce"&&e.time>0)==(task=="rally-bounce-feed");}
      }
     }
     Assert.Less(closest,.25f,task+" seat "+seat+" lane "+lane);Assert.IsTrue(correctBounce,task+" lane "+lane);
    }
    Assert.AreEqual(3,lanes.Count);
   }
  }
  [Test] public void TwoPrivateActorsMoveIndependentlyAndCourtsHaveSeparateGroups()
  {
   var root=new GameObject("Pair private action fixture");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="paired-maintenance";
    run.RequireTrainer=false;run.AutoRun=false;run.FirstSeed=1301000;run.SeedCount=4;run.ArenaCount=2;
    root.SetActive(true);run.InitializeRun();
    Assert.IsTrue(run.Report.cooperativePairs);
    Assert.AreNotEqual(run.ActiveArenas[0].GroupId,run.ActiveArenas[1].GroupId);
    foreach(var arena in run.ActiveArenas) {
     Assert.AreEqual(2,arena.RegisteredPlayers);
     foreach(var agent in arena.Agents) {
      Assert.AreEqual(agent.Seat/2==arena.Drill.Player/2,agent.Learning);
      agent.HeuristicControls=Commands(agent.Seat%2==0?.4f:-.4f);
     }
    }
    for(int tick=0;tick<13;tick++)run.StepOneTick();
    foreach(var arena in run.ActiveArenas)foreach(var agent in arena.Agents) {
     if(!agent.Learning){Assert.AreEqual(0,agent.DecisionsReceived);Assert.IsTrue(arena.Drill.Match.ActiveFor(agent.Seat).ToArray().All(x=>x==0));continue;}
     Assert.Greater(agent.DecisionsReceived,0);Assert.AreEqual(agent.Seat,agent.LastObservation.player);
     Assert.AreEqual(PlayerObservationV3.Count,agent.LastObservation.ToArray().Length);
     Assert.AreEqual(agent.Seat%2==0?.4f:-.4f,arena.Drill.Match.ActiveFor(agent.Seat).ToArray()[0],1e-5);
     Assert.AreEqual(0,agent.LastCommand.ToArray()[4]);Assert.AreEqual(0,agent.LastCommand.ToArray()[16]);
    }
    Assert.IsFalse(ReferenceEquals(run.ActiveArenas[0].Agents[0].LastObservation,run.ActiveArenas[0].Agents[1].LastObservation));
   }finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
  }
  [Test] public void PairedEpisodeResetRotatesBothTeamMembersWithoutInactiveDecisions()
  {
   var root=new GameObject("Pair lifecycle fixture");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="paired-maintenance";
    run.RequireTrainer=false;run.AutoRun=false;run.FirstSeed=1301000;run.SeedCount=4;run.ArenaCount=1;
    root.SetActive(true);run.InitializeRun();
    for(int tick=0;tick<6000&&run.Report.status=="running";tick++)run.StepOneTick();
    Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(4,run.Episodes.Count);
    foreach(var e in run.Episodes) {
     Assert.IsTrue(e.cooperativePairs);Assert.AreEqual(4,e.decisionsByPlayer.Length);
     Assert.AreEqual(e.decisions,e.decisionsByPlayer.Sum());
     for(int p=0;p<4;p++)if(p/2==e.player/2)Assert.Greater(e.decisionsByPlayer[p],0);else Assert.AreEqual(0,e.decisionsByPlayer[p]);
    }
   }finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
  }
  [Test] public void OpeningReturnStillRequiresBounceAndDesignatedReceiver()
  {
   for(int seat=0;seat<4;seat++)for(int variant=0;variant<2;variant++)
   using(var d=new PlayerContactDrillV3(1103000,seat,"receive-feed",0,cooperative:true)) {
    Assert.IsTrue(d.Cooperative);var r=d.Match.World.Rules;
    if(variant==1)r.Bounce(new Vector3(r.ServiceX(seat),0,DoublesRules.Side(seat/2)*4),.01f);
    r.Hit(variant==0?seat:seat^1,.02f);
    Assert.AreEqual(variant==0?Fault.EarlyVolley:Fault.WrongReceiver,r.LastFault);
    for(int p=0;p<4;p++) {
     var mask=PlayerContactDrillV3.ActionMask(p,seat,"receive-feed",true);
     Assert.AreEqual(p/2==seat/2,mask[0]);Assert.IsFalse(mask[4]||mask[16]);
    }
   }
  }
  [Test] public void EitherPartnerCanTakeRallyBallAndMustRecoverVolleyBalance()
  {
   for(int seat=0;seat<4;seat++)for(int partner=0;partner<2;partner++)
   using(var d=new PlayerContactDrillV3(1103000,seat,"rally-air-feed",0,cooperative:true)) {
    int hitter=seat^partner;var r=d.Match.World.Rules;
    r.Feet(hitter,false,true,true,.01f);r.Hit(hitter,.02f);
    Assert.IsFalse(r.Dead);Assert.IsTrue(r.VolleyMomentumPending(hitter));
    r.Bounce(new Vector3(0,0,-DoublesRules.Side(seat/2)*3),.03f);
    r.Feet(hitter,true,false,false,.04f);Assert.AreEqual(Fault.KitchenMomentum,r.LastFault);
    Assert.AreEqual(1-seat/2,r.Winner);
   }
  }
  [Test] public void PairFeedsCoverLeftMiddleRightOnFullCourtWithBothBodiesPresent()
  {
   var lanes=new System.Collections.Generic.HashSet<int>();
   for(int seat=0;seat<4;seat++)for(int i=0;i<12;i++)
   using(var d=new PlayerContactDrillV3(1103000+i,seat,"rally-air-feed",0,cooperative:true)) {
    lanes.Add(d.Match.RallyFeedLane);Assert.IsFalse(d.Match.BallHeld||d.Match.StationarySupportActive);
    Assert.AreEqual(3.2f,Mathf.Abs(d.Match.World.Players[seat].Position.z),1e-5);
    Assert.AreEqual(d.Match.World.Players[seat].Position.z,d.Match.World.Players[seat^1].Position.z,1e-5);
    Assert.AreEqual(6.096f,DoublesRules.HalfWidth*2,1e-5);Assert.AreEqual(13.4112f,DoublesRules.HalfLength*2,1e-5);
    Assert.Less(Mathf.Abs(d.Match.World.Ball.position.x),DoublesRules.HalfWidth);
    Assert.IsTrue(d.Match.World.Rules.CanVolley);Assert.IsFalse(d.Match.World.Rules.Bounced);
   }
   CollectionAssert.AreEquivalent(new[]{0,1,2},lanes);
  }
  [Test] public void PairedMaintenanceKeepsServeSidesAndAllReturnContexts()
  {
   var root=new GameObject("Pair schedule fixture");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="paired-maintenance";run.FixedServeSides="both";run.MaximumReturnDifficulty=.25f;
    for(int i=0;i<32;i++) {
     Assert.AreEqual(i/4<2?"stationary-serve":i/4<4?"receive-feed":i/4<6?"rally-air-feed":"rally-bounce-feed",run.TaskForEpisode(i));
     Assert.AreEqual(i/4==1,run.ServeFromLeftForEpisode(i));
     Assert.AreEqual(i/4<2?1:i/4==3?.25f:0,run.DifficultyForEpisode(i));
    }
    Assert.AreEqual(32,PlayerWorkerPlanV3.CycleLength(run.Task,run.FixedServeSides));
   }finally{Object.DestroyImmediate(root);}
  }
 }
}
