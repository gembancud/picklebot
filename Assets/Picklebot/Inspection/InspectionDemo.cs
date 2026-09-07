using System;
using System.IO;
using UnityEngine;

namespace Picklebot.Inspection
{
    public sealed class InspectionDemo:MonoBehaviour
    {
        public InspectionWorld World { get; private set; }
        public bool Paused=true, DemonstrationStroke=true;
        public float Speed=1;
        public int SelectedPlayer;
        private float accumulator;
        private int view;
        private Camera cameraView;
        private string exportMessage="";
        private static readonly string[] Names={"1 Court drop","2 Angled bounce","3 Flat strike","4 Brush up","5 Brush down","6 Serve + rules","7 Granite reference"};
        private void Start() { World=new InspectionWorld(true);cameraView=Camera.main;SetCamera(); }
        private void Update()
        {
            if(World==null)return;
            if(Input.GetKeyDown(KeyCode.Space))Paused=!Paused;
            if(Input.GetKeyDown(KeyCode.R))Select((int)World.Preset);
            if(Input.GetKeyDown(KeyCode.Tab)) { SelectedPlayer=1-SelectedPlayer;SetCamera(); }
            if(Input.GetKeyDown(KeyCode.C)) { view=(view+1)%3;SetCamera(); }
            for(int i=0;i<7;i++)if(Input.GetKeyDown((KeyCode)((int)KeyCode.Alpha1+i)))Select(i);
            if(view!=0)SetCamera();
            if(Paused||World.AtTimeLimit)return;
            var translation=new Vector3(Axis(KeyCode.LeftArrow,KeyCode.RightArrow),Axis(KeyCode.Q,KeyCode.E),Axis(KeyCode.DownArrow,KeyCode.UpArrow));
            var rotation=new Vector3(Axis(KeyCode.K,KeyCode.I),Axis(KeyCode.J,KeyCode.L),Axis(KeyCode.U,KeyCode.O));
            var move=new Vector2(Axis(KeyCode.A,KeyCode.D),Axis(KeyCode.S,KeyCode.W));
            accumulator+=Mathf.Min(Time.unscaledDeltaTime,.1f)*Speed;
            while(accumulator>=InspectionWorld.Dt&&!World.AtTimeLimit)
            {
                World.Step(SelectedPlayer,translation,rotation,move,DemonstrationStroke&&SelectedPlayer==0);
                accumulator-=InspectionWorld.Dt;
            }
        }
        private static float Axis(KeyCode negative,KeyCode positive)=>(Input.GetKey(positive)?1:0)-(Input.GetKey(negative)?1:0);
        public void Select(int preset)
        {
            if(preset<0||preset>=Names.Length)throw new ArgumentOutOfRangeException(nameof(preset));
            World.Reset((InspectionPreset)preset);accumulator=0;Paused=false;exportMessage="";
            if(preset==2||preset==3||preset==4)SelectedPlayer=0;
            SetCamera();
        }
        private void SetCamera()
        {
            if(cameraView==null||World==null)return;
            Vector3 target;
            if(view==0) { cameraView.transform.position=new Vector3(10,12,-15);target=new Vector3(0,0,0);cameraView.fieldOfView=48; }
            else if(view==1) { target=World.Motors[SelectedPlayer].Body.position;cameraView.transform.position=target+new Vector3(2,1.3f,-2);cameraView.fieldOfView=48; }
            else { target=World.Ball.position;cameraView.transform.position=target+new Vector3(3,2,-3);cameraView.fieldOfView=50; }
            cameraView.transform.LookAt(target);
        }
        [Serializable] private sealed class ExportRecord
        {
            public string version,createdUtc,profile,configurationHash,configuration,preset,releaseDatum;
            public bool empiricalCalibration=false;
            public float seconds,firstReboundBottomHeight,firstReboundTopHeight;
            public bool reboundComplete;
            public InspectionContact[] contacts;
            public InspectionFrame[] frames;
        }
        public string Export()
        {
            string directory=Path.GetFullPath("artifacts/inspection");Directory.CreateDirectory(directory);
            string path=Path.Combine(directory,"inspection-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff")+".json");
            File.WriteAllText(path,JsonUtility.ToJson(new ExportRecord {version=InspectionWorld.Version,createdUtc=DateTime.UtcNow.ToString("O"),
                profile=Picklebot.Core.SimulationConfigV1.ReferenceProfile,configurationHash=World.Configuration.ConfigurationHash,
                configuration=World.Configuration.CanonicalText(),preset=World.Preset.ToString(),seconds=World.Elapsed,
                firstReboundBottomHeight=World.FirstReboundHeight,firstReboundTopHeight=World.FirstReboundHeight+World.Configuration.BallDiameter,
                reboundComplete=World.ReboundComplete,contacts=World.Contacts.ToArray(),frames=World.Frames.ToArray(),
                releaseDatum="Drop release measured to ball bottom. Granite 1.9812 m datum is assumed, not certification evidence."},true));
            exportMessage="Saved: "+Path.GetFileName(path);return path;
        }
        private void OnGUI()
        {
            if(World==null)return;
            float scale=Mathf.Max(1,Screen.height/1000f);var old=GUI.matrix;GUI.matrix=Matrix4x4.Scale(new Vector3(scale,scale,1));
            GUI.skin.label.fontSize=17;GUI.skin.button.fontSize=16;GUI.skin.toggle.fontSize=16;
            GUILayout.BeginArea(new Rect(12,12,470,640),GUI.skin.box);
            GUILayout.Label("PICKLEBALL PHYSICS INSPECTION");
            GUILayout.Label("6.096 x 13.411 m | outdoor 40-hole profile");
            GUILayout.Label("74 mm / 24 g ball | acrylic court | no AI model");
            GUILayout.Label("PROVISIONAL: not fitted to measured court data");
            GUILayout.BeginHorizontal();
            if(GUILayout.Button(Paused?"Resume [Space]":"Pause [Space]",GUILayout.Height(30)))Paused=!Paused;
            if(GUILayout.Button("Reset [R]",GUILayout.Height(30)))Select((int)World.Preset);
            if(GUILayout.Button(Speed<1?"Normal":"Slow motion",GUILayout.Height(30)))Speed=Speed<1?1:.25f;
            GUILayout.EndHorizontal();
            for(int row=0;row<3;row++)
            {
                GUILayout.BeginHorizontal();for(int col=0;col<2;col++) {int i=row*2+col;if(GUILayout.Button(Names[i],GUILayout.Height(28)))Select(i);}GUILayout.EndHorizontal();
            }
            if(GUILayout.Button(Names[6],GUILayout.Height(28)))Select(6);
            DemonstrationStroke=GUILayout.Toggle(DemonstrationStroke,"Fixed stroke on presets 3-5 (not AI)");
            GUILayout.Label($"Control: {(SelectedPlayer==0?"Orange":"Blue")} [Tab] | Camera [C]");
            GUILayout.Label("Arrows: paddle X/Z | Q/E: paddle down/up");
            GUILayout.Label("I/K: pitch | J/L: yaw | U/O: roll");
            GUILayout.Label("WASD: move player ground marker");
            GUILayout.Label($"Time {World.Elapsed:F2}s | speed {World.Ball.linearVelocity.magnitude:F2} m/s | spin {World.Ball.angularVelocity.magnitude:F1} rad/s");
            GUILayout.Label($"Paddle Y {World.Motors[SelectedPlayer].Body.position.y:F2} m | contact count {World.Contacts.Count}");
            if(World.ReboundComplete)GUILayout.Label($"First rebound: bottom {World.FirstReboundHeight:F3} m | top {World.FirstReboundHeight+World.Configuration.BallDiameter:F3} m");
            GUILayout.Label(World.RulesEnabled?World.Rules.Result:"Inspection: ball continues after each collision");
            if(World.RulesEnabled)GUILayout.Label("Kitchen uses ground-disc proxy, not full human footwork");
            if(World.AtTimeLimit)GUILayout.Label("20-second inspection limit. Select Reset to continue.");
            if(GUILayout.Button("Export measurements",GUILayout.Height(28)))Export();
            if(exportMessage!="")GUILayout.Label(exportMessage);
            GUILayout.EndArea();GUI.matrix=old;
        }
        private void OnDestroy() { World?.Dispose();World=null; }
    }
}
