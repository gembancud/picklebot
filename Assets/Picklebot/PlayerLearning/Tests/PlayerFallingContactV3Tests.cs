using NUnit.Framework;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
using UnityEngine;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerFallingContactV3Tests
    {
        [Test]
        public void AllSeatsStartAtRestAndFollowOrdinaryGravityImmediately()
        {
            for(int seat=0;seat<4;seat++)
            {
                using(var falling=new PlayerContactDrillV3(1302049+seat,seat,"falling-contact"))
                using(var reference=new PlayerContactDrillV3(1302049+seat,seat,"stationary-contact"))
                {
                    var ball=falling.Match.World.Ball;var other=reference.Match.World.Ball;
                    Assert.AreEqual(other.position,ball.position);Assert.AreEqual(Vector3.zero,ball.linearVelocity);
                    Assert.IsFalse(ball.isKinematic);Assert.IsTrue(ball.detectCollisions);
                    Assert.IsFalse(falling.Match.BallHeld);Assert.IsFalse(falling.Match.StationarySupportActive);
                    var start=ball.position;
                    var actions=new PlayerActionV3[4];
                    for(int tick=0;tick<12;tick++)
                    {
                        Assert.IsTrue(falling.Match.Step(actions));
                        reference.Match.World.Simulate(false);
                        Assert.Less(Vector3.Distance(other.position,ball.position),1e-6);
                        Assert.Less(Vector3.Distance(other.linearVelocity,ball.linearVelocity),1e-6);
                        Assert.IsFalse(falling.Match.StationarySupportActive);
                    }
                    Assert.Less(ball.position.y,start.y);Assert.Less(ball.linearVelocity.y,0);
                    Assert.AreEqual(0,falling.Match.World.Contacts.Count);
                    Assert.IsFalse(PlayerContactDrillV3.ActionMask(seat,seat,"falling-contact")[16]);
                }
            }
        }
    }
}
