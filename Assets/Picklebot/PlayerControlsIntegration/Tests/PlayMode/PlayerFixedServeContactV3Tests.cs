using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerFixedServeContactV3Tests
    {
        private sealed class Idle:IPlayerPolicyV3
        {
            public string Name=>"physics fixture only";
            public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 o,System.Random r)=>default;
        }
        private static void Setup(PlayerContactDrillV3 d)
        {
            d.Match.AttachPolicies(new IPlayerPolicyV3[]{new Idle(),new Idle(),new Idle(),new Idle()},d.Seed);
            var paddle=d.Match.World.Players[d.Player].Paddle;var ball=d.Match.World.Ball;var normal=paddle.rotation*Vector3.forward;
            // Isolate real collision accounting. Never fed to the trainer.
            ball.position=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint+normal*.06f;
            ball.transform.position=ball.position;ball.linearVelocity=-normal*3;
        }
        [UnityTest]
        public IEnumerator ContactStagePreservesServePhysicsAndDoesNotClaimLanding()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var contact=new PlayerContactDrillV3(1302126+seat,seat,"stationary-serve-contact"))
                using(var full=new PlayerContactDrillV3(1302126+seat,seat,"stationary-serve"))
                {
                    CollectionAssert.AreEqual(PlayerObservationV3.Capture(contact.Match,seat,0).ToArray(),PlayerObservationV3.Capture(full.Match,seat,0).ToArray());
                    Assert.IsFalse(PlayerContactDrillV3.ActionMask(seat,seat,contact.Task)[16]);
                    Setup(contact);Setup(full);
                    for(int tick=0;tick<30&&!contact.Done;tick++)
                    {
                        contact.Step();full.Step();
                        Assert.Less(Vector3.Distance(contact.Match.World.Ball.position,full.Match.World.Ball.position),1e-6);
                        Assert.Less(Vector3.Distance(contact.Match.World.Ball.linearVelocity,full.Match.World.Ball.linearVelocity),1e-6);
                    }
                    Assert.AreEqual("fixed_serve_contact",contact.Outcome);
                    Assert.GreaterOrEqual(contact.Reward,1);
                    Assert.IsTrue(contact.FaceContact&&contact.ServeAccepted);
                    Assert.IsFalse(contact.DropBounced);Assert.IsFalse(contact.Match.StationarySupportActive);
                    Assert.IsFalse(full.Done,"Full serve must still wait for the actual landing.");
                    Assert.IsTrue(full.Match.World.IsPaddleContactActive(seat));
                    Assert.AreEqual(-1,full.ServeDirectionRewardTick,"Direction reward waits for separation.");
                    Assert.AreEqual(contact.Reward,full.Reward,1e-6,"While contact is active, both drills receive only the contact incentive.");
                }
                yield return null;
            }
        }
    }
}
