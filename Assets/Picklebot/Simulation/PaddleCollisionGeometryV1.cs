using System;
using System.Collections.Generic;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    public static class PaddleCollisionGeometryV1
    {
        public const int CornerSegments = 6;

        public static Mesh CreateRoundedFaceMesh(
            Vector3 size,
            float cornerRadius = CourtGeometryV1.PaddleCornerRadius)
        {
            if (!FiniteMath.IsFinite(size) ||
                size.x <= 0f ||
                size.y <= 0f ||
                size.z <= 0f ||
                !FiniteMath.IsFinite(cornerRadius) ||
                cornerRadius <= 0f ||
                cornerRadius > Mathf.Min(size.x, size.y) / 2f)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(size),
                    "Rounded paddle dimensions must be finite and physically valid.");
            }

            var boundary = CreateBoundary(size.x, size.y, cornerRadius);
            var count = boundary.Count;
            var vertices = new Vector3[2 + (count * 2)];
            var halfThickness = size.z / 2f;
            vertices[0] = new Vector3(0f, 0f, halfThickness);
            vertices[1] = new Vector3(0f, 0f, -halfThickness);
            for (var index = 0; index < count; index++)
            {
                var point = boundary[index];
                vertices[2 + index] =
                    new Vector3(point.x, point.y, halfThickness);
                vertices[2 + count + index] =
                    new Vector3(point.x, point.y, -halfThickness);
            }

            var triangles = new int[count * 12];
            var cursor = 0;
            for (var index = 0; index < count; index++)
            {
                var next = (index + 1) % count;
                var front = 2 + index;
                var frontNext = 2 + next;
                var back = 2 + count + index;
                var backNext = 2 + count + next;

                triangles[cursor++] = 0;
                triangles[cursor++] = front;
                triangles[cursor++] = frontNext;

                triangles[cursor++] = 1;
                triangles[cursor++] = backNext;
                triangles[cursor++] = back;

                triangles[cursor++] = front;
                triangles[cursor++] = back;
                triangles[cursor++] = backNext;
                triangles[cursor++] = front;
                triangles[cursor++] = backNext;
                triangles[cursor++] = frontNext;
            }

            var mesh = new Mesh
            {
                name = "RoundedPaddleFaceCollisionV1",
                vertices = vertices,
                triangles = triangles
            };
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }

        public static MeshCollider AddRoundedFace(
            GameObject target,
            Vector3 size,
            out Mesh mesh)
        {
            if (target == null)
            {
                throw new ArgumentNullException(nameof(target));
            }

            mesh = CreateRoundedFaceMesh(size);
            var filter = target.AddComponent<MeshFilter>();
            filter.sharedMesh = mesh;
            target.AddComponent<MeshRenderer>();
            var collider = target.AddComponent<MeshCollider>();
            collider.sharedMesh = mesh;
            collider.convex = true;
            return collider;
        }

        private static List<Vector2> CreateBoundary(
            float width,
            float length,
            float radius)
        {
            var points = new List<Vector2>(CornerSegments * 4);
            var halfWidth = width / 2f;
            var halfLength = length / 2f;
            AddCorner(points, halfWidth - radius, -halfLength + radius, -90f, radius);
            AddCorner(points, halfWidth - radius, halfLength - radius, 0f, radius);
            AddCorner(points, -halfWidth + radius, halfLength - radius, 90f, radius);
            AddCorner(points, -halfWidth + radius, -halfLength + radius, 180f, radius);
            return points;
        }

        private static void AddCorner(
            ICollection<Vector2> points,
            float centerX,
            float centerY,
            float startDegrees,
            float radius)
        {
            for (var segment = 0; segment < CornerSegments; segment++)
            {
                var angle = (
                    startDegrees +
                    ((90f * segment) / CornerSegments)) * Mathf.Deg2Rad;
                points.Add(new Vector2(
                    centerX + (Mathf.Cos(angle) * radius),
                    centerY + (Mathf.Sin(angle) * radius)));
            }
        }
    }
}
