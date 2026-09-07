using System.IO;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.Competition.Tests
{
    public sealed class CompetitionPhysicsTests
    {
        private static DensePolicy Stroke()=>new DensePolicy(File.ReadAllText("Assets/Picklebot/Competition/Models/stroke.json"),"competitive-stroke-v1",10,6);
        [Test] public void PaddleIsSmallRelativeToCourt()
        {
            using var world=new CompetitiveWorld(Stroke(),false);
            Assert.That(world.Paddles[0].transform.localScale.x,Is.EqualTo(.18f).Within(.00001));
            Assert.That(world.Paddles[0].transform.localScale.y,Is.EqualTo(.20f).Within(.00001));
            Assert.That(world.Root.transform.Find("Table").localScale.x,Is.EqualTo(1.8f).Within(.00001));
        }
        [Test] public void CourtCollisionLosesEnergy()
        {
            using var world=new CompetitiveWorld(Stroke(),false);world.Reset(840000);
            world.Ball.position=new Vector3(0,1.025f,.6f);world.Ball.linearVelocity=Vector3.zero;Physics.SyncTransforms();
            bool rose=false;float apex=0;
            for(int i=0;i<400;i++)
            {
                world.StepFreePhysics();if(world.Ball.linearVelocity.y>0)rose=true;
                if(rose)apex=Mathf.Max(apex,world.Ball.position.y-CompetitiveWorld.Radius);
                if(rose&&world.Ball.linearVelocity.y<=0)break;
            }
            Assert.That(rose,Is.True);Assert.That(apex,Is.InRange(.68f,.77f));
        }
    }
}
