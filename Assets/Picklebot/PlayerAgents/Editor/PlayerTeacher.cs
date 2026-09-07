using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Picklebot.Doubles;
using Picklebot.Doubles.Editor;
using UnityEditor;
using UnityEngine;

namespace Picklebot.PlayerAgents.Editor
{
    [Serializable] public sealed class TeacherRecord
    {
        public int gameSeed, rally, player, tick;
        public float[] observation;
        public PlayerAction action;
    }
    [Serializable] public sealed class TeacherReport
    {
        public string sourceHash, configurationHash, protocolHash, contactModelHash, teamModelHash, baselineManifestHash, createdUtc, dataPath, method, split;
        public int seed, rallies, games, rows;
        public double wallSeconds;
    }

    // Privileged teacher data is used only for a disclosed imitation warm start.
    // The runtime actors never call this class or receive its planned intercept.
    public static class PlayerTeacher
    {
        public static string Status { get; private set; } = "idle";
        public static bool Running => match != null;
        private static DoublesMatch match;
        private static TeacherReport report;
        private static StreamWriter writer;
        private static Stopwatch watch;
        private static int wanted, tick, previousRallies, game;
        private static System.Random random;
        private static string reportPath;

        public static void Start(int rallies = 128, int seed = 1000000, bool development = false)
        {
            if (!EditorApplication.isPlaying || Running || PlayerDiagnostics.Running || PlayerEvaluation.Running || PlayerControlProbe.Running || PlayerCurriculum.Running || PlayerCompetition.Running)
                throw new InvalidOperationException("Start Play and finish active jobs first.");
            int lower = development ? 1100000 : 1000000;
            if (rallies < 1 || seed < lower || seed + rallies >= lower + 100000)
                throw new ArgumentException("Teacher data must use its training or development seed partition.");
            wanted = rallies; game = 0; random = new System.Random(seed);
            Directory.CreateDirectory(PlayerDiagnostics.Output);
            string stem = Path.Combine(PlayerDiagnostics.Output, "teacher-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss"));
            reportPath = stem + ".json";
            report = new TeacherReport { createdUtc = DateTime.UtcNow.ToString("O"), seed = seed, sourceHash = PlayerDiagnostics.SourceHash(), split = development ? "development" : "training",
                baselineManifestHash = ContactTraining.Hash(File.ReadAllText(Path.Combine(PlayerDiagnostics.Output, "baseline-manifest.json"))),
                protocolHash = ContactTraining.Hash(File.ReadAllText("config/player-agents/evaluation-v1.json")),
                contactModelHash = ContactTraining.Hash(File.ReadAllText(ContactTraining.ModelPath)),
                teamModelHash = ContactTraining.Hash(File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json")),
                dataPath = stem + ".jsonl", method = "scripted baseline teacher; current observations only; pre-step observations and requested movement labels; no actor receives teacher intercepts" };
            writer = new StreamWriter(new FileStream(report.dataPath, FileMode.CreateNew, FileAccess.Write));
            watch = Stopwatch.StartNew(); NewGame(); EditorApplication.update += Tick;
        }

        private static void NewGame()
        {
            match?.Dispose();
            match = new DoublesMatch(false, report.seed + game) { CentreOnly = false, SampleActions = true, AutoNext = false,
                ContactModel = ContactModel.Load(File.ReadAllText(ContactTraining.ModelPath)),
                Models = DoublesModels.Load(File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json")) };
            report.configurationHash = match.World.Configuration.ConfigurationHash;
            tick = previousRallies = 0; VaryServe();
        }
        private static void VaryServe() => match.ServeJitter = new Vector2((float)(random.NextDouble() * .6 - .3), (float)(random.NextDouble() * .8 - .4));

        private static void Tick()
        {
            try
            {
                double until = EditorApplication.timeSinceStartup + .02;
                while (match != null && EditorApplication.timeSinceStartup < until)
                {
                    var world = match.World; var rules = world.Rules;
                    bool record = tick % PlayerDecisionLoop.DecisionTicks == 0 && !rules.Dead && rules.Phase != RallyPhase.AwaitServe;
                    var observations = record ? Enumerable.Range(0, 4).Select(i => PlayerObservation.Capture(world, i, tick)).ToArray() : null;
                    var positions = record ? world.Players.Select(p => p.Position).ToArray() : null;
                    int hits = rules.Hits; bool volley = rules.CanVolley;
                    match.Step();
                    // A contact at the sample boundary invalidates a label based
                    // on the earlier phase. Skip that boundary instead of leaking it.
                    if (record && !rules.Dead && rules.Hits == hits)
                    {
                        for (int i = 0; i < 4; i++)
                        {
                            int side = world.Players[i].Side; var stroke = match.Strokes[i];
                            float x = (i % 2 == 0 ? 1.55f : -1.55f) * -side;
                            if (match.ActivePlayer >= 0 && i == (match.ActivePlayer ^ 1)) x = positions[match.ActivePlayer].x >= 0 ? -1.55f : 1.55f;
                            var feet = stroke.Planned ? new Vector3(stroke.Impact.x + side * .38f, 0, side * Mathf.Max(2.6f, side * stroke.Impact.z + .43f))
                                : new Vector3(x, 0, side * (volley ? 3.5f : 6f));
                            var move = PlayerObservation.ToLocal(Vector3.ClampMagnitude((feet - positions[i]) * 4f, PlayerBody.Speed) / PlayerBody.Speed, i);
                            int shot = match.Decisions.Count == 0 ? 0 : match.Decisions[match.Decisions.Count - 1].action;
                            if (side > 0 && shot > 0) shot = (shot & 1) == 1 ? shot + 1 : shot - 1;
                            var action = new PlayerAction { moveX = move.x, moveZ = move.z, attempt = i == match.ActivePlayer, shot = shot }.Validated();
                            writer.WriteLine(JsonUtility.ToJson(new TeacherRecord { gameSeed = report.seed + game, rally = report.rallies, player = i,
                                tick = tick, observation = observations[i].values, action = action })); report.rows++;
                        }
                    }
                    tick++;
                    if (match.CompletedRallies != previousRallies)
                    {
                        previousRallies = match.CompletedRallies; report.rallies++;
                        if (rules.GameWinner >= 0) report.games++;
                        Status = $"teacher: {report.rallies}/{wanted} rallies; {report.rows} rows";
                        if (report.rallies >= wanted) { Finish(); break; }
                        if (rules.GameWinner >= 0) { game++; NewGame(); }
                        else { match.Next(); tick = 0; VaryServe(); }
                    }
                }
            }
            catch (Exception e) { Cancel(); Status = "failed: " + e; UnityEngine.Debug.LogException(e); }
        }

        private static void Finish()
        {
            writer.Dispose(); writer = null; match.Dispose(); match = null; EditorApplication.update -= Tick;
            report.wallSeconds = watch.Elapsed.TotalSeconds;
            if (report.sourceHash != PlayerDiagnostics.SourceHash()) throw new InvalidOperationException("Source changed during teacher collection.");
            File.WriteAllText(reportPath, JsonUtility.ToJson(report, true)); Status = "complete: " + reportPath;
        }
        public static void Cancel()
        { EditorApplication.update -= Tick; writer?.Dispose(); writer = null; match?.Dispose(); match = null; Status = "cancelled; partial data is not accepted"; }
    }
}
