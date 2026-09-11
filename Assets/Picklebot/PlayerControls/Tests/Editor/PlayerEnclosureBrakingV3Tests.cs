using NUnit.Framework;
using UnityEngine;

namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerEnclosureBrakingV3Tests
    {
        [Test] public void InteriorDoesNotChangeRequestedMotion()
        {
            var old = new Vector2(.2f, .3f); var wanted = old + new Vector2(.02f, -.01f);
            Assert.AreEqual(wanted, PlayerEnclosureBrakingV3.Constrain(new Vector2(0, 3), old, wanted, 1, 14, 1f/240));
        }

        [TestCase(-1)] [TestCase(1)]
        public void DiagonalWallApproachBrakesWithinTotalEffortAndPreservesSliding(int side)
        {
            const float dt=1f/240; var position=new Vector2(3.9f,7.8f*side);var velocity=Vector2.zero;
            for(int tick=0;tick<2400;tick++)
            {
                var requested=Vector2.MoveTowards(velocity,new Vector2(3,3*side),14*dt);
                var next=PlayerEnclosureBrakingV3.Constrain(position,velocity,requested,side,14,dt);
                Assert.LessOrEqual((next-velocity).magnitude,14*dt+1e-5f);
                position+=next*dt;velocity=next;
                Assert.LessOrEqual(position.x,4.200001f);Assert.LessOrEqual(position.y*side,8.100001f);
            }
            Assert.That(position.x,Is.EqualTo(4.2f).Within(.001f));
            Assert.That(position.y*side,Is.EqualTo(8.1f).Within(.001f));
            var slide=PlayerEnclosureBrakingV3.Constrain(new Vector2(4.2f,3*side),new Vector2(0,1),new Vector2(.01f,1),side,14,dt);
            Assert.AreEqual(new Vector2(0,1),slide);
        }

        [TestCase(-1)] [TestCase(1)]
        public void ArticulatedPlayerCanKeepRequestingMotionIntoBackWall(int side)
        {
            var positions=new[]{new Vector3(-1.5f,0,-6),new Vector3(1.5f,0,-6),new Vector3(-1.5f,0,6),new Vector3(1.5f,0,6)};
            int seat=side<0?0:2;positions[seat].z=7.9f*side;
            var world=new PlayerControlWorldV3(positions);var actions=new PlayerActionV3[4];
            var command=new float[18];command[1]=-1;actions[seat]=new PlayerActionV3(command);
            var old=world.StateFor(seat);var previousPaddle=Vector3.zero;
            for(int tick=0;tick<1200;tick++)
            {
                Assert.IsTrue(world.TryStep(actions),"Rejected player "+world.RejectedPlayer+" at "+tick);
                var state=world.StateFor(seat);var paddle=world.UpperFor(seat).ActualVelocity;
                Assert.LessOrEqual((state.velocity-old.velocity).magnitude,14f/240+1e-5f);
                Assert.LessOrEqual((paddle-previousPaddle).magnitude,100f/240+1e-5f);
                Assert.LessOrEqual(paddle.magnitude,12);
                Assert.LessOrEqual(state.position.z*side,8.100001f);
                old=state;previousPaddle=paddle;
            }
            Assert.That(old.position.z*side,Is.EqualTo(8.1f).Within(.001f));
        }
    }
}
