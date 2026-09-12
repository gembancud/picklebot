if (!UnityEditor.EditorApplication.isPlaying) throw new System.InvalidOperationException("Requires Play Mode");
if (UnityEngine.Object.FindObjectsByType<Picklebot.PlayerLearning.PlayerMlDrillsV3>(UnityEngine.FindObjectsInactive.Include,UnityEngine.FindObjectsSortMode.None).Length!=0) throw new System.InvalidOperationException("Expected empty scene");
var field=typeof(Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena).GetField("goals",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
if(field==null)throw new System.InvalidOperationException("Goal adapter changed");
var summaries=new System.Collections.Generic.List<object>();
foreach(string model in new[]{"ExecutionV1Placement01"}) foreach(int side in new[]{-1,1})
{
    var root=new UnityEngine.GameObject("Counterfactual "+model+" "+side);root.SetActive(false);
    try
    {
        var run=root.AddComponent<Picklebot.PlayerLearning.PlayerMlDrillsV3>();
        var goals=root.AddComponent<Picklebot.PlayerLearning.PlayerExecutionDrillsV1>();
        run.AutoRun=false;run.RequireTrainer=false;run.Task="movement-maintenance";
        run.FirstSeed=1109529;run.SeedCount=64;run.ArenaCount=8;run.MaximumReturnDifficulty=.25f;
        run.FixedServeSides="both";run.MovementRange=.1f;run.AlignDrillDecisions=false;run.RecordDecisions=true;
        run.InferenceModel=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/"+model+".onnx");
        if(run.InferenceModel==null)throw new System.InvalidOperationException("Missing model");
        run.EvidenceDirectory="F:/dev/picklebot/artifacts/hierarchy-v1/target-response-placement-01/"+model+"-"+side;
        run.SourceIdentity="02e964f7c75b2bd39ff209691b9ffdc944465c7030c7497975b6da6165cac9c0";
        goals.SampleShotTargets=true;goals.TargetRadius=1.5f;goals.LegalTargetReward=.25f;
        root.SetActive(true);run.InitializeRun();
        var assigned=new System.Collections.Generic.Dictionary<Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena,int>();
        for(int tick=0;tick<100000 && run.Report.status!="seed_budget_complete";tick++)
        {
            foreach(var arena in run.ActiveArenas)
            {
                if(arena.Finished)continue;
                var drill=arena.Drill;
                if(assigned.TryGetValue(arena,out int oldSeed)&&oldSeed==drill.Seed)continue;
                var values=(Picklebot.PlayerLearning.PlayerExecutionGoalV1[])field.GetValue(arena);
                float x=1.8f*side;
                if(Picklebot.PlayerControlsIntegration.PlayerContactDrillV3.IsServeTask(drill.Task))
                {
                    int sign=drill.Player<2?1:-1;
                    x=UnityEngine.Mathf.Sign(drill.Match.World.Rules.ServiceX(drill.Match.World.Rules.DesignatedReceiver)*sign)*(side<0?.7f:2.3f);
                }
                values[drill.Player]=new Picklebot.PlayerLearning.PlayerExecutionGoalV1(drill.Player,0,Picklebot.PlayerLearning.PlayerIntentV1.PlayBall,shotTarget:new UnityEngine.Vector2(x,4.5f),shotRadius:1.5f);
                assigned[arena]=drill.Seed;
            }
            run.StepOneTick();
        }
        if(run.Report.status!="seed_budget_complete"||goals.Completed!=64)throw new System.InvalidOperationException("Incomplete evaluation");
        summaries.Add(new{model,side,episodes=goals.Completed,legal=goals.LegalLandings,targets=goals.TargetsHit});
    }
    finally
    {
        UnityEngine.Object.DestroyImmediate(root);
        if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();
    }
}
string result=Newtonsoft.Json.JsonConvert.SerializeObject(summaries,Newtonsoft.Json.Formatting.Indented);
System.IO.File.WriteAllText("F:/dev/picklebot/artifacts/hierarchy-v1/target-response-placement-01/summary.json",result);
return result;


