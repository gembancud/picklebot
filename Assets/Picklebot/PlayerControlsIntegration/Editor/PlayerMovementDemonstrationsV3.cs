using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Picklebot.PlayerControls;
using UnityEngine;
using UnityEditor;

namespace Picklebot.PlayerControlsIntegration.Editor
{
    // Offline demonstration fixture only. Never attached to a learned player or playable scene.
    public static class PlayerMovementDemonstrationsV3
    {
        [Serializable] public sealed class Row
        {
            public int seed, seat, observationTick, applyTick;
            public bool terminal;
            public float[] observation, physical;
        }
        [Serializable] public sealed class Episode
        {
            public int seed,seat,ticks,decisions;
            public float durationScale,amplitudeScale,maxSpeed,maxAcceleration,maxAngularSpeed;
            public string failure;
        }
        [Serializable] public sealed class Report
        {
            public string kind="Authored movement demonstrations through actual delayed player decisions; no learned policy, hits or biomechanical validation.";
            public string status="running",failure;
            public int firstSeed,matchCount,referenceSamples,movingSamples,physicsTicks;
            public List<Episode> episodes=new List<Episode>();
        }
        private sealed class Teacher:IPlayerPolicyV3
        {
            private readonly PlayerStrokePreviewV3.Sample[] path;
            public readonly float duration, amplitude;
            public int EndTick=>Mathf.CeilToInt(path.Length*duration/12)*12;
            public string Name=>"Offline authored movement reference";
            public Teacher(PlayerStrokePreviewV3.Sample[] path,int seed)
            {
                this.path=path;var random=new System.Random(seed);
                duration=3.5f+(float)random.NextDouble();amplitude=.9f+.15f*(float)random.NextDouble();
            }
            public void Reset(){}
            public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)
            {
                var sample=path[Mathf.Min(path.Length-1,(int)(observation.tick/duration))];
                var t=sample.torsoAngles*amplitude;var a=new float[18];a[6]=t.x/60;a[7]=t.y/(t.y>=0?35:15);a[8]=t.z/25;
                var ready=PlayerArmJointsV3.Ready;
                for(int j=0;j<7;j++){float delta=(sample.armAngles[j]-ready[j])*amplitude;a[9+j]=delta/(delta>=0?PlayerArmJointsV3.Maximum(j)-ready[j]:ready[j]-PlayerArmJointsV3.Minimum(j));}
                return new PlayerActionV3(a);
            }
        }
        public static string Generate(string directory,string referencePath,int firstSeed,int matchCount)
        {
            if(!EditorApplication.isPlaying)throw new InvalidOperationException("Play Mode required for isolated physics.");
            if(firstSeed<1000000||firstSeed+4*matchCount>1100000||matchCount<1)throw new ArgumentException("Training seed block required.");
            if(Directory.Exists(directory))throw new IOException("Preserve prior demonstrations; use a fresh directory.");
            Directory.CreateDirectory(directory);
            var reference=JsonUtility.FromJson<PlayerStrokePreviewV3.Report>(File.ReadAllText(referencePath));
            var moving=new List<PlayerStrokePreviewV3.Sample>();var previous=reference.samples[0];
            foreach(var s in reference.samples.Skip(1))
            {
                float change=Vector3.Distance(s.torsoAngles,previous.torsoAngles);
                for(int j=0;j<7;j++)change=Mathf.Max(change,Mathf.Abs(s.armAngles[j]-previous.armAngles[j]));
                if(change>1e-4f)moving.Add(s);
                previous=s;
            }
            if(moving.Count<2)throw new InvalidOperationException("No movement in reference.");
            var report=new Report{firstSeed=firstSeed,matchCount=matchCount,referenceSamples=reference.samples.Count,movingSamples=moving.Count};
            try
            {
                for(int index=0;index<matchCount;index++)
                using(var match=new PlayerLearningMatchV3(false,index%4))
                {
                    var teachers=Enumerable.Range(0,4).Select(seat=>new Teacher(moving.ToArray(),firstSeed+index*4+seat)).ToArray();
                    var episodes=Enumerable.Range(0,4).Select(seat=>new Episode{seed=firstSeed+index*4+seat,seat=seat,durationScale=teachers[seat].duration,amplitudeScale=teachers[seat].amplitude}).ToArray();
                    report.episodes.AddRange(episodes);
                    var writers=episodes.Select(e=>new StreamWriter(Path.Combine(directory,e.seed+".jsonl"),false)).ToArray();
                    var oldVelocity=new Vector3[4];
                    try
                    {
                        match.AttachPolicies(teachers.Cast<IPlayerPolicyV3>().ToArray(),firstSeed+index*4);
                        match.Decisions.Decided+=d=>
                        {
                            if(d.observationTick>=teachers[d.player].EndTick)return;
                            var e=episodes[d.player];e.decisions++;
                            writers[d.player].WriteLine(JsonUtility.ToJson(new Row{seed=e.seed,seat=e.seat,observationTick=d.observationTick,applyTick=d.applyTick,observation=d.observation.ToArray(),physical=d.action.ToArray()}));
                        };
                        int maxTicks=teachers.Max(t=>t.EndTick);
                        for(int tick=0;tick<maxTicks;tick++)
                        {
                            if(!match.StepAgents())throw new InvalidOperationException(match.Failure);
                            report.physicsTicks++;
                            for(int seat=0;seat<4;seat++)
                            {
                                var e=episodes[seat];var upper=match.Controls.UpperFor(seat);
                                if(tick<teachers[seat].EndTick)
                                {
                                    e.ticks++;e.maxSpeed=Mathf.Max(e.maxSpeed,upper.ActualVelocity.magnitude);
                                    e.maxAcceleration=Mathf.Max(e.maxAcceleration,(upper.ActualVelocity-oldVelocity[seat]).magnitude/PlayerJointMotorV3.Dt);
                                    e.maxAngularSpeed=Mathf.Max(e.maxAngularSpeed,upper.ActualAngularVelocity.magnitude);
                                    if(e.maxSpeed>12||e.maxAcceleration>100||e.maxAngularSpeed>11.99f)throw new InvalidOperationException("Physical limit exceeded.");
                                    if(tick+1==teachers[seat].EndTick)
                                        writers[seat].WriteLine(JsonUtility.ToJson(new Row{seed=e.seed,seat=seat,terminal=true,observationTick=tick+1,applyTick=-1,observation=PlayerObservationV3.Capture(match,seat,tick+1).ToArray(),physical=new float[18]}));
                                }
                                oldVelocity[seat]=upper.ActualVelocity;
                            }
                        }
                    }
                    catch(Exception error){foreach(var e in episodes)e.failure=error.ToString();throw;}
                    finally{foreach(var writer in writers)writer.Dispose();}
                }
                report.status="complete";
            }
            catch(Exception error){report.status="failed";report.failure=error.ToString();throw;}
            finally{File.WriteAllText(Path.Combine(directory,"report.json"),JsonUtility.ToJson(report,true));}
            return directory;
        }
    }
}
