using System;
using System.Collections;
using NUnit.Framework;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerLearningMatchV3Tests
    {
        private sealed class Policy:IPlayerPolicyV3
        {
            public bool fail;public int calls,lastPlayer=-1;public string Name=>"ownership fixture";public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 o,System.Random r)
            {calls++;if(fail)throw new InvalidOperationException("inference fixture");lastPlayer=o.player;var data=new float[PlayerActionV3.Count];if(o.player==0)data[16]=1;return new PlayerActionV3(data);}
        }
        [UnityTest] public IEnumerator FourPrivateDecisionsUseVersionedObservationsAndDelayedLearnedRelease()
        {
            using(var match=new PlayerLearningMatchV3())
            {
                var p=new[]{new Policy(),new Policy(),new Policy(),new Policy()};match.AttachPolicies(p,1300000);
                Assert.AreEqual(PlayerObservationV3.Count,PlayerObservationV3.Fields.Length);
                for(int i=0;i<4;i++)
                {
                    var obs=PlayerObservationV3.Capture(match,i,0);var copy=obs.ToArray();copy[0]=float.NaN;
                    Assert.IsTrue(float.IsFinite(obs.ToArray()[0]));Assert.AreEqual(PlayerObservationV3.Count,copy.Length);
                }
                for(int tick=0;tick<6;tick++){Assert.IsTrue(match.StepAgents());Assert.IsTrue(match.BallHeld);}
                Assert.IsTrue(match.StepAgents());Assert.IsFalse(match.BallHeld);
                Assert.Less(match.World.Ball.linearVelocity.y,0);Assert.AreEqual(0,match.World.Ball.linearVelocity.x);Assert.AreEqual(0,match.World.Ball.linearVelocity.z);
                for(int i=0;i<4;i++){Assert.AreEqual(1,p[i].calls);Assert.AreEqual(i,p[i].lastPlayer);}
                Assert.IsNull(match.Failure);
            }
            yield return null;
        }
        [UnityTest] public IEnumerator InferenceFailureIsTerminalWithoutAdvancingPhysicsOrRetryingPolicy()
        {
            using(var match=new PlayerLearningMatchV3())
            {
                var p=new[]{new Policy(),new Policy(),new Policy(),new Policy{fail=true}};match.AttachPolicies(p,1300000);
                Assert.Throws<InvalidOperationException>(()=>match.StepAgents());Assert.IsNotNull(match.Failure);Assert.AreEqual(0,match.Tick);
                Assert.Throws<InvalidOperationException>(()=>match.StepAgents());Assert.AreEqual(1,p[3].calls);Assert.AreEqual(0,match.Tick);
            }
            yield return null;
        }
        [UnityTest] public IEnumerator AnotherPlayerCannotReleaseServersHeldBall()
        {
            using(var match=new PlayerLearningMatchV3())
            {
                var actions=new PlayerActionV3[4];var data=new float[PlayerActionV3.Count];data[16]=1;actions[1]=new PlayerActionV3(data);
                for(int tick=0;tick<24;tick++)Assert.IsTrue(match.Step(actions));
                Assert.IsTrue(match.BallHeld);Assert.IsTrue(match.World.Ball.isKinematic);
                Assert.Throws<ArgumentException>(()=>match.Step(new PlayerActionV3[3]));Assert.AreEqual(24,match.Tick);
            }
            yield return null;
        }
    }
}
