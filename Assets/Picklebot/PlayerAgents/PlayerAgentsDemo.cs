using System;
using System.Collections.Generic;
using System.Linq;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    public sealed class PlayerAgentsDemo : MonoBehaviour
    {
        public bool Paused, ShowIntent = true;
        public TextAsset ContactAsset;
        public TextAsset ActorAsset;
        public bool SampleActor;
        public float Speed = 1f;
        public int Seed = 1300000;
        public PlayerMatch Match { get; private set; }
        public bool IsReplaying { get; private set; }
        public int ReplayFrames => lastReplay?.Count ?? 0;
        private float budget, replayTime;
        private System.Random serveRandom;
        private readonly LineRenderer[] movement = new LineRenderer[4], shot = new LineRenderer[4];
        private readonly List<Material> materials = new List<Material>();
        private Renderer[] sources;
        private Transform[] ghosts;
        private bool[] liveVisibility;
        private GameObject ghostRoot, intentRoot;
        private readonly List<Pose[]> currentReplay = new List<Pose[]>();
        private List<Pose[]> lastReplay;
        private int recordedTick, completed;
        private string lastFault;
        private struct Pose { public Vector3 position, scale; public Quaternion rotation; }

        private void Start() => NewGame();

        public void NewGame()
        {
            ExitReplay(); ClearVisuals(); Match?.Dispose();
            int seed = Seed++; serveRandom = new System.Random(seed);
            var model = ActorAsset == null ? null : PlayerActorModel.Load(ActorAsset.text);
            var policies = Enumerable.Range(0, 4).Select(i => model == null
                ? (IPlayerPolicy)new ConstantPlayerPolicy(new PlayerAction { attempt = true, shot = i % 2 == 0 ? 3 : 8 })
                : new PlayerActor(model, SampleActor)).ToArray();
            Match = new PlayerMatch(true, policies, ContactAsset == null ? null : ContactModel.Load(ContactAsset.text), seed) { AutoNext = false };
            budget = 0; completed = 0; recordedTick = -1; currentReplay.Clear(); lastReplay = null;
            VaryServe(); BuildVisuals();
        }

        private void VaryServe() => Match.ServeJitter = new Vector2((float)(serveRandom.NextDouble() * .6 - .3), (float)(serveRandom.NextDouble() * .8 - .4));

        private void BuildVisuals()
        {
            intentRoot = new GameObject("Player intent / visual only");
            for (int i = 0; i < 4; i++)
            {
                var color = i < 2 ? new Color(1, .45f, .15f) : new Color(.2f, .7f, 1);
                movement[i] = Line("Player " + (i + 1) + " movement", color, .035f);
                shot[i] = Line("Player " + (i + 1) + " shot", new Color(color.r, color.g, color.b, .5f), .012f);
            }
            sources = Match.World.Players.SelectMany(p => p.Root.GetComponentsInChildren<Renderer>().Concat(p.Paddle.GetComponentsInChildren<Renderer>()))
                .Concat(new[] { Match.World.Ball.GetComponent<Renderer>() }).Where(r => r is MeshRenderer).ToArray();
            ghosts = new Transform[sources.Length]; liveVisibility = new bool[sources.Length];
            ghostRoot = new GameObject("Fault replay / meshes only / no physics");
            for (int i = 0; i < sources.Length; i++)
            {
                var go = new GameObject(sources[i].name + " replay"); go.transform.SetParent(ghostRoot.transform);
                go.AddComponent<MeshFilter>().sharedMesh = sources[i].GetComponent<MeshFilter>().sharedMesh;
                go.AddComponent<MeshRenderer>().sharedMaterials = sources[i].sharedMaterials;
                ghosts[i] = go.transform;
            }
            ghostRoot.SetActive(false);
        }

        private LineRenderer Line(string name, Color color, float width)
        {
            var go = new GameObject(name); go.transform.SetParent(intentRoot.transform);
            var renderer = go.AddComponent<LineRenderer>(); renderer.positionCount = 2;
            renderer.startWidth = renderer.endWidth = width;
            var material = new Material(Shader.Find("Sprites/Default")) { color = color }; materials.Add(material);
            renderer.sharedMaterial = material; return renderer;
        }

        private void Update()
        {
            if (Match == null) return;
            if (Input.GetKeyDown(KeyCode.Space)) Paused = !Paused;
            if (Input.GetKeyDown(KeyCode.N)) { Paused = false; NewGame(); }
            if (Input.GetKeyDown(KeyCode.R)) ToggleReplay();
            if (Input.GetKeyDown(KeyCode.I)) ShowIntent = !ShowIntent;
            intentRoot.SetActive(ShowIntent && !IsReplaying);
            if (IsReplaying)
            {
                if (!Paused) replayTime += Time.unscaledDeltaTime * Speed;
                ShowReplayFrame(Mathf.FloorToInt(replayTime * 60)); return;
            }
            if (!Paused)
            {
                budget += Mathf.Min(Time.unscaledDeltaTime, .1f) * Speed; int steps = 0;
                while (budget >= DoublesWorld.Dt && steps++ < 160)
                {
                    Match.Step(); budget -= DoublesWorld.Dt;
                    if (Match.Tick % 4 == 0 && Match.Tick != recordedTick)
                    {
                        currentReplay.Add(sources.Select(r => new Pose { position = r.transform.position, rotation = r.transform.rotation, scale = r.transform.lossyScale }).ToArray());
                        recordedTick = Match.Tick;
                    }
                    if (Match.CompletedRallies != completed)
                    {
                        completed = Match.CompletedRallies; lastReplay = new List<Pose[]>(currentReplay); currentReplay.Clear();
                        lastFault = Match.World.Rules.Winner < 0 ? "time limit; no point" : Match.World.Rules.LastFault.ToString();
                        if (Match.World.Rules.GameWinner >= 0) { Paused = true; break; }
                        Match.Next(); recordedTick = -1; VaryServe();
                    }
                }
            }
            for (int i = 0; i < 4; i++)
            {
                var p = Match.World.Players[i]; var action = Match.Actors.ActionFor(i);
                movement[i].SetPosition(0, p.Position + Vector3.up * .04f);
                movement[i].SetPosition(1, p.Position + action.WorldVelocity(i) * .35f + Vector3.up * .04f);
                shot[i].enabled = action.attempt;
                shot[i].SetPosition(0, p.Paddle.position); shot[i].SetPosition(1, Match.Swings[i].ShotTarget + Vector3.up * .04f);
            }
        }

        public void ToggleReplay()
        {
            if (IsReplaying) { ExitReplay(); return; }
            if (ReplayFrames == 0) return;
            IsReplaying = true; replayTime = 0;
            for (int i = 0; i < sources.Length; i++) { liveVisibility[i] = sources[i].enabled; sources[i].enabled = false; }
            var trail = Match.World.Ball.GetComponent<TrailRenderer>(); if (trail != null) trail.enabled = false;
            ghostRoot.SetActive(true); ShowReplayFrame(0);
        }

        public void ShowReplayFrame(int frame)
        {
            if (!IsReplaying || ReplayFrames == 0) return;
            var poses = lastReplay[Mathf.Clamp(frame, 0, ReplayFrames - 1)];
            for (int i = 0; i < ghosts.Length; i++)
            { ghosts[i].SetPositionAndRotation(poses[i].position, poses[i].rotation); ghosts[i].localScale = poses[i].scale; }
        }

        private void ExitReplay()
        {
            if (!IsReplaying) return;
            for (int i = 0; i < sources.Length; i++) sources[i].enabled = liveVisibility[i];
            var trail = Match.World.Ball.GetComponent<TrailRenderer>(); if (trail != null) trail.enabled = true;
            ghostRoot.SetActive(false); IsReplaying = false;
        }

        private void ClearVisuals()
        {
            if (ghostRoot != null) Destroy(ghostRoot);
            if (intentRoot != null) Destroy(intentRoot);
            foreach (var material in materials) Destroy(material); materials.Clear();
        }

        private void OnDestroy() { ExitReplay(); ClearVisuals(); Match?.Dispose(); Match = null; }

        private void OnGUI()
        {
            if (Match == null) return;
            var before = GUI.matrix; float scale = Screen.width / 1920f;
            GUI.matrix = Matrix4x4.Scale(new Vector3(scale, scale, 1));
            GUI.Box(new Rect(15, 15, 730, 245), "");
            var rules = Match.World.Rules;
            GUI.Label(new Rect(28, 23, 700, 25), $"INDEPENDENT PLAYER CONTROL PROBE   Orange {rules.Score[0]} : {rules.Score[1]} Blue");
            GUI.Label(new Rect(28, 48, 900, 25), ActorAsset == null ? "UNTRAINED. Scripted serve, swing, dead-ball reset + body IK. Physics is provisional."
                : "Learned decisions. Scripted serve, swing, dead-ball reset + body IK. Physics is provisional.");
            GUI.Label(new Rect(28, 73, 700, 25), $"Serve {rules.ScoreCall} | {rules.Phase} | 20 decisions/s/player | 25 ms action delay");
            for (int i = 0; i < 4; i++)
            {
                var action = Match.Actors.ActionFor(i); var swing = Match.Swings[i];
                GUI.Label(new Rect(28, 100 + i * 25, 700, 25), $"P{i + 1}: move ({action.moveX:F2}, {action.moveZ:F2}) | {(action.attempt ? "HIT" : "LEAVE")} | shot req/use {action.shot}/{swing.SelectedShot}{(swing.ShotCommitted ? "*" : "")} | brake {swing.SafetyLimited} | returns {Match.Metrics.legalHits[i]}");
            }
            GUI.Label(new Rect(28, 204, 700, 25), IsReplaying ? "REPLAY: " + lastFault : "Space pause | N reset | R replay | I intent | * shot locked near contact");
            GUI.Label(new Rect(28, 230, 700, 25), $"Both teammates request hit: {Match.Metrics.simultaneousChaseSteps} ticks | Safety limits: {Match.Metrics.safetyLimitedPlayerSteps}");
            GUI.matrix = before;
        }
    }
}
