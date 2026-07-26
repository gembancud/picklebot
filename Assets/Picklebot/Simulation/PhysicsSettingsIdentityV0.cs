using System.IO;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    public static class PhysicsSettingsIdentityV0
    {
        public static string CanonicalText()
        {
            var projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            var dynamicsPath = Path.Combine(
                projectRoot,
                "ProjectSettings",
                "DynamicsManager.asset");
            var timePath = Path.Combine(
                projectRoot,
                "ProjectSettings",
                "TimeManager.asset");
            if (File.Exists(dynamicsPath) && File.Exists(timePath))
            {
                return string.Join(
                    "\n--PICKLEBOT-PHYSICS-SETTINGS-V0--\n",
                    Normalize(File.ReadAllText(timePath)),
                    Normalize(File.ReadAllText(dynamicsPath)));
            }

            return string.Join(
                "|",
                StableHashV0.Float(Time.fixedDeltaTime),
                StableHashV0.Vector(Physics.gravity),
                Physics.defaultSolverIterations,
                Physics.defaultSolverVelocityIterations,
                StableHashV0.Float(Physics.defaultContactOffset),
                StableHashV0.Float(Physics.bounceThreshold),
                Physics.simulationMode);
        }

        public static string Hash()
        {
            return StableHashV0.Hex(CanonicalText());
        }

        private static string Normalize(string value)
        {
            return value.Replace("\r\n", "\n").Trim();
        }
    }
}
