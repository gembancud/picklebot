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
    public sealed class PlayerMixedHeightV3Tests
    {
        private sealed class ReleaseProbe : IDiscreteActionMask
        {
            public bool enabled;
            public void SetActionEnabled(int branch,int actionIndex,bool value)
            {Assert.AreEqual(0,branch);Assert.AreEqual(1,actionIndex);enabled=value;}
        }

        [UnityTest]
        public IEnumerator EveryHeightCoversEverySeatWithEquivalentResetsAndPrivateActions()
        {
            var root=new GameObject("Mixed-height ownership fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.RequireTrainer=false;run.AutoRun=false;
            run.FirstSeed=1301192;run.SeedCount=80;run.ArenaCount=8;run.AlignDrillDecisions=true;
            run.Task="mixed-height-return";run.FeedLowering=.4f;run.MaximumReturnDifficulty=.5f;
            root.SetActive(true);run.InitializeRun();
            var seen=new HashSet<int>();
            try
            {
                Assert.Throws<ArgumentOutOfRangeException>(()=>run.FeedLoweringForEpisode(-1));
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
                            Assert.AreEqual(0,current.LastCommand.ToArray()[16]);
                            if(current.ObservedTick!=0)return;
                            Assert.IsTrue(seen.Add(drill.Seed));
                            // Curriculum selects an existing physical reset. It may
                            // not change the body, ball dynamics or private observations.
                            using(var reference=new PlayerContactDrillV3(drill.Seed,drill.Player,drill.Task,.5f,drill.FeedLowering))
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
                    {var mask=new ReleaseProbe();agent.WriteDiscreteActionMask(mask);Assert.IsFalse(mask.enabled);}
                    run.StepOneTick();
                }
                Assert.AreEqual("seed_budget_complete",run.Report.status);
                Assert.AreEqual(80,seen.Count);Assert.AreEqual(80,run.Episodes.Count);
                Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));
                Assert.AreEqual(run.Report.decisions,run.Episodes.Sum(e=>e.decisions));
                foreach(int seat in Enumerable.Range(0,4))
                {
                    Assert.AreEqual(10,run.Episodes.Count(e=>e.player==seat&&e.task=="varied-return"));
                    foreach(float height in new[]{0,.1f,.2f,.3f,.4f})
                        Assert.AreEqual(2,run.Episodes.Count(e=>e.player==seat&&e.task=="low-return"&&Mathf.Abs(e.feedLowering-height)<1e-6));
                }
                foreach(var e in run.Episodes)
                {
                    Assert.AreEqual((e.seed-run.FirstSeed)%4,e.player);
                    Assert.IsFalse(new[]{"exception","infeasible"}.Contains(e.outcome));
                    if(e.task=="varied-return")Assert.AreEqual(0,e.feedLowering);
                    else Assert.AreEqual(0,e.feedDifficulty);
                }
            }
            finally{UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }
    }
}
