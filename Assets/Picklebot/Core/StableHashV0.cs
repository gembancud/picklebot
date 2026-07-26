using System;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace Picklebot.Core
{
    public static class StableHashV0
    {
        public static ulong Fnv1A64(string value)
        {
            if (value == null)
            {
                throw new ArgumentNullException(nameof(value));
            }

            const ulong offset = 14695981039346656037UL;
            const ulong prime = 1099511628211UL;
            var hash = offset;
            var bytes = Encoding.UTF8.GetBytes(value);

            unchecked
            {
                foreach (var current in bytes)
                {
                    hash ^= current;
                    hash *= prime;
                }
            }

            return hash;
        }

        public static string Hex(string value)
        {
            return Fnv1A64(value).ToString("x16", CultureInfo.InvariantCulture);
        }

        public static string Float(float value)
        {
            return value.ToString("R", CultureInfo.InvariantCulture);
        }

        public static string Vector(Vector3 value)
        {
            return $"{Float(value.x)},{Float(value.y)},{Float(value.z)}";
        }

        public static string QuaternionValue(Quaternion value)
        {
            var canonical = FiniteMath.Canonicalize(value);
            return $"{Float(canonical.x)},{Float(canonical.y)},{Float(canonical.z)},{Float(canonical.w)}";
        }
    }
}
