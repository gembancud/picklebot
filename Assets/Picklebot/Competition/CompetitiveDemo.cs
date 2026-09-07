using UnityEngine;

namespace Picklebot.Competition
{
    public sealed class CompetitiveDemo : MonoBehaviour
    {
        public TextAsset StrokeModel, StrategyModel;
        public int InitialSeed = 845000;
        public bool Paused;
        public float Speed = 1;
        public CompetitiveWorld World { get; private set; }
        private DensePolicy strategy;
        private float accumulator, delay;
        private int seed, orangeScore, blueScore, best;
        private bool scored;
        private void Start()
        {
            strategy = new DensePolicy(StrategyModel.text,"competitive-strategy-v1",8,5);
            World = new CompetitiveWorld(new DensePolicy(StrokeModel.text,"competitive-stroke-v1",10,6),true);
            seed=InitialSeed; World.Reset(seed);
        }
        private void Update()
        {
            if(World==null)return;
            if(Input.GetKeyDown(KeyCode.Space))Paused=!Paused;
            if(Input.GetKeyDown(KeyCode.R))Replay();
            if(Paused)return;
            if(World.Finished)
            {
                if(!scored)
                {
                    if(!World.Truncated) { if(World.Rules.Winner<0)orangeScore++;else blueScore++; }
                    scored=true;
                }
                delay+=Time.unscaledDeltaTime;
                if(delay>1.5f) { seed++;Replay(); }
                return;
            }
            accumulator+=Mathf.Min(Time.unscaledDeltaTime,.1f)*Speed;
            while(accumulator>=CompetitiveWorld.Dt&&!World.Finished)
            {
                World.Step(strategy,strategy);
                accumulator-=CompetitiveWorld.Dt;
            }
            best=Mathf.Max(best,World.Rules.Returns);
        }
        public void Replay()
        {
            accumulator=delay=0;scored=false;World.Reset(seed);
        }
        private void OnGUI()
        {
            if(World==null)return;
            float scale=Mathf.Max(1,Screen.height/900f);
            var old=GUI.matrix; GUI.matrix=Matrix4x4.Scale(new Vector3(scale,scale,1));
            GUI.skin.label.fontSize=18; GUI.skin.button.fontSize=16;
            GUILayout.BeginArea(new Rect(16,16,490,250),GUI.skin.box);
            GUILayout.Label("AI MATCH | competing paddles");
            GUILayout.Label($"Orange {orangeScore} : {blueScore} Blue    Returns {World.Rules.Returns}");
            GUILayout.Label(World.Truncated?"Time cap: no point awarded":World.Rules.Result+(World.Rules.Finished?$" - {(World.Rules.Winner<0?"Orange":"Blue")} wins":""));
            GUILayout.BeginHorizontal();
            if(GUILayout.Button(Paused?"Resume [Space]":"Pause [Space]",GUILayout.Height(34)))Paused=!Paused;
            if(GUILayout.Button("Replay [R]",GUILayout.Height(34)))Replay();
            if(GUILayout.Button(Speed<1?"Normal speed":"Slow motion",GUILayout.Height(34)))Speed=Speed<1?1:.25f;
            GUILayout.EndHorizontal();
            GUILayout.Label("Learned stroke + learned point-winning shot choice");
            GUILayout.Label("Small paddles. Energy loss. One bounce per side.");
            GUILayout.Label($"Seed {seed} | Provisional physics | Best {best} returns");
            GUILayout.EndArea();GUI.matrix=old;
        }
        private void OnDestroy() { World?.Dispose();World=null; }
    }
}
