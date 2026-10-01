string axesRepo=@"F:/dev/picklebot";
System.Func<string,string> axesHash=path=>{using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();};
System.Action verifyAxesInputs=()=>{
    if(axesHash(@"F:/dev/picklebot/artifacts/hierarchy-v1/axes-recovery-01/plan.json")!="38d5e09ce80ef22a0403edc04f645a5b0eabcdcd92054a9580753c3300f36e8d")throw new System.InvalidOperationException("Frozen axes plan changed");
    if(axesHash(@"F:/dev/picklebot/training/snapshots/execution-v1-axes-recovery-final-01.pt")!="c6915987421940f0e2cb9ca18d3b1902fc89efba5efce97c37f3d1c3b614287a")throw new System.InvalidOperationException("Selected checkpoint changed");
    if(axesHash(@"F:/dev/picklebot/artifacts/hierarchy-v1/axes-recovery-01/source-records.json")!="6c6b01eda3e0edf88f50694ee74f1542e1f275279763e2c6edaa60098cdb0543")throw new System.InvalidOperationException("Frozen source manifest changed");
    var axesSource=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(@"F:/dev/picklebot/artifacts/hierarchy-v1/axes-recovery-01/source-records.json"));
    if((string)axesSource["sourceIdentity"]!="557040f9cec6f4825aa263e192de05d98388962b98a022d3add8c47a064f057f")throw new System.InvalidOperationException("Axes source identity changed");
    foreach(var file in ((Newtonsoft.Json.Linq.JObject)axesSource["files"]).Properties())if(axesHash(System.IO.Path.Combine(axesRepo,file.Name))!=(string)file.Value)throw new System.InvalidOperationException("Axes source file changed: "+file.Name);
};
verifyAxesInputs();
if(!UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Requires Play Mode");
if(UnityEngine.Object.FindObjectsByType<Picklebot.PlayerLearning.PlayerMlDrillsV3>(UnityEngine.FindObjectsInactive.Include,UnityEngine.FindObjectsSortMode.None).Length!=0)throw new System.InvalidOperationException("Expected empty scene");
string model="ExecutionV1AxesRecoveryFinal01", condition="B";
string expectedModelHash="c6b0b76dad004c7f8ef6155a460bcc6ae0c49958b595ad8f8ab0825166c8fa25", expectedCheckpointHash="c6915987421940f0e2cb9ca18d3b1902fc89efba5efce97c37f3d1c3b614287a";
string absoluteModelPath="F:/dev/picklebot/Assets/Picklebot/PlayerLearning/Models/ExecutionV1AxesRecoveryFinal01.onnx";
System.Func<string> actualModelHash=()=>{using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(absoluteModelPath))).Replace("-","").ToLowerInvariant();};
if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model hash mismatch before evaluation");
int region=1;
string output="F:/dev/picklebot/artifacts/hierarchy-v1/axes-recovery-01/evaluation/narrow/"+model+"/"+condition;
var field=typeof(Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena).GetField("goals",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
var root=new UnityEngine.GameObject("Two-region evaluation");root.SetActive(false);
var first=new System.Collections.Generic.Dictionary<int,object>();
string result="";
try
{
    var run=root.AddComponent<Picklebot.PlayerLearning.PlayerMlDrillsV3>();
    var goals=root.AddComponent<Picklebot.PlayerLearning.PlayerExecutionDrillsV1>();
    run.AutoRun=false;run.RequireTrainer=false;run.Task="movement-maintenance";
    run.FirstSeed=1109593;run.SeedCount=256;run.ArenaCount=8;run.MaximumReturnDifficulty=.25f;
    run.FixedServeSides="both";run.MovementRange=.025f;run.MovementPattern="lateral";run.MovementRehearsalRange=.1f;
    run.MovementRecoveryMix=true;run.InterleavedRecovery=true;run.AlignDrillDecisions=false;
    run.InferenceModel=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/"+model+".onnx");
    if(run.InferenceModel==null)throw new System.InvalidOperationException("Missing model");
    run.EvidenceDirectory=output;run.SourceIdentity="557040f9cec6f4825aa263e192de05d98388962b98a022d3add8c47a064f057f";
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
    System.IO.File.WriteAllText(output+"/first-decisions.json",Newtonsoft.Json.JsonConvert.SerializeObject(first));
    if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model changed during evaluation");
    System.IO.File.WriteAllText(output+"/model-identity.json",Newtonsoft.Json.JsonConvert.SerializeObject(new{model,modelHash=expectedModelHash,checkpointHash=expectedCheckpointHash,step=2097159,sourceIdentity="557040f9cec6f4825aa263e192de05d98388962b98a022d3add8c47a064f057f"}));
    verifyAxesInputs();
    result=Newtonsoft.Json.JsonConvert.SerializeObject(new{model,condition,episodes=goals.Completed,legal=goals.LegalLandings,targets=goals.TargetsHit});
    System.IO.File.WriteAllText(output+"/summary.json",result);
}
finally
{
    UnityEngine.Object.DestroyImmediate(root);
    if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();
}
return result;
