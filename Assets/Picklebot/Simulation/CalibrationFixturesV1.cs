using System;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    public enum DropReleaseDatumV1
    {
        BallTop,
        BallCenter,
        BallBottom
    }

    public readonly struct BallDropResultV1
    {
        public readonly DropReleaseDatumV1 ReleaseDatum;
        public readonly float ReleaseReferenceHeight;
        public readonly float InitialCenterHeight;
        public readonly float FirstImpactTime;
        public readonly float FirstReboundTopHeight;
        public readonly float HorizontalDrift;
        public readonly float PreImpactMechanicalEnergy;
        public readonly float PostImpactMechanicalEnergy;
        public readonly int SimulatedTicks;
        public readonly bool Completed;

        public BallDropResultV1(
            DropReleaseDatumV1 releaseDatum,
            float releaseReferenceHeight,
            float initialCenterHeight,
            float firstImpactTime,
            float firstReboundTopHeight,
            float horizontalDrift,
            float preImpactMechanicalEnergy,
            float postImpactMechanicalEnergy,
            int simulatedTicks,
            bool completed)
        {
            ReleaseDatum = releaseDatum;
            ReleaseReferenceHeight = releaseReferenceHeight;
            InitialCenterHeight = initialCenterHeight;
            FirstImpactTime = firstImpactTime;
            FirstReboundTopHeight = firstReboundTopHeight;
            HorizontalDrift = horizontalDrift;
            PreImpactMechanicalEnergy = preImpactMechanicalEnergy;
            PostImpactMechanicalEnergy = postImpactMechanicalEnergy;
            SimulatedTicks = simulatedTicks;
            Completed = completed;
        }
    }

    public readonly struct PaddleImpactResultV1
        {
            public readonly float IncomingBallSpeed;
            public readonly float PaddleSpeed;
            public readonly Vector2 ImpactOffset;
            public readonly Vector3 IncomingBallVelocity;
            public readonly Vector3 OutgoingBallVelocity;
            public readonly Vector3 IncomingAngularVelocity;
            public readonly Vector3 OutgoingAngularVelocity;
            public readonly float IncomingRelativeNormalSpeed;
            public readonly float OutgoingRelativeNormalSpeed;
            public readonly float OutgoingBallSpeed;
            public readonly float EffectiveRestitution;
            public readonly float BallKineticEnergyRatio;
            public readonly float TangentialVelocityChange;
            public readonly float AngularVelocityChange;
            public readonly int SimulatedTicks;
            public readonly bool Completed;

            public PaddleImpactResultV1(
                float incomingBallSpeed,
                float paddleSpeed,
                Vector2 impactOffset,
                Vector3 incomingBallVelocity,
                Vector3 outgoingBallVelocity,
                Vector3 incomingAngularVelocity,
                Vector3 outgoingAngularVelocity,
                float incomingRelativeNormalSpeed,
                float outgoingRelativeNormalSpeed,
                float outgoingBallSpeed,
                float effectiveRestitution,
                float ballKineticEnergyRatio,
                float tangentialVelocityChange,
                float angularVelocityChange,
                int simulatedTicks,
                bool completed)
            {
                IncomingBallSpeed = incomingBallSpeed;
                PaddleSpeed = paddleSpeed;
                ImpactOffset = impactOffset;
                IncomingBallVelocity = incomingBallVelocity;
                OutgoingBallVelocity = outgoingBallVelocity;
                IncomingAngularVelocity = incomingAngularVelocity;
                OutgoingAngularVelocity = outgoingAngularVelocity;
                IncomingRelativeNormalSpeed = incomingRelativeNormalSpeed;
                OutgoingRelativeNormalSpeed = outgoingRelativeNormalSpeed;
                OutgoingBallSpeed = outgoingBallSpeed;
                EffectiveRestitution = effectiveRestitution;
                BallKineticEnergyRatio = ballKineticEnergyRatio;
                TangentialVelocityChange = tangentialVelocityChange;
                AngularVelocityChange = angularVelocityChange;
                SimulatedTicks = simulatedTicks;
                Completed = completed;
            }
    }

    public readonly struct CourtImpactResultV1
    {
        public readonly Vector3 IncomingVelocity;
        public readonly Vector3 OutgoingVelocity;
        public readonly Vector3 IncomingAngularVelocity;
        public readonly Vector3 OutgoingAngularVelocity;
        public readonly float FirstReboundTopHeight;
        public readonly float PreImpactMechanicalEnergy;
        public readonly float PostImpactMechanicalEnergy;
        public readonly int LogicalContactCount;
        public readonly int SimulatedTicks;
        public readonly bool Completed;

        public CourtImpactResultV1(
            Vector3 incomingVelocity,
            Vector3 outgoingVelocity,
            Vector3 incomingAngularVelocity,
            Vector3 outgoingAngularVelocity,
            float firstReboundTopHeight,
            float preImpactMechanicalEnergy,
            float postImpactMechanicalEnergy,
            int logicalContactCount,
            int simulatedTicks,
            bool completed)
        {
            IncomingVelocity = incomingVelocity;
            OutgoingVelocity = outgoingVelocity;
            IncomingAngularVelocity = incomingAngularVelocity;
            OutgoingAngularVelocity = outgoingAngularVelocity;
            FirstReboundTopHeight = firstReboundTopHeight;
            PreImpactMechanicalEnergy = preImpactMechanicalEnergy;
            PostImpactMechanicalEnergy = postImpactMechanicalEnergy;
            LogicalContactCount = logicalContactCount;
            SimulatedTicks = simulatedTicks;
            Completed = completed;
        }
    }

    public readonly struct NetImpactResultV1
    {
        public readonly float LocalImpactX;
        public readonly float InitialCenterHeight;
        public readonly Vector3 IncomingVelocity;
        public readonly Vector3 FinalVelocity;
        public readonly Vector3 IncomingAngularVelocity;
        public readonly Vector3 FinalAngularVelocity;
        public readonly bool ContactDetected;
        public readonly bool ContinuedFlight;
        public readonly float KineticEnergyRatio;
        public readonly int SimulatedTicks;

        public NetImpactResultV1(
            float localImpactX,
            float initialCenterHeight,
            Vector3 incomingVelocity,
            Vector3 finalVelocity,
            Vector3 incomingAngularVelocity,
            Vector3 finalAngularVelocity,
            bool contactDetected,
            bool continuedFlight,
            float kineticEnergyRatio,
            int simulatedTicks)
        {
            LocalImpactX = localImpactX;
            InitialCenterHeight = initialCenterHeight;
            IncomingVelocity = incomingVelocity;
            FinalVelocity = finalVelocity;
            IncomingAngularVelocity = incomingAngularVelocity;
            FinalAngularVelocity = finalAngularVelocity;
            ContactDetected = contactDetected;
            ContinuedFlight = continuedFlight;
            KineticEnergyRatio = kineticEnergyRatio;
            SimulatedTicks = simulatedTicks;
        }
    }

    public static class CalibrationFixturesV1
    {
        private const float FixtureIsolationX = 1000f;
        public const float OfficialDropReferenceHeight = 1.981f;
        public const float OfficialMinimumReboundTopHeight = 0.762f;
        public const float OfficialMaximumReboundTopHeight = 0.864f;

        public static float ResolveInitialCenterHeight(
            float referenceHeight,
            float ballRadius,
            DropReleaseDatumV1 datum)
        {
            if (!FiniteMath.IsFinite(referenceHeight) || referenceHeight <= 0f ||
                !FiniteMath.IsFinite(ballRadius) || ballRadius <= 0f)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(referenceHeight),
                    "Drop height and ball radius must be finite and positive.");
            }

            return datum switch
            {
                DropReleaseDatumV1.BallTop => referenceHeight - ballRadius,
                DropReleaseDatumV1.BallCenter => referenceHeight,
                DropReleaseDatumV1.BallBottom => referenceHeight + ballRadius,
                _ => throw new ArgumentOutOfRangeException(nameof(datum))
            };
        }

        public static BallDropResultV1 RunBallDrop(
            SimulationConfigV1 configuration,
            DropReleaseDatumV1 datum,
            float releaseReferenceHeight = OfficialDropReferenceHeight,
            float maximumSeconds = 3f)
        {
            if (configuration == null)
            {
                throw new ArgumentNullException(nameof(configuration));
            }

            configuration.ValidateOrThrow();
            if (!FiniteMath.IsFinite(maximumSeconds) || maximumSeconds <= 0f)
            {
                throw new ArgumentOutOfRangeException(nameof(maximumSeconds));
            }

            var radius = configuration.BallDiameter / 2f;
            var initialCenterHeight = ResolveInitialCenterHeight(
                releaseReferenceHeight,
                radius,
                datum);
            if (initialCenterHeight <= radius)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(releaseReferenceHeight),
                    "The resolved ball centre must start above the surface.");
            }

            var root = new GameObject("BallDropCalibrationV1");
            PhysicsMaterial ballMaterial = null;
            PhysicsMaterial graniteMaterial = null;
            var previousSimulationMode = Physics.simulationMode;

            try
            {
                Physics.simulationMode = SimulationMode.Script;

                var surface = GameObject.CreatePrimitive(PrimitiveType.Cube);
                surface.name = "GraniteReferenceSurface";
                surface.transform.SetParent(root.transform);
                surface.transform.position =
                    new Vector3(FixtureIsolationX, -0.05f, 0f);
                surface.transform.localScale = new Vector3(1f, 0.1f, 1f);

                var ballObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                ballObject.name = "ReferenceBall";
                ballObject.transform.SetParent(root.transform);
                ballObject.transform.localScale =
                    Vector3.one * configuration.BallDiameter;
                ballObject.transform.position =
                    new Vector3(FixtureIsolationX, initialCenterHeight, 0f);
                var ball = ballObject.AddComponent<Rigidbody>();
                ball.mass = configuration.BallMass;
                ball.useGravity = false;
                ball.linearDamping = 0f;
                ball.angularDamping = 0f;
                ball.collisionDetectionMode =
                    CollisionDetectionMode.ContinuousDynamic;
                ball.interpolation = RigidbodyInterpolation.None;

                ballMaterial = CreatePhysicsMaterial(
                    "BallDropBallV1",
                    1f,
                    configuration.BallDynamicFriction);
                graniteMaterial = CreatePhysicsMaterial(
                    "GraniteReferenceV1",
                    configuration.GraniteRestitution,
                    0f);
                ballObject.GetComponent<Collider>().material = ballMaterial;
                surface.GetComponent<Collider>().material = graniteMaterial;

                Physics.SyncTransforms();

                var delta = EnvironmentVersion.PhysicsDeltaTime;
                var maximumTicks = Mathf.CeilToInt(maximumSeconds / delta);
                var previousPosition = ball.position;
                var previousVelocity = ball.linearVelocity;
                var impacted = false;
                var firstImpactTime = 0f;
                var preImpactEnergy = 0f;
                var postImpactEnergy = 0f;
                var reboundTopHeight = 0f;
                var reboundHorizontalDrift = 0f;

                for (var tick = 1; tick <= maximumTicks; tick++)
                {
                    var aerodynamic = AerodynamicModelV1.Evaluate(
                        ball.linearVelocity,
                        ball.angularVelocity,
                        configuration.AerodynamicParameters);
                    ball.AddForce(
                        aerodynamic.TotalForce +
                        (configuration.Gravity * ball.mass),
                        ForceMode.Force);
                    ball.angularVelocity *=
                        AerodynamicModelV1.AngularVelocityMultiplier(
                            delta,
                            configuration.AerodynamicParameters);
                    Physics.Simulate(delta);

                    var currentPosition = ball.position;
                    var currentVelocity = ball.linearVelocity;
                    if (!impacted &&
                        previousVelocity.y < 0f &&
                        currentVelocity.y > 0f)
                    {
                        impacted = true;
                        firstImpactTime = tick * delta;
                        preImpactEnergy = MechanicalEnergy(
                            previousPosition,
                            previousVelocity,
                            configuration,
                            radius);
                        postImpactEnergy = MechanicalEnergy(
                            currentPosition,
                            currentVelocity,
                            configuration,
                            radius);
                        reboundTopHeight = currentPosition.y + radius;
                    }
                    else if (impacted)
                    {
                        reboundTopHeight = Mathf.Max(
                            reboundTopHeight,
                            currentPosition.y + radius);
                        reboundHorizontalDrift = Mathf.Max(
                            reboundHorizontalDrift,
                            new Vector2(
                                currentPosition.x - FixtureIsolationX,
                                currentPosition.z).magnitude);
                        if (previousVelocity.y > 0f && currentVelocity.y <= 0f)
                        {
                            return new BallDropResultV1(
                                datum,
                                releaseReferenceHeight,
                                initialCenterHeight,
                                firstImpactTime,
                                reboundTopHeight,
                                reboundHorizontalDrift,
                                preImpactEnergy,
                                postImpactEnergy,
                                tick,
                                true);
                        }
                    }

                    previousPosition = currentPosition;
                    previousVelocity = currentVelocity;
                }

                return new BallDropResultV1(
                    datum,
                    releaseReferenceHeight,
                    initialCenterHeight,
                    firstImpactTime,
                    reboundTopHeight,
                    reboundHorizontalDrift,
                    preImpactEnergy,
                    postImpactEnergy,
                    maximumTicks,
                    false);
            }
            finally
            {
                Physics.simulationMode = previousSimulationMode;
                UnityEngine.Object.DestroyImmediate(root);
                if (ballMaterial != null)
                {
                    UnityEngine.Object.DestroyImmediate(ballMaterial);
                }

                if (graniteMaterial != null)
                {
                    UnityEngine.Object.DestroyImmediate(graniteMaterial);
                }
            }
        }

        public static PaddleImpactResultV1 RunPaddleImpact(
            SimulationConfigV1 configuration,
            float incomingBallSpeed,
            float paddleSpeed,
            float maximumSeconds = 1f)
        {
            return RunPaddleImpact(
                configuration,
                incomingBallSpeed,
                paddleSpeed,
                Vector2.zero,
                0f,
                Vector3.zero,
                maximumSeconds);
        }

        public static PaddleImpactResultV1 RunPaddleImpact(
            SimulationConfigV1 configuration,
            float incomingBallSpeed,
            float paddleSpeed,
            Vector2 impactOffset,
            float incomingTangentialSpeed,
            Vector3 incomingAngularVelocity,
            float maximumSeconds = 1f)
        {
            if (configuration == null)
            {
                throw new ArgumentNullException(nameof(configuration));
            }

            configuration.ValidateOrThrow();
            if (!FiniteMath.IsFinite(incomingBallSpeed) ||
                incomingBallSpeed <= 0f ||
                !FiniteMath.IsFinite(paddleSpeed) ||
                paddleSpeed < 0f ||
                !FiniteMath.IsFinite(impactOffset.x) ||
                !FiniteMath.IsFinite(impactOffset.y) ||
                !FiniteMath.IsFinite(incomingTangentialSpeed) ||
                !FiniteMath.IsFinite(incomingAngularVelocity) ||
                !FiniteMath.IsFinite(maximumSeconds) ||
                maximumSeconds <= 0f)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(incomingBallSpeed),
                    "Impact speeds and duration must be finite and valid.");
            }

            var root = new GameObject("PaddleImpactCalibrationV1");
            PhysicsMaterial ballMaterial = null;
            PhysicsMaterial paddleMaterial = null;
            Mesh paddleMesh = null;
            var previousSimulationMode = Physics.simulationMode;

            try
            {
                Physics.simulationMode = SimulationMode.Script;

                var paddleObject = new GameObject("ReferencePaddleFace");
                paddleObject.name = "ReferencePaddleFace";
                paddleObject.transform.SetParent(root.transform);
                paddleObject.transform.position =
                    new Vector3(FixtureIsolationX * 2f, 1f, 0f);
                var paddleCollider = PaddleCollisionGeometryV1.AddRoundedFace(
                    paddleObject,
                    configuration.PaddleFaceSize,
                    out paddleMesh);
                var paddle = paddleObject.AddComponent<Rigidbody>();
                paddle.useGravity = false;
                paddle.isKinematic = true;
                paddle.collisionDetectionMode =
                    CollisionDetectionMode.ContinuousSpeculative;
                paddle.interpolation = RigidbodyInterpolation.None;

                var ballObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                ballObject.name = "ReferenceImpactBall";
                ballObject.transform.SetParent(root.transform);
                const float initialNormalDistance = 0.5f;
                var estimatedContactTime =
                    (
                        initialNormalDistance -
                        (configuration.BallDiameter / 2f) -
                        (configuration.PaddleFaceSize.z / 2f)) /
                    incomingBallSpeed;
                ballObject.transform.position =
                    new Vector3(
                        (FixtureIsolationX * 2f) +
                        impactOffset.x -
                        (incomingTangentialSpeed * estimatedContactTime),
                        1f + impactOffset.y,
                        initialNormalDistance);
                ballObject.transform.localScale =
                    Vector3.one * configuration.BallDiameter;
                var ball = ballObject.AddComponent<Rigidbody>();
                ball.mass = configuration.BallMass;
                ball.useGravity = false;
                ball.linearDamping = 0f;
                ball.angularDamping = 0f;
                ball.collisionDetectionMode =
                    CollisionDetectionMode.ContinuousDynamic;
                ball.interpolation = RigidbodyInterpolation.None;
                var incomingVelocity =
                    new Vector3(incomingTangentialSpeed, 0f, -incomingBallSpeed);
                ball.linearVelocity = incomingVelocity;
                ball.angularVelocity = incomingAngularVelocity;

                ballMaterial = CreatePhysicsMaterial(
                    "PaddleImpactBallV1",
                    1f,
                    configuration.BallDynamicFriction);
                paddleMaterial = CreatePhysicsMaterial(
                    "PaddleImpactFaceV1",
                    configuration.PaddleRestitution,
                    configuration.PaddleDynamicFriction);
                ballObject.GetComponent<Collider>().material = ballMaterial;
                paddleCollider.material = paddleMaterial;
                Physics.SyncTransforms();

                var delta = EnvironmentVersion.PhysicsDeltaTime;
                var maximumTicks = Mathf.CeilToInt(maximumSeconds / delta);
                var priorRelativeSpeed =
                    ball.linearVelocity.z - paddleSpeed;

                for (var tick = 1; tick <= maximumTicks; tick++)
                {
                    paddle.MovePosition(
                        paddle.position +
                        (new Vector3(0f, 0f, paddleSpeed) * delta));
                    Physics.Simulate(delta);

                    var currentRelativeSpeed =
                        ball.linearVelocity.z - paddleSpeed;
                    if (priorRelativeSpeed < 0f && currentRelativeSpeed > 0f)
                    {
                        var incomingRelativeNormalSpeed = -priorRelativeSpeed;
                        var outgoingRelativeNormalSpeed = currentRelativeSpeed;
                        var effectiveRestitution =
                            outgoingRelativeNormalSpeed /
                            incomingRelativeNormalSpeed;
                        var energyRatio =
                            ball.linearVelocity.sqrMagnitude /
                            incomingVelocity.sqrMagnitude;
                        return new PaddleImpactResultV1(
                            incomingBallSpeed,
                            paddleSpeed,
                            impactOffset,
                            incomingVelocity,
                            ball.linearVelocity,
                            incomingAngularVelocity,
                            ball.angularVelocity,
                            incomingRelativeNormalSpeed,
                            outgoingRelativeNormalSpeed,
                            ball.linearVelocity.magnitude,
                            effectiveRestitution,
                            energyRatio,
                            Mathf.Abs(
                                ball.linearVelocity.x -
                                incomingVelocity.x),
                            Vector3.Distance(
                                ball.angularVelocity,
                                incomingAngularVelocity),
                            tick,
                            true);
                    }

                    priorRelativeSpeed = currentRelativeSpeed;
                }

                return new PaddleImpactResultV1(
                    incomingBallSpeed,
                    paddleSpeed,
                    impactOffset,
                    incomingVelocity,
                    ball.linearVelocity,
                    incomingAngularVelocity,
                    ball.angularVelocity,
                    0f,
                    0f,
                    ball.linearVelocity.magnitude,
                    0f,
                    0f,
                    Mathf.Abs(
                        ball.linearVelocity.x -
                        incomingVelocity.x),
                    Vector3.Distance(
                        ball.angularVelocity,
                        incomingAngularVelocity),
                    maximumTicks,
                    false);
            }
            finally
            {
                Physics.simulationMode = previousSimulationMode;
                UnityEngine.Object.DestroyImmediate(root);
                if (ballMaterial != null)
                {
                    UnityEngine.Object.DestroyImmediate(ballMaterial);
                }

                if (paddleMaterial != null)
                {
                    UnityEngine.Object.DestroyImmediate(paddleMaterial);
                }

                if (paddleMesh != null)
                {
                    UnityEngine.Object.DestroyImmediate(paddleMesh);
                }
            }
        }

        public static CourtImpactResultV1 RunCourtImpact(
            SimulationConfigV1 configuration,
            Vector3 incomingVelocity,
            Vector3 incomingAngularVelocity,
            float maximumSeconds = 2f)
        {
            if (configuration == null)
            {
                throw new ArgumentNullException(nameof(configuration));
            }

            configuration.ValidateOrThrow();
            if (!FiniteMath.IsFinite(incomingVelocity) ||
                incomingVelocity.y >= 0f ||
                !FiniteMath.IsFinite(incomingAngularVelocity) ||
                !FiniteMath.IsFinite(maximumSeconds) ||
                maximumSeconds <= 0f)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(incomingVelocity),
                    "Court impact inputs must be finite and approach the surface.");
            }

            var root = new GameObject("CourtImpactCalibrationV1");
            PhysicsMaterial ballMaterial = null;
            PhysicsMaterial courtMaterial = null;
            var previousSimulationMode = Physics.simulationMode;
            const float isolationX = FixtureIsolationX * 3f;
            var radius = configuration.BallDiameter / 2f;

            try
            {
                Physics.simulationMode = SimulationMode.Script;
                var surface = GameObject.CreatePrimitive(PrimitiveType.Cube);
                surface.name = "AcrylicReferenceSurfaceProvisional";
                surface.transform.SetParent(root.transform);
                surface.transform.position = new Vector3(isolationX, -0.05f, 0f);
                surface.transform.localScale = new Vector3(4f, 0.1f, 4f);

                var ballObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                ballObject.name = "CourtImpactBall";
                ballObject.transform.SetParent(root.transform);
                ballObject.transform.position = new Vector3(isolationX, 0.5f, 0f);
                ballObject.transform.localScale =
                    Vector3.one * configuration.BallDiameter;
                var ball = ballObject.AddComponent<Rigidbody>();
                ball.mass = configuration.BallMass;
                ball.useGravity = false;
                ball.linearDamping = 0f;
                ball.angularDamping = 0f;
                ball.collisionDetectionMode =
                    CollisionDetectionMode.ContinuousDynamic;
                ball.interpolation = RigidbodyInterpolation.None;
                ball.linearVelocity = incomingVelocity;
                ball.angularVelocity = incomingAngularVelocity;

                ballMaterial = CreatePhysicsMaterial(
                    "CourtImpactBallV1",
                    1f,
                    configuration.BallDynamicFriction);
                courtMaterial = CreatePhysicsMaterial(
                    "AcrylicCourtProvisionalV1",
                    configuration.CourtRestitution,
                    configuration.CourtDynamicFriction);
                ballObject.GetComponent<Collider>().material = ballMaterial;
                surface.GetComponent<Collider>().material = courtMaterial;
                Physics.SyncTransforms();

                var delta = EnvironmentVersion.PhysicsDeltaTime;
                var maximumTicks = Mathf.CeilToInt(maximumSeconds / delta);
                var priorPosition = ball.position;
                var priorVelocity = ball.linearVelocity;
                var impacted = false;
                var outgoingVelocity = Vector3.zero;
                var outgoingSpin = Vector3.zero;
                var reboundTop = 0f;
                var preEnergy = 0f;
                var postEnergy = 0f;
                var logicalContacts = 0;

                for (var tick = 1; tick <= maximumTicks; tick++)
                {
                    ApplyFlightForces(ball, configuration, delta);
                    Physics.Simulate(delta);
                    var currentPosition = ball.position;
                    var currentVelocity = ball.linearVelocity;

                    if (priorVelocity.y < 0f && currentVelocity.y > 0f)
                    {
                        logicalContacts++;
                        if (!impacted)
                        {
                            impacted = true;
                            outgoingVelocity = currentVelocity;
                            outgoingSpin = ball.angularVelocity;
                            preEnergy = MechanicalEnergy(
                                priorPosition,
                                priorVelocity,
                                configuration,
                                radius);
                            postEnergy = MechanicalEnergy(
                                currentPosition,
                                currentVelocity,
                                configuration,
                                radius);
                            reboundTop = currentPosition.y + radius;
                        }
                    }

                    if (impacted)
                    {
                        reboundTop = Mathf.Max(
                            reboundTop,
                            currentPosition.y + radius);
                        if (priorVelocity.y > 0f && currentVelocity.y <= 0f)
                        {
                            return new CourtImpactResultV1(
                                incomingVelocity,
                                outgoingVelocity,
                                incomingAngularVelocity,
                                outgoingSpin,
                                reboundTop,
                                preEnergy,
                                postEnergy,
                                logicalContacts,
                                tick,
                                true);
                        }
                    }

                    priorPosition = currentPosition;
                    priorVelocity = currentVelocity;
                }

                return new CourtImpactResultV1(
                    incomingVelocity,
                    outgoingVelocity,
                    incomingAngularVelocity,
                    outgoingSpin,
                    reboundTop,
                    preEnergy,
                    postEnergy,
                    logicalContacts,
                    maximumTicks,
                    false);
            }
            finally
            {
                Physics.simulationMode = previousSimulationMode;
                UnityEngine.Object.DestroyImmediate(root);
                if (ballMaterial != null)
                {
                    UnityEngine.Object.DestroyImmediate(ballMaterial);
                }

                if (courtMaterial != null)
                {
                    UnityEngine.Object.DestroyImmediate(courtMaterial);
                }
            }
        }

        public static NetImpactResultV1 RunNetImpact(
            SimulationConfigV1 configuration,
            float localImpactX,
            float initialCenterHeight,
            Vector3 incomingVelocity,
            Vector3 incomingAngularVelocity,
            float duration = 0.15f)
        {
            if (configuration == null)
            {
                throw new ArgumentNullException(nameof(configuration));
            }

            configuration.ValidateOrThrow();
            if (!FiniteMath.IsFinite(localImpactX) ||
                !FiniteMath.IsFinite(initialCenterHeight) ||
                initialCenterHeight <= 0f ||
                !FiniteMath.IsFinite(incomingVelocity) ||
                incomingVelocity.z <= 0f ||
                !FiniteMath.IsFinite(incomingAngularVelocity) ||
                !FiniteMath.IsFinite(duration) ||
                duration <= 0f)
            {
                throw new ArgumentOutOfRangeException(
                    nameof(incomingVelocity),
                    "Net impact inputs must be finite and move toward the net.");
            }

            var root = new GameObject("NetImpactCalibrationV1");
            PhysicsMaterial ballMaterial = null;
            PhysicsMaterial netMaterial = null;
            var previousSimulationMode = Physics.simulationMode;
            const float isolationX = FixtureIsolationX * 4f;

            try
            {
                Physics.simulationMode = SimulationMode.Script;
                var netRoot = new GameObject("RegulationSpanNet");
                netRoot.transform.SetParent(root.transform);
                netRoot.transform.position = new Vector3(isolationX, 0f, 0f);
                var netColliders =
                    PicklebotEnvironmentFactoryV1.CreateNet(netRoot.transform);

                var ballObject = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                ballObject.name = "NetImpactBall";
                ballObject.transform.SetParent(root.transform);
                ballObject.transform.position = new Vector3(
                    isolationX + localImpactX,
                    initialCenterHeight,
                    -0.5f);
                ballObject.transform.localScale =
                    Vector3.one * configuration.BallDiameter;
                var ball = ballObject.AddComponent<Rigidbody>();
                ball.mass = configuration.BallMass;
                ball.useGravity = false;
                ball.linearDamping = 0f;
                ball.angularDamping = 0f;
                ball.collisionDetectionMode =
                    CollisionDetectionMode.ContinuousDynamic;
                ball.interpolation = RigidbodyInterpolation.None;
                ball.linearVelocity = incomingVelocity;
                ball.angularVelocity = incomingAngularVelocity;

                ballMaterial = CreatePhysicsMaterial(
                    "NetImpactBallV1",
                    1f,
                    configuration.BallDynamicFriction);
                netMaterial = CreatePhysicsMaterial(
                    "RigidNetV1",
                    configuration.NetRestitution,
                    configuration.NetDynamicFriction);
                ballObject.GetComponent<Collider>().material = ballMaterial;
                foreach (var collider in netColliders)
                {
                    collider.material = netMaterial;
                }

                Physics.SyncTransforms();
                var delta = EnvironmentVersion.PhysicsDeltaTime;
                var maximumTicks = Mathf.CeilToInt(duration / delta);
                var contactDetected = false;
                var priorNormalVelocity = ball.linearVelocity.z;
                for (var tick = 1; tick <= maximumTicks; tick++)
                {
                    ApplyFlightForces(
                        ball,
                        configuration,
                        delta,
                        includeGravity: false);
                    Physics.Simulate(delta);
                    if (priorNormalVelocity > 0f && ball.linearVelocity.z < 0f)
                    {
                        contactDetected = true;
                    }

                    priorNormalVelocity = ball.linearVelocity.z;
                }

                var finalVelocity = ball.linearVelocity;
                var finalSpin = ball.angularVelocity;
                return new NetImpactResultV1(
                    localImpactX,
                    initialCenterHeight,
                    incomingVelocity,
                    finalVelocity,
                    incomingAngularVelocity,
                    finalSpin,
                    contactDetected,
                    finalVelocity.sqrMagnitude > 0.0001f,
                    finalVelocity.sqrMagnitude / incomingVelocity.sqrMagnitude,
                    maximumTicks);
            }
            finally
            {
                Physics.simulationMode = previousSimulationMode;
                UnityEngine.Object.DestroyImmediate(root);
                if (ballMaterial != null)
                {
                    UnityEngine.Object.DestroyImmediate(ballMaterial);
                }

                if (netMaterial != null)
                {
                    UnityEngine.Object.DestroyImmediate(netMaterial);
                }
            }
        }

        private static void ApplyFlightForces(
            Rigidbody ball,
            SimulationConfigV1 configuration,
            float delta,
            bool includeGravity = true)
        {
            var aerodynamic = AerodynamicModelV1.Evaluate(
                ball.linearVelocity,
                ball.angularVelocity,
                configuration.AerodynamicParameters);
            ball.AddForce(
                aerodynamic.TotalForce +
                (includeGravity
                    ? configuration.Gravity * ball.mass
                    : Vector3.zero),
                ForceMode.Force);
            ball.angularVelocity *=
                AerodynamicModelV1.AngularVelocityMultiplier(
                    delta,
                    configuration.AerodynamicParameters);
        }

        private static PhysicsMaterial CreatePhysicsMaterial(
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

        private static float MechanicalEnergy(
            Vector3 position,
            Vector3 velocity,
            SimulationConfigV1 configuration,
            float radius)
        {
            var kinetic =
                0.5f * configuration.BallMass * velocity.sqrMagnitude;
            var height = Mathf.Max(0f, position.y - radius);
            var potential =
                configuration.BallMass * configuration.Gravity.magnitude * height;
            return kinetic + potential;
        }
    }
}
