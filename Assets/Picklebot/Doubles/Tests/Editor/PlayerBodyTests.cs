using NUnit.Framework;
using UnityEngine;
namespace Picklebot.Doubles.Tests
{
    public sealed class PlayerBodyTests
    {
        [Test] public void ElbowMaintainsSegmentLengths()
        {
            var root=new Vector3(0,1,0);var hand=new Vector3(.3f,.8f,.3f);
            var elbow=PlayerBody.Bend(root,hand,Vector3.left,.32f,.31f);
            Assert.That(Vector3.Distance(root,elbow),Is.EqualTo(.32f).Within(.0001));
            Assert.That(Vector3.Distance(elbow,hand),Is.EqualTo(.31f).Within(.0001));
        }
        [Test] public void CollinearHintDoesNotProduceInvalidPose()
        {var elbow=PlayerBody.Bend(Vector3.zero,Vector3.down*.5f,Vector3.down,.32f,.31f);Assert.That(float.IsFinite(elbow.x));Assert.That(elbow.magnitude,Is.EqualTo(.32f).Within(.0001));}
        [Test] public void ShoeOverKitchenLineCountsAsContact()
        {Assert.That(PlayerBody.FootInKitchen(new Vector3(0,.055f,DoublesRules.Kitchen+.1f)));}
        [Test] public void AirborneFootIsNotGroundContact()
        {Assert.That(PlayerBody.FootInKitchen(new Vector3(0,.2f,1)),Is.False);}
    }
}
