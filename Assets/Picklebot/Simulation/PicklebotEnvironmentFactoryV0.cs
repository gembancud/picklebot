using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    public sealed class PicklebotEnvironmentFixtureV0
    {
        public GameObject Root { get; }
        public PicklebotEnvironmentV0 Environment { get; }
        public SimulationConfigV0 Configuration { get; }
        private readonly PhysicsMaterial[] materials;

        internal PicklebotEnvironmentFixtureV0(
            GameObject root,
            PicklebotEnvironmentV0 environment,
            SimulationConfigV0 configuration,
            PhysicsMaterial[] createdMaterials)
        {
            Root = root;
            Environment = environment;
            Configuration = configuration;
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

            foreach (var material in materials)
            {
                if (material != null)
                {
                    Object.DestroyImmediate(material);
                }
            }
        }
    }

    public static class PicklebotEnvironmentFactoryV0
    {
        public static PicklebotEnvironmentFixtureV0 Create(string rootName = "PicklebotTestEnvironment")
        {
            var configuration = ScriptableObject.CreateInstance<SimulationConfigV0>();
            var root = new GameObject(rootName);
            var environment = root.AddComponent<PicklebotEnvironmentV0>();

            var floor = GameObject.CreatePrimitive(PrimitiveType.Cube);
            floor.name = "CourtSurface";
            floor.transform.SetParent(root.transform);
            floor.transform.position = new Vector3(0f, -0.05f, 0f);
            floor.transform.localScale = new Vector3(
                CourtGeometryV0.CourtWidth,
                0.1f,
                CourtGeometryV0.CourtLength);
            floor.AddComponent<CollisionIdentityV0>()
                .Configure(CollisionEntityKindV0.Floor, 10);

            var catchFloor = new GameObject("OutCatchFloor");
            catchFloor.transform.SetParent(root.transform);
            catchFloor.transform.position = new Vector3(0f, -0.075f, 0f);
            catchFloor.transform.localScale = new Vector3(
                CourtGeometryV0.CourtWidth +
                    (configuration.PlayableHorizontalMargin * 2f),
                0.1f,
                CourtGeometryV0.CourtLength +
                    (configuration.PlayableHorizontalMargin * 2f));
            var catchFloorCollider = catchFloor.AddComponent<BoxCollider>();
            catchFloor.AddComponent<CollisionIdentityV0>()
                .Configure(CollisionEntityKindV0.Floor, 11);

            var net = new GameObject("Net");
            net.transform.SetParent(root.transform);
            net.AddComponent<CollisionIdentityV0>()
                .Configure(CollisionEntityKindV0.Net, 20);
            var netLeft = CreateNetSegment(net.transform, "NetLeft", -1f);
            var netRight = CreateNetSegment(net.transform, "NetRight", 1f);

            var ballObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            ballObject.name = "Ball";
            ballObject.transform.SetParent(root.transform);
            ballObject.transform.localScale = Vector3.one * configuration.BallDiameter;
            var ball = ballObject.AddComponent<Rigidbody>();
            ballObject.AddComponent<BallContactReporterV0>();

            var paddleObject = GameObject.CreatePrimitive(PrimitiveType.Cube);
            paddleObject.name = "Paddle";
            paddleObject.transform.SetParent(root.transform);
            paddleObject.transform.localScale = configuration.PaddleSize;
            var paddle = paddleObject.AddComponent<Rigidbody>();
            paddleObject.AddComponent<CollisionIdentityV0>()
                .Configure(CollisionEntityKindV0.ControlledPaddle, 30);

            var ballMaterial = CreateMaterial(
                "BallPhysicsV0",
                configuration.BallBounciness,
                configuration.BallDynamicFriction,
                configuration.BallStaticFriction);
            var paddleMaterial = CreateMaterial(
                "PaddlePhysicsV0",
                configuration.PaddleBounciness,
                configuration.PaddleDynamicFriction,
                configuration.PaddleStaticFriction);
            var courtMaterial = CreateMaterial(
                "CourtPhysicsV0",
                configuration.CourtBounciness,
                configuration.CourtDynamicFriction,
                configuration.CourtStaticFriction);
            var netMaterial = CreateMaterial(
                "NetPhysicsV0",
                configuration.NetBounciness,
                configuration.NetDynamicFriction,
                configuration.NetStaticFriction);

            environment.Configure(
                configuration,
                ball,
                paddle,
                floor.GetComponent<Collider>(),
                netLeft,
                ballMaterial,
                paddleMaterial,
                courtMaterial,
                netMaterial);
            netRight.material = netMaterial;
            catchFloorCollider.material = courtMaterial;
            Physics.SyncTransforms();

            return new PicklebotEnvironmentFixtureV0(
                root,
                environment,
                configuration,
                new[] { ballMaterial, paddleMaterial, courtMaterial, netMaterial });
        }

        private static PhysicsMaterial CreateMaterial(
            string name,
            float bounciness,
            float dynamicFriction,
            float staticFriction)
        {
            return new PhysicsMaterial(name)
            {
                bounciness = bounciness,
                dynamicFriction = dynamicFriction,
                staticFriction = staticFriction,
                bounceCombine = PhysicsMaterialCombine.Average,
                frictionCombine = PhysicsMaterialCombine.Average
            };
        }

        private static BoxCollider CreateNetSegment(
            Transform parent,
            string name,
            float side)
        {
            var segment = GameObject.CreatePrimitive(PrimitiveType.Cube);
            segment.name = name;
            segment.transform.SetParent(parent);
            segment.transform.position = new Vector3(
                side * CourtGeometryV0.HalfWidth / 2f,
                CourtGeometryV0.NetSegmentAverageHeight / 2f,
                0f);
            segment.transform.rotation = Quaternion.Euler(
                0f,
                0f,
                side * CourtGeometryV0.NetSegmentSlopeDegrees);
            segment.transform.localScale = new Vector3(
                CourtGeometryV0.HalfWidth,
                CourtGeometryV0.NetSegmentAverageHeight,
                0.04f);
            return segment.GetComponent<BoxCollider>();
        }
    }
}
