using System;
using NUnit.Framework;
using UnityEngine;
using Picklebot.PlayerControlsIntegration;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerPrecontactPotentialV3Tests
    {
        private static readonly Vector3 Size=new Vector3(.2032f,.2794f,.016f);
        private static float P(Vector3 ball,Vector3 origin,Quaternion rotation)=>PlayerPrecontactPotentialV3.Measure(ball,origin,rotation,Size,.0254f,.037f);
        [Test] public void BothBroadApproachPatchesAreZeroAndEdgesHaveError()
        {
            Assert.That(P(new Vector3(0,0,.045f),Vector3.zero,Quaternion.identity),Is.EqualTo(0).Within(1e-7));
            Assert.That(P(new Vector3(0,0,-.045f),Vector3.zero,Quaternion.identity),Is.EqualTo(0).Within(1e-7));
            Assert.That(P(new Vector3(.2f,0,.045f),Vector3.zero,Quaternion.identity),Is.LessThan(0));
            Assert.That(P(new Vector3(0,.2f,.045f),Vector3.zero,Quaternion.identity),Is.LessThan(0));
        }
        [Test] public void GeometryIsInvariantToWorldFrame()
        {
            var v=new Vector3(.2f,-.3f,.13f);var q=Quaternion.Euler(31,172,-43);var origin=new Vector3(2,1,-4);
            Assert.That(P(origin+q*v,origin,q),Is.EqualTo(P(v,Vector3.zero,Quaternion.identity)).Within(2e-7));
        }
        [Test] public void InvalidGeometryCannotBecomeAReward()
        {
            Assert.Throws<ArgumentException>(()=>P(new Vector3(float.NaN,0,0),Vector3.zero,Quaternion.identity));
            Assert.Throws<ArgumentException>(()=>P(Vector3.zero,Vector3.zero,new Quaternion(0,0,0,0)));
        }
        [TestCase(1)] [TestCase(6)] [TestCase(12)]
        public void PartialOrFullFinalIntervalTelescopes(int finalTicks)
        {
            foreach(var path in new[]{new[]{-.25f},new[]{-.25f,-.1f,-.2f,-.01f},new[]{-.1f,0f,0f,0f},new[]{-.1f,-.24f,-.25f}})
            {
                var tracker=new PlayerPrecontactPotentialV3(path[0],.99f);double sum=0;int transition=0;
                for(int i=1;i<path.Length;i++)sum+=Math.Pow(.99f,transition++)*tracker.AtDecision(i*12,path[i]);
                sum+=Math.Pow(.99f,transition)*tracker.AtTerminal((path.Length-1)*12+finalTicks);
                Assert.That(sum,Is.EqualTo(-path[0]).Within(1e-7));
                Assert.That(tracker.DiscountedReward,Is.EqualTo(sum).Within(1e-8));
                Assert.AreEqual(path.Length,tracker.Transitions);Assert.IsTrue(tracker.Settled);
            }
        }
        [Test] public void WrongClockGammaAndDoubleSettlementAreRejected()
        {
            Assert.Throws<ArgumentException>(()=>new PlayerPrecontactPotentialV3(-.1f,.95f));
            var tracker=new PlayerPrecontactPotentialV3(-.1f,.99f);
            Assert.Throws<InvalidOperationException>(()=>tracker.AtDecision(1,-.05f));
            Assert.Throws<InvalidOperationException>(()=>tracker.AtTerminal(13));
            tracker.AtTerminal(4);
            Assert.Throws<InvalidOperationException>(()=>tracker.AtTerminal(4));
            Assert.Throws<InvalidOperationException>(()=>tracker.AtDecision(12,0));
        }
    }
}
