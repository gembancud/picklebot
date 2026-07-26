using System.Collections.Generic;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    public sealed class PicklebotEnvironmentFixtureV1
    {
        public GameObject Root { get; }
        public PicklebotEnvironmentV1 Environment { get; }
        public SimulationConfigV1 Configuration { get; }
        public Collider PaddleFaceCollider { get; }
        public Collider PaddleHandleCollider { get; }
        public IReadOnlyList<Collider> NetColliders { get; }
        private readonly PhysicsMaterial[] materials;
        private readonly Mesh paddleFaceMesh;

        internal PicklebotEnvironmentFixtureV1(
            GameObject root,
            PicklebotEnvironmentV1 environment,
            SimulationConfigV1 configuration,
            Collider paddleFaceCollider,
            Collider paddleHandleCollider,
            IReadOnlyList<Collider> netColliders,
            Mesh createdPaddleFaceMesh,
            PhysicsMaterial[] createdMaterials)
        {
            Root = root;
            Environment = environment;
            Configuration = configuration;
            PaddleFaceCollider = paddleFaceCollider;
            PaddleHandleCollider = paddleHandleCollider;
            NetColliders = netColliders;
            paddleFaceMesh = createdPaddleFaceMesh;
            materials = createdMaterials;
        }

        public void Destroy()
        {
            if (Root != null)
            {
                Object.DestroyImmediate(Root);
            }

            if (Configuration != null)
            {
                Object.DestroyImmediate(Configuration);
            }

            if (paddleFaceMesh != null)
            {
                Object.DestroyImmediate(paddleFaceMesh);
            }

            foreach (var material in materials)
            {
                if (material != null)
                {
                    Object.DestroyImmediate(material);
                }
            }
        }
    }

    public static class PicklebotEnvironmentFactoryV1
    {
        public static PicklebotEnvironmentFixtureV1 Create(
            string rootName = "PicklebotTestEnvironmentV1")
        {
            var configuration = ScriptableObject.CreateInstance<SimulationConfigV1>();
            var root = new GameObject(rootName);
            var environment = root.AddComponent<PicklebotEnvironmentV1>();

            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "CourtSurface";
            floor.transform.SetParent(root.transform);
            floor.transform.position = new Vector3(0f, -0.05f, 0f);
            floor.transform.localScale = new Vector3(
                CourtGeometryV1.CourtWidth,
                0.1f,
                CourtGeometryV1.CourtLength);
            floor.AddComponent<CollisionIdentityV0>()
                .Configure(CollisionEntityKindV0.Floor, 10);

            var catchFloor = new GameObject("OutCatchFloor");
            catchFloor.transform.SetParent(root.transform);
            catchFloor.transform.position = new Vector3(0f, -0.075f, 0f);
            catchFloor.transform.localScale = new Vector3(
                CourtGeometryV1.CourtWidth +
                    (configuration.PlayableHorizontalMargin * 2f),
                0.1f,
                CourtGeometryV1.CourtLength +
                    (configuration.PlayableHorizontalMargin * 2f));
            var catchFloorCollider = catchFloor.AddComponent<BoxCollider>();
            catchFloor.AddComponent<CollisionIdentityV0>()
                .Configure(CollisionEntityKindV0.Floor, 11);

            var net = new GameObject("Net");
            net.transform.SetParent(root.transform);
            net.AddComponent<CollisionIdentityV0>()
                .Configure(CollisionEntityKindV0.Net, 20);
            var netColliders = CreateNet(net.transform);

            var ballObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            ballObject.name = "Ball";
            ballObject.transform.SetParent(root.transform);
            ballObject.transform.localScale =
                Vector3.one * configuration.BallDiameter;
            var ball = ballObject.AddComponent<Rigidbody>();
            ballObject.AddComponent<BallContactReporterV1>();

            var paddleObject = new GameObject("Paddle");
            paddleObject.transform.SetParent(root.transform);
            var paddle = paddleObject.AddComponent<Rigidbody>();
            paddleObject.AddComponent<CollisionIdentityV0>()
                .Configure(CollisionEntityKindV0.ControlledPaddle, 30);

            var paddleFace = new GameObject("RoundedHittingFace");
            paddleFace.name = "RoundedHittingFace";
            paddleFace.transform.SetParent(paddleObject.transform);
            paddleFace.transform.localPosition =
                new Vector3(0f, CourtGeometryV1.PaddleHandleLength / 2f, 0f);
            var paddleFaceCollider = PaddleCollisionGeometryV1.AddRoundedFace(
                paddleFace,
                configuration.PaddleFaceSize,
                out var paddleFaceMesh);

            var paddleHandle = GameObject.CreatePrimitive(PrimitiveType.Cube);
            paddleHandle.name = "NonContactHandle";
            paddleHandle.transform.SetParent(paddleObject.transform);
            paddleHandle.transform.localPosition =
                new Vector3(0f, -CourtGeometryV1.PaddleFaceLength / 2f, 0f);
            paddleHandle.transform.localScale = new Vector3(
                0.035f,
                CourtGeometryV1.PaddleHandleLength,
                CourtGeometryV1.PaddleThickness);
            paddleHandle.AddComponent<CollisionIdentityV0>()
                .Configure(CollisionEntityKindV0.Other, 31);
            var paddleHandleCollider = paddleHandle.GetComponent<BoxCollider>();

            var ballMaterial = CreateMaterial(
                "BallPhysicsV1",
                1f,
                configuration.BallDynamicFriction);
            var paddleMaterial = CreateMaterial(
                "PaddlePhysicsV1",
                configuration.PaddleRestitution,
                configuration.PaddleDynamicFriction);
            var handleMaterial = CreateMaterial(
                "PaddleHandlePhysicsV1",
                0f,
                configuration.PaddleDynamicFriction);
            var courtMaterial = CreateMaterial(
                "CourtPhysicsV1",
                configuration.CourtRestitution,
                configuration.CourtDynamicFriction);
            var netMaterial = CreateMaterial(
                "NetPhysicsV1",
                configuration.NetRestitution,
                configuration.NetDynamicFriction);

            paddleHandleCollider.material = handleMaterial;
            catchFloorCollider.material = courtMaterial;
            foreach (var current in netColliders)
            {
                current.material = netMaterial;
            }

            environment.Configure(
                configuration,
                ball,
                paddle,
                paddleFaceCollider,
                floor.GetComponent<Collider>(),
                netColliders[0],
                ballMaterial,
                paddleMaterial,
                courtMaterial,
                netMaterial);
            Physics.SyncTransforms();

            return new PicklebotEnvironmentFixtureV1(
                root,
                environment,
                configuration,
                paddleFaceCollider,
                paddleHandleCollider,
                netColliders,
                paddleFaceMesh,
                new[]
                {
                    ballMaterial,
                    paddleMaterial,
                    handleMaterial,
                    courtMaterial,
                    netMaterial
                });
        }

        private static PhysicsMaterial CreateMaterial(
            string name,
            float bounciness,
            float friction)
        {
            return new PhysicsMaterial(name)
            {
                bounciness = bounciness,
                dynamicFriction = friction,
                staticFriction = friction,
                bounceCombine = PhysicsMaterialCombine.Multiply,
                frictionCombine = PhysicsMaterialCombine.Multiply
            };
        }

        internal static Collider[] CreateNet(Transform parent)
        {
            var colliders = new List<Collider>(4)
            {
                CreateNetSegment(
                    parent,
                    "NetLeftOuter",
                    -CourtGeometryV1.HalfNetPostSpan,
                    -CourtGeometryV1.HalfWidth,
                    CourtGeometryV1.NetSidelineHeight,
                    CourtGeometryV1.NetSidelineHeight),
                CreateNetSegment(
                    parent,
                    "NetLeftInner",
                    -CourtGeometryV1.HalfWidth,
                    0f,
                    CourtGeometryV1.NetSidelineHeight,
                    CourtGeometryV1.NetCenterHeight),
                CreateNetSegment(
                    parent,
                    "NetRightInner",
                    0f,
                    CourtGeometryV1.HalfWidth,
                    CourtGeometryV1.NetCenterHeight,
                    CourtGeometryV1.NetSidelineHeight),
                CreateNetSegment(
                    parent,
                    "NetRightOuter",
                    CourtGeometryV1.HalfWidth,
                    CourtGeometryV1.HalfNetPostSpan,
                    CourtGeometryV1.NetSidelineHeight,
                    CourtGeometryV1.NetSidelineHeight)
            };
            return colliders.ToArray();
        }

        private static BoxCollider CreateNetSegment(
            Transform parent,
            string name,
            float startX,
            float endX,
            float startHeight,
            float endHeight)
        {
            var segment = GameObject.CreatePrimitive(PrimitiveType.Cube);
            segment.name = name;
            segment.transform.SetParent(parent);

            var width = endX - startX;
            var averageHeight = (startHeight + endHeight) / 2f;
            var slopeDegrees = Mathf.Atan2(
                endHeight - startHeight,
                width) * Mathf.Rad2Deg;

            segment.transform.localPosition = new Vector3(
                (startX + endX) / 2f,
                averageHeight / 2f,
                0f);
            segment.transform.localRotation =
                Quaternion.Euler(0f, 0f, slopeDegrees);
            segment.transform.localScale = new Vector3(
                width,
                averageHeight,
                0.04f);
            return segment.GetComponent<BoxCollider>();
        }
    }
}
