using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TestTools;
using Picklebot.PlayerControls;
using Picklebot.PlayerControlsIntegration;

namespace Picklebot.PlayerLearning.Tests
{
    public sealed class PlayerMovementFlightRewardIntegrationV3Tests
    {
        private const int FixtureSeed = 1305400;
        private HashSet<SceneHandle> priorScenes;

        [SetUp]
        public void RememberExistingScenes()
        {
            Assert.IsFalse(Unity.MLAgents.Academy.IsInitialized,
                "These tests use local drill physics without an Academy or trainer.");
            priorScenes = new HashSet<SceneHandle>(Enumerable.Range(0, SceneManager.sceneCount)
                .Select(i => SceneManager.GetSceneAt(i).handle));
        }

        [UnityTearDown]
        public IEnumerator WaitForDisposedWorldScenes()
        {
            // Dispose requests async unloading. Only wait for our newly created
            // local worlds; never unload existing scenes or change global clocks.
            for (int frame = 0; frame < 120 && HasPendingScenes(); frame++)
                yield return null;
            Assert.IsFalse(HasPendingScenes(), "Disposed test worlds did not finish unloading.");
            Assert.IsFalse(Unity.MLAgents.Academy.IsInitialized);
        }

        private bool HasPendingScenes() => priorScenes != null && Enumerable.Range(0, SceneManager.sceneCount)
            .Select(i => SceneManager.GetSceneAt(i))
            .Any(scene => !priorScenes.Contains(scene.handle) && scene.isLoaded &&
                scene.name.StartsWith("Doubles-", StringComparison.Ordinal));

        private static PlayerWorkerManifestV3 Manifest(bool enabled) => new PlayerWorkerManifestV3
        {
            version = PlayerWorkerPlanV3.Version, mode = "training", task = "movement-maintenance",
            sourceIdentity = new string('a', 64), buildIdentity = new string('b', 64), modelHash = new string('c', 64),
            evidenceRoot = Path.Combine(Path.GetTempPath(), "picklebot-flight-reward-test-unused"),
            basePort = 5705, workerCount = 8, firstSeed = 1000000, seedsPerWorker = 256,
            arenasPerWorker = 16, ticksPerFrame = 48, maximumReturnDifficulty = .25f,
            fixedServeSides = "both", movementRecoveryMix = true, interleavedRecovery = true,
            movementRange = .0625f, movementRehearsalRange = .1f, movementPattern = "axes",
            movementForwardProgressReward = enabled
        };

        private static PlayerMlDrillsV3 Owner(GameObject holder, bool enabled)
        {
            holder.SetActive(false);
            var run = holder.AddComponent<PlayerMlDrillsV3>();
            Assert.IsFalse(run.MovementForwardProgressReward);
            PlayerWorkerPlanV3.Create(Manifest(enabled), 0).Configure(run, null);
            Assert.AreEqual(enabled, run.MovementForwardProgressReward);
            run.enabled = false;
            run.AutoRun = false;
            run.RequireTrainer = false;
            run.EvidenceDirectory = null;
            run.FirstSeed = FixtureSeed;
            return run;
        }

        [Test]
        public void EnabledRunAndManifestRejectUnsupportedTasksOrNonpositiveRanges()
        {
            foreach (string task in new[] { "stationary-serve", "receive-feed", "rally-air-feed",
                "paired-movement-maintenance", "fixed-team-match", "", null })
                Assert.Catch<ArgumentException>(() =>
                    PlayerMlDrillsV3.ValidateMovementForwardProgressReward(task, .0625f, true));
            foreach (float range in new[] { -1f, 0f, float.NaN, float.PositiveInfinity, float.NegativeInfinity })
            {
                Assert.Catch<ArgumentException>(() =>
                    PlayerMlDrillsV3.ValidateMovementForwardProgressReward("movement-maintenance", range, true));
                var manifest = Manifest(true);
                manifest.movementRecoveryMix = false;
                manifest.interleavedRecovery = false;
                manifest.movementRehearsalRange = 0;
                manifest.movementPattern = "court";
                manifest.movementRange = range;
                Assert.Catch<ArgumentException>(() => PlayerWorkerPlanV3.Create(manifest, 0));
            }
            Assert.DoesNotThrow(() =>
                PlayerMlDrillsV3.ValidateMovementForwardProgressReward("movement-maintenance", .0625f, true));
            Assert.DoesNotThrow(() =>
                PlayerMlDrillsV3.ValidateMovementForwardProgressReward("stationary-serve", 0, false));

            var invalidTask = Manifest(true);
            invalidTask.movementRecoveryMix = false;
            invalidTask.interleavedRecovery = false;
            invalidTask.movementRehearsalRange = 0;
            invalidTask.movementPattern = "court";
            invalidTask.task = "paired-movement-maintenance";
            Assert.Catch<ArgumentException>(() => PlayerWorkerPlanV3.Create(invalidTask, 0));
        }

