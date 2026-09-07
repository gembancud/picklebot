using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Picklebot.Core;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Picklebot.Inspection.Editor
{
    public static class InspectionEditor
    {
        public const string ScenePath="Assets/Picklebot/Scenes/PickleballInspection.unity";
        [MenuItem("Picklebot/Inspection/Create full-size scene")]
        public static string CreateScene()
        {
            if(EditorApplication.isPlaying)throw new InvalidOperationException("Stop Play first.");
            if(File.Exists(ScenePath))throw new InvalidOperationException("Inspection scene exists. Open it instead of replacing it.");
            var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Additive);SceneManager.SetActiveScene(scene);
            new GameObject("Pickleball Inspection").AddComponent<InspectionDemo>();
            var camera=new GameObject("Inspection Camera").AddComponent<Camera>();camera.tag="MainCamera";
            camera.transform.position=new Vector3(10,12,-15);camera.transform.LookAt(Vector3.zero);camera.fieldOfView=48;
            camera.nearClipPlane=.02f;camera.farClipPlane=100;camera.clearFlags=CameraClearFlags.SolidColor;
            camera.backgroundColor=new Color(.025f,.04f,.06f);camera.gameObject.AddComponent<AudioListener>();
            var light=new GameObject("Inspection Light").AddComponent<Light>();light.type=LightType.Directional;light.intensity=1.1f;light.transform.rotation=Quaternion.Euler(45,-30,0);
            if(!EditorSceneManager.SaveScene(scene,ScenePath))throw new IOException("Scene save failed.");
            return ScenePath;
        }
        [Serializable] public sealed class PresetResult
        {
            public string preset,ruleResult;
            public float reboundBottom,reboundTop,seconds;
            public bool reboundComplete;
            public Vector3 finalVelocity,finalSpin;
            public InspectionContact[] contacts;
        }
        [Serializable] public sealed class Verification
        {
            public string version,createdUtc,unityVersion,configurationHash,configuration;
            public bool empiricalCalibration=false;
            public string releaseDatum="Bottom of ball; granite reference is not a certification claim.";
            public List<string> sourceFiles=new();
            public List<string> sourceHashes=new();
            public List<PresetResult> presets=new();
        }
        public static string Verify()
        {
            if(!EditorApplication.isPlaying)throw new InvalidOperationException("Use Play Mode for physical contacts.");
            using var world=new InspectionWorld(false);
            var report=new Verification {version=InspectionWorld.Version,createdUtc=DateTime.UtcNow.ToString("O"),unityVersion=Application.unityVersion,
                configurationHash=world.Configuration.ConfigurationHash,configuration=world.Configuration.CanonicalText()};
            foreach(var folder in new[]{"Assets/Picklebot/Inspection","Assets/Picklebot/Core","Assets/Picklebot/Simulation"})
                foreach(var path in Directory.GetFiles(folder,"*.cs",SearchOption.AllDirectories).OrderBy(p=>p,StringComparer.Ordinal))
                {
                    using var sha=SHA256.Create();report.sourceFiles.Add(path);
                    report.sourceHashes.Add(BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant());
                }
            foreach(InspectionPreset preset in Enum.GetValues(typeof(InspectionPreset)))
            {
                world.Reset(preset);
                for(int i=0;i<960;i++)world.Step(demonstration:true);
                report.presets.Add(new PresetResult {preset=preset.ToString(),ruleResult=world.RulesEnabled?world.Rules.Result:"Inspection only",reboundBottom=world.FirstReboundHeight,
                    reboundTop=world.FirstReboundHeight+world.Configuration.BallDiameter,reboundComplete=world.ReboundComplete,seconds=world.Elapsed,
                    finalVelocity=world.Ball.linearVelocity,finalSpin=world.Ball.angularVelocity,contacts=world.Contacts.ToArray()});
            }
            Directory.CreateDirectory("artifacts/inspection");var output="artifacts/inspection/verification.json";
            File.WriteAllText(output,JsonUtility.ToJson(report,true));return Path.GetFullPath(output);
        }
    }
}
