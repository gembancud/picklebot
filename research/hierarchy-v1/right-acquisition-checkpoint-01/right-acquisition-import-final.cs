if(UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Import outside Play Mode");
UnityEditor.AssetDatabase.Refresh(UnityEditor.ImportAssetOptions.ForceSynchronousImport);
var model=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/ExecutionV1RightAcquisitionFinal01.onnx");
if(model==null)throw new System.InvalidOperationException("Final model import failed");
return "Imported fixed final checkpoint";
