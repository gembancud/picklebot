using System;
using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerLearning.Tests
{
 public sealed class PlayerMatchStatePracticeV3Tests
 {
  [Test]
  public void InitializedStatesPreserveSideOutScoringAndServiceOrder()
  {
   for(int server=0;server<4;server++)foreach(bool right in new[]{false,true})foreach(int number in new[]{1,2})foreach(bool swap in new[]{false,true}){
    var rules=new DoublesRules(server,right,4,7,number,swap);int team=server/2;
    Assert.AreEqual(server,rules.Server);Assert.AreEqual(right,rules.IsRight(server));Assert.AreEqual(number,rules.ServerNumber);
    Assert.AreEqual(4,rules.Score[0]);Assert.AreEqual(7,rules.Score[1]);Assert.AreEqual(0,rules.Events.Count);Assert.AreEqual(RallyPhase.AwaitServe,rules.Phase);
    Assert.AreEqual(right,rules.IsRight(rules.DesignatedReceiver));Assert.AreEqual(1-team,rules.DesignatedReceiver/2);
    rules.Fail(team,Fault.Out,1);Assert.IsTrue(rules.ResolveRally());rules.BeginRally();
    Assert.AreEqual(4,rules.Score[0]);Assert.AreEqual(7,rules.Score[1]);
    if(number==1){Assert.AreEqual(server^1,rules.Server);Assert.AreEqual(2,rules.ServerNumber);Assert.AreEqual(team,rules.ServingTeam);}
    else{Assert.AreEqual(1-team,rules.ServingTeam);Assert.AreEqual(1,rules.ServerNumber);Assert.IsTrue(rules.IsRight(rules.Server));}
    var scoring=new DoublesRules(server,right,4,7,number,swap);scoring.Fail(1-team,Fault.Out,1);Assert.IsTrue(scoring.ResolveRally());scoring.BeginRally();
    Assert.AreEqual(server,scoring.Server);Assert.AreEqual(!right,scoring.IsRight(server));Assert.AreEqual(team==0?5:4,scoring.Score[0]);Assert.AreEqual(team==1?8:7,scoring.Score[1]);
   }
   Assert.Throws<ArgumentException>(()=>new DoublesRules(0,true,11,0));
   Assert.Throws<ArgumentException>(()=>new DoublesRules(0,true,0,0,3));
  }
  [UnityTest]
  public IEnumerator PracticeScoresAreRealPrivateObservationsAndLegacyResetsRemainZero()
  {
   var root=new GameObject("Match-state reset fixture");root.SetActive(false);var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;
   run.Task="serve-context-return";run.FixedServeSides="both";run.StationaryFlightDifficulty=1;run.MaximumReturnDifficulty=.5f;run.FirstSeed=1306630;run.RandomizeMatchContext=true;
   var scores=new HashSet<int>();var numbers=new HashSet<int>();int randomized=0;
   try{for(int index=0;index<256;index++)using(var d=run.CreateDrillForEpisode(index,out var rejections)){
    Assert.IsEmpty(rejections);bool contextual=d.Task=="stationary-serve"||d.Task=="stationary-flight";Assert.AreEqual(contextual,d.RandomMatchContext);
    var rules=d.Match.World.Rules;var obs=PlayerObservationV3.Capture(d.Match,d.Player,0).ToArray();int team=d.Player/2;
    Assert.AreEqual(Mathf.Clamp01(rules.Score[team]/11f),obs[50]);Assert.AreEqual(Mathf.Clamp01(rules.Score[1-team]/11f),obs[51]);Assert.AreEqual(rules.ServerNumber/2f,obs[52]);
    if(contextual){randomized++;scores.Add(rules.Score[0]);scores.Add(rules.Score[1]);numbers.Add(rules.ServerNumber);
     var random=new System.Random((run.FirstSeed+index)^0x17c9b43);Assert.AreEqual(random.Next(11),rules.Score[0]);Assert.AreEqual(random.Next(11),rules.Score[1]);Assert.AreEqual(1+random.Next(2),rules.ServerNumber);
     if(d.Task=="stationary-serve"){
      Assert.AreEqual(d.Player,rules.Server);Assert.AreEqual(!d.ServeFromLeft,rules.IsRight(d.Player));Assert.AreEqual(RallyPhase.AwaitServe,rules.Phase);
      var p=d.Match.World.Ball.position;
      for(int tick=0;tick<18;tick++)Assert.IsTrue(d.Match.Step(new PlayerActionV3[4]));
      Assert.Less(Vector3.Distance(p,d.Match.World.Ball.position),.0001f);Assert.IsFalse(d.Match.BallHeld);Assert.IsTrue(d.Match.StationarySupportActive);
     }else{Assert.AreEqual(RallyPhase.Rally,rules.Phase);Assert.AreEqual(team,rules.ExpectedTeam);}
    }else{Assert.AreEqual(0,rules.Score[0]);Assert.AreEqual(0,rules.Score[1]);}
   }
   Assert.AreEqual(192,randomized);Assert.AreEqual(11,scores.Count);Assert.AreEqual(2,numbers.Count);
   run.RandomizeMatchContext=false;using(var legacy=run.CreateDrillForEpisode(0,out _)){Assert.IsFalse(legacy.RandomMatchContext);Assert.AreEqual(0,legacy.Match.World.Rules.Score[0]);Assert.AreEqual(0,legacy.Match.World.Rules.Score[1]);Assert.AreEqual(2,legacy.Match.World.Rules.ServerNumber);}
   }finally{UnityEngine.Object.DestroyImmediate(root);}
   yield return null;
  }
 }
}
