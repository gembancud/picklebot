if(UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Expected idle evaluation Editor.");
string axesBase="F:/dev/picklebot/artifacts/hierarchy-v1/axes-recovery-01";
if(!System.IO.File.Exists(axesBase+"/training/verification.json")||!System.IO.File.Exists(axesBase+"/selected-models.json"))throw new System.InvalidOperationException("Verified training and fixed endpoint selection required.");
var previous=UnityEditor.SceneManagement.EditorSceneManager.GetSceneManagerSetup();
for(int i=0;i<UnityEngine.SceneManagement.SceneManager.sceneCount;i++)if(UnityEngine.SceneManagement.SceneManager.GetSceneAt(i).isDirty)throw new System.InvalidOperationException("Unsaved scene; do not replace it.");
using(var file=new System.IO.FileStream(axesBase+"/candidate-evaluation-scene-before.json",System.IO.FileMode.CreateNew))
using(var writer=new System.IO.StreamWriter(file))writer.Write(Newtonsoft.Json.JsonConvert.SerializeObject(previous));
UnityEditor.SceneManagement.EditorSceneManager.NewScene(UnityEditor.SceneManagement.NewSceneSetup.EmptyScene,UnityEditor.SceneManagement.NewSceneMode.Single);
return "Empty task-owned evaluation scene ready";
