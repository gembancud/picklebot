if(UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Wait for Play Mode to stop.");
string progressBase="F:/dev/picklebot/artifacts/hierarchy-v1/movement-progress-trace-02";
var previous=Newtonsoft.Json.JsonConvert.DeserializeObject<UnityEditor.SceneManagement.SceneSetup[]>(System.IO.File.ReadAllText(progressBase+"/candidate-evaluation-scene-before.json"));
if(previous.Length>0 && System.Array.Exists(previous,s=>s.isLoaded) && System.Array.Exists(previous,s=>s.isActive) && System.Array.TrueForAll(previous,s=>!s.isLoaded || !string.IsNullOrEmpty(s.path)))
    UnityEditor.SceneManagement.EditorSceneManager.RestoreSceneManagerSetup(previous);
else UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene,UnityEditor.SceneManagement.NewSceneMode.Single);
using(var file=new System.IO.FileStream(progressBase+"/candidate-evaluation-editor-restored.json",System.IO.FileMode.CreateNew))
using(var writer=new System.IO.StreamWriter(file))writer.Write("{\"restored\":true,\"exitRequested\":true}");
UnityEditor.EditorApplication.delayCall+=()=>UnityEditor.EditorApplication.Exit(0);
return "Restored; closing task-owned Editor";
