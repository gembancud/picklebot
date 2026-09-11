using System;
using NUnit.Framework;
using UnityEngine;

namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerControlContactTests
    {
        private static Vector2[] Positions()=>new[]{new Vector2(-.3f,-3),new Vector2(.3f,-3),new Vector2(-1,3),new Vector2(1,3)};
        private static int[] Sides()=>new[]{-1,-1,1,1};
        [Test] public void HeadOnStopsAtContactWithoutOverlapOrMomentumCreation()
        {
            var p=Positions();var v=new[]{Vector2.right*3,Vector2.left*3,Vector2.zero,Vector2.zero};
            var r=PlayerControlContacts.Solve(p,v,Sides(),.05f);
            Assert.That(Vector2.Distance(r.positions[0],r.positions[1]),Is.EqualTo(.56f).Within(1e-5f));
            Assert.That((r.velocities[0]+r.velocities[1]).magnitude,Is.LessThan(1e-6f));
            Assert.That(r.velocities[0].magnitude,Is.LessThan(1e-6f));
            Assert.AreEqual(new Vector2(-.3f,-3),p[0]);Assert.AreEqual(Vector2.right*3,v[0]);
            Assert.That(r.contactDeltaVelocity[0].x,Is.EqualTo(-3).Within(1e-5f));
        }
        [Test] public void GlancingContactPreservesTangentialMotionAndDoesNotAddEnergy()
        {
            var v=new[]{new Vector2(3,1),new Vector2(-3,1),Vector2.zero,Vector2.zero};
            var r=PlayerControlContacts.Solve(Positions(),v,Sides(),.05f);
            Assert.That(r.velocities[0].y,Is.EqualTo(1).Within(1e-5f));
            Assert.That(r.velocities[1].y,Is.EqualTo(1).Within(1e-5f));
            Assert.LessOrEqual(r.velocities[0].sqrMagnitude+r.velocities[1].sqrMagnitude,v[0].sqrMagnitude+v[1].sqrMagnitude);
        }
        [Test] public void SafetyBoundsStopNormalMotionAndPreserveSliding()
        {
            var p=Positions();p[0]=new Vector2(-4.19f,-3);
            var v=new[]{new Vector2(-3,2),Vector2.zero,Vector2.zero,Vector2.zero};
            var r=PlayerControlContacts.Solve(p,v,Sides(),.05f);
            Assert.That(r.positions[0].x,Is.EqualTo(-4.2f).Within(1e-5f));
            Assert.That(r.positions[0].y,Is.EqualTo(-2.9f).Within(1e-5f));
            Assert.That(r.velocities[0].x,Is.EqualTo(0).Within(1e-5f));
            Assert.That(r.velocities[0].y,Is.EqualTo(2).Within(1e-5f));
        }
        [Test] public void SwappingSeatsDoesNotChangeIsolatedCollision()
        {
            var p=Positions();var v=new[]{new Vector2(3,1),new Vector2(-2,1),Vector2.zero,Vector2.zero};
            var a=PlayerControlContacts.Solve(p,v,Sides(),.05f);
            (p[0],p[1])=(p[1],p[0]);(v[0],v[1])=(v[1],v[0]);
            var b=PlayerControlContacts.Solve(p,v,Sides(),.05f);
            Assert.That(Vector2.Distance(a.positions[0],b.positions[1]),Is.LessThan(1e-5f));
            Assert.That(Vector2.Distance(a.velocities[0],b.velocities[1]),Is.LessThan(1e-5f));
        }
        [Test] public void RepeatedApproachAt240HzStaysSeparated()
        {
            var p=Positions();var v=new Vector2[4];
            for(int k=0;k<2400;k++)
            {
                v[0]=Vector2.MoveTowards(v[0],Vector2.right*3,14f/240);
                v[1]=Vector2.MoveTowards(v[1],Vector2.left*3,14f/240);
                var r=PlayerControlContacts.Solve(p,v,Sides(),1f/240);p=r.positions;v=r.velocities;
                Assert.GreaterOrEqual(Vector2.Distance(p[0],p[1]),.56f-1e-5f);
            }
        }
        [Test] public void InvalidAndOverlappingStatesAreRejected()
        {
            var p=Positions();p[1]=p[0];
            Assert.Throws<ArgumentException>(()=>PlayerControlContacts.Solve(p,new Vector2[4],Sides(),1f/240));
            p=Positions();p[0].x=float.NaN;
            Assert.Throws<ArgumentException>(()=>PlayerControlContacts.Solve(p,new Vector2[4],Sides(),1f/240));
        }
    }
}
