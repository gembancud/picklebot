using System;
using NUnit.Framework;
using Picklebot.PlayerControlsIntegration;

namespace Picklebot.PlayerLearning.Tests
{
    // Accounting tests supply contact/stop flags explicitly. They do not establish
    // that a reset or policy can physically reach a contact or a legal landing.
    public sealed class PlayerMovementFlightRewardV3Tests
    {
        [Test]
        public void IncomingFlightPaysNothingAndFirstAcceptedFaceContactOnlyStartsTracking()
        {
            var reward = new PlayerMovementFlightRewardV3();
            Assert.IsFalse(reward.Started);
            Assert.IsFalse(reward.Stopped);
            foreach (float z in new[] { -5f, -1f, 2f, 5f })
                Assert.AreEqual(0, reward.Advance(z, false, false, false, false));
            Assert.AreEqual(0, reward.TotalReward);
            Assert.AreEqual(0, reward.RewardedSteps);
            Assert.IsFalse(reward.Started);

            Assert.AreEqual(0, reward.Advance(-3, true, false, false, false));
            Assert.IsTrue(reward.Started);
            Assert.IsFalse(reward.Stopped);
            Assert.AreEqual(0, reward.TotalReward);
            Assert.AreEqual(0, reward.RewardedSteps);
            Assert.AreEqual(.125f, reward.Advance(-1, false, false, false, false), 1e-7);
            Assert.AreEqual(1, reward.RewardedSteps);
        }

        [Test]
        public void RepeatedContactFlagsAndOscillationCannotRestartOrFarmTheQuarterPointBudget()
        {
            var reward = new PlayerMovementFlightRewardV3();
            Assert.AreEqual(.25f, PlayerMovementFlightRewardV3.MaximumReward);
            reward.Advance(-3, true, false, false, false);
            Assert.AreEqual(.125f, reward.Advance(-1, true, false, false, false), 1e-7);
            for (int i = 0; i < 20; i++)
            {
                Assert.AreEqual(0, reward.Advance(-4, true, false, false, false));
                Assert.AreEqual(0, reward.Advance(-1, false, false, false, false));
            }
            Assert.AreEqual(.125f, reward.Advance(1, false, false, false, false), 1e-7);
            Assert.AreEqual(0, reward.Advance(100, true, false, false, false));
            Assert.AreEqual(.25f, reward.TotalReward, 1e-7);
            Assert.AreEqual(2, reward.RewardedSteps);
        }

        [TestCase(-3f)]
        [TestCase(.9f)]
        [TestCase(2f)]
        public void AcceptedFlightUsesExistingReturnProgressAccounting(float start)
        {
            var reference = new PlayerReturnProgressV3(start);
            var reward = new PlayerMovementFlightRewardV3();
            reward.Advance(start, true, false, false, false);
            float sum = 0;
            int paidSteps = 0;
            foreach (float delta in new[] { -.5f, 0f, .1f, .3f, .15f, .5f, 1f, 5f, 0f, 10f })
            {
                float expected = reference.Advance(start + delta);
                Assert.AreEqual(expected, reward.Advance(start + delta, true, false, false, false), 1e-7);
                sum += expected;
                if (expected > 0) paidSteps++;
                Assert.AreEqual(sum, reward.TotalReward, 1e-7);
                Assert.AreEqual(paidSteps, reward.RewardedSteps);
                Assert.That(reward.TotalReward, Is.InRange(0f, .25f));
            }
        }

        [TestCase(true, false, false)]
        [TestCase(false, true, false)]
        [TestCase(false, false, true)]
        [TestCase(true, true, true)]
        public void EachStopGuardWinsBeforeAccumulationAndRemainsSticky(bool fault, bool terminal, bool landing)
        {
            var reward = new PlayerMovementFlightRewardV3();
            reward.Advance(-3, true, false, false, false);
            Assert.AreEqual(.125f, reward.Advance(-1, false, false, false, false), 1e-7);
            Assert.AreEqual(0, reward.Advance(1, true, fault, terminal, landing));
            Assert.IsTrue(reward.Started);
            Assert.IsTrue(reward.Stopped);
            for (int i = 0; i < 3; i++)
                Assert.AreEqual(0, reward.Advance(20, true, false, false, false));
            Assert.AreEqual(.125f, reward.TotalReward, 1e-7);
            Assert.AreEqual(1, reward.RewardedSteps);
        }

        [TestCase(true, false, false)]
        [TestCase(false, true, false)]
        [TestCase(false, false, true)]
        public void StopBeforeContactPreventsAllLaterContactCredit(bool fault, bool terminal, bool landing)
        {
            var reward = new PlayerMovementFlightRewardV3();
            Assert.AreEqual(0, reward.Advance(-3, true, fault, terminal, landing));
            Assert.IsFalse(reward.Started);
            Assert.IsTrue(reward.Stopped);
            Assert.AreEqual(0, reward.Advance(10, true, false, false, false));
            Assert.AreEqual(0, reward.TotalReward);
            Assert.AreEqual(0, reward.RewardedSteps);
        }

        [TestCase(false)]
        [TestCase(true)]
        public void ExplicitStopUsedByDrillFinishIsIdempotentAndPreservesPaidCredit(bool started)
        {
            var reward = new PlayerMovementFlightRewardV3();
            if (started)
            {
                reward.Advance(-3, true, false, false, false);
                reward.Advance(-1, false, false, false, false);
            }
            reward.Stop();
            reward.Stop();
            Assert.IsTrue(reward.Stopped);
            Assert.AreEqual(started, reward.Started);
            Assert.AreEqual(0, reward.Advance(10, true, false, false, false));
            Assert.AreEqual(started ? .125f : 0, reward.TotalReward);
            Assert.AreEqual(started ? 1 : 0, reward.RewardedSteps);
        }

        [TestCase(float.NaN)]
        [TestCase(float.PositiveInfinity)]
        [TestCase(float.NegativeInfinity)]
        public void NonfiniteInputIsRejectedWithoutMutatingAnyLifecycleState(float invalid)
        {
            var fresh = new PlayerMovementFlightRewardV3();
            Assert.Throws<ArgumentException>(() => fresh.Advance(invalid, true, true, true, true));
            Assert.IsFalse(fresh.Started);
            Assert.IsFalse(fresh.Stopped);
            Assert.AreEqual(0, fresh.TotalReward);
            Assert.AreEqual(0, fresh.RewardedSteps);

            fresh.Advance(-3, true, false, false, false);
            Assert.Throws<ArgumentException>(() => fresh.Advance(invalid, false, false, false, false));
            Assert.AreEqual(.125f, fresh.Advance(-1, false, false, false, false), 1e-7);
            fresh.Advance(1, false, false, true, false);
            Assert.Throws<ArgumentException>(() => fresh.Advance(invalid, true, false, false, false));
            Assert.IsTrue(fresh.Stopped);
            Assert.AreEqual(.125f, fresh.TotalReward, 1e-7);
            Assert.AreEqual(1, fresh.RewardedSteps);
        }
    }
}
