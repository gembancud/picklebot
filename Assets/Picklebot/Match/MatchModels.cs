using System;
using UnityEngine;
namespace Picklebot.Match
{
    [Serializable] public sealed class MatchModels
    {
        public string version=PickleballMatch.Version,method="Independent softmax policies; terminal REINFORCE; scripted contact assistance";
        public string configurationHash,sourceHash,createdUtc;
        public int episodes,seed=860000;
        public ShotPolicy orange=new(),blue=new();
        public static MatchModels Load(string json)
        {
            var m=JsonUtility.FromJson<MatchModels>(json);
            if(m==null||m.version!=PickleballMatch.Version)throw new ArgumentException("Wrong match model version.");
            foreach(var p in new[]{m.orange,m.blue})
            {
                if(p==null||p.version!="pickleball-shot-policy-v1"||p.weights==null||p.weights.Length!=ShotPolicy.Inputs*ShotPolicy.Actions)throw new ArgumentException("Invalid shot policy.");
                foreach(float w in p.weights)if(!float.IsFinite(w))throw new ArgumentException("Invalid policy weight.");
            }
            return m;
        }
    }
}
