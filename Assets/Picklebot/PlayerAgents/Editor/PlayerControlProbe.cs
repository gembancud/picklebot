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
    // Privileged diagnostic teacher. Never used by the exported player policy.
    // It supplies actions through the same 20 Hz / 25 ms path as the learner.
    public sealed class PlayerOracle
    {
        public sealed class Buffer : IPlayerPolicy
        {
            public PlayerAction Action;
            public string Name => "privileged diagnostic teacher (not learned)";
            public PlayerAction Decide(PlayerObservation observation, System.Random random) => Action;
        }
        public readonly Buffer[] Policies = { new Buffer(), new Buffer(), new Buffer(), new Buffer() };
        private readonly PlayerContactPlan[] plans = { new PlayerContactPlan(), new PlayerContactPlan(), new PlayerContactPlan(), new PlayerContactPlan() };
        private readonly ContactModel contact;
        private readonly DoublesModels models;
        private readonly System.Random random;
        private int previousHits = -1, active = -1, shot;
        private Vector2 goal;
        private readonly int fixedShot;

        public PlayerOracle(ContactModel contact, DoublesModels models, int seed, int fixedShot = -1)
        { this.contact = contact; this.models = models; this.fixedShot = fixedShot; random = new System.Random(seed); }

        public void Reset() { previousHits = -1; active = -1; foreach (var p in plans) p.Reset(); }

        public void Prepare(DoublesWorld world)
        {
            var rules = world.Rules;
            if (rules.Dead || rules.Phase == RallyPhase.AwaitServe) return;
            if (previousHits != rules.Hits)
            {
                previousHits = rules.Hits; active = -1;
                foreach (var p in plans) p.Reset();
                shot = fixedShot >= 0 ? fixedShot : models.ForTeam(rules.ExpectedTeam).Choose(world, rules.ExpectedTeam, random, true).action;
                goal = TeamPolicy.Target(shot);
            }
            if (active < 0)
            {
                if (rules.Phase == RallyPhase.ServeFlight) active = rules.DesignatedReceiver;
                else
                {
                    int a = rules.ExpectedTeam * 2, b = a + 1;
                    bool pa = plans[a].Plan(world, a, goal), pb = plans[b].Plan(world, b, goal);
                    if (pa || pb)
                    {
                        float ca = plans[a].ImpactAt + .2f * Vector3.Distance(world.Players[a].Position, plans[a].Impact);
                        float cb = plans[b].ImpactAt + .2f * Vector3.Distance(world.Players[b].Position, plans[b].Impact);
                        active = !pb ? a : !pa ? b : ca <= cb ? a : b;
                        plans[active ^ 1].Reset(); plans[active].Reset();
                    }
                }
            }
            if (active >= 0)
            {
                plans[active].Kind = TeamPolicy.Kind(shot);
                contact.strokes[(int)plans[active].Kind].Apply(plans[active].Residuals);
                plans[active].Plan(world, active, goal);
            }
            for (int i = 0; i < 4; i++)
            {
                int side = world.Players[i].Side;
                float x = (i % 2 == 0 ? 1.55f : -1.55f) * -side;
                if (active >= 0 && i == (active ^ 1)) x = world.Players[active].Position.x >= 0 ? -1.55f : 1.55f;
                // Only the privileged teaching policy supplies these feet
                // targets. Runtime actors continue to choose their own motion.
                float minimumContactDepth = plans[i].LowContact && plans[i].Impact.z * side < 2.65f ? .38f : 2.6f;
                var feet = plans[i].Planned
                    ? new Vector3(plans[i].Impact.x + side * .38f, 0, side * Mathf.Max(minimumContactDepth, side * plans[i].Impact.z + .43f))
                    : new Vector3(x, 0, side * (rules.CanVolley ? 3.5f : 6f));
                var move = PlayerObservation.ToLocal(Vector3.ClampMagnitude((feet - world.Players[i].Position) * 4, PlayerBody.Speed) / PlayerBody.Speed, i);
                int localShot = side > 0 && shot > 0 ? ((shot & 1) == 1 ? shot + 1 : shot - 1) : shot;
                Policies[i].Action = new PlayerAction { moveX = move.x, moveZ = move.z, attempt = i == active, shot = localShot }.Validated();
            }
        }
    }

    public static class PlayerControlProbe
    {
        public static bool Running => match != null;
        public static string Status { get; private set; } = "idle";
        private static PlayerMatch match;
        private static PlayerOracle oracle;
        private static PlayerEvaluationReport report;
        private static System.Random random;
        private static Stopwatch watch;
        private static int wanted, game, completed;
        private static int[] previousHits;
        private static string output;

        public static void Start(int rallies = 32, int seed = 1100200)
        {
            if (!EditorApplication.isPlaying || Running || PlayerTeacher.Running || PlayerEvaluation.Running || PlayerCurriculum.Running || PlayerDiagnostics.Running || PlayerCompetition.Running)
                throw new InvalidOperationException("Start Play and finish other jobs first.");
            if (rallies < 1 || seed < 1100000 || seed + rallies >= 1200000) throw new ArgumentException("Development seeds only.");
            wanted = rallies; game = 0; random = new System.Random(seed); watch = Stopwatch.StartNew();
            output = Path.Combine(PlayerDiagnostics.Output, "teacher-control-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json");
            report = new PlayerEvaluationReport { sourceHash = PlayerDiagnostics.SourceHash(), seed = seed, createdUtc = DateTime.UtcNow.ToString("O"),
                contactModelHash = ContactTraining.Hash(File.ReadAllText(ContactTraining.ModelPath)),
                protocolHash = ContactTraining.Hash(File.ReadAllText("config/player-agents/evaluation-v1.json")),
                mode = "privileged teacher actions through independent control; diagnostic only; not learned or baseline comparison" };
            NewGame(); EditorApplication.update += Tick; Status = "running teacher control probe";
        }
        private static void NewGame()
        {
            match?.Dispose();
            var contact = ContactModel.Load(File.ReadAllText(ContactTraining.ModelPath));
            oracle = new PlayerOracle(contact, DoublesModels.Load(File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json")), report.seed + game);
            match = new PlayerMatch(false, oracle.Policies, contact, report.seed + game) { AutoNext = false };
            report.configurationHash = match.World.Configuration.ConfigurationHash;
            report.gameMetrics.Add(match.Metrics); completed = 0; previousHits = new int[4]; VaryServe();
        }
        private static void VaryServe() => match.ServeJitter = new Vector2((float)(random.NextDouble() * .6 - .3), (float)(random.NextDouble() * .8 - .4));
        private static void Tick()
        {
            try
            {
                double until = EditorApplication.timeSinceStartup + .02;
                while (Running && EditorApplication.timeSinceStartup < until)
                {
                    oracle.Prepare(match.World); match.Step();
                    if (match.CompletedRallies == completed) continue;
                    completed = match.CompletedRallies; var r = match.World.Rules;
                    var hits = Enumerable.Range(0, 4).Select(i => match.Metrics.legalHits[i] - previousHits[i]).ToArray();
                    previousHits = (int[])match.Metrics.legalHits.Clone();
                    report.rallies.Add(new PlayerRallyResult { gameSeed = report.seed + game, winner = r.Winner, gameWinner = r.GameWinner,
                        hits = r.Hits, fault = r.LastFault.ToString(), score = (int[])r.Score.Clone(), legalHits = hits, seconds = match.World.Time });
                    if (r.GameWinner >= 0) report.games++;
                    Status = $"teacher control: {report.rallies.Count}/{wanted}; hits {r.Hits}";
                    if (report.rallies.Count >= wanted)
                    {
                        match.Dispose(); match = null; EditorApplication.update -= Tick;
                        report.wallSeconds = watch.Elapsed.TotalSeconds;
                        if (report.sourceHash != PlayerDiagnostics.SourceHash()) throw new InvalidOperationException("Source changed during probe.");
                        File.WriteAllText(output, JsonUtility.ToJson(report, true)); Status = "complete: " + output; break;
                    }
                    if (r.GameWinner >= 0) { game++; NewGame(); }
                    else { match.Next(); oracle.Reset(); VaryServe(); }
                }
            }
            catch (Exception e) { Cancel(); Status = "failed: " + e; UnityEngine.Debug.LogException(e); }
        }
        public static void Cancel() { EditorApplication.update -= Tick; match?.Dispose(); match = null; Status = "cancelled"; }
    }
}
