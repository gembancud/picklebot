using System;
using System.Collections.Generic;
using System.Linq;
using Picklebot.Core;
using UnityEngine;

namespace Picklebot.Simulation
{
    [DisallowMultipleComponent]
    public sealed class PicklebotEnvironmentV1 : MonoBehaviour, IPicklebotEnvironmentV1
    {
        private readonly struct RawContact
        {
            public readonly CollisionEntityKindV0 Kind;
            public readonly int EntityId;
            public readonly Vector3 Position;
            public readonly Vector3 Normal;
            public readonly float Impulse;

            public RawContact(
                CollisionEntityKindV0 kind,
                int entityId,
                Vector3 position,
                Vector3 normal,
                float impulse)
            {
                Kind = kind;
                EntityId = entityId;
                Position = position;
                Normal = normal;
                Impulse = impulse;
            }
        }

        [Header("Contract dependencies")]
        [SerializeField] private SimulationConfigV1 configuration;
        [SerializeField] private Rigidbody ball;
        [SerializeField] private Rigidbody paddle;
        [SerializeField] private Collider ballCollider;
        [SerializeField] private Collider paddleCollider;
        [SerializeField] private Collider floorCollider;
        [SerializeField] private Collider netCollider;

        [Header("Versioned material assets")]
        [SerializeField] private PhysicsMaterial ballMaterial;
        [SerializeField] private PhysicsMaterial paddleMaterial;
        [SerializeField] private PhysicsMaterial courtMaterial;
        [SerializeField] private PhysicsMaterial netMaterial;

        private readonly EpisodeStateMachineV0 stateMachine = new();
        private readonly ContactLedgerV0 contactLedger = new();
        private readonly List<EnvironmentEventV0> stepEvents = new();
        private readonly List<RawContact> rawContacts = new();
        private readonly List<Vector3> trajectory = new();
        private readonly List<EnvironmentEventV0> recentEvents = new();

        private ScenarioParametersV0 scenario;
        private RewardFeaturesV0 stepFeatures;
        private ulong episodeId;
        private ulong physicsTick;
        private int eventSequence;
        private float elapsedTime;
        private LastTouchV0 lastTouch;
        private int controlledPaddleContacts;
        private int ballFloorContacts;
        private Vector3 paddleLinearVelocityWorld;
        private Vector3 paddleAngularVelocityWorld;
        private TerminationReasonV0 terminationReason;
        private AerodynamicForcesV1 lastAerodynamicForces;

        public EpisodeStateV0 State => stateMachine.State;
        public EpisodeManifestV0 CurrentManifest { get; private set; }
        public StepResultV0 LastStepResult { get; private set; }
        public IReadOnlyList<Vector3> Trajectory => trajectory;
        public IReadOnlyList<EnvironmentEventV0> RecentEvents => recentEvents;
        public SimulationConfigV1 Configuration => configuration;
        public TerminationReasonV0 TerminationReason => terminationReason;
        public Rigidbody Ball => ball;
        public Rigidbody Paddle => paddle;
        public Vector3 PaddleCommandLinearVelocityWorld => paddleLinearVelocityWorld;
        public Vector3 PaddleCommandAngularVelocityWorld => paddleAngularVelocityWorld;
        public AerodynamicForcesV1 LastAerodynamicForces => lastAerodynamicForces;

        public void Configure(
            SimulationConfigV1 simulationConfiguration,
            Rigidbody ballBody,
            Rigidbody paddleBody,
            Collider configuredPaddle,
            Collider configuredFloor,
            Collider configuredNet,
            PhysicsMaterial configuredBallMaterial = null,
            PhysicsMaterial configuredPaddleMaterial = null,
            PhysicsMaterial configuredCourtMaterial = null,
            PhysicsMaterial configuredNetMaterial = null)
        {
            configuration = simulationConfiguration;
            ball = ballBody;
            paddle = paddleBody;
            ballCollider = ballBody == null ? null : ballBody.GetComponent<Collider>();
            paddleCollider = configuredPaddle;
            floorCollider = configuredFloor;
            netCollider = configuredNet;
            ballMaterial = configuredBallMaterial;
            paddleMaterial = configuredPaddleMaterial;
            courtMaterial = configuredCourtMaterial;
            netMaterial = configuredNetMaterial;
            InitializeDependencies();
        }

