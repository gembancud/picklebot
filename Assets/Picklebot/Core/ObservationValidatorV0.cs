namespace Picklebot.Core
{
    public static class ObservationValidatorV0
    {
        public static bool IsFinite(ObservationV0 observation)
        {
            return FiniteMath.IsFinite(observation.ElapsedTime) &&
                   SnapshotIsFinite(observation.Ball) &&
                   SnapshotIsFinite(observation.Paddle) &&
                   FiniteMath.IsFinite(observation.BallPositionFromPaddle) &&
                   FiniteMath.IsFinite(observation.BallVelocityFromPaddle);
        }

        private static bool SnapshotIsFinite(KinematicSnapshotV0 snapshot)
        {
            return FiniteMath.IsFinite(snapshot.PositionWorld) &&
                   FiniteMath.IsFinite(snapshot.RotationWorld) &&
                   FiniteMath.IsFinite(snapshot.LinearVelocityWorld) &&
                   FiniteMath.IsFinite(snapshot.AngularVelocityWorld);
        }
    }
}
