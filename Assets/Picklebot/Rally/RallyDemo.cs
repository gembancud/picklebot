using UnityEngine;

namespace Picklebot.Rally
{
    public sealed class RallyDemo : MonoBehaviour
    {
        public TextAsset TrainedPolicy;
        public int InitialSeed = 820000;
        public RallyWorld World { get; private set; }
        public bool Paused;
        public float Speed = 1f;
        private RallyNeuralPolicy policy;
        private float accumulator, resetDelay;
        private int seed, nearScore, farScore, best;
        private bool scored;

        private void Start()
        {
            policy = new RallyNeuralPolicy(TrainedPolicy);
            World = new RallyWorld(true);
            seed = InitialSeed;
            World.Reset(seed);
        }

        private void Update()
        {
            if (World == null) return;
            if (Input.GetKeyDown(KeyCode.Space)) Paused = !Paused;
            if (Input.GetKeyDown(KeyCode.R)) Replay();
            if (Paused) return;
            if (World.Rules.Finished)
            {
                if (!scored)
                {
                    if (World.Rules.Winner < 0) nearScore++; else farScore++;
                    scored = true;
                }
                resetDelay += Time.unscaledDeltaTime;
                if (resetDelay > 1.5f) { seed++; ResetPoint(); }
                return;
            }
            accumulator += Mathf.Min(Time.unscaledDeltaTime, .1f) * Speed;
            while (accumulator >= RallyWorld.Dt && !World.Rules.Finished)
            {
                World.Step(policy);
                accumulator -= RallyWorld.Dt;
            }
            best = Mathf.Max(best, World.Rules.Returns);
        }

        public void Replay() => ResetPoint();
        private void ResetPoint()
        {
            accumulator = resetDelay = 0;
            scored = false;
            World.Reset(seed);
        }

        private void OnGUI()
        {
            if (World == null) return;
            GUI.skin.label.fontSize = 18;
            GUILayout.BeginArea(new Rect(20,20,480,265), GUI.skin.box);
            GUILayout.Label("AI RALLY  |  two learned paddles");
            GUILayout.Label($"Returns: {World.Rules.Returns}    Best: {best}");
            GUILayout.Label($"Orange {nearScore}  :  {farScore} Blue");
            GUILayout.Label(World.Rules.Result + (World.Rules.Finished ? $" — {(World.Rules.Winner < 0 ? "Orange" : "Blue")} wins" : ""));
            GUILayout.BeginHorizontal();
            if (GUILayout.Button(Paused ? "Resume [Space]" : "Pause [Space]", GUILayout.Height(32))) Paused = !Paused;
            if (GUILayout.Button("Replay serve [R]", GUILayout.Height(32))) Replay();
            if (GUILayout.Button(Speed < 1 ? "Normal speed" : "Slow motion", GUILayout.Height(32))) Speed = Speed < 1 ? 1f : .25f;
            GUILayout.EndHorizontal();
            GUILayout.Label($"Seed {seed}  |  neural position + angle control");
            GUILayout.Label("One bounce per side. Provisional elastic physics.");
            GUILayout.EndArea();
        }

        private void OnDestroy() { World?.Dispose(); World = null; }
    }
}
