using UnityEngine;
using System.Collections.Generic;
using System.Linq;
namespace Picklebot.Doubles
{
    public sealed class DoublesDemo : MonoBehaviour
    {
        public DoublesMatch Match {get;private set;}
        public bool Paused,CentreOnly=false,Learning,SampleActions=true;
        public TextAsset ContactModelAsset,TeamModelAsset;
        public float Speed=1;
        public int InteractiveSeed=950000;
        private float budget;
        private int lastCompleted;
        private DoublesFrame[] replay;
        private string replayFault;
        private bool replaying;
        private float replayTime;
        private struct Pose { public Vector3 position,scale;public Quaternion rotation; }
        private Transform[] bodyTransforms;
        private readonly List<Pose[]> currentPoses=new();
        private Pose[][] replayPoses;
        private System.Random serveRandom;
        private void Start()=>NewGame();
        public void NewGame()
        {
            var retainedModels=Match?.Models;
            int seed=InteractiveSeed++;serveRandom=new System.Random(seed);
            Match?.Dispose();Match=new DoublesMatch(true,seed){AutoNext=false,SampleActions=SampleActions};
            if(ContactModelAsset!=null)Match.ContactModel=ContactModel.Load(ContactModelAsset.text);
            if(TeamModelAsset!=null)Match.Models=DoublesModels.Load(TeamModelAsset.text);
            else Match.Models=retainedModels;
            foreach(var renderer in Match.World.Root.GetComponentsInChildren<Renderer>())
            {
                if(renderer.name!="OutCatchFloor")continue;
                var block=new MaterialPropertyBlock();block.SetColor("_BaseColor",new Color(.055f,.16f,.19f));block.SetColor("_Color",new Color(.055f,.16f,.19f));renderer.SetPropertyBlock(block);
            }
            bodyTransforms=Match.World.Players.SelectMany(p=>p.Root.GetComponentsInChildren<Transform>()).ToArray();
            currentPoses.Clear();budget=0;lastCompleted=0;replaying=false;
            VaryServe();
        }
        private void VaryServe()=>Match.ServeJitter=new Vector2((float)(serveRandom.NextDouble()*.6-.3),(float)(serveRandom.NextDouble()*.8-.4));
        private void OnDestroy(){Match?.Dispose();Match=null;}
        private void Update()
        {
            if(Match==null)return;
            if(Input.GetKeyDown(KeyCode.Space))Paused=!Paused;
            if(Input.GetKeyDown(KeyCode.N))NewGame();
            if(Input.GetKeyDown(KeyCode.R))ToggleReplay();
            if(replaying)
            {
                if(!Paused)replayTime+=Time.unscaledDeltaTime*Speed;
                int frame=Mathf.Clamp(Mathf.FloorToInt(replayTime*60),0,replay.Length-1);var f=replay[frame];
                Match.World.Ball.transform.position=f.ball;
                for(int i=0;i<4;i++){var p=Match.World.Players[i];p.Reset(f.players[i]);p.Paddle.position=f.paddles[i];p.Paddle.rotation=f.rotations[i];p.Paddle.transform.SetPositionAndRotation(f.paddles[i],f.rotations[i]);p.Draw();}
                if(replayPoses!=null&&frame<replayPoses.Length)for(int i=0;i<bodyTransforms.Length;i++)
                {var pose=replayPoses[frame][i];bodyTransforms[i].SetPositionAndRotation(pose.position,pose.rotation);bodyTransforms[i].localScale=pose.scale;}
                return;
            }
            Match.CentreOnly=CentreOnly;Match.Learning=Learning;Match.SampleActions=SampleActions;
            if(Paused)return;budget+=Mathf.Min(Time.unscaledDeltaTime,.1f)*Speed;
            int limit=0;while(budget>=DoublesWorld.Dt&&limit++<160)
            {
                Match.Step();budget-=DoublesWorld.Dt;
                if(Match.World.Frames.Count>currentPoses.Count)
                    currentPoses.Add(bodyTransforms.Select(t=>new Pose{position=t.position,rotation=t.rotation,scale=t.localScale}).ToArray());
                if(Match.CompletedRallies>lastCompleted)
                {
                    lastCompleted=Match.CompletedRallies;replay=Match.World.Frames.ToArray();replayPoses=currentPoses.ToArray();currentPoses.Clear();replayFault=Match.World.Rules.Winner<0?"Time limit - no point":Match.World.Rules.LastFault.ToString();
                    if(Match.World.Rules.GameWinner>=0){Paused=true;break;}Match.Next();VaryServe();
                }
            }
        }
        public bool HasReplay=>replay?.Length>0;
        public bool IsReplaying=>replaying;
        public void ToggleReplay()
        {if(!HasReplay)return;replaying=!replaying;replayTime=0;if(!replaying)NewGame();}
        private void OnGUI()
        {
            if(Match==null)return;var r=Match.World.Rules;
            var previousMatrix=GUI.matrix;float scale=Screen.width/1920f;GUI.matrix=Matrix4x4.Scale(new Vector3(scale,scale,1));
            GUI.Box(new Rect(15,15,610,178),"");var style=new GUIStyle(GUI.skin.label){fontSize=18};
            GUI.Label(new Rect(28,23,530,28),$"PICKLEBALL DOUBLES   Orange {r.Score[0]} : {r.Score[1]} Blue",style);
            GUI.Label(new Rect(28,54,530,25),$"Serve {r.ScoreCall}  |  Player {r.Server+1}  |  {r.Phase}");
            GUI.Label(new Rect(28,78,530,25),$"Active player {Match.ActivePlayer+1}  |  Contacts {r.Hits}  |  {r.LastFault}");
            GUI.Label(new Rect(28,102,580,25),Match.Models==null?"Development: scripted control. No trained team model.":"Learned contact + shot choice. Scripted movement and body IK.");
            Paused=GUI.Toggle(new Rect(28,130,100,25),Paused,"Pause");CentreOnly=GUI.Toggle(new Rect(140,130,140,25),CentreOnly,"Centre shots");
            GUI.Label(new Rect(285,130,310,25),"Space: pause   R: replay   N: new game");
            GUI.Label(new Rect(28,155,580,25),replaying?$"REPLAY / last fault: {replayFault}":"Outdoor 40-hole ball / acrylic court. Contact parameters are provisional.");
            GUI.matrix=previousMatrix;
        }
    }
}
