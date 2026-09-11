using System;
using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerLateralFeedV3Tests
    {
        private sealed class Still:IPlayerPolicyV3
        {
            public string Name=>"reset translation fixture";
            public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)=>default;
        }
        private static void Attach(PlayerContactDrillV3 d)=>d.Match.AttachPolicies(new IPlayerPolicyV3[]{new Still(),new Still(),new Still(),new Still()},d.Seed);
        [UnityTest]
        public IEnumerator ZeroOffsetPreservesTheWholeEasyEpisodeExactly()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var a=new PlayerContactDrillV3(1301320+seat,seat,"easy-return"))
                using(var b=new PlayerContactDrillV3(1301320+seat,seat,"low-return",1,0,0))
                {
                    Attach(a);Attach(b);
                    while(!a.Done)
                    {
                        a.Step();b.Step();
                        Assert.AreEqual(a.Match.World.Ball.position,b.Match.World.Ball.position);
                        Assert.AreEqual(a.Match.World.Ball.linearVelocity,b.Match.World.Ball.linearVelocity);
                        Assert.AreEqual(a.Reward,b.Reward);Assert.AreEqual(a.Done,b.Done);
                        Assert.IsNull(b.Match.Failure);
                    }
                    Assert.AreEqual(a.Outcome,b.Outcome);Assert.AreEqual(a.Match.Tick,b.Match.Tick);
                }
                yield return null;
            }
        }
        [UnityTest]
        public IEnumerator TranslationRotatesWithPlayerFrameAndLeavesBodyAndFreeFlightUnchanged()
        {
            foreach(float offset in new[]{-.9f,-.6f,-.4f,-.2f,.2f,.6f,.9f})
            for(int seat=0;seat<4;seat++)
            {
                int seed=1301324+seat;
                using(var a=new PlayerContactDrillV3(seed,seat,"low-return",1,.2f,0))
                using(var b=new PlayerContactDrillV3(seed,seat,"low-return",1,.2f,offset))
                {
                    Attach(a);Attach(b);
                    Assert.AreEqual(offset,b.FeedLateralOffset);
                    var expected=Vector3.right*(seat<2?offset:-offset);
                    for(int tick=0;tick<24;tick++)
                    {
                        Assert.Less(Vector3.Distance(expected,b.Match.World.Ball.position-a.Match.World.Ball.position),1e-5);
                        Assert.Less(Vector3.Distance(a.Match.World.Ball.linearVelocity,b.Match.World.Ball.linearVelocity),1e-5);
                        for(int player=0;player<4;player++)
                        {
                            Assert.AreEqual(a.Match.World.Players[player].Position,b.Match.World.Players[player].Position);
                            Assert.AreEqual(a.Match.World.Players[player].Paddle.position,b.Match.World.Players[player].Paddle.position);
                            Assert.AreEqual(a.Match.World.Players[player].Paddle.rotation,b.Match.World.Players[player].Paddle.rotation);
                        }
                        a.Step();b.Step();Assert.IsFalse(b.Done,b.Outcome);Assert.IsNull(b.Match.Failure);
                    }
                }
                yield return null;
            }
            foreach(float invalid in new[]{float.NaN,float.PositiveInfinity,float.NegativeInfinity,-1,1})
                Assert.Throws<ArgumentOutOfRangeException>(()=>new PlayerContactDrillV3(1301328,0,"low-return",1,0,invalid));
            using(var d=new PlayerContactDrillV3(1301328,0,"low-return",1,0,0))
                Assert.Throws<InvalidOperationException>(()=>d.Match.InitializeContactDrill(0,1301328,"low-return",1,0,-.2f));
        }
    }
}
