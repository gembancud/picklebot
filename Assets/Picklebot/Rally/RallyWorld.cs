using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Picklebot.Rally
{
    // A separate local physics scene prevents the prototype from changing the
    // existing pickleball simulator or the Editor's global simulation mode.
    public sealed class RallyWorld : IDisposable
    {
        public const float Dt = 1f / 240f;
        public const string Version = "rally-world-v1-elastic";
        public readonly RallyRules Rules = new();
        public readonly GameObject Root;
        public readonly Rigidbody Ball;
        public readonly Rigidbody[] Paddles = new Rigidbody[2];
        public readonly List<string> Events = new();
        public int Seed { get; private set; }
        public float Elapsed { get; private set; }
        public Vector3 InitialPosition { get; private set; }
        public Vector3 InitialVelocity { get; private set; }
        private readonly Scene scene;
        private readonly PhysicsScene physics;
        private readonly PhysicsMaterial material;
        private readonly List<Material> visuals = new();
        private readonly Vector3[] target = new Vector3[2];
        private readonly Quaternion[] rotation = new Quaternion[2];
        private readonly List<(string name, Vector3 point)> contacts = new();
        private int decisionContacts = -1;

        public RallyWorld(bool visible)
        {
            scene = SceneManager.CreateScene("RallyPhysics-" + Guid.NewGuid().ToString("N"),
                new CreateSceneParameters(LocalPhysicsMode.Physics3D));
            physics = scene.GetPhysicsScene();
            Root = new GameObject("AI Rally / provisional physics");
            SceneManager.MoveGameObjectToScene(Root, scene);
            material = new PhysicsMaterial("Ideal elastic rally material")
            {
                bounciness = 1f, dynamicFriction = 0f, staticFriction = 0f,
                bounceCombine = PhysicsMaterialCombine.Multiply,
                frictionCombine = PhysicsMaterialCombine.Minimum
            };
            Box("Table", new Vector3(0, -0.06f, 0), new Vector3(1.8f, .12f, 3f), new Color(.04f,.30f,.36f));
            Box("Net", new Vector3(0, .075f, 0), new Vector3(1.9f, .15f, .025f), new Color(.7f,.8f,.85f));
            for (int i = 0; i < 2; i++)
            {
                var paddle = Box(i == 0 ? "PaddleNear" : "PaddleFar", Vector3.zero,
                    new Vector3(.40f,.40f,.035f), i == 0 ? new Color(.96f,.35f,.18f) : new Color(.2f,.6f,1f));
                Paddles[i] = paddle.AddComponent<Rigidbody>();
                Paddles[i].isKinematic = true;
                Paddles[i].useGravity = false;
                Paddles[i].collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            }
            var ball = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            ball.name = "RallyBall";
            ball.transform.SetParent(Root.transform, false);
            ball.transform.localScale = Vector3.one * .07f;
            ball.GetComponent<Collider>().sharedMaterial = material;
            Paint(ball, new Color(1f,.9f,.25f));
            Ball = ball.AddComponent<Rigidbody>();
            Ball.mass = .0027f;
            Ball.useGravity = false;
            Ball.linearDamping = Ball.angularDamping = 0;
            Ball.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            Ball.solverIterations = 12;
            Ball.solverVelocityIterations = 12;
            Ball.sleepThreshold = 0;
            ball.AddComponent<RallyBallContacts>().World = this;
            foreach (var collider in Root.GetComponentsInChildren<Collider>()) collider.contactOffset = .001f;
            if (visible)
            {
                var trail = ball.AddComponent<TrailRenderer>();
                trail.time = .4f; trail.startWidth = .025f; trail.endWidth = .002f;
                trail.material = ball.GetComponent<Renderer>().sharedMaterial;
                foreach (float x in new[] { -.895f, .895f })
                    DecorativeLine(new Vector3(x,.002f,0), new Vector3(.012f,.005f,3));
                foreach (float z in new[] { -1.495f, 1.495f })
                    DecorativeLine(new Vector3(0,.002f,z), new Vector3(1.8f,.005f,.012f));
                DecorativeLine(new Vector3(0,.002f,0), new Vector3(.008f,.005f,3));
            }
            else foreach (var renderer in Root.GetComponentsInChildren<Renderer>()) renderer.enabled = false;
        }

        private GameObject Box(string name, Vector3 position, Vector3 size, Color color)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(Root.transform, false);
            go.transform.position = position;
            go.transform.localScale = size;
            go.GetComponent<Collider>().sharedMaterial = material;
            Paint(go, color);
            return go;
        }

        private void Paint(GameObject go, Color color)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            var visual = new Material(shader) { color = color };
            visuals.Add(visual);
            go.GetComponent<Renderer>().sharedMaterial = visual;
        }

        private void DecorativeLine(Vector3 position, Vector3 size)
        {
            var go = Box("Court line", position, size, Color.white);
            go.GetComponent<Collider>().enabled = false;
        }

        public void Reset(int seed)
        {
            Seed = seed;
            Elapsed = 0;
            decisionContacts = -1;
            contacts.Clear(); Events.Clear();
            var rng = new System.Random(seed);
            int server = seed % 2 == 0 ? 1 : -1;
            Rules.Reset(server);
            InitialPosition = new Vector3((float)(rng.NextDouble()-.5)*.3f, .10f, server * 1.1f);
            InitialVelocity = new Vector3((float)(rng.NextDouble()-.5)*.25f, -1.3f,
                -server * (4.4f + (float)rng.NextDouble()*.35f));
            Ball.position = InitialPosition;
            Ball.rotation = Quaternion.identity;
            Ball.linearVelocity = InitialVelocity;
            Ball.angularVelocity = Vector3.zero;
            for (int i = 0; i < 2; i++)
            {
                target[i] = new Vector3(0, .35f, i == 0 ? -1.32f : 1.32f);
                rotation[i] = i == 0 ? Quaternion.identity : Quaternion.Euler(0,180,0);
                Paddles[i].position = target[i];
                Paddles[i].rotation = rotation[i];
            }
            Ball.WakeUp();
            var trail = Ball.GetComponent<TrailRenderer>();
            if (trail != null) trail.Clear();
            Physics.SyncTransforms();
        }

        public void Step(RallyNeuralPolicy policy)
        {
            if (Rules.Finished) return;
            if (Rules.ReadyToHit && decisionContacts != Rules.Contacts)
            {
                if (policy != null) ApplyAction(policy.Decide(Ball.position, Ball.linearVelocity, Rules.Receiver), Rules.Receiver);
                decisionContacts = Rules.Contacts;
            }
            for (int i = 0; i < 2; i++)
            {
                Paddles[i].MovePosition(Vector3.MoveTowards(Paddles[i].position, target[i], 8f * Dt));
                Paddles[i].MoveRotation(Quaternion.RotateTowards(Paddles[i].rotation, rotation[i], 900f * Dt));
            }
            // Gravity is explicit so global project gravity cannot alter this experiment.
            Ball.AddForce(new Vector3(0,-9.81f,0), ForceMode.Acceleration);
            physics.Simulate(Dt);
            Elapsed += Dt;
            foreach (var contact in contacts)
            {
                if (Rules.Finished) break;
                Events.Add($"{Elapsed:F4} {contact.name} {contact.point.x:F4},{contact.point.y:F4},{contact.point.z:F4}");
                switch (contact.name)
                {
                    case "Table":
                        if (contact.point.y < -.01f) Rules.Lost("Table edge");
                        else Rules.Bounce(contact.point.z < 0 ? -1 : 1);
                        break;
                    case "PaddleNear": Rules.Hit(-1); break;
                    case "PaddleFar": Rules.Hit(1); break;
                    case "Net": Rules.Lost("Net contact"); break;
                }
            }
            contacts.Clear();
            var p = Ball.position;
            if (p.y < -.15f || Mathf.Abs(p.x) > 1.4f || Mathf.Abs(p.z) > 1.9f)
                Rules.Lost("Miss or out");
            if (Elapsed > 90f) Rules.Lost("Time limit");
            if (!float.IsFinite(p.x) || !float.IsFinite(p.y) || !float.IsFinite(p.z)) Rules.Lost("Invalid state");
        }

        private void ApplyAction(float[] action, int side)
        {
            // Generic bounded position/angle motor. Every target comes from the network.
            float mirror = -side;
            var normal = new Vector3(Mathf.Clamp(action[2],-.6f,.6f), Mathf.Clamp(action[3],-.6f,.6f), 1f).normalized;
            var impact = new Vector3(Mathf.Clamp(action[0],-.78f,.78f), Mathf.Clamp(action[1],.09f,1.1f), -1.25f);
            var centre = impact - normal * (.035f + .0175f);
            int index = side < 0 ? 0 : 1;
            target[index] = new Vector3(centre.x*mirror, centre.y, centre.z*mirror);
            var worldNormal = new Vector3(normal.x*mirror, normal.y, normal.z*mirror);
            rotation[index] = Quaternion.LookRotation(worldNormal, Vector3.up);
        }

        public void Contact(string name, Vector3 point) => contacts.Add((name, point));

        public void Dispose()
        {
            if (Root != null) UnityEngine.Object.DestroyImmediate(Root);
            foreach (var visual in visuals) UnityEngine.Object.DestroyImmediate(visual);
            UnityEngine.Object.DestroyImmediate(material);
            if (scene.IsValid() && scene.isLoaded) SceneManager.UnloadSceneAsync(scene);
        }
    }
}
