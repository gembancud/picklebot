if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Evaluation requires Play Mode.");
if (UnityEngine.Object.FindObjectsByType<Picklebot.PlayerLearning.PlayerMlDrillsV3>(UnityEngine.FindObjectsInactive.Include,UnityEngine.FindObjectsSortMode.None).Length!=0) throw new System.InvalidOperationException("Evaluation scene is not empty.");
var summaries=new System.Collections.Generic.List<object>();
foreach(string name in new[]{"ExecutionV1Initial","ExecutionV1Smoke01"})
{
    var root=new UnityEngine.GameObject("Goal evaluation "+name);root.SetActive(false);
    try
    {
        var run=root.AddComponent<Picklebot.PlayerLearning.PlayerMlDrillsV3>();
        var goals=root.AddComponent<Picklebot.PlayerLearning.PlayerExecutionDrillsV1>();
        run.AutoRun=false;run.RequireTrainer=false;run.Task="movement-maintenance";
        run.FirstSeed=1109529;run.SeedCount=64;run.ArenaCount=8;run.MaximumReturnDifficulty=.25f;
        run.FixedServeSides="both";run.MovementRange=.1f;run.AlignDrillDecisions=true;
        run.InferenceModel=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/"+name+".onnx");
        if(run.InferenceModel==null)throw new System.InvalidOperationException("Missing exported model "+name);
        run.EvidenceDirectory="F:/dev/picklebot/artifacts/hierarchy-v1/placement-dev-01/"+name;
        run.SourceIdentity="02e964f7c75b2bd39ff209691b9ffdc944465c7030c7497975b6da6165cac9c0";
        goals.SampleShotTargets=true;goals.TargetRadius=1.5f;goals.LegalTargetReward=.25f;
        root.SetActive(true);run.InitializeRun();
        for(int i=0;i<100000 && run.Report.status!="seed_budget_complete";i++)run.StepOneTick();
        if(run.Report.status!="seed_budget_complete"||run.Episodes.Count!=64||goals.Completed!=64)throw new System.InvalidOperationException("Evaluation did not finish its budget.");
        summaries.Add(new{model=name,episodes=goals.Completed,legal=goals.LegalLandings,targets=goals.TargetsHit});
    }
    finally
    {
        UnityEngine.Object.DestroyImmediate(root);
        if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();
    }
}
string result=Newtonsoft.Json.JsonConvert.SerializeObject(summaries,Newtonsoft.Json.Formatting.Indented);
System.IO.File.WriteAllText("F:/dev/picklebot/artifacts/hierarchy-v1/placement-dev-01/summary.json",result);
return result;
