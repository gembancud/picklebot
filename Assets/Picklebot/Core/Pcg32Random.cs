using System;

namespace Picklebot.Core
{
    /// <summary>
    /// Project-owned PCG32 implementation. Its output is part of env-v0 and
    /// does not depend on UnityEngine.Random or the runtime's string hashing.
    /// </summary>
    public sealed class Pcg32Random
    {
        private ulong _state;
        private readonly ulong _increment;

        public Pcg32Random(ulong seed, ulong stream = 1UL)
        {
            _state = 0UL;
            _increment = (stream << 1) | 1UL;
            NextUInt();
            _state += seed;
            NextUInt();
        }

        public uint NextUInt()
        {
            var oldState = _state;
            _state = unchecked((oldState * 6364136223846793005UL) + _increment);
            var xorShifted = (uint)(((oldState >> 18) ^ oldState) >> 27);
            var rotation = (int)(oldState >> 59);
            return (xorShifted >> rotation) | (xorShifted << ((-rotation) & 31));
        }

        public float NextFloat()
        {
            return (NextUInt() >> 8) * (1f / 16777216f);
        }

        public float Range(float minimum, float maximum)
        {
            if (maximum < minimum)
            {
                throw new ArgumentOutOfRangeException(nameof(maximum));
            }

            return minimum + ((maximum - minimum) * NextFloat());
        }

        public static ulong DeriveStream(ulong episodeSeed, string streamName)
        {
            if (streamName == null)
            {
                throw new ArgumentNullException(nameof(streamName));
            }

            const ulong offset = 14695981039346656037UL;
            const ulong prime = 1099511628211UL;
            var hash = offset;

            unchecked
            {
                for (var index = 0; index < 8; index++)
                {
                    hash ^= (byte)(episodeSeed >> (index * 8));
                    hash *= prime;
                }

                foreach (var character in streamName)
                {
                    hash ^= (byte)(character & 0xff);
                    hash *= prime;
                    hash ^= (byte)(character >> 8);
                    hash *= prime;
                }
            }

            return hash;
        }
    }
}
