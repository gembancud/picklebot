using System;
using System.Linq;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
namespace Picklebot.PlayerLearning.Tests {
public sealed class PlayerRandomizedScaleV1Tests {
 [Test] public void SeedControlsContinuousVariationAndOldRecipesRemainDeterministic() {
  var distances=new HashSet<float>();
  for(int i=0;i<1024;i++) {
   var a=PlayerRecoveryScheduleV3.For(i,.25f,.1f,.5f,"randomized",2000000+i);
   var b=PlayerRecoveryScheduleV3.For(i,.25f,.1f,.5f,"randomized",2000000+i);
   Assert.AreEqual(a,b);Assert.IsTrue(a.Difficulty>=0&&a.Difficulty<=1);
   if(a.Group=="focus") {distances.Add(a.Range);Assert.That(a.Range,Is.InRange(.00625f,.25f));Assert.That(a.Timing,Is.InRange(0,.25f));Assert.That(a.Starts,Is.InRange(0,.15f));}
   Assert.AreEqual(PlayerRecoveryScheduleV3.For(i,.0625f,.1f,.25f,"axes",1),PlayerRecoveryScheduleV3.For(i,.0625f,.1f,.25f,"axes",2));
  }
  Assert.Greater(distances.Count,500);
 }
 [Test] public void ActualTrainAndDevelopmentResetsAreFiniteDiverseAndReproducible() {
  var g=new GameObject("Randomized reset validation");g.SetActive(false);
  try {
   var run=g.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;run.Task="movement-maintenance";run.FixedServeSides="both";run.MovementRecoveryMix=true;run.MovementPattern="randomized";run.MovementRange=.25f;run.MovementRehearsalRange=.1f;run.MaximumReturnDifficulty=.5f;run.SeedCount=1024;
   var unique=new HashSet<string>();
   foreach(int first in new[]{2000000,4000000}) {
    run.FirstSeed=first;
    for(int i=0;i<512;i++) {
     using(var a=run.CreateDrillForEpisode(i,out _))
     using(var b=run.CreateDrillForEpisode(i,out _)) {
      var obs=PlayerObservationV3.Capture(a.Match,i%4,0).ToArray();
      CollectionAssert.AreEqual(obs,PlayerObservationV3.Capture(b.Match,i%4,0).ToArray());
      Assert.IsTrue(obs.All(float.IsFinite));
      if(i%256>=64)Assert.IsTrue(unique.Add(string.Join(",",obs.Select(x=>x.ToString("R",System.Globalization.CultureInfo.InvariantCulture)))));
      Assert.AreEqual(0,a.MovementPositionReward);
      if(i%256>=128)Assert.IsFalse(a.Match.BallHeld||a.Match.StationarySupportActive||a.Match.World.Ball.isKinematic);
     }
    }
   }
   Assert.AreEqual(768,unique.Count);
  } finally {UnityEngine.Object.DestroyImmediate(g);}
 }
}}
