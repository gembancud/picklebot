using System;
using System.Collections.Generic;
using System.Linq;
using Picklebot.Doubles;
using Picklebot.PlayerControlsIntegration;
using Unity.InferenceEngine;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Policies;
using UnityEngine;

namespace Picklebot.PlayerLearning
{
    [Serializable] public sealed class MlTeamRallyV3
    {
        public int seed, index, server, winner, physicsTicks, totalPhysicsTicks, score0, score1;
        public bool interrupted, unresolvedMomentum, serveAccepted, legalServe;
        public string fault, reason;
        public int[] legalNonServeHits;
        public string serveMode = PlayerMlTeamArenaV3.ServeMode;
    }
    [Serializable] public sealed class MlTeamGameV3
    {
        public int seed, initialServer, winner, physicsTicks, decisions, rallies, truncatedRallies, score0, score1;
        public int[] legalNonServeHits;
        public string serveMode = PlayerMlTeamArenaV3.ServeMode;
        public string reason;
        public bool complete;
    }

    // A training episode is a settled rally. Side-out scoring persists across
    // rallies until a complete game or an explicitly recorded safety truncation.
    public sealed class PlayerMlTeamArenaV3 : IDisposable
    {
        public const string ContractVersion = "mlagents-v3-four-players-rally-groups-2-fixed-serve";
        public const string ServeMode = "fixed-ball-prototype";
        public readonly PlayerLearningMatchV3 Match;
        public readonly PlayerMlAgentV3[] Agents = new PlayerMlAgentV3[4];
        public readonly SimpleMultiAgentGroup[] Groups = {new(), new()};
        public readonly List<MlTeamRallyV3> Rallies = new();
        public readonly int Seed, InitialServer;
        public readonly int MaximumRallies, MaximumGameTicks;
        public MlTeamGameV3 Result { get; private set; }
        public bool Finished => Result != null;
        public event Action<MlTeamRallyV3> RallyFinished;
        private int server, episodeStartTick;
        private bool disposed;

