using System;
using System.Collections.Generic;
using System.Text;
using Picklebot.Core;
using Picklebot.Simulation;
using UnityEngine;

namespace Picklebot.Museum
{
    [DisallowMultipleComponent]
    public sealed class PhysicsMuseumControllerV1 : MonoBehaviour
    {
        private const int MaximumMuseumReboundTicks = 600;
        private const float ReboundRiseVelocityThreshold = 0.02f;

        private static readonly float[] PlaybackSpeeds = { 0.25f, 0.5f, 1f };
        private static readonly Color[] TraceColors =
        {
            new(1f, 0.82f, 0.18f, 1f),
            new(1f, 0.34f, 0.26f, 1f),
            new(0.18f, 0.88f, 1f, 1f)
        };

        [Header("Scene")]
        [SerializeField] private Camera museumCamera;

        [Header("Committed visual assets")]
        [SerializeField] private Material courtMaterial;
        [SerializeField] private Material ballMaterial;
        [SerializeField] private Material lineMaterial;
        [SerializeField] private Material paddleMaterial;
        [SerializeField] private Material netMaterial;

        private readonly List<Material> runtimeMaterials = new();
        private readonly List<Texture2D> runtimeTextures = new();
        private readonly List<GameObject> contactMarkers = new();
        private readonly List<Vector3> reboundTrace = new();
        private readonly LineRenderer[] traces = new LineRenderer[3];

        private PicklebotEnvironmentFixtureV1 fixture;
        private Transform presentationRoot;
        private LineRenderer spinAxis;
        private LineRenderer reboundMarker;
        private bool museumReboundStarted;
        private bool museumReboundInProgress;
        private bool museumReboundCompleted;
        private bool museumReboundHasRisen;
        private int museumReboundTicks;
        private float museumReboundApexTopHeight;
        private ObservationV0 observation;
        private StepResultV0 lastResult;
        private PhysicsMuseumStationV1 selectedStation;
        private int selectedVariant;
        private int playbackSpeedIndex = 2;
        private float simulationAccumulator;
        private bool isRunning;
        private bool isPaused;
        private bool initialized;
        private string lastContact = "none";
        private int completedSpinTraces;
        private BallDropResultV1 dropMeasurement;
        private CourtImpactResultV1 courtMeasurement;
        private NetImpactResultV1 netMeasurement;
        private bool hasDropMeasurement;
        private bool hasCourtMeasurement;
        private bool hasNetMeasurement;
        private GUIStyle titleStyle;
        private GUIStyle subtitleStyle;
        private GUIStyle tabStyle;
        private GUIStyle activeTabStyle;
        private GUIStyle panelStyle;
        private GUIStyle bodyStyle;
        private GUIStyle metricStyle;
        private GUIStyle warningStyle;
        private GUIStyle buttonStyle;

        public bool IsInitialized => initialized;
        public bool IsRunning => isRunning;
        public bool IsPaused => isPaused;
        public PhysicsMuseumStationV1 SelectedStation => selectedStation;
        public int SelectedVariant => selectedVariant;
        public float PlaybackSpeed => PlaybackSpeeds[playbackSpeedIndex];
        public PicklebotEnvironmentV1 Environment => fixture?.Environment;
        public int CompletedSpinTraces => completedSpinTraces;
        public int ActiveTracePointCount =>
            traces[selectedStation == PhysicsMuseumStationV1.SpinFlight
                ? selectedVariant
                : 0]?.positionCount ?? 0;
        public ObservationV0 CurrentObservation => observation;
        public bool HasMuseumPhysicsRebound => museumReboundStarted;
        public bool MuseumPhysicsReboundInProgress => museumReboundInProgress;
        public bool MuseumPhysicsReboundCompleted => museumReboundCompleted;
        public float MuseumPhysicsReboundApexTopHeight =>
            museumReboundApexTopHeight;
        public int MuseumPhysicsReboundPointCount => reboundTrace.Count;
        public int MuseumPhysicsReboundTicks => museumReboundTicks;

        private void Start()
        {
            Initialize();
        }

        private void Update()
        {
            if (!initialized)
            {
                return;
            }

            HandleKeyboardInput();
            SmoothCamera();
            if (!isRunning || isPaused)
            {
                UpdatePresentation();
                return;
            }

            var actionSeconds =
                EnvironmentVersion.PhysicsDeltaTime *
                EnvironmentVersion.DefaultTicksPerAction;
            simulationAccumulator +=
                Time.unscaledDeltaTime * PlaybackSpeeds[playbackSpeedIndex];
            var steps = 0;
            while (simulationAccumulator >= actionSeconds && steps < 8)
            {
                simulationAccumulator -= actionSeconds;
                AdvanceSimulation(ReadManualAction());
                steps++;
                if (!isRunning || isPaused)
                {
                    break;
                }
            }

            UpdatePresentation();
        }

