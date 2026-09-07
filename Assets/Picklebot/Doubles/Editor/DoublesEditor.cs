using System;
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
namespace Picklebot.Doubles.Editor
{
    public static class DoublesEditor
    {
        public const string ScenePath="Assets/Picklebot/Scenes/PickleballDoubles.unity";
        [MenuItem("Picklebot/Doubles/Create development scene")]
        public static void CreateScene()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play before scene creation.");
            if(File.Exists(ScenePath))throw new InvalidOperationException("The doubles scene already exists.");
            if(!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())return;
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            new GameObject("Doubles game").AddComponent<DoublesDemo>();
            var camera=new GameObject("Main Camera").AddComponent<Camera>();camera.tag="MainCamera";camera.transform.position=new Vector3(11,12,-14);camera.transform.LookAt(new Vector3(0,.6f,0));camera.fieldOfView=48;
            camera.backgroundColor=new Color(.04f,.07f,.10f);camera.clearFlags=CameraClearFlags.SolidColor;camera.nearClipPlane=.1f;camera.farClipPlane=100;camera.gameObject.AddComponent<AudioListener>();
            var light=new GameObject("Sun").AddComponent<Light>();light.type=LightType.Directional;light.intensity=1.4f;light.transform.rotation=Quaternion.Euler(50,-30,0);light.shadows=LightShadows.Soft;
            RenderSettings.ambientLight=new Color(.5f,.5f,.5f);EditorSceneManager.SaveScene(scene,ScenePath);
        }
        public static string Snapshot()
        {
            var demo=UnityEngine.Object.FindFirstObjectByType<DoublesDemo>();if(demo?.Match==null)return "No running doubles game.";
            var m=demo.Match;var w=m.World;
            return JsonUtility.ToJson(new SnapshotData{time=w.Time,phase=w.Rules.Phase.ToString(),fault=w.Rules.LastFault.ToString(),active=m.ActivePlayer,hits=w.Rules.Hits,
                ball=w.Ball.position,velocity=w.Ball.linearVelocity,completed=m.CompletedRallies,playerHits=m.PlayerHits,contacts=w.Contacts.ToArray()},true);
        }
        public static string Probe(int steps=2400)
        {
            var demo=UnityEngine.Object.FindFirstObjectByType<DoublesDemo>();
            if(demo?.Match==null)throw new InvalidOperationException("Start Play first.");
            demo.Paused=true;demo.Match.AutoNext=false;
            for(int i=0;i<steps&&!demo.Match.World.Rules.Dead;i++)demo.Match.Step();
            return Snapshot();
        }
        [MenuItem("Picklebot/Doubles/Open trained game")]
        public static void InstallModels()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first.");
            var scene=EditorSceneManager.OpenScene(ScenePath);
            var demo=UnityEngine.Object.FindFirstObjectByType<DoublesDemo>();
            demo.ContactModelAsset=AssetDatabase.LoadAssetAtPath<TextAsset>(ContactTraining.ModelPath);
            demo.TeamModelAsset=AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Picklebot/Doubles/Models/teams.json");
            if(demo.ContactModelAsset==null||demo.TeamModelAsset==null)throw new InvalidOperationException("Train and import both models first.");
            demo.Paused=false;demo.CentreOnly=false;demo.Learning=false;demo.SampleActions=true;demo.InteractiveSeed=950000;demo.Speed=1;
            var camera=Camera.main;camera.orthographic=true;camera.orthographicSize=9.1f;camera.transform.position=new Vector3(10,12,-13);camera.transform.LookAt(new Vector3(0,.4f,0));
            EditorSceneManager.MarkSceneDirty(scene);EditorSceneManager.SaveScene(scene);
        }
        [Serializable] private sealed class SnapshotData {public float time;public string phase,fault;public int active,hits,completed;public Vector3 ball,velocity;public int[] playerHits;public DoublesContact[] contacts;}
    }
}
