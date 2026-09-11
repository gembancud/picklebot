using System;
using System.Collections;
using System.Linq;
using System.Reflection;
using NUnit.Framework;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Policies;
using UnityEngine;
using UnityEngine.TestTools;

namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerMlTeamsV3Tests
    {
        private sealed class FixedCommand : IPlayerPolicyV3
        {
            public PlayerActionV3 command;
            public string Name => "test fixture";
            public void Reset() { }
            public PlayerActionV3 Decide(PlayerObservationV3 observation, System.Random random)
            {
                var action = command.ToArray();
                if (observation.ToArray()[Array.IndexOf(PlayerObservationV3.Fields, "ball.heldByServer")] < .5f) action[16] = 0;
                return new PlayerActionV3(action);
            }
        }
        // Inspect the actual SDK terminal packet, not a parallel project flag.
        private static AgentInfo Info(Agent agent) => (AgentInfo)typeof(Agent)
            .GetField("m_Info", BindingFlags.Instance | BindingFlags.NonPublic).GetValue(agent);
        private static void Step(PlayerMlTeamArenaV3 arena)
        { arena.RequestDecisions(); Academy.Instance.EnvironmentStep(); arena.StepPhysics(); }
        private static void Cleanup(GameObject root)
        { UnityEngine.Object.DestroyImmediate(root); if (Academy.IsInitialized) Academy.Instance.Dispose(); }
        private static float[] ZeroControls()
        { var controls = new float[16]; controls[3] = controls[4] = controls[15] = -1; return controls; }

        [UnityTest]
        public IEnumerator FourSimultaneousPrivateCommandsMatchTheOriginalPhysicalWorld()
        {
            var root = new GameObject("Four-player parity fixture");
            Academy.Instance.AutomaticSteppingEnabled = false;
            try
            {
                using var arena = new PlayerMlTeamArenaV3(root.transform, 1300600, 0, BehaviorType.HeuristicOnly);
                using var direct = new PlayerLearningMatchV3(false, 0);
                direct.InitializeStationaryServe();
                var commands = new FixedCommand[4];
                var snapshots = Enumerable.Range(0, 4).Select(i => PlayerObservationV3.Capture(arena.Match, i, 0)).ToArray();
                for (int seat = 0; seat < 4; seat++)
                {
                    var raw = ZeroControls(); raw[0] = (seat + 1) * .04f; raw[5] = (seat + 1) * .02f;
                    arena.Agents[seat].HeuristicControls = raw;
                    arena.Agents[seat].HeuristicRelease = 1;
                    commands[seat] = new FixedCommand {command = PlayerMlAgentV3.Decode(new ActionBuffers(
                        new ActionSegment<float>(raw), new ActionSegment<int>(new[] {1})), seat == 0)};
                }
                direct.AttachPolicies(commands, 1300600);
                for (int tick = 0; tick < 24; tick++)
                {
                    Step(arena); Assert.IsTrue(direct.StepAgents());
                    Assert.AreEqual(direct.Tick, arena.Match.Tick);
                    Assert.Less(Vector3.Distance(direct.World.Ball.position, arena.Match.World.Ball.position), .00001f);
                    Assert.IsFalse(arena.Match.BallHeld);
                    for (int seat = 0; seat < 4; seat++)
                    {
                        CollectionAssert.AreEqual(direct.ActiveFor(seat).ToArray(), arena.Match.ActiveFor(seat).ToArray(), "Tick " + tick + ", seat " + seat);
                        Assert.Less(Vector3.Distance(direct.World.Players[seat].Paddle.position, arena.Match.World.Players[seat].Paddle.position), .00001f);
                        if (tick == 0) CollectionAssert.AreEqual(snapshots[seat].ToArray(), arena.Agents[seat].LastObservation.ToArray());
                        Assert.AreEqual(0, arena.Agents[seat].LastCommand[16]);
                    }
                }
                for (int seat = 0; seat < 4; seat++)
                {
                    var agent = arena.Agents[seat];
                    Assert.AreEqual(2, agent.DecisionsReceived); Assert.AreEqual(12, agent.ObservedTick);
                    Assert.AreEqual(seat, agent.LastObservation.player);
                    var copy = agent.LastObservation.ToArray(); copy[0] = float.NaN;
                    Assert.IsTrue(float.IsFinite(agent.LastObservation.ToArray()[0]));
                    Assert.AreEqual(seat / 2, agent.GetComponent<BehaviorParameters>().TeamId);
                    Assert.AreEqual(PlayerMlAgentV3.BehaviorName, agent.GetComponent<BehaviorParameters>().BehaviorName);
                }
            }
            finally { Cleanup(root); }
            yield return null;
        }
        [UnityTest]
        public IEnumerator FixedServeRemainsStationaryAndMaskedThroughServiceChangesForEveryInitialServer()
        {
            for (int initialServer=0; initialServer<4; initialServer++)
            {
                var root=new GameObject("Fixed team serve lifecycle fixture");
                Academy.Instance.AutomaticSteppingEnabled=false;
                try
                {
                    using var arena=new PlayerMlTeamArenaV3(root.transform,1302162+initialServer,initialServer,BehaviorType.HeuristicOnly);
                    for (int rally=0;rally<4;rally++)
                    {
                        var match=arena.Match; var rules=match.World.Rules;
                        int server=rules.Server;
                        Assert.IsTrue(match.World.FixedBallServe);
                        Assert.IsFalse(match.BallHeld);Assert.IsTrue(match.StationarySupportActive);
                        var start=match.World.Ball.position;
                        var paddle=match.World.Players[server].Paddle;
                        Assert.Less(Vector3.Distance(start,paddle.position+paddle.rotation*(PlayerStrokeAimV3.FacePoint+Vector3.forward*.25f)),1e-6);
                        foreach(var agent in arena.Agents)agent.HeuristicRelease=1;
                        for(int tick=0;tick<120;tick++)
                        {
                            Step(arena);
                            Assert.Less(Vector3.Distance(start,match.World.Ball.position),1e-6);
                            foreach(var agent in arena.Agents)
                            {
                                Assert.AreEqual(0,agent.LastCommand[16]);
                                Assert.AreEqual(0,match.ActiveFor(agent.Seat)[16]);
                                Assert.AreEqual(agent.Seat,agent.LastObservation.player);
                            }
                        }
                        Assert.AreEqual(RallyPhase.AwaitServe,rules.Phase);
                        Assert.IsFalse(rules.Events.Any(e=>e.kind=="serve"));
                        // Explicit rules fixture: test reset lifecycle, not a learned rally outcome.
                        rules.Fail(rules.ServingTeam,Fault.ServeTimeout,match.World.Time);
                        Assert.IsTrue(arena.ResolveBoundary());
                        Assert.AreEqual(rally+1,arena.Rallies.Count);
                        Assert.AreEqual(server,arena.Rallies.Last().server);
                        Assert.AreEqual(PlayerMlTeamArenaV3.ServeMode,arena.Rallies.Last().serveMode);
                        Assert.AreEqual(0,rules.Score.Sum());Assert.AreEqual(0,match.Tick);
                        Assert.AreNotEqual(server,rules.Server);
                        Assert.IsTrue(match.StationarySupportActive);
                    }
                }
                finally { Cleanup(root); }
                yield return null;
            }
        }

        [UnityTest]
        public IEnumerator RewardGroupsBelongToOnePairOnOneCourt()
        {
            var root = new GameObject("Group isolation fixture");
            Academy.Instance.AutomaticSteppingEnabled = false;
            try
            {
                using var a = new PlayerMlTeamArenaV3(root.transform, 1300601, 0, BehaviorType.HeuristicOnly);
                using var b = new PlayerMlTeamArenaV3(root.transform, 1300602, 1, BehaviorType.HeuristicOnly);
                Assert.AreEqual(4, a.Groups.Concat(b.Groups).Select(g => g.GetId()).Distinct().Count());
                foreach (var arena in new[] {a,b})
                    for (int team = 0; team < 2; team++)
                        CollectionAssert.AreEquivalent(arena.Agents.Skip(team * 2).Take(2), arena.Groups[team].GetRegisteredAgents());
                a.Groups[0].AddGroupReward(.75f);
                a.RequestDecisions(); b.RequestDecisions(); Academy.Instance.EnvironmentStep();
                for (int i = 0; i < 4; i++)
                {
                    Assert.AreEqual(i < 2 ? .75f : 0, Info(a.Agents[i]).groupReward);
                    Assert.AreEqual(0, Info(b.Agents[i]).groupReward);
                    Assert.AreEqual(0, Info(a.Agents[i]).reward);
                    Assert.AreEqual(i / 2, b.Agents[i].GetComponent<BehaviorParameters>().TeamId);
                }
            }
            finally { Cleanup(root); }
            yield return null;
        }
        [UnityTest]
        public IEnumerator RealServeTimeoutEndsBothGroupsAndChangesServiceWithoutAFreePoint()
        {
            var root = new GameObject("Serve timeout fixture");
            Academy.Instance.AutomaticSteppingEnabled = false;
            try
            {
                using var arena = new PlayerMlTeamArenaV3(root.transform, 1300603, 0, BehaviorType.HeuristicOnly);
                int ticks = 0;
                while (arena.Rallies.Count == 0 && ticks++ < 2410) Step(arena);
                Assert.AreEqual(1, arena.Rallies.Count);
                var rally = arena.Rallies[0];
                Assert.AreEqual("ServeTimeout", rally.fault); Assert.AreEqual(1, rally.winner);
                Assert.IsFalse(rally.interrupted); Assert.IsFalse(rally.serveAccepted);
                Assert.AreEqual(0, arena.Match.World.Rules.Score.Sum()); Assert.AreEqual(1, arena.Match.World.Rules.ServingTeam);
                Assert.AreEqual(2, arena.Match.World.Rules.Server); Assert.AreEqual(0, arena.Match.Tick);
                Assert.IsFalse(arena.Match.BallHeld);
                Assert.IsTrue(arena.Match.StationarySupportActive);
                for (int i = 0; i < 4; i++)
                {
                    var info = Info(arena.Agents[i]);
                    Assert.IsTrue(info.done); Assert.IsFalse(info.maxStepReached);
                    Assert.AreEqual(i < 2 ? -1 : 1, info.groupReward); Assert.AreEqual(0, info.reward);
                    Assert.AreEqual(rally.physicsTicks, arena.Agents[i].LastObservation.tick);
                    CollectionAssert.AreEqual(new float[18], arena.Match.ActiveFor(i).ToArray());
                }
                Step(arena);
                Assert.AreEqual(0, arena.Agents[0].ObservedTick);
                Assert.AreEqual(0, arena.Match.ActiveFor(0)[16]);
            }
            finally { Cleanup(root); }
            yield return null;
        }
        [UnityTest]
        public IEnumerator AGameSafetyLimitInterruptsAllFourPlayersWithoutInventingAWinner()
        {
            var root = new GameObject("Game truncation fixture");
            Academy.Instance.AutomaticSteppingEnabled = false;
            try
            {
                using var arena = new PlayerMlTeamArenaV3(root.transform, 1300604, 0, BehaviorType.HeuristicOnly, maximumGameTicks:24);
                for (int i = 0; i < 24; i++) Step(arena);
                Assert.IsTrue(arena.Finished); Assert.IsFalse(arena.Result.complete); Assert.AreEqual(-1, arena.Result.winner);
                Assert.AreEqual(24, arena.Result.physicsTicks); Assert.AreEqual(0, arena.Result.score0 + arena.Result.score1);
                Assert.AreEqual(1, arena.Result.truncatedRallies); Assert.IsFalse(arena.Match.World.Rules.Dead);
                foreach (var agent in arena.Agents)
                {
                    var info = Info(agent); Assert.IsTrue(info.done); Assert.IsTrue(info.maxStepReached);
                    Assert.AreEqual(0, info.reward); Assert.AreEqual(0, info.groupReward);
                    Assert.AreEqual(24, agent.LastObservation.tick);
                }
                Assert.Throws<InvalidOperationException>(() => arena.StepPhysics());
            }
            finally { Cleanup(root); }
            yield return null;
        }
        [UnityTest]
        public IEnumerator LateVolleyFaultIsResolvedBeforeAwardingTeamReward()
        {
            var root = new GameObject("Late momentum lifecycle fixture");
            Academy.Instance.AutomaticSteppingEnabled = false;
            try
            {
                using var arena = new PlayerMlTeamArenaV3(root.transform, 1300605, 0, BehaviorType.HeuristicOnly);
                for (int i = 0; i < 12; i++) Step(arena);
                var r = arena.Match.World.Rules;
                // Synthetic rule fixture only: never training experience or a claim of a learned stroke.
                r.Serve(0,true,true,true,true,false,false,false,.01f);
                r.Bounce(new Vector3(r.ServiceX(r.DesignatedReceiver),0,4),.02f); r.Hit(2,.03f);
                r.Bounce(new Vector3(0,0,-4),.04f); r.Hit(0,.05f); r.Hit(2,.06f); r.Hit(0,.07f);
                r.Feet(2,false,true,true,.08f); r.Fail(1,Fault.Out,.09f);
                Assert.AreEqual(0,r.Winner); Assert.IsTrue(r.VolleyMomentumPending(0));
                Assert.IsFalse(arena.ResolveBoundary()); Assert.AreEqual(0,arena.Rallies.Count);
                r.Feet(0,true,false,false,.10f);
                Assert.AreEqual(1,r.Winner); Assert.IsFalse(arena.ResolveBoundary());
                r.Feet(0,false,true,true,.11f);
                Assert.IsTrue(arena.ResolveBoundary());
                Assert.AreEqual(1,arena.Rallies[0].winner); Assert.AreEqual("KitchenMomentum",arena.Rallies[0].fault);
                Assert.AreEqual(0,r.Score.Sum()); Assert.AreEqual(1,r.ServingTeam);
                for (int i=0;i<4;i++) Assert.AreEqual(i<2?-1:1,Info(arena.Agents[i]).groupReward);
            }
            finally { Cleanup(root); }
            yield return null;
        }
        [UnityTest]
        public IEnumerator AcademyResetDuringDecisionRetiresBothCourtsWithoutAdvancingPhysics()
        {
            var root=new GameObject("Framework reset integration fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlTeamsV3>();run.RequireTrainer=false;run.AutoRun=false;
            run.FirstSeed=1300700;run.SeedCount=4;run.ArenaCount=2;root.SetActive(true);run.InitializeRun();
            var academy=Academy.Instance;
            var flags=BindingFlags.Instance|BindingFlags.NonPublic;
            var eventInfo=typeof(Academy).GetEvent("DecideAction",flags);
            bool fired=false;
            Action reset=()=>{if(fired)return;fired=true;typeof(Academy).GetMethod("OnResetCommand",flags).Invoke(academy,null);};
            try
            {
                for(int i=0;i<12;i++)run.StepOneTick();
                Assert.AreEqual(0,run.Report.frameworkResets);
                eventInfo.GetAddMethod(true).Invoke(academy,new object[]{reset});
                run.StepOneTick();
                Assert.IsTrue(fired);Assert.AreEqual(1,run.Report.frameworkResets);
                Assert.AreEqual(24,run.Report.physicsTicks,"Reset must discard this action batch before any court advances.");
                Assert.AreEqual(2,run.Games.Count);Assert.AreEqual(2,run.Report.incompleteGames);
                foreach(var game in run.Games){Assert.IsFalse(game.complete);Assert.AreEqual(-1,game.winner);Assert.AreEqual("framework_reset",game.reason);Assert.AreEqual(12,game.physicsTicks);Assert.AreEqual(0,game.score0+game.score1);}
                CollectionAssert.AreEqual(new[]{1300702,1300703},run.ActiveArenas.Select(a=>a.Seed));
                foreach(var arena in run.ActiveArenas)Assert.AreEqual(0,arena.Match.Tick);
                for(int i=0;i<24;i++)run.StepOneTick();
                foreach(var arena in run.ActiveArenas)foreach(var agent in arena.Agents){Assert.AreEqual(12,agent.ObservedTick);Assert.AreEqual(2,agent.DecisionsReceived);}
                Assert.AreEqual("running",run.Report.status);
            }
            finally {eventInfo.GetRemoveMethod(true).Invoke(academy,new object[]{reset});Cleanup(root);}
            yield return null;
        }

        [UnityTest]
        public IEnumerator ShutdownAccountsForEveryUnfinishedCourtWithoutInventingWins()
        {
            var root=new GameObject("Shutdown accounting fixture");root.SetActive(false);
            var run=root.AddComponent<PlayerMlTeamsV3>();run.RequireTrainer=false;run.AutoRun=false;
            run.FirstSeed=1300704;run.SeedCount=2;run.ArenaCount=2;root.SetActive(true);run.InitializeRun();
            var report=run.Report;var games=run.Games;
            try { for(int i=0;i<7;i++)run.StepOneTick(); }
            finally { Cleanup(root); }
            Assert.AreEqual("stopped",report.status);Assert.AreEqual(2,report.finishedGames);
            Assert.AreEqual(2,report.incompleteGames);Assert.AreEqual(0,report.completeGames);
            Assert.AreEqual(report.physicsTicks,games.Sum(g=>g.physicsTicks));
            foreach(var game in games){Assert.AreEqual("environment_stopped",game.reason);Assert.AreEqual(7,game.physicsTicks);Assert.IsFalse(game.complete);Assert.AreEqual(-1,game.winner);}
            yield return null;
        }

        [UnityTest]
        public IEnumerator GameCompletionUsesElevenPointsAndCannotAwardAnotherPoint()
        {
            var root = new GameObject("Game scoring lifecycle fixture");
            Academy.Instance.AutomaticSteppingEnabled = false;
            try
            {
                using var arena = new PlayerMlTeamArenaV3(root.transform, 1300606, 0, BehaviorType.HeuristicOnly);
                for (int point=1;point<=11;point++)
                {
                    for (int i=0;i<12;i++) Step(arena);
                    // Synthetic outcome exercises the real score/reset lifecycle, not game skill.
                    arena.Match.World.Rules.Fail(1,Fault.BodyContact,arena.Match.World.Time);
                    Assert.IsTrue(arena.ResolveBoundary());
                    Assert.AreEqual(point,arena.Match.World.Rules.Score[0]);
                    Assert.AreEqual(point==11,arena.Finished);
                    foreach(var agent in arena.Agents)
                        Assert.AreEqual(point/11f,agent.LastObservation.ToArray()[agent.Seat<2?50:51],.000001f);
                }
                Assert.IsTrue(arena.Result.complete); Assert.AreEqual(0,arena.Result.winner);
                Assert.AreEqual(11,arena.Result.rallies); Assert.AreEqual(11,arena.Result.score0);
                Assert.IsFalse(arena.ResolveBoundary()); Assert.AreEqual(11,arena.Match.World.Rules.Score[0]);
            }
            finally { Cleanup(root); }
            yield return null;
        }
    }
}
