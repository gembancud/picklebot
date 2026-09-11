using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Picklebot.Core;
using Picklebot.Doubles;
using Picklebot.Doubles.Editor;
using UnityEditor;
using UnityEngine;

namespace Picklebot.PlayerAgents.Editor
{
    [Serializable] public sealed class ThroughputCase
    {
        public string mode;
        public int steps, rallies, decisions;
        public double wallSeconds, simulationSeconds, stepsPerWallSecond;
        public PlayerMetrics metrics;
    }
    [Serializable] public sealed class ThroughputReport
    {
        public string createdUtc, sourceHash, configurationHash, contactHash, teamHash, note;
        public List<ThroughputCase> cases = new List<ThroughputCase>();
    }
    [Serializable] public sealed class MotorCase
    {
        public string mode;
        public float maxSpeed, maxAcceleration, maxPaddleSpeed, maxReach, minSeparation = 100;
        public float stopDistance, stopSeconds;
        public bool finite = true;
    }
    [Serializable] public sealed class DropCase
    {
        public float releaseCentreHeight, radius, firstImpactTime, reboundCentreHeight;
        public float heightRatio, incomingSpeed, outgoingSpeed;
        public bool bounced;
    }
    [Serializable] public sealed class PhysicsAuditReport
    {
        public string createdUtc, configurationHash, sourceHash;
        public string status = "measurement only; not physical calibration";
        public List<MotorCase> motors = new List<MotorCase>();
        public List<DropCase> drops = new List<DropCase>();
    }

    public static class PlayerDiagnostics
    {
        public const string Output = "artifacts/player-agents";
        public static string Status { get; private set; } = "idle";
        public static bool Running => baseline != null || independent != null;
        private static DoublesMatch baseline;
        private static PlayerMatch independent;
        private static ThroughputReport report;
        private static PlayerMetrics metrics;
        private static int wanted, steps, mode, previousRallies;
        private static Stopwatch watch;
        private static string outputPath;
        private static readonly string[] Modes = { "saved baseline / sampled shots", "four actors / constant hold", "four actors / constant attempt" };

        public static string SourceHash() => ContactTraining.Hash(ContactTraining.SourceHash() + "\n" + ContactTraining.SourceText(
            Directory.GetFiles("Assets/Picklebot/PlayerAgents", "*.cs", SearchOption.AllDirectories)
            .Where(p => !ContactTraining.CanonicalPath(p).Contains("/Tests/"))));