        private void OnDestroy()
        {
            fixture?.Destroy();
            fixture = null;
            foreach (var material in runtimeMaterials)
            {
                if (material != null)
                {
                    DestroyImmediate(material);
                }
            }

            foreach (var texture in runtimeTextures)
            {
                if (texture != null)
                {
                    DestroyImmediate(texture);
                }
            }

            runtimeMaterials.Clear();
            runtimeTextures.Clear();
            contactMarkers.Clear();
            reboundTrace.Clear();
            Array.Clear(traces, 0, traces.Length);
            presentationRoot = null;
            spinAxis = null;
            reboundMarker = null;
            museumReboundStarted = false;
            museumReboundInProgress = false;
            museumReboundCompleted = false;
            museumReboundHasRisen = false;
            museumReboundTicks = 0;
            museumReboundApexTopHeight = 0f;
            initialized = false;
            isRunning = false;
            isPaused = false;
            titleStyle = null;
            subtitleStyle = null;
            tabStyle = null;
            activeTabStyle = null;
            panelStyle = null;
            bodyStyle = null;
            metricStyle = null;
            warningStyle = null;
            buttonStyle = null;
        }

        public void Initialize()
        {
            if (initialized && fixture != null)
            {
                return;
            }

            initialized = false;
            PhysicsMuseumProtocolV1.ValidateOrThrow();
            fixture = PicklebotEnvironmentFactoryV1.Create(
                "PhysicsMuseumEnvV1");
            fixture.Root.transform.SetParent(transform, true);
            presentationRoot =
                new GameObject("MuseumPresentationOnly").transform;
            presentationRoot.SetParent(transform, false);

            if (museumCamera == null)
            {
                museumCamera = Camera.main;
            }

            ConfigureCamera();
            ApplyVisualMaterials();
            CreateCourtPresentation();
            CreateTrajectoryRenderers();
            CreateSpinAxis();
            CreateReboundMarker();
            initialized = true;
            SelectStation(PhysicsMuseumStationV1.DropRebound);
        }

        public void SelectStation(PhysicsMuseumStationV1 station)
        {
            EnsureInitialized();
            var definition = PhysicsMuseumProtocolV1.Definition(station);
            selectedStation = station;
            selectedVariant = 0;
            completedSpinTraces = 0;
            isRunning = false;
            isPaused = false;
            simulationAccumulator = 0f;
            lastContact = "none";
            ClearTraces();
            ClearContactMarkers();
            MeasureStation();
            ResetEnvironment();
            SetCameraImmediate(definition);
            UpdatePresentation();
        }

        public void LaunchStation()
        {
            EnsureInitialized();
            if (selectedStation == PhysicsMuseumStationV1.SpinFlight)
            {
                selectedVariant = 0;
                completedSpinTraces = 0;
                ClearTraces();
            }
            else
            {
                ClearTrace(traces[0]);
            }

            ClearContactMarkers();
            lastContact = "none";
            ResetEnvironment();
            isRunning = true;
            isPaused = false;
            simulationAccumulator = 0f;
        }

        public void ResetStation()
        {
            EnsureInitialized();
            isRunning = false;
            isPaused = false;
            simulationAccumulator = 0f;
            ClearTraces();
            ClearContactMarkers();
            ResetEnvironment();
            UpdatePresentation();
        }

        public void TogglePause()
        {
            EnsureInitialized();
            isPaused = !isPaused;
        }

        public void CyclePlaybackSpeed()
        {
            EnsureInitialized();
            playbackSpeedIndex =
                (playbackSpeedIndex + 1) % PlaybackSpeeds.Length;
        }

        public void CycleVariant()
        {
            EnsureInitialized();
            var definition =
                PhysicsMuseumProtocolV1.Definition(selectedStation);
            if (definition.VariantCount <= 1 ||
                selectedStation == PhysicsMuseumStationV1.SpinFlight)
            {
                return;
            }

            selectedVariant =
                (selectedVariant + 1) % definition.VariantCount;
            ResetStation();
            MeasureStation();
        }

        public bool AdvanceForTest(PaddleActionV0 action)
        {
            EnsureInitialized();
            if (!isRunning)
            {
                LaunchStation();
            }

            AdvanceSimulation(action);
            UpdatePresentation();
            return isRunning;
        }

        private void ResetEnvironment()
        {
            ResetMuseumPhysicsRebound();
            observation = fixture.Environment.Reset(
                PhysicsMuseumProtocolV1.CreateRequest(
                    selectedStation,
                    selectedVariant));
            lastResult = null;
            UpdateTrajectory();
        }

        private void AdvanceSimulation(PaddleActionV0 action)
        {
            if (museumReboundInProgress)
            {
                AdvanceMuseumPhysicsRebound();
                return;
            }

            if (fixture.Environment.State == EpisodeStateV0.Terminal)
            {
                HandleTerminal();
                return;
            }

            lastResult = fixture.Environment.Step(action);
            observation = lastResult.Observation;
            RecordContacts(lastResult.Events);
            UpdateTrajectory();
            if (lastResult.IsTerminal)
            {
                HandleTerminal();
            }
        }

        private void HandleTerminal()
        {
            if (SupportsMuseumPhysicsRebound(selectedStation) &&
                observation.Episode.BallFloorContacts > 0 &&
                !museumReboundStarted)
            {
                BeginMuseumPhysicsRebound();
                return;
            }

            if (selectedStation == PhysicsMuseumStationV1.SpinFlight)
            {
                completedSpinTraces = Mathf.Max(
                    completedSpinTraces,
                    selectedVariant + 1);
                if (selectedVariant + 1 <
                    PhysicsMuseumProtocolV1.Definition(selectedStation)
                        .VariantCount)
                {
                    selectedVariant++;
                    ResetEnvironment();
                    return;
                }
            }

            isRunning = false;
            isPaused = false;
        }

