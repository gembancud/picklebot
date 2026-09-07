using System;
using UnityEngine;

namespace Picklebot.Rally
{
    [Serializable] public sealed class RallyDenseLayer
    {
        public int inputs, outputs;
        public float[] weights, bias;
    }

    [Serializable] public sealed class RallyWeights
    {
        public string version;
        public int seed;
        public float[] mean, scale;
        public RallyDenseLayer[] layers;
    }

    // Direct CPU inference of exported PyTorch weights. No analytical controller
    // or trajectory predictor is used in the deployed policy.
    public sealed class RallyNeuralPolicy
    {
        private readonly RallyWeights model;
        public RallyNeuralPolicy(TextAsset asset)
        {
            if (asset == null) throw new ArgumentNullException(nameof(asset), "Assign trained rally weights.");
            model = JsonUtility.FromJson<RallyWeights>(asset.text);
            if (model.version != "rally-policy-v1" || model.mean.Length != 6 || model.layers.Length != 3)
                throw new ArgumentException("Unsupported rally policy.");
            int width = 6;
            foreach (var layer in model.layers)
            {
                if (layer.inputs != width || layer.weights.Length != layer.inputs * layer.outputs || layer.bias.Length != layer.outputs)
                    throw new ArgumentException("Invalid dense layer shape.");
                width = layer.outputs;
            }
            if (width != 4) throw new ArgumentException("Expected four paddle commands.");
        }

        public float[] Decide(Vector3 position, Vector3 velocity, int side)
        {
            // Rotate the far player's frame 180 degrees around the up axis.
            float mirror = -side;
            var values = new[] { position.x * mirror, position.y, position.z * mirror,
                velocity.x * mirror, velocity.y, velocity.z * mirror };
            for (int i = 0; i < values.Length; i++) values[i] = (values[i] - model.mean[i]) / model.scale[i];
            for (int l = 0; l < model.layers.Length; l++)
            {
                var layer = model.layers[l];
                var output = new float[layer.outputs];
                for (int j = 0; j < layer.outputs; j++)
                {
                    float sum = layer.bias[j];
                    for (int i = 0; i < layer.inputs; i++) sum += values[i] * layer.weights[j * layer.inputs + i];
                    output[j] = l == model.layers.Length - 1 ? sum : (float)Math.Tanh(sum);
                }
                values = output;
            }
            foreach (float value in values)
                if (float.IsNaN(value) || float.IsInfinity(value)) throw new InvalidOperationException("Non-finite neural action.");
            return values;
        }
    }
}
