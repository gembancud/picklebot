using System;
using NUnit.Framework;
using UnityEngine;
namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerControlWorldV3Tests
    {
        private static PlayerControlWorldV3 World()=>new PlayerControlWorldV3(new[]{new Vector3(-1,0,-3),new Vector3(1,0,-3),new Vector3(-1,0,3),new Vector3(1,0,3)});
        [Test] public void DirectActionsOwnTheirDataAndRespectEveryJointRange()
        {
            foreach(float sign in new[]{-1f,0f,1f})
            {
                var data=new float[PlayerActionV3.Count];for(int i=0;i<PlayerActionV3.Count;i++)data[i]=sign;var action=new PlayerActionV3(data);data[9]=float.NaN;
                for(int i=0;i<7;i++)Assert.AreEqual(sign<0?PlayerArmJointsV3.Minimum(i):sign>0?PlayerArmJointsV3.Maximum(i):PlayerArmJointsV3.Ready[i],action.ArmTarget[i]);
            }
            Assert.AreEqual(PlayerActionV3.Count,PlayerActionV3.Fields.Length);
            Assert.Throws<ArgumentException>(()=>new PlayerActionV3(new float[15]));
        }
        [Test] public void IndependentBodiesMoveAndReturnedCopiesCannotMutateWorld()
        {
            var world=World();var actions=new PlayerActionV3[4];var data=new float[PlayerActionV3.Count];data[0]=.2f;data[6]=.2f;data[12]=.3f;actions[0]=new PlayerActionV3(data);
            var other=world.StateFor(1).position;var arm=world.UpperFor(1).ArmAngles.ToArray();
            for(int tick=0;tick<480;tick++)Assert.IsTrue(world.TryStep(actions),"Rejected player "+world.RejectedPlayer+" tick="+tick);
            Assert.Greater(world.StateFor(0).position.x,-.8f);Assert.AreEqual(other,world.StateFor(1).position);
            CollectionAssert.AreEqual(arm,world.UpperFor(1).ArmAngles.ToArray());
            var copy=world.UpperFor(1);Assert.IsTrue(copy.TryStep(new Vector3(10,0,0),PlayerArmJointsV3.Ready));
            Assert.AreEqual(Vector3.zero,world.UpperFor(1).TorsoAngles);
        }
        [Test] public void InfeasibleRootImpulseCannotPartiallyAdvanceAnyPlayer()
        {
            var world=World();var old=new PlayerControlState[4];for(int i=0;i<4;i++)old[i]=world.StateFor(i);
            var actions=new PlayerActionV3[4];var data=new float[PlayerActionV3.Count];data[4]=1;actions[3]=new PlayerActionV3(data);
            Assert.IsFalse(world.TryStep(actions));Assert.AreEqual(3,world.RejectedPlayer);
            for(int i=0;i<4;i++){Assert.AreEqual(old[i].position,world.StateFor(i).position);Assert.AreEqual(Vector3.zero,world.UpperFor(i).ActualVelocity);}
        }
    }
}
