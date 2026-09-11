using System;
using Picklebot.PlayerAgents;
using Picklebot.PlayerControls;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // Shared immutable weights; each player owns its actor sample/state and RNG.
    public sealed class PlayerActorModelV3
    {
        [Serializable] private sealed class Payload
        {public string version,observationVersion,actionVersion,sourceHash;public ActorLayer[] layers;public float[] logStd;}
        private readonly ActorLayer[] layers;private readonly float[] logStd;
        public readonly string SourceHash;
        private PlayerActorModelV3(Payload p)
        {
            if(p==null||p.version!="player-actor-v3"||p.observationVersion!=PlayerObservationV3.Version||p.actionVersion!=PlayerActionV3.Version)
                throw new ArgumentException("V3 actor schema mismatch.");
            if(p.layers==null||p.layers.Length<2||p.layers.Length>4)throw new ArgumentException("Invalid layer count.");
            int width=PlayerObservationV3.Count;layers=new ActorLayer[p.layers.Length];
            for(int i=0;i<layers.Length;i++)
            {
                var l=p.layers[i];if(l==null||l.inputs!=width||l.outputs<1||l.outputs>256)throw new ArgumentException("Invalid actor shape.");
                Check(l.weights,l.inputs*l.outputs);Check(l.bias,l.outputs);
                layers[i]=new ActorLayer{inputs=l.inputs,outputs=l.outputs,weights=(float[])l.weights.Clone(),bias=(float[])l.bias.Clone()};width=l.outputs;
            }
            if(width!=PlayerActionV3.Count)throw new ArgumentException("V3 action mean count mismatch.");
            Check(p.logStd,PlayerActionV3.Count);if(Array.Exists(p.logStd,v=>v < -5||v>1))throw new ArgumentException("Invalid exploration scale.");
            logStd=(float[])p.logStd.Clone();SourceHash=p.sourceHash;
        }
        private static void Check(float[] x,int count)
        {if(x==null||x.Length!=count||Array.Exists(x,v=>!float.IsFinite(v)))throw new ArgumentException("Invalid actor tensor.");}
        public static PlayerActorModelV3 Load(string json)=>new PlayerActorModelV3(JsonUtility.FromJson<Payload>(json));
        public float LogStd(int i)=>logStd[i];
        public float[] Forward(float[] observation)
        {
            Check(observation,PlayerObservationV3.Count);var value=observation;
            for(int n=0;n<layers.Length;n++)
            {
                var l=layers[n];var next=new float[l.outputs];
                for(int o=0;o<l.outputs;o++)
                {float sum=l.bias[o];for(int i=0;i<l.inputs;i++)sum+=l.weights[o*l.inputs+i]*value[i];next[o]=n==layers.Length-1?sum:(float)Math.Tanh(sum);}
                Check(next,l.outputs);value=next;
            }
            return value;
        }
    }
    [Serializable] public sealed class PlayerSampleV3
    {public float[] raw,mean,action;public bool[] mask;public float logProbability;}
    public sealed class PlayerActorV3:IPlayerPolicyV3
    {
        private readonly PlayerActorModelV3 model;private readonly bool sampled;private readonly bool[] mask;
        public PlayerSampleV3 LastSample {get;private set;}
        public string Name=>"shared V3 body policy";
        public PlayerActorV3(PlayerActorModelV3 model,bool sampled,bool[] actionMask=null)
        {
            this.model=model??throw new ArgumentNullException(nameof(model));this.sampled=sampled;
            if(actionMask!=null&&actionMask.Length!=PlayerActionV3.Count)throw new ArgumentException("V3 action mask count mismatch.");
            mask=actionMask==null?new bool[PlayerActionV3.Count]:(bool[])actionMask.Clone();if(actionMask==null)for(int i=0;i<PlayerActionV3.Count;i++)mask[i]=true;
        }
        public void Reset()=>LastSample=null;
        public PlayerActionV3 Decide(PlayerObservationV3 observation,System.Random random)
        {
            var mean=model.Forward(observation.ToArray());var raw=new float[PlayerActionV3.Count];var action=new float[PlayerActionV3.Count];float logp=0;
            for(int i=0;i<PlayerActionV3.Count;i++)
            {
                raw[i]=mean[i];float sigma=Mathf.Exp(model.LogStd(i));
                if(sampled)raw[i]+=sigma*(float)(Math.Sqrt(-2*Math.Log(Math.Max(1e-12,random.NextDouble())))*Math.Cos(2*Math.PI*random.NextDouble()));
                float value=(float)Math.Tanh(raw[i]);if(i==3||i==4||i==5||i==16||i==17)value=(value+1)*.5f;
                action[i]=mask[i]?value:0;
                if(mask[i]){float z=(raw[i]-mean[i])/sigma;logp+=-.5f*z*z-model.LogStd(i)-.9189385332f;}
            }
            LastSample=new PlayerSampleV3{raw=raw,mean=mean,action=action,mask=(bool[])mask.Clone(),logProbability=logp};
            return new PlayerActionV3(action);
        }
    }
}
