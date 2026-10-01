using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Picklebot.PlayerControlsIntegration;
using Unity.MLAgents;
using Unity.MLAgents.Policies;
using UnityEngine;
using UnityEngine.TestTools;
using Object = UnityEngine.Object;

namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerExecutionGoalV1Tests
    {
        [Test]
        public void AppendsPrivateGoalAndPreservesEveryLegacyField()
        {
            var values=Enumerable.Range(0,124).Select(i=>i/100f).ToArray();
            var obs=new PlayerObservationV3(2,12,values);
            var goal=new PlayerExecutionGoalV1(2,6,PlayerIntentV1.Cover,new Vector2(1,-3),.5f,new Vector2(-1,4),1);
            var encoded=goal.Observe(obs);
            Assert.AreEqual(136,encoded.Length);CollectionAssert.AreEqual(values,encoded.Take(124));
            Assert.AreEqual(1,encoded[126]);Assert.AreEqual(1,encoded[128]);Assert.AreEqual(1,encoded[132]);
            Assert.AreEqual((1-values[0]*4.2f)/8.4f,encoded[129]);
            encoded[0]=99;Assert.AreEqual(values[0],obs.ToArray()[0]);
            Assert.Throws<InvalidOperationException>(()=>goal.Observe(new PlayerObservationV3(1,12,values)));
            Assert.Throws<InvalidOperationException>(()=>goal.Observe(new PlayerObservationV3(2,5,values)));
        }

        [Test]
        public void MissingTargetsAreMaskedAndTeamsShareTheSameCanonicalGoal()
        {
            var values=new float[124];values[0]=.2f;values[1]=-.5f;
            var near=new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(1,4));
            var far=new PlayerExecutionGoalV1(2,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(1,4));
            CollectionAssert.AreEqual(near.Observe(new PlayerObservationV3(0,0,values)),far.Observe(new PlayerObservationV3(2,0,values)));
            Assert.AreEqual(0,near.LandingDistance(new Vector3(1,0,4)));
            Assert.AreEqual(0,far.LandingDistance(new Vector3(-1,0,-4)));
            var neutral=new PlayerExecutionGoalV1(0,0,PlayerIntentV1.Yield).Observe(new PlayerObservationV3(0,0,values));
            Assert.IsTrue(neutral.Skip(128).All(v=>v==0));
        }

        [Test]
        public void InvalidGoalsCannotReachTheActor()
        {
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(4,0,PlayerIntentV1.PlayBall));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,-1,PlayerIntentV1.PlayBall));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,(PlayerIntentV1)99));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(float.NaN,4)));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,movementTarget:new Vector2(0,2)));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(0,-2)));
            Assert.Throws<ArgumentException>(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotRadius:0));
        }

        [Test]
        public void PlacementBonusCannotRewardAnIllegalHitOrMiss()
        {
            var goal=new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall,shotTarget:new Vector2(1,4));
            Assert.AreEqual(0,PlayerExecutionDrillsV1.TargetBonus(goal,false,new Vector3(1,0,4),.25f));
            Assert.AreEqual(.25f,PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(1,0,4),.25f));
            Assert.AreEqual(.125f,PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(1.5f,0,4),.25f));
            Assert.AreEqual(0,PlayerExecutionDrillsV1.TargetBonus(goal,true,new Vector3(3,0,4),.25f));
            Assert.AreEqual(0,PlayerExecutionDrillsV1.TargetBonus(new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall),true,Vector3.zero,.25f));
            Assert.Throws<ArgumentException>(()=>PlayerExecutionDrillsV1.TargetBonus(goal,true,Vector3.zero,1));
        }

        [Test]
        public void LegacyBehaviorCannotSilentlyLoadNewObservations()
        {
            var root=new GameObject("Contract fixture");root.SetActive(false);
            try
            {
                var behavior=root.AddComponent<BehaviorParameters>();
                behavior.BehaviorName=PlayerMlAgentV3.BehaviorName;behavior.BrainParameters.VectorObservationSize=124;
                var agent=root.AddComponent<PlayerMlAgentV3>();
                Assert.Throws<InvalidOperationException>(()=>agent.BindGoal(()=>new PlayerExecutionGoalV1(0,0,PlayerIntentV1.PlayBall)));
            }
            finally{Object.DestroyImmediate(root);}
        }

        private static (string[] episodes,float[] trace) Run(bool execution)
        {
            var root=new GameObject("Execution parity fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;
            run.FirstSeed=1304000;run.SeedCount=32;run.ArenaCount=4;run.Task="rally-maintenance";
            run.MaximumReturnDifficulty=0;run.AlignDrillDecisions=true;
            PlayerExecutionDrillsV1 goals=null;
            if(execution){goals=root.AddComponent<PlayerExecutionDrillsV1>();goals.SampleShotTargets=true;goals.LegalTargetReward=0;}
            var trace=new List<float>();var seats=new HashSet<int>();
            try
            {
                root.SetActive(true);run.InitializeRun();
                foreach(var arena in run.ActiveArenas)foreach(var agent in arena.Agents)
                {
                    agent.Received+=(current,actions)=>
                    {
                        var input=current.LastPolicyObservation;seats.Add(current.Seat);
                        Assert.AreEqual(execution?136:124,input.Length);
                        CollectionAssert.AreEqual(current.LastObservation.ToArray(),input.Take(124));
                        if(execution){Assert.AreEqual(current.Seat,current.LastGoal.Seat);Assert.IsTrue(current.LastGoal.HasShotTarget);}
                        trace.AddRange(input.Take(124));trace.AddRange(current.LastCommand.ToArray());
                    };
                }
                for(int i=0;i<100000&&run.Report.status!="seed_budget_complete";i++)run.StepOneTick();
                Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(32,run.Episodes.Count);
                Assert.AreEqual(4,seats.Count);Assert.IsTrue(run.Episodes.All(e=>e.outcome!="exception"&&e.outcome!="infeasible"));
                if(execution){Assert.AreEqual(32,goals.Completed);Assert.AreEqual(PlayerExecutionGoalV1.Contract,run.Report.contract);}
                return (run.Episodes.Select(e=>JsonUtility.ToJson(e)).ToArray(),trace.ToArray());
            }
            finally{Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
        }

        [UnityTest]
        public IEnumerator GoalSamplingPreservesFeedsActionsAndEpisodeResetsAcrossAllSeats()
        {
            var old=Run(false);var next=Run(true);
            CollectionAssert.AreEqual(old.episodes,next.episodes);
            CollectionAssert.AreEqual(old.trace,next.trace);
            yield return null;
        }
    }
}
