using System.Linq;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.Match.Tests
{
    public sealed class MatchPhysicsTests
    {
        [TestCase(860000)] [TestCase(860001)] public void BothSidesMakePhysicalLegalReturns(int seed)
        {
            using var m=new PickleballMatch(false);m.Reset(seed);var p=new ShotPolicy();
            for(int i=0;i<1200&&!m.Finished;i++)m.Step(p,p);
            Assert.That(m.World.Contacts.Any(c=>c.surface=="PaddleNear"),Is.True);
            Assert.That(m.World.Contacts.Any(c=>c.surface=="PaddleFar"),Is.True);
            Assert.That(m.World.Rules.Returns,Is.GreaterThanOrEqualTo(1));
            Assert.That(m.Decisions.Count,Is.GreaterThanOrEqualTo(2));
            Assert.That(m.Travel[0],Is.GreaterThan(.5f));Assert.That(m.Travel[1],Is.GreaterThan(.5f));
        }
        [Test] public void StationaryPaddlesDoNotReturnTheServe()
        {
            using var m=new PickleballMatch(false);var p=new ShotPolicy();while(!m.Finished)m.Step(p,p,stationary:true);
            Assert.That(m.World.Contacts.Any(c=>c.surface=="PaddleNear"||c.surface=="PaddleFar"),Is.False);Assert.That(m.Winner,Is.Not.Zero);
        }
        [Test] public void ResetRepeatsTheSameDecisionAndPhysicsTrace()
        {
            using var m=new PickleballMatch(false);var p=new ShotPolicy();
            for(int i=0;i<700;i++)m.Step(p,p,true);var position=m.World.Ball.position;int action=m.Decisions[0].action;
            m.Reset(860000);for(int i=0;i<700;i++)m.Step(p,p,true);
            Assert.That(Vector3.Distance(position,m.World.Ball.position),Is.LessThan(.001));Assert.That(m.Decisions[0].action,Is.EqualTo(action));
        }
    }
}