        public static void StartBenchmark(int physicsSteps = 6000)
        {
            if (!EditorApplication.isPlaying || Running || PlayerTeacher.Running || PlayerEvaluation.Running || PlayerControlProbe.Running || PlayerCurriculum.Running || PlayerCompetition.Running)
                throw new InvalidOperationException("Start Play and finish the current job first.");
            if (physicsSteps < 240) throw new ArgumentOutOfRangeException(nameof(physicsSteps));
            wanted = physicsSteps; mode = 0;
            outputPath = Path.Combine(Output, "throughput-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json");
            report = new ThroughputReport { createdUtc = DateTime.UtcNow.ToString("O"), sourceHash = SourceHash(),
                contactHash = ContactTraining.Hash(File.ReadAllText(ContactTraining.ModelPath)),
                teamHash = ContactTraining.Hash(File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json")),
                note = "Editor wall-clock throughput, including update scheduling. Constant actors are untrained; this is not playing-strength evidence." };
            NewCase(); EditorApplication.update += Tick;
        }

        private static void NewCase()
        {
            var contact = ContactModel.Load(File.ReadAllText(ContactTraining.ModelPath));
            metrics = new PlayerMetrics(); steps = previousRallies = 0;
            if (mode == 0)
                baseline = new DoublesMatch(false, 1100000) { CentreOnly = false, SampleActions = true, ContactModel = contact,
                    Models = DoublesModels.Load(File.ReadAllText("Assets/Picklebot/Doubles/Models/teams.json")) };
            else
            {
                var policies = Enumerable.Range(0, 4).Select(i => (IPlayerPolicy)new ConstantPlayerPolicy(new PlayerAction { attempt = mode == 2 })).ToArray();
                independent = new PlayerMatch(false, policies, contact, 1100000);
                metrics = independent.Metrics;
            }
            report.configurationHash = (baseline != null ? baseline.World : independent.World).Configuration.ConfigurationHash;
            watch = Stopwatch.StartNew(); Status = Modes[mode] + ": 0/" + wanted;
        }

        private static void Tick()
        {
            try
            {
                double until = EditorApplication.timeSinceStartup + .02;
                while (Running && EditorApplication.timeSinceStartup < until)
                {
                    if (baseline != null)
                    {
                        metrics.Before(baseline.World); baseline.Step();
                        if (baseline.CompletedRallies != previousRallies) { metrics.ResetRally(); previousRallies = baseline.CompletedRallies; }
                        metrics.After(baseline.World);
                    }
                    else independent.Step();
                    steps++;
                    Status = Modes[mode] + ": " + steps + "/" + wanted;
                    if (steps >= wanted)
                    {
                        report.cases.Add(new ThroughputCase { mode = Modes[mode], steps = steps,
                            rallies = baseline != null ? baseline.CompletedRallies : independent.CompletedRallies,
                            decisions = independent?.Actors.Decisions ?? 0, wallSeconds = watch.Elapsed.TotalSeconds,
                            simulationSeconds = steps * (double)DoublesWorld.Dt, stepsPerWallSecond = steps / watch.Elapsed.TotalSeconds, metrics = metrics });
                        baseline?.Dispose(); independent?.Dispose(); baseline = null; independent = null;
                        mode++;
                        if (mode < Modes.Length) NewCase();
                        else
                        {
                            EditorApplication.update -= Tick;
                            if (SourceHash() != report.sourceHash) throw new InvalidOperationException("Source changed during benchmark.");
                            Directory.CreateDirectory(Output); File.WriteAllText(outputPath, JsonUtility.ToJson(report, true));
                            Status = "complete: " + outputPath;
                        }
                    }
                }
            }
            catch (Exception e) { Cancel(); Status = "failed: " + e; UnityEngine.Debug.LogException(e); }
        }

        public static void Cancel()
        { EditorApplication.update -= Tick; baseline?.Dispose(); independent?.Dispose(); baseline = null; independent = null; Status = "cancelled"; }

        public static string AuditPhysics()
        {
            if (!EditorApplication.isPlaying || Running || PlayerTeacher.Running || PlayerEvaluation.Running || PlayerControlProbe.Running || PlayerCurriculum.Running || PlayerCompetition.Running)
                throw new InvalidOperationException("Start Play and finish active jobs first.");
            var audit = new PhysicsAuditReport { createdUtc = DateTime.UtcNow.ToString("O"), sourceHash = SourceHash() };
            foreach (var modeName in new[] { "free acceleration and stop", "opposed partner movement", "aggressive paddle rotation", "bounded opposed partner movement", "bounded run toward court limit" })
            {
                using var w = new DoublesWorld(false);
                audit.configurationHash = w.Configuration.ConfigurationHash;
                foreach (var collider in w.Ball.GetComponents<Collider>()) collider.enabled = false;
                w.Players[0].Reset(new Vector3(-1, 0, -4)); w.Players[1].Reset(new Vector3(1, 0, -4));
                var row = new MotorCase { mode = modeName }; Vector3 stopStart = default;
                for (int step = 0; step < 480; step++)
                {
                    if (step == 240) stopStart = w.Players[0].Position;
                    for (int i = 0; i < 2; i++)
                    {
                        var p = w.Players[i]; var oldVelocity = p.Velocity;
                        Vector3 velocity = modeName.Contains("opposed partner movement") ? new Vector3(i == 0 ? 3.8f : -3.8f, 0, 0)
                            : modeName == "bounded run toward court limit" && i == 0 ? Vector3.back * 3.8f
                            : step < 240 && i == 0 ? Vector3.back * 3.8f : Vector3.zero;
                        if (modeName.StartsWith("bounded")) velocity = PlayerMovement.Constrain(p, w.Players[i ^ 1], velocity);
                        var rotation = modeName == "aggressive paddle rotation" ? Quaternion.Euler(step % 120 < 60 ? 65 : -65, step % 120 < 60 ? 105 : -105, 85) : Quaternion.identity;
                        var target = modeName == "aggressive paddle rotation" ? p.Shoulder + new Vector3(.7f, -.7f, .7f)
                            : p.Position + new Vector3(.19f, 1.1f, .46f);
                        p.Step(p.Position + velocity / 4f, target, rotation, Vector3.zero, w.Players[i ^ 1], DoublesWorld.Dt);
                        row.maxSpeed = Mathf.Max(row.maxSpeed, p.Velocity.magnitude);
                        row.maxAcceleration = Mathf.Max(row.maxAcceleration, (p.Velocity - oldVelocity).magnitude / DoublesWorld.Dt);
                        row.maxPaddleSpeed = Mathf.Max(row.maxPaddleSpeed, p.PaddleVelocity.magnitude);
                        row.finite &= float.IsFinite(p.Position.x) && float.IsFinite(p.PaddleVelocity.x);
                    }
                    w.Simulate();
                    for (int i = 0; i < 2; i++) row.maxReach = Mathf.Max(row.maxReach, Vector3.Distance(w.Players[i].Shoulder, w.Players[i].Hand));
                    row.minSeparation = Mathf.Min(row.minSeparation, Vector3.Distance(w.Players[0].Position, w.Players[1].Position));
                    if (step >= 240 && row.stopSeconds == 0 && w.Players[0].Velocity.magnitude < .02f)
                    { row.stopDistance = Vector3.Distance(stopStart, w.Players[0].Position); row.stopSeconds = (step - 239) * DoublesWorld.Dt; }
                }
                audit.motors.Add(row);
            }
            foreach (float height in new[] { 1f, 1.5f, 2f })
            {
                using var w = new DoublesWorld(false);
                var row = new DropCase { releaseCentreHeight = height, radius = CourtGeometryV1.BallRadius };
                w.Ball.position = new Vector3(0, height, -4); w.Ball.transform.position = w.Ball.position;
                w.Ball.linearVelocity = w.Ball.angularVelocity = Vector3.zero;
                for (int step = 0; step < 500; step++)
                {
                    float before = w.Ball.linearVelocity.y; w.Simulate();
                    if (!row.bounced && before < 0 && w.Ball.linearVelocity.y > 0)
                    { row.bounced = true; row.firstImpactTime = w.Time; row.incomingSpeed = -before; row.outgoingSpeed = w.Ball.linearVelocity.y; }
                    if (row.bounced)
                    {
                        row.reboundCentreHeight = Mathf.Max(row.reboundCentreHeight, w.Ball.position.y);
                        if (w.Ball.linearVelocity.y <= 0) break;
                    }
                }
                row.heightRatio = (row.reboundCentreHeight - row.radius) / (height - row.radius); audit.drops.Add(row);
            }
            Directory.CreateDirectory(Output);
            string path = Path.Combine(Output, "physics-audit-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".json");
            File.WriteAllText(path, JsonUtility.ToJson(audit, true)); return path;
        }
    }
}
