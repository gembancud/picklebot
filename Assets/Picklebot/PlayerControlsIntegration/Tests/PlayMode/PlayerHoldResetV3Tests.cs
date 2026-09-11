using System;
using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using Picklebot.PlayerControls;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerHoldResetV3Tests
    {
        [UnityTest]
        public IEnumerator ExplicitZeroPreservesDefaultObservationsAndTrajectory()
        {
            for(int seat=0;seat<4;seat++)using(var a=new PlayerLearningMatchV3(false,seat))using(var b=new PlayerLearningMatchV3(false,seat,0))
            {
                var actions=new PlayerActionV3[4];var command=new float[18];command[17]=.5f;actions[seat]=new PlayerActionV3(command);
                for(int tick=0;tick<120;tick++)
                {
                    for(int i=0;i<4;i++)CollectionAssert.AreEqual(PlayerObservationV3.Capture(a,i,tick).ToArray(),PlayerObservationV3.Capture(b,i,tick).ToArray());
                    Assert.IsTrue(a.Step(actions));Assert.IsTrue(b.Step(actions));
                }
            }
            yield return null;
        }
        [UnityTest]
        public IEnumerator RaisedHoldChangesOnlyServerOffHandAndStillRequiresOwnRelease()
        {
            for(int seat=0;seat<4;seat++)using(var normal=new PlayerLearningMatchV3(false,seat))using(var raised=new PlayerLearningMatchV3(false,seat,90))
            {
                Assert.AreEqual(0,raised.Tick);Assert.IsTrue(raised.BallHeld);
                Assert.AreEqual(1.63f,raised.World.Ball.position.y,1e-5f);
                for(int i=0;i<4;i++)
                {
                    Assert.AreEqual(i==seat?90:0,raised.Controls.OffHandAngleFor(i));Assert.AreEqual(0,raised.Controls.OffHandRateFor(i));
                    Assert.AreEqual(normal.Controls.StateFor(i).position,raised.Controls.StateFor(i).position);
                    Assert.AreEqual(normal.World.Players[i].Paddle.position,raised.World.Players[i].Paddle.position);
                    Assert.AreEqual(normal.World.Players[i].Paddle.rotation,raised.World.Players[i].Paddle.rotation);
                }
                var obs=PlayerObservationV3.Capture(raised,seat,0).ToArray();Assert.AreEqual(90f/140,obs[121],1e-6f);Assert.AreEqual(1,obs[120]);
                var actions=new PlayerActionV3[4];var wrong=new float[18];wrong[16]=1;actions[seat^1]=new PlayerActionV3(wrong);
                for(int tick=0;tick<24;tick++){Assert.IsTrue(raised.Step(actions));Assert.IsTrue(raised.BallHeld);}
                Assert.Less(raised.Controls.OffHandAngleFor(seat),90,"The initial pose must not lock the motor against subsequent actions.");
                actions[seat]=new PlayerActionV3(wrong);Assert.IsTrue(raised.Step(actions));Assert.IsFalse(raised.BallHeld);
                Assert.AreEqual(0,raised.World.Ball.linearVelocity.x);Assert.AreEqual(0,raised.World.Ball.linearVelocity.z);Assert.Less(raised.World.Ball.linearVelocity.y,0);
            }
            yield return null;
        }
        [Test]
        public void InvalidHoldResetsAreRejectedBeforeCreatingAMatch()
        {
            foreach(float value in new[]{-1f,141f,float.NaN,float.PositiveInfinity})
                Assert.Throws<ArgumentOutOfRangeException>(()=>new PlayerContactDrillV3(1301912,0,"drop-contact",initialHoldLift:value));
            Assert.Throws<ArgumentOutOfRangeException>(()=>new PlayerContactDrillV3(1301912,0,"low-return",initialHoldLift:90));
            Assert.Throws<ArgumentException>(()=>new PlayerLearningMatchV3(false,0,float.NaN));
        }
    }
}
