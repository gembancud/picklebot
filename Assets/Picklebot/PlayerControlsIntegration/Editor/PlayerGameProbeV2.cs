using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using Picklebot.PlayerAgents;
using Picklebot.Doubles;
using UnityEditor;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration.Editor
{
    public static class PlayerGameProbeV2
    {
        private sealed class Ready:IPlayerPolicyV2
        {public string Name=>"untrained ready hold probe";public void Reset(){}public PlayerActionV2 Decide(PlayerObservationV2 o,System.Random r)=>default;}
        [Serializable] public sealed class Report
        {
            public string sourceHash,status,failure,note,actorSha256,actorTrainingSourceHash,contactModelHash;
            public Picklebot.PlayerControls.PlayerPaddleFailure failedPaddle;
            public int steps,gameWinner,score0,score1,phase,assistedServeSteps,assistedResetSteps;
            public float time,impactAt,ballX,ballY,ballZ,paddleX,paddleY,paddleZ,shoulderY;
            public Vector3 root,shoulder,hand,face,forearm,plannedImpact;
            public Quaternion paddleRotation;
            public List<PlayerRallyResultV2> rallies;
            public List<DoublesContact> contacts;
        }
        private static PlayerGameV2 game;
        private static int limit;
        private static string output,source,actorHash,trainingSource,note,contactHash;
        public static bool Running=>game!=null;
        public static string Status {get;private set;}="idle";
        public static void Start(int maxSteps=24000,string path="artifacts/player-controls-v2/game-probe.json",string actorPath=null,string contactPath=null)
        {
            if(Running||!EditorApplication.isPlaying)throw new InvalidOperationException("Play mode and no active probe required.");
            if(EditorUtility.scriptCompilationFailed||EditorApplication.isCompiling)throw new InvalidOperationException("Current scripts must compile first.");
            if(maxSteps<1||maxSteps>240000)throw new ArgumentOutOfRangeException(nameof(maxSteps));
            if(File.Exists(path))throw new InvalidOperationException("Probe evidence already exists; choose a new path.");
            IPlayerPolicyV2[] policies;
            PlayerContactCalibrationV2 calibration=null;contactHash=null;
            if(contactPath!=null&&actorPath==null)throw new ArgumentException("Contact calibration requires checkpoint provenance.");
            actorHash=null;trainingSource=null;
            if(actorPath==null)
            {
                policies=Enumerable.Range(0,4).Select(i=>(IPlayerPolicyV2)new Ready()).ToArray();
                note="Deterministic untrained hold opponents and disclosed serve/reset; diagnostic only, not agent strength or final evaluation.";
            }
            else
            {
                var bytes=File.ReadAllBytes(actorPath);var model=PlayerActorModel.Load(System.Text.Encoding.UTF8.GetString(bytes));
                using(var sha=SHA256.Create())actorHash=BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();
                trainingSource=model.sourceHash;
                if(contactPath!=null){calibration=PlayerContactCalibrationV2.Load(File.ReadAllText(contactPath),model.contactModelHash);contactHash=calibration.Hash;}
                policies=Enumerable.Range(0,4).Select(i=>(IPlayerPolicyV2)new LegacyActorIntentPolicyV2(model)).ToArray();
                note="Four private fixed-inference V1 actors sharing weights; explicit 54-input projection, compatibility sprint and automatic crouch; neutral contact residuals; disclosed serve/reset. Interactive seed 1300000 only. Not V2 training or final acceptance.";
            }
            if(calibration!=null)note=note.Replace("neutral contact residuals","matching historical contact residuals");
            output=path;limit=maxSteps;source=PlayerControlSource.SourceHash();
            game=new PlayerGameV2(false,policies,1300000,calibration:calibration);
            Status="running";EditorApplication.update+=Tick;
        }
        private static void Tick()
        {
            string failure=null;
            try{for(int i=0;i<120&&!game.Complete&&game.PhysicsSteps<limit;i++)game.Step();}
            catch(Exception e){failure=e.ToString();}
            if(failure==null&&!game.Complete&&game.PhysicsSteps<limit)return;
            EditorApplication.update-=Tick;
            try
            {
                var w=game.Match.World;var body=w.Players[w.Rules.Server];
                var report=new Report{failedPaddle=game.Match.Controls.LastPaddleFailure,sourceHash=source,status=failure!=null?"failed":game.Complete?"complete":"step limit",failure=failure,
                    note=note,actorSha256=actorHash,actorTrainingSourceHash=trainingSource,contactModelHash=contactHash,
                    steps=game.PhysicsSteps,gameWinner=w.Rules.GameWinner,score0=w.Rules.Score[0],score1=w.Rules.Score[1],phase=(int)w.Rules.Phase,
                    time=w.Time,impactAt=game.Serve.PlannedImpactAt,ballX=w.Ball.position.x,ballY=w.Ball.position.y,ballZ=w.Ball.position.z,
                    paddleX=body.Paddle.position.x,paddleY=body.Paddle.position.y,paddleZ=body.Paddle.position.z,shoulderY=body.Shoulder.y,
                    root=body.Position,shoulder=body.Shoulder,hand=body.Hand,face=body.Paddle.transform.Find("RoundedHittingFace").position,
                    forearm=body.Root.transform.Find("Right forearm").position,plannedImpact=game.Serve.PlannedImpact,paddleRotation=body.Paddle.rotation,
                    rallies=game.Rallies,contacts=w.Contacts,assistedServeSteps=game.AssistedServeSteps,assistedResetSteps=game.AssistedResetSteps};
                if(PlayerControlSource.SourceHash()!=source)throw new InvalidOperationException("Source changed during probe.");
                Directory.CreateDirectory(Path.GetDirectoryName(output));File.WriteAllText(output,JsonUtility.ToJson(report,true));Status=report.status+": "+output;
            }
            finally {game.Dispose();game=null;}
        }
    }
}