        private static bool SupportsMuseumPhysicsRebound(
            PhysicsMuseumStationV1 station)
        {
            return station is PhysicsMuseumStationV1.DropRebound or
                PhysicsMuseumStationV1.CourtBounce;
        }

        private void BeginMuseumPhysicsRebound()
        {
            var ball = fixture.Environment.Ball;
            museumReboundStarted = true;
            museumReboundInProgress = true;
            museumReboundCompleted = false;
            museumReboundHasRisen =
                ball.linearVelocity.y > ReboundRiseVelocityThreshold;
            museumReboundTicks = 0;
            museumReboundApexTopHeight =
                ball.position.y + (fixture.Configuration.BallDiameter / 2f);
            reboundTrace.Clear();
            reboundTrace.Add(ball.position);
        }

        private void AdvanceMuseumPhysicsRebound()
        {
            if (!museumReboundInProgress)
            {
                return;
            }

            var ball = fixture.Environment.Ball;
            var configuration = fixture.Configuration;
            var delta = EnvironmentVersion.PhysicsDeltaTime;
            var forces = AerodynamicModelV1.Evaluate(
                ball.linearVelocity,
                ball.angularVelocity,
                configuration.AerodynamicParameters);
            ball.AddForce(
                forces.TotalForce + (configuration.Gravity * ball.mass),
                ForceMode.Force);
            ball.angularVelocity *=
                AerodynamicModelV1.AngularVelocityMultiplier(
                    delta,
                    configuration.AerodynamicParameters);
            Physics.Simulate(delta);

            museumReboundTicks++;
            reboundTrace.Add(ball.position);
            museumReboundApexTopHeight = Mathf.Max(
                museumReboundApexTopHeight,
                ball.position.y + (configuration.BallDiameter / 2f));

            if (!FiniteMath.IsFinite(ball.position) ||
                !FiniteMath.IsFinite(ball.rotation) ||
                !FiniteMath.IsFinite(ball.linearVelocity) ||
                !FiniteMath.IsFinite(ball.angularVelocity))
            {
                CompleteMuseumPhysicsRebound();
                return;
            }

            if (ball.linearVelocity.y > ReboundRiseVelocityThreshold)
            {
                museumReboundHasRisen = true;
            }

            if ((museumReboundHasRisen && ball.linearVelocity.y <= 0f) ||
                museumReboundTicks >= MaximumMuseumReboundTicks)
            {
                CompleteMuseumPhysicsRebound();
            }
        }

        private void CompleteMuseumPhysicsRebound()
        {
            museumReboundInProgress = false;
            museumReboundCompleted = true;
            isRunning = false;
            isPaused = false;
        }

        private void ResetMuseumPhysicsRebound()
        {
            museumReboundStarted = false;
            museumReboundInProgress = false;
            museumReboundCompleted = false;
            museumReboundHasRisen = false;
            museumReboundTicks = 0;
            museumReboundApexTopHeight = 0f;
            reboundTrace.Clear();
        }

        private PaddleActionV0 ReadManualAction()
        {
            var definition =
                PhysicsMuseumProtocolV1.Definition(selectedStation);
            if (!definition.AllowsManualPaddle)
            {
                return PaddleActionV0.Zero;
            }

            var pointer = new Vector2(
                Screen.width <= 0
                    ? 0.5f
                    : Input.mousePosition.x / Screen.width,
                Screen.height <= 0
                    ? 0.5f
                    : Input.mousePosition.y / Screen.height);
            var depth =
                (Input.GetKey(KeyCode.W) ? 1f : 0f) -
                (Input.GetKey(KeyCode.S) ? 1f : 0f);
            var angular = new Vector3(
                (Input.GetKey(KeyCode.E) ? 1f : 0f) -
                (Input.GetKey(KeyCode.Q) ? 1f : 0f),
                (Input.GetKey(KeyCode.D) ? 1f : 0f) -
                (Input.GetKey(KeyCode.A) ? 1f : 0f),
                (Input.GetKey(KeyCode.X) ? 1f : 0f) -
                (Input.GetKey(KeyCode.Z) ? 1f : 0f));
            return PhysicsMuseumProtocolV1.ManualAction(
                fixture.Environment.Paddle.position,
                fixture.Environment.Paddle.rotation,
                pointer,
                Input.GetMouseButton(0),
                depth,
                angular,
                fixture.Configuration);
        }

        private void HandleKeyboardInput()
        {
            for (var index = 0;
                 index < PhysicsMuseumProtocolV1.StationCount;
                 index++)
            {
                var key = (KeyCode)((int)KeyCode.Alpha1 + index);
                if (Input.GetKeyDown(key))
                {
                    SelectStation((PhysicsMuseumStationV1)index);
                    return;
                }
            }

            if (Input.GetKeyDown(KeyCode.Space))
            {
                LaunchStation();
            }

            if (Input.GetKeyDown(KeyCode.R))
            {
                ResetStation();
            }

            if (Input.GetKeyDown(KeyCode.P))
            {
                TogglePause();
            }

            if (Input.GetKeyDown(KeyCode.LeftBracket) ||
                Input.GetKeyDown(KeyCode.RightBracket))
            {
                CyclePlaybackSpeed();
            }

            if (Input.GetKeyDown(KeyCode.V))
            {
                CycleVariant();
            }
        }

