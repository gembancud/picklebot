using System;
using System.IO;
using System.Linq;
using NUnit.Framework;
using Picklebot.PlayerAgents;
using UnityEngine;
using Random=System.Random;
namespace Picklebot.PlayerControlsIntegration.Tests
{
    public sealed class PlayerIntentBridgeTests
    {
        private sealed class IntentPolicy:IPlayerIntentPolicyV2
        {
            public string Name=>"intent test";
            public PlayerShotIntentV2 LastIntent{get;set;}
            public PlayerActionV2 Decide(PlayerObservationV2 o,Random r)
            {LastIntent=new PlayerShotIntentV2(true,o.tick==0?2:7);var a=default(PlayerActionV2).ToArray();a[0]=o.tick==0?.2f:.7f;return new PlayerActionV2(a);}
            public void Reset(){LastIntent=default;}
        }
        [Test] public void IntentAndMovementAreCapturedTogetherAndDelayedTogether()
        {
            var policies=Enumerable.Range(0,4).Select(i=>new IntentPolicy()).ToArray();
            var loop=new PlayerDecisionLoopV2(policies,1300000);
            for(int tick=0;tick<=18;tick++)
            {
                loop.Step((p,t)=>new PlayerObservationV2(p,t,new float[96]),tick);
                policies[0].LastIntent=new PlayerShotIntentV2(false,8);
                if(tick<6)Assert.IsFalse(loop.IntentFor(0).enabled);
                else
                {Assert.IsTrue(loop.IntentFor(0).attempt);Assert.AreEqual(tick<18?2:7,loop.IntentFor(0).shot);Assert.AreEqual(tick<18?.2f:.7f,loop.ActionFor(0)[0]);}
            }
            loop.Reset();Assert.IsFalse(loop.IntentFor(0).enabled);Assert.AreEqual(0,loop.ActionFor(0)[0]);
        }
        [TestCase(false)] [TestCase(true)]
        public void HistoricalCheckpointMatchesOriginalInferenceAndRandomStream(bool sample)
        {
            var path=Path.Combine(Application.dataPath,"../artifacts/player-agents/ppo-20260907-130353/actor.json");
            var model=PlayerActorModel.Load(File.ReadAllText(path));
            var bridge=new LegacyActorIntentPolicyV2(model,sample);var original=new PlayerActor(model,sample);
            var a=new Random(1300000);var b=new Random(1300000);
            for(int n=0;n<64;n++)
            {
                var v=new float[96];for(int j=0;j<v.Length;j++)v[j]=Mathf.Sin(n*.13f+j*.17f);
                float angle=n*.11f;v[54]=Mathf.Sin(angle);v[55]=Mathf.Cos(angle);
                var old=original.Decide(new PlayerObservation{player=n%4,tick=n*12,values=v.Take(54).ToArray()},a);
                var action=bridge.Decide(new PlayerObservationV2(n%4,n*12,v),b);
                Assert.AreEqual(old.attempt,bridge.LastIntent.attempt);Assert.AreEqual(old.shot,bridge.LastIntent.shot);
                Assert.That(v[55]*action[0]+v[54]*action[1],Is.EqualTo(old.moveX).Within(2e-6f));
                Assert.That(-v[54]*action[0]+v[55]*action[1],Is.EqualTo(old.moveZ).Within(2e-6f));
                Assert.AreEqual(original.LastSample.logProbability,bridge.LastSample.logProbability);
                Assert.IsTrue(bridge.LastIntent.legacyAutoPosture);Assert.AreEqual(0,action[4]);
            }
            Assert.AreEqual(a.Next(),b.Next());Assert.AreSame(model,bridge.Model);
            Assert.AreEqual("player-observation-v1",model.observationVersion);
        }
        [Test] public void SharedWeightsDoNotShareDecisionState()
        {
            var model=PlayerActorModel.Load(File.ReadAllText(Path.Combine(Application.dataPath,"../artifacts/player-agents/ppo-20260907-130353/actor.json")));
            var first=new LegacyActorIntentPolicyV2(model);var second=new LegacyActorIntentPolicyV2(model);
            var v=new float[96];v[55]=1;first.Decide(new PlayerObservationV2(0,0,v),new Random(1300000));
            Assert.IsTrue(first.LastIntent.enabled);Assert.IsFalse(second.LastIntent.enabled);Assert.IsNull(second.LastSample);
            first.Reset();Assert.IsFalse(first.LastIntent.enabled);
        }
    }
}