        public PlayerMlTeamArenaV3(Transform parent, int seed, int initialServer,
            BehaviorType behaviorType, ModelAsset model = null, int maximumRallies = 300,
            int maximumGameTicks = 864000, bool visible = false)
        {
            if (parent == null || !parent.gameObject.activeInHierarchy) throw new ArgumentException("An active arena owner is required.");
            if (!((seed >= 1000000 && seed < 1200000) || (seed >= 1300000 && seed < 1400000)))
                throw new ArgumentException("Training adapter cannot consume final evaluation seeds.");
            if (initialServer < 0 || initialServer > 3 || maximumRallies < 1 || maximumGameTicks < 1)
                throw new ArgumentException("Invalid game configuration.");
            if (behaviorType == BehaviorType.InferenceOnly && model == null) throw new ArgumentException("Inference requires a model.");
            if (behaviorType != BehaviorType.InferenceOnly && model != null) throw new ArgumentException("Do not mix training or heuristic control with an inference model.");
            Seed = seed; InitialServer = initialServer; MaximumRallies = maximumRallies; MaximumGameTicks = maximumGameTicks;
            Match = new PlayerLearningMatchV3(visible, initialServer); server = initialServer;
            try
            {
                // Prototype serve: stationary until physical contact, with no release action.
                Match.InitializeStationaryServe();
                for (int i = 0; i < 4; i++)
                {
                    int seat = i;
                    var go = new GameObject("Team " + i / 2 + " player " + i);
                    go.SetActive(false); go.transform.SetParent(parent);
                    var parameters = go.AddComponent<BehaviorParameters>();
                    parameters.BehaviorName = PlayerMlAgentV3.BehaviorName;
                    parameters.TeamId = i / 2;
                    parameters.BrainParameters.VectorObservationSize = PlayerObservationV3.Count;
                    parameters.BrainParameters.NumStackedVectorObservations = 1;
                    parameters.BrainParameters.ActionSpec = new ActionSpec(PlayerMlAgentV3.ContinuousCount, new[] {2});
                    parameters.BehaviorType = behaviorType; parameters.Model = model; parameters.DeterministicInference = true;
                    var agent = go.AddComponent<PlayerMlAgentV3>();
                    agent.Bind(seat, () => PlayerObservationV3.Capture(Match, seat, Match.Tick),
                        () => Match.BallHeld && !Match.World.Rules.Dead && Match.World.Rules.Server == seat);
                    agent.Learning = true; Agents[i] = agent; go.SetActive(true);
                    Groups[i / 2].RegisterAgent(agent);
                }
                Match.AttachPolicies(Agents.Cast<IPlayerPolicyV3>().ToArray(), seed);
            }
            catch { Dispose(); throw; }
        }
        // The run owner requests every court before advancing the shared Academy.
        public void RequestDecisions()
        {
            if (!Finished && Match.Tick % PlayerDecisionLoopV3.DecisionTicks == 0)
                foreach (var agent in Agents) agent.RequestDecision();
        }
        public void StepPhysics()
        {
            if (Finished) throw new InvalidOperationException("Game already finished.");
            if (!Match.StepAgents()) throw new InvalidOperationException("Physical control failure: " + Match.Failure);
            ResolveBoundary();
        }
        public bool ResolveBoundary()
        {
            if (Finished) return false;
            var rules = Match.World.Rules;
            bool pending = Enumerable.Range(0, 4).Any(rules.VolleyMomentumPending);
            if (rules.Dead && !pending)
            {
                // Capture events before TryResetRally clears them. No reward or
                // score is committed while a late volley fault remains possible.
                var rally = CaptureRally(rules.Winner < 0, false, "settled_rally");
                bool reset = Match.TryResetRally(() => EndGroups(rally.winner, rally.interrupted));
                if (!reset && rules.GameWinner < 0) throw new InvalidOperationException("A settled rally failed to resolve.");
                rally.score0 = rules.Score[0]; rally.score1 = rules.Score[1];
                Record(rally);
                if (rules.GameWinner >= 0) Finish("game_complete", rules.GameWinner);
                else if (Rallies.Count >= MaximumRallies) Finish("maximum_rallies", -1);
                else if (Match.TotalTicks >= MaximumGameTicks) Finish("maximum_game_time", -1);
                else { server = rules.Server; episodeStartTick = Match.TotalTicks; }
                return true;
            }
            if (Match.TotalTicks >= MaximumGameTicks || (rules.Dead && pending && Match.World.Time >= 30))
            {
                string reason = pending ? "unresolved_volley_momentum" : "maximum_game_time";
                var rally = CaptureRally(true, pending, reason);
                EndGroups(-1, true); Record(rally); Finish(reason, -1);
                return true;
            }
            return false;
        }
        public void InterruptForFrameworkReset() => InterruptWithoutSdkTermination("framework_reset");
        public void InterruptForShutdown() => InterruptWithoutSdkTermination("environment_stopped");
        private void InterruptWithoutSdkTermination(string reason)
        {
            if (Finished) return;
            // Reset/shutdown is owned by the SDK. Record the interrupted physical
            // trajectory without issuing another terminal or reward to its policies.
            Record(CaptureRally(true, Enumerable.Range(0,4).Any(Match.World.Rules.VolleyMomentumPending), reason));
            Finish(reason, -1);
        }
        private MlTeamRallyV3 CaptureRally(bool interrupted, bool pending, string reason)
        {
            var rules = Match.World.Rules;
            return new MlTeamRallyV3 { seed = Seed, index = Rallies.Count, server = server,
                winner = interrupted ? -1 : rules.Winner, interrupted = interrupted, unresolvedMomentum = pending,
                physicsTicks = Match.TotalTicks - episodeStartTick, totalPhysicsTicks = Match.TotalTicks,
                score0 = rules.Score[0], score1 = rules.Score[1], fault = rules.LastFault.ToString(), reason = reason,
                serveAccepted = rules.Events.Any(e => e.kind == "serve"),
                legalServe = rules.Events.Any(e => e.kind == "serve") && rules.Events.Any(e => e.kind == "bounce"),
                legalNonServeHits = Enumerable.Range(0, 4).Select(i => rules.Events.Count(e => e.kind == "hit" && e.player == i)).ToArray() };
        }
        private void EndGroups(int winner, bool interrupted)
        {
            for (int team = 0; team < 2; team++)
            {
                Groups[team].SetGroupReward(interrupted ? 0 : team == winner ? 1 : -1);
                if (interrupted) Groups[team].GroupEpisodeInterrupted();
                else Groups[team].EndGroupEpisode();
            }
        }
        private void Record(MlTeamRallyV3 rally) { Rallies.Add(rally); RallyFinished?.Invoke(rally); }
        private void Finish(string reason, int winner)
        {
            Result = new MlTeamGameV3 { seed = Seed, initialServer = InitialServer, winner = winner, reason = reason,
                complete = winner >= 0, physicsTicks = Match.TotalTicks, decisions = Agents.Sum(a => a.DecisionsReceived),
                rallies = Rallies.Count, truncatedRallies = Rallies.Count(r => r.interrupted),
                score0 = Match.World.Rules.Score[0], score1 = Match.World.Rules.Score[1],
                legalNonServeHits = Enumerable.Range(0, 4).Select(i => Rallies.Sum(r => r.legalNonServeHits[i])).ToArray() };
        }
        public void Dispose()
        {
            if (disposed) return; disposed = true;
            foreach (var agent in Agents) if (agent != null) UnityEngine.Object.DestroyImmediate(agent.gameObject);
            foreach (var group in Groups) group.Dispose();
            Match?.Dispose();
        }
    }
}
