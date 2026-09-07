using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Picklebot.Rally.Editor
{
    [Serializable] public sealed class RallyEpisode
    {
        public int seed, returns, contacts, winner;
        public float seconds;
        public string result;
        public Vector3 servePosition, serveVelocity;
        public string[] events;
    }

    [Serializable] public sealed class RallyReport
    {
        public string worldVersion, policySha256, runtimeSourceSha256, unityVersion, actionSource, createdUtc;
        public bool provisional = true;
        public int episodes, successAtTen, bestReturns, firstReturnSuccess;
        public float meanReturns;
        public List<RallyEpisode> results = new();
    }

    [InitializeOnLoad]
    public static class RallyEditor
    {
        public const string PolicyPath = "Assets/Picklebot/Rally/Models/rally-policy.json";
        public const string ScenePath = "Assets/Picklebot/Scenes/AIRally.unity";
        private static RallyWorld world;
        private static RallyNeuralPolicy policy;
        private static RallyReport report;
        private static int firstSeed, count;
        private static string output;
        public static string Status { get; private set; } = "idle";

        static RallyEditor() => EditorApplication.playModeStateChanged += change =>
        {
            if (change == PlayModeStateChange.ExitingPlayMode) Stop();
        };

        [MenuItem("Picklebot/AI Rally/Create demo scene")]
        public static string CreateScene()
        {
            if (EditorApplication.isPlaying) throw new InvalidOperationException("Stop Play before creating the scene.");
            var model = AssetDatabase.LoadAssetAtPath<TextAsset>(PolicyPath);
            if (model == null) throw new InvalidOperationException("Train and import the rally policy first.");
            var existing = SceneManager.GetSceneByPath(ScenePath);
            if (existing.IsValid() && existing.isLoaded)
                throw new InvalidOperationException("AI Rally scene is already loaded; inspect it before replacing.");
            var created = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            SceneManager.SetActiveScene(created);
            var go = new GameObject("AI Rally");
            go.AddComponent<RallyDemo>().TrainedPolicy = model;
            var cameraGo = new GameObject("Rally Camera");
            var camera = cameraGo.AddComponent<Camera>();
            cameraGo.tag = "MainCamera";
            camera.transform.position = new Vector3(3.2f,2.9f,-4f);
            camera.transform.LookAt(new Vector3(0,.10f,0));
            camera.fieldOfView = 43;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(.035f,.055f,.08f);
            camera.nearClipPlane = .01f;
            cameraGo.AddComponent<AudioListener>();
            var sun = new GameObject("Rally Light").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.4f;
            sun.transform.rotation = Quaternion.Euler(45,-30,0);
            if (!EditorSceneManager.SaveScene(created, ScenePath)) throw new IOException("Could not save rally scene.");
            return ScenePath;
        }

        public static string Evaluate(int seed = 820000, int episodes = 100, string label = "neural", bool zeroAction = false)
        {
            if (!EditorApplication.isPlaying) throw new InvalidOperationException("Run evaluation in Play Mode for collision callbacks.");
            if (world != null) throw new InvalidOperationException("Evaluation already running: " + Status);
            if (seed < 820000 || seed + episodes > 821000 || episodes < 1)
                throw new ArgumentException("Use the rally validation partition [820000,821000).");
            if (label.Any(c => !char.IsLetterOrDigit(c) && c != '-')) throw new ArgumentException("Invalid label.");
            var asset = AssetDatabase.LoadAssetAtPath<TextAsset>(PolicyPath);
            policy = zeroAction ? null : new RallyNeuralPolicy(asset);
            using var sha = SHA256.Create();
            string hash = BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(PolicyPath))).Replace("-", "").ToLowerInvariant();
            report = new RallyReport { worldVersion=RallyWorld.Version, policySha256=hash,
                runtimeSourceSha256=BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(
                    string.Join("\n", Directory.GetFiles("Assets/Picklebot/Rally", "*.cs").OrderBy(p => p, StringComparer.Ordinal)
                        .Select(p => p + "\n" + File.ReadAllText(p)))))).Replace("-", "").ToLowerInvariant(),
                actionSource=zeroAction ? "zero-action-baseline" : "trained-neural-policy-both-paddles",
                unityVersion=Application.unityVersion, createdUtc=DateTime.UtcNow.ToString("O") };
            firstSeed = seed; count = episodes;
            output = Path.GetFullPath("artifacts/rally/validation/" + label + ".json");
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            world = new RallyWorld(false);
            world.Reset(firstSeed);
            Status = "running 0/" + count;
            EditorApplication.update += Tick;
            return Status;
        }

        private static void Tick()
        {
            if (world == null) return;
            try
            {
                for (int i = 0; i < 2000; i++)
                {
                    world.Step(policy);
                    if (!world.Rules.Finished && world.Rules.Returns < 20) continue;
                    var rules = world.Rules;
                    report.results.Add(new RallyEpisode { seed=world.Seed, returns=rules.Returns,
                        contacts=rules.Contacts, winner=rules.Winner, seconds=world.Elapsed,
                        result=rules.Finished ? rules.Result : "Evaluation cap: 20 legal returns",
                        servePosition=world.InitialPosition, serveVelocity=world.InitialVelocity, events=world.Events.ToArray() });
                    report.episodes++;
                    if (rules.Returns >= 10) report.successAtTen++;
                    if (rules.Returns > 0) report.firstReturnSuccess++;
                    report.bestReturns = Math.Max(report.bestReturns, rules.Returns);
                    Status = $"running {report.episodes}/{count}; successes {report.successAtTen}; best {report.bestReturns}";
                    if (report.episodes == count)
                    {
                        report.meanReturns = report.results.Sum(r => r.returns) / (float)report.episodes;
                        File.WriteAllText(output, JsonUtility.ToJson(report, true));
                        Status = "completed: " + output;
                        Stop();
                        return;
                    }
                    world.Reset(firstSeed + report.episodes);
                }
            }
            catch (Exception exception)
            {
                Status = "failed: " + exception;
                Stop();
                Debug.LogException(exception);
            }
        }

        private static void Stop()
        {
            EditorApplication.update -= Tick;
            world?.Dispose();
            world = null;
        }
    }
}
