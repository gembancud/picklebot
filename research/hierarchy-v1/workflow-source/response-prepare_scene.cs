if(UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Expected idle evaluation Editor.");
var previous=UnityEditor.SceneManagement.EditorSceneManager.GetSceneManagerSetup();
for(int i=0;i<UnityEngine.SceneManagement.SceneManager.sceneCount;i++)if(UnityEngine.SceneManagement.SceneManager.GetSceneAt(i).isDirty)throw new System.InvalidOperationException("Unsaved scene; do not replace it.");
System.IO.File.WriteAllText("F:/dev/picklebot/artifacts/hierarchy-v1/target-response-01/evaluation-scene-before.json",Newtonsoft.Json.JsonConvert.SerializeObject(previous));
UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene,UnityEditor.SceneManagement.NewSceneMode.Single);
return "Empty task-owned evaluation scene ready";

