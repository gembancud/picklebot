// Unity CLI eval_file body. Generated destination; no project/source edits.
const string destination=@"C:/Users/Admin/Documents/Codex/2026-09-07/https-unity-com-blog-meet-the-7/outputs/right-acquisition-review-01/baseline";
void Require(bool ok,string message){if(!ok)throw new System.InvalidOperationException(message);}
string Hash(string path){using(var hash=System.Security.Cryptography.SHA256.Create())return System.BitConverter.ToString(hash.ComputeHash(System.IO.File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
float[] V(UnityEngine.Vector3 v)=>new[]{v.x,v.y,v.z};
float[] Q(UnityEngine.Quaternion q)=>new[]{q.x,q.y,q.z,q.w};
void WriteNew(string path,object value){using(var stream=new System.IO.FileStream(path,System.IO.FileMode.CreateNew,System.IO.FileAccess.Write))using(var writer=new System.IO.StreamWriter(stream))writer.Write(Newtonsoft.Json.JsonConvert.SerializeObject(value,Newtonsoft.Json.Formatting.Indented));}
bool Same(Newtonsoft.Json.Linq.JToken a,Newtonsoft.Json.Linq.JToken b)
{
    if(a==null||b==null)return a==null&&b==null;
    if(a is Newtonsoft.Json.Linq.JObject ao&&b is Newtonsoft.Json.Linq.JObject bo)
        return ao.Count==bo.Count&&ao.Properties().All(p=>bo.TryGetValue(p.Name,out var v)&&Same(p.Value,v));
    if(a is Newtonsoft.Json.Linq.JArray aa&&b is Newtonsoft.Json.Linq.JArray ba)
        return aa.Count==ba.Count&&aa.Select((v,i)=>Same(v,ba[i])).All(v=>v);
    bool an=a.Type==Newtonsoft.Json.Linq.JTokenType.Float||a.Type==Newtonsoft.Json.Linq.JTokenType.Integer;
    bool bn=b.Type==Newtonsoft.Json.Linq.JTokenType.Float||b.Type==Newtonsoft.Json.Linq.JTokenType.Integer;
    if(an&&bn){if(a.Type==Newtonsoft.Json.Linq.JTokenType.Integer&&b.Type==Newtonsoft.Json.Linq.JTokenType.Integer)return (long)a==(long)b;float x=(float)a,y=(float)b;return float.IsFinite(x)&&float.IsFinite(y)&&x==y;}
    return Newtonsoft.Json.Linq.JToken.DeepEquals(a,b);
}
System.Collections.Generic.Dictionary<int,Newtonsoft.Json.Linq.JObject> Rows(string path)=>System.IO.File.ReadAllLines(path).Where(s=>!string.IsNullOrWhiteSpace(s)).Select(Newtonsoft.Json.Linq.JObject.Parse).ToDictionary(row=>(int)row["seed"]);

Require(UnityEditor.EditorApplication.isPlaying,"Requires isolated Play Mode after the four wider evaluations");
Require(!UnityEditor.EditorApplication.isCompiling&&!UnityEditor.EditorApplication.isUpdating,"Editor still compiling/importing");
Require(UnityEngine.SystemInfo.graphicsDeviceType!=UnityEngine.Rendering.GraphicsDeviceType.Null,"JPEG capture requires a graphics device; preserve this attempt if rendering is unavailable");
Require(UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects().Length==0,"Active Play Mode scene must be empty");
Require(!Unity.MLAgents.Academy.IsInitialized,"Previous evaluation Academy still exists");
Require(UnityEngine.Object.FindObjectsByType<Picklebot.PlayerLearning.PlayerMlDrillsV3>(UnityEngine.FindObjectsInactive.Include,UnityEngine.FindObjectsSortMode.None).Length==0,"Another drill runner exists");
Require(!System.IO.File.Exists(System.IO.Path.Combine(destination,"started.json")),"Refusing duplicate capture");
string repo=System.IO.Path.GetFullPath(System.IO.Path.Combine(UnityEngine.Application.dataPath,".."));
string manifestPath=System.IO.Path.Combine(destination,"manifest.json");
var manifest=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(manifestPath));
string manifestHash=Hash(manifestPath),sourceIdentity=(string)manifest["sourceIdentity"];
Require((int)manifest["checkpoint"]==1048609&&(int)manifest["firstSeed"]==1109849&&(int)manifest["seedCount"]==512,"Unexpected selected model/reset interval");
Require((int)manifest["fullReplayEpisodes"]==512&&((Newtonsoft.Json.Linq.JArray)manifest["stages"]).Count==1&&(string)manifest["stages"][0]["condition"]=="A","Only condition A recording is supported");
Require(Hash(System.IO.Path.Combine(destination,"capture.cs"))==(string)manifest["captureScriptSha256"],"Generated capture script changed");
var source=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(destination,"source-records.json")));
Require((string)source["sourceIdentity"]==sourceIdentity&&sourceIdentity=="078092d28f4dde258c904e3a925a9a1fd555f3c55384d92f012b6cdeb8bb60c4","Source identity mismatch");
void VerifyInputs()
{
    Require(Hash(manifestPath)==manifestHash,"Recording manifest changed");
    foreach(var pair in ((Newtonsoft.Json.Linq.JObject)source["files"]).Properties())Require(Hash(System.IO.Path.Combine(repo,pair.Name))==(string)pair.Value,"Simulation source changed: "+pair.Name);
    foreach(var pair in ((Newtonsoft.Json.Linq.JObject)manifest["referenceInputSha256"]).Properties())Require(Hash(System.IO.Path.Combine(repo,pair.Name))==(string)pair.Value,"Audited reference changed: "+pair.Name);
    Require(Hash(System.IO.Path.Combine(repo,(string)manifest["model"]))==(string)manifest["modelHash"],"Frozen model changed");
    Require(Hash(System.IO.Path.Combine(repo,(string)manifest["checkpointPath"]))==(string)manifest["checkpointHash"],"Frozen checkpoint changed");
    string ledgerPath=System.IO.Path.Combine(repo,"artifacts/player-v3/seed-ledger.json");
    Require(Hash(ledgerPath)==(string)manifest["ledgerHash"],"Seed ledger changed");
    Require(((Newtonsoft.Json.Linq.JArray)Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(ledgerPath))["finalSeedsConsumed"]).Count==0,"Final seeds consumed");
}
VerifyInputs();
string reference=(string)manifest["stages"][0]["referenceDirectory"];
var referenceEpisodes=Rows(System.IO.Path.Combine(reference,"episodes.jsonl"));
var referenceGoals=Rows(System.IO.Path.Combine(reference,"execution-goals.jsonl"));
var referenceFirst=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(reference,"first-decisions.json")));
Require(referenceEpisodes.Count==512&&referenceGoals.Count==512&&referenceFirst.Count==512,"Incomplete audited reference");
var selected=new System.Collections.Generic.HashSet<int>(((Newtonsoft.Json.Linq.JArray)manifest["stages"][0]["clipSeeds"]).Select(s=>(int)s));
Require(selected.Count==(int)manifest["clipCount"]&&selected.Count>0&&selected.Count<=8&&selected.All(seed=>referenceEpisodes.ContainsKey(seed)),"Invalid systematic clip selection");
var model=UnityEditor.AssetDatabase.LoadAssetAtPath<Unity.InferenceEngine.ModelAsset>((string)manifest["model"]);
Require(model!=null,"Missing frozen inference model");
WriteNew(System.IO.Path.Combine(destination,"started.json"),new{manifestHash,sourceIdentity,modelHash=(string)manifest["modelHash"],condition="A",firstSeed=1109849,seedCount=512,graphicsDevice=UnityEngine.SystemInfo.graphicsDeviceType.ToString(),startedAt=System.DateTime.UtcNow.ToString("O")});

