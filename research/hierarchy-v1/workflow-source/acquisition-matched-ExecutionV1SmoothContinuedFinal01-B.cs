if(!UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Requires Play Mode");
if(UnityEngine.Object.FindObjectsByType<Picklebot.PlayerLearning.PlayerMlDrillsV3>(UnityEngine.FindObjectsInactive.Include,UnityEngine.FindObjectsSortMode.None).Length!=0)throw new System.InvalidOperationException("Expected empty scene");
string model="ExecutionV1SmoothContinuedFinal01", condition="B";
string expectedModelHash="40047704eaf92ae933e861abfbe4c6f262a4595685ca985e3c1a185804ed13cb", expectedCheckpointHash="93029a5bfe5a13815f47d1487ff15c3e9455516ee3b5609d9e38f0c0f82e778d";
string absoluteModelPath="F:/dev/picklebot/Assets/Picklebot/PlayerLearning/Models/ExecutionV1SmoothContinuedFinal01.onnx";
System.Func<string> actualModelHash=()=>{using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(absoluteModelPath))).Replace("-","").ToLowerInvariant();};
if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model hash mismatch before evaluation");
int region=1;
string output="F:/dev/picklebot/artifacts/hierarchy-v1/right-acquisition-01/evaluation/acquisition/"+model+"/"+condition;
var field=typeof(Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena).GetField("goals",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
if(System.IO.Directory.Exists(output))throw new System.InvalidOperationException("Preserve existing acquisition evaluation");
var root=new UnityEngine.GameObject("Two-region evaluation");root.SetActive(false);
var first=new System.Collections.Generic.Dictionary<int,object>();
string result="";
try
{
    var run=root.AddComponent<Picklebot.PlayerLearning.PlayerMlDrillsV3>();
    var goals=root.AddComponent<Picklebot.PlayerLearning.PlayerExecutionDrillsV1>();
    run.AutoRun=false;run.RequireTrainer=false;run.Task="right-return-acquisition";
    run.FirstSeed=1109849;run.SeedCount=512;run.ArenaCount=16;run.MaximumReturnDifficulty=0;
    run.FixedServeSides="both";run.MovementRange=.0625f;run.MovementPattern="lateral-right";run.MovementRehearsalRange=0;
    run.MovementRecoveryMix=false;run.InterleavedRecovery=false;run.AlignDrillDecisions=false;run.PrecontactAlignmentReward=false;run.MovementForwardProgressReward=false;
    run.InferenceModel=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/"+model+".onnx");
    if(run.InferenceModel==null)throw new System.InvalidOperationException("Missing model");
    run.EvidenceDirectory=output;run.SourceIdentity="078092d28f4dde258c904e3a925a9a1fd555f3c55384d92f012b6cdeb8bb60c4";
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
    if(run.Report.status!="seed_budget_complete"||goals.Completed!=512||first.Count!=512)throw new System.InvalidOperationException("Incomplete evaluation");
    foreach(var ep in run.Episodes)if(ep.movementPattern!="lateral-right"||ep.movementRegion!=5||ep.movementRange!=.0625f||ep.precontactAlignmentRewardEnabled||ep.precontactShapingReward!=0||ep.movementForwardProgressRewardEnabled)throw new System.InvalidOperationException("Acquisition reset or reward contract mismatch");
    System.IO.File.WriteAllText(output+"/first-decisions.json",Newtonsoft.Json.JsonConvert.SerializeObject(first));
    if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model changed during evaluation");
    System.IO.File.WriteAllText(output+"/model-identity.json",Newtonsoft.Json.JsonConvert.SerializeObject(new{model,modelHash=expectedModelHash,checkpointHash=expectedCheckpointHash,step=1048609,trainingSourceIdentity="5f8c4a10a777ea4c69c0a2ef01831163252a3614bddaaedfe2ab4024d04831c9",sourceIdentity="078092d28f4dde258c904e3a925a9a1fd555f3c55384d92f012b6cdeb8bb60c4"}));
    result=Newtonsoft.Json.JsonConvert.SerializeObject(new{model,condition,episodes=goals.Completed,legal=goals.LegalLandings,targets=goals.TargetsHit});
    System.IO.File.WriteAllText(output+"/summary.json",result);
}
finally
{
    UnityEngine.Object.DestroyImmediate(root);
    if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();
}
return result;
