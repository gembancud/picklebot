using UnityEngine;

namespace Picklebot.Core
{
    public static class FiniteMath
    {
        public static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        public static bool IsFinite(Vector3 value)
        {
            return IsFinite(value.x) && IsFinite(value.y) && IsFinite(value.z);
        }

        public static bool IsFinite(Quaternion value)
        {
            return IsFinite(value.x) &&
                   IsFinite(value.y) &&
                   IsFinite(value.z) &&
                   IsFinite(value.w);
        }

        public static Quaternion Canonicalize(Quaternion value)
        {
            var magnitude = Mathf.Sqrt(
                (value.x * value.x) +
                (value.y * value.y) +
                (value.z * value.z) +
                (value.w * value.w));

            if (!IsFinite(magnitude) || magnitude <= Mathf.Epsilon)
            {
                return Quaternion.identity;
            }

            var normalized = new Quaternion(
                value.x / magnitude,
                value.y / magnitude,
                value.z / magnitude,
                value.w / magnitude);

            if (normalized.w < 0f ||
                (Mathf.Approximately(normalized.w, 0f) && FirstNonZeroIsNegative(normalized)))
            {
                normalized = new Quaternion(
                    -normalized.x,
                    -normalized.y,
                    -normalized.z,
                    -normalized.w);
            }

            return normalized;
        }

        public static Vector3 ClampUnitCube(Vector3 value)
        {
            return new Vector3(
                Mathf.Clamp(value.x, -1f, 1f),
                Mathf.Clamp(value.y, -1f, 1f),
                Mathf.Clamp(value.z, -1f, 1f));
        }

        private static bool FirstNonZeroIsNegative(Quaternion value)
        {
            if (!Mathf.Approximately(value.x, 0f))
            {
                return value.x < 0f;
            }

            if (!Mathf.Approximately(value.y, 0f))
            {
                return value.y < 0f;
            }

            return value.z < 0f;
        }
    }
}
