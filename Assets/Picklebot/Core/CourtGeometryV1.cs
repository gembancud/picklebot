using UnityEngine;

namespace Picklebot.Core
{
    public static class CourtGeometryV1
    {
        public const float CourtLength = CourtGeometryV0.CourtLength;
        public const float CourtWidth = CourtGeometryV0.CourtWidth;
        public const float HalfLength = CourtLength / 2f;
        public const float HalfWidth = CourtWidth / 2f;
        public const float NonVolleyZoneDepth = CourtGeometryV0.NonVolleyZoneDepth;

        public const float NetSidelineHeight = CourtGeometryV0.NetSidelineHeight;
        public const float NetCenterHeight = CourtGeometryV0.NetCenterHeight;
        public const float NetPostSpan = 6.7056f;
        public const float HalfNetPostSpan = NetPostSpan / 2f;

        public const float BallMass = 0.024f;
        public const float BallDiameter = 0.074f;
        public const float BallRadius = BallDiameter / 2f;

        public const float PaddleWidth = 0.2032f;
        public const float PaddleLength = 0.4064f;
        public const float PaddleThickness = 0.016f;
        public const float PaddleHandleLength = 0.127f;
        public const float PaddleFaceLength = PaddleLength - PaddleHandleLength;
        public const float PaddleCornerRadius = 0.0254f;

        public static Vector3 PaddleOuterSize =>
            new(PaddleWidth, PaddleLength, PaddleThickness);

        public static Vector3 PaddleFaceSize =>
            new(PaddleWidth, PaddleFaceLength, PaddleThickness);

        public static float NetSegmentAverageHeight =>
            (NetSidelineHeight + NetCenterHeight) / 2f;

        public static float NetSegmentSlopeDegrees =>
            Mathf.Atan2(
                NetSidelineHeight - NetCenterHeight,
                HalfNetPostSpan) * Mathf.Rad2Deg;

        public static float NetHeightAtX(float x)
        {
            if (!FiniteMath.IsFinite(x))
            {
                return 0f;
            }

            var absoluteX = Mathf.Abs(x);
            if (absoluteX <= HalfWidth)
            {
                return Mathf.Lerp(
                    NetCenterHeight,
                    NetSidelineHeight,
                    absoluteX / HalfWidth);
            }

            return absoluteX <= HalfNetPostSpan
                ? NetSidelineHeight
                : 0f;
        }

        public static ZoneClassificationV0 ClassifyFloorContact(Vector3 contact)
        {
            return CourtGeometryV0.ClassifyFloorContact(contact);
        }

        public static bool IsFarCourt(ZoneClassificationV0 zone)
        {
            return CourtGeometryV0.IsFarCourt(zone);
        }

        public static bool IsNearCourt(ZoneClassificationV0 zone)
        {
            return CourtGeometryV0.IsNearCourt(zone);
        }
    }
}
