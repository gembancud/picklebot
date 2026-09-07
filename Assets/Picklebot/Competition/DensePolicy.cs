using System;
using Picklebot.Rally;
using UnityEngine;

namespace Picklebot.Competition
{
    public sealed class DensePolicy
    {
        private readonly RallyWeights model;
        public DensePolicy(string json, string version, int inputs, int outputs)
        {
            model = JsonUtility.FromJson<RallyWeights>(json);
            if (model.version != version || model.mean.Length != inputs || model.scale.Length != inputs)
                throw new ArgumentException("Incompatible competition model.");
            foreach (var s in model.scale) if (!(s > 0)) throw new ArgumentException("Invalid normalization.");
            int width=inputs;
            foreach(var layer in model.layers)
            {
                if(layer.inputs!=width || layer.weights.Length!=layer.inputs*layer.outputs || layer.bias.Length!=layer.outputs)
                    throw new ArgumentException("Invalid layer dimensions.");
                width=layer.outputs;
            }
            if(width!=outputs) throw new ArgumentException("Invalid action dimensions.");
        }
        public float[] Predict(float[] input)
        {
            if(input == null || input.Length != model.mean.Length) throw new ArgumentException("Invalid observation dimensions.");
            var values=(float[])input.Clone();
            for(int i=0;i<values.Length;i++) values[i]=(values[i]-model.mean[i])/model.scale[i];
            for(int l=0;l<model.layers.Length;l++)
            {
                var layer=model.layers[l];var next=new float[layer.outputs];
                for(int j=0;j<next.Length;j++)
                {
                    float s=layer.bias[j];
                    for(int i=0;i<values.Length;i++) s+=values[i]*layer.weights[j*layer.inputs+i];
                    next[j]=l==model.layers.Length-1?s:(float)Math.Tanh(s);
                    if(!float.IsFinite(next[j])) throw new InvalidOperationException("Invalid model output.");
                }
                values=next;
            }
            return values;
        }
    }
}
