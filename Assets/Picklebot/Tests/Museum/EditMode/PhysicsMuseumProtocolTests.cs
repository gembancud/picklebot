using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Museum;
using UnityEngine;

namespace Picklebot.Tests.Museum.EditMode
{
    public sealed class PhysicsMuseumProtocolTests
    {
        private SimulationConfigV1 configuration;

        [SetUp]
        public void SetUp()
        {
            configuration = ScriptableObject.CreateInstance<SimulationConfigV1>();
        }

        [TearDown]
        public void TearDown()
        {
            UnityEngine.Object.DestroyImmediate(configuration);
        }

        [Test]
        public void ProtocolExposesExactlySixCompleteUniqueStations()
        {
            Assert.DoesNotThrow(PhysicsMuseumProtocolV1.ValidateOrThrow);
            Assert.That(
                PhysicsMuseumProtocolV1.Stations.Count,
                Is.EqualTo(PhysicsMuseumProtocolV1.StationCount));
            Assert.That(
                PhysicsMuseumProtocolV1.Stations.Select(value => value.Id).Distinct().Count(),
                Is.EqualTo(PhysicsMuseumProtocolV1.StationCount));
            Assert.That(
                PhysicsMuseumProtocolV1.Stations.Select(value => value.Station),
                Is.EquivalentTo(Enum.GetValues(typeof(PhysicsMuseumStationV1))));
            Assert.That(
                PhysicsMuseumProtocolV1.Stations.Count(value => value.AllowsManualPaddle),
                Is.EqualTo(2));
        }

        [Test]
        public void EveryVariantCreatesAUniqueFiniteEnvV1Request()
        {
            var seeds = new HashSet<ulong>();
            foreach (var definition in PhysicsMuseumProtocolV1.Stations)
            {
                for (var variant = 0; variant < definition.VariantCount; variant++)
                {
                    var request = PhysicsMuseumProtocolV1.CreateRequest(
                        definition.Station,
                        variant);

                    Assert.That(seeds.Add(request.Seed), Is.True);
                    Assert.That(request.ScenarioId, Is.Not.Empty);
                    Assert.That(request.Overrides, Is.Not.Empty);
                    Assert.That(
                        request.Overrides.All(value =>
                            !string.IsNullOrWhiteSpace(value.Key) &&
                            FiniteMath.IsFinite(value.Value)),
                        Is.True);
                    Assert.That(
                        Override(request, "maximum_episode_seconds"),
                        Is.EqualTo(6f));
                }
            }
        }

        [Test]
        public void SpinComparisonChangesOnlyXSpinAcrossVariants()
        {
            var zero = PhysicsMuseumProtocolV1.CreateRequest(
                PhysicsMuseumStationV1.SpinFlight,
                0);
            var top = PhysicsMuseumProtocolV1.CreateRequest(
                PhysicsMuseumStationV1.SpinFlight,
                1);
            var back = PhysicsMuseumProtocolV1.CreateRequest(
                PhysicsMuseumStationV1.SpinFlight,
                2);

            Assert.That(Override(zero, "ball.angular_velocity.x"), Is.Zero);
            Assert.That(
                Override(top, "ball.angular_velocity.x"),
                Is.EqualTo(PhysicsMuseumProtocolV1.SpinComparisonMagnitude));
            Assert.That(
                Override(back, "ball.angular_velocity.x"),
                Is.EqualTo(-PhysicsMuseumProtocolV1.SpinComparisonMagnitude));

            var ignoredKeys = new HashSet<string>
            {
                "ball.angular_velocity.x"
            };
            Assert.That(
                CanonicalOverrides(zero, ignoredKeys),
                Is.EqualTo(CanonicalOverrides(top, ignoredKeys)));
            Assert.That(
                CanonicalOverrides(zero, ignoredKeys),
                Is.EqualTo(CanonicalOverrides(back, ignoredKeys)));
        }

        [Test]
        public void ManualPointerAndKeyboardMappingIsFiniteBoundedAndDirectional()
        {
            var paddlePosition = new Vector3(0f, 1f, 0f);
            var right = PhysicsMuseumProtocolV1.ManualAction(
                paddlePosition,
                Quaternion.identity,
                new Vector2(1f, 0.5f),
                true,
                0f,
                Vector3.zero,
                configuration);
            var left = PhysicsMuseumProtocolV1.ManualAction(
                paddlePosition,
                Quaternion.identity,
                new Vector2(0f, 0.5f),
                true,
                0f,
                Vector3.zero,
                configuration);
            var keys = PhysicsMuseumProtocolV1.ManualAction(
                paddlePosition,
                Quaternion.identity,
                Vector2.zero,
                false,
                1f,
                new Vector3(2f, -2f, 0.5f),
                configuration);

            Assert.That(right.LinearVelocityLocal.x, Is.GreaterThan(0f));
            Assert.That(left.LinearVelocityLocal.x, Is.LessThan(0f));
            Assert.That(keys.LinearVelocityLocal.z, Is.EqualTo(1f));
            Assert.That(
                keys.AngularVelocityLocal,
                Is.EqualTo(new Vector3(1f, -1f, 0.5f)));
            AssertUnitCube(right);
            AssertUnitCube(left);
            AssertUnitCube(keys);
        }

        private static float Override(ResetRequestV0 request, string key)
        {
            return request.Overrides.Single(value => value.Key == key).Value;
        }

        private static string CanonicalOverrides(
            ResetRequestV0 request,
            ISet<string> ignoredKeys)
        {
            return string.Join(
                "|",
                request.Overrides
                    .Where(value => !ignoredKeys.Contains(value.Key))
                    .OrderBy(value => value.Key, StringComparer.Ordinal)
                    .Select(value => $"{value.Key}={value.Value:R}"));
        }

        private static void AssertUnitCube(PaddleActionV0 action)
        {
            Assert.That(FiniteMath.IsFinite(action.LinearVelocityLocal), Is.True);
            Assert.That(FiniteMath.IsFinite(action.AngularVelocityLocal), Is.True);
            Assert.That(
                Mathf.Max(
                    Mathf.Abs(action.LinearVelocityLocal.x),
                    Mathf.Abs(action.LinearVelocityLocal.y),
                    Mathf.Abs(action.LinearVelocityLocal.z)),
                Is.LessThanOrEqualTo(1f));
            Assert.That(
                Mathf.Max(
                    Mathf.Abs(action.AngularVelocityLocal.x),
                    Mathf.Abs(action.AngularVelocityLocal.y),
                    Mathf.Abs(action.AngularVelocityLocal.z)),
                Is.LessThanOrEqualTo(1f));
        }
    }
}
