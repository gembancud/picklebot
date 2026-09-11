using System;
using NUnit.Framework;
using UnityEngine;

namespace Picklebot.PlayerControls.Tests
{
    public sealed class PlayerControlWorldTests
    {
        [Test] public void InvalidFourthCommandCannotAdvanceTheOtherPlayers()
        {
            var world=new PlayerControlWorld();var before=world.StateFor(0);
            var commands=new PlayerControlCommand[4];commands[0].jump=true;commands[3].crouch=float.NaN;
            Assert.Throws<ArgumentException>(()=>world.Step(commands,1f/240));
            Assert.AreEqual(before.position,world.StateFor(0).position);
            Assert.AreEqual(before.energy,world.StateFor(0).energy);
            commands[3].crouch=0;world.Step(commands,1f/240);
            Assert.IsFalse(world.StateFor(0).grounded,"Rejected input must not consume the jump edge.");
        }
        [Test] public void FourMotorsRetainPrivateEnergyAndResolveRepeatedContacts()
        {
            var world=new PlayerControlWorld();var commands=new PlayerControlCommand[4];
            commands[0]=new PlayerControlCommand{move=Vector2.right,sprint=true};
            commands[1]=new PlayerControlCommand{move=Vector2.left,sprint=true};
            commands[2].facingYaw=commands[3].facingYaw=180;
            bool touched=false;
            for(int i=0;i<2400;i++)
            {
                world.Step(commands,1f/240);
                touched|=world.LastContacts.events>0;
                Assert.GreaterOrEqual(Vector3.Distance(world.StateFor(0).position,world.StateFor(1).position),.56f-1e-5f);
            }
            Assert.IsTrue(touched);Assert.Less(world.StateFor(0).energy,1);
            Assert.AreEqual(1,world.StateFor(2).energy);Assert.AreEqual(1,world.StateFor(3).energy);
        }
        [Test] public void ResetReproducesTheSameTrajectory()
        {
            var world=new PlayerControlWorld();var commands=new PlayerControlCommand[4];
            commands[0]=new PlayerControlCommand{move=Vector2.up,jump=true,sprint=true};
            for(int i=0;i<100;i++)world.Step(commands,1f/240);
            var expected=world.StateFor(0);world.Reset();
            for(int i=0;i<100;i++)world.Step(commands,1f/240);
            Assert.AreEqual(expected.position,world.StateFor(0).position);
            Assert.AreEqual(expected.velocity,world.StateFor(0).velocity);
            Assert.AreEqual(expected.energy,world.StateFor(0).energy);
        }
    }
}
