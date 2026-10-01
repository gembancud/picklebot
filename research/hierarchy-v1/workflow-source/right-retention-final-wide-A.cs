var fixtureCheck=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText("F:/dev/picklebot/artifacts/hierarchy-v1/wide-movement-fixture-01/fixture-summary.json"));
if((bool?)fixtureCheck["outcomeAllowed"]!=true || (int?)fixtureCheck["seedCount"]!=512)throw new System.InvalidOperationException("Wide reset fixture must pass before policy evaluation");
if(!UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Requires Play Mode");
if(UnityEngine.Object.FindObjectsByType<Picklebot.PlayerLearning.PlayerMlDrillsV3>(UnityEngine.FindObjectsInactive.Include,UnityEngine.FindObjectsSortMode.None).Length!=0)throw new System.InvalidOperationException("Expected empty scene");
string model="ExecutionV1RightRetentionFinal01", condition="A";
string expectedModelHash="a8af32d4adea142bbbaf3942d4c2927266fd798153dff5edfa155a867b4e6590", expectedCheckpointHash="ebe469fce16e41c9963d50e4a6783fb49496b21d865c5ac6653057524411397e";
string absoluteModelPath="F:/dev/picklebot/Assets/Picklebot/PlayerLearning/Models/ExecutionV1RightRetentionFinal01.onnx";
System.Func<string> actualModelHash=()=>{using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(absoluteModelPath))).Replace("-","").ToLowerInvariant();};
if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model hash mismatch before evaluation");
int region=0;
string output="F:/dev/picklebot/artifacts/hierarchy-v1/right-retention-01/evaluation/wide/"+model+"/"+condition;
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
    run.FirstSeed=1109849;run.SeedCount=512;run.ArenaCount=8;run.MaximumReturnDifficulty=.25f;
    run.FixedServeSides="both";run.MovementRange=.25f;run.MovementPattern="axes";run.MovementRehearsalRange=0;
    run.MovementRecoveryMix=false;run.InterleavedRecovery=false;run.AlignDrillDecisions=false;
    run.InferenceModel=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/"+model+".onnx");
    if(run.InferenceModel==null)throw new System.InvalidOperationException("Missing model");
    run.EvidenceDirectory=output;run.SourceIdentity="de8bda54ce1aad9fcb545226c91a92a115f08b41e57dc036b6f9431e15b1ed4e";
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
    for(int tick=0;tick<400000&&run.Report.status!="seed_budget_complete";tick++)
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
    if(run.PrecontactAlignmentReward||run.Report.precontactAlignmentReward||run.MovementForwardProgressReward||run.Report.movementForwardProgressReward)throw new System.InvalidOperationException("Shaping enabled during evaluation");
    foreach(var ep in run.Episodes)if(ep.precontactAlignmentRewardEnabled||ep.precontactShapingReward!=0f||ep.precontactTransitions!=0||ep.movementForwardProgressRewardEnabled)throw new System.InvalidOperationException("Evaluation received shaping");
    System.IO.File.WriteAllText(output+"/first-decisions.json",Newtonsoft.Json.JsonConvert.SerializeObject(first));
    if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model changed during evaluation");
    System.IO.File.WriteAllText(output+"/model-identity.json",Newtonsoft.Json.JsonConvert.SerializeObject(new{model,modelHash=expectedModelHash,checkpointHash=expectedCheckpointHash,step=2097180,sourceIdentity="de8bda54ce1aad9fcb545226c91a92a115f08b41e57dc036b6f9431e15b1ed4e"}));
    result=Newtonsoft.Json.JsonConvert.SerializeObject(new{model,condition,episodes=goals.Completed,legal=goals.LegalLandings,targets=goals.TargetsHit});
    System.IO.File.WriteAllText(output+"/summary.json",result);
}
finally
{
    UnityEngine.Object.DestroyImmediate(root);
    if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();
}
return result;
