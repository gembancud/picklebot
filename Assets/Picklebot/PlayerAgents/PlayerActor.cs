using System;
using UnityEngine;

namespace Picklebot.PlayerAgents
{
    [Serializable] public sealed class ActorLayer
    {
        public int inputs, outputs;
        public float[] weights, bias; // Row-major [output, input], as in PyTorch Linear.
    }

    [Serializable] public sealed class PlayerActorModel
    {
        public string version = "player-actor-v1", observationVersion = PlayerObservation.Version;
        public string sourceHash, configurationHash, contactModelHash, protocolHash, trainerHash, dataHash, createdUtc, method;
        public int trainingSteps;
        public ActorLayer[] layers;
        public float[] logStd = { -2f, -2f };

        public void Validate()
        {
            if (version != "player-actor-v1" || observationVersion != PlayerObservation.Version)
                throw new ArgumentException("Player actor schema mismatch.");
            if (layers == null || layers.Length < 2 || layers.Length > 4)
                throw new ArgumentException("Invalid actor layers.");
            int width = PlayerObservation.Count;
            foreach (var layer in layers)
            {
                if (layer == null || layer.inputs != width || layer.outputs < 1 || layer.outputs > 256)
                    throw new ArgumentException("Actor layer dimensions do not match.");
                Check(layer.weights, layer.inputs * layer.outputs); Check(layer.bias, layer.outputs); width = layer.outputs;
            }
            if (width != 12) throw new ArgumentException("Actor needs two movement means, one hit logit and nine shot logits.");
            Check(logStd, 2);
            if (Array.Exists(logStd, x => x < -5 || x > 1)) throw new ArgumentException("Invalid actor exploration scale.");
        }

        private static void Check(float[] values, int count)
        {
            if (values == null || values.Length != count || Array.Exists(values, v => !float.IsFinite(v)))
                throw new ArgumentException("Invalid actor tensor.");
        }

        public float[] Forward(float[] observation)
        {
            Check(observation, PlayerObservation.Count);
            var value = observation;
            for (int n = 0; n < layers.Length; n++)
            {
                var layer = layers[n]; var next = new float[layer.outputs];
                for (int output = 0; output < layer.outputs; output++)
                {
                    float sum = layer.bias[output];
                    for (int input = 0; input < layer.inputs; input++) sum += layer.weights[output * layer.inputs + input] * value[input];
                    next[output] = n == layers.Length - 1 ? sum : (float)Math.Tanh(sum);
                    if (!float.IsFinite(next[output])) throw new InvalidOperationException("Non-finite actor output.");
                }
                value = next;
            }
            return value;
        }

        public static PlayerActorModel Load(string json)
        {
            var model = JsonUtility.FromJson<PlayerActorModel>(json);
            if (model == null) throw new ArgumentException("Missing player actor.");
            model.Validate(); return model;
        }
    }

    [Serializable] public sealed class PlayerPolicySample
    {
        // PPO stores the sampled Gaussian variables before tanh/radial bounds.
        // These are training traces, not additional controls or observations.
        public float rawX, rawZ, logProbability;
        public PlayerAction action;
    }

    public interface ITracedPlayerPolicy : IPlayerPolicy
    { PlayerPolicySample LastSample { get; } }

    public sealed class PlayerActor : ITracedPlayerPolicy
    {
        public readonly PlayerActorModel Model;
        public readonly bool Sample;
        public string Name => "learned player actor / " + Model.method;
        public PlayerPolicySample LastSample { get; private set; }
        public PlayerActor(PlayerActorModel model, bool sample = false)
        { model.Validate(); Model = model; Sample = sample; }

        public PlayerAction Decide(PlayerObservation observation, System.Random random)
        {
            var output = Model.Forward(observation.values);
            float rawX = output[0], rawZ = output[1];
            if (Sample)
            { rawX += Mathf.Exp(Model.logStd[0]) * Normal(random); rawZ += Mathf.Exp(Model.logStd[1]) * Normal(random); }
            float probability = 1f / (1f + Mathf.Exp(-output[2]));
            bool attempt = Sample ? random.NextDouble() < probability : output[2] >= 0;
            int shot = 0; float max = output[3];
            for (int a = 1; a < 9; a++) if (output[3 + a] > max) { max = output[3 + a]; shot = a; }
            float total = 0; for (int a = 0; a < 9; a++) total += Mathf.Exp(output[3 + a] - max);
            if (Sample)
            {
                double draw = random.NextDouble() * total;
                for (int a = 0; a < 9; a++) { draw -= Mathf.Exp(output[3 + a] - max); if (draw <= 0) { shot = a; break; } }
            }
            var action = new PlayerAction { moveX = (float)Math.Tanh(rawX), moveZ = (float)Math.Tanh(rawZ), attempt = attempt, shot = shot }.Validated();
            float logProbability = GaussianLog(rawX, output[0], Model.logStd[0]) + GaussianLog(rawZ, output[1], Model.logStd[1])
                - Softplus(attempt ? -output[2] : output[2]) + output[3 + shot] - max - Mathf.Log(total);
            LastSample = new PlayerPolicySample { rawX = rawX, rawZ = rawZ, logProbability = logProbability, action = action };
            return action;
        }

        private static float Normal(System.Random rng) => (float)(Math.Sqrt(-2 * Math.Log(Math.Max(1e-12, rng.NextDouble()))) * Math.Cos(2 * Math.PI * rng.NextDouble()));
        private static float GaussianLog(float value, float mean, float logStd)
        { float z = (value - mean) / Mathf.Exp(logStd); return -.5f * z * z - logStd - .9189385332f; }
        private static float Softplus(float x) => Mathf.Max(x, 0) + (float)Math.Log(1 + Math.Exp(-Math.Abs(x)));
    }
}
