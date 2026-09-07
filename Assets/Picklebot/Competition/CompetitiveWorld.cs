using System;
using System.Collections.Generic;
using Picklebot.Rally;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Picklebot.Competition
{
    [Serializable] public sealed class ShotDecision
    {
        public float[] observation;
        public int action, side;
        public float logProbability;
    }

    public sealed class CompetitiveWorld : IDisposable
    {
        public const float Dt = 1f / 240f, Radius = .025f, CourtRestitution = .86f;
        public const string Version = "competition-v1";
        public readonly RallyRules Rules = new();
        public readonly GameObject Root;
        public readonly Rigidbody Ball;
        public readonly Rigidbody[] Paddles = new Rigidbody[2];
        public readonly List<string> Events = new();
        public readonly List<ShotDecision> Decisions = new();
        public readonly float[] Travel = new float[2];
        public static readonly Vector2[] Goals = { new(-.58f,.48f), new(.58f,.48f), new(-.58f,.9f), new(.58f,.9f), new(0,.65f) };
        public int Seed { get; private set; }
        public float Elapsed { get; private set; }
        public bool Truncated { get; private set; }
        public bool Finished => Rules.Finished || Truncated;
        private readonly Scene scene;
        private readonly PhysicsScene physics;
        private readonly List<Material> visuals = new();
        private readonly List<PhysicsMaterial> materials = new();
        private readonly List<(string name, Vector3 point)> contacts = new();
        private readonly Vector3[] centre = new Vector3[2], normal = new Vector3[2];
        private readonly float[] swing = new float[2], contactAt = new float[2];
        private readonly bool[] planned = new bool[2];
        private readonly DensePolicy stroke;
        private System.Random rng;
        private int decisionContacts = -1, bounces;

        public CompetitiveWorld(DensePolicy strokePolicy, bool visible)
        {
            stroke = strokePolicy;
            scene = SceneManager.CreateScene("CompetitivePhysics-" + Guid.NewGuid().ToString("N"), new CreateSceneParameters(LocalPhysicsMode.Physics3D));
            physics = scene.GetPhysicsScene();
            Root = new GameObject("Competitive paddles / provisional physics");
            SceneManager.MoveGameObjectToScene(Root, scene);
            var courtMaterial = Surface("Court", CourtRestitution);
            var paddleMaterial = Surface("Paddle", .9f);
            Box("Table", new Vector3(0,-.06f,0), new Vector3(1.8f,.12f,3), new Color(.04f,.3f,.36f), courtMaterial);
            Box("Net", new Vector3(0,.075f,0), new Vector3(1.9f,.15f,.025f), new Color(.7f,.8f,.85f), Surface("Net", .05f));
            for (int i = 0; i < 2; i++)
            {
                var go = Box(i == 0 ? "PaddleNear" : "PaddleFar", Vector3.zero, new Vector3(.18f,.20f,.02f),
                    i == 0 ? new Color(.96f,.35f,.18f) : new Color(.2f,.6f,1), paddleMaterial);
                Paddles[i] = go.AddComponent<Rigidbody>();
                Paddles[i].isKinematic = true;
                Paddles[i].useGravity = false;
                Paddles[i].collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            }
            var ball = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            ball.name = "CompetitionBall";
            ball.transform.SetParent(Root.transform, false);
            ball.transform.localScale = Vector3.one * Radius * 2;
            ball.GetComponent<Collider>().sharedMaterial = Surface("Ball", 1);
            Paint(ball, new Color(1,.9f,.25f));
            Ball = ball.AddComponent<Rigidbody>();
            Ball.mass = .0027f;
            Ball.useGravity = false;
            Ball.linearDamping = Ball.angularDamping = 0;
            Ball.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            Ball.solverIterations = Ball.solverVelocityIterations = 12;
            Ball.sleepThreshold = 0;
            ball.AddComponent<CompetitiveContacts>().World = this;
            foreach (var c in Root.GetComponentsInChildren<Collider>()) c.contactOffset = .001f;
            if (visible)
            {
                var trail = ball.AddComponent<TrailRenderer>();
                trail.time = .16f; trail.startWidth = .012f; trail.endWidth = .001f;
                trail.material = ball.GetComponent<Renderer>().sharedMaterial;
                foreach (float x in new[] { -.895f, .895f }) Line(new Vector3(x,.002f,0), new Vector3(.012f,.005f,3));
                foreach (float z in new[] { -1.495f, 1.495f }) Line(new Vector3(0,.002f,z), new Vector3(1.8f,.005f,.012f));
                Line(new Vector3(0,.002f,0), new Vector3(.008f,.005f,3));
            }
            else foreach (var renderer in Root.GetComponentsInChildren<Renderer>()) renderer.enabled = false;
        }

        private PhysicsMaterial Surface(string name, float restitution)
        {
            var m = new PhysicsMaterial(name) { bounciness = restitution, dynamicFriction = 0, staticFriction = 0,
                bounceCombine = PhysicsMaterialCombine.Multiply, frictionCombine = PhysicsMaterialCombine.Minimum };
            materials.Add(m); return m;
        }
        private GameObject Box(string name, Vector3 p, Vector3 scale, Color color, PhysicsMaterial material)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube); go.name = name;
            go.transform.SetParent(Root.transform, false); go.transform.position = p; go.transform.localScale = scale;
            go.GetComponent<Collider>().sharedMaterial = material; Paint(go,color); return go;
        }
        private void Paint(GameObject go, Color color)
        {
            var m = new Material(Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard")) { color = color };
            visuals.Add(m); go.GetComponent<Renderer>().sharedMaterial = m;
        }
        private void Line(Vector3 p, Vector3 scale) => Box("Court line",p,scale,Color.white,materials[0]).GetComponent<Collider>().enabled = false;

        public void Reset(int seed)
        {
            Seed = seed; Elapsed = 0; Truncated = false; decisionContacts = -1; bounces = 0;
            rng = new System.Random(seed); contacts.Clear(); Events.Clear(); Decisions.Clear();
            int server = seed % 2 == 0 ? 1 : -1; Rules.Reset(server);
            Ball.position = new Vector3((float)(rng.NextDouble()-.5)*.3f,.12f,server*1.1f);
            Ball.rotation = Quaternion.identity;
            Ball.linearVelocity = new Vector3((float)(rng.NextDouble()-.5)*.25f,-1.8f,-server*(4.6f+(float)rng.NextDouble()*.15f));
            Ball.angularVelocity = Vector3.zero;
            for (int i = 0; i < 2; i++)
            {
                centre[i] = new Vector3(0,.3f,i == 0 ? -1.32f : 1.32f);
                normal[i] = i == 0 ? Vector3.forward : Vector3.back;
                planned[i] = false; swing[i] = Travel[i] = 0;
                Paddles[i].position = centre[i]; Paddles[i].rotation = Quaternion.LookRotation(normal[i]);
            }
            Ball.WakeUp();
            var trail = Ball.GetComponent<TrailRenderer>();
            if(trail != null) trail.Clear();
            Physics.SyncTransforms();
        }

        public void Step(DensePolicy nearStrategy = null, DensePolicy farStrategy = null, bool sample = false, int fixedGoal = 4)
        {
            if (Finished) return;
            int side = Rules.Receiver, index = side < 0 ? 0 : 1;
            float mirror = -side;
            if (bounces > 0 && decisionContacts != Rules.Contacts && Ball.position.z * mirror < .8f && Ball.linearVelocity.z * mirror < 0)
            {
                var obs = new[] { Ball.position.x*mirror, Ball.position.y, Ball.position.z*mirror,
                    Ball.linearVelocity.x*mirror, Ball.linearVelocity.y, Ball.linearVelocity.z*mirror,
                    Paddles[index].position.x*mirror, Paddles[1-index].position.x*mirror };
                var strategy = side < 0 ? nearStrategy : farStrategy;
                int action = fixedGoal; float logp = 0;
                if (strategy != null)
                {
                    var logits = strategy.Predict(obs); float max = Mathf.Max(logits), total = 0;
                    for (int j=0;j<logits.Length;j++) { logits[j] = Mathf.Exp(logits[j]-max); total += logits[j]; }
                    if (sample)
                    {
                        float choice = (float)rng.NextDouble()*total; action = logits.Length-1;
                        for(int j=0;j<logits.Length;j++) { choice -= logits[j]; if(choice <= 0) { action=j; break; } }
                    }
                    else { action=0; for(int j=1;j<logits.Length;j++) if(logits[j]>logits[action]) action=j; }
                    logp = Mathf.Log(logits[action]/total);
                }
                Decisions.Add(new ShotDecision { observation=obs, action=action, side=side, logProbability=logp });
                var goal = Goals[action];
                var command = stroke.Predict(new[] { obs[0],obs[1],obs[2],obs[3],obs[4],obs[5],Rules.ReadyToHit?1f:0f,goal.x,goal.y,.48f });
                var n = new Vector3(Mathf.Clamp(command[2],-.8f,.8f),Mathf.Clamp(command[3],-.8f,.8f),1).normalized;
                var impact = new Vector3(Mathf.Clamp(command[0],-1.05f,1.05f),Mathf.Clamp(command[1],.075f,1),-1.25f);
                var c = impact - n * (Radius+.01f);
                centre[index] = new Vector3(c.x*mirror,c.y,c.z*mirror);
                normal[index] = new Vector3(n.x*mirror,n.y,n.z*mirror);
                swing[index] = Mathf.Clamp(command[4],-2.5f,2.5f);
                contactAt[index] = Elapsed + Mathf.Clamp(command[5],.015f,.8f);
                planned[index] = true; decisionContacts = Rules.Contacts;
            }
            for (int i=0;i<2;i++)
            {
                var target = centre[i];
                if (planned[i]) target += normal[i]*swing[i]*Mathf.Clamp(Elapsed+Dt-contactAt[i],-.8f,.06f);
                var before = Paddles[i].position;
                // Physical kinematic motor: finite travel speed; no ball steering.
                var after = Vector3.MoveTowards(before,target,2.0f*Dt);
                Travel[i] += Mathf.Abs(after.x-before.x);
                Paddles[i].MovePosition(after);
                Paddles[i].MoveRotation(Quaternion.RotateTowards(Paddles[i].rotation,Quaternion.LookRotation(normal[i]),900*Dt));
            }
            Integrate();
            foreach (var c in contacts)
            {
                if (Rules.Finished) break;
                Events.Add($"{Elapsed:F4} {c.name} {c.point.x:F4},{c.point.y:F4},{c.point.z:F4}");
                switch(c.name)
                {
                    case "Table": bounces++; if(c.point.y<-.01f) Rules.Lost("Table edge"); else Rules.Bounce(c.point.z<0?-1:1); break;
                    case "PaddleNear": Rules.Hit(-1); Hold(0); break;
                    case "PaddleFar": Rules.Hit(1); Hold(1); break;
                    case "Net": Rules.Lost("Net contact"); break;
                }
            }
            contacts.Clear();
            var p = Ball.position;
            if(p.y<-.15f || Mathf.Abs(p.x)>1.4f || Mathf.Abs(p.z)>1.9f) Rules.Lost("Miss or out");
            if(Elapsed>30 && !Rules.Finished) Truncated = true;
            if(!float.IsFinite(p.x)||!float.IsFinite(p.y)||!float.IsFinite(p.z)) Rules.Lost("Invalid state");
        }
        private void Hold(int i) { centre[i]=Paddles[i].position; planned[i]=false; }
        private void Integrate()
        {
            var velocity = Ball.linearVelocity;
            Ball.AddForce(new Vector3(0,-9.81f,0)-.025f*velocity.magnitude*velocity,ForceMode.Acceleration);
            physics.Simulate(Dt); Elapsed += Dt;
        }
        // Measurement mode only: lets a drop continue after rule faults.
        public void StepFreePhysics() { Integrate(); contacts.Clear(); }
        public void Contact(string name, Vector3 point) => contacts.Add((name,point));
        public void Dispose()
        {
            if(Root!=null) UnityEngine.Object.DestroyImmediate(Root);
            foreach(var m in visuals) UnityEngine.Object.DestroyImmediate(m);
            foreach(var m in materials) UnityEngine.Object.DestroyImmediate(m);
            if(scene.IsValid()&&scene.isLoaded) SceneManager.UnloadSceneAsync(scene);
        }
    }
}