        private void Awake()
        {
            InitializeDependencies();
        }

        public ObservationV0 Reset(ResetRequestV0 request)
        {
            EnsureConfigured();
            stateMachine.BeginReset();

            episodeId++;
            physicsTick = 0;
            eventSequence = 0;
            elapsedTime = 0f;
            lastTouch = LastTouchV0.None;
            controlledPaddleContacts = 0;
            ballFloorContacts = 0;
            terminationReason = TerminationReasonV0.None;
            lastAerodynamicForces = default;
            paddleLinearVelocityWorld = Vector3.zero;
            paddleAngularVelocityWorld = Vector3.zero;
            stepFeatures = default;
            stepEvents.Clear();
            rawContacts.Clear();
            contactLedger.Clear();
            trajectory.Clear();
            recentEvents.Clear();
            LastStepResult = null;

            scenario = ScenarioCatalogV0.Generate(request, configuration);
            CurrentManifest = new EpisodeManifestV0
            {
                EnvironmentVersion = SimulationConfigV1.EnvironmentVersion,
                ConfigurationVersion = SimulationConfigV1.CanonicalVersion,
                ConfigurationHash = configuration.ConfigurationHash,
                PhysicsSettingsHash = PhysicsSettingsIdentityV0.Hash(),
                EpisodeId = episodeId,
                Seed = request.Seed,
                ScenarioId = request.ScenarioId,
                Difficulty = request.Difficulty,
                Parameters = scenario,
                Overrides = request.Overrides.ToArray()
            };

            ApplyBodyState();
            Physics.SyncTransforms();
            trajectory.Add(ball.position);

            stateMachine.CompleteReset();
            return CreateObservation();
        }

        public StepResultV0 Step(PaddleActionV0 action)
        {
            EnsureConfigured();
            if (State == EpisodeStateV0.Terminal)
            {
                throw new InvalidOperationException(
                    "Step cannot be called after Terminal; Reset is required.");
            }

            if (State is not (EpisodeStateV0.Ready or EpisodeStateV0.Running))
            {
                throw new InvalidOperationException($"Cannot step while state is {State}.");
            }

            stepEvents.Clear();
            stepFeatures = default;

            var processed = ActionProcessorV0.Process(action, configuration);
            if (!processed.IsValid)
            {
                Terminate(TerminationReasonV0.InvalidAction, "non-finite action");
                return CompleteStep();
            }

            if (State == EpisodeStateV0.Ready)
            {
                stateMachine.BeginRunning();
                lastTouch = LastTouchV0.Launcher;
                QueueEvent(
                    EnvironmentEventKindV0.EpisodeStarted,
                    0,
                    ball.position,
                    Vector3.zero,
                    0f,
                    CurrentManifest.ScenarioId);
                QueueEvent(
                    EnvironmentEventKindV0.BallLaunched,
                    1,
                    ball.position,
                    ball.linearVelocity.normalized,
                    ball.linearVelocity.magnitude,
                    CurrentManifest.ScenarioId);
            }

            if (processed.WasClamped)
            {
                stepFeatures.ActionClampCount++;
                QueueEvent(
                    EnvironmentEventKindV0.ActionClamped,
                    2,
                    paddle.position,
                    Vector3.zero,
                    0f,
                    "finite action clamped to [-1,1]");
            }

            for (var index = 0;
                 index < EnvironmentVersion.DefaultTicksPerAction &&
                 State != EpisodeStateV0.Terminal;
                 index++)
            {
                StepPhysics(processed);
            }

            return CompleteStep();
        }

        public void AbortForTest()
        {
            if (State is EpisodeStateV0.Ready or EpisodeStateV0.Running)
            {
                Terminate(TerminationReasonV0.TestAbort, "explicit test abort");
            }
        }

