using UnityEngine;
namespace Picklebot.Match
{
    public sealed class MatchDemo:MonoBehaviour
    {
        public TextAsset Models;
        public MatchModels ActiveModels {get;private set;}
        public PickleballMatch Match {get;private set;}
        public bool Paused,Learning;
        public float Speed=1;
        public string TrainingStatus="";
        public int OrangeScore,BlueScore,Points,BestHits;
        private float accumulator,delay;
        private bool scored;
        private int seed=870000;
        private void Start()
        {
            ActiveModels=Models!=null?MatchModels.Load(Models.text):new MatchModels();
            Match=new PickleballMatch(true);Match.Reset(seed);
            if(ActiveModels.configurationHash!=null&&ActiveModels.configurationHash!=""&&ActiveModels.configurationHash!=Match.World.Configuration.ConfigurationHash)
                throw new System.InvalidOperationException("Model physics configuration changed.");
        }
        public void Install(MatchModels models) {ActiveModels=MatchModels.Load(JsonUtility.ToJson(models));}
        public void Replay() {Match.Reset(seed);delay=accumulator=0;scored=false;}
        private void Update()
        {
            if(Match==null)return;
            if(Input.GetKeyDown(KeyCode.Space))Paused=!Paused;
            if(Input.GetKeyDown(KeyCode.R))Replay();
            if(Paused)return;
            if(Match.Finished)
            {
                if(!scored)
                {
                    int winner=Match.Winner;if(winner<0)OrangeScore++;if(winner>0)BlueScore++;Points++;
                    if(Learning)
                    {
                        ActiveModels.orange.Learn(Match.Decisions,-1,winner);ActiveModels.blue.Learn(Match.Decisions,1,winner);ActiveModels.episodes++;
                    }
                    BestHits=Mathf.Max(BestHits,Hits());scored=true;
                }
                delay+=Time.unscaledDeltaTime;if(delay>1.2f){seed++;Replay();}return;
            }
            accumulator+=Mathf.Min(Time.unscaledDeltaTime,.1f)*Speed;
            while(accumulator>=Picklebot.Inspection.InspectionWorld.Dt&&!Match.Finished)
            {
                Match.Step(ActiveModels.orange,ActiveModels.blue,Learning);accumulator-=Picklebot.Inspection.InspectionWorld.Dt;
            }
        }
        private int Hits()
        {
            int count=0;foreach(var c in Match.World.Contacts)if(c.surface=="PaddleNear"||c.surface=="PaddleFar")count++;return count;
        }
        private void OnGUI()
        {
            if(Match==null)return;
            float scale=Mathf.Max(1,Screen.height/1000f);var old=GUI.matrix;GUI.matrix=Matrix4x4.Scale(Vector3.one*scale);
            GUI.skin.label.fontSize=18;GUI.skin.button.fontSize=17;GUI.skin.toggle.fontSize=17;
            GUILayout.BeginArea(new Rect(12,12,480,480),GUI.skin.box);
            GUILayout.Label("PICKLEBALL: ORANGE vs BLUE");
            GUILayout.Label($"Points  ORANGE {OrangeScore} : {BlueScore} BLUE");
            GUILayout.Label($"Paddle hits {Hits()} | best {BestHits} | serve {seed}");
            GUILayout.Label("Full-size court | outdoor ball | provisional physics");
            GUILayout.Label("AI learns shot choice. Contact motion is scripted.");
            GUILayout.Label($"Training points: {ActiveModels.episodes}");
            if(TrainingStatus!="")GUILayout.Label(TrainingStatus);
            GUILayout.Label(Match.Finished?(Match.Winner==0?"20 s cap: no point":Match.World.Rules.Result):Match.World.Rules.Result);
            GUILayout.Label($"Ball {Match.World.Ball.linearVelocity.magnitude:F1} m/s | spin {Match.World.Ball.angularVelocity.magnitude:F1} rad/s");
            GUILayout.BeginHorizontal();
            if(GUILayout.Button(Paused?"Resume [Space]":"Pause [Space]",GUILayout.Height(32)))Paused=!Paused;
            if(GUILayout.Button("Replay [R]",GUILayout.Height(32)))Replay();
            if(GUILayout.Button(Speed<1?"Normal speed":"Slow motion",GUILayout.Height(32)))Speed=Speed<1?1:.25f;
            GUILayout.EndHorizontal();
            Learning=GUILayout.Toggle(Learning,"Learn during visible play (exploration on)");
            GUILayout.Label("Reward: winner +1, loser -1. No rally reward.");
            GUILayout.Label("Live learning stays in memory until saved.");
            GUILayout.Label("Basic rally rules and kitchen ground-disc proxy.");
            GUILayout.EndArea();GUI.matrix=old;
        }
        private void OnDestroy(){Match?.Dispose();Match=null;}
    }
}
