using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerSwingTrajectoryV2Tests
    {
        [Test] public void SwingRampReachesTheContactPointAtTheRequestedSpeed()
        {
            var velocity=new Vector3(1,3,5);float duration=velocity.magnitude/PlayerSwingTrajectoryV2.RampAcceleration;
            PlayerSwingTrajectoryV2.Sample(velocity,-duration,out var start,out var initial);
            Assert.AreEqual(Vector3.zero,initial);
            PlayerSwingTrajectoryV2.Sample(velocity,0,out var contact,out var feed);
            Assert.Less(contact.magnitude,1e-6f);Assert.AreEqual(velocity,feed);
            Assert.Less(Vector3.Distance(start,-.5f*velocity*duration),1e-6f);
            const float dt=.0001f;var previous=initial;
            for(float phase=-duration+dt;phase<0;phase+=dt)
            {
                PlayerSwingTrajectoryV2.Sample(velocity,phase,out var position,out var current);
                PlayerSwingTrajectoryV2.Sample(velocity,phase-dt,out var prior,out var unused);
                Assert.LessOrEqual((current-previous).magnitude/dt,80.02f);
                Assert.Less(Vector3.Distance((position-prior)/dt,(current+previous)*.5f),.002f);previous=current;
            }
        }
    }
}
