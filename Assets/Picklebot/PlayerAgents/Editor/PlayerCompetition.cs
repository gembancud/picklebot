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
    [Serializable] public sealed class PlayerExperience
    {
        public string episode;
        public int gameSeed, candidateTeam, rally, player, tick;
        public float[] observation, criticObservation;
        public PlayerPolicySample sample;
        public float reward;
        public bool terminal;
    }
    [Serializable] public sealed class CompetitiveRally
    {
        public int gameSeed, candidateTeam, winner, hits;
        public string fault;
        public int[] score, legalHits;
        public float seconds;
    }
    [Serializable] public sealed class CompetitiveGame
    {
        public int gameSeed, candidateTeam, winner, rallies;
        public bool complete;
        public string reason;
        public int[] score;
        public PlayerMetrics metrics;
    }
    [Serializable] public sealed class CompetitionReport
    {
        public string status, sourceHash, actorHash, actorTrainingSourceHash, opponentHash, opponentTrainingSourceHash, opponentMode;
        public string configurationHash, contactModelHash, protocolHash, baselineManifestHash, createdUtc, dataPath, split, rewardMode;
        public int seed, rows, initialCandidateTeam;
        public bool sampledActor, alternateEnds, historicalCandidate;
        public double wallSeconds;
        public List<CompetitiveRally> rallies = new List<CompetitiveRally>();
        public List<CompetitiveGame> games = new List<CompetitiveGame>();
    }

    // Development evaluation and local on-policy collection. No final seeds.
    // Saved opponent control never selects an action for a candidate player.
    public static class PlayerCompetition
    {
        public static bool Running => match != null;
        public static string Status { get; private set; } = "idle";
        private static PlayerMatch match;
        private static PlayerActorModel actor, opponent;
        private static CompetitionReport report;
        private static StreamWriter writer;
        private static Stopwatch watch;
        private static System.Random serveRandom;
        private static readonly List<PlayerExperience> episode = new List<PlayerExperience>();
        private static int wanted, game, completed, team;
        private static int[] previousHits;
        private static bool sampledBaseline;
        private static double completedGameSeconds;
        private static string output;

        public static void Start(string actorPath, int rallies = 64, int seed = 1000600, bool development = false,
            bool sampledActor = true, string rewardMode = "rally_win", string opponentActorPath = "", bool sampleBaseline = true,
            int candidateTeam = 0, bool alternateEnds = true, bool allowHistoricalCandidate = false)
        {
            if (!EditorApplication.isPlaying || Running || PlayerCurriculum.Running || PlayerEvaluation.Running || PlayerTeacher.Running || PlayerControlProbe.Running || PlayerDiagnostics.Running)
                throw new InvalidOperationException("Start Play and finish other jobs first.");
            int lower = development ? 1100000 : 1000000;
            if (rallies < 1 || rallies > 10000 || seed < lower || seed + rallies + 1000 >= lower + 100000 || candidateTeam < 0 || candidateTeam > 1
                || (rewardMode != "rally_win" && rewardMode != "game_win") || (!development && !sampledActor))
                throw new ArgumentException("Invalid competitive collection settings or seed partition.");
            actor = PlayerActorModel.Load(File.ReadAllText(actorPath));
            opponent = string.IsNullOrEmpty(opponentActorPath) ? null : PlayerActorModel.Load(File.ReadAllText(opponentActorPath));
            string source = PlayerDiagnostics.SourceHash();
            if (actor.sourceHash != source && !allowHistoricalCandidate) throw new InvalidOperationException("Actor source differs; historical development use must be explicit.");
            string contactHash = ContactTraining.Hash(File.ReadAllText(ContactTraining.ModelPath));
            string protocolHash = ContactTraining.Hash(File.ReadAllText("config/player-agents/evaluation-v1.json"));
            foreach (var model in new[] { actor, opponent })
                if (model != null && (model.contactModelHash != contactHash || model.protocolHash != protocolHash))
                    throw new InvalidOperationException("Actor contact or protocol is incompatible.");
            string stem = Path.Combine(PlayerDiagnostics.Output, "competition-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss"));
            output = stem + ".json"; wanted = rallies; game = 0; sampledBaseline = sampleBaseline;
            serveRandom = new System.Random(seed); watch = Stopwatch.StartNew(); episode.Clear();
            report = new CompetitionReport { status = "running", sourceHash = source, actorHash = ContactTraining.Hash(File.ReadAllText(actorPath)),
                actorTrainingSourceHash = actor.sourceHash, opponentHash = ContactTraining.Hash(File.ReadAllText(opponent == null ? "Assets/Picklebot/Doubles/Models/teams.json" : opponentActorPath)),
                opponentTrainingSourceHash = opponent?.sourceHash ?? "frozen doubles baseline", opponentMode = opponent != null ? "older actor / sampled" : sampleBaseline ? "baseline / sampled" : "baseline / maximum probability",
                contactModelHash = contactHash, protocolHash = protocolHash, baselineManifestHash = ContactTraining.Hash(File.ReadAllText(Path.Combine(PlayerDiagnostics.Output, "baseline-manifest.json"))),
                createdUtc = DateTime.UtcNow.ToString("O"), dataPath = development ? "" : stem + ".jsonl", split = development ? "development" : "training",
                seed = seed, rewardMode = rewardMode, sampledActor = sampledActor, initialCandidateTeam = candidateTeam, alternateEnds = alternateEnds, historicalCandidate = actor.sourceHash != source };
            if (!development) writer = new StreamWriter(new FileStream(report.dataPath, FileMode.CreateNew, FileAccess.Write));
            try { NewGame(); EditorApplication.update += Tick; Status = "running competitive " + report.split; }
            catch (Exception e) { Fail(e); throw; }
        }

        private static void NewGame()
        {
            match?.Dispose();
            team = report.alternateEnds ? report.initialCandidateTeam ^ (game & 1) : report.initialCandidateTeam;
            int seed = report.seed + game;
            var contact = ContactModel.Load(File.ReadAllText(ContactTraining.ModelPath));
            BaselineControl baseline = opponent == null ? new BaselineControl(1 << (1 - team), DoublesModels.Load(File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json")), contact, seed, sampledBaseline) : null;
            var policies = Enumerable.Range(0, 4).Select(i => i / 2 == team ? (IPlayerPolicy)new PlayerActor(actor, report.sampledActor)
                : opponent != null ? new PlayerActor(opponent, true) : new ConstantPlayerPolicy(default)).ToArray();
            match = new PlayerMatch(false, policies, contact, seed, baseline) { AutoNext = false };
            report.configurationHash = match.World.Configuration.ConfigurationHash;
            if (actor.configurationHash != report.configurationHash || (opponent != null && opponent.configurationHash != report.configurationHash))
                throw new InvalidOperationException("Actor physics configuration mismatch.");
            completed = 0; completedGameSeconds = 0; previousHits = new int[4]; VaryServe();
            if (writer != null) match.Actors.Decided += Record;
        }
        private static void Record(PlayerDecision decision)
        {
            if (decision.player / 2 != team) return;
            if (decision.trace == null) throw new InvalidOperationException("Missing sampled actor trace.");
            var partner = PlayerObservation.Capture(match.World, decision.player ^ 1, decision.observationTick);
            var joint = new float[108]; Array.Copy(decision.observation.values, 0, joint, 0, 54); Array.Copy(partner.values, 0, joint, 54, 54);
            episode.Add(new PlayerExperience { episode = (report.seed + game) + "/" + (report.rewardMode == "rally_win" ? completed.ToString() : "game"),
                gameSeed = report.seed + game, candidateTeam = team, rally = completed, player = decision.player, tick = decision.observationTick,
                observation = (float[])decision.observation.values.Clone(), criticObservation = joint, sample = decision.trace });
        }
        private static void CloseEpisode(int winner)
        {
            if (writer == null) return;
            for (int i = team * 2; i < team * 2 + 2; i++)
            {
                var last = episode.LastOrDefault(row => row.player == i);
                if (last != null) { last.reward = PlayerMatch.TeamReward(i, winner); last.terminal = true; }
            }
            foreach (var row in episode) { writer.WriteLine(JsonUtility.ToJson(row)); report.rows++; }
            episode.Clear();
        }
        private static void VaryServe() => match.ServeJitter = new Vector2((float)(serveRandom.NextDouble() * .6 - .3), (float)(serveRandom.NextDouble() * .8 - .4));
        private static void Tick()
        {
            try
            {
                if (!EditorApplication.isPlaying) throw new InvalidOperationException("Play mode stopped during collection.");
                double until = EditorApplication.timeSinceStartup + .02;
                while (Running && EditorApplication.timeSinceStartup < until)
                {
                    match.Step(); var rules = match.World.Rules;
                    if (match.World.Time > 35) { EndGame(false, "rally did not resolve within 35 seconds"); continue; }
                    if (match.CompletedRallies == completed) continue;
                    completed = match.CompletedRallies; completedGameSeconds += match.World.Time;
                    var hits = Enumerable.Range(0, 4).Select(i => match.Metrics.legalHits[i] - previousHits[i]).ToArray();
                    previousHits = (int[])match.Metrics.legalHits.Clone();
                    report.rallies.Add(new CompetitiveRally { gameSeed = report.seed + game, candidateTeam = team, winner = rules.Winner,
                        hits = rules.Hits, fault = rules.LastFault.ToString(), score = (int[])rules.Score.Clone(), legalHits = hits, seconds = match.World.Time });
                    if (report.rewardMode == "rally_win") CloseEpisode(rules.Winner);
                    Status = $"competitive {report.split}: {report.rallies.Count}/{wanted} rallies; {report.games.Count} games; side {team}; hits {rules.Hits}";
                    if (rules.GameWinner >= 0) { EndGame(true, "game complete"); continue; }
                    if (completed >= 300 || completedGameSeconds >= 3600) { EndGame(false, "game safety cap"); continue; }
                    match.Next(); VaryServe();
                }
            }
            catch (Exception e) { Fail(e); UnityEngine.Debug.LogException(e); }
        }
        private static void EndGame(bool complete, string reason)
        {
            var rules = match.World.Rules;
            if (report.rewardMode == "game_win" || episode.Count > 0) CloseEpisode(complete ? rules.GameWinner : -1);
            report.games.Add(new CompetitiveGame { gameSeed = report.seed + game, candidateTeam = team, winner = complete ? rules.GameWinner : -1,
                complete = complete, reason = reason, rallies = completed, score = (int[])rules.Score.Clone(), metrics = match.Metrics });
            if (!complete) { Finish("incomplete_game"); return; }
            // Every request ends on a game boundary. Incomplete games are retained.
            if (report.rallies.Count >= wanted) { Finish(); return; }
            if (++game >= wanted + 1000) throw new InvalidOperationException("Too many incomplete games.");
            NewGame();
        }
        private static void Finish(string status = "complete")
        {
            match.Dispose(); match = null; writer?.Dispose(); writer = null; EditorApplication.update -= Tick;
            report.wallSeconds = watch.Elapsed.TotalSeconds;
            if (report.sourceHash != PlayerDiagnostics.SourceHash()) throw new InvalidOperationException("Source changed during competitive collection.");
            report.status = status; File.WriteAllText(output, JsonUtility.ToJson(report, true)); Status = status + ": " + output;
        }
        private static void Fail(Exception error)
        {
            EditorApplication.update -= Tick; match?.Dispose(); match = null; writer?.Dispose(); writer = null; episode.Clear();
            if (report != null) { report.status = "failed: " + error.Message; report.wallSeconds = watch.Elapsed.TotalSeconds; File.WriteAllText(output, JsonUtility.ToJson(report, true)); }
            Status = "failed: " + error.Message;
        }
        public static void Cancel() { if (Running) Fail(new OperationCanceledException("Competitive job cancelled; partial data is not accepted.")); }
    }
}
