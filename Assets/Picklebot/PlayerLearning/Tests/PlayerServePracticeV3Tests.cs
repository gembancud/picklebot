using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Picklebot.PlayerControlsIntegration;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using UnityEngine;
using UnityEngine.TestTools;

namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerServePracticeV3Tests
    {
        private sealed class ReleaseProbe : IDiscreteActionMask
        {
            public bool enabled;
            public void SetActionEnabled(int branch,int actionIndex,bool value)
            {Assert.AreEqual(0,branch);Assert.AreEqual(1,actionIndex);enabled=value;}
        }

        [UnityTest]
        public IEnumerator ServePracticePreservesPhysicalResetsPrivateActionsAndReleaseOwnership()
        {
            var root=new GameObject("Serve practice ownership fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.RequireTrainer=false;run.AutoRun=false;
            run.FirstSeed=1301704;run.SeedCount=64;run.ArenaCount=8;run.AlignDrillDecisions=true;
            run.Task="serve-practice-return";run.FeedLowering=.2f;run.FeedLateralOffset=-.2f;run.MaximumReturnDifficulty=.5f;
            root.SetActive(true);run.InitializeRun();
            var seen=new HashSet<int>();
            try
            {
                Assert.Throws<ArgumentOutOfRangeException>(()=>run.FeedLoweringForEpisode(-1));
                Assert.Throws<ArgumentOutOfRangeException>(()=>run.FeedLateralOffsetForEpisode(-1));
                foreach(var arena in run.ActiveArenas)
                {
                    var currentArena=arena;
                    foreach(var agent in arena.Agents)
                    {
                        agent.HeuristicRelease=1; // Fixture only: verify release cannot leak into feeds.
                        agent.Received+=(current,actions)=>
                        {
                            var drill=currentArena.Drill;
                            Assert.AreEqual(drill.Player,current.Seat);
                            Assert.AreEqual(drill.Match.Tick,current.ObservedTick);
                            Assert.AreEqual(PlayerContactDrillV3.IsDropTask(drill.Task)&&drill.Match.BallHeld&&drill.Match.World.Rules.Server==current.Seat?1:0,current.LastCommand.ToArray()[16]);
                            if(current.ObservedTick!=0)return;
                            Assert.IsTrue(seen.Add(drill.Seed));
                            // Curriculum selects an existing physical reset. It may
                            // not change the body, ball dynamics or private observations.
                            int condition=(drill.Seed-run.FirstSeed)/4%8;
                            Assert.AreEqual(condition==0||condition==4?"drop-contact":condition==2||condition==6?"varied-return":"low-return",drill.Task);
                            float expectedHeight=new[]{0,.2f,0,.3f,0,.2f,0,.2f}[condition];
                            float expectedOffset=new[]{0,-.2f,0,0,0,-.2f,0,-.1f}[condition];
                            Assert.AreEqual(expectedHeight,drill.FeedLowering);
                            Assert.AreEqual(expectedOffset,drill.FeedLateralOffset);
                            using(var reference=new PlayerContactDrillV3(drill.Seed,drill.Player,drill.Task,.5f,expectedHeight,expectedOffset))
                            {
                                CollectionAssert.AreEqual(PlayerObservationV3.Capture(reference.Match,current.Seat,0).ToArray(),current.LastObservation.ToArray());
                                Assert.AreEqual(reference.Match.World.Ball.linearVelocity,drill.Match.World.Ball.linearVelocity);
                                foreach(int seat in Enumerable.Range(0,4))
                                    Assert.AreEqual(reference.Match.World.Players[seat].Paddle.position,drill.Match.World.Players[seat].Paddle.position);
                            }
                        };
                    }
                }
                for(int tick=0;run.Report.status!="seed_budget_complete"&&tick<15000;tick++)
                {
                    foreach(var arena in run.ActiveArenas.Where(a=>!a.Finished))
                    foreach(var agent in arena.Agents)
                    {var mask=new ReleaseProbe();agent.WriteDiscreteActionMask(mask);Assert.AreEqual(PlayerContactDrillV3.IsDropTask(arena.Drill.Task)&&arena.Drill.Match.BallHeld&&arena.Drill.Match.World.Rules.Server==agent.Seat,mask.enabled);}
                    run.StepOneTick();
                }
                Assert.AreEqual("seed_budget_complete",run.Report.status);
                Assert.AreEqual(64,seen.Count);Assert.AreEqual(64,run.Episodes.Count);
                Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));
                Assert.AreEqual(run.Report.decisions,run.Episodes.Sum(e=>e.decisions));
                foreach(int seat in Enumerable.Range(0,4))
                {
                    Assert.AreEqual(4,run.Episodes.Count(e=>e.player==seat&&e.task=="varied-return"));
                    Assert.AreEqual(4,run.Episodes.Count(e=>e.player==seat&&e.task=="low-return"&&e.feedLowering==.2f&&e.feedLateralOffset==-.2f));
                    Assert.AreEqual(4,run.Episodes.Count(e=>e.player==seat&&e.task=="drop-contact"));
                    Assert.AreEqual(2,run.Episodes.Count(e=>e.player==seat&&e.task=="low-return"&&e.feedLowering==.2f&&e.feedLateralOffset==-.1f));
                    Assert.AreEqual(2,run.Episodes.Count(e=>e.player==seat&&e.task=="low-return"&&e.feedLowering==.3f&&e.feedLateralOffset==0));
                }
                foreach(var e in run.Episodes)
                {
                    Assert.AreEqual((e.seed-run.FirstSeed)%4,e.player);
                    Assert.IsFalse(new[]{"exception","infeasible"}.Contains(e.outcome));
                    if(e.task=="drop-contact"){Assert.IsTrue(e.released);Assert.IsTrue(e.dropBounced);}
                    else if(e.task=="varied-return")Assert.AreEqual(0,e.feedLowering);
                    else Assert.AreEqual(0,e.feedDifficulty);
                }
            }
            finally{UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }
    }
}
