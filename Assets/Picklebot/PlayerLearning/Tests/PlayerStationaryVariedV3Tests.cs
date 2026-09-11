using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using Picklebot.PlayerControlsIntegration;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerStationaryVariedV3Tests
    {
        [UnityTest]
        public IEnumerator SampledResetsAreBoundedRepeatableAndPhysicallyClear()
        {
            var root=new GameObject("Varied stationary reset fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.FirstSeed=1301985;
            run.Task="stationary-practice";run.FeedLowering=.2f;run.FeedLateralOffset=-.15f;
            var positions=new HashSet<Vector2>();var counts=new int[4];
            try
            {
                for(int i=0;i<64;i++)
                {
                    float lower=run.FeedLoweringForEpisode(i),left=run.FeedLateralOffsetForEpisode(i);
                    Assert.AreEqual("stationary-contact",run.TaskForEpisode(i));
                    Assert.That(lower,Is.InRange(0,.2f));Assert.That(left,Is.InRange(-.15f,0));
                    Assert.AreEqual(lower,run.FeedLoweringForEpisode(i));Assert.AreEqual(left,run.FeedLateralOffsetForEpisode(i));
                    positions.Add(new Vector2(lower,left));counts[i%4]++;
                    using(var drill=new PlayerContactDrillV3(run.FirstSeed+i,i%4,run.TaskForEpisode(i),.5f,lower,left))
                    {
                        Assert.IsFalse(drill.Done);Assert.IsFalse(drill.FaceContact);
                        Assert.AreEqual(lower,drill.FeedLowering);Assert.AreEqual(left,drill.FeedLateralOffset);
                        Assert.IsTrue(drill.Match.StationarySupportActive);
                        var ball=drill.Match.World.Ball;var p=ball.position;
                        for(int tick=0;tick<12;tick++)drill.Match.World.Simulate(true);
                        Assert.Less(Vector3.Distance(p,ball.position),1e-6);
                        Assert.AreEqual(Vector3.zero,ball.linearVelocity);
                        Assert.AreEqual(0,drill.Match.World.Contacts.Count,"Sampled reset must not contact any collider");
                    }
                    if(i%8==7)yield return null;
                }
                Assert.AreEqual(64,positions.Count);CollectionAssert.AreEqual(new[]{16,16,16,16},counts);
            }
            finally{Object.DestroyImmediate(root);}
        }
    }
}
