using NUnit.Framework;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerServeDirectionV3Tests
    {
        [Test] public void ForwardMotionOutranksBackwardAndVerticalMotion()
        {
            Assert.Less(PlayerServeDirectionV3.ContactReward(-1),0);
            Assert.AreEqual(0,PlayerServeDirectionV3.ContactReward(0));
            Assert.Greater(PlayerServeDirectionV3.ContactReward(1),0);
            Assert.Greater(PlayerServeDirectionV3.ContactReward(3),PlayerServeDirectionV3.ContactReward(1));
        }
        [Test] public void MeasuredShortServeSpeedsRemainBelowRewardSaturation()
        {
            Assert.Less(PlayerServeDirectionV3.ContactReward(4),PlayerServeDirectionV3.ContactReward(5.26527548f));
            Assert.Less(PlayerServeDirectionV3.ContactReward(5.26527548f),PlayerServeDirectionV3.ContactReward(6));
            Assert.Less(PlayerServeDirectionV3.ContactReward(6),PlayerServeDirectionV3.ContactReward(8));
            Assert.AreEqual(PlayerServeDirectionV3.MaximumMagnitude,PlayerServeDirectionV3.ContactReward(8));
        }
        [Test] public void RewardIsBoundedAndRejectsInvalidMeasurements()
        {
            Assert.AreEqual(.5f,PlayerServeDirectionV3.ContactReward(100));
            Assert.AreEqual(-.5f,PlayerServeDirectionV3.ContactReward(-100));
            Assert.Throws<System.ArgumentException>(()=>PlayerServeDirectionV3.ContactReward(float.NaN));
            Assert.Throws<System.ArgumentException>(()=>PlayerServeDirectionV3.ContactReward(float.PositiveInfinity));
        }
    }
}
