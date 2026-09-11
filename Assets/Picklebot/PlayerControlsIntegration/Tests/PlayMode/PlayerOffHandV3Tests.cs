using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;

namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerOffHandV3Tests
    {
        [UnityTest]
        public IEnumerator OffHandLiftIsIndependentBoundedAndChangesActualDropHeight()
        {
            using (var match = new PlayerLearningMatchV3())
            {
                var paddle = match.World.Players[0].Paddle.position;
                float initialHeight = match.World.Ball.position.y;
                var data = new float[PlayerActionV3.Count]; data[17] = 1;
                var actions = new PlayerActionV3[4]; actions[0] = new PlayerActionV3(data);
                float previousRate = 0;
                for (int tick = 0; tick < 240; tick++)
                {
                    Assert.IsTrue(match.Step(actions));
                    float angle = match.Controls.OffHandAngleFor(0), rate = match.Controls.OffHandRateFor(0);
                    Assert.That(angle, Is.InRange(0f, 140f));
                    Assert.LessOrEqual(Mathf.Abs(rate), 180.001f);
                    Assert.LessOrEqual(Mathf.Abs(rate - previousRate), 900 * PlayerJointMotorV3.Dt + .001f);
                    previousRate = rate;
                    for (int i = 1; i < 4; i++) Assert.AreEqual(0, match.Controls.OffHandAngleFor(i));
                }
                Assert.Greater(match.World.Ball.position.y - initialHeight, .6f);
                Assert.Less(Vector3.Distance(paddle, match.World.Players[0].Paddle.position), .00001f);
                Assert.IsTrue(match.BallHeld);
                var observation = PlayerObservationV3.Capture(match, 0, match.Tick).ToArray();
                Assert.AreEqual(124, observation.Length);
                Assert.AreEqual(match.Controls.OffHandAngleFor(0) / 140, observation[121]);
                Assert.AreEqual(match.Controls.OffHandRateFor(0) / 180, observation[122]);
                Assert.AreEqual(1, observation[123]);
                data[16] = 1; actions[0] = new PlayerActionV3(data);
                Assert.IsTrue(match.Step(actions));
                Assert.IsFalse(match.BallHeld);
                Assert.IsEmpty(match.World.Contacts, "Release started in contact with the body.");
                Assert.Greater(match.ReleasePosition.Value.y, 1.6f);
                Assert.AreEqual(0, match.World.Ball.linearVelocity.x);
                Assert.AreEqual(0, match.World.Ball.linearVelocity.z);
            }
            yield return null;
        }

        [UnityTest]
        public IEnumerator FixedGripAttachmentClearsTheArmAcrossItsLiftRange()
        {
            foreach(float lift in new[]{0f,.25f,.5f,.75f,1f})
            {
                using(var match=new PlayerLearningMatchV3())
                {
                    var data=new float[PlayerActionV3.Count];data[17]=lift;
                    var actions=new PlayerActionV3[4];actions[0]=new PlayerActionV3(data);
                    for(int tick=0;tick<300;tick++)Assert.IsTrue(match.Step(actions));
                    data[16]=1;actions[0]=new PlayerActionV3(data);
                    for(int tick=0;tick<4;tick++)Assert.IsTrue(match.Step(actions));
                    Assert.IsFalse(match.BallHeld);
                    Assert.IsEmpty(match.World.Contacts,"Grip attachment intersects the arm at lift "+lift);
                }
                yield return null;
            }
        }

        [UnityTest]
        public IEnumerator FailedBodyStepDoesNotAdvanceAnyOffHandMotor()
        {
            using (var match = new PlayerLearningMatchV3())
            {
                var actions = new PlayerActionV3[4];
                var lift = new float[PlayerActionV3.Count]; lift[17] = 1;
                var jump = new float[PlayerActionV3.Count]; jump[4] = 1;
                actions[0] = new PlayerActionV3(lift); actions[3] = new PlayerActionV3(jump);
                Assert.IsFalse(match.Step(actions));
                Assert.AreEqual(0, match.Tick);
                for (int i = 0; i < 4; i++)
                {
                    Assert.AreEqual(0, match.Controls.OffHandAngleFor(i));
                    Assert.AreEqual(0, match.Controls.OffHandRateFor(i));
                }
            }
            yield return null;
        }
    }
}
