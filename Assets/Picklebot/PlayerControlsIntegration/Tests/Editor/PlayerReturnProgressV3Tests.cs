using NUnit.Framework;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerReturnProgressV3Tests
    {
        [Test] public void RepeatedCrossingsCannotFarmProgressOrRewardBackwardFlight()
        {
            var reward=new PlayerReturnProgressV3(-3);float total=0;
            Assert.AreEqual(0,reward.Advance(-4));Assert.AreEqual(0,reward.Advance(-3));
            for(int i=0;i<20;i++){total+=reward.Advance(-1);total+=reward.Advance(-3);}
            Assert.AreEqual(.125f,total,.00001f);
            total+=reward.Advance(1);total+=reward.Advance(100);
            Assert.AreEqual(PlayerReturnProgressV3.MaximumReward,total,.00001f);
            Assert.AreEqual(0,reward.Advance(-3));Assert.AreEqual(0,reward.Advance(1));
        }
        [Test] public void InvalidFlightDataFailsWithoutConsumingFutureReward()
        {
            var reward=new PlayerReturnProgressV3(-3);
            Assert.Throws<System.ArgumentException>(()=>reward.Advance(float.NaN));
            Assert.AreEqual(.25f,reward.Advance(1),.00001f);
        }
    }
}
