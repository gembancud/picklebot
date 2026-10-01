if(UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Wait for Play Mode to stop.");
var previous=Newtonsoft.Json.JsonConvert.DeserializeObject<UnityEditor.SceneManagement.SceneSetup[]>(System.IO.File.ReadAllText("F:/dev/picklebot/artifacts/hierarchy-v1/placement-dev-02/evaluation-scene-before.json"));
if(previous.Length>0 && System.Array.Exists(previous,s=>s.isLoaded) && System.Array.Exists(previous,s=>s.isActive) && System.Array.TrueForAll(previous,s=>!s.isLoaded || !string.IsNullOrEmpty(s.path)))
    UnityEditor.SceneManagement.EditorSceneManager.RestoreSceneManagerSetup(previous);
else UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene,UnityEditor.SceneManagement.NewSceneMode.Single);
System.IO.File.WriteAllText("F:/dev/picklebot/artifacts/hierarchy-v1/placement-dev-02/evaluation-editor-restored.json","{\"restored\":true,\"exitRequested\":true}");
UnityEditor.EditorApplication.delayCall+=()=>UnityEditor.EditorApplication.Exit(0);
return "Restored; closing task-owned Editor";

