using System;
using System.IO;
using NUnit.Framework;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerAgents.Tests
{
    public sealed class PlayerPaddleReplayTests
    {
        [Serializable] private sealed class BodyState
        { public float[] position, velocity, paddle, rotation, paddleVelocity; public float shoulderHeight; }
        [Serializable] private sealed class Frame
        { public BodyState before, partner, after; public float[] moveTarget, target, rotation, feed; public int tick; }
        [Serializable] private sealed class Window
        { public int player; public Frame[] frames; }

        [TestCase(false)] [TestCase(true)]
        public void StoppingCrouchDoesNotForceAReachCorrectionOnEitherCourtEnd(bool oppositeEnd)
            => ReplayFixture("paddle-posture-stop-v1.json", "1c2ab9f6b0f6be2074fcc0104deab73e0ea255996c31996c1180c182caafd90e", 1, oppositeEnd);

        [TestCase(false)] [TestCase(true)]
        public void LowSwingRecoveryStaysWithinMotorLimitsOnEitherCourtEnd(bool oppositeEnd)
            => ReplayFixture("paddle-low-recovery-v1.json", "57b5a0ba19a4737b25e79bff1ecc3ae082a85bba51e40f202fd6d3ea19ff1a89", 0, oppositeEnd);

        [TestCase(false)] [TestCase(true)]
        public void CurvedHandRecoveryBrakesBeforeHardReachOnEitherCourtEnd(bool oppositeEnd)
            => ReplayFixture("paddle-curved-recovery-v1.json", "4f4f9299f17207ebca0a1d573fc67bf1f02b300c7f15f3c7dbfa57198a471ac6", 1, oppositeEnd);

        [TestCase(false)] [TestCase(true)]
        public void StoppedPostureCurvatureStaysBoundedOnEitherCourtEnd(bool oppositeEnd)
            => ReplayFixture("paddle-stopped-curvature-v1.json", "1d3cad07859c2522ae22f34168580160036d1bfc2ab1640d8da6791dbb97a980", 1, oppositeEnd);

        [TestCase(false)] [TestCase(true)]
        public void FastInnerSwingCanBrakeWithoutAReachCorrectionOnEitherCourtEnd(bool oppositeEnd)
            => ReplayFixture("paddle-inner-recovery-v1.json", "b3bb4363ad062cfbacb500a7a9d4f1bf5465589f7b95e09fb7b5c54e3f374013", 0, oppositeEnd);

        [TestCase(false)] [TestCase(true)]
        public void RisingAfterALowSwingPreservesStoppingDistanceOnEitherCourtEnd(bool oppositeEnd)
            => ReplayFixture("paddle-rising-recovery-v1.json", "37ee0667403f26ab778c530a012cedad2b29363d567ed36e5735dbe58e5a0d12", 0, oppositeEnd);

        [TestCase(false)] [TestCase(true)]
        public void InwardRecoveryConvergesWithinUnchangedLimitsOnEitherCourtEnd(bool oppositeEnd)
            => ReplayFixture("paddle-inward-convergence-v1.json", "ca12cc8f232d955ef2680ee4668db4cc5820b113459e0542a24cb3944507ccb6", 0, oppositeEnd);

        private static void ReplayFixture(string filename, string expectedHash, int expectedPlayer, bool oppositeEnd)
        {
            string path = Path.Combine(Application.dataPath, "Picklebot/PlayerAgents/Tests/Fixtures", filename);
            using (var hash = System.Security.Cryptography.SHA256.Create())
                Assert.That(BitConverter.ToString(hash.ComputeHash(File.ReadAllBytes(path))).Replace("-", "").ToLowerInvariant(),
                    Is.EqualTo(expectedHash));
            var window = JsonUtility.FromJson<Window>(File.ReadAllText(path));
            Assert.That(window.frames.Length, Is.EqualTo(120)); Assert.That(window.player, Is.EqualTo(expectedPlayer));
            Vector3 V(float[] a) => oppositeEnd ? new Vector3(-a[0], a[1], -a[2]) : new Vector3(a[0], a[1], a[2]);
            Quaternion Q(float[] a)
            { var q = new Quaternion(a[0], a[1], a[2], a[3]); return oppositeEnd ? new Quaternion(0, 1, 0, 0) * q : q; }
            void Restore(PlayerBody body, BodyState state)
            {
                // Diagnostic initial state and recorded partner path only.
                // The game never sets these private motor properties.
                body.Reset(V(state.position));
                typeof(PlayerBody).GetProperty("Velocity").SetValue(body, V(state.velocity));
                typeof(PlayerBody).GetProperty("PaddleVelocity").SetValue(body, V(state.paddleVelocity));
                typeof(PlayerBody).GetField("shoulderHeight", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)
                    .SetValue(body, state.shoulderHeight);
                body.Paddle.position = V(state.paddle); body.Paddle.rotation = Q(state.rotation);
                body.Paddle.transform.SetPositionAndRotation(V(state.paddle), Q(state.rotation));
            }
            using var world = new DoublesWorld(false);
            foreach (var collider in world.Ball.GetComponents<Collider>()) collider.enabled = false;
            int seat = oppositeEnd ? expectedPlayer ^ 2 : expectedPlayer;
            var player = world.Players[seat]; var partner = world.Players[seat ^ 1];
            Restore(player, window.frames[0].before); Physics.SyncTransforms();
            foreach (var frame in window.frames)
            {
                Restore(partner, frame.partner);
                var target = V(frame.target); var rotation = Q(frame.rotation); var feed = V(frame.feed); var move = V(frame.moveTarget);
                var previous = player.PaddleVelocity;
                Assert.That(PlayerPaddleMotor.Constrain(player, partner, move, ref target, ref rotation, ref feed, DoublesWorld.Dt),
                    Is.True, "No feasible command at recorded tick " + frame.tick);
                player.Step(move, target, rotation, feed, partner, DoublesWorld.Dt); world.Simulate();
                Assert.That((player.PaddleVelocity - previous).magnitude / DoublesWorld.Dt, Is.LessThanOrEqualTo(100.1f));
                Assert.That(player.PaddleVelocity.magnitude, Is.LessThanOrEqualTo(12.01f));
                Assert.That(player.AngularVelocity.magnitude, Is.LessThanOrEqualTo(12.01f));
                Assert.That(Vector3.Distance(player.Hand, player.Shoulder), Is.LessThanOrEqualTo(.6201f));
                Assert.That(Vector3.Distance(player.Position, V(frame.after.position)), Is.LessThan(.0001f), "Paddle guard must not move the feet.");
            }
        }
    }
}
