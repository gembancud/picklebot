using System;
using System.IO;
using System.Linq;
using Picklebot.Doubles;
using UnityEditor;
using UnityEngine;

namespace Picklebot.PlayerLearning.Editor
{
    // Editor-only observer. Rendering and wall-clock presentation may change;
    // observations, policy actions, rewards and physical time steps may not.
    public sealed class PlayerTrainingMonitorWindow : EditorWindow
    {
        private PlayerMlDrillsV3 drills;
        private PlayerMlTeamsV3 teams;
        private GameObject shown;
        private int court;
        private bool showCourt=true, closeView=true;
        private string lastStatus="Waiting for a training or evaluation run.";
        private double nextLookup;

        [MenuItem("Window/Picklebot/Training Monitor")]
        public static void Open() => GetWindow<PlayerTrainingMonitorWindow>("Training Monitor").Show();
        private void OnEnable() { EditorApplication.update+=Observe; }
        private void OnDisable() { EditorApplication.update-=Observe; HideShown(); }
        private void HideShown()
        {
            if(shown!=null)foreach(var r in shown.GetComponentsInChildren<Renderer>())r.enabled=false;
            shown=null;
        }
        private void Observe()
        {
            if(!EditorApplication.isPlaying) { drills=null;teams=null;shown=null;Repaint();return; }
            if(EditorApplication.timeSinceStartup>=nextLookup)
            {
                nextLookup=EditorApplication.timeSinceStartup+.25;
                if(drills==null)drills=FindFirstObjectByType<PlayerMlDrillsV3>();
                if(teams==null)teams=FindFirstObjectByType<PlayerMlTeamsV3>();
            }
            var world=CurrentWorld(out int player);
            if(world!=null && showCourt && shown!=world.Root)
            {
                HideShown();shown=world.Root;
                foreach(var r in shown.GetComponentsInChildren<Renderer>())r.enabled=true;
                foreach(var c in world.Fixture.NetColliders)c.GetComponent<Renderer>().enabled=false;
                foreach(var r in shown.GetComponentsInChildren<Renderer>())
                {var c=r.GetComponent<Collider>();if(c!=null&&!c.enabled)r.enabled=false;}
                Frame(world,player);
            }
            if(!showCourt && shown!=null)HideShown();
            if(shown!=null)SceneView.RepaintAll();
            Repaint();
        }
        private DoublesWorld CurrentWorld(out int player)
        {
            player=0;
            if(drills!=null && drills.Report!=null && drills.ActiveArenas.Count>0)
            {
                court=Mathf.Clamp(court,0,drills.ActiveArenas.Count-1);
                var drill=drills.ActiveArenas[court].Drill;player=drill.Player;
                return drill.Match.World;
            }
            if(teams!=null && teams.Report!=null && teams.ActiveArenas.Count>0)
            {court=Mathf.Clamp(court,0,teams.ActiveArenas.Count-1);return teams.ActiveArenas[court].Match.World;}
            return null;
        }
        private void Frame(DoublesWorld world,int player)
        {
            var view=SceneView.lastActiveSceneView; if(view==null)view=SceneView.GetWindow<SceneView>();view.sceneLighting=false;
            if(closeView)view.LookAt(world.Players[player].Position+Vector3.up*.8f,
                Quaternion.Euler(24,player<2?-30:150,0),2.7f,false,true);
            else view.LookAt(Vector3.zero,Quaternion.Euler(48,0,0),11,false,true);
            view.Repaint();
        }
        private void Speed(int ticks)
        {
            string path=null;int physicalTicks=0;
            if(drills!=null && drills.Report!=null){drills.TicksPerFrame=ticks;path=drills.EvidenceDirectory;physicalTicks=drills.Report.physicsTicks;}
            else if(teams!=null && teams.Report!=null){teams.TicksPerFrame=ticks;path=teams.EvidenceDirectory;physicalTicks=teams.Report.physicsTicks;}
            if(!string.IsNullOrEmpty(path))File.AppendAllText(Path.Combine(path,"monitor-events.jsonl"),
                "{\"event\":\"watch_speed\",\"ticksPerFrame\":"+ticks+",\"physicsTicks\":"+physicalTicks+"}\n");
        }
        private void OnGUI()
        {
            EditorGUILayout.LabelField("Live policy practice",EditorStyles.boldLabel);
            var world=CurrentWorld(out int player);
            if(world==null)
            {
                EditorGUILayout.HelpBox(lastStatus+"\nStart a drill/team scene to watch its active court here.",MessageType.Info);
            }
            else
            {
                bool isDrill=drills!=null && drills.Report!=null;
                int count=isDrill?drills.ActiveArenas.Count:teams.ActiveArenas.Count;
                lastStatus=isDrill?drills.Report.status:teams.Report.status;
                string mode=isDrill?(drills.RequireTrainer?"TRAINING":"SAVED POLICY EVALUATION"):(teams.RequireTrainer?"TEAM TRAINING":"TEAM EVALUATION");
                EditorGUILayout.LabelField(mode+" â€” "+lastStatus);
                court=EditorGUILayout.IntSlider("Court",court,0,Mathf.Max(0,count-1));
                EditorGUILayout.LabelField("Courts running",count.ToString());
                if(isDrill)
                {
                    var d=drills.ActiveArenas[court].Drill;
                    EditorGUILayout.LabelField("Task",d.Task);
                    EditorGUILayout.LabelField("Active player",(d.Player+1)+" (other players inactive in this drill)");
                    EditorGUILayout.LabelField("Seed / tick",d.Seed+" / "+d.Match.Tick);
                    EditorGUILayout.LabelField("Completed attempts",drills.Report.completedEpisodes.ToString());
                    var last=drills.Episodes.LastOrDefault();
                    if(last!=null)EditorGUILayout.LabelField("Last result",last.outcome);
                    EditorGUILayout.LabelField("Legal returns",drills.Episodes.Count(e=>e.outcome=="legal_return").ToString());
                }
                else
                {
                    EditorGUILayout.LabelField("Started / completed games",teams.Report.startedGames+" / "+teams.Report.completeGames);
                    EditorGUILayout.LabelField("Rallies",teams.Report.rallies.ToString());
                }
                showCourt=EditorGUILayout.Toggle("Show selected court",showCourt);
                bool close=EditorGUILayout.Toggle("Close view of player",closeView);
                if(close!=closeView){closeView=close;Frame(world,player);}
                EditorGUILayout.BeginHorizontal();
                if(GUILayout.Button("Watch speed"))Speed(1);
                if(GUILayout.Button("Fast training"))Speed(48);
                EditorGUILayout.EndHorizontal();
                if(GUILayout.Button("Focus Scene view")){Frame(world,player);SceneView.GetWindow<SceneView>().Focus();}
                EditorGUILayout.HelpBox("Watch speed advances one physics tick per Editor frame. All courts keep learning. Scene view shows the selected court; Game view may be blank.",MessageType.None);
            }
            if(GUILayout.Button("Open TensorBoard metrics"))Application.OpenURL("http://127.0.0.1:6008/#scalars&regexInput=Picklebot");
        }
    }
}
