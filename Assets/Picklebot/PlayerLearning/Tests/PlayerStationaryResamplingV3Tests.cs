using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControlsIntegration;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerStationaryResamplingV3Tests
    {
        [UnityTest]
        public IEnumerator WiderRangeRejectsOverlapWithoutLeakingOrChangingValidCandidates()
        {
            var root=new GameObject("Stationary resampling fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;
            // Replay the already allocated failed development range; no training or final seeds.
            run.FirstSeed=1101613;run.Task="stationary-practice";run.FeedLowering=.4f;run.FeedLateralOffset=-.25f;
            int rejected=0, acceptedFirst=0;
            try
            {
                for(int i=0;i<128;i++)
                {
                    int before=Object.FindObjectsByType<Collider>(FindObjectsSortMode.None).Length;
                    using(var drill=run.CreateDrillForEpisode(i,out var reasons))
                    {
                        rejected+=reasons.Length;if(reasons.Length==0)acceptedFirst++;
                        for(int attempt=0;attempt<reasons.Length;attempt++)
                        {
                            var f=PlayerMlDrillsV3.StationaryResetFractions(run.FirstSeed+i,attempt);
                            var error=Assert.Throws<StationaryResetOverlapException>(()=>
                            {using(var invalid=new PlayerContactDrillV3(run.FirstSeed+i,i%4,"stationary-contact",1,.4f*f.x,-.25f*f.y)){} });
                            Assert.AreEqual(reasons[attempt],error.Surface);
                        }
                        var accepted=PlayerMlDrillsV3.StationaryResetFractions(run.FirstSeed+i,reasons.Length);
                        Assert.AreEqual(.4f*accepted.x,drill.FeedLowering);
                        Assert.AreEqual(-.25f*accepted.y,drill.FeedLateralOffset);
                        using(var repeat=run.CreateDrillForEpisode(i,out var repeated))
                        {
                            CollectionAssert.AreEqual(reasons,repeated);
                            Assert.AreEqual(drill.Match.World.Ball.position,repeat.Match.World.Ball.position);
                        }
                        var p=drill.Match.World.Ball.position;
                        for(int tick=0;tick<12;tick++)drill.Match.World.Simulate(true);
                        Assert.AreEqual(0,drill.Match.World.Contacts.Count);
                        Assert.Less(Vector3.Distance(p,drill.Match.World.Ball.position),1e-6);
                        Assert.AreEqual(0,drill.Match.Tick);Assert.IsFalse(drill.Done);
                    }
                    Assert.AreEqual(before,Object.FindObjectsByType<Collider>(FindObjectsSortMode.None).Length,"Reset worlds must be disposed, including rejected candidates");
                    if(i%8==7)yield return null;
                }
                Assert.Greater(rejected,0,"Must exercise the actual overlap failure");
                Assert.Greater(acceptedFirst,0);
                Assert.Throws<System.ArgumentOutOfRangeException>(()=>PlayerMlDrillsV3.StationaryResetFractions(1101613,64));
                run.Task="stationary-practice";run.FeedLowering=float.NaN;
                Assert.Throws<System.ArgumentOutOfRangeException>(()=>run.CreateDrillForEpisode(0,out _));
            }
            finally{Object.DestroyImmediate(root);}
        }
    }
}
