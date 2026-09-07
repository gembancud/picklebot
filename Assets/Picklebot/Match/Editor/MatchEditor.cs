using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Picklebot.Inspection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Picklebot.Match.Editor
{
    [Serializable] public sealed class MatchPoint
    {
        public int seed,winner,hits,returns;
        public float seconds;
        public string reason;
        public float[] travel;
        public InspectionContact[] contacts;
        public ShotSample[] decisions;
    }
    [Serializable] public sealed class MatchReport
    {
        public string version=PickleballMatch.Version,sourceHash,configurationHash,configuration,unityVersion,createdUtc,modelHash,mode;
        public bool empiricalCalibration=false;
        public List<MatchPoint> points=new();
    }
    [InitializeOnLoad] public static class MatchEditor
    {
        public const string ModelPath="Assets/Picklebot/Match/Models/agents.json";
        public const string ScenePath="Assets/Picklebot/Scenes/PickleballMatch.unity";
        public static string Status {get;private set;}="idle";
        private static PickleballMatch match;
        private static MatchModels models;
        private static MatchReport report;
        private static int count,firstSeed;
        private static string output;
        private static bool training,stationary,centre;
        static MatchEditor()=>EditorApplication.playModeStateChanged+=s=>{if(s==PlayModeStateChange.ExitingPlayMode&&match!=null){Status="stopped: Play Mode ended";Stop();}};
        public static string Hash(string value)
        {using var sha=SHA256.Create();return BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(value))).Replace("-","").ToLowerInvariant();}
        public static string SourceHash()=>Hash(string.Join("\n",new[]{"Match","Inspection","Core","Simulation"}.SelectMany(f=>Directory.GetFiles("Assets/Picklebot/"+f,"*.cs",SearchOption.AllDirectories)).OrderBy(p=>p,StringComparer.Ordinal).Select(p=>p+"\n"+File.ReadAllText(p))));
        public static string Start(int episodes=500,bool learn=true,int seed=860000,string label="training",bool zero=false,bool centreOnly=false)
        {
            if(!EditorApplication.isPlaying||match!=null)throw new InvalidOperationException("Enter Play Mode and stop any current match job first.");
            if(episodes<1||episodes>5000||seed<(learn?860000:870000)||seed+episodes>(learn?870000:880000))throw new ArgumentException("Use separate training [860000,870000) and validation [870000,880000) seeds.");
            if(label.Any(c=>!char.IsLetterOrDigit(c)&&c!='-'))throw new ArgumentException("Invalid report label.");
            models=learn?new MatchModels():MatchModels.Load(File.ReadAllText(ModelPath));
            if(learn)models.seed=seed;
            count=episodes;firstSeed=seed;training=learn;stationary=zero;centre=centreOnly;
            match=new PickleballMatch(false);match.Reset(seed);
            if(!learn&&(models.configurationHash!=match.World.Configuration.ConfigurationHash||models.sourceHash!=SourceHash())){match.Dispose();match=null;throw new InvalidOperationException("Stale model evidence.");}
            if(centre)models.orange=models.blue=new ShotPolicy();
            report=new MatchReport {sourceHash=SourceHash(),configurationHash=match.World.Configuration.ConfigurationHash,
                configuration=match.World.Configuration.CanonicalText(),unityVersion=Application.unityVersion,createdUtc=DateTime.UtcNow.ToString("O"),
                mode=learn?"independent-policy training":zero?"stationary":centre?"centre":"trained",modelHash=learn?"fresh-zero-weights":Hash(File.ReadAllText(ModelPath))};
            Directory.CreateDirectory("artifacts/match");output=Path.GetFullPath("artifacts/match/"+label+".json");
            Status="running 0/"+count;EditorApplication.update+=Tick;return Status;
        }
        private static void Tick()
        {
            if(match==null)return;
            var timer=Stopwatch.StartNew();
            try
            {
                do
                {
                    match.Step(models.orange,models.blue,training,stationary);
                    if(!match.Finished)continue;
                    report.points.Add(new MatchPoint {seed=match.Seed,winner=match.Winner,hits=match.World.Contacts.Count(c=>c.surface=="PaddleNear"||c.surface=="PaddleFar"),
                        returns=match.World.Rules.Returns,seconds=match.World.Elapsed,reason=match.World.Rules.Finished?match.World.Rules.Result:"Time cap",travel=(float[])match.Travel.Clone(),
                        contacts=match.World.Contacts.ToArray(),decisions=match.Decisions.ToArray()});
                    if(training)
                    {
                        models.orange.Learn(match.Decisions,-1,match.Winner);models.blue.Learn(match.Decisions,1,match.Winner);models.episodes++;
                    }
                    Status=$"running {report.points.Count}/{count}";
                    var demo=UnityEngine.Object.FindFirstObjectByType<MatchDemo>();
                    if(demo!=null) {demo.TrainingStatus=(training?"Training: ":"Checking: ")+Status;if(training&&report.points.Count%25==0)demo.Install(models);}
                    if(report.points.Count==count)
                    {
                        if(training)SaveModels();
                        File.WriteAllText(output,JsonUtility.ToJson(report,true));Status="completed: "+output;
                        if(demo!=null) {demo.TrainingStatus=training?"Training complete":"Checks complete";if(training)demo.Install(models);}
                        Stop();return;
                    }
                    match.Reset(firstSeed+report.points.Count);
                }while(timer.ElapsedMilliseconds<20);
            }
            catch(Exception e){Status="failed: "+e;Stop();UnityEngine.Debug.LogException(e);}
        }
        private static void SaveModels()
        {
            models.configurationHash=report.configurationHash;models.sourceHash=report.sourceHash;models.createdUtc=DateTime.UtcNow.ToString("O");
            Directory.CreateDirectory(Path.GetDirectoryName(ModelPath));File.WriteAllText(ModelPath,JsonUtility.ToJson(models,true));AssetDatabase.ImportAsset(ModelPath);
        }
        public static void Stop(){EditorApplication.update-=Tick;match?.Dispose();match=null;}
        [MenuItem("Picklebot/Match/Save visible learning")]
        public static void SaveVisible()
        {
            if(match!=null)throw new InvalidOperationException("Wait for the training job to finish.");
            var demo=UnityEngine.Object.FindFirstObjectByType<MatchDemo>();if(demo==null||demo.ActiveModels==null)throw new InvalidOperationException("Run the match scene first.");
            var live=demo.ActiveModels;live.configurationHash=demo.Match.World.Configuration.ConfigurationHash;live.sourceHash=SourceHash();live.createdUtc=DateTime.UtcNow.ToString("O");
            Directory.CreateDirectory("artifacts/match");File.WriteAllText("artifacts/match/visible-learning-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss")+".json",JsonUtility.ToJson(live,true));
        }
        [MenuItem("Picklebot/Match/Create full-size match")]
        public static string CreateScene()
        {
            if(EditorApplication.isPlaying||File.Exists(ScenePath))throw new InvalidOperationException("Stop Play. Do not replace an existing scene.");
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Additive);SceneManager.SetActiveScene(scene);
            var demo=new GameObject("Pickleball Match").AddComponent<MatchDemo>();demo.Models=AssetDatabase.LoadAssetAtPath<TextAsset>(ModelPath);
            var camera=new GameObject("Match Camera").AddComponent<Camera>();camera.tag="MainCamera";camera.transform.position=new Vector3(10,12,-15);camera.transform.LookAt(Vector3.zero);
            camera.fieldOfView=48;camera.nearClipPlane=.02f;camera.farClipPlane=100;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.025f,.04f,.06f);
            var light=new GameObject("Match Light").AddComponent<Light>();light.type=LightType.Directional;light.intensity=1.1f;light.transform.rotation=Quaternion.Euler(45,-30,0);
            if(!EditorSceneManager.SaveScene(scene,ScenePath))throw new IOException("Scene save failed.");return ScenePath;
        }
    }
}
