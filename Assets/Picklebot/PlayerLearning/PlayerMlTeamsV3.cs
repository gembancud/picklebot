using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Unity.InferenceEngine;
using Unity.MLAgents;
using Unity.MLAgents.Policies;
using UnityEngine;

namespace Picklebot.PlayerLearning
{
    [Serializable] public sealed class MlTeamsReportV3
    {
        public string contract = PlayerMlTeamArenaV3.ContractVersion;
        public string serveMode = PlayerMlTeamArenaV3.ServeMode;
        public string episodeUnit = "settled_rally", status, failure, sourceIdentity, split;
        public bool trainerConnected;
        public int frameworkResets;
        public int firstSeed, seedCount, arenas, startedGames, finishedGames, completeGames, incompleteGames, decisions, physicsTicks, rallies;
    }
    // The sole Academy/physics owner for this scene. Training Elo is rally Elo;
    // separately recorded complete games remain the gameplay evaluation unit.
    public sealed class PlayerMlTeamsV3 : MonoBehaviour
    {
        public int FirstSeed = 1052480, SeedCount = 4, ArenaCount = 1, TicksPerFrame = 48;
        public int MaximumRallies = 300, MaximumGameTicks = 864000;
        public bool RequireTrainer = true, AutoRun = true, Visible;
        public ModelAsset InferenceModel;
        public string EvidenceDirectory, SourceIdentity;
        public MlTeamsReportV3 Report { get; private set; }
        public readonly List<MlTeamGameV3> Games = new();
        private readonly List<PlayerMlTeamArenaV3> arenas = new();
        public IReadOnlyList<PlayerMlTeamArenaV3> ActiveArenas => arenas;
        private StreamWriter gameEvidence, rallyEvidence;
        private bool initialized, stopped, academyStepped, environmentResetPending;
        private int nextIndex;
        private BehaviorType behavior;
        public void InitializeRun()
        {
            if (initialized || !gameObject.activeInHierarchy) throw new InvalidOperationException("Activate a fresh run before initialization.");
            int minimum = RequireTrainer ? 1000000 : InferenceModel != null ? 1100000 : 1300000;
            if (FirstSeed < minimum || (long)FirstSeed + SeedCount > minimum + 100000 || ArenaCount < 1 || ArenaCount > 16 ||
                SeedCount < ArenaCount || TicksPerFrame < 1 || MaximumRallies < 1 || MaximumGameTicks < 1)
                throw new ArgumentException("Invalid run allocation or limits.");
            if (RequireTrainer && InferenceModel != null) throw new ArgumentException("Resume trainer checkpoints through Python.");
            var academy = Academy.Instance;
            if (RequireTrainer != academy.IsCommunicatorOn) throw new InvalidOperationException("Unexpected trainer connection; no controller fallback.");
            academy.AutomaticSteppingEnabled = false;
            behavior = RequireTrainer ? BehaviorType.Default : InferenceModel != null ? BehaviorType.InferenceOnly : BehaviorType.HeuristicOnly;
            Report = new MlTeamsReportV3 { status = "running", failure = "", sourceIdentity = SourceIdentity,
                split = RequireTrainer ? "training" : InferenceModel != null ? "development" : "interactive",
                trainerConnected = academy.IsCommunicatorOn, firstSeed = FirstSeed, seedCount = SeedCount, arenas = ArenaCount };
            if (!string.IsNullOrEmpty(EvidenceDirectory))
            {
                Directory.CreateDirectory(EvidenceDirectory);
                gameEvidence = new StreamWriter(new FileStream(Path.Combine(EvidenceDirectory, "games.jsonl"), FileMode.CreateNew)) { AutoFlush = true };
                rallyEvidence = new StreamWriter(new FileStream(Path.Combine(EvidenceDirectory, "rallies.jsonl"), FileMode.CreateNew)) { AutoFlush = true };
            }
            initialized = true;
            academy.OnEnvironmentReset += OnFrameworkReset;
            for (int i = 0; i < ArenaCount; i++) arenas.Add(NewArena());
            SaveReport();
        }
        private PlayerMlTeamArenaV3 NewArena()
        {
            int index = nextIndex++;
            var arena = new PlayerMlTeamArenaV3(transform, FirstSeed + index, index % 4, behavior, InferenceModel,
                MaximumRallies, MaximumGameTicks, Visible && ArenaCount == 1);
            arena.RallyFinished += rally =>
            {
                Report.rallies++; rallyEvidence?.WriteLine(JsonUtility.ToJson(rally));
                var stats = Academy.Instance.StatsRecorder;
                stats.Add("Picklebot/RallyInterrupted", rally.interrupted ? 1 : 0);
                stats.Add("Picklebot/LegalServeLanding", rally.legalServe ? 1 : 0);
                stats.Add("Picklebot/LegalNonServeHits", rally.legalNonServeHits.Sum());
            };
            Report.startedGames = nextIndex;
            return arena;
        }
        private void Start() { if (!initialized) InitializeRun(); }
        private void Update()
        {
            if (!initialized || stopped || !AutoRun) return;
            try { for (int i = 0; i < TicksPerFrame && !stopped; i++) StepOneTick(); }
            catch (Exception error)
            {
                stopped = true; Report.status = "failed"; Report.failure = error.ToString(); SaveReport(); Debug.LogException(error);
            }
        }
        public void StepOneTick()
        {
            if (!initialized || stopped) throw new InvalidOperationException("Run is not active.");
            if (environmentResetPending) { ApplyFrameworkReset(); return; }
            foreach (var arena in arenas) arena.RequestDecisions();
            int before = arenas.Sum(a => a.Agents.Sum(p => p.DecisionsReceived));
            Academy.Instance.EnvironmentStep(); academyStepped = true;
            Report.decisions += arenas.Sum(a => a.Agents.Sum(p => p.DecisionsReceived)) - before;
            if (environmentResetPending) { ApplyFrameworkReset(); return; }
            for (int i = 0; i < arenas.Count; i++)
            {
                var arena = arenas[i]; if (arena.Finished) continue;
                arena.StepPhysics(); Report.physicsTicks++;
                if (!arena.Finished) continue;
                Games.Add(arena.Result); Report.finishedGames++;
                if (arena.Result.complete) Report.completeGames++; else Report.incompleteGames++;
                gameEvidence?.WriteLine(JsonUtility.ToJson(arena.Result)); SaveReport();
                if (nextIndex < SeedCount) { arena.Dispose(); arenas[i] = NewArena(); }
            }
            if (arenas.All(a => a.Finished))
            {
                stopped = true; Report.status = "seed_budget_complete";
                Academy.Instance.EnvironmentStep(); SaveReport();
            }
        }
        private void OnFrameworkReset()
        {
            // Ignore the initial Academy reset before any physical step. Later
            // resets can arrive inside policy communication during EnvironmentStep.
            if (academyStepped && !stopped) environmentResetPending = true;
        }
        private void ApplyFrameworkReset()
        {
            environmentResetPending = false; Report.frameworkResets++;
            for (int i=0;i<arenas.Count;i++)
            {
                var arena=arenas[i]; if (arena.Finished) continue;
                arena.InterruptForFrameworkReset();
                Games.Add(arena.Result); Report.finishedGames++; Report.incompleteGames++;
                gameEvidence?.WriteLine(JsonUtility.ToJson(arena.Result));
                if (nextIndex<SeedCount) { arena.Dispose(); arenas[i]=NewArena(); }
            }
            if (arenas.All(a=>a.Finished)) { stopped=true; Report.status="seed_budget_complete"; }
            SaveReport();
        }
        private void SaveReport()
        {
            if (Report != null && !string.IsNullOrEmpty(EvidenceDirectory))
                File.WriteAllText(Path.Combine(EvidenceDirectory, "report.json"), JsonUtility.ToJson(Report, true));
        }
        private void OnDestroy()
        {
            if (Academy.IsInitialized) Academy.Instance.OnEnvironmentReset -= OnFrameworkReset;
            foreach (var arena in arenas)
            {
                if (Report != null && !arena.Finished)
                {
                    arena.InterruptForShutdown(); Games.Add(arena.Result);
                    Report.finishedGames++; Report.incompleteGames++;
                    gameEvidence?.WriteLine(JsonUtility.ToJson(arena.Result));
                }
                arena.Dispose();
            }
            arenas.Clear();
            gameEvidence?.Dispose(); rallyEvidence?.Dispose();
            if (Report != null && Report.status == "running") Report.status = "stopped";
            SaveReport(); if (Academy.IsInitialized) Academy.Instance.AutomaticSteppingEnabled = true;
        }
    }
}
