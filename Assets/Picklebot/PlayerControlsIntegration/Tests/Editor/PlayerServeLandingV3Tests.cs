using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerServeLandingV3Tests
    {
        [Test] public void MeasuredDepthAndDiagonalDirectionImproveFeedback()
        {
            float R(float x,float z)=>PlayerServeLandingV3.ContactReward(new Vector3(x,0,z),0,-1);
            Assert.Less(R(-1,-5),R(-1,0));Assert.Less(R(-1,0),R(-1,2.11358762f));
            Assert.Less(R(-1,2.11358762f),R(-1,3));
            Assert.Less(R(1.47544742f,2.44100428f),R(-.8476763f,2.13924384f));
            Assert.Less(R(-4,4),R(-1,4));Assert.Less(R(-1,9),R(-1,4));
            Assert.AreEqual(.5f,R(-1,4),1e-6);
        }
        [Test] public void BothSidesAndCourtEndsHaveEquivalentRewards()
        {
            foreach(int server in new[]{0,1,2,3})foreach(float side in new[]{-1f,1f})
            {
                float zSign=server<2?1:-1;
                Assert.AreEqual(.5f,PlayerServeLandingV3.ContactReward(new Vector3(side,0,zSign*4),server,side),1e-6);
                float reference=PlayerServeLandingV3.ContactReward(new Vector3(-1,0,-3),0,-1);
                Assert.AreEqual(reference,PlayerServeLandingV3.ContactReward(new Vector3(side,0,zSign*-3),server,side),1e-6);
            }
        }
        [Test] public void FeedbackIsBoundedAndRejectsInvalidInput()
        {
            Assert.That(PlayerServeLandingV3.ContactReward(new Vector3(100,0,-100),0,-1),Is.InRange(0,.5f));
            Assert.Throws<System.ArgumentException>(()=>PlayerServeLandingV3.ContactReward(new Vector3(float.NaN,0,0),0,-1));
            Assert.Throws<System.ArgumentException>(()=>PlayerServeLandingV3.ContactReward(Vector3.zero,0,0));
            Assert.Throws<System.ArgumentOutOfRangeException>(()=>PlayerServeLandingV3.ContactReward(Vector3.zero,4,-1));
        }
    }
}
