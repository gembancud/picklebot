using UnityEngine;

namespace Picklebot.Core
{
    public static class CourtGeometryV0
    {
        public const float CourtLength = 13.4112f;
        public const float CourtWidth = 6.0960f;
        public const float HalfLength = CourtLength / 2f;
        public const float HalfWidth = CourtWidth / 2f;
        public const float NonVolleyZoneDepth = 2.1336f;
        public const float NetSidelineHeight = 0.9144f;
        public const float NetCenterHeight = 0.8636f;
        public const float BallMass = 0.024f;
        public const float BallDiameter = 0.074f;
        public const float BallRadius = BallDiameter / 2f;
        public const float BoundaryEpsilon = 0.0001f;

        public static float NetSegmentAverageHeight =>
            (NetSidelineHeight + NetCenterHeight) / 2f;

        public static float NetSegmentSlopeDegrees =>
            Mathf.Atan2(
                NetSidelineHeight - NetCenterHeight,
                HalfWidth) * Mathf.Rad2Deg;

        public static ZoneClassificationV0 ClassifyFloorContact(Vector3 contact)
        {
            if (!FiniteMath.IsFinite(contact))
            {
                return ZoneClassificationV0.Unknown;
            }

            if (Mathf.Abs(contact.x) > HalfWidth + BoundaryEpsilon ||
                Mathf.Abs(contact.z) > HalfLength + BoundaryEpsilon)
            {
                return ZoneClassificationV0.Out;
            }

            if (contact.z >= -BoundaryEpsilon)
            {
                return contact.z <= NonVolleyZoneDepth + BoundaryEpsilon
                    ? ZoneClassificationV0.FarNonVolleyZone
                    : ZoneClassificationV0.FarCourtIn;
            }

            return contact.z >= -NonVolleyZoneDepth - BoundaryEpsilon
                ? ZoneClassificationV0.NearNonVolleyZone
                : ZoneClassificationV0.NearCourtIn;
        }

        public static bool IsFarCourt(ZoneClassificationV0 zone)
        {
            return zone is ZoneClassificationV0.FarCourtIn or
                ZoneClassificationV0.FarNonVolleyZone;
        }

        public static bool IsNearCourt(ZoneClassificationV0 zone)
        {
            return zone is ZoneClassificationV0.NearCourtIn or
                ZoneClassificationV0.NearNonVolleyZone;
        }

        public static bool IsInsidePlayableVolume(Vector3 position)
        {
            return FiniteMath.IsFinite(position) &&
                   Mathf.Abs(position.x) <= 8f &&
                   position.y >= -1f &&
                   position.y <= 8f &&
                   Mathf.Abs(position.z) <= 9f;
        }
    }
}