        public void ReportContact(
            CollisionIdentityV0 identity,
            Vector3 position,
            Vector3 normal,
            float impulse)
        {
            if (State != EpisodeStateV0.Running)
            {
                return;
            }

            rawContacts.Add(new RawContact(
                identity == null ? CollisionEntityKindV0.Other : identity.Kind,
                identity == null ? 1000 : identity.StableEntityId,
                position,
                normal,
                impulse));
        }

        private void InitializeDependencies()
        {
            if (ball != null)
            {
                var reporter = ball.GetComponent<BallContactReporterV1>();
                if (reporter == null)
                {
                    reporter = ball.gameObject.AddComponent<BallContactReporterV1>();
                }

                reporter.Configure(this);
            }

            if (configuration != null && ball != null && paddle != null)
            {
                ApplyConfiguration();
            }
        }

        private void EnsureConfigured()
        {
            if (configuration == null || ball == null || paddle == null ||
                ballCollider == null || paddleCollider == null ||
                floorCollider == null || netCollider == null)
            {
                throw new InvalidOperationException(
                    "PicklebotEnvironmentV1 is missing required configuration or scene references.");
            }

            configuration.ValidateOrThrow();
            if (Mathf.Abs(Time.fixedDeltaTime - EnvironmentVersion.PhysicsDeltaTime) > 0.0000001f)
            {
                throw new InvalidOperationException(
                    $"Fixed timestep must be {EnvironmentVersion.PhysicsDeltaTime:R}.");
            }

            Physics.simulationMode = SimulationMode.Script;
        }

        private void ApplyConfiguration()
        {
            configuration.ValidateOrThrow();

            ball.mass = configuration.BallMass;
            ball.transform.localScale = Vector3.one * configuration.BallDiameter;
            ball.linearDamping = 0f;
            ball.angularDamping = 0f;
            ball.useGravity = false;
            ball.isKinematic = false;
            ball.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            ball.interpolation = RigidbodyInterpolation.None;
            ball.maxAngularVelocity = 200f;

            paddle.useGravity = false;
            paddle.isKinematic = true;
            paddle.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            paddle.interpolation = RigidbodyInterpolation.None;

            if (ballCollider != null && ballMaterial != null)
            {
                ConfigureMaterial(
                    ballMaterial,
                    1f,
                    configuration.BallDynamicFriction);
                ballCollider.material = ballMaterial;
            }

            if (paddleCollider != null && paddleMaterial != null)
            {
                ConfigureMaterial(
                    paddleMaterial,
                    configuration.PaddleRestitution,
                    configuration.PaddleDynamicFriction);
                var identity =
                    paddleCollider.GetComponentInParent<CollisionIdentityV0>();
                var colliders = identity == null
                    ? new[] { paddleCollider }
                    : identity.GetComponentsInChildren<Collider>();
                foreach (var current in colliders)
                {
                    if (current.GetComponentInParent<CollisionIdentityV0>() == identity)
                    {
                        current.material = paddleMaterial;
                    }
                }
            }

            if (floorCollider != null && courtMaterial != null)
            {
                ConfigureMaterial(
                    courtMaterial,
                    configuration.CourtRestitution,
                    configuration.CourtDynamicFriction);
                floorCollider.material = courtMaterial;
            }

            if (netCollider != null && netMaterial != null)
            {
                ConfigureMaterial(
                    netMaterial,
                    configuration.NetRestitution,
                    configuration.NetDynamicFriction);
                var identity = netCollider.GetComponentInParent<CollisionIdentityV0>();
                var colliders = identity == null
                    ? new[] { netCollider }
                    : identity.GetComponentsInChildren<Collider>();
                foreach (var current in colliders)
                {
                    current.material = netMaterial;
                }
            }
        }

        private static void ConfigureMaterial(
            PhysicsMaterial material,
            float bounciness,
            float friction)
        {
            material.bounciness = bounciness;
            material.dynamicFriction = friction;
            material.staticFriction = friction;
            material.bounceCombine = PhysicsMaterialCombine.Multiply;
            material.frictionCombine = PhysicsMaterialCombine.Multiply;
        }

