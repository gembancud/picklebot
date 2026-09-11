using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerBodyBrakingV3Tests
    {
        private static Vector2[] Positions()=>new[]{new Vector2(-1,-3),new Vector2(1,-3),new Vector2(-1,3),new Vector2(1,3)};
        [Test] public void SeparatedAndTogetherMovingBodiesKeepTheirRequestedVelocity()
        {
            var p=Positions();var v=new[]{new Vector2(.2f,0),new Vector2(.2f,0),new Vector2(0,.1f),new Vector2(0,.1f)};
            CollectionAssert.AreEqual(v,PlayerBodyBrakingV3.Constrain(p,v,v,new[]{-1,-1,1,1},14,1f/240));
            p[1]=p[0]+Vector2.right*.5601f;
            CollectionAssert.AreEqual(v,PlayerBodyBrakingV3.Constrain(p,v,v,new[]{-1,-1,1,1},14,1f/240));
        }
        [Test] public void ApproachBrakesWithoutMovingStationaryPartner()
        {
            var positions=Positions();var world=new PlayerControlWorldV3(System.Array.ConvertAll(positions,p=>new Vector3(p.x,0,p.y)));
            var commands=new PlayerActionV3[4];var a=new float[18];a[0]=1;commands[0]=new PlayerActionV3(a);
            var previous=world.StateFor(0);var paddle=Vector3.zero;
            for(int tick=0;tick<2400;tick++)
            {
                Assert.IsTrue(world.TryStep(commands),"Rejected at "+tick);
                var next=world.StateFor(0);var velocity=world.UpperFor(0).ActualVelocity;
                Assert.AreEqual(new Vector3(1,0,-3),world.StateFor(1).position);
                Assert.LessOrEqual((next.velocity-previous.velocity).magnitude,14f/240+1e-5f);
                Assert.LessOrEqual((velocity-paddle).magnitude,100f/240+1e-5f);
                Assert.GreaterOrEqual(Vector3.Distance(next.position,world.StateFor(1).position),.56f-1e-5f);
                previous=next;paddle=velocity;
            }
            Assert.Greater(previous.position.x,.43f,"Must approach the partner, not freeze at a distance.");
        }
        [Test] public void GroundedContactFailureSequenceKeepsAllPhysicalBounds()
        {
            var world=new PlayerControlWorldV3(System.Array.ConvertAll(Positions(),p=>new Vector3(p.x,0,p.y)));
            var random=new System.Random(1301846);var commands=new PlayerActionV3[4];var previous=new PlayerControlState[4];var paddle=new Vector3[4];
            for(int i=0;i<4;i++)previous[i]=world.StateFor(i);
            for(int tick=0;tick<4800;tick++)
            {
                if(tick%12==0)for(int i=0;i<4;i++)
                {
                    var a=new float[18];for(int j=0;j<18;j++)a[j]=(float)(random.NextDouble()*2-1);
                    a[3]=(a[3]+1)*.5f;a[5]=(a[5]+1)*.5f;a[17]=(a[17]+1)*.5f;a[4]=a[16]=0;commands[i]=new PlayerActionV3(a);
                }
                Assert.IsTrue(world.TryStep(commands),"Rejected player "+world.RejectedPlayer+" tick "+tick);
                for(int i=0;i<4;i++)
                {
                    var next=world.StateFor(i);var upper=world.UpperFor(i);
                    Assert.LessOrEqual((next.velocity-previous[i].velocity).magnitude,14f/240+1e-5f);
                    Assert.LessOrEqual(upper.ActualVelocity.magnitude,12);
                    Assert.LessOrEqual((upper.ActualVelocity-paddle[i]).magnitude,100f/240+1e-5f);
                    for(int j=0;j<i;j++)Assert.GreaterOrEqual(Vector3.Distance(next.position,world.StateFor(j).position),.56f-1e-5f);
                    previous[i]=next;paddle[i]=upper.ActualVelocity;
                }
            }
        }
    }
}
