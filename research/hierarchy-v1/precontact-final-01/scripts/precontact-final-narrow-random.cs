if(!UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Requires Play Mode");
if(UnityEngine.Object.FindObjectsByType<Picklebot.PlayerLearning.PlayerMlDrillsV3>(UnityEngine.FindObjectsInactive.Include,UnityEngine.FindObjectsSortMode.None).Length!=0)throw new System.InvalidOperationException("Expected empty scene");
string model="ExecutionV1PrecontactFinal01", condition="random";
string expectedModelHash="334026a8fcfa156f52331aadf8c1eea4c25ffa53997322a6ea25954aa12676e0", expectedCheckpointHash="d46814c54313bf3d332242039a83bb2a57357aca05e5097bc9a2515eb4f1129a";
string absoluteModelPath="F:/dev/picklebot/Assets/Picklebot/PlayerLearning/Models/ExecutionV1PrecontactFinal01.onnx";
System.Func<string> actualModelHash=()=>{using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(absoluteModelPath))).Replace("-","").ToLowerInvariant();};
if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model hash mismatch before evaluation");
int region=-1;
string output="F:/dev/picklebot/artifacts/hierarchy-v1/precontact-alignment-01/evaluation/narrow/"+model+"/"+condition;
var field=typeof(Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena).GetField("goals",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
if(System.IO.Directory.Exists(output))throw new System.InvalidOperationException("Preserve existing evaluation");
var root=new UnityEngine.GameObject("Two-region evaluation");root.SetActive(false);
var first=new System.Collections.Generic.Dictionary<int,object>();
string result="";
try
{
    var run=root.AddComponent<Picklebot.PlayerLearning.PlayerMlDrillsV3>();
    var goals=root.AddComponent<Picklebot.PlayerLearning.PlayerExecutionDrillsV1>();
    run.AutoRun=false;run.RequireTrainer=false;run.Task="movement-maintenance";
    run.PrecontactAlignmentReward=false;run.MovementForwardProgressReward=false;
    run.FirstSeed=1109593;run.SeedCount=256;run.ArenaCount=8;run.MaximumReturnDifficulty=.25f;
    run.FixedServeSides="both";run.MovementRange=.025f;run.MovementPattern="lateral";run.MovementRehearsalRange=.1f;
    run.MovementRecoveryMix=true;run.InterleavedRecovery=true;run.AlignDrillDecisions=false;
    run.InferenceModel=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/"+model+".onnx");
    if(run.InferenceModel==null)throw new System.InvalidOperationException("Missing model");
    run.EvidenceDirectory=output;run.SourceIdentity="02db54a0f390d9a015bce4dfad86fca8f01b10319737d2af9950924c40b1fe68";
    goals.RewardMode=Picklebot.PlayerLearning.PlayerExecutionDrillsV1.LinearReward;goals.SampleShotTargets=true;goals.TargetLayout=region<0?"random":"two-regions";
    goals.TargetRadius=region<0?1.5f:1f;goals.LegalTargetReward=.25f;
    root.SetActive(true);run.InitializeRun();
    foreach(var arena in run.ActiveArenas)foreach(var agent in arena.Agents)
    {
        var captured=arena;
        agent.Received+=(current,actions)=>
        {
            if(current.ObservedTick==0&&!first.ContainsKey(captured.Drill.Seed))
                first[captured.Drill.Seed]=new{seed=captured.Drill.Seed,player=current.Seat,observation=current.LastPolicyObservation,physical=current.LastCommand.ToArray()};
        };
    }
    var assigned=new System.Collections.Generic.Dictionary<Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena,int>();
    for(int tick=0;tick<200000&&run.Report.status!="seed_budget_complete";tick++)
    {
        if(region>=0)foreach(var arena in run.ActiveArenas)
        {
            if(arena.Finished)continue;var drill=arena.Drill;
            if(assigned.TryGetValue(arena,out int oldSeed)&&oldSeed==drill.Seed)continue;
            bool serve=Picklebot.PlayerControlsIntegration.PlayerContactDrillV3.IsServeTask(drill.Task);
            int sign=drill.Player<2?1:-1;
            int serviceSign=serve?(int)UnityEngine.Mathf.Sign(drill.Match.World.Rules.ServiceX(drill.Match.World.Rules.DesignatedReceiver)*sign):0;
            var values=(Picklebot.PlayerLearning.PlayerExecutionGoalV1[])field.GetValue(arena);
            values[drill.Player]=new Picklebot.PlayerLearning.PlayerExecutionGoalV1(drill.Player,0,Picklebot.PlayerLearning.PlayerIntentV1.PlayBall,
                shotTarget:Picklebot.PlayerLearning.PlayerExecutionDrillsV1.RegionTarget(serve,serviceSign,region),shotRadius:1f);
            assigned[arena]=drill.Seed;
        }
        run.StepOneTick();
    }
    if(run.Report.status!="seed_budget_complete"||goals.Completed!=256||first.Count!=256)throw new System.InvalidOperationException("Incomplete evaluation");
    if(run.PrecontactAlignmentReward||run.Report.precontactAlignmentReward||run.MovementForwardProgressReward||run.Report.movementForwardProgressReward)throw new System.InvalidOperationException("Shaping enabled during evaluation");
    foreach(var ep in run.Episodes)if(ep.precontactAlignmentRewardEnabled||ep.precontactShapingReward!=0f||ep.precontactTransitions!=0||ep.movementForwardProgressRewardEnabled)throw new System.InvalidOperationException("Evaluation received shaping");
    System.IO.File.WriteAllText(output+"/first-decisions.json",Newtonsoft.Json.JsonConvert.SerializeObject(first));
    if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model changed during evaluation");
    System.IO.File.WriteAllText(output+"/model-identity.json",Newtonsoft.Json.JsonConvert.SerializeObject(new{model,modelHash=expectedModelHash,checkpointHash=expectedCheckpointHash,step=2097186,sourceIdentity="02db54a0f390d9a015bce4dfad86fca8f01b10319737d2af9950924c40b1fe68"}));
    result=Newtonsoft.Json.JsonConvert.SerializeObject(new{model,condition,episodes=goals.Completed,legal=goals.LegalLandings,targets=goals.TargetsHit});
    System.IO.File.WriteAllText(output+"/summary.json",result);
}
finally
{
    UnityEngine.Object.DestroyImmediate(root);
    if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();
}
return result;
