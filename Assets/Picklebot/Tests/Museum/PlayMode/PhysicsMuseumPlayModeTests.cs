using System.Collections;
using NUnit.Framework;
using Picklebot.Core;
using Picklebot.Museum;
using UnityEngine;
using UnityEngine.TestTools;

namespace Picklebot.Tests.Museum.PlayMode
{
    public sealed class PhysicsMuseumPlayModeTests
    {
        private GameObject root;
        private PhysicsMuseumControllerV1 controller;

        [SetUp]
        public void SetUp()
        {
            root = new GameObject("PhysicsMuseumTest");
            controller = root.AddComponent<PhysicsMuseumControllerV1>();
            controller.Initialize();
        }

        [TearDown]
        public void TearDown()
        {
            Object.DestroyImmediate(root);
        }

        [Test]
        public void EveryStationResetsTheRealEnvV1Simulation()
        {
            foreach (var definition in PhysicsMuseumProtocolV1.Stations)
            {
                controller.SelectStation(definition.Station);

                Assert.That(controller.IsInitialized, Is.True);
                Assert.That(controller.SelectedStation, Is.EqualTo(definition.Station));
                Assert.That(
                    controller.Environment.CurrentManifest.EnvironmentVersion,
                    Is.EqualTo(SimulationConfigV1.EnvironmentVersion));
                Assert.That(
                    controller.Environment.CurrentManifest.Seed,
                    Is.EqualTo(PhysicsMuseumProtocolV1.CreateRequest(
                        definition.Station).Seed));
                Assert.That(
                    FiniteMath.IsFinite(
                        controller.CurrentObservation.Ball.PositionWorld),
                    Is.True);
            }
        }

        [Test]
        public void PauseSpeedAndNetVariantControlsChangeOnlyMuseumState()
        {
            controller.SelectStation(PhysicsMuseumStationV1.NetInteraction);
            var configurationHash =
                controller.Environment.CurrentManifest.ConfigurationHash;
            var firstSeed = controller.Environment.CurrentManifest.Seed;

            controller.TogglePause();
            Assert.That(controller.IsPaused, Is.True);
            controller.TogglePause();
            Assert.That(controller.IsPaused, Is.False);

            var initialSpeed = controller.PlaybackSpeed;
            controller.CyclePlaybackSpeed();
            Assert.That(controller.PlaybackSpeed, Is.Not.EqualTo(initialSpeed));

            controller.CycleVariant();
            Assert.That(controller.SelectedVariant, Is.EqualTo(1));
            Assert.That(
                controller.Environment.CurrentManifest.Seed,
                Is.Not.EqualTo(firstSeed));
            Assert.That(
                controller.Environment.CurrentManifest.ConfigurationHash,
                Is.EqualTo(configurationHash));
        }

        [Test]
        public void ControllerCanReinitializeAfterRuntimeCleanupWithoutDomainReload()
        {
            controller.SendMessage(
                "OnDestroy",
                SendMessageOptions.DontRequireReceiver);

            Assert.That(controller.IsInitialized, Is.False);
            Assert.That(controller.Environment, Is.Null);

            controller.Initialize();

            Assert.That(controller.IsInitialized, Is.True);
            Assert.That(controller.Environment, Is.Not.Null);
            Assert.That(
                controller.Environment.CurrentManifest.EnvironmentVersion,
                Is.EqualTo(SimulationConfigV1.EnvironmentVersion));
        }

        [UnityTest]
        public IEnumerator AllSixStationsAdvanceWithoutInvalidNumericState()
        {
            foreach (var definition in PhysicsMuseumProtocolV1.Stations)
            {
                controller.SelectStation(definition.Station);
                controller.LaunchStation();
                for (var action = 0; action < 12 && controller.IsRunning; action++)
                {
                    controller.AdvanceForTest(PaddleActionV0.Zero);
                }

                Assert.That(
                    FiniteMath.IsFinite(
                        controller.CurrentObservation.Ball.PositionWorld),
                    Is.True,
                    definition.Id);
                Assert.That(
                    FiniteMath.IsFinite(
                        controller.CurrentObservation.Ball.LinearVelocityWorld),
                    Is.True,
                    definition.Id);
                yield return null;
            }
        }

        [UnityTest]
        public IEnumerator SpinStationCompletesAndRetainsThreeComparisonTraces()
        {
            controller.SelectStation(PhysicsMuseumStationV1.SpinFlight);
            controller.LaunchStation();

            var guard = 0;
            while (controller.IsRunning && guard++ < 1200)
            {
                controller.AdvanceForTest(PaddleActionV0.Zero);
                if (guard % 100 == 0)
                {
                    yield return null;
                }
            }

            Assert.That(controller.IsRunning, Is.False);
            Assert.That(guard, Is.LessThan(1200));
            Assert.That(controller.CompletedSpinTraces, Is.EqualTo(3));
            Assert.That(controller.ActiveTracePointCount, Is.GreaterThan(3));
        }

        [UnityTest]
        public IEnumerator DropAndCourtStationsContinueTheRealBallToReboundApex()
        {
            var stations = new[]
            {
                PhysicsMuseumStationV1.DropRebound,
                PhysicsMuseumStationV1.CourtBounce
            };

            foreach (var station in stations)
            {
                controller.SelectStation(station);
                controller.LaunchStation();

                var frameGuard = 0;
                var deadline = Time.realtimeSinceStartup + 10f;
                while (controller.IsRunning &&
                       Time.realtimeSinceStartup < deadline)
                {
                    frameGuard++;
                    yield return null;
                }

                Assert.That(controller.IsRunning, Is.False, station.ToString());
                Assert.That(frameGuard, Is.GreaterThan(3), station.ToString());
                Assert.That(
                    controller.HasMuseumPhysicsRebound,
                    Is.True,
                    station.ToString());
                Assert.That(
                    controller.MuseumPhysicsReboundInProgress,
                    Is.False,
                    station.ToString());
                Assert.That(
                    controller.MuseumPhysicsReboundCompleted,
                    Is.True,
                    station.ToString());
                Assert.That(
                    controller.MuseumPhysicsReboundPointCount,
                    Is.GreaterThan(3),
                    station.ToString());
                Assert.That(
                    controller.MuseumPhysicsReboundTicks,
                    Is.GreaterThan(3),
                    station.ToString());
                Assert.That(
                    controller.MuseumPhysicsReboundApexTopHeight,
                    Is.GreaterThan(
                        controller.CurrentObservation.Ball.PositionWorld.y +
                        (controller.Environment.Configuration.BallDiameter / 2f)),
                    station.ToString());
                Assert.That(
                    controller.Environment.State,
                    Is.EqualTo(EpisodeStateV0.Terminal),
                    station.ToString());
                Assert.That(
                    controller.CurrentObservation.Episode.BallFloorContacts,
                    Is.GreaterThan(0),
                    station.ToString());
                Assert.That(
                    controller.Environment.TerminationReason,
                    Is.Not.EqualTo(TerminationReasonV0.Timeout),
                    station.ToString());
                Assert.That(
                    controller.Environment.Ball.position,
                    Is.Not.EqualTo(controller.CurrentObservation.Ball.PositionWorld),
                    station.ToString());
                Assert.That(
                    controller.Environment.Ball.gameObject.activeInHierarchy,
                    Is.True,
                    station.ToString());
            }
        }
    }
}
