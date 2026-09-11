using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Picklebot.Doubles;
using UnityEditor;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration.Editor
{
    // Interactive mechanics diagnostic. No learned weights or final seeds used.
    public static class PlayerServeSweepV2
    {
        private sealed class Ready:IPlayerPolicyV2
        {public string Name=>"serve diagnostic hold";public void Reset(){}public PlayerActionV2 Decide(PlayerObservationV2 o,System.Random r)=>default;}
        [Serializable] public sealed class Trial
        {public float offset,pitch,speed,timing,lateral,depth;public int steps,score,fault;public string failure;public List<DoublesContact> contacts;}
        [Serializable] public sealed class Report
        {public string sourceHash;public int seed=1300000;public List<Trial> trials=new List<Trial>();}
        private static PlayerGameV2 game;
        private static Report report;
        private static Trial current;
        private static string path;
        private static float bodyOffset,landingDepth;
        private static float[] offsets,pitches,speeds,timings;
        public static bool Running=>report!=null;
        public static string Status{get;private set;}="idle";
        public static void Start(string output,float[] contactOffsets=null,float[] pitchValues=null,float[] speedValues=null,float[] timingValues=null,float lateralOffset=.4f,float targetDepth=4.2f)
        {
            if(Running||PlayerGameProbeV2.Running||!EditorApplication.isPlaying||EditorApplication.isCompiling||EditorUtility.scriptCompilationFailed)throw new InvalidOperationException("Idle compiled play mode required.");
            if(File.Exists(output))throw new InvalidOperationException("Evidence already exists.");
            if(!float.IsFinite(lateralOffset)||lateralOffset<.3f||lateralOffset>.7f||!float.IsFinite(targetDepth)||targetDepth<3||targetDepth>8)throw new ArgumentException("Bounded serve clearance/depth required.");
            bodyOffset=lateralOffset;landingDepth=targetDepth;
            timings=(float[])(timingValues??new[]{0f}).Clone();
            offsets=(float[])(contactOffsets??new[]{.0635f,.1435f,.1835f}).Clone();
            pitches=(float[])(pitchValues??new[]{-4f,0f,4f}).Clone();speeds=(float[])(speedValues??new[]{1f,1.25f}).Clone();
            if(offsets.Length*pitches.Length*speeds.Length*timings.Length<1||offsets.Length*pitches.Length*speeds.Length*timings.Length>100||
                timings.Any(v=>!float.IsFinite(v)||Mathf.Abs(v)>.05f)||offsets.Any(v=>!float.IsFinite(v)||v<0||v>.35f)||pitches.Any(v=>!float.IsFinite(v)||Mathf.Abs(v)>20)||speeds.Any(v=>!float.IsFinite(v)||v<.5f||v>1.5f))throw new ArgumentException("Bounded serve trial grid required.");
            path=output;report=new Report{sourceHash=PlayerControlSource.SourceHash()};Status="running";EditorApplication.update+=Tick;
        }
        private static void Tick()
        {
            if(game==null)
            {
                int n=report.trials.Count;
                if(n==offsets.Length*pitches.Length*speeds.Length*timings.Length){Finish();return;}
                current=new Trial{lateral=bodyOffset,depth=landingDepth,offset=offsets[n/(pitches.Length*speeds.Length*timings.Length)],pitch=pitches[n/(speeds.Length*timings.Length)%pitches.Length],speed=speeds[n/timings.Length%speeds.Length],timing=timings[n%timings.Length]};
                game=new PlayerGameV2(false,Enumerable.Range(0,4).Select(i=>(IPlayerPolicyV2)new Ready()).ToArray(),1300000);
                var flags=BindingFlags.Instance|BindingFlags.NonPublic;
                var stroke=(StrokeController)typeof(PlayerServeSkillV2).GetField("stroke",flags).GetValue(game.Serve);
                stroke.TimingBias=current.timing;stroke.PitchBias=current.pitch;stroke.SpeedScale=current.speed;
                typeof(PlayerServeSkillV2).GetField("faceUpOffset",flags).SetValue(game.Serve,current.offset);
                typeof(PlayerServeSkillV2).GetField("lateralOffset",flags).SetValue(game.Serve,current.lateral);
                typeof(PlayerServeSkillV2).GetField("targetDepth",flags).SetValue(game.Serve,current.depth);
            }
            try{for(int i=0;i<120&&game.PhysicsSteps<1800&&game.Rallies.Count==0;i++)game.Step();}
            catch(Exception e){current.failure=e.ToString();}
            if(current.failure==null&&game.PhysicsSteps<1800&&game.Rallies.Count==0)return;
            current.steps=game.PhysicsSteps;current.score=game.Match.World.Rules.Score[0];
            current.fault=game.Rallies.Count>0?(int)game.Rallies[0].fault:(int)game.Match.World.Rules.LastFault;
            current.contacts=game.Rallies.Count>0?game.Rallies[0].contacts:new List<DoublesContact>(game.Match.World.Contacts);
            report.trials.Add(current);game.Dispose();game=null;Status="running "+report.trials.Count+"/"+(offsets.Length*pitches.Length*speeds.Length*timings.Length);
        }
        private static void Finish()
        {
            EditorApplication.update-=Tick;
            try{if(PlayerControlSource.SourceHash()!=report.sourceHash)throw new InvalidOperationException("Source changed during sweep.");Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllText(path,JsonUtility.ToJson(report,true));Status="complete: "+path;}
            finally{report=null;}
        }
    }
}
