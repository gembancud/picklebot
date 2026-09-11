using System;
using System.IO;
using System.Security.Cryptography;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Unity.InferenceEngine;

namespace Picklebot.PlayerLearning.Editor
{
    public static class PlayerHeadlessBuildV3
    {
        public static string Build(string outputDirectory,string sourceIdentity,string modelHash,string modelAssetPath="Assets/Picklebot/PlayerLearning/Models/AfterLateralPractice01.onnx",string previewScenePath="Assets/Picklebot/Scenes/ArticulatedLateralPracticePreview01.unity")
        {
            if(EditorApplication.isPlaying||EditorApplication.isCompiling||EditorUtility.scriptCompilationFailed||BuildPipeline.isBuildingPlayer)throw new InvalidOperationException("Build requires an idle, cleanly compiled Editor.");
            if(!PlayerWorkerPlanV3.IsHash(sourceIdentity)||!PlayerWorkerPlanV3.IsHash(modelHash)||!Path.IsPathFullyQualified(outputDirectory)||Directory.Exists(outputDirectory))throw new ArgumentException("New absolute build output and pinned identities required.");
            var scene=SceneManager.GetActiveScene();
            if(scene.isDirty||scene.path!=previewScenePath)throw new InvalidOperationException("Unexpected or unsaved scene.");
            string original=scene.path;
            string scenePath="Assets/Picklebot/Scenes/"+Path.GetFileName(outputDirectory.TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar))+".unity";
            if(File.Exists(scenePath))throw new InvalidOperationException("Refuse to overwrite build scene.");
            var model=AssetDatabase.LoadAssetAtPath<ModelAsset>(modelAssetPath);
            if(model==null)throw new InvalidOperationException("Missing evaluation model.");
            using(var digest=SHA256.Create())
                if(BitConverter.ToString(digest.ComputeHash(File.ReadAllBytes(modelAssetPath))).Replace("-","").ToLowerInvariant()!=modelHash)throw new InvalidOperationException("Evaluation model hash mismatch.");
            Directory.CreateDirectory(outputDirectory);
            File.WriteAllText(Path.Combine(outputDirectory,"build-started.json"),"{\"status\":\"building\",\"sourceIdentity\":\""+sourceIdentity+"\"}");
            try
            {
                var buildScene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                var root=new GameObject("Standalone independent-player worker bootstrap");
                var boot=root.AddComponent<PlayerHeadlessBootstrapV3>();
                boot.BuiltSourceIdentity=sourceIdentity;boot.BuiltModelHash=modelHash;boot.EvaluationModel=model;
                boot.RuntimeCourtShader=Shader.Find("Universal Render Pipeline/Lit")??Shader.Find("Standard");
                if(boot.RuntimeCourtShader==null)throw new InvalidOperationException("Missing dynamically-created court material shader.");
                if(!EditorSceneManager.SaveScene(buildScene,scenePath))throw new InvalidOperationException("Build scene save failed.");
                string binary=Path.Combine(outputDirectory,"Picklebot.exe");
                var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scenePath},locationPathName=binary,target=BuildTarget.StandaloneWindows64,options=BuildOptions.None});
                var result=new {status=report.summary.result.ToString(),errors=report.summary.totalErrors,warnings=report.summary.totalWarnings,bytes=report.summary.totalSize,seconds=report.summary.totalTime.TotalSeconds,binary,scene=scenePath,sourceIdentity,modelHash,messages=report.steps.SelectMany(s=>s.messages).Where(m=>m.type==LogType.Error||m.type==LogType.Exception).Select(m=>m.content).ToArray()};
                File.WriteAllText(Path.Combine(outputDirectory,"build-result.json"),Newtonsoft.Json.JsonConvert.SerializeObject(result,Newtonsoft.Json.Formatting.Indented));
                if(report.summary.result!=BuildResult.Succeeded)throw new InvalidOperationException("Standalone build failed; inspect its build-result.json.");
                return binary;
            }
            finally{EditorSceneManager.OpenScene(original);}
        }
    }
}
