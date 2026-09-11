using System;
using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerDropContactV3Tests
    {
        private sealed class Policy:IPlayerPolicyV3
        {
            public PlayerActionV3 action;
            public string Name=>"test-only feasibility command";
            public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)=>action;
        }
        private static IPlayerPolicyV3[] Policies(int seat,PlayerActionV3 action)
        {
            var policies=new IPlayerPolicyV3[4];
            for(int i=0;i<4;i++)policies[i]=new Policy{action=i==seat?action:default};
            return policies;
        }
        private static float ApproachScore(params float[] distances)
        {
            var reward=new PlayerDropApproachV3(distances[0]);float total=0;
            foreach(float distance in distances)total+=reward.Advance(distance);
            return total;
        }
        [Test]
        public void CloserApproachMustNotLoseToStartingFartherAway()
        {
            float closer=ApproachScore(.4f,.3f),farther=ApproachScore(1.5f,1);
            Assert.Greater(closer,farther,"A .3m closest approach must outrank a 1m near miss, regardless of bounce-start distance.");
            Assert.AreEqual(ApproachScore(1.5f,.3f),closer,1e-6,"Identical closest distance must not gain reward from starting farther away.");
            Assert.AreEqual(PlayerDropApproachV3.MaximumReward,ApproachScore(0),1e-6,"An initially close measurement must not lose proximity credit.");
        }
        [Test]
        public void ApproachCannotPayAgainForRetreatOrExceedItsBudget()
        {
            var reward=new PlayerDropApproachV3(3);
            float total=reward.Advance(1);
            for(int i=0;i<20;i++)
            {
                Assert.AreEqual(0,reward.Advance(3));
                Assert.AreEqual(0,reward.Advance(1));
            }
            total+=reward.Advance(0);
            Assert.AreEqual(PlayerDropApproachV3.MaximumReward,total,1e-6);
            Assert.AreEqual(0,reward.Advance(0));
            Assert.Throws<ArgumentOutOfRangeException>(()=>reward.Advance(float.NaN));
            Assert.Throws<ArgumentOutOfRangeException>(()=>reward.Advance(-1));
        }
        [UnityTest]
        public IEnumerator ContactMilestoneUsesTheSamePhysicsAndDoesNotClaimALegalLanding()
        {
            // Offline feasibility input only; never supplied to the training policy.
            var action=new PlayerActionV3(new float[]{0,0,0,.5f,0,0,-.254720449f,1,1,
                -.134723678f,.24835f,-.965271354f,-.805382f,-.722499f,-.147358075f,-.447676748f,1,0});
            for(int seat=0;seat<4;seat++)
            {
                using(var contact=new PlayerContactDrillV3(1301090+seat,seat,"drop-contact"))
                using(var serve=new PlayerContactDrillV3(1301090+seat,seat,"drop-serve"))
                {
                    contact.Match.AttachPolicies(Policies(seat,action),contact.Seed);
                    serve.Match.AttachPolicies(Policies(seat,action),serve.Seed);
                    while(!contact.Done)
                    {
                        contact.Step();serve.Step();
                        Assert.IsNull(contact.Match.Failure);
                        Assert.Less(Vector3.Distance(contact.Match.World.Ball.position,serve.Match.World.Ball.position),1e-5);
                        Assert.Less(Vector3.Distance(contact.Match.World.Players[seat].Paddle.position,serve.Match.World.Players[seat].Paddle.position),1e-5);
                        if(!contact.DropBounced)Assert.AreEqual(contact.Match.Tick==7?.05f:0,contact.Reward,1e-6,"No pre-bounce approach bonus");
                    }
                    Assert.AreEqual("serve_contact",contact.Outcome);
                    Assert.IsTrue(contact.DropBounced&&contact.ServeAccepted&&contact.FaceContact);
                    Assert.AreEqual(7,contact.ReleaseTick);
                    Assert.IsFalse(serve.Done,"Landing evaluation must continue beyond the contact milestone");
                    while(!serve.Done)serve.Step();
                    Assert.AreEqual("bad_return",serve.Outcome);
                }
                yield return null;
            }
        }
        [UnityTest]
        public IEnumerator HoldingTheBallCannotEarnApproachOrContactSuccess()
        {
            using(var drill=new PlayerContactDrillV3(1301094,0,"drop-contact"))
            {
                drill.Match.AttachPolicies(Policies(0,default),drill.Seed);
                float total=0;
                while(!drill.Done){drill.Step();total+=drill.Reward;}
                Assert.AreEqual("time_limit",drill.Outcome);Assert.AreEqual(-1,total);
                Assert.IsFalse(drill.Released||drill.DropBounced||drill.FaceContact||drill.ServeAccepted);
                Assert.AreEqual(1200,drill.Match.Tick);
            }
            yield return null;
        }
    }
}
