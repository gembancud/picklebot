from pathlib import Path
import json,uuid
R=Path('F:/dev/picklebot'); H=Path(__file__).parent
def edit(rel,fn):
 p=R/rel;s=p.read_text(encoding='utf-8');out=fn(s);assert out!=s,rel;p.write_bytes(out.replace('\r\n','\n').replace('\n','\r\n').encode('utf-8'))
def schedule(s):
 s=s.replace('public readonly float Range,Difficulty;','public readonly float Range,Difficulty,Timing,Starts;')
 s=s.replace('bool left=false)','bool left=false,float timing=0,float starts=0)')
 s=s.replace('ServeFromLeft=left;}','ServeFromLeft=left;Timing=timing;Starts=starts;}')
 s=s.replace('string focusPattern="lateral")','string focusPattern="lateral",int seed=0)')
 s=s.replace('if(focusPattern!="lateral"', 'if(focusPattern=="randomized")return Randomized(index,seed,lateralRange,priorRange,receiveDifficulty);\n            if(focusPattern!="lateral"',1)
 pos=s.index('        public static void Validate(')
 s=s[:pos]+'''        // Explicit opt-in reset distribution. Actual episode seed drives continuous
        // variation; schedule index controls only balanced task/seat allocation.
        private static Episode Randomized(int index,int seed,float range,float prior,float difficulty)
        {
            var old=For(index,range,prior,difficulty,"axes");
            var rng=new Random(unchecked(seed^0x715abd));
            float U()=> (float)rng.NextDouble();
            if(old.Group=="familiar") {
                if(old.Task=="stationary-serve")return old;
                // Half familiar resets remain exact anchors, half vary the feed.
                return new Episode(old.Task,"court",old.Group,old.Range,
                    index/256%2==0?old.Difficulty:difficulty*U(),old.ServeFromLeft);
            }
            if(old.Group=="prior")return new Episode(old.Task,"court",old.Group,
                prior*(.05f+.95f*U()),difficulty*U());
            // Uniform distances from 2.5cm to the declared maximum (up to1m),
            // with both lateral and depth directions. No action assistance.
            return new Episode(old.Task,"axes",old.Group,
                .00625f+(range-.00625f)*U(),difficulty*U(),false,
                .25f*U(),.15f*U());
        }
''' + s[pos:]
 s=s.replace('pattern!="lateral-right")','pattern!="lateral-right"&&pattern!="randomized")')
 return s
edit('Assets/Picklebot/PlayerLearning/PlayerRecoveryScheduleV3.cs',schedule)
def drills(s):
 s=s.replace('MaximumReturnDifficulty,MovementPattern);','MaximumReturnDifficulty,MovementPattern,FirstSeed+index);')
 s=s.replace('movementTiming:NewMovementChallenge(index)?MovementTiming:0','movementTiming:MovementRecoveryMix&&MovementPattern=="randomized"?Recovery(index).Timing:NewMovementChallenge(index)?MovementTiming:0')
 s=s.replace('movementStartVariation:NewMovementChallenge(index)?MovementStartVariation:0','movementStartVariation:MovementRecoveryMix&&MovementPattern=="randomized"?Recovery(index).Starts:NewMovementChallenge(index)?MovementStartVariation:0')
 s=s.replace('PlayerMovementPatternV3.Validate(MovementPattern,','PlayerMovementPatternV3.Validate(MovementRecoveryMix&&MovementPattern=="randomized"?"axes":MovementPattern,')
 return s
edit('Assets/Picklebot/PlayerLearning/PlayerMlDrillsV3.cs',drills)
edit('Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs',lambda s:s.replace('PlayerMovementPatternV3.Validate(manifest.movementPattern,','PlayerMovementPatternV3.Validate(manifest.movementRecoveryMix&&manifest.movementPattern=="randomized"?"axes":manifest.movementPattern,'))
test='''using System;
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
'''
p=R/'Assets/Picklebot/PlayerLearning/Tests/PlayerRandomizedScaleV1Tests.cs';assert not p.exists();p.write_bytes(test.replace('\n','\r\n').encode())
Path(str(p)+'.meta').write_text('fileFormatVersion: 2\nguid: '+uuid.uuid4().hex+'\n',encoding='utf-8')
(H/'randomized-scale-tests-metadata.json').write_text(json.dumps({'testFilter':'PlayerRandomizedScaleV1Tests|PlayerRightReturnRetentionV1Tests|PlayerRecoveryScheduleV3Tests|PlayerInterleavedRecoveryV3Tests'}),encoding='utf-8')
print('Randomized recipe and independent reset tests prepared.')
