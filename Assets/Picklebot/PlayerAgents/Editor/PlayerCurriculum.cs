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
    [Serializable] public sealed class CurriculumReport
    {
        public string status;
        public string sourceHash, configurationHash, protocolHash, contactModelHash, teamModelHash, baselineManifestHash, createdUtc, dataPath, method, split;
        public string actorHash, actorTrainingSourceHash;
        public int seed, rallies, games, rows, teacherDecisions, actorDecisions, fixedShot;
        public float teacherProbability;
        public double wallSeconds;
        public int[] legalHits = new int[4];
        public string opponentMode;
        public bool baselineOpponent, sampleBaseline;
        public int initialCandidateTeam, candidateReturns, opponentReturns;
        public List<CompetitiveGame> gameResults = new List<CompetitiveGame>();
    }

    [Serializable] public sealed class CurriculumRecord
    {
        public int gameSeed, rally, player, tick, candidateTeam;
        public float[] observation;
        public PlayerAction action;
    }

    // Training-only teacher/learner mixture. Actor-only evaluation remains separate.
    public static class PlayerCurriculum
    {
        private sealed class Mixture : IPlayerPolicy
        {
            public PlayerOracle.Buffer Teacher;
            public PlayerActor Actor;
            public string Name => "training-only teacher/learner mixture";
            public PlayerAction Decide(PlayerObservation observation, System.Random random)
            {
                if (Actor == null || random.NextDouble() < report.teacherProbability)
                { report.teacherDecisions++; return Teacher.Action; }
                report.actorDecisions++; return Actor.Decide(observation, random);
            }
        }
        public static bool Running => match != null;
        public static string Status { get; private set; } = "idle";
        private static PlayerMatch match;
        private static PlayerOracle oracle;
        private static PlayerActorModel actor;
        private static CurriculumReport report;
        private static StreamWriter writer;
        private static Stopwatch watch;
        private static System.Random random;
        private static int wanted, game, completed, team;
        private static double gameSeconds;
        private static int[] previousHits;
        private static string output;

        public static void Start(int rallies = 128, int seed = 1000200, bool development = false, string actorPath = "", float teacherProbability = 1, int fixedShot = 0,
            bool baselineOpponent = false, bool sampleBaseline = true, int candidateTeam = 0)
        {
            if (!EditorApplication.isPlaying || Running || PlayerTeacher.Running || PlayerEvaluation.Running || PlayerControlProbe.Running || PlayerDiagnostics.Running || PlayerCompetition.Running)
                throw new InvalidOperationException("Start Play and finish other jobs first.");
            int lower = development ? 1100000 : 1000000;
            if (rallies < 1 || rallies > 10000 || seed < lower || seed + rallies >= lower + 100000 || float.IsNaN(teacherProbability)
                || teacherProbability < 0 || teacherProbability > 1 || fixedShot < -1 || fixedShot > 8 || candidateTeam < 0 || candidateTeam > 1)
                throw new ArgumentException("Invalid curriculum bounds or seed partition.");
            actor = string.IsNullOrEmpty(actorPath) ? null : PlayerActorModel.Load(File.ReadAllText(actorPath));
            string contactHash = ContactTraining.Hash(File.ReadAllText(ContactTraining.ModelPath));
            string protocolHash = ContactTraining.Hash(File.ReadAllText("config/player-agents/evaluation-v1.json"));
            if (actor != null && (actor.contactModelHash != contactHash || actor.protocolHash != protocolHash))
                throw new InvalidOperationException("Curriculum actor contact or protocol is incompatible.");
            if (actor == null && teacherProbability != 1) throw new ArgumentException("A learner checkpoint is required for mixed actions.");
            // Earlier development actors are permitted for state collection only.
            // Record both hashes. Do not relabel their training source or accept them for final evaluation.
            wanted = rallies; game = 0; random = new System.Random(seed); watch = Stopwatch.StartNew();
            string stem = Path.Combine(PlayerDiagnostics.Output, "curriculum-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss"));
            output = stem + ".json";
            report = new CurriculumReport { status = "running", sourceHash = PlayerDiagnostics.SourceHash(), seed = seed, split = development ? "development" : "training",
                createdUtc = DateTime.UtcNow.ToString("O"), contactModelHash = contactHash, protocolHash = protocolHash, dataPath = stem + ".jsonl",
                baselineManifestHash = ContactTraining.Hash(File.ReadAllText(Path.Combine(PlayerDiagnostics.Output, "baseline-manifest.json"))),
                teamModelHash = ContactTraining.Hash(File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json")),
                actorHash = actor == null ? "none" : ContactTraining.Hash(File.ReadAllText(actorPath)), actorTrainingSourceHash = actor?.sourceHash ?? "none",
                teacherProbability = teacherProbability, fixedShot = fixedShot,
                baselineOpponent = baselineOpponent, sampleBaseline = sampleBaseline, initialCandidateTeam = candidateTeam,
                opponentMode = baselineOpponent ? (sampleBaseline ? "frozen baseline / sampled" : "frozen baseline / maximum probability") : "four teacher/learner mixtures",
                method = "training-only privileged teacher labels on independent-control states; optional learner mixture; 20 Hz and 25 ms latency; no competitive reward training" };
            writer = new StreamWriter(new FileStream(report.dataPath, FileMode.CreateNew, FileAccess.Write));
            try { NewGame(); EditorApplication.update += Tick; Status = "running curriculum collection"; }
            catch (Exception error) { Fail(error); throw; }
        }
        private static void NewGame()
        {
            match?.Dispose();
            team = report.baselineOpponent ? report.initialCandidateTeam ^ (game & 1) : -1;
            var contact = ContactModel.Load(File.ReadAllText(ContactTraining.ModelPath));
            var models = DoublesModels.Load(File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json"));
            oracle = new PlayerOracle(contact, models, report.seed + game, report.fixedShot);
            var baseline = report.baselineOpponent ? new BaselineControl(1 << (1 - team), models, contact, report.seed + game, report.sampleBaseline) : null;
            var policies = Enumerable.Range(0, 4).Select(i => (IPlayerPolicy)new Mixture { Teacher = oracle.Policies[i], Actor = actor == null ? null : new PlayerActor(actor, false) }).ToArray();
            match = new PlayerMatch(false, policies, contact, report.seed + game, baseline) { AutoNext = false };
            report.configurationHash = match.World.Configuration.ConfigurationHash;
            if (actor != null && actor.configurationHash != report.configurationHash) throw new InvalidOperationException("Actor physics configuration mismatch.");
            match.Actors.Decided += decision =>
            {
                if (report.baselineOpponent && decision.player / 2 != team) throw new InvalidOperationException("Opponent decision entered the curriculum.");
                writer.WriteLine(JsonUtility.ToJson(new CurriculumRecord { candidateTeam = team, gameSeed = report.seed + game, rally = report.rallies, player = decision.player,
                    tick = decision.observationTick, observation = decision.observation.values, action = oracle.Policies[decision.player].Action }));
                report.rows++;
            };
            completed = 0; gameSeconds = 0; previousHits = new int[4]; VaryServe();
        }
        private static void VaryServe() => match.ServeJitter = new Vector2((float)(random.NextDouble() * .6 - .3), (float)(random.NextDouble() * .8 - .4));
        private static void Tick()
        {
            try
            {
                if (!EditorApplication.isPlaying) throw new InvalidOperationException("Play mode stopped during collection.");
                double until = EditorApplication.timeSinceStartup + .02;
                while (Running && EditorApplication.timeSinceStartup < until)
                {
                    oracle.Prepare(match.World); match.Step();
                    if (match.World.Time > 35) { EndGame(false, "rally did not resolve within 35 seconds"); continue; }
                    if (match.CompletedRallies == completed) continue;
                    completed = match.CompletedRallies; report.rallies++; gameSeconds += match.World.Time;
                    for (int i = 0; i < 4; i++)
                    {
                        int hits = match.Metrics.legalHits[i] - previousHits[i];
                        report.legalHits[i] += hits; previousHits[i] = match.Metrics.legalHits[i];
                        if (team < 0 || i / 2 == team) report.candidateReturns += hits;
                        else report.opponentReturns += hits;
                    }
                    var rules = match.World.Rules;
                    Status = $"curriculum: {report.rallies}/{wanted}; rows {report.rows}; learner-side returns {report.candidateReturns}";
                    if (rules.GameWinner >= 0) EndGame(true, "game complete");
                    else if (report.rallies >= wanted) EndGame(false, "requested curriculum rally limit");
                    else if (completed >= 300 || gameSeconds >= 3600) EndGame(false, "game safety cap");
                    else { match.Next(); oracle.Reset(); VaryServe(); }
                }
            }
            catch (Exception e) { Fail(e); UnityEngine.Debug.LogException(e); }
        }
        private static void EndGame(bool complete, string reason)
        {
            var rules = match.World.Rules;
            report.gameResults.Add(new CompetitiveGame { gameSeed = report.seed + game, candidateTeam = team,
                complete = complete, winner = complete ? rules.GameWinner : -1, reason = reason, rallies = completed,
                score = (int[])rules.Score.Clone(), metrics = match.Metrics });
            if (complete) report.games++;
            // Imitation labels do not require a terminal reward. A requested
            // rally limit is allowed, but never counts as a complete game.
            if (!complete && reason != "requested curriculum rally limit") { Finish("incomplete_game"); return; }
            if (report.rallies >= wanted) { Finish(); return; }
            game++; NewGame();
        }
        private static void Finish(string status = "complete")
        {
            match.Dispose(); match = null; writer.Dispose(); writer = null; EditorApplication.update -= Tick;
            report.wallSeconds = watch.Elapsed.TotalSeconds;
            if (report.sourceHash != PlayerDiagnostics.SourceHash()) throw new InvalidOperationException("Source changed during curriculum collection.");
            report.status = status; File.WriteAllText(output, JsonUtility.ToJson(report, true)); Status = status + ": " + output;
        }
        private static void Fail(Exception error)
        {
            EditorApplication.update -= Tick; writer?.Dispose(); writer = null; match?.Dispose(); match = null;
            if (report != null) { report.status = "failed: " + error.Message; report.wallSeconds = watch.Elapsed.TotalSeconds; File.WriteAllText(output, JsonUtility.ToJson(report, true)); }
            Status = "failed: " + error.Message;
        }
        public static void Cancel() { if (Running) Fail(new OperationCanceledException("Curriculum cancelled; partial data is not accepted.")); }
    }
}
