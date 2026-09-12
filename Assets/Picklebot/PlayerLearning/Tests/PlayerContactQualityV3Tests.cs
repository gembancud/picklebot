using NUnit.Framework;
using UnityEngine;
using Picklebot.Doubles;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerContactQualityV3Tests
    {
        [Test] public void BothBroadFacesAreEquivalentAndSideGrazeIsDistinct()
        {
            var q=Quaternion.Euler(31,-72,17);
            Assert.That(DoublesContact.MeasureFaceNormalAlignment(q*Vector3.forward,q*Vector3.forward),Is.EqualTo(1).Within(1e-6));
            Assert.That(DoublesContact.MeasureFaceNormalAlignment(q*Vector3.back,q*Vector3.forward),Is.EqualTo(1).Within(1e-6));
            Assert.That(DoublesContact.MeasureFaceNormalAlignment(q*Vector3.right,q*Vector3.forward),Is.LessThan(1e-6));
        }
        [Test] public void RecordedRightwardGrazeDiffersFromSuccessfulReference()
        {
            var face=new Vector3(.017f,.335f,-.942f);
            var graze=new Vector3(-.88676995f,-.430144f,-.169161543f);
            Assert.That(DoublesContact.MeasureFaceNormalAlignment(graze,face),Is.LessThan(.02));
            Assert.That(DoublesContact.MeasureFaceNormalAlignment(new Vector3(.16065459f,.198684514f,-.9668064f),new Vector3(.304f,.298f,-.905f)),Is.GreaterThan(.97));
        }
        [Test] public void MissingOrInvalidNormalStaysUnmeasured()
        {
            Assert.AreEqual(-1,new DoublesContact().faceNormalAlignment);
            Assert.AreEqual(-1,DoublesContact.MeasureFaceNormalAlignment(Vector3.zero,Vector3.forward));
            Assert.AreEqual(-1,DoublesContact.MeasureFaceNormalAlignment(Vector3.forward,Vector3.zero));
            Assert.AreEqual(-1,DoublesContact.MeasureFaceNormalAlignment(new Vector3(float.NaN,0,0),Vector3.forward));
        }
    }
}