        private void MeasureStation()
        {
            hasDropMeasurement = false;
            hasCourtMeasurement = false;
            hasNetMeasurement = false;
            switch (selectedStation)
            {
                case PhysicsMuseumStationV1.DropRebound:
                    dropMeasurement = CalibrationFixturesV1.RunBallDrop(
                        fixture.Configuration,
                        DropReleaseDatumV1.BallTop);
                    hasDropMeasurement = dropMeasurement.Completed;
                    break;
                case PhysicsMuseumStationV1.CourtBounce:
                    courtMeasurement = CalibrationFixturesV1.RunCourtImpact(
                        fixture.Configuration,
                        new Vector3(3f, -4f, 4f),
                        new Vector3(
                            0f,
                            0f,
                            PhysicsMuseumProtocolV1.SpinComparisonMagnitude));
                    hasCourtMeasurement = courtMeasurement.Completed;
                    break;
                case PhysicsMuseumStationV1.NetInteraction:
                    var height = selectedVariant == 0
                        ? CourtGeometryV1.NetCenterHeight +
                          CourtGeometryV1.BallRadius + 0.18f
                        : CourtGeometryV1.NetCenterHeight;
                    netMeasurement = CalibrationFixturesV1.RunNetImpact(
                        fixture.Configuration,
                        0f,
                        height,
                        new Vector3(0f, selectedVariant == 0 ? 0.7f : 0.1f, 7.5f),
                        Vector3.zero);
                    hasNetMeasurement = true;
                    break;
            }

            UpdateReboundMarker();
        }

        private void RecordContacts(
            IReadOnlyList<EnvironmentEventV0> events)
        {
            foreach (var current in events)
            {
                if (current.Kind is not (
                    EnvironmentEventKindV0.BallFloorContact or
                    EnvironmentEventKindV0.BallNetContact or
                    EnvironmentEventKindV0.BallPaddleContact))
                {
                    continue;
                }

                lastContact =
                    $"{current.Kind} @ {current.Position:F2}";
                var marker = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                marker.name = $"Contact_{current.Kind}";
                marker.transform.SetParent(presentationRoot, true);
                marker.transform.position = current.Position;
                marker.transform.localScale = Vector3.one * 0.09f;
                var collider = marker.GetComponent<Collider>();
                if (collider != null)
                {
                    Destroy(collider);
                }

                var renderer = marker.GetComponent<Renderer>();
                if (renderer != null)
                {
                    renderer.sharedMaterial = RuntimeMaterial(
                        new Color(1f, 0.28f, 0.18f, 1f));
                }

                contactMarkers.Add(marker);
                if (contactMarkers.Count > 20)
                {
                    var oldest = contactMarkers[0];
                    contactMarkers.RemoveAt(0);
                    Destroy(oldest);
                }
            }
        }

        private void UpdatePresentation()
        {
            if (!initialized)
            {
                return;
            }

            UpdateTrajectory();
            if (spinAxis != null)
            {
                var start = fixture.Environment.Ball.position;
                var spin = fixture.Environment.Ball.angularVelocity;
                spinAxis.positionCount = 2;
                spinAxis.SetPosition(0, start);
                spinAxis.SetPosition(
                    1,
                    start +
                    (spin.sqrMagnitude <= Mathf.Epsilon
                        ? Vector3.up * 0.05f
                        : spin.normalized *
                          Mathf.Lerp(
                              0.1f,
                              0.85f,
                              Mathf.Clamp01(
                                  spin.magnitude /
                                  fixture.Configuration.MaximumBallAngularSpeed))));
            }
        }

        private void UpdateTrajectory()
        {
            if (fixture == null)
            {
                return;
            }

            var lineIndex =
                selectedStation == PhysicsMuseumStationV1.SpinFlight
                    ? selectedVariant
                    : 0;
            var line = traces[lineIndex];
            if (line == null)
            {
                return;
            }

            var points = fixture.Environment.Trajectory;
            line.positionCount = points.Count + reboundTrace.Count;
            for (var index = 0; index < points.Count; index++)
            {
                line.SetPosition(index, points[index]);
            }

            for (var index = 0; index < reboundTrace.Count; index++)
            {
                line.SetPosition(points.Count + index, reboundTrace[index]);
            }
        }

        private void CreateTrajectoryRenderers()
        {
            for (var index = 0; index < traces.Length; index++)
            {
                traces[index] = CreateLine(
                    $"Trajectory_{index}",
                    TraceColors[index],
                    0.025f);
            }
        }

        private void CreateSpinAxis()
        {
            spinAxis = CreateLine(
                "BallSpinAxis",
                new Color(0.1f, 1f, 0.88f, 1f),
                0.018f);
        }

        private void CreateReboundMarker()
        {
            reboundMarker = CreateLine(
                "MeasuredReboundApex",
                new Color(0.1f, 0.92f, 1f, 0.85f),
                0.018f);
            reboundMarker.positionCount = 0;
        }

