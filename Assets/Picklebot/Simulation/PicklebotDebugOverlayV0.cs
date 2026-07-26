using System.Text;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    [DisallowMultipleComponent]
    public sealed class PicklebotDebugOverlayV0 : MonoBehaviour
    {
        [SerializeField] private PicklebotEnvironmentV0 environment;
        [SerializeField] private bool drawOverlay = true;
        [SerializeField] private bool drawTrajectory = true;
        [SerializeField] private Color trajectoryColor = Color.yellow;
        [SerializeField] private Color contactColor = Color.red;

        private GUIStyle labelStyle;

        private void Awake()
        {
            if (environment == null)
            {
                environment = GetComponent<PicklebotEnvironmentV0>();
            }
        }

        private void OnGUI()
        {
            if (!drawOverlay || environment == null)
            {
                return;
            }

            labelStyle ??= new GUIStyle(GUI.skin.box)
            {
                alignment = TextAnchor.UpperLeft,
                fontSize = 13,
                normal = { textColor = Color.white }
            };

            var manifest = environment.CurrentManifest;
            var result = environment.LastStepResult;
            var text = new StringBuilder();
            text.AppendLine($"Picklebot {EnvironmentVersion.Current}");
            text.AppendLine($"state: {environment.State}");
            if (manifest != null)
            {
                text.AppendLine($"seed: {manifest.Seed}");
                text.AppendLine($"scenario: {manifest.ScenarioId}");
                text.AppendLine($"config: {manifest.ConfigurationHash}");
            }

            if (result != null)
            {
                text.AppendLine($"tick: {result.Observation.PhysicsTick}");
                text.AppendLine($"terminal: {result.TerminationReason}");
                text.AppendLine(
                    $"paddle linear cmd: {environment.PaddleCommandLinearVelocityWorld:F2}");
                text.AppendLine(
                    $"paddle angular cmd: {environment.PaddleCommandAngularVelocityWorld:F2}");
                text.AppendLine(
                    $"features: paddle={result.RewardFeatures.PaddleContactCount}, " +
                    $"net={result.RewardFeatures.NetContactCount}, " +
                    $"far={result.RewardFeatures.FarCourtLanding}, " +
                    $"near={result.RewardFeatures.NearCourtLanding}, " +
                    $"out={result.RewardFeatures.OutLanding}");
            }

            text.AppendLine("recent events:");
            foreach (var current in environment.RecentEvents)
            {
                text.AppendLine(
                    $"  {current.PhysicsTick}:{current.Sequence} {current.Kind} {current.Detail}");
            }

            GUI.Box(new Rect(12f, 12f, 470f, 330f), text.ToString(), labelStyle);
        }

        private void OnDrawGizmos()
        {
            if (environment == null)
            {
                return;
            }

            DrawCourtBounds();
            DrawPaddleAxes();

            if (drawTrajectory)
            {
                Gizmos.color = trajectoryColor;
                var points = environment.Trajectory;
                for (var index = 1; index < points.Count; index++)
                {
                    Gizmos.DrawLine(points[index - 1], points[index]);
                }
            }

            Gizmos.color = contactColor;
            foreach (var current in environment.RecentEvents)
            {
                if (current.Kind is EnvironmentEventKindV0.BallFloorContact or
                    EnvironmentEventKindV0.BallNetContact or
                    EnvironmentEventKindV0.BallPaddleContact)
                {
                    Gizmos.DrawSphere(current.Position, 0.04f);
                    Gizmos.DrawRay(current.Position, current.Normal * 0.25f);
                }
            }

            if (environment.Ball != null)
            {
                Gizmos.color = Color.cyan;
                Gizmos.DrawRay(
                    environment.Ball.position,
                    environment.Ball.linearVelocity * 0.1f);
            }
        }

        private static void DrawCourtBounds()
        {
            Gizmos.color = Color.white;
            var y = 0.012f;
            var nearLeft = new Vector3(-CourtGeometryV0.HalfWidth, y, -CourtGeometryV0.HalfLength);
            var nearRight = new Vector3(CourtGeometryV0.HalfWidth, y, -CourtGeometryV0.HalfLength);
            var farLeft = new Vector3(-CourtGeometryV0.HalfWidth, y, CourtGeometryV0.HalfLength);
            var farRight = new Vector3(CourtGeometryV0.HalfWidth, y, CourtGeometryV0.HalfLength);
            Gizmos.DrawLine(nearLeft, nearRight);
            Gizmos.DrawLine(nearRight, farRight);
            Gizmos.DrawLine(farRight, farLeft);
            Gizmos.DrawLine(farLeft, nearLeft);

            Gizmos.color = Color.green;
            Gizmos.DrawLine(
                new Vector3(-CourtGeometryV0.HalfWidth, y, -CourtGeometryV0.NonVolleyZoneDepth),
                new Vector3(CourtGeometryV0.HalfWidth, y, -CourtGeometryV0.NonVolleyZoneDepth));
            Gizmos.DrawLine(
                new Vector3(-CourtGeometryV0.HalfWidth, y, CourtGeometryV0.NonVolleyZoneDepth),
                new Vector3(CourtGeometryV0.HalfWidth, y, CourtGeometryV0.NonVolleyZoneDepth));
        }

        private void DrawPaddleAxes()
        {
            if (environment.Paddle == null)
            {
                return;
            }

            var paddleTransform = environment.Paddle.transform;
            Gizmos.color = Color.red;
            Gizmos.DrawRay(paddleTransform.position, paddleTransform.right * 0.4f);
            Gizmos.color = Color.green;
            Gizmos.DrawRay(paddleTransform.position, paddleTransform.up * 0.4f);
            Gizmos.color = Color.blue;
            Gizmos.DrawRay(paddleTransform.position, paddleTransform.forward * 0.4f);
            Gizmos.color = Color.magenta;
            Gizmos.DrawRay(
                paddleTransform.position,
                environment.PaddleCommandLinearVelocityWorld * 0.1f);
            Gizmos.color = Color.yellow;
            Gizmos.DrawRay(
                paddleTransform.position,
                environment.PaddleCommandAngularVelocityWorld * 0.03f);
        }
    }
}
