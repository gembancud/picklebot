using System;
using System.IO;
using Picklebot.Doubles.Editor;
using UnityEngine;

namespace Picklebot.PlayerAgents.Editor
{
    [Serializable] public sealed class FloatRow { public float[] values; }
    [Serializable] public sealed class ParityInput { public FloatRow[] observations, expected; }
    [Serializable] public sealed class ParityReport
    {
        public string actorHash, sourceHash, inputHash;
        public int cases;
        public float maximumError;
        public bool passed;
    }
    public static class ActorChecks
    {
        public static string Parity(string actorPath, string inputPath)
        {
            var model = PlayerActorModel.Load(File.ReadAllText(actorPath));
            var input = JsonUtility.FromJson<ParityInput>(File.ReadAllText(inputPath));
            if (input?.observations == null || input.expected == null || input.observations.Length != input.expected.Length || input.observations.Length < 1)
                throw new ArgumentException("Missing parity cases.");
            var report = new ParityReport { actorHash = ContactTraining.Hash(File.ReadAllText(actorPath)), sourceHash = PlayerDiagnostics.SourceHash(),
                inputHash = ContactTraining.Hash(File.ReadAllText(inputPath)), cases = input.observations.Length };
            for (int i = 0; i < input.observations.Length; i++)
            {
                var result = model.Forward(input.observations[i].values);
                if (input.expected[i].values.Length != result.Length) throw new ArgumentException("Parity output dimensions differ.");
                for (int j = 0; j < result.Length; j++)
                {
                    if (!float.IsFinite(input.expected[i].values[j])) throw new ArgumentException("Non-finite parity target.");
                    report.maximumError = Mathf.Max(report.maximumError, Mathf.Abs(result[j] - input.expected[i].values[j]));
                }
            }
            report.passed = report.maximumError < .0001f;
            string path = Path.Combine(Path.GetDirectoryName(actorPath), "unity-parity.json");
            File.WriteAllText(path, JsonUtility.ToJson(report, true));
            if (!report.passed) throw new InvalidOperationException("Actor parity failed: " + path);
            return path;
        }
    }
}