        private LineRenderer CreateLine(
            string name,
            Color color,
            float width)
        {
            var lineObject = new GameObject(name);
            lineObject.transform.SetParent(presentationRoot, false);
            var line = lineObject.AddComponent<LineRenderer>();
            line.useWorldSpace = true;
            line.startWidth = width;
            line.endWidth = width;
            line.numCapVertices = 4;
            line.numCornerVertices = 4;
            line.material = RuntimeMaterial(color);
            line.positionCount = 0;
            return line;
        }

        private void UpdateReboundMarker()
        {
            if (reboundMarker == null)
            {
                return;
            }

            var height = 0f;
            var visible = false;
            if (selectedStation == PhysicsMuseumStationV1.DropRebound &&
                hasDropMeasurement)
            {
                height = dropMeasurement.FirstReboundTopHeight;
                visible = true;
            }
            else if (selectedStation == PhysicsMuseumStationV1.CourtBounce &&
                     hasCourtMeasurement)
            {
                height = courtMeasurement.FirstReboundTopHeight;
                visible = true;
            }

            reboundMarker.positionCount = visible ? 2 : 0;
            if (visible)
            {
                var markerZ = selectedStation == PhysicsMuseumStationV1.DropRebound
                    ? PhysicsMuseumProtocolV1.DropReboundCourtZ
                    : 0f;
                reboundMarker.SetPosition(0, new Vector3(-0.5f, height, markerZ));
                reboundMarker.SetPosition(1, new Vector3(0.5f, height, markerZ));
            }
        }

        private void ClearTraces()
        {
            foreach (var trace in traces)
            {
                ClearTrace(trace);
            }
        }

        private static void ClearTrace(LineRenderer trace)
        {
            if (trace != null)
            {
                trace.positionCount = 0;
            }
        }

        private void ClearContactMarkers()
        {
            foreach (var marker in contactMarkers)
            {
                if (marker != null)
                {
                    Destroy(marker);
                }
            }

            contactMarkers.Clear();
        }

        private void ApplyVisualMaterials()
        {
            foreach (var renderer in
                     fixture.Root.GetComponentsInChildren<Renderer>(true))
            {
                renderer.sharedMaterial = renderer.gameObject.name switch
                {
                    "CourtSurface" or "OutCatchFloor" =>
                        courtMaterial ?? renderer.sharedMaterial,
                    "Ball" =>
                        ballMaterial ?? renderer.sharedMaterial,
                    "RoundedHittingFace" or "NonContactHandle" =>
                        paddleMaterial ?? renderer.sharedMaterial,
                    "NetLeftOuter" or "NetLeftInner" or
                    "NetRightInner" or "NetRightOuter" =>
                        netMaterial ?? renderer.sharedMaterial,
                    _ => renderer.sharedMaterial
                };
            }
        }

        private void CreateCourtPresentation()
        {
            var lineWidth = 0.045f;
            var y = 0.008f;
            CreatePresentationBar(
                "NearBaseline",
                new Vector3(0f, y, -CourtGeometryV1.HalfLength),
                new Vector3(CourtGeometryV1.CourtWidth, 0.012f, lineWidth));
            CreatePresentationBar(
                "FarBaseline",
                new Vector3(0f, y, CourtGeometryV1.HalfLength),
                new Vector3(CourtGeometryV1.CourtWidth, 0.012f, lineWidth));
            CreatePresentationBar(
                "LeftSideline",
                new Vector3(-CourtGeometryV1.HalfWidth, y, 0f),
                new Vector3(lineWidth, 0.012f, CourtGeometryV1.CourtLength));
            CreatePresentationBar(
                "RightSideline",
                new Vector3(CourtGeometryV1.HalfWidth, y, 0f),
                new Vector3(lineWidth, 0.012f, CourtGeometryV1.CourtLength));
            CreatePresentationBar(
                "NearKitchenLine",
                new Vector3(0f, y, -CourtGeometryV1.NonVolleyZoneDepth),
                new Vector3(CourtGeometryV1.CourtWidth, 0.012f, lineWidth));
            CreatePresentationBar(
                "FarKitchenLine",
                new Vector3(0f, y, CourtGeometryV1.NonVolleyZoneDepth),
                new Vector3(CourtGeometryV1.CourtWidth, 0.012f, lineWidth));
            var serviceLength =
                CourtGeometryV1.HalfLength -
                CourtGeometryV1.NonVolleyZoneDepth;
            CreatePresentationBar(
                "NearCenterLine",
                new Vector3(
                    0f,
                    y,
                    -(CourtGeometryV1.NonVolleyZoneDepth +
                      (serviceLength / 2f))),
                new Vector3(lineWidth, 0.012f, serviceLength));
            CreatePresentationBar(
                "FarCenterLine",
                new Vector3(
                    0f,
                    y,
                    CourtGeometryV1.NonVolleyZoneDepth +
                    (serviceLength / 2f)),
                new Vector3(lineWidth, 0.012f, serviceLength));
        }

