using System;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using Unity.InferenceEngine;
using UnityEngine;

namespace Picklebot.PlayerLearning
{
    [DefaultExecutionOrder(-10000)]
    public sealed class PlayerHeadlessBootstrapV3:MonoBehaviour
    {
        public string BuiltSourceIdentity, BuiltModelHash;
        public ModelAsset EvaluationModel;
        // Keep the dynamically looked-up court shader in standalone build dependencies.
        public Shader RuntimeCourtShader;
        private PlayerMlDrillsV3 run;
        private PlayerMlTeamsV3 teamRun;
        private string RunStatus=>teamRun!=null?teamRun.Report?.status:run!=null?run.Report?.status:null;
        private string RunFailure=>teamRun!=null?teamRun.Report?.failure:run!=null?run.Report?.failure:null;
        private PlayerWorkerPlanV3 plan;
        private bool claimed,finished;
        private readonly Stopwatch clock=new();
        [Serializable] private sealed class WorkerRecord
        {
            public string version="player-worker-startup-v1",status,manifestPath,manifestHash,sourceIdentity,expectedBuildIdentity,modelHash,evidenceDirectory,unityVersion,error;
            public int workerId,firstSeed,seedCount,arenas,processId;
            public bool trainerRequired;
            public double elapsedSeconds;
        }
        private WorkerRecord record;
        [Serializable] private sealed class RuntimeRecord
        {
            public string status="ready",platform,graphicsDevice,simulationMode;
            public float fixedDeltaTime,timeScale,contactOffset,bounceThreshold;
            public int solverIterations,solverVelocityIterations,processorCount;
            public Vector3 gravity;
        }
        private static void CreateJson(string path,object value)
        {
            using(var stream=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read))
            using(var writer=new StreamWriter(stream))writer.Write(JsonUtility.ToJson(value,true));
        }
        private void Start()
        {
            try
            {
                var args=Environment.GetCommandLineArgs();
                string path=PlayerWorkerPlanV3.Argument(args,"--picklebot-manifest",true);
                if(!Path.IsPathFullyQualified(path))throw new ArgumentException("Absolute manifest path required.");
                byte[] bytes=File.ReadAllBytes(path);
                var manifest=JsonUtility.FromJson<PlayerWorkerManifestV3>(System.Text.Encoding.UTF8.GetString(bytes));
                plan=PlayerWorkerPlanV3.Create(manifest,PlayerWorkerPlanV3.WorkerFromArguments(manifest,args));
                if(manifest.sourceIdentity!=BuiltSourceIdentity)throw new InvalidOperationException("Manifest does not match this build's source identity.");
                if(!string.IsNullOrEmpty(manifest.backgroundModelHash)&&(manifest.backgroundModelHash!=BuiltModelHash||EvaluationModel==null))throw new InvalidOperationException("Frozen practice model does not match embedded build model.");
                if(!plan.RequireTrainer&&(manifest.modelHash!=BuiltModelHash||EvaluationModel==null))throw new InvalidOperationException("Manifest does not match the embedded evaluation model.");
                if(FindObjectsByType<PlayerMlDrillsV3>(FindObjectsInactive.Include,FindObjectsSortMode.None).Length!=0||FindObjectsByType<PlayerMlTeamsV3>(FindObjectsInactive.Include,FindObjectsSortMode.None).Length!=0)throw new InvalidOperationException("Bootstrap requires an otherwise empty learning scene.");
                Directory.CreateDirectory(plan.EvidenceDirectory);
                using var hash=SHA256.Create();
                record=new WorkerRecord{status="configured",manifestPath=Path.GetFullPath(path),manifestHash=BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant(),sourceIdentity=BuiltSourceIdentity,expectedBuildIdentity=manifest.buildIdentity,modelHash=plan.RequireTrainer?null:BuiltModelHash,evidenceDirectory=plan.EvidenceDirectory,unityVersion=Application.unityVersion,workerId=plan.WorkerId,firstSeed=plan.FirstSeed,seedCount=plan.SeedCount,arenas=manifest.arenasPerWorker,processId=Process.GetCurrentProcess().Id,trainerRequired=plan.RequireTrainer};
                // Atomic claim prevents worker restarts or duplicate IDs from overwriting evidence.
                CreateJson(Path.Combine(plan.EvidenceDirectory,"worker-startup.json"),record);claimed=true;
                clock.Start();Application.runInBackground=true;
                var root=new GameObject("Worker "+plan.WorkerId+(plan.IsTeamMatch?" four-player matches":" independent-player drills"));root.SetActive(false);
                if(plan.IsTeamMatch)
                {
                    teamRun=root.AddComponent<PlayerMlTeamsV3>();plan.Configure(teamRun,EvaluationModel);
                    root.SetActive(true);teamRun.InitializeRun();
                }
                else
                {
                    run=root.AddComponent<PlayerMlDrillsV3>();plan.Configure(run,EvaluationModel);
                    root.SetActive(true);run.InitializeRun();
                }
                CreateJson(Path.Combine(plan.EvidenceDirectory,"worker-ready.json"),new RuntimeRecord{
                    platform=Application.platform.ToString(),graphicsDevice=SystemInfo.graphicsDeviceType.ToString(),simulationMode=Physics.simulationMode.ToString(),
                    fixedDeltaTime=Time.fixedDeltaTime,timeScale=Time.timeScale,contactOffset=Physics.defaultContactOffset,bounceThreshold=Physics.bounceThreshold,
                    solverIterations=Physics.defaultSolverIterations,solverVelocityIterations=Physics.defaultSolverVelocityIterations,processorCount=Environment.ProcessorCount,gravity=Physics.gravity});
            }
            catch(Exception error){Fail(error);}
        }
        private void LateUpdate()
        {
            if(finished||RunStatus==null)return;
            if(RunStatus=="failed"){Fail(new InvalidOperationException(RunFailure));return;}
            if(RunStatus=="seed_budget_complete")
            {
                record.status="seed_budget_complete";record.elapsedSeconds=clock.Elapsed.TotalSeconds;
                CreateJson(Path.Combine(plan.EvidenceDirectory,"worker-finish.json"),record);finished=true;
                // Training allocations must outlast the trainer budget; an exhausted
                // worker is an explicit failure, never a silent duplicated restart.
                Quit(plan.RequireTrainer?3:0);
            }
        }
        private void Fail(Exception error)
        {
            if(run!=null)
            {
                run.AutoRun=false;run.enabled=false;
                if(run.Report!=null){run.Report.status="failed";run.Report.failure=error.ToString();}
            }
            if(teamRun!=null)
            {
                teamRun.AutoRun=false;teamRun.enabled=false;
                if(teamRun.Report!=null){teamRun.Report.status="failed";teamRun.Report.failure=error.ToString();}
            }
            finished=true;UnityEngine.Debug.LogException(error);
            if(claimed)
            {
                record.status="failed";record.error=error.ToString();record.elapsedSeconds=clock.Elapsed.TotalSeconds;
                CreateJson(Path.Combine(plan.EvidenceDirectory,"worker-failure.json"),record);
            }
            Quit(2);
        }
        private void OnApplicationQuit()
        {
            if(!claimed||finished)return;
            record.status="application_quit";record.elapsedSeconds=clock.Elapsed.TotalSeconds;
            CreateJson(Path.Combine(plan.EvidenceDirectory,"worker-quit.json"),record);
        }
        private static void Quit(int code)
        {
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying=false;
#else
            Application.Quit(code);
#endif
        }
    }
}
