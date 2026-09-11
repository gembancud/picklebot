using System;
using Random = System.Random;
using System.Linq;
using NUnit.Framework;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerDecisionLoopV2Tests
    {
        private sealed class Policy:IPlayerPolicyV2
        {
            public string Name=>"test policy";
            public Func<PlayerObservationV2,Random,PlayerActionV2> decide;
            public int calls,resets;
            public PlayerActionV2 Decide(PlayerObservationV2 observation,Random random) {calls++;return decide==null?default:decide(observation,random);}
            public void Reset(){resets++;calls=0;}
        }
        private static Policy[] Policies()=>Enumerable.Range(0,4).Select(i=>new Policy()).ToArray();
        private static PlayerObservationV2 Capture(int player,int tick)=>new PlayerObservationV2(player,tick,new float[96]);
        [Test] public void SchemaDimensionsAreExplicitAndFieldNamesUnique()
        {
            Assert.AreEqual(96,PlayerObservationV2.Fields.Length);Assert.AreEqual(96,PlayerObservationV2.Fields.Distinct().Count());
            Assert.AreEqual(15,PlayerActionV2.Fields.Length);
            Assert.Throws<ArgumentException>(()=>new PlayerObservationV2(0,0,new float[54]));
            Assert.Throws<ArgumentException>(()=>new PlayerActionV2(new float[12]));
        }
        [Test] public void ActionOwnsItsValuesAndBoundsMovementInOneVector()
        {
            var values=default(PlayerActionV2).ToArray();values[0]=values[1]=4;
            var action=new PlayerActionV2(values);values[0]=-1;var copy=action.ToArray();copy[0]=-1;
            Assert.Greater(action[0],0);Assert.That(action.Movement(0).move.magnitude,Is.EqualTo(1).Within(1e-6f));
            values[0]=float.NaN;Assert.Throws<ArgumentException>(()=>new PlayerActionV2(values));
        }
        [Test] public void FacingUsesCourtRotationWhileMovementAndPaddleStayBodyLocal()
        {
            var values=default(PlayerActionV2).ToArray();values[0]=.4f;values[2]=.25f;
            var action=new PlayerActionV2(values);
            Assert.AreEqual(45,action.Movement(0).facingYaw);Assert.AreEqual(225,action.Movement(2).facingYaw);
            Assert.AreEqual(action.Movement(0).move,action.Movement(2).move);
            Assert.That(Vector3.Distance(action.Paddle().localHandTarget,new Vector3(0,-.2f,.35f)),Is.LessThan(1e-6f));
        }
        [Test] public void AllInputsAreFrozenBeforeAnyPolicyRuns()
        {
            float external=1;var policies=Policies();float seen=-1;
            policies[0].decide=(o,r)=>{external=9;o.values[0]=88;return default;};
            policies[1].decide=(o,r)=>{seen=o.values[0];return default;};
            var loop=new PlayerDecisionLoopV2(policies,1300000);PlayerDecisionV2 first=null;
            loop.Decided+=d=>{if(d.player==0)first=d;};
            loop.Step((p,t)=>{var v=new float[96];v[0]=external;return new PlayerObservationV2(p,t,v);},0);
            Assert.AreEqual(1,seen);Assert.AreEqual(1,first.observation.values[0]);
        }
        [Test] public void ActionsApplyAfterSixTicksAndRemainHeldUntilNextDecision()
        {
            var policies=Policies();policies[0].decide=(o,r)=>{var v=default(PlayerActionV2).ToArray();v[0]=.4f;return new PlayerActionV2(v);};
            var loop=new PlayerDecisionLoopV2(policies,1300000);
            for(int t=0;t<18;t++)
            {
                loop.Step(Capture,t);Assert.AreEqual(t<6?0:.4f,loop.ActionFor(0)[0]);
            }
            Assert.AreEqual(2,policies[0].calls);loop.Reset();Assert.AreEqual(0,loop.ActionFor(0)[0]);
            Assert.AreEqual(1,policies[0].resets);loop.Step(Capture,0);
        }
        [Test] public void OnePlayersRandomConsumptionCannotChangeAnotherPlayersStream()
        {
            float Run(int draws)
            {
                var policies=Policies();policies[0].decide=(o,r)=>{for(int i=0;i<draws;i++)r.NextDouble();return default;};
                policies[1].decide=(o,r)=>{var v=default(PlayerActionV2).ToArray();v[0]=(float)r.NextDouble();return new PlayerActionV2(v);};
                var loop=new PlayerDecisionLoopV2(policies,1300000);for(int t=0;t<=6;t++)loop.Step(Capture,t);return loop.ActionFor(1)[0];
            }
            Assert.AreEqual(Run(1),Run(1000));
        }
        [Test] public void SeatSwapCarriesThePrivateIdentityRandomStream()
        {
            float Run(int[] identities,int seat)
            {
                var policies=Policies();foreach(var p in policies)p.decide=(o,r)=>{var v=default(PlayerActionV2).ToArray();v[0]=(float)r.NextDouble();return new PlayerActionV2(v);};
                var loop=new PlayerDecisionLoopV2(policies,1300000,identities);for(int t=0;t<=6;t++)loop.Step(Capture,t);return loop.ActionFor(seat)[0];
            }
            Assert.AreEqual(Run(new[]{0,1,2,3},0),Run(new[]{1,0,3,2},1));
        }
        [Test] public void RejectsSharedMutablePolicyInstancesAndInvalidClock()
        {
            var policy=new Policy();Assert.Throws<ArgumentException>(()=>new PlayerDecisionLoopV2(new[]{policy,policy,policy,policy},1));
            var loop=new PlayerDecisionLoopV2(Policies(),1);Assert.Throws<ArgumentException>(()=>loop.Step(Capture,1));
            loop.Step(Capture,0);Assert.Throws<ArgumentException>(()=>loop.Step(Capture,0));
            Assert.Throws<ArgumentException>(()=>new PlayerDecisionLoopV2(Policies(),1,new[]{2,1,0,3}));
        }
    }
}
