using NUnit.Framework;
using UnityEngine;
namespace Picklebot.Inspection.Tests
{
    public sealed class InspectionRulesTests
    {
        private static InspectionRules Start() { var r=new InspectionRules();r.BeginServe(-1,1);return r; }
        private static InspectionRules Live()
        {
            var r=Start();r.Bounce(new Vector3(-1,0,4));r.Hit(1,false);r.Bounce(new Vector3(1,0,-4));return r;
        }
        [Test] public void ServeMustLandAcrossNetNotOnOwnSide() {var r=Start();r.Bounce(new Vector3(1,0,-4));Assert.That(r.Winner,Is.EqualTo(1));}
        [TestCase(1f,4f)] [TestCase(-1f,2.1336f)]
        public void ServeRejectsWrongDiagonalAndKitchenLine(float x,float z) {var r=Start();r.Bounce(new Vector3(x,0,z));Assert.That(r.Winner,Is.EqualTo(1));}
        [Test] public void ServeAcceptsCentreServiceLine() {var r=Start();r.Bounce(new Vector3(0,0,4));Assert.That(r.Finished,Is.False);}
        [Test] public void VolleyBeforeServeBounceIsFault() {var r=Start();r.Hit(1,false);Assert.That(r.Winner,Is.EqualTo(-1));}
        [Test] public void ServerMustLetReturnBounce() {var r=Start();r.Bounce(new Vector3(-1,0,4));r.Hit(1,false);r.Hit(-1,false);Assert.That(r.Winner,Is.EqualTo(1));}
        [Test] public void VolleysAllowedAfterInitialTwoBounces() {var r=Live();r.Hit(-1,false);r.Hit(1,false);Assert.That(r.Finished,Is.False);Assert.That(r.CanVolley,Is.True);}
        [Test] public void KitchenVolleyFaultButGroundstrokeAllowed()
        {
            var r=Live();r.Hit(-1,true);Assert.That(r.Finished,Is.False);r.Hit(1,true);Assert.That(r.Winner,Is.EqualTo(-1));
        }
        [Test] public void SecondBounceLosesForReceiver() {var r=Live();r.Bounce(new Vector3(1,0,-4));Assert.That(r.Winner,Is.EqualTo(1));}
        [Test] public void OutBeforeLandingLosesForHitter() {var r=Live();r.Hit(-1,false);r.Bounce(new Vector3(4,0,4));Assert.That(r.Winner,Is.EqualTo(1));}
        [Test] public void MarkerMomentumCanFaultAfterBallDies()
        {
            var r=Live();r.Hit(-1,false);r.Hit(1,false);r.Bounce(new Vector3(1,0,-4));r.Lost();
            Assert.That(r.Winner,Is.EqualTo(1));r.ObservePlayer(1,true,false,.01f);Assert.That(r.Winner,Is.EqualTo(-1));
        }
        [Test] public void MarkerRestClearsMomentumLatch()
        {
            var r=Live();r.Hit(-1,false);r.Hit(1,false);r.ObservePlayer(1,false,true,.21f);r.ObservePlayer(1,true,false,.01f);Assert.That(r.Finished,Is.False);
        }
    }
}