        private void ApplyBodyState()
        {
            ball.position = scenario.BallPosition;
            ball.rotation = FiniteMath.Canonicalize(scenario.BallRotation);
            ball.linearVelocity = scenario.BallLinearVelocity;
            ball.angularVelocity = scenario.BallAngularVelocity;
            ball.WakeUp();

            paddle.position = scenario.PaddlePosition;
            paddle.rotation = FiniteMath.Canonicalize(scenario.PaddleRotation);
            paddle.WakeUp();
        }

        private void StepPhysics(ProcessedPaddleActionV0 action)
        {
            physicsTick++;
            eventSequence = 0;
            rawContacts.Clear();

            paddleLinearVelocityWorld = paddle.rotation * action.LinearVelocityLocal;
            paddleAngularVelocityWorld = paddle.rotation * action.AngularVelocityLocal;

            var delta = EnvironmentVersion.PhysicsDeltaTime;
            paddle.MovePosition(paddle.position + (paddleLinearVelocityWorld * delta));
            var angularDelta = Quaternion.Euler(
                paddleAngularVelocityWorld * (Mathf.Rad2Deg * delta));
            paddle.MoveRotation(FiniteMath.Canonicalize(angularDelta * paddle.rotation));

            lastAerodynamicForces = AerodynamicModelV1.Evaluate(
                ball.linearVelocity,
                ball.angularVelocity,
                configuration.AerodynamicParameters);
            ball.AddForce(
                lastAerodynamicForces.TotalForce +
                (configuration.Gravity * ball.mass),
                ForceMode.Force);
            ball.angularVelocity *= AerodynamicModelV1.AngularVelocityMultiplier(
                delta,
                configuration.AerodynamicParameters);

            Physics.Simulate(delta);
            elapsedTime = physicsTick * EnvironmentVersion.PhysicsDeltaTime;
            stepFeatures.ElapsedTime = elapsedTime;

            if (!BodiesAreFinite())
            {
                rawContacts.Clear();
                stepFeatures.InvalidState = 1f;
                QueueEvent(
                    EnvironmentEventKindV0.InvalidNumericState,
                    -1,
                    Vector3.zero,
                    Vector3.zero,
                    0f,
                    "non-finite rigidbody state");
                Terminate(TerminationReasonV0.InvalidNumericState, "non-finite rigidbody state");
                return;
            }

            ProcessRawContacts();
            if (State == EpisodeStateV0.Terminal)
            {
                return;
            }

            if (!IsInsidePlayableVolume(ball.position))
            {
                QueueEvent(
                    EnvironmentEventKindV0.BallExitedPlayableVolume,
                    3,
                    ball.position,
                    Vector3.zero,
                    0f,
                    "ball outside configured playable volume");
                Terminate(TerminationReasonV0.PlayableVolumeExit, "playable volume exit");
                return;
            }

            if (elapsedTime + 0.000001f >= scenario.MaximumEpisodeSeconds)
            {
                Terminate(TerminationReasonV0.Timeout, "scenario time limit");
            }

            trajectory.Add(ball.position);
            if (trajectory.Count > 2048)
            {
                trajectory.RemoveAt(0);
            }
        }

        private void ProcessRawContacts()
        {
            foreach (var contact in rawContacts
                         .OrderBy(value => value.EntityId)
                         .ThenBy(value => value.Position.x)
                         .ThenBy(value => value.Position.y)
                         .ThenBy(value => value.Position.z))
            {
                if (!contactLedger.ShouldRecord(
                        contact.EntityId,
                        physicsTick,
                        configuration.ContactMinimumSeparationTicks))
                {
                    continue;
                }

                switch (contact.Kind)
                {
                    case CollisionEntityKindV0.ControlledPaddle:
                        ApplyPaddleSpinTransfer(contact);
                        controlledPaddleContacts++;
                        stepFeatures.PaddleContactCount++;
                        lastTouch = LastTouchV0.ControlledPaddle;
                        QueueEvent(
                            EnvironmentEventKindV0.BallPaddleContact,
                            contact.EntityId,
                            contact.Position,
                            contact.Normal,
                            contact.Impulse);
                        break;
                    case CollisionEntityKindV0.Net:
                        stepFeatures.NetContactCount++;
                        lastTouch = LastTouchV0.Net;
                        QueueEvent(
                            EnvironmentEventKindV0.BallNetContact,
                            contact.EntityId,
                            contact.Position,
                            contact.Normal,
                            contact.Impulse);
                        break;
                    case CollisionEntityKindV0.Floor:
                        ProcessFloorContact(contact);
                        return;
                    default:
                        lastTouch = LastTouchV0.Other;
                        break;
                }
            }
        }

