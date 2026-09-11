using System;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;

namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerMovementPositionRewardV3Tests
 {
  [Test] public void StationaryBodyReceivesNothingForAnApproachingBall()
  {
   var reward=new PlayerMovementPositionRewardV3(Vector3.zero,Vector3.right,.15f);
   for(int i=0;i<100;i++)Assert.AreEqual(0,reward.Advance(Vector3.zero,new Vector3(1,2,5-i*.1f)));
   Assert.AreEqual(0,reward.TotalReward);
  }
  [Test] public void BodyProgressPaysOnceAndOscillationCannotExceedBudget()
  {
   var reward=new PlayerMovementPositionRewardV3(Vector3.zero,Vector3.zero,.15f);var ball=Vector3.right*3;
   Assert.AreEqual(.05f,reward.Advance(Vector3.right*.25f,ball),1e-6);
   for(int i=0;i<20;i++){Assert.AreEqual(0,reward.Advance(Vector3.left,ball));Assert.AreEqual(0,reward.Advance(Vector3.right*.25f,ball));}
   Assert.AreEqual(.10f,reward.Advance(Vector3.right,ball),1e-6);
   for(int i=0;i<20;i++)Assert.AreEqual(0,reward.Advance(Vector3.right*(i%4),ball));
   Assert.AreEqual(.15f,reward.TotalReward,1e-6);
  }
  [Test] public void VerticalMotionAndMovingAwayDoNotEarnReward()
  {
   var reward=new PlayerMovementPositionRewardV3(Vector3.zero,Vector3.zero,.15f);
   Assert.AreEqual(0,reward.Advance(Vector3.up,Vector3.right));
   Assert.AreEqual(0,reward.Advance(Vector3.left,Vector3.right));
  }
  [Test] public void ZeroBudgetDisablesReward()
  {
   var reward=new PlayerMovementPositionRewardV3(Vector3.zero,Vector3.zero,0);
   Assert.AreEqual(0,reward.Advance(Vector3.right,Vector3.right));
  }
  [Test] public void InvalidBudgetsAndUnsupportedTasksFailBeforePhysics()
  {
   foreach(float v in new[]{-.1f,.251f,float.NaN,float.PositiveInfinity})
    Assert.Throws<ArgumentOutOfRangeException>(()=>PlayerMovementPositionRewardV3.ValidateBudget(v));
   foreach(string task in new[]{"stationary-serve","paired-movement-maintenance","fixed-team-match"})
    Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidateMovementPositionReward(task,.25f,.15f));
   Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidateMovementPositionReward("movement-maintenance",0,.15f));
   Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1301200,0,"rally-air-feed",0,cooperative:true,movementRange:.25f,movementPositionReward:.15f));
   Assert.Throws<ArgumentException>(()=>new PlayerContactDrillV3(1301200,0,"rally-air-feed",0,movementPositionReward:.15f));
  }
  [Test] public void BonusIsRoutedOnlyToTheChallengeHalfOfTheCurriculum()
  {
   var root=new GameObject("Position reward routing");root.SetActive(false);
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();run.Task="movement-maintenance";run.FixedServeSides="both";
    run.FirstSeed=1301200;run.MovementRange=.25f;run.MaximumReturnDifficulty=.25f;run.MovementPositionReward=.15f;
    for(int i=0;i<64;i++)using(var d=run.CreateDrillForEpisode(i,out _))Assert.AreEqual(i>=32?.15f:0,d.MovementPositionRewardScale);
   }finally{UnityEngine.Object.DestroyImmediate(root);}
  }
  [Test] public void WorkerManifestRoutesAndValidatesTheOptionalBonus()
  {
   var manifest=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="evaluation",task="movement-maintenance",fixedServeSides="both",basePort=5400,workerCount=1,arenasPerWorker=4,seedsPerWorker=64,firstSeed=1104000,ticksPerFrame=1,sourceIdentity=new string('a',64),buildIdentity=new string('b',64),modelHash=new string('c',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/position-reward-fixture",movementRange=.25f,movementPositionReward=.15f};
   var root=new GameObject("Position reward worker");root.SetActive(false);
   var model=ScriptableObject.CreateInstance<Unity.InferenceEngine.ModelAsset>();
   try {
    var run=root.AddComponent<PlayerMlDrillsV3>();PlayerWorkerPlanV3.Create(manifest,0).Configure(run,model);Assert.AreEqual(.15f,run.MovementPositionReward);
    manifest.task="paired-movement-maintenance";Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(manifest,0));
   }finally{UnityEngine.Object.DestroyImmediate(root);UnityEngine.Object.DestroyImmediate(model);}
  }
  private sealed class FixedPolicy:IPlayerPolicyV3
  {
   private readonly PlayerActionV3 action;
   public string Name=>"test-only-fixed-actions";
   public FixedPolicy(PlayerActionV3 action){this.action=action;}
   public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)=>action;
   public void Reset(){}
  }
  [Test] public void IdenticalActionsHaveIdenticalPhysicsAndOnlyTheCappedRewardDiffers()
  {
   float totalBonus=0;
   for(int seat=0;seat<4;seat++)foreach(string task in new[]{"rally-air-feed","rally-bounce-feed"})
   using(var control=new PlayerContactDrillV3(1301200,seat,task,0,movementRange:.25f))
   using(var shaped=new PlayerContactDrillV3(1301200,seat,task,0,movementRange:.25f,movementPositionReward:.15f)) {
    var delta=control.Match.World.Ball.position-control.Match.World.Players[seat].Position;
    var a=new float[18];float sign=seat<2?1:-1;a[0]=Mathf.Sign(delta.x)*sign;a[1]=Mathf.Sign(delta.z)*sign;a[5]=1;
    foreach(var d in new[]{control,shaped})d.Match.AttachPolicies(Enumerable.Range(0,4).Select(i=>(IPlayerPolicyV3)new FixedPolicy(i==seat?new PlayerActionV3(a):default)).ToArray(),1301200);
    float controlReward=0,shapedReward=0;
    while(!control.Done) {
     float paid=shaped.MovementPositionReward;
     control.Step();shaped.Step();controlReward+=control.Reward;shapedReward+=shaped.Reward;
     Assert.AreEqual(control.Done,shaped.Done);Assert.AreEqual(control.FaceContact,shaped.FaceContact);
     CollectionAssert.AreEqual(PlayerObservationV3.Capture(control.Match,seat,control.Match.Tick).ToArray(),PlayerObservationV3.Capture(shaped.Match,seat,shaped.Match.Tick).ToArray());
     if(shaped.FaceContact||shaped.Match.World.Rules.Dead)Assert.AreEqual(paid,shaped.MovementPositionReward);
    }
    Assert.AreEqual(control.Outcome,shaped.Outcome);Assert.AreEqual(shaped.MovementPositionReward,shapedReward-controlReward,1e-5);
    Assert.LessOrEqual(shaped.MovementPositionReward,.15f);totalBonus+=shaped.MovementPositionReward;
   }
   Assert.Greater(totalBonus,0,"Integration fixture must exercise the enabled reward.");
  }
 }
}
