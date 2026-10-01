if(UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Import before evaluation Play Mode.");
UnityEditor.AssetDatabase.Refresh(UnityEditor.ImportAssetOptions.ForceSynchronousImport);
foreach(string name in new[]{"ExecutionV1SmoothContinuedMid01","ExecutionV1SmoothContinuedFinal01"})
    if(UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/"+name+".onnx")==null)
        throw new System.InvalidOperationException("Missing selected model "+name);
return "Both selected models imported";