        private void ApplyPaddleSpinTransfer(RawContact contact)
        {
            var paddlePointVelocity =
                paddleLinearVelocityWorld +
                Vector3.Cross(
                    paddleAngularVelocityWorld,
                    contact.Position - paddle.position);
            var transfer = PaddleSpinTransferV1.Evaluate(
                ball.position,
                ball.linearVelocity,
                ball.angularVelocity,
                paddlePointVelocity,
                contact.Position,
                contact.Normal,
                configuration);
            ball.linearVelocity = transfer.LinearVelocity;
            ball.angularVelocity = transfer.AngularVelocity;
        }

        private void ProcessFloorContact(RawContact contact)
        {
            ballFloorContacts++;
            lastTouch = LastTouchV0.Floor;
            var projected = new Vector3(contact.Position.x, 0f, contact.Position.z);
            QueueEvent(
                EnvironmentEventKindV0.BallFloorContact,
                contact.EntityId,
                projected,
                contact.Normal,
                contact.Impulse);

            var zone = CourtGeometryV1.ClassifyFloorContact(projected);
            QueueEvent(
                EnvironmentEventKindV0.BallEnteredZone,
                200 + (int)zone,
                projected,
                Vector3.up,
                0f,
                zone.ToString());

            if (CourtGeometryV1.IsFarCourt(zone))
            {
                stepFeatures.FarCourtLanding = 1f;
                stepFeatures.TargetDistanceAtLanding =
                    Vector2.Distance(
                        new Vector2(projected.x, projected.z),
                        new Vector2(scenario.TargetPosition.x, scenario.TargetPosition.z));
                Terminate(TerminationReasonV0.FarCourtLanding, zone.ToString());
            }
            else if (CourtGeometryV1.IsNearCourt(zone))
            {
                stepFeatures.NearCourtLanding = 1f;
                Terminate(TerminationReasonV0.NearCourtLanding, zone.ToString());
            }
            else
            {
                stepFeatures.OutLanding = 1f;
                Terminate(TerminationReasonV0.OutOfBoundsLanding, zone.ToString());
            }
        }

        private bool IsInsidePlayableVolume(Vector3 position)
        {
            return Mathf.Abs(position.x) <=
                       CourtGeometryV1.HalfWidth + configuration.PlayableHorizontalMargin &&
                   Mathf.Abs(position.z) <=
                       CourtGeometryV1.HalfLength + configuration.PlayableHorizontalMargin &&
                   position.y >= -configuration.PlayableFloorMargin &&
                   position.y <= configuration.PlayableCeiling;
        }

        private bool BodiesAreFinite()
        {
            return FiniteMath.IsFinite(ball.position) &&
                   FiniteMath.IsFinite(ball.rotation) &&
                   FiniteMath.IsFinite(ball.linearVelocity) &&
                   FiniteMath.IsFinite(ball.angularVelocity) &&
                   FiniteMath.IsFinite(paddle.position) &&
                   FiniteMath.IsFinite(paddle.rotation) &&
                   FiniteMath.IsFinite(paddleLinearVelocityWorld) &&
                   FiniteMath.IsFinite(paddleAngularVelocityWorld);
        }

        private void Terminate(TerminationReasonV0 reason, string detail)
        {
            if (!stateMachine.TryTerminate(reason))
            {
                return;
            }

            terminationReason = reason;
            QueueEvent(
                EnvironmentEventKindV0.EpisodeTerminated,
                9999,
                ball == null ? Vector3.zero : ball.position,
                Vector3.zero,
                0f,
                $"{reason}:{detail}");
        }

