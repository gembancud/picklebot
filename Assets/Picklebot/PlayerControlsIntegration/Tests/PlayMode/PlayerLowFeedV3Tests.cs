using System;
using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerLowFeedV3Tests
    {
        private sealed class Still:IPlayerPolicyV3
        {
            public string Name=>"stationary endpoint fixture";
            public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)=>default;
        }
        private static void Attach(PlayerContactDrillV3 d)
            =>d.Match.AttachPolicies(new IPlayerPolicyV3[]{new Still(),new Still(),new Still(),new Still()},d.Seed);
        [UnityTest]
        public IEnumerator ZeroLoweringExactlyPreservesEasyTrajectoryRewardsAndOutcomes()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var easy=new PlayerContactDrillV3(1301130+seat,seat,"easy-return"))
                using(var low=new PlayerContactDrillV3(1301130+seat,seat,"low-return",1,0))
                {
                    Attach(easy);Attach(low);
                    while(!easy.Done)
                    {
                        easy.Step();low.Step();
                        Assert.AreEqual(easy.Match.World.Ball.position,low.Match.World.Ball.position);
                        Assert.AreEqual(easy.Match.World.Ball.linearVelocity,low.Match.World.Ball.linearVelocity);
                        Assert.AreEqual(easy.Reward,low.Reward);Assert.AreEqual(easy.Done,low.Done);
                        Assert.AreEqual(easy.FaceContactBallHeight,low.FaceContactBallHeight);
                        Assert.IsNull(low.Match.Failure);
                    }
                    Assert.AreEqual(easy.Outcome,low.Outcome);Assert.AreEqual(easy.Match.Tick,low.Match.Tick);
                }
                yield return null;
            }
        }
        [UnityTest]
        public IEnumerator LoweringTranslatesTheFeedWithoutMovingTheBodyOrChangingFlightPhysics()
        {
            foreach(float lowering in new[]{.1f,.2f,.4f,.8f,.9f})
            for(int seat=0;seat<4;seat++)
            {
                int seed=1301140+seat;
                using(var easy=new PlayerContactDrillV3(seed,seat,"easy-return"))
                using(var low=new PlayerContactDrillV3(seed,seat,"low-return",1,lowering))
                {
                    Assert.AreEqual(lowering,low.FeedLowering);Assert.AreEqual(0,low.FeedDifficulty);
                    Assert.IsFalse(PlayerContactDrillV3.ActionMask(seat,seat,"low-return")[16]);
                    Attach(easy);Attach(low);
                    for(int tick=0;tick<24;tick++)
                    {
                        var offset=easy.Match.World.Ball.position-low.Match.World.Ball.position;
                        Assert.Less(Vector3.Distance(Vector3.up*lowering,offset),1e-5);
                        Assert.Less(Vector3.Distance(easy.Match.World.Ball.linearVelocity,low.Match.World.Ball.linearVelocity),1e-5);
                        for(int player=0;player<4;player++)Assert.AreEqual(easy.Match.World.Players[player].Paddle.position,low.Match.World.Players[player].Paddle.position);
                        easy.Step();low.Step();Assert.IsFalse(low.Done,low.Outcome);
                        Assert.IsFalse(low.FaceContact);Assert.IsNull(low.Match.Failure);
                    }
                }
                yield return null;
            }
            Assert.Throws<ArgumentOutOfRangeException>(()=>new PlayerContactDrillV3(1301144,0,"low-return",1,-.1f));
            Assert.Throws<ArgumentOutOfRangeException>(()=>new PlayerContactDrillV3(1301144,0,"low-return",1,float.NaN));
            Assert.Throws<ArgumentOutOfRangeException>(()=>new PlayerContactDrillV3(1301144,0,"low-return",1,1));
        }
    }
}
