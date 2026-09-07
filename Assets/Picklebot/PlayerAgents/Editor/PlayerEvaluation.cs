using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Picklebot.Doubles;
using Picklebot.Doubles.Editor;
using UnityEditor;
using UnityEngine;

namespace Picklebot.PlayerAgents.Editor
{
    [Serializable] public sealed class PlayerRallyResult
    {
        public int gameSeed, winner, gameWinner, hits;
        public string fault;
        public int[] score, legalHits;
        public float seconds;
    }
    [Serializable] public sealed class PlayerEvaluationReport
    {
        public string actorHash, sourceHash, configurationHash, contactModelHash, protocolHash, createdUtc, mode;
        public int seed, games;
        public double wallSeconds;
        public List<PlayerRallyResult> rallies = new List<PlayerRallyResult>();
        public List<PlayerMetrics> gameMetrics = new List<PlayerMetrics>();
    }
    public static class PlayerEvaluation
    {
        public static string Status { get; private set; } = "idle";
        public static bool Running => match != null;
        private static PlayerMatch match;
        private static PlayerActorModel actor;
        private static PlayerEvaluationReport report;
        private static int wanted, game, completed;
        private static int[] previousHits;
        private static bool sample;
        private static System.Random random;
        private static string outputPath;
        private static Stopwatch watch;

        public static void Start(string actorPath, int rallies = 32, int seed = 1100100, bool sampled = false)
        {
            if (!EditorApplication.isPlaying || Running || PlayerTeacher.Running || PlayerDiagnostics.Running || PlayerControlProbe.Running || PlayerCurriculum.Running || PlayerCompetition.Running)
                throw new InvalidOperationException("Start Play and finish other jobs first.");
            if (rallies < 1 || seed < 1100000 || seed + rallies >= 1200000)
                throw new ArgumentException("This diagnostic evaluator only uses development seeds.");
            actor = PlayerActorModel.Load(File.ReadAllText(actorPath));
            if (actor.sourceHash != PlayerDiagnostics.SourceHash()) throw new InvalidOperationException("Actor source is stale.");
            string contactHash = ContactTraining.Hash(File.ReadAllText(ContactTraining.ModelPath));
            string protocolHash = ContactTraining.Hash(File.ReadAllText("config/player-agents/evaluation-v1.json"));
            if (actor.contactModelHash != contactHash || actor.protocolHash != protocolHash) throw new InvalidOperationException("Actor contact model or protocol is stale.");
            wanted = rallies; game = 0; sample = sampled; random = new System.Random(seed);
            outputPath = Path.Combine(Path.GetDirectoryName(actorPath), "development-selfplay-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json");
            report = new PlayerEvaluationReport { actorHash = ContactTraining.Hash(File.ReadAllText(actorPath)), sourceHash = PlayerDiagnostics.SourceHash(),
                contactModelHash = contactHash, protocolHash = protocolHash, seed = seed, createdUtc = DateTime.UtcNow.ToString("O"),
                mode = sampled ? "development selfplay / sampled actor / not a baseline comparison" : "development selfplay / deterministic actor / not a baseline comparison" };
            watch = Stopwatch.StartNew(); NewGame(); EditorApplication.update += Tick;
        }

        private static void NewGame()
        {
            match?.Dispose();
            var policies = Enumerable.Range(0, 4).Select(i => (IPlayerPolicy)new PlayerActor(actor, sample)).ToArray();
            match = new PlayerMatch(false, policies, ContactModel.Load(File.ReadAllText(ContactTraining.ModelPath)), report.seed + game) { AutoNext = false };
            report.configurationHash = match.World.Configuration.ConfigurationHash;
            if (actor.configurationHash != report.configurationHash) throw new InvalidOperationException("Actor physics configuration is stale.");
            report.gameMetrics.Add(match.Metrics); previousHits = new int[4]; completed = 0; VaryServe();
        }
        private static void VaryServe() => match.ServeJitter = new Vector2((float)(random.NextDouble() * .6 - .3), (float)(random.NextDouble() * .8 - .4));
        private static void Tick()
        {
            try
            {
                double until = EditorApplication.timeSinceStartup + .02;
                while (match != null && EditorApplication.timeSinceStartup < until)
                {
                    match.Step();
                    if (match.CompletedRallies != completed)
                    {
                        completed = match.CompletedRallies; var r = match.World.Rules;
                        var hits = Enumerable.Range(0, 4).Select(i => match.Metrics.legalHits[i] - previousHits[i]).ToArray();
                        previousHits = (int[])match.Metrics.legalHits.Clone();
                        report.rallies.Add(new PlayerRallyResult { gameSeed = report.seed + game, winner = r.Winner, gameWinner = r.GameWinner,
                            hits = r.Hits, fault = r.LastFault.ToString(), score = (int[])r.Score.Clone(), legalHits = hits, seconds = match.World.Time });
                        Status = $"development selfplay: {report.rallies.Count}/{wanted}; hits {r.Hits}; {r.LastFault}";
                        if (r.GameWinner >= 0) report.games++;
                        if (report.rallies.Count >= wanted) { Finish(); break; }
                        if (r.GameWinner >= 0) { game++; NewGame(); } else { match.Next(); VaryServe(); }
                    }
                }
            }
            catch (Exception e) { Cancel(); Status = "failed: " + e; UnityEngine.Debug.LogException(e); }
        }
        private static void Finish()
        {
            match.Dispose(); match = null; EditorApplication.update -= Tick; report.wallSeconds = watch.Elapsed.TotalSeconds;
            if (report.sourceHash != PlayerDiagnostics.SourceHash()) throw new InvalidOperationException("Source changed during evaluation.");
            File.WriteAllText(outputPath, JsonUtility.ToJson(report, true)); Status = "complete: " + outputPath;
        }
        public static void Cancel() { EditorApplication.update -= Tick; match?.Dispose(); match = null; Status = "cancelled"; }
    }
}