        private void CreatePresentationBar(
            string name,
            Vector3 position,
            Vector3 scale)
        {
            var bar = GameObject.CreatePrimitive(PrimitiveType.Cube);
            bar.name = name;
            bar.transform.SetParent(presentationRoot, false);
            bar.transform.position = position;
            bar.transform.localScale = scale;
            var collider = bar.GetComponent<Collider>();
            if (collider != null)
            {
                Destroy(collider);
            }

            var renderer = bar.GetComponent<Renderer>();
            if (renderer != null)
            {
                renderer.sharedMaterial = lineMaterial;
            }
        }

        private void ConfigureCamera()
        {
            if (museumCamera == null)
            {
                return;
            }

            museumCamera.clearFlags = CameraClearFlags.SolidColor;
            museumCamera.backgroundColor =
                new Color(0.025f, 0.055f, 0.085f, 1f);
            museumCamera.fieldOfView = 52f;
            museumCamera.nearClipPlane = 0.05f;
        }

        private void SetCameraImmediate(
            PhysicsMuseumStationDefinitionV1 definition)
        {
            if (museumCamera == null)
            {
                return;
            }

            museumCamera.transform.position = definition.CameraPosition;
            museumCamera.transform.LookAt(definition.CameraTarget, Vector3.up);
        }

        private void SmoothCamera()
        {
            if (museumCamera == null)
            {
                return;
            }

            var definition =
                PhysicsMuseumProtocolV1.Definition(selectedStation);
            museumCamera.transform.position = Vector3.Lerp(
                museumCamera.transform.position,
                definition.CameraPosition,
                1f - Mathf.Exp(-Time.unscaledDeltaTime * 8f));
            var targetRotation = Quaternion.LookRotation(
                definition.CameraTarget -
                museumCamera.transform.position,
                Vector3.up);
            museumCamera.transform.rotation = Quaternion.Slerp(
                museumCamera.transform.rotation,
                targetRotation,
                1f - Mathf.Exp(-Time.unscaledDeltaTime * 8f));
        }

        private Material RuntimeMaterial(Color color)
        {
            var source = lineMaterial;
            Material material;
            if (source != null)
            {
                material = new Material(source);
            }
            else
            {
                var shader = Shader.Find("Standard");
                if (shader == null)
                {
                    shader = Shader.Find("Sprites/Default");
                }

                material = new Material(shader);
            }

            material.color = color;
            runtimeMaterials.Add(material);
            return material;
        }

        private void EnsureInitialized()
        {
            if (!initialized)
            {
                Initialize();
            }
        }

