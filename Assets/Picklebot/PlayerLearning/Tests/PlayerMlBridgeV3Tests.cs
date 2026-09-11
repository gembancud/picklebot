using System;
using System.Collections;
using System.IO;
using System.Linq;
using NUnit.Framework;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using UnityEngine;
using UnityEngine.TestTools;

namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerMlBridgeV3Tests
    {
        private sealed class FixedCommand : IPlayerPolicyV3
        {
            public PlayerActionV3 command;
            public string Name => "test commands";
            public void Reset() { }
            public PlayerActionV3 Decide(PlayerObservationV3 observation, System.Random random) => command;
        }
        private sealed class BrokenPolicy : IPlayerPolicyV3
        {
            public string Name => "Injected software failure";
            public void Reset() { }
            public PlayerActionV3 Decide(PlayerObservationV3 observation, System.Random random)
                => throw new InvalidOperationException("Injected software failure");
        }
        private sealed class ReleaseMaskProbe : IDiscreteActionMask
        {
            public bool enabled;
            public void SetActionEnabled(int branch,int actionIndex,bool isEnabled)
            {Assert.AreEqual(0,branch);Assert.AreEqual(1,actionIndex);enabled=isEnabled;}
        }

        [UnityTest]
        public IEnumerator MixedPracticeRotatesAllSeatsAndMasksReleasePerActualTask()
            => MixedPractice("serve-return","drop-serve",1300900);
        [UnityTest]
        public IEnumerator ContactPracticeRotatesAllSeatsAndMasksReleasePerActualTask()
            => MixedPractice("contact-return","drop-contact",1301070);
        private IEnumerator MixedPractice(string mixedTask,string dropTask,int firstSeed)
        {
            var root=new GameObject("Mixed-practice fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();
            run.RequireTrainer=false;run.AutoRun=false;run.ArenaCount=8;run.AlignDrillDecisions=true;
            run.FirstSeed=firstSeed;run.SeedCount=16;run.Task=mixedTask;run.MaximumReturnDifficulty=.5f;
            root.SetActive(true);run.InitializeRun();
            var observed=new System.Collections.Generic.HashSet<int>();
            try
            {
                foreach(var arena in run.ActiveArenas)
                {
                    var currentArena=arena;
                    foreach(var agent in arena.Agents)
                    {
                        agent.HeuristicRelease=1; // Fixture only: policy channel plumbing, not a learner controller.
                        agent.Received+=(current,actions)=>
                        {
                            var drill=currentArena.Drill;
                            Assert.AreEqual(drill.Player,current.Seat);
                            Assert.AreEqual(drill.Match.Tick,current.ObservedTick);
                            bool available=drill.Task==dropTask&&drill.Match.BallHeld;
                            Assert.AreEqual(available?1:0,current.LastCommand.ToArray()[16]);
                            observed.Add(drill.Seed);
                        };
                    }
                }
                for(int tick=0;run.Report.status!="seed_budget_complete"&&tick<5000;tick++)
                {
                    foreach(var arena in run.ActiveArenas)
                    {
                        if(arena.Finished)continue;
                        foreach(var agent in arena.Agents)
                        {
                            var mask=new ReleaseMaskProbe();agent.WriteDiscreteActionMask(mask);
                            Assert.AreEqual(agent.Seat==arena.Drill.Player&&arena.Drill.Task==dropTask&&arena.Drill.Match.BallHeld,mask.enabled);
                        }
                    }
                    run.StepOneTick();
                    if(tick<6)foreach(var arena in run.ActiveArenas.Where(a=>a.Drill.Task==dropTask))Assert.IsTrue(arena.Drill.Match.BallHeld,"Release must wait for the real action latency");
                    if(tick==6)foreach(var arena in run.ActiveArenas.Where(a=>a.Drill.Task==dropTask))Assert.IsFalse(arena.Drill.Match.BallHeld);
                }
                Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(16,run.Episodes.Count);Assert.AreEqual(16,observed.Count);
                Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));
                foreach(int seat in Enumerable.Range(0,4))foreach(string task in new[]{dropTask,"varied-return"})
                    Assert.AreEqual(2,run.Episodes.Count(e=>e.player==seat&&e.task==task));
                foreach(var episode in run.Episodes)
                {
                    Assert.AreEqual((episode.seed-run.FirstSeed)/4%2==0?dropTask:"varied-return",episode.task);
                    Assert.IsFalse(new[]{"exception","infeasible"}.Contains(episode.outcome));
                    if(episode.task==dropTask)Assert.IsTrue(episode.released);
                }
            }
            finally{UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }

        [UnityTest]
        public IEnumerator LowHighPracticeKeepsFeedHeightOnItsTaskAndPlayerDecisionsPrivate()
        {
            var root=new GameObject("Low/high practice fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.RequireTrainer=false;run.AutoRun=false;
            run.FirstSeed=1301150;run.SeedCount=16;run.ArenaCount=8;run.AlignDrillDecisions=true;
            run.Task="low-high-return";run.FeedLowering=.2f;run.MaximumReturnDifficulty=.5f;
            root.SetActive(true);run.InitializeRun();
            var observed=new System.Collections.Generic.HashSet<int>();
            try
            {
                foreach(var arena in run.ActiveArenas)
                {
                    var currentArena=arena;
                    foreach(var agent in arena.Agents)
                    {
                        agent.HeuristicRelease=1; // Test release must be masked on both feed tasks.
                        agent.Received+=(current,actions)=>
                        {
                            Assert.AreEqual(currentArena.Drill.Player,current.Seat);
                            Assert.AreEqual(currentArena.Drill.Match.Tick,current.ObservedTick);
                            Assert.AreEqual(0,current.LastCommand.ToArray()[16]);
                            observed.Add(currentArena.Drill.Seed);
                        };
                    }
                }
                for(int tick=0;run.Report.status!="seed_budget_complete"&&tick<5000;tick++)
                {
                    foreach(var arena in run.ActiveArenas.Where(a=>!a.Finished))
                    {
                        Assert.AreEqual(arena.Drill.Task=="low-return"?.2f:0,arena.Drill.FeedLowering);
                        foreach(var agent in arena.Agents)
                        {var mask=new ReleaseMaskProbe();agent.WriteDiscreteActionMask(mask);Assert.IsFalse(mask.enabled);}
                    }
                    run.StepOneTick();
                }
                Assert.AreEqual("seed_budget_complete",run.Report.status);Assert.AreEqual(16,observed.Count);
                Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));
                foreach(int seat in Enumerable.Range(0,4))foreach(string task in new[]{"low-return","varied-return"})
                    Assert.AreEqual(2,run.Episodes.Count(e=>e.player==seat&&e.task==task));
                foreach(var e in run.Episodes)
                {
                    Assert.AreEqual(e.task=="low-return"?.2f:0,e.feedLowering);
                    Assert.IsFalse(new[]{"exception","infeasible"}.Contains(e.outcome));
                    if(!e.faceContact)Assert.AreEqual(-1,e.faceContactBallHeight);
                    else Assert.IsTrue(float.IsFinite(e.faceContactBallHeight));
                }
            }
            finally{UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }

        [UnityTest]
        public IEnumerator SimulationFailureCannotSubmitRewardOrTerminalTrainingSample()
        {
            var root=new GameObject("Drill failure boundary fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlDrillsV3>();run.RequireTrainer=false;run.AutoRun=false;
            string evidence=Path.Combine(Application.temporaryCachePath,"failure-trace-"+Guid.NewGuid().ToString("N"));
            run.EvidenceDirectory=evidence;run.SourceIdentity="failure-fixture";
            run.FirstSeed=1300710;run.SeedCount=4;run.ArenaCount=1;root.SetActive(true);run.InitializeRun();
            try
            {
                var arena=run.ActiveArenas[0];var agent=arena.Agents[arena.Drill.Player];
                var policies=(IPlayerPolicyV3[])typeof(PlayerDecisionLoopV3).GetField("policies",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).GetValue(arena.Drill.Match.Decisions); policies[0]=new BrokenPolicy();
                Assert.Throws<InvalidOperationException>(()=>run.StepOneTick());
                Assert.AreEqual("exception",arena.Drill.Outcome);Assert.AreEqual(0,run.Episodes.Count);
                Assert.AreEqual(0,agent.GetCumulativeReward());
                var info=(AgentInfo)typeof(Agent).GetField("m_Info",System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic).GetValue(agent);
                Assert.IsFalse(info.done);Assert.AreEqual(0,run.Report.completedEpisodes);
                var trace=JsonUtility.FromJson<MlSimulationFailureV3>(File.ReadAllText(Path.Combine(evidence,"simulation-failure.json")));
                Assert.AreEqual(1300710,trace.seed);Assert.AreEqual(0,trace.player);Assert.AreEqual(0,trace.physicsTick);
                Assert.AreEqual("exception",trace.outcome);Assert.AreEqual("failure-fixture",trace.sourceIdentity);
                Assert.AreEqual(1,trace.decisions.Length);Assert.AreEqual(0,trace.decisions[0].observationTick);
                CollectionAssert.AreEqual(agent.LastCommand.ToArray(),trace.decisions[0].physical);
                CollectionAssert.AreEqual(agent.LastObservation.ToArray(),trace.decisions[0].observation);
                Assert.AreEqual(0,new FileInfo(Path.Combine(evidence,"episodes.jsonl")).Length);
            }
            finally {UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
            yield return null;
        }

        [Test]
        public void FrameworkActionsKeepTheFullRangeAndEnforceReleaseAvailability()
        {
            var continuous = Enumerable.Repeat(1f, 16).ToArray();
            var actions = new ActionBuffers(new ActionSegment<float>(continuous), new ActionSegment<int>(new[] {1}));
            var upper = PlayerMlAgentV3.Decode(actions, true);
            for (int i = 0; i < 18; i++) Assert.AreEqual(i == 4 ? 0 : 1, upper[i], "Channel " + i);
            for (int i = 0; i < 16; i++) continuous[i] = -1;
            var lower = PlayerMlAgentV3.Decode(actions, false);
            for (int i = 0; i < 18; i++) Assert.AreEqual(new[] {3,4,5,16,17}.Contains(i) ? 0 : -1, lower[i], "Channel " + i);
            continuous[0] = float.NaN;
            Assert.Throws<ArgumentException>(() => PlayerMlAgentV3.Decode(actions, true));
        }

        [UnityTest]
        public IEnumerator FrameworkDecisionsPreserveTheExistingClockAndPhysicalTrajectory()
        {
            var root = new GameObject("ML-Agents bridge parity fixture");
            root.SetActive(false);
            var run = root.AddComponent<PlayerMlDrillsV3>();
            run.RequireTrainer = false; run.AutoRun = false; run.ArenaCount = 1;
            run.FirstSeed = 1300500; run.SeedCount = 4; run.Task = "reaction-return";
            root.SetActive(true);
            run.InitializeRun();
            try
            {
                var arena = run.ActiveArenas[0];
                var controls = new float[16]; controls[3] = controls[4] = controls[15] = -1;
                controls[0] = .2f; controls[5] = .12f; controls[8] = .15f;
                arena.Agents[0].HeuristicControls = controls;
                var expected = PlayerMlAgentV3.Decode(new ActionBuffers(new ActionSegment<float>(controls),
                    new ActionSegment<int>(new[] {0})), false);
                using (var direct = new PlayerContactDrillV3(1300500, 0, "reaction-return"))
                {
                    direct.Match.AttachPolicies(new IPlayerPolicyV3[] {new FixedCommand {command=expected},
                        new FixedCommand(),new FixedCommand(),new FixedCommand()}, 1300500);
                    for (int tick = 0; tick < 24; tick++)
                    {
                        run.StepOneTick(); direct.Step();
                        Assert.IsFalse(arena.Drill.Done); Assert.IsFalse(direct.Done);
                        Assert.AreEqual(direct.Match.Tick, arena.Drill.Match.Tick);
                        Assert.Less(Vector3.Distance(direct.Match.World.Ball.position, arena.Drill.Match.World.Ball.position), .00001f);
                        Assert.Less(Vector3.Distance(direct.Match.World.Players[0].Paddle.position,
                            arena.Drill.Match.World.Players[0].Paddle.position), .00001f);
                        CollectionAssert.AreEqual(direct.Match.ActiveFor(0).ToArray(), arena.Drill.Match.ActiveFor(0).ToArray());
                        if (tick < 6) CollectionAssert.AreEqual(new float[18], arena.Drill.Match.ActiveFor(0).ToArray());
                    }
                    Assert.AreEqual(2, arena.Agents[0].DecisionsReceived);
                    Assert.AreEqual(12, arena.Agents[0].ObservedTick);
                    Assert.AreEqual(0, arena.Agents[0].LastObservation.player);
                    for (int seat=1;seat<4;seat++)
                    {
                        Assert.AreEqual(0, arena.Agents[seat].DecisionsReceived);
                        CollectionAssert.AreEqual(new float[18], arena.Drill.Match.ActiveFor(seat).ToArray());
                        Assert.AreNotSame(arena.Agents[0], arena.Agents[seat]);
                    }
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(root); if (Academy.IsInitialized) Academy.Instance.Dispose(); }
            yield return null;
        }

        [UnityTest]
        public IEnumerator TerminalObservationsBelongToTheFinishedWorldAndSeedsRotateSeats()
        {
            var root = new GameObject("ML-Agents terminal fixture"); root.SetActive(false);
            var run = root.AddComponent<PlayerMlDrillsV3>();
            run.RequireTrainer = false; run.AutoRun = false; run.ArenaCount = 1;
            run.FirstSeed = 1300504; run.SeedCount = 4; run.Task = "reaction-contact";
            root.SetActive(true);
            run.InitializeRun();
            try
            {
                int iterations = 0;
                while (run.Episodes.Count < 4 && iterations++ < 1500)
                {
                    int count = run.Episodes.Count;
                    int player = run.ActiveArenas[0].Drill.Player;
                    run.StepOneTick();
                    if (run.Episodes.Count != count)
                    {
                        var episode = run.Episodes.Last();
                        var terminal = run.ActiveArenas[0].Agents[player].LastObservation;
                        Assert.AreEqual(player, terminal.player);
                        Assert.AreEqual(episode.physicsTicks, terminal.tick);
                        Assert.Greater(terminal.tick, 0);
                    }
                }
                Assert.AreEqual(4, run.Episodes.Count);
                CollectionAssert.AreEqual(new[] {0,1,2,3}, run.Episodes.Select(e => e.player));
                CollectionAssert.AreEqual(new[] {1300504,1300505,1300506,1300507}, run.Episodes.Select(e => e.seed));
                Assert.AreEqual("seed_budget_complete", run.Report.status);
                Assert.IsFalse(run.Report.trainerConnected);
            }
            finally { UnityEngine.Object.DestroyImmediate(root); if (Academy.IsInitialized) Academy.Instance.Dispose(); }
            yield return null;
        }

        [UnityTest]
        public IEnumerator AlignedCourtsPreservePrivateObservationsAcrossEpisodeResets()
        {
            var baseline = new System.Collections.Generic.Dictionary<string,float[]>();
            var terminalBaseline = new System.Collections.Generic.Dictionary<int,string>();
            foreach (bool aligned in new[] {false,true})
            {
                var root = new GameObject("Scheduler parity fixture"); root.SetActive(false);
                var run = root.AddComponent<PlayerMlDrillsV3>();
                run.RequireTrainer=false; run.AutoRun=false; run.ArenaCount=4;
                run.FirstSeed=1300720; run.SeedCount=12; run.Task="reaction-contact"; run.AlignDrillDecisions=aligned;
                root.SetActive(true); run.InitializeRun();
                int observed=0;
                try
                {
                    foreach (var arena in run.ActiveArenas)
                    {
                        var currentArena=arena;
                        foreach (var agent in arena.Agents) agent.Received+=(current,actions)=>
                        {
                            if(aligned)Assert.AreEqual(0,run.Report.schedulerTicks%12,"Courts must request together.");
                            Assert.AreEqual(currentArena.Drill.Player,current.Seat);
                            Assert.AreEqual(currentArena.Drill.Match.Tick,current.ObservedTick);
                            string key=currentArena.Drill.Seed+":"+current.ObservedTick;
                            var observation=current.LastObservation.ToArray();
                            if(!aligned)baseline.Add(key,observation);
                            else {Assert.IsTrue(baseline.ContainsKey(key));CollectionAssert.AreEqual(baseline[key],observation,key);}
                            observed++;
                        };
                    }
                    int iterations=0;
                    while(run.Report.status!="seed_budget_complete"&&iterations++<12000)
                    {
                        var previous=run.ActiveArenas.Select(a=>a.Drill).ToArray();
                        var stoppedTicks=previous.Select(d=>d.Done?d.Match.Tick:-1).ToArray();
                        run.StepOneTick();
                        for(int i=0;i<previous.Length;i++)
                            if(stoppedTicks[i]>=0&&ReferenceEquals(previous[i],run.ActiveArenas[i].Drill))
                                Assert.AreEqual(stoppedTicks[i],previous[i].Match.Tick,"No physical time passes while a finished court waits.");
                    }
                    Assert.AreEqual("seed_budget_complete",run.Report.status);
                    Assert.AreEqual(12,run.Episodes.Count);Assert.AreEqual(observed,run.Report.decisions);
                    Assert.AreEqual(observed,run.Report.requestedDecisions);
                    Assert.AreEqual(run.Report.physicsTicks,run.Episodes.Sum(e=>e.physicsTicks));
                    if(aligned)Assert.AreEqual(baseline.Count,observed);
                    foreach(var episode in run.Episodes)
                    {
                        string terminal=JsonUtility.ToJson(episode);
                        if(!aligned)terminalBaseline.Add(episode.seed,terminal);
                        else Assert.AreEqual(terminalBaseline[episode.seed],terminal,"Terminal observation/reward reset semantics changed.");
                    }
                }
                finally {UnityEngine.Object.DestroyImmediate(root);if(Academy.IsInitialized)Academy.Instance.Dispose();}
                yield return null;
            }
        }
    }
}
