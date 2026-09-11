using System;
using System.Collections;
using System.Linq;
using NUnit.Framework;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;

namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerControlMatchTests
    {
        private static PlayerControlCommand[] Movement()=>new[]{new PlayerControlCommand(),new PlayerControlCommand(),new PlayerControlCommand{facingYaw=180},new PlayerControlCommand{facingYaw=180}};
        private static PlayerPaddleCommand[] Paddles()=>Enumerable.Repeat(PlayerPaddleCommand.Ready,4).ToArray();
        [UnityTest] public IEnumerator ActualBodiesAndPaddlesFollowTheSingleIntegratedController()
        {
            using(var match=new PlayerControlMatch(false))
            {
                var commands=Movement();var paddles=Paddles();
                for(int tick=0;tick<360;tick++)
                {
                    commands[1]=new PlayerControlCommand{move=Vector2.up*.25f,facingYaw=tick*.2f,crouch=tick<100?1:0,jump=tick==130,sprint=true};
                    match.Step(commands,paddles);
                    for(int i=0;i<4;i++)
                    {
                        var root=match.Controls.StateFor(i);var body=match.World.Players[i];var expected=match.Controls.PaddleFor(i);
                        Assert.That(Vector3.Distance(root.position,body.Position),Is.LessThan(1e-6f));
                        Assert.That(Vector3.Distance(expected.position,body.Paddle.position),Is.LessThan(1e-4f));
                        Assert.That(Vector3.Distance(body.Hand,body.Shoulder),Is.LessThanOrEqualTo(.6201f));
                        if(!root.grounded)Assert.IsFalse(body.BothFeetOutside);
                    }
                }
                Assert.That(match.World.Time,Is.EqualTo(1.5f).Within(.001f));
            }
            yield return null;
        }
        [UnityTest] public IEnumerator BallActuallyCollidesWithTheControlledPaddle()
        {
            using(var match=new PlayerControlMatch(false))
            {
                var body=match.World.Players[0];var face=body.Paddle.transform.Find("RoundedHittingFace");
                var normal=body.Paddle.rotation*Vector3.forward;
                var start=face.position+normal*.10f;
                match.World.Ball.position=start;match.World.Ball.transform.position=start;
                match.World.Ball.linearVelocity=-normal*3;match.World.Ball.angularVelocity=Vector3.zero;
                Physics.SyncTransforms();
                for(int i=0;i<16;i++)match.Step(Movement(),Paddles());
                Assert.IsTrue(match.World.Contacts.Any(c=>c.player==0&&c.surface=="RoundedHittingFace"),"Must observe real PhysX paddle contact.");
                Assert.Greater(Vector3.Dot(match.World.Ball.linearVelocity,normal),0,"Ball must rebound from the paddle.");
            }
            yield return null;
        }
        private sealed class SharedWeightProbe:IPlayerPolicyV2
        {
            private readonly float[] weights;
            public int calls;
            public string Name=>"untrained shared-weight integration probe";
            public SharedWeightProbe(float[] weights){this.weights=weights;}
            public void Reset(){calls=0;}
            public PlayerActionV2 Decide(PlayerObservationV2 observation,System.Random random)
            {calls++;var v=default(PlayerActionV2).ToArray();v[1]=weights[0];return new PlayerActionV2(v);}
        }
        [UnityTest] public IEnumerator FourIndependentPoliciesSharingWeightsDriveActualPlayers()
        {
            using(var match=new PlayerControlMatch(false))
            {
                var weights=new[]{.10f};var policies=Enumerable.Range(0,4).Select(i=>new SharedWeightProbe(weights)).ToArray();
                match.AttachPolicies(policies,1300000);int decisions=0;match.Decisions.Decided+=d=>decisions++;
                var start=Enumerable.Range(0,4).Select(i=>match.World.Players[i].Position).ToArray();
                for(int t=0;t<120;t++)match.StepAgents();
                Assert.AreEqual(40,decisions);Assert.AreEqual(120,match.Tick);
                for(int i=0;i<4;i++)
                {
                    Assert.AreEqual(10,policies[i].calls);
                    Assert.Greater(Vector3.Distance(start[i],match.World.Players[i].Position),.02f);
                    var observation=PlayerObservationV2.Capture(match,i,120,match.Decisions.ActionFor(i));
                    Assert.AreEqual(96,observation.values.Length);Assert.AreEqual(.1f,observation.values[82]);
                    Assert.AreEqual(match.World.Rules.EstablishedOutside(i)?1:0,observation.values[79]);
                    Assert.AreEqual(match.World.Rules.VolleyMomentumPending(i)?1:0,observation.values[80]);
                }
            }
            yield return null;
        }
        [UnityTest] public IEnumerator LegacyMotorCannotDoubleIntegrateAnExternallyDrivenBody()
        {
            using(var match=new PlayerControlMatch(false))
            {
                var body=match.World.Players[0];var position=body.Position;
                Assert.Throws<InvalidOperationException>(()=>body.Step(position,body.Paddle.position,body.Paddle.rotation,Vector3.zero,match.World.Players[1],DoublesWorld.Dt));
                Assert.AreEqual(position,body.Position);
                body.Reset(position);
                Assert.DoesNotThrow(()=>body.Step(position,body.Paddle.position,body.Paddle.rotation,Vector3.zero,match.World.Players[1],DoublesWorld.Dt));
                Assert.AreEqual(.9f,body.Torso.height);
            }
            yield return null;
        }
    }
}