        private void QueueEvent(
            EnvironmentEventKindV0 kind,
            int entityId,
            Vector3 position,
            Vector3 normal,
            float magnitude,
            string detail = "")
        {
            var current = new EnvironmentEventV0(
                physicsTick,
                eventSequence++,
                kind,
                entityId,
                position,
                normal,
                magnitude,
                detail);
            stepEvents.Add(current);
            recentEvents.Add(current);
            if (recentEvents.Count > 32)
            {
                recentEvents.RemoveAt(0);
            }
        }

        private StepResultV0 CompleteStep()
        {
            var observation = CreateObservation();
            if (!ObservationValidatorV0.IsFinite(observation) &&
                State != EpisodeStateV0.Terminal)
            {
                stepFeatures.InvalidState = 1f;
                QueueEvent(
                    EnvironmentEventKindV0.InvalidNumericState,
                    -1,
                    Vector3.zero,
                    Vector3.zero,
                    0f,
                    "non-finite observation");
                Terminate(TerminationReasonV0.InvalidNumericState, "non-finite observation");
                observation = CreateObservation();
            }

            var orderedEvents = OrderStepEvents();
            LastStepResult = new StepResultV0(
                observation,
                orderedEvents,
                stepFeatures,
                State == EpisodeStateV0.Terminal,
                terminationReason);
            return LastStepResult;
        }

        private EnvironmentEventV0[] OrderStepEvents()
        {
            var ordered = stepEvents
                .OrderBy(value => value.PhysicsTick)
                .ThenBy(value => EventOrderingV0.Phase(value.Kind))
                .ThenBy(value => value.EntityId)
                .ThenBy(value => value.Sequence)
                .ToArray();

            var lastTick = ulong.MaxValue;
            var sequence = 0;
            for (var index = 0; index < ordered.Length; index++)
            {
                var current = ordered[index];
                if (current.PhysicsTick != lastTick)
                {
                    lastTick = current.PhysicsTick;
                    sequence = 0;
                }

                ordered[index] = new EnvironmentEventV0(
                    current.PhysicsTick,
                    sequence++,
                    current.Kind,
                    current.EntityId,
                    current.Position,
                    current.Normal,
                    current.Magnitude,
                    current.Detail);
            }

            return ordered;
        }

        private ObservationV0 CreateObservation()
        {
            var ballSnapshot = new KinematicSnapshotV0
            {
                PositionWorld = ball.position,
                RotationWorld = FiniteMath.Canonicalize(ball.rotation),
                LinearVelocityWorld = ball.linearVelocity,
                AngularVelocityWorld = ball.angularVelocity
            };
            var paddleSnapshot = new KinematicSnapshotV0
            {
                PositionWorld = paddle.position,
                RotationWorld = FiniteMath.Canonicalize(paddle.rotation),
                LinearVelocityWorld = paddleLinearVelocityWorld,
                AngularVelocityWorld = paddleAngularVelocityWorld
            };

            return new ObservationV0
            {
                EnvironmentVersion = SimulationConfigV1.EnvironmentVersion,
                EpisodeId = episodeId,
                Seed = CurrentManifest == null ? 0UL : CurrentManifest.Seed,
                ScenarioId = CurrentManifest == null ? string.Empty : CurrentManifest.ScenarioId,
                PhysicsTick = physicsTick,
                ElapsedTime = elapsedTime,
                Ball = ballSnapshot,
                Paddle = paddleSnapshot,
                BallPositionFromPaddle = ball.position - paddle.position,
                BallVelocityFromPaddle = ball.linearVelocity - paddleLinearVelocityWorld,
                Episode = new EpisodeSnapshotV0
                {
                    State = State,
                    LastTouch = lastTouch,
                    ControlledPaddleContacts = controlledPaddleContacts,
                    BallFloorContacts = ballFloorContacts
                }
            };
        }
    }
}
