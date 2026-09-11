using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
using Unity.MLAgents;
using UnityEngine;
using UnityEngine.TestTools;
namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerFixedServeSidesV3Tests
    {
        [UnityTest] public IEnumerator BothServiceSidesRemainStationaryWithoutInventingRuleHistory()
        {
            for(int seat=0;seat<4;seat++)
            foreach(bool left in new[]{false,true})
            {
                using(var drill=new PlayerContactDrillV3(1302166+seat,seat,"stationary-serve",serveFromLeft:left))
                {
                    var m=drill.Match;var rules=m.World.Rules;var ball=m.World.Ball;var start=ball.position;
                    Assert.AreEqual(seat,rules.Server);Assert.AreEqual(!left,rules.IsRight(seat));
                    Assert.AreEqual(!left,rules.IsRight(rules.DesignatedReceiver));
                    Assert.AreEqual(0,rules.Score.Sum());Assert.AreEqual(0,rules.Events.Count);
                    Assert.IsFalse(m.BallHeld);Assert.IsTrue(m.StationarySupportActive);Assert.IsFalse(m.World.ServeBounced);
                    for(int tick=0;tick<120;tick++)Assert.IsTrue(m.Step(new PlayerActionV3[4]));
                    Assert.Less(Vector3.Distance(start,ball.position),1e-6);Assert.AreEqual(Vector3.zero,ball.linearVelocity);
                    Assert.IsFalse(rules.Dead);Assert.IsFalse(rules.Events.Any(e=>e.kind=="serve"));
                }
                yield return null;
            }
        }
        [UnityTest] public IEnumerator MixedBothSidesUsePrivateActionsAndBalanceEverySeat()
        {
            var root=new GameObject("Both-side serve curriculum fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.AutoRun=false;run.RequireTrainer=false;
            run.FirstSeed=1302166;run.SeedCount=32;run.ArenaCount=8;run.AlignDrillDecisions=true;
            run.Task="fixed-serve-return";run.FixedServeSides="both";
            var seen=new HashSet<int>();root.SetActive(true);run.InitializeRun();
            try
            {
                foreach(var arena in run.ActiveArenas)
                {
                    var captured=arena;
                    foreach(var agent in arena.Agents)
                    {
                        agent.HeuristicRelease=1;
                        agent.Received+=(current,actions)=>
                        {
                            Assert.AreEqual(captured.Drill.Player,current.Seat);Assert.AreEqual(0,current.LastCommand[16]);
                            Assert.AreEqual(current.Seat,current.LastObservation.player);
                            if(current.ObservedTick!=0)return;
                            var d=captured.Drill;int index=d.Seed-run.FirstSeed;Assert.IsTrue(seen.Add(d.Seed));
                            Assert.AreEqual(index/4%2==0?"stationary-serve":"varied-return",d.Task);
                            Assert.AreEqual(index/4%4==2,d.ServeFromLeft);
                            if(d.Task=="stationary-serve")Assert.AreEqual(!d.ServeFromLeft,d.Match.World.Rules.IsRight(d.Player));
                        };
                    }
                }
                for(int tick=0;tick<10000&&run.Report.status!="seed_budget_complete";tick++)run.StepOneTick();
                Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual("both",run.Report.fixedServeSides);
                Assert.AreEqual(32,seen.Count);Assert.AreEqual(32,run.Episodes.Count);
                Assert.AreEqual(8,run.Episodes.Count(e=>e.serveFromLeft));
                Assert.AreEqual(8,run.Episodes.Count(e=>e.task=="stationary-serve"&&!e.serveFromLeft));
                Assert.AreEqual(16,run.Episodes.Count(e=>e.task=="varied-return"));
                foreach(int seat in Enumerable.Range(0,4))Assert.AreEqual(2,run.Episodes.Count(e=>e.player==seat&&e.serveFromLeft));
                Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));
                Assert.AreEqual(run.Report.decisions,run.Episodes.Sum(e=>e.decisions));
                Assert.IsFalse(run.Episodes.Any(e=>e.outcome=="infeasible"||e.outcome=="exception"));
            }
            finally{UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }
        [Test] public void SideSelectionRejectsUnrelatedTasksAndWorkersRequireCompleteSideCycles()
        {
            Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidateFixedServeSides("random","stationary-serve"));
            Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidateFixedServeSides("both","varied-return"));
            Assert.Throws<ArgumentException>(()=>PlayerMlDrillsV3.ValidateFixedServeSides("left","fixed-team-match"));
            var m=new PlayerWorkerManifestV3{version=PlayerWorkerPlanV3.Version,mode="training",task="fixed-serve-return",fixedServeSides="both",sourceIdentity=new string('a',64),buildIdentity=new string('b',64),evidenceRoot="F:/dev/picklebot/artifacts/player-v3/side-plan-fixture",basePort=5005,workerCount=4,firstSeed=1000000,seedsPerWorker=16,arenasPerWorker=8,ticksPerFrame=48};
            Assert.AreEqual(16,PlayerWorkerPlanV3.CycleLength(m.task,m.fixedServeSides));
            for(int i=0;i<4;i++)Assert.AreEqual(1000000+i*16,PlayerWorkerPlanV3.Create(m,i).FirstSeed);
            m.seedsPerWorker=8;Assert.Throws<ArgumentException>(()=>PlayerWorkerPlanV3.Create(m,0));
            m.task="stationary-serve";Assert.AreEqual(8,PlayerWorkerPlanV3.CycleLength(m.task,m.fixedServeSides));
            PlayerWorkerPlanV3.Create(m,0);m.fixedServeSides="right";Assert.AreEqual(4,PlayerWorkerPlanV3.CycleLength(m.task,m.fixedServeSides));
        }
    }
}
