using System.IO;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.Doubles.Tests
{
    public sealed class DoublesPhysicsTests
    {
        [Test] public void FourBodiesUseRealSizePaddlesAndFixedGrips()
        {
            using var world=new DoublesWorld(false);Assert.That(world.Players.Length,Is.EqualTo(4));
            for(int i=0;i<4;i++)
            {
                var p=world.Players[i];Assert.That(p.Paddle.isKinematic);Assert.That(p.Root.GetComponentsInChildren<Collider>().Length,Is.GreaterThan(10));
                Assert.That(Vector3.Distance(p.Hand,p.Root.transform.Find("Right hand grip").position),Is.LessThan(.001));
            }
        }
        [Test] public void DropServeAndReturnUsePhysicalContacts()
        {
            using var m=new DoublesMatch(false);Assert.That(m.World.Ball.linearVelocity,Is.EqualTo(Vector3.zero));
            for(int i=0;i<1000&&!m.World.Rules.Dead&&m.World.Rules.Hits<2;i++)m.Step();
            Assert.That(m.World.Rules.Hits,Is.GreaterThanOrEqualTo(2),m.World.Rules.LastFault.ToString());Assert.That(m.World.ServeBounced);
        }
        [Test] public void LocalSimulationPreservesGlobalGravity()
        {var gravity=Physics.gravity;using(var m=new DoublesMatch(false))for(int i=0;i<300;i++)m.Step();Assert.That(Physics.gravity,Is.EqualTo(gravity));}
        [Test] public void PaddleHandReachRemainsBounded()
        {
            using var m=new DoublesMatch(false);
            for(int i=0;i<1400&&!m.World.Rules.Dead;i++)
            {
                m.Step();foreach(var p in m.World.Players)
                {Assert.That(Vector3.Distance(p.Shoulder,p.Hand),Is.LessThanOrEqualTo(PlayerBody.ArmUpper+PlayerBody.ArmLower+.003f));Assert.That(float.IsFinite(p.PaddleVelocity.x));}
            }
        }
        [Test] public void TeammatesRemainSeparated()
        {
            using var m=new DoublesMatch(false){CentreOnly=false};
            for(int i=0;i<1400&&!m.World.Rules.Dead;i++)
            {m.Step();for(int p=0;p<4;p+=2)Assert.That(Vector3.Distance(m.World.Players[p].Position,m.World.Players[p+1].Position),Is.GreaterThanOrEqualTo(PlayerBody.Radius*2-.001));}
        }
        [Test] public void SavedContactModelHasAllThreeSkills()
        {
            var model=ContactModel.Load(File.ReadAllText("Assets/Picklebot/Doubles/Models/contact.json"));
            Assert.That(model.trials,Is.GreaterThan(0));Assert.That(model.sourceHash,Is.Not.Empty);Assert.That(model.strokes.Length,Is.EqualTo(3));
        }
        [Test] public void PaddleCanRotateOnThreeAxesWithFixedHandGrip()
        {
            using var w=new DoublesWorld(false);var p=w.Players[0];var target=Quaternion.Euler(25,35,30);bool threeAxes=false;
            for(int i=0;i<100;i++)
            {
                p.Step(p.Position,p.Paddle.position,target,Vector3.zero,w.Players[1],DoublesWorld.Dt);w.Simulate();
                var a=p.AngularVelocity;threeAxes|=Mathf.Abs(a.x)>.1f&&Mathf.Abs(a.y)>.1f&&Mathf.Abs(a.z)>.1f;
                Assert.That(a.magnitude,Is.LessThanOrEqualTo(PlayerBody.AngularSpeed+.01f));
                Assert.That(Vector3.Distance(p.Hand,p.Root.transform.Find("Right hand grip").position),Is.LessThan(.001f));
            }
            Assert.That(threeAxes);Assert.That(Quaternion.Angle(p.Paddle.rotation,target),Is.LessThan(.2f));
        }
    }
}
