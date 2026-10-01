string progressRepo=@"F:/dev/picklebot";
System.Func<string,string> progressHash=path=>{using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();};
System.Action verifyProgressInputs=()=>{
    if(progressHash(@"F:/dev/picklebot/artifacts/hierarchy-v1/movement-progress-01/plan.json")!="c4c705180cb80ce5ad1d294c232cfcfcb2fced67851afd8ba8cb8c06cc4446c0")throw new System.InvalidOperationException("Frozen movement-progress plan changed");
    if(progressHash(@"F:/dev/picklebot/training/snapshots/execution-v1-movement-progress-final-01.pt")!="4414ab97ddf51b530c2f7fa3aa9d0c55664d2569cd963db890ee335435d79dce")throw new System.InvalidOperationException("Selected checkpoint changed");
    if(progressHash(@"F:/dev/picklebot/artifacts/hierarchy-v1/movement-progress-01/source-records.json")!="265d8cad8d0ab3918f4a6051b6efa15eff606cf9541f5f59f179bca0c2a2ac22")throw new System.InvalidOperationException("Frozen source manifest changed");
    var progressSource=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(@"F:/dev/picklebot/artifacts/hierarchy-v1/movement-progress-01/source-records.json"));
    if((string)progressSource["sourceIdentity"]!="cf513a204b81fbdafc2464f2509a8a66ddd8b22f9ee6d7a64e8486b930126978")throw new System.InvalidOperationException("Movement-progress source identity changed");
    foreach(var file in ((Newtonsoft.Json.Linq.JObject)progressSource["files"]).Properties())if(progressHash(System.IO.Path.Combine(progressRepo,file.Name))!=(string)file.Value)throw new System.InvalidOperationException("Movement-progress source file changed: "+file.Name);
};
verifyProgressInputs();
var fixtureCheck=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText("F:/dev/picklebot/artifacts/hierarchy-v1/wide-movement-fixture-01/fixture-summary.json"));
if((bool?)fixtureCheck["outcomeAllowed"]!=true || (int?)fixtureCheck["seedCount"]!=512)throw new System.InvalidOperationException("Wide reset fixture must pass before policy evaluation");
if(!UnityEditor.EditorApplication.isPlaying)throw new System.InvalidOperationException("Requires Play Mode");
if(UnityEngine.Object.FindObjectsByType<Picklebot.PlayerLearning.PlayerMlDrillsV3>(UnityEngine.FindObjectsInactive.Include,UnityEngine.FindObjectsSortMode.None).Length!=0)throw new System.InvalidOperationException("Expected empty scene");
string model="ExecutionV1MovementProgressFinal01", condition="A";
string expectedModelHash="90ba3ef7bcd17f5c07e505fcc11e4f6098ce3490e1b7981bea85d30962962bb2", expectedCheckpointHash="4414ab97ddf51b530c2f7fa3aa9d0c55664d2569cd963db890ee335435d79dce";
string absoluteModelPath="F:/dev/picklebot/Assets/Picklebot/PlayerLearning/Models/ExecutionV1MovementProgressFinal01.onnx";
System.Func<string> actualModelHash=()=>{using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(absoluteModelPath))).Replace("-","").ToLowerInvariant();};
if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model hash mismatch before evaluation");
int region=0;
string output="F:/dev/picklebot/artifacts/hierarchy-v1/movement-progress-trace-01/evaluation/"+model+"/"+condition;
var field=typeof(Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena).GetField("goals",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
if(System.IO.Directory.Exists(output))throw new System.InvalidOperationException("Preserve existing evaluation directory");
var root=new UnityEngine.GameObject("Two-region evaluation");root.SetActive(false);
var first=new System.Collections.Generic.Dictionary<int,object>();
string result="";
var trace=new System.Collections.Generic.List<object>();
var tracedSeeds=new System.Collections.Generic.HashSet<int>{1109945,1109881,1109899,1109964,1109963};
float[] V(UnityEngine.Vector3 v)=>new[]{v.x,v.y,v.z};
float[] Q(UnityEngine.Quaternion q)=>new[]{q.x,q.y,q.z,q.w};

try
{
    var run=root.AddComponent<Picklebot.PlayerLearning.PlayerMlDrillsV3>();
    var goals=root.AddComponent<Picklebot.PlayerLearning.PlayerExecutionDrillsV1>();
    run.AutoRun=false;run.RequireTrainer=false;run.Task="movement-maintenance";
    run.MovementForwardProgressReward=false;
    run.FirstSeed=1109849;run.SeedCount=512;run.ArenaCount=8;run.MaximumReturnDifficulty=.25f;
    run.FixedServeSides="both";run.MovementRange=.25f;run.MovementPattern="axes";run.MovementRehearsalRange=0;
    run.MovementRecoveryMix=false;run.InterleavedRecovery=false;run.AlignDrillDecisions=false;
    run.InferenceModel=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>("Assets/Picklebot/PlayerLearning/Models/"+model+".onnx");
    if(run.InferenceModel==null)throw new System.InvalidOperationException("Missing model");
    run.EvidenceDirectory=output;run.SourceIdentity="cf513a204b81fbdafc2464f2509a8a66ddd8b22f9ee6d7a64e8486b930126978";
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
        if(run.MovementForwardProgressReward||run.Report.movementForwardProgressReward)throw new System.InvalidOperationException("Forward-progress reward must remain disabled in evaluation");
        foreach(var rewardArena in run.ActiveArenas)
            if(rewardArena.Drill.MovementForwardProgressRewardEnabled||rewardArena.Drill.MovementForwardProgressReward!=0f||rewardArena.Drill.MovementForwardProgressRewardedSteps!=0)
                throw new System.InvalidOperationException("Evaluation drill accumulated disabled forward-progress reward");
        foreach(var tracedArena in run.ActiveArenas)
        {
            if(tracedArena.Finished||!tracedSeeds.Contains(tracedArena.Drill.Seed))continue;
            var d=tracedArena.Drill;var m=d.Match;var body=m.World.Players[d.Player];var upper=m.Controls.UpperFor(d.Player);
            trace.Add(new{seed=d.Seed,tick=m.Tick,time=m.World.Time,player=d.Player,
                ball=V(m.World.Ball.position),ballVelocity=V(m.World.Ball.linearVelocity),
                root=V(body.Position),velocity=V(body.Velocity),shoulder=V(body.Shoulder),hand=V(body.Hand),
                paddle=V(body.Paddle.position),paddleRotation=Q(body.Paddle.rotation),paddleVelocity=V(body.PaddleVelocity),paddleAngularVelocity=V(body.AngularVelocity),
                torso=V(upper.TorsoAngles),arm=upper.ArmAngles.ToArray(),armRates=upper.ArmRates,
                command=tracedArena.Agents[d.Player].LastCommand.ToArray(),
                faceContact=d.FaceContact,netCrossed=d.NetCrossed,phase=m.World.Rules.Phase.ToString(),fault=m.World.Rules.LastFault.ToString(),
                parts=body.Root.GetComponentsInChildren<UnityEngine.Transform>().Select(t=>new{name=t.name,position=V(t.position),rotation=Q(t.rotation)}).ToArray()});
        }
        run.StepOneTick();
    }
    if(run.Report.status!="seed_budget_complete"||goals.Completed!=512||first.Count!=512)throw new System.InvalidOperationException("Incomplete evaluation");
        if(run.MovementForwardProgressReward||run.Report.movementForwardProgressReward)throw new System.InvalidOperationException("Forward-progress reward must remain disabled in evaluation");
        foreach(var rewardArena in run.ActiveArenas)
            if(rewardArena.Drill.MovementForwardProgressRewardEnabled||rewardArena.Drill.MovementForwardProgressReward!=0f||rewardArena.Drill.MovementForwardProgressRewardedSteps!=0)
                throw new System.InvalidOperationException("Evaluation drill accumulated disabled forward-progress reward");
    System.IO.File.WriteAllText(output+"/first-decisions.json",Newtonsoft.Json.JsonConvert.SerializeObject(first));
    if(actualModelHash()!=expectedModelHash)throw new System.InvalidOperationException("Selected model changed during evaluation");
    System.IO.File.WriteAllText(output+"/model-identity.json",Newtonsoft.Json.JsonConvert.SerializeObject(new{model,modelHash=expectedModelHash,checkpointHash=expectedCheckpointHash,step=2097183,sourceIdentity="cf513a204b81fbdafc2464f2509a8a66ddd8b22f9ee6d7a64e8486b930126978"}));
    System.IO.File.WriteAllText(output+"/trace.json",Newtonsoft.Json.JsonConvert.SerializeObject(trace));
    verifyProgressInputs();
    result=Newtonsoft.Json.JsonConvert.SerializeObject(new{model,condition,episodes=goals.Completed,legal=goals.LegalLandings,targets=goals.TargetsHit});
    System.IO.File.WriteAllText(output+"/summary.json",result);
}
finally
{
    UnityEngine.Object.DestroyImmediate(root);
    if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();
}
return result;