var frames=selected.ToDictionary(seed=>seed,seed=>new System.Collections.Generic.List<object>());
var first=new System.Collections.Generic.Dictionary<int,object>();
var assigned=new System.Collections.Generic.Dictionary<Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena,int>();
var field=typeof(Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena).GetField("goals",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
Require(field!=null,"Execution goal field is unavailable");
UnityEngine.GameObject owner=null,cameraGo=null,lightGo=null;
UnityEngine.Camera camera=null;
UnityEngine.RenderTexture rt=null;
UnityEngine.Texture2D texture=null;
Picklebot.PlayerLearning.PlayerMlDrillsV3 run=null;
Picklebot.PlayerLearning.PlayerExecutionDrillsV1 goals=null;
int schedulerTicks=0;
bool finished=false;
var wall=System.Diagnostics.Stopwatch.StartNew();
UnityEditor.EditorApplication.CallbackFunction pump=null;
System.Action cleanup=()=>{
    UnityEditor.EditorApplication.update-=pump;
    if(owner!=null)UnityEngine.Object.DestroyImmediate(owner);
    if(Unity.MLAgents.Academy.IsInitialized)Unity.MLAgents.Academy.Instance.Dispose();
    if(cameraGo!=null)UnityEngine.Object.DestroyImmediate(cameraGo);
    if(lightGo!=null)UnityEngine.Object.DestroyImmediate(lightGo);
    if(rt!=null)UnityEngine.Object.DestroyImmediate(rt);
    if(texture!=null)UnityEngine.Object.DestroyImmediate(texture);
};
void Capture(Picklebot.PlayerLearning.PlayerMlDrillsV3.Arena arena)
{
    var d=arena.Drill;var m=d.Match;var list=frames[d.Seed];
    string dir=System.IO.Path.Combine(destination,"clips","A-"+d.Seed);
    var targetRenderers=new System.Collections.Generic.HashSet<UnityEngine.Renderer>(m.World.Root.GetComponentsInChildren<UnityEngine.Renderer>());
    var renderers=run.ActiveArenas.Where(a=>!a.Finished).SelectMany(a=>a.Drill.Match.World.Root.GetComponentsInChildren<UnityEngine.Renderer>()).Distinct().ToArray();
    var enabled=renderers.Select(r=>r.enabled).ToArray();
    var previous=UnityEngine.RenderTexture.active;
    try
    {
        // Renderer visibility only: do not touch collider layers or synchronize
        // pending physics transforms while taking a diagnostic photograph.
        foreach(var renderer in renderers)renderer.enabled=targetRenderers.Contains(renderer);
        var focus=m.World.Players[d.Player].Position+new UnityEngine.Vector3(0,.9f,0);
        for(int view=0;view<2;view++)
        {
            camera.orthographicSize=view==0?9:2.8f;
            var target=view==0?UnityEngine.Vector3.zero:focus;
            cameraGo.transform.position=target+(view==0?new UnityEngine.Vector3(10,15,-18):new UnityEngine.Vector3(d.Player<2?4:-4,2,d.Player<2?-4:4));
            cameraGo.transform.LookAt(target);camera.Render();UnityEngine.RenderTexture.active=rt;
            texture.ReadPixels(new UnityEngine.Rect(0,0,800,600),0,0);texture.Apply();
            string imagePath=System.IO.Path.Combine(dir,"frame-"+list.Count.ToString("D4")+"-"+view+".jpg");
            using(var stream=new System.IO.FileStream(imagePath,System.IO.FileMode.CreateNew,System.IO.FileAccess.Write))
            {var bytes=texture.EncodeToJPG(82);stream.Write(bytes,0,bytes.Length);}
        }
    }
    finally
    {
        UnityEngine.RenderTexture.active=previous;
        for(int i=0;i<renderers.Length;i++)renderers[i].enabled=enabled[i];
    }
    var players=new System.Collections.Generic.List<object>();
    foreach(var body in m.World.Players)
    {
        var parts=body.Root.GetComponentsInChildren<UnityEngine.Transform>().Select(t=>new{name=t.name,position=V(t.position),rotation=Q(t.rotation),localScale=V(t.localScale)}).ToArray();
        players.Add(new{seat=body.Id,root=V(body.Position),velocity=V(body.Velocity),leftFoot=V(body.LeftFoot),rightFoot=V(body.RightFoot),shoulder=V(body.Shoulder),hand=V(body.Hand),paddlePosition=V(body.Paddle.position),paddleRotation=Q(body.Paddle.rotation),paddleVelocity=V(body.PaddleVelocity),paddleAngularVelocity=V(body.AngularVelocity),parts});
    }
    list.Add(new{tick=m.Tick,worldSeconds=m.World.Time,phase=m.World.Rules.Phase.ToString(),player=d.Player,hitter=d.Hitter,faceContact=d.FaceContact,netCrossed=d.NetCrossed,
        ball=V(m.World.Ball.position),ballRotation=Q(m.World.Ball.rotation),ballVelocity=V(m.World.Ball.linearVelocity),ballAngularVelocity=V(m.World.Ball.angularVelocity),players,
        server=m.World.Rules.Server,designatedReceiver=m.World.Rules.DesignatedReceiver,
        observation124=Picklebot.PlayerControlsIntegration.PlayerObservationV3.Capture(m,d.Player,0).ToArray(),condition="A"});
}
void Complete()
{
    Require(run.Report.status=="seed_budget_complete"&&run.Episodes.Count==512&&goals.Completed==512&&first.Count==512,"Incomplete replay");
    // The seed budget is complete: close only terminal evidence writers before
    // reading them. No more actions, physics ticks, rewards or runner steps occur.
    foreach(var holder in new object[]{run,goals})
    foreach(string name in new[]{"evidence","decisionEvidence"})
    {
        var writerField=holder.GetType().GetField(name,System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance);
        if(writerField?.GetValue(holder) is System.IO.StreamWriter writer)
        {writer.Dispose();writerField.SetValue(holder,null);}
    }
    string folder=System.IO.Path.Combine(destination,"evaluations","A");
    WriteNew(System.IO.Path.Combine(folder,"first-decisions.json"),first);
    var episodes=Rows(System.IO.Path.Combine(folder,"episodes.jsonl"));
    var goalRows=Rows(System.IO.Path.Combine(folder,"execution-goals.jsonl"));
    var actualFirst=Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"first-decisions.json")));
    var mismatches=new System.Collections.Generic.List<object>();
    for(int seed=1109849;seed<1110361;seed++)
    {
        bool ep=episodes.TryGetValue(seed,out var e)&&Same(referenceEpisodes[seed],e);
        bool goal=goalRows.TryGetValue(seed,out var g)&&Same(referenceGoals[seed],g);
        bool decision=Same(referenceFirst[seed.ToString()],actualFirst[seed.ToString()]);
        if(!ep||!goal||!decision)mismatches.Add(new{seed,physicalEpisode=ep,goalAndLanding=goal,firstObservationAndAction=decision});
    }
    Require(episodes.Count==512&&goalRows.Count==512,"Replay evidence count mismatch");
    bool matches=mismatches.Count==0;
    WriteNew(System.IO.Path.Combine(destination,"parity.json"),new{status=matches?"exact_float32_parity":"mismatch",episodes=512,condition="A",mismatches,
        definition="All episode fields including physical metrics/reward, all execution goal/landing fields, and first observations/actions; floating fields compared after float32 conversion, integers/strings/bools exact.",
        referenceEpisodeHash=Hash(System.IO.Path.Combine(reference,"episodes.jsonl")),replayEpisodeHash=Hash(System.IO.Path.Combine(folder,"episodes.jsonl")),
        referenceGoalHash=Hash(System.IO.Path.Combine(reference,"execution-goals.jsonl")),replayGoalHash=Hash(System.IO.Path.Combine(folder,"execution-goals.jsonl"))});
    foreach(int seed in selected)
    {
        Require(frames[seed].Count>=2,"No useful replay frames for "+seed);
        WriteNew(System.IO.Path.Combine(destination,"clips","A-"+seed,"recording.json"),new{stage="A",condition="A",episode=episodes[seed],goal=goalRows[seed],frames=frames[seed],matchesReference=matches,fps=20,
            modelHash=(string)manifest["modelHash"],sourceIdentity,manifestHash,checkpoint=1048609,
            frameMeaning="Actual poses and JPEGs sampled every12 physics ticks; terminal outcomes come from the completed attempt and may occur between image samples."});
    }
    VerifyInputs();
    Require(matches,"Recording parity mismatch; preserve all raw evidence and do not publish as a verified replay");
    WriteNew(System.IO.Path.Combine(folder,"model-identity.json"),new{model=(string)manifest["modelName"],modelHash=(string)manifest["modelHash"],checkpointHash=(string)manifest["checkpointHash"],step=1048609,sourceIdentity});
    WriteNew(System.IO.Path.Combine(folder,"summary.json"),new{model=(string)manifest["modelName"],condition="A",episodes=512,legal=goals.LegalLandings,targets=goals.TargetsHit});
    WriteNew(System.IO.Path.Combine(destination,"complete.json"),new{status="complete_verified_replay",condition="A",episodes=512,matchesReference=512,clips=selected.Count,
        frames=frames.Sum(pair=>pair.Value.Count),images=2*frames.Sum(pair=>pair.Value.Count),elapsedSeconds=wall.Elapsed.TotalSeconds,manifestHash,sourceIdentity,modelHash=(string)manifest["modelHash"],finalSeedsConsumed=false,masteryAccepted=false});
}
pump=()=>{
    if(finished)return;
    try
    {
        Require(UnityEditor.EditorApplication.isPlaying,"Play Mode ended during recording");
        Require(wall.Elapsed.TotalSeconds<2400,"Capture wall-time guard exceeded");
        if(run==null)
        {
            foreach(int seed in selected)System.IO.Directory.CreateDirectory(System.IO.Path.Combine(destination,"clips","A-"+seed));
            rt=new UnityEngine.RenderTexture(800,600,24);Require(rt.Create(),"Could not create recording render texture");
            texture=new UnityEngine.Texture2D(800,600,UnityEngine.TextureFormat.RGB24,false);
            cameraGo=new UnityEngine.GameObject("Wide review recording camera");camera=cameraGo.AddComponent<UnityEngine.Camera>();camera.enabled=false;camera.orthographic=true;camera.targetTexture=rt;
            camera.nearClipPlane=.01f;camera.farClipPlane=100;camera.clearFlags=UnityEngine.CameraClearFlags.SolidColor;camera.backgroundColor=new UnityEngine.Color(.055f,.08f,.09f);camera.cullingMask=~0;
            lightGo=new UnityEngine.GameObject("Wide review recording light");var light=lightGo.AddComponent<UnityEngine.Light>();light.type=UnityEngine.LightType.Directional;light.intensity=2;light.cullingMask=~0;lightGo.transform.rotation=UnityEngine.Quaternion.Euler(35,-30,0);
            owner=new UnityEngine.GameObject("Wide review replay A");owner.SetActive(false);
            run=owner.AddComponent<Picklebot.PlayerLearning.PlayerMlDrillsV3>();goals=owner.AddComponent<Picklebot.PlayerLearning.PlayerExecutionDrillsV1>();
            run.AutoRun=false;run.RequireTrainer=false;run.Task="right-return-acquisition";run.FirstSeed=1109849;run.SeedCount=512;run.ArenaCount=16;run.MaximumReturnDifficulty=0;
            run.FixedServeSides="both";run.MovementRange=.0625f;run.MovementPattern="lateral-right";run.PrecontactAlignmentReward=false;run.MovementForwardProgressReward=false;run.MovementRehearsalRange=0;run.MovementRecoveryMix=false;run.InterleavedRecovery=false;run.AlignDrillDecisions=false;
            run.MovementTiming=0;run.MovementStartVariation=0;run.MovementPositionReward=0;run.InferenceModel=model;run.EvidenceDirectory=System.IO.Path.Combine(destination,"evaluations","A");run.SourceIdentity=sourceIdentity;
            goals.RewardMode=Picklebot.PlayerLearning.PlayerExecutionDrillsV1.LinearReward;goals.SampleShotTargets=true;goals.TargetLayout="two-regions";goals.TargetRadius=1;goals.LegalTargetReward=.25f;
            owner.SetActive(true);run.InitializeRun();
            foreach(var arena in run.ActiveArenas)foreach(var agent in arena.Agents)
            {
                var captured=arena;
                agent.Received+=(current,actions)=>{if(current.ObservedTick==0&&!first.ContainsKey(captured.Drill.Seed))first[captured.Drill.Seed]=new{seed=captured.Drill.Seed,player=current.Seat,observation=current.LastPolicyObservation,physical=current.LastCommand.ToArray()};};
            }
        }
        var slice=System.Diagnostics.Stopwatch.StartNew();
        while(run.Report.status=="running"&&slice.ElapsedMilliseconds<12)
        {
            foreach(var arena in run.ActiveArenas)
            {
                if(arena.Finished)continue;var d=arena.Drill;
                if(!assigned.TryGetValue(arena,out int oldSeed)||oldSeed!=d.Seed)
                {
                    bool serve=Picklebot.PlayerControlsIntegration.PlayerContactDrillV3.IsServeTask(d.Task);int sign=d.Player<2?1:-1;
                    int serviceSign=serve?(int)UnityEngine.Mathf.Sign(d.Match.World.Rules.ServiceX(d.Match.World.Rules.DesignatedReceiver)*sign):0;
                    var values=(Picklebot.PlayerLearning.PlayerExecutionGoalV1[])field.GetValue(arena);
                    values[d.Player]=new Picklebot.PlayerLearning.PlayerExecutionGoalV1(d.Player,0,Picklebot.PlayerLearning.PlayerIntentV1.PlayBall,shotTarget:Picklebot.PlayerLearning.PlayerExecutionDrillsV1.RegionTarget(serve,serviceSign,0),shotRadius:1f);
                    assigned[arena]=d.Seed;
                }
                if(selected.Contains(d.Seed)&&d.Match.Tick%12==0)Capture(arena);
            }
            run.StepOneTick();Require(++schedulerTicks<=400000,"Replay tick guard exceeded");
        }
        if(run.Report.status!="running")
        {
            Complete();finished=true;cleanup();
        }
    }
    catch(System.Exception ex)
    {
        finished=true;
        try{WriteNew(System.IO.Path.Combine(destination,"error.json"),new{error=ex.ToString(),schedulerTicks,elapsedSeconds=wall.Elapsed.TotalSeconds,completedEpisodes=run==null?0:run.Episodes.Count,partialFrames=frames.ToDictionary(pair=>pair.Key,pair=>pair.Value.Count),manifestHash});}
        finally{cleanup();}
        UnityEngine.Debug.LogException(ex);
    }
};
UnityEditor.EditorApplication.update+=pump;
return "Registered bounded condition-A recording; completion requires complete.json and exact parity.json. No optimizer or ledger changes.";