        private void InitializeStyles()
        {
            var compact = Screen.width < 850f;
            var panelTexture = SolidTexture(
                new Color(0.025f, 0.05f, 0.075f, 0.92f));
            var tabTexture = SolidTexture(
                new Color(0.055f, 0.12f, 0.16f, 0.96f));
            var activeTexture = SolidTexture(
                new Color(0.02f, 0.55f, 0.58f, 0.98f));
            var buttonTexture = SolidTexture(
                new Color(0.08f, 0.28f, 0.32f, 0.98f));

            titleStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = compact ? 18 : 26,
                fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleLeft,
                normal = { textColor = new Color(0.9f, 1f, 1f, 1f) }
            };
            subtitleStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = compact ? 9 : 11,
                alignment = TextAnchor.MiddleLeft,
                normal = { textColor = new Color(0.48f, 0.82f, 0.84f, 1f) }
            };
            tabStyle = new GUIStyle(GUI.skin.button)
            {
                fontSize = compact ? 10 : 12,
                fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleCenter,
                normal =
                {
                    background = tabTexture,
                    textColor = new Color(0.72f, 0.9f, 0.9f, 1f)
                },
                hover = { background = buttonTexture, textColor = Color.white }
            };
            activeTabStyle = new GUIStyle(tabStyle)
            {
                normal = { background = activeTexture, textColor = Color.white }
            };
            panelStyle = new GUIStyle(GUI.skin.box)
            {
                padding = new RectOffset(16, 16, 14, 14),
                normal = { background = panelTexture }
            };
            bodyStyle = new GUIStyle(GUI.skin.label)
            {
                fontSize = compact ? 11 : 13,
                wordWrap = true,
                richText = true,
                normal = { textColor = new Color(0.82f, 0.92f, 0.94f, 1f) }
            };
            metricStyle = new GUIStyle(bodyStyle)
            {
                fontSize = compact ? 10 : 12,
                normal = { textColor = new Color(0.75f, 1f, 0.92f, 1f) }
            };
            warningStyle = new GUIStyle(bodyStyle)
            {
                fontSize = compact ? 9 : 11,
                fontStyle = FontStyle.Bold,
                normal = { textColor = new Color(1f, 0.73f, 0.28f, 1f) }
            };
            buttonStyle = new GUIStyle(GUI.skin.button)
            {
                fontSize = compact ? 10 : 12,
                fontStyle = FontStyle.Bold,
                normal = { background = buttonTexture, textColor = Color.white },
                hover = { background = activeTexture, textColor = Color.white }
            };
        }

        private Texture2D SolidTexture(Color color)
        {
            var texture = new Texture2D(1, 1)
            {
                name = "MuseumRuntimeUI"
            };
            texture.SetPixel(0, 0, color);
            texture.Apply();
            runtimeTextures.Add(texture);
            return texture;
        }

        private void OnGUI()
        {
            if (!initialized)
            {
                return;
            }

            if (titleStyle == null)
            {
                InitializeStyles();
            }

            var compact = Screen.width < 850f;
            var margin = compact ? 8f : 16f;
            GUI.Label(
                new Rect(margin, 8f, Screen.width - (margin * 2f), 38f),
                "PICKLEBOT PHYSICS MUSEUM",
                titleStyle);
            GUI.Label(
                new Rect(margin, 42f, Screen.width - (margin * 2f), 22f),
                $"{PhysicsMuseumProtocolV1.Version}  |  real env-v1 " +
                $"({fixture.Configuration.ConfigurationHash})",
                subtitleStyle);

            var tabY = 66f;
            var tabGap = compact ? 3f : 5f;
            var tabWidth =
                (Screen.width - (margin * 2f) -
                 (tabGap * (PhysicsMuseumProtocolV1.StationCount - 1))) /
                PhysicsMuseumProtocolV1.StationCount;
            for (var index = 0;
                 index < PhysicsMuseumProtocolV1.StationCount;
                 index++)
            {
                var definition = PhysicsMuseumProtocolV1.Stations[index];
                var rect = new Rect(
                    margin + ((tabWidth + tabGap) * index),
                    tabY,
                    tabWidth,
                    38f);
                if (GUI.Button(
                        rect,
                        $"{index + 1}  {definition.ShortLabel}",
                        selectedStation == definition.Station
                            ? activeTabStyle
                            : tabStyle))
                {
                    SelectStation(definition.Station);
                }
            }

            var panelTop = 116f;
            var panelBottom = 54f;
            var panelHeight = Mathf.Max(
                220f,
                Screen.height - panelTop - panelBottom);
            var leftWidth = compact
                ? Screen.width * 0.43f
                : Mathf.Min(345f, Screen.width * 0.34f);
            var rightWidth = compact
                ? Screen.width * 0.43f
                : Mathf.Min(315f, Screen.width * 0.31f);
            DrawStationPanel(new Rect(
                margin,
                panelTop,
                leftWidth,
                panelHeight));
            DrawTelemetryPanel(new Rect(
                Screen.width - margin - rightWidth,
                panelTop,
                rightWidth,
                panelHeight));
            DrawBottomControls();
        }

        private void DrawStationPanel(Rect rect)
        {
            var compact = Screen.width < 850f;
            var definition =
                PhysicsMuseumProtocolV1.Definition(selectedStation);
            GUI.Box(rect, GUIContent.none, panelStyle);
            var x = rect.x + 16f;
            var width = rect.width - 32f;
            var y = rect.y + 14f;

            GUI.Label(
                new Rect(x, y, width, compact ? 46f : 30f),
                definition.Title,
                titleStyle);
            y += compact ? 50f : 38f;
            GUI.Label(
                new Rect(x, y, width, 86f),
                definition.Description,
                bodyStyle);
            y += 92f;
            GUI.Label(
                new Rect(x, y, width, 68f),
                $"<b>HOW TO TRY IT</b>\n{definition.InteractionHint}",
                bodyStyle);
            y += 78f;
            GUI.Label(
                new Rect(x, y, width, 22f),
                $"VARIANT: {PhysicsMuseumProtocolV1.VariantLabel(selectedStation, selectedVariant)}",
                metricStyle);
            y += 30f;

            var buttonGap = 7f;
            var buttonWidth = (width - buttonGap) / 2f;
            if (GUI.Button(
                    new Rect(x, y, buttonWidth, 34f),
                    compact ? "GO  [SPACE]" : "LAUNCH  [SPACE]",
                    buttonStyle))
            {
                LaunchStation();
            }

            if (GUI.Button(
                    new Rect(
                        x + buttonWidth + buttonGap,
                        y,
                        buttonWidth,
                        34f),
                    "RESET  [R]",
                    buttonStyle))
            {
                ResetStation();
            }

            y += 42f;
            if (GUI.Button(
                    new Rect(x, y, buttonWidth, 34f),
                    isPaused ? "RESUME  [P]" : "PAUSE  [P]",
                    buttonStyle))
            {
                TogglePause();
            }

            if (GUI.Button(
                    new Rect(
                        x + buttonWidth + buttonGap,
                        y,
                        buttonWidth,
                        34f),
                    $"SPEED {PlaybackSpeed:0.##}x  [ ]",
                    buttonStyle))
            {
                CyclePlaybackSpeed();
            }

            y += 44f;
            if (definition.VariantCount > 1 &&
                selectedStation != PhysicsMuseumStationV1.SpinFlight &&
                GUI.Button(
                    new Rect(x, y, width, 34f),
                    "CHANGE VARIANT  [V]",
                    buttonStyle))
            {
                CycleVariant();
            }

            GUI.Label(
                new Rect(
                    x,
                    rect.yMax - 66f,
                    width,
                    54f),
                "INTUITIVE FEEL CHECK ONLY\n" +
                "This museum cannot replace measured Phase 1B calibration.",
                warningStyle);
        }

        private void DrawTelemetryPanel(Rect rect)
        {
            GUI.Box(rect, GUIContent.none, panelStyle);
            var x = rect.x + 16f;
            var width = rect.width - 32f;
            var y = rect.y + 14f;
            GUI.Label(
                new Rect(x, y, width, 28f),
                "LIVE TELEMETRY",
                titleStyle);
            y += 38f;

            var text = BuildTelemetryText();
            GUI.Label(
                new Rect(x, y, width, rect.height - 52f),
                text,
                metricStyle);
        }

        private string BuildTelemetryText()
        {
            var useLiveMuseumBall = museumReboundStarted;
            var displayedVelocity = useLiveMuseumBall
                ? fixture.Environment.Ball.linearVelocity
                : observation.Ball.LinearVelocityWorld;
            var spin = useLiveMuseumBall
                ? fixture.Environment.Ball.angularVelocity
                : observation.Ball.AngularVelocityWorld;
            var ballSpeed = displayedVelocity.magnitude;
            var spinRps = spin.magnitude / (Mathf.PI * 2f);
            var paddleSpeed = observation.Paddle.LinearVelocityWorld.magnitude;
            var state = fixture.Environment.State;
            var builder = new StringBuilder();
            builder.AppendLine(
                museumReboundInProgress
                    ? "state                 museum real-physics rebound"
                    : museumReboundCompleted
                        ? "state                 Terminal (rebound apex)"
                        : $"state                 {state}");
            builder.AppendLine(
                $"playback              {(isPaused ? "paused" : $"{PlaybackSpeed:0.##}x")}");
            builder.AppendLine($"variant               {PhysicsMuseumProtocolV1.VariantLabel(selectedStation, selectedVariant)}");
            builder.AppendLine($"physics tick          {observation.PhysicsTick}");
            builder.AppendLine($"elapsed               {observation.ElapsedTime:0.000} s");
            builder.AppendLine();
            builder.AppendLine($"ball speed            {ballSpeed:0.000} m/s");
            builder.AppendLine($"ball velocity         {displayedVelocity:F2}");
            builder.AppendLine($"spin magnitude        {spin.magnitude:0.00} rad/s");
            builder.AppendLine($"spin rate             {spinRps:0.00} rps");
            builder.AppendLine($"spin vector           {spin:F2}");
            builder.AppendLine($"paddle speed          {paddleSpeed:0.000} m/s");
            builder.AppendLine($"paddle angular        {observation.Paddle.AngularVelocityWorld:F2}");
            builder.AppendLine();
            builder.AppendLine($"paddle contacts       {observation.Episode.ControlledPaddleContacts}");
            builder.AppendLine($"floor contacts        {observation.Episode.BallFloorContacts}");
            builder.AppendLine($"last contact          {lastContact}");
            builder.AppendLine($"trajectory points     {ActiveTracePointCount}");

            if (museumReboundStarted)
            {
                builder.AppendLine();
                builder.AppendLine("<b>REAL UNITY PHYSICS REBOUND</b>");
                builder.AppendLine(
                    $"rebound state          {(museumReboundCompleted ? "apex reached" : "rising")}");
                builder.AppendLine(
                    $"real apex              {museumReboundApexTopHeight:0.000} m");
                builder.AppendLine($"museum physics ticks  {museumReboundTicks}");
                builder.AppendLine("episode record remains terminal");
            }

            if (hasDropMeasurement)
            {
                builder.AppendLine();
                builder.AppendLine("<b>DROP FIXTURE</b>");
                builder.AppendLine($"impact time           {dropMeasurement.FirstImpactTime:0.000} s");
                builder.AppendLine($"rebound apex          {dropMeasurement.FirstReboundTopHeight:0.000} m");
                builder.AppendLine($"horizontal drift      {dropMeasurement.HorizontalDrift:0.0000} m");
            }

            if (hasCourtMeasurement)
            {
                builder.AppendLine();
                builder.AppendLine("<b>COURT FIXTURE</b>");
                builder.AppendLine($"rebound apex          {courtMeasurement.FirstReboundTopHeight:0.000} m");
                builder.AppendLine($"out velocity          {courtMeasurement.OutgoingVelocity:F2}");
                builder.AppendLine($"out spin              {courtMeasurement.OutgoingAngularVelocity:F2}");
            }

            if (hasNetMeasurement)
            {
                builder.AppendLine();
                builder.AppendLine("<b>NET FIXTURE</b>");
                builder.AppendLine($"contact detected      {netMeasurement.ContactDetected}");
                builder.AppendLine($"continued flight      {netMeasurement.ContinuedFlight}");
                builder.AppendLine($"energy ratio          {netMeasurement.KineticEnergyRatio:0.000}");
            }

            if (selectedStation == PhysicsMuseumStationV1.SpinFlight)
            {
                builder.AppendLine();
                builder.AppendLine($"comparison traces     {completedSpinTraces}/3");
            }

            return builder.ToString();
        }

        private void DrawBottomControls()
        {
            var compact = Screen.width < 850f;
            GUI.Label(
                new Rect(
                    16f,
                    Screen.height - 42f,
                    Screen.width - 32f,
                    30f),
                compact
                    ? "1-6 station | SPACE launch | R reset | P pause | " +
                      "[ ] speed | V variant"
                    : "1-6 stations   SPACE launch   R reset   P pause   " +
                      "[ ] speed   V variant   |   manual: hold/click + move " +
                      "pointer, W/S depth, Q/E pitch, A/D yaw, Z/X roll",
                subtitleStyle);
        }
    }
}
