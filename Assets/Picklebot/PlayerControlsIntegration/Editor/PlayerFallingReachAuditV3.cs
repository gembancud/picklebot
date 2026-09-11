using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Picklebot.PlayerControls;
using Picklebot.PlayerAgents;
using UnityEditor;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration.Editor
{
    // Diagnostic search only. Never referenced by a training run or deployed policy.
    // Geometric targets are fixed before a trial; execution uses the normal 20 Hz
    // private policy interface, 6-tick latency, bounded body and real drop physics.
    public static class PlayerFallingReachAuditV3
    {
        private sealed class Fixed : IPlayerPolicyV3
        {
            public PlayerActionV3 command;
            public string Name=>"Isolated falling-reach fixture";
            public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)=>command;
        }
        [Serializable] public sealed class Candidate
        {public int seat,targetTick;public float crouch;public Vector3 localPoint,localNormal;}
        [Serializable] public sealed class Trial
        {
            public Candidate candidate;public float geometryPositionError,geometryNormalError,minFaceDistance=100;
            public int ticks,releaseTick,closestTick;public float[] command;public bool faceContact,dropBounced,serveAccepted;
            public string outcome,failure;public Vector3 ballAtClosest,faceAtClosest;
        }
        [Serializable] public sealed class Report
        {
            public string status="running",failure,sourceIdentity;
            public string note="Isolated fixed-command feasibility search; never training data or a deployed controller. A miss is not proof of unreachability. Static geometry is separate from timed physical contact.";
            public int completed,total;public List<Trial> trials=new();
        }
        private static string directory;private static Report report;private static List<Candidate> candidates;
        public static string Start(string path,string source)
        {
            if(!EditorApplication.isPlaying)throw new InvalidOperationException("Requires Play Mode in an empty diagnostic scene.");
            if(UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects().Length!=0)throw new InvalidOperationException("Requires an empty diagnostic scene; do not run alongside training.");
            if(report!=null&&report.status=="running")throw new InvalidOperationException("Audit already running.");
            if(Directory.Exists(path))throw new IOException("Preserve prior evidence.");
            Directory.CreateDirectory(path);directory=path;report=new Report{sourceIdentity=source};candidates=new List<Candidate>();
            var release=new float[18];release[16]=0;
            var flight=new List<(int tick,Vector3 point)>();
            using(var drill=new PlayerContactDrillV3(1302081,0,"falling-contact"))
            {
                drill.Match.AttachPolicies(new IPlayerPolicyV3[]{new Fixed{command=new PlayerActionV3(release)},new Fixed(),new Fixed(),new Fixed()},1302081);
                var origin=drill.Match.World.Players[0].Position;
                while(!drill.Done&&drill.Match.Tick<252)
                {
                    drill.Step();
                    if(drill.Match.Tick%12==0)flight.Add((drill.Match.Tick,drill.Match.World.Ball.position-origin));
                }
            }
            if(flight.Count<3)throw new InvalidOperationException("No free-fall targets.");
            var targets=flight.Where(p=>p.tick==24||p.tick==48||p.tick==72||p.tick==96).ToArray();
            foreach(float crouch in new[]{0f,.5f,1f})foreach(var target in targets)
            foreach(var normal in new[]{Vector3.forward,new Vector3(0,.6f,1).normalized,Vector3.up})
                candidates.Add(new Candidate{seat=0,crouch=crouch,targetTick=target.tick,localPoint=target.point,localNormal=normal});
            report.total=candidates.Count;Save();EditorApplication.update+=Advance;return "Started "+report.total+" bounded physical reach trials";
        }
        private static void Save()=>File.WriteAllText(Path.Combine(directory,"report.json"),JsonUtility.ToJson(report,true));
        private static void Advance()
        {
            if(!EditorApplication.isPlaying){report.status="interrupted";EditorApplication.update-=Advance;Save();return;}
            try
            {
                var candidate=candidates[report.completed];var trial=RunTrial(candidate,1302082+report.completed);
                report.trials.Add(trial);report.completed++;
                if(trial.failure!=null){report.status="failed";report.failure=trial.failure;EditorApplication.update-=Advance;}
                else if(report.completed==report.total){report.status="completed";EditorApplication.update-=Advance;}
                Save();
            }
            catch(Exception error){report.status="failed";report.failure=error.ToString();EditorApplication.update-=Advance;Save();}
        }
        public static Trial RunTrial(Candidate candidate,int seed)
        {
            var result=new Trial{candidate=candidate};
            using(var drill=new PlayerContactDrillV3(seed,candidate.seat,"falling-contact"))
            {
                var match=drill.Match;var positions=match.World.Players.Select(p=>p.Position).ToArray();
                var settled=new PlayerControlWorldV3(positions);var actions=new PlayerActionV3[4];var crouch=new float[18];crouch[3]=candidate.crouch;actions[candidate.seat]=new PlayerActionV3(crouch);
                for(int tick=0;tick<480;tick++)if(!settled.TryStep(actions))throw new InvalidOperationException("Static crouch preparation rejected.");
                var pelvis=settled.PoseFor(candidate.seat).Pelvis;
                var rotation=Quaternion.Euler(0,candidate.seat<2?0:180,0);
                var point=positions[candidate.seat]+PlayerObservation.ToWorld(candidate.localPoint,candidate.seat);
                var normal=PlayerObservation.ToWorld(candidate.localNormal,candidate.seat);
                var aim=PlayerStrokeAimV3.Solve(pelvis,rotation,Vector3.zero,PlayerArmJointsV3.Ready,point,normal);
                result.geometryPositionError=aim.positionError;result.geometryNormalError=aim.normalErrorDegrees;
                var command=new float[18];command[3]=candidate.crouch;command[16]=0;
                command[6]=aim.torso.x/60;command[7]=aim.torso.y/(aim.torso.y>=0?35:15);command[8]=aim.torso.z/25;
                for(int i=0;i<7;i++){float delta=aim.arm[i]-PlayerArmJointsV3.Ready[i];command[9+i]=delta/(delta>=0?PlayerArmJointsV3.Maximum(i)-PlayerArmJointsV3.Ready[i]:PlayerArmJointsV3.Ready[i]-PlayerArmJointsV3.Minimum(i));}
                result.command=command;var policies=Enumerable.Range(0,4).Select(i=>(IPlayerPolicyV3)new Fixed{command=i==candidate.seat?new PlayerActionV3(command):default}).ToArray();
                match.AttachPolicies(policies,seed);
                while(!drill.Done)
                {
                    drill.Step();
                    var paddle=match.World.Players[candidate.seat].Paddle;
                    var face=paddle.position+paddle.rotation*PlayerStrokeAimV3.FacePoint;
                    float distance=Vector3.Distance(face,match.World.Ball.position);
                    if(distance<result.minFaceDistance)
                    {result.minFaceDistance=distance;result.closestTick=match.Tick;result.ballAtClosest=match.World.Ball.position;result.faceAtClosest=face;}
                }
                result.ticks=match.Tick;result.releaseTick=drill.ReleaseTick;result.faceContact=drill.FaceContact;result.dropBounced=drill.DropBounced;result.serveAccepted=drill.ServeAccepted;result.outcome=drill.Outcome;result.failure=match.Failure;
                if(drill.Outcome=="infeasible"||drill.Outcome=="exception")result.failure=result.failure??drill.Outcome;
            }
            return result;
        }
    }
}
