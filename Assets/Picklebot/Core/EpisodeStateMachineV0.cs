using System;

namespace Picklebot.Core
{
    public sealed class EpisodeStateMachineV0
    {
        public EpisodeStateV0 State { get; private set; } = EpisodeStateV0.Uninitialized;
        public TerminationReasonV0 TerminationReason { get; private set; } = TerminationReasonV0.None;

        public void BeginReset()
        {
            if (State == EpisodeStateV0.Resetting)
            {
                throw new InvalidOperationException($"Cannot reset while state is {State}.");
            }

            State = EpisodeStateV0.Resetting;
            TerminationReason = TerminationReasonV0.None;
        }

        public void CompleteReset()
        {
            Require(EpisodeStateV0.Resetting);
            State = EpisodeStateV0.Ready;
        }

        public void BeginRunning()
        {
            Require(EpisodeStateV0.Ready);
            State = EpisodeStateV0.Running;
        }

        public bool TryTerminate(TerminationReasonV0 reason)
        {
            if (reason == TerminationReasonV0.None)
            {
                throw new ArgumentOutOfRangeException(nameof(reason));
            }

            if (State == EpisodeStateV0.Terminal)
            {
                return false;
            }

            if (State is not (EpisodeStateV0.Ready or EpisodeStateV0.Running))
            {
                throw new InvalidOperationException($"Cannot terminate while state is {State}.");
            }

            State = EpisodeStateV0.Terminal;
            TerminationReason = reason;
            return true;
        }

        private void Require(EpisodeStateV0 expected)
        {
            if (State != expected)
            {
                throw new InvalidOperationException($"Expected state {expected}, actual state {State}.");
            }
        }
    }
}
