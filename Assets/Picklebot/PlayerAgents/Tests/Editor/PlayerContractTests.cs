using System;
using NUnit.Framework;
using UnityEngine;

namespace Picklebot.PlayerAgents.Tests
{
    public sealed class PlayerContractTests
    {
        [Test] public void SchemaHasOneNameForEachObservation()
        { Assert.That(PlayerObservation.Fields.Length, Is.EqualTo(PlayerObservation.Count)); }

        [TestCase(0)] [TestCase(1)] [TestCase(2)] [TestCase(3)]
        public void CoordinateConversionRoundTrips(int player)
        {
            var vector = new Vector3(1.2f, 2.3f, -4.5f);
            Assert.That(PlayerObservation.ToWorld(PlayerObservation.ToLocal(vector, player), player), Is.EqualTo(vector));
        }

        [Test] public void BothTeamsSeeForwardAsPositiveZ()
        {
            Assert.That(PlayerObservation.ToLocal(Vector3.forward, 0).z, Is.EqualTo(1));
            Assert.That(PlayerObservation.ToLocal(Vector3.back, 2).z, Is.EqualTo(1));
        }

        [Test] public void SpinTransformPreservesCrossProducts()
        {
            var a = new Vector3(2, 1, -3); var b = new Vector3(4, -1, 5);
            Assert.That(PlayerObservation.ToLocal(Vector3.Cross(a, b), 2),
                Is.EqualTo(Vector3.Cross(PlayerObservation.ToLocal(a, 2), PlayerObservation.ToLocal(b, 2))));
        }

        [Test] public void MovementMagnitudeIsBoundedWithoutChangingIntent()
        {
            var a = new PlayerAction { moveX = 3, moveZ = 4, attempt = true, shot = 8 }.Validated();
            Assert.That(new Vector2(a.moveX, a.moveZ).magnitude, Is.EqualTo(1).Within(.00001));
            Assert.That(a.attempt); Assert.That(a.shot, Is.EqualTo(8));
        }

        [Test] public void NonFiniteMovementAndInvalidShotAreRejected()
        {
            Assert.Throws<ArgumentException>(() => new PlayerAction { moveX = float.NaN }.Validated());
            Assert.Throws<ArgumentException>(() => new PlayerAction { moveZ = float.PositiveInfinity }.Validated());
            Assert.Throws<ArgumentOutOfRangeException>(() => new PlayerAction { shot = 9 }.Validated());
            Assert.Throws<ArgumentOutOfRangeException>(() => new PlayerAction { shot = -1 }.Validated());
        }

        [Test] public void RewardIsSharedWithinTeamAndOpposedAcrossTeams()
        {
            for (int winner = 0; winner < 2; winner++)
            for (int player = 0; player < 4; player++)
                Assert.That(PlayerMatch.TeamReward(player, winner), Is.EqualTo(player / 2 == winner ? 1 : -1));
            for (int player = 0; player < 4; player++) Assert.That(PlayerMatch.TeamReward(player, -1), Is.Zero);
        }

        [Test] public void PolicyReceivesNoWorldOrOtherPlayerController()
        {
            var parameters = typeof(IPlayerPolicy).GetMethod("Decide").GetParameters();
            Assert.That(parameters.Length, Is.EqualTo(2));
            Assert.That(parameters[0].ParameterType, Is.EqualTo(typeof(PlayerObservation)));
            Assert.That(parameters[1].ParameterType, Is.EqualTo(typeof(System.Random)));
            foreach (var field in typeof(PlayerObservation).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance))
                Assert.That(field.FieldType == typeof(int) || field.FieldType == typeof(float[]), Is.True, field.Name);
        }
    }
}
