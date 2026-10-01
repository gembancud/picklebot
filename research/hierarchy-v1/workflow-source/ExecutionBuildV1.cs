using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;

namespace Picklebot.PlayerLearning.Editor
{
    public static class ExecutionBuildV1
    {
        public static void FromCommandLine()
        {
            var args=Environment.GetCommandLineArgs();
            string Arg(string name)=>PlayerWorkerPlanV3.Argument(args,name,true);
            string output=Arg("--execution-output");
            string source=Arg("--execution-source");
            string modelHash=Arg("--execution-model-hash");
            string model=Arg("--execution-model");
            if(!Path.IsPathFullyQualified(output)||Directory.Exists(output))throw new ArgumentException("Fresh absolute output directory required.");
            var previous=EditorSceneManager.GetSceneManagerSetup();
            if(SceneManager.GetActiveScene().isDirty)throw new InvalidOperationException("Unsaved Editor scene.");
            string preview="Assets/Picklebot/Scenes/"+Path.GetFileName(output)+"-empty.unity";
            if(File.Exists(preview))throw new InvalidOperationException("Refusing to overwrite an existing scene.");
            try
            {
                var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
                if(!EditorSceneManager.SaveScene(scene,preview))throw new InvalidOperationException("Scene save failed.");
                PlayerHeadlessBuildV3.Build(output,source,modelHash,model,preview);
            }
            finally{EditorSceneManager.RestoreSceneManagerSetup(previous);}
        }
    }
}
