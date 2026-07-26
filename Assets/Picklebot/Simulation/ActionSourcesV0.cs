using System;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    public interface IPaddleActionSourceV0
    {
        void Reset(ulong seed);
        bool TryGetNext(out PaddleActionV0 action);
    }

    public sealed class ZeroActionSourceV0 : IPaddleActionSourceV0
    {
        public void Reset(ulong seed)
        {
        }

        public bool TryGetNext(out PaddleActionV0 action)
        {
            action = PaddleActionV0.Zero;
            return true;
        }
    }

    [Serializable]
    public struct RecordedActionFrameV0
    {
        public Vector3 LinearVelocityLocal;
        public Vector3 AngularVelocityLocal;

        public PaddleActionV0 ToAction()
        {
            return new PaddleActionV0(LinearVelocityLocal, AngularVelocityLocal);
        }
    }

    [CreateAssetMenu(
        fileName = "RecordedActionSequenceV0",
        menuName = "Picklebot/Recorded Action Sequence V0")]
    public sealed class RecordedActionSequenceV0 : ScriptableObject
    {
        public string RecordingVersion = "recording-v0";
        public RecordedActionFrameV0[] Frames = Array.Empty<RecordedActionFrameV0>();
    }

    public sealed class RecordedActionSourceV0 : IPaddleActionSourceV0
    {
        private readonly RecordedActionSequenceV0 sequence;
        private int index;

        public RecordedActionSourceV0(RecordedActionSequenceV0 recordedSequence)
        {
            sequence = recordedSequence != null
                ? recordedSequence
                : throw new ArgumentNullException(nameof(recordedSequence));
        }

        public void Reset(ulong seed)
        {
            index = 0;
        }

        public bool TryGetNext(out PaddleActionV0 action)
        {
            if (index >= sequence.Frames.Length)
            {
                action = PaddleActionV0.Zero;
                return false;
            }

            action = sequence.Frames[index++].ToAction();
            return true;
        }
    }
}