        [Test]
        public void ConstructorRejectsUnsupportedEnabledRequestsBeforeCreatingPhysics()
        {
            int scenes = SceneManager.sceneCount;
            foreach (string task in new[] { "stationary-serve", "receive-feed", "receive-serve", "contact" })
                Assert.Catch<ArgumentException>(() =>
                {
                    using (var drill = new PlayerContactDrillV3(FixtureSeed, 0, task,
                        movementForwardProgressReward: true)) { }
                });
            foreach (float range in new[] { -1f, 0f, float.NaN, float.PositiveInfinity, float.NegativeInfinity })
                Assert.Catch<ArgumentException>(() =>
                {
                    using (var drill = new PlayerContactDrillV3(FixtureSeed, 0, "rally-air-feed", 0,
                        movementRange: range, movementForwardProgressReward: true)) { }
                });
            Assert.Catch<ArgumentException>(() =>
            {
                using (var drill = new PlayerContactDrillV3(FixtureSeed, 0, "rally-air-feed", 0,
                    cooperative: true, movementRange: .0625f, movementForwardProgressReward: true)) { }
            });
            Assert.AreEqual(scenes, SceneManager.sceneCount, "Invalid requests must fail before constructing a world.");
        }

        [UnityTest]
        public IEnumerator FullRecoveryCycleEnablesOnly128FocusEpisodesAndExplicitFalseDisablesAll()
        {
            var oldHolder = new GameObject("Inactive flight reward disabled");
            var newHolder = new GameObject("Inactive flight reward focus enabled");
            int familiar = 0, prior = 0, focus = 0, enabledCount = 0;
            try
            {
                var old = Owner(oldHolder, false);
                var enabled = Owner(newHolder, true);
                for (int i = 0; i < 256; i++)
                {
                    int index = enabled.AllocationIndexForOrdinal(i);
                    Assert.AreEqual(old.AllocationIndexForOrdinal(i), index);
                    var spec = PlayerRecoveryScheduleV3.For(index, .0625f, .1f, .25f, "axes");
                    if (spec.Group == "familiar") familiar++;
                    else if (spec.Group == "prior") prior++;
                    else { Assert.AreEqual("focus", spec.Group); focus++; }
                    using (var a = old.CreateDrillForEpisode(index, out var oldRejected))
                    using (var b = enabled.CreateDrillForEpisode(index, out var newRejected))
                    {
                        bool expected = spec.Group == "focus";
                        Assert.IsFalse(a.MovementForwardProgressRewardEnabled);
                        Assert.AreEqual(expected, b.MovementForwardProgressRewardEnabled);
                        if (b.MovementForwardProgressRewardEnabled) enabledCount++;
                        Assert.AreEqual(spec.Task, b.Task);
                        Assert.AreEqual(spec.Range, b.MovementRange);
                        Assert.AreEqual(spec.Pattern, b.MovementPattern);
                        CollectionAssert.AreEqual(oldRejected, newRejected);
                        Assert.AreEqual(0, a.Match.Tick);
                        Assert.AreEqual(0, b.Match.TotalTicks);
                        Assert.AreEqual(0, b.Match.World.Time);
                        Assert.IsNull(a.Match.Decisions);
                        Assert.IsNull(b.Match.Decisions);
                        Assert.AreEqual(0, a.MovementForwardProgressReward);
                        Assert.AreEqual(0, b.MovementForwardProgressReward);
                        Assert.AreEqual(0, a.MovementForwardProgressRewardedSteps);
                        Assert.AreEqual(0, b.MovementForwardProgressRewardedSteps);
                        SamePhysicalState(a, b);
                    }
                    // Limit pending PhysicsScene unloads during the reset-only cycle.
                    if ((i + 1) % 16 == 0)
                        yield return WaitForDisposedWorldScenes();
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(oldHolder);
                UnityEngine.Object.DestroyImmediate(newHolder);
            }
            Assert.AreEqual(64, familiar);
            Assert.AreEqual(64, prior);
            Assert.AreEqual(128, focus);
            Assert.AreEqual(128, enabledCount);
        }

        private sealed class FixedPolicy : IPlayerPolicyV3
        {
            private readonly PlayerActionV3 action;
            public string Name => "test-only-fixed-commands";
            public FixedPolicy(PlayerActionV3 action) { this.action = action; }
            public PlayerActionV3 Decide(PlayerObservationV3 observation, System.Random random) => action;
            public void Reset() { }
        }

        private static void AttachCommands(PlayerContactDrillV3 drill, bool move)
        {
            var values = new float[PlayerActionV3.Count];
            if (move) { values[0] = .2f; values[1] = .1f; }
            // Commands are fixed before the first tick and never inspect ball state.
            var learnerAction = new PlayerActionV3(values);
            drill.Match.AttachPolicies(Enumerable.Range(0, 4)
                .Select(seat => (IPlayerPolicyV3)new FixedPolicy(seat == drill.Player ? learnerAction : default))
                .ToArray(), FixtureSeed);
        }

        [TestCase("stationary-serve", -1f)]
        [TestCase("receive-feed", -1f)]
        [TestCase("rally-air-feed", 0f)]
        [TestCase("rally-bounce-feed", 0f)]
        public void DefaultAndExplicitFalsePreserveFamiliarPhysicsActionsAndEveryReward(string task, float range)
        {
            using (var omitted = new PlayerContactDrillV3(FixtureSeed, 0, task, 0, movementRange: range))
            using (var disabled = new PlayerContactDrillV3(FixtureSeed, 0, task, 0, movementRange: range,
                movementForwardProgressReward: false))
            {
                Assert.IsFalse(omitted.MovementForwardProgressRewardEnabled);
                Assert.IsFalse(disabled.MovementForwardProgressRewardEnabled);
                SamePhysicalState(omitted, disabled);
                AttachCommands(omitted, false);
                AttachCommands(disabled, false);
                for (int tick = 0; tick < 7201 && !omitted.Done; tick++)
                {
                    omitted.Step();
                    disabled.Step();
                    SamePhysicalState(omitted, disabled);
                    Assert.AreEqual(omitted.Reward, disabled.Reward);
                    Assert.AreEqual(0, omitted.MovementForwardProgressReward);
                    Assert.AreEqual(0, disabled.MovementForwardProgressRewardedSteps);
                }
                Assert.IsTrue(omitted.Done);
                Assert.IsNull(omitted.Match.Failure);
            }
        }

        [TestCase(0, "rally-air-feed", false)]
        [TestCase(1, "rally-air-feed", true)]
        [TestCase(2, "rally-air-feed", false)]
        [TestCase(3, "rally-air-feed", true)]
        [TestCase(0, "rally-bounce-feed", true)]
        [TestCase(1, "rally-bounce-feed", false)]
        [TestCase(2, "rally-bounce-feed", true)]
        [TestCase(3, "rally-bounce-feed", false)]
        public void EnabledFocusPreservesResetPhysicsAndActionsWithOnlyAccountedRewardDifference(int seat, string task, bool move)
        {
            using (var omitted = new PlayerContactDrillV3(FixtureSeed, seat, task, 0,
                movementRange: .0625f, movementPattern: "axes"))
            using (var disabled = new PlayerContactDrillV3(FixtureSeed, seat, task, 0,
                movementRange: .0625f, movementPattern: "axes", movementForwardProgressReward: false))
            using (var enabled = new PlayerContactDrillV3(FixtureSeed, seat, task, 0,
                movementRange: .0625f, movementPattern: "axes", movementForwardProgressReward: true))
            {
                Assert.IsTrue(enabled.MovementForwardProgressRewardEnabled);
                SamePhysicalState(omitted, disabled);
                SamePhysicalState(omitted, enabled);
                foreach (var drill in new[] { omitted, disabled, enabled }) AttachCommands(drill, move);
                float baseSum = 0, enabledSum = 0;
                int countedRewardSteps = 0;
                bool stopped = false;
                for (int tick = 0; tick < 7201 && !omitted.Done; tick++)
                {
                    float previousBonus = enabled.MovementForwardProgressReward;
                    bool previouslyContacted = enabled.FaceContact;
                    omitted.Step();
                    disabled.Step();
                    enabled.Step();
                    SamePhysicalState(omitted, disabled);
                    SamePhysicalState(omitted, enabled);
                    Assert.AreEqual(omitted.Reward, disabled.Reward);
                    Assert.AreEqual(0, omitted.MovementForwardProgressReward);
                    Assert.AreEqual(0, disabled.MovementForwardProgressRewardedSteps);

                    float delta = enabled.MovementForwardProgressReward - previousBonus;
                    bool landed = enabled.FaceContact && enabled.NetCrossed && enabled.Match.World.Rules.Events
                        .Any(e => e.kind == "bounce" && e.time > enabled.FaceContactTime && e.position.z * (seat < 2 ? 1 : -1) > 0);
                    stopped |= enabled.Match.World.Rules.Dead || enabled.Done || landed;
                    if (!previouslyContacted || stopped) Assert.AreEqual(0, delta);
                    Assert.GreaterOrEqual(delta, 0);
                    Assert.That(enabled.MovementForwardProgressReward, Is.InRange(0f, .25f));
                    if (delta > 0) countedRewardSteps++;
                    Assert.AreEqual(countedRewardSteps, enabled.MovementForwardProgressRewardedSteps);
                    Assert.AreEqual(omitted.Reward + delta, enabled.Reward, 1e-6);
                    baseSum += omitted.Reward;
                    enabledSum += enabled.Reward;
                }
                Assert.IsTrue(omitted.Done);
                Assert.IsNull(omitted.Match.Failure);
                Assert.AreEqual(enabled.MovementForwardProgressReward, enabledSum - baseSum, 1e-5);
                TestContext.WriteLine($"seat={seat} task={task} moved={move} contact={enabled.FaceContact} outcome={enabled.Outcome} bonus={enabled.MovementForwardProgressReward:R}");
                // Zero bonus is valid here. Positive reachability requires separate
                // real-contact evidence; accounting is exercised in helper tests.
            }
        }

        [TestCase(0)]
        [TestCase(2)]
        public void StagedDynamicBallCollisionExercisesActualContactAndNonzeroFlightAccounting(int seat)
        {
            // Diagnostic transition fixture: deliberately place the dynamic ball
            // near the ready paddle, then stage outgoing flight after real contact.
            // This is not a
            // natural reset, learned behavior, training example, or success score.
            // The world must produce the collision and accepted-contact state;
            // no contact/rule event, FaceContact flag, or reward is fabricated.
            using (var disabled = new PlayerContactDrillV3(FixtureSeed, seat, "rally-air-feed", 0,
                movementRange: .0625f, movementPattern: "axes", movementForwardProgressReward: false))
            using (var enabled = new PlayerContactDrillV3(FixtureSeed, seat, "rally-air-feed", 0,
                movementRange: .0625f, movementPattern: "axes", movementForwardProgressReward: true))
            {
                foreach (var drill in new[] { disabled, enabled })
                {
                    var paddle = drill.Match.World.Players[seat].Paddle;
                    var normal = paddle.rotation * Vector3.forward;
                    var ball = drill.Match.World.Ball;
                    ball.position = paddle.position + paddle.rotation * PlayerStrokeAimV3.FacePoint + normal * .06f;
                    ball.transform.position = ball.position;
                    ball.linearVelocity = -normal * 3;
                    ball.angularVelocity = Vector3.zero;
                    AttachCommands(drill, false);
                }
                SamePhysicalState(disabled, enabled);
                float baseSum = 0, shapedSum = 0;
                int paidSteps = 0;
                bool stagedOutgoing = false;
                for (int tick = 0; tick < 240 && !disabled.Done; tick++)
                {
                    float previous = enabled.MovementForwardProgressReward;
                    bool hadContact = enabled.FaceContact;
                    disabled.Step();
                    enabled.Step();
                    SamePhysicalState(disabled, enabled);
                    Assert.IsNull(enabled.Match.Failure);
                    float delta = enabled.MovementForwardProgressReward - previous;
                    if (!hadContact || enabled.Match.World.Rules.Dead || enabled.Done)
                        Assert.AreEqual(0, delta);
                    Assert.AreEqual(disabled.Reward + delta, enabled.Reward, 1e-6);
                    if (delta > 0) paidSteps++;
                    Assert.AreEqual(paidSteps, enabled.MovementForwardProgressRewardedSteps);
                    baseSum += disabled.Reward;
                    shapedSum += enabled.Reward;
                    if (!stagedOutgoing && enabled.FaceContact)
                    {
                        Assert.IsFalse(enabled.Done);
                        Assert.IsFalse(enabled.Match.World.Rules.Dead);
                        // Do not assume a passive rebound is forward. After the
                        // real accepted contact, stage the same outgoing state in
                        // both worlds. Subsequent steps use normal physics; this
                        // isolates reward wiring and is not reachability evidence.
                        foreach (var drill in new[] { disabled, enabled })
                        {
                            var ball = drill.Match.World.Ball;
                            var forward = Vector3.forward * (seat < 2 ? 1 : -1);
                            ball.position += forward * .2f + Vector3.up * .3f;
                            ball.transform.position = ball.position;
                            ball.linearVelocity = forward * 3;
                            ball.angularVelocity = Vector3.zero;
                        }
                        SamePhysicalState(disabled, enabled);
                        stagedOutgoing = true;
                    }
                }
                Assert.IsTrue(enabled.FaceContact, "Actual physics must accept the staged face contact.");
                Assert.IsTrue(stagedOutgoing);
                Assert.IsTrue(enabled.Match.World.Contacts.Any(c => c.player == seat && c.surface == "RoundedHittingFace"));
                Assert.Greater(enabled.MovementForwardProgressReward, 0,
                    "This diagnostic case must exercise the drill's positive reward path.");
                Assert.Greater(enabled.MovementForwardProgressRewardedSteps, 0);
                Assert.LessOrEqual(enabled.MovementForwardProgressReward, .25f);
                Assert.AreEqual(enabled.MovementForwardProgressReward, shapedSum - baseSum, 1e-5);
                TestContext.WriteLine($"STAGED diagnostic seat={seat} contact={enabled.FaceContact} bonus={enabled.MovementForwardProgressReward:R}; not natural-reset reachability evidence");
            }
        }

        private static void SamePhysicalState(PlayerContactDrillV3 a, PlayerContactDrillV3 b)
        {
            Assert.AreEqual(a.Match.Tick, b.Match.Tick);
            Assert.AreEqual(a.Match.TotalTicks, b.Match.TotalTicks);
            Assert.AreEqual(a.Match.World.Time, b.Match.World.Time);
            Assert.AreEqual(a.Match.Failure, b.Match.Failure);
            Assert.AreEqual(a.Done, b.Done);
            Assert.AreEqual(a.Outcome, b.Outcome);
            Assert.AreEqual(a.FaceContact, b.FaceContact);
            Assert.AreEqual(a.FaceContactTime, b.FaceContactTime);
            Assert.AreEqual(a.NetCrossed, b.NetCrossed);
            Assert.AreEqual(a.Match.World.Ball.position, b.Match.World.Ball.position);
            Assert.AreEqual(a.Match.World.Ball.linearVelocity, b.Match.World.Ball.linearVelocity);
            Assert.AreEqual(a.Match.World.Ball.angularVelocity, b.Match.World.Ball.angularVelocity);
            for (int seat = 0; seat < 4; seat++)
            {
                CollectionAssert.AreEqual(a.Match.ActiveFor(seat).ToArray(), b.Match.ActiveFor(seat).ToArray());
                CollectionAssert.AreEqual(PlayerObservationV3.Capture(a.Match, seat, a.Match.Tick).ToArray(),
                    PlayerObservationV3.Capture(b.Match, seat, b.Match.Tick).ToArray());
                Assert.AreEqual(a.Match.World.Players[seat].Position, b.Match.World.Players[seat].Position);
                Assert.AreEqual(a.Match.World.Players[seat].Paddle.position, b.Match.World.Players[seat].Paddle.position);
                Assert.AreEqual(a.Match.World.Players[seat].Paddle.rotation, b.Match.World.Players[seat].Paddle.rotation);
            }
            var ar = a.Match.World.Rules;
            var br = b.Match.World.Rules;
            Assert.AreEqual(ar.Phase, br.Phase);
            Assert.AreEqual(ar.Dead, br.Dead);
            Assert.AreEqual(ar.Winner, br.Winner);
            Assert.AreEqual(ar.LastFault, br.LastFault);
            Assert.AreEqual(ar.Events.Count, br.Events.Count);
            for (int i = 0; i < ar.Events.Count; i++)
            {
                var x = ar.Events[i];
                var y = br.Events[i];
                Assert.AreEqual(x.kind, y.kind);
                Assert.AreEqual(x.time, y.time);
                Assert.AreEqual(x.player, y.player);
                Assert.AreEqual(x.position, y.position);
                Assert.AreEqual(x.fault, y.fault);
                Assert.AreEqual(x.winner, y.winner);
            }
            Assert.AreEqual(a.Match.World.Contacts.Count, b.Match.World.Contacts.Count);
            for (int i = 0; i < a.Match.World.Contacts.Count; i++)
            {
                var x = a.Match.World.Contacts[i];
                var y = b.Match.World.Contacts[i];
                Assert.AreEqual(x.time, y.time);
                Assert.AreEqual(x.player, y.player);
                Assert.AreEqual(x.surface, y.surface);
                Assert.AreEqual(x.point, y.point);
                Assert.AreEqual(x.normal, y.normal);
                Assert.AreEqual(x.incoming, y.incoming);
                Assert.AreEqual(x.velocity, y.velocity);
                Assert.AreEqual(x.spin, y.spin);
            }
        }
    }
}
