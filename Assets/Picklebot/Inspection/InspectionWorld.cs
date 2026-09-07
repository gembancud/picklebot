using System;
using System.Collections.Generic;
using Picklebot.Core;
using Picklebot.Simulation;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Picklebot.Inspection
{
    public enum InspectionPreset { CourtDrop, AngledBounce, FlatContact, BrushUp, BrushDown, Serve, GraniteDrop }
    public readonly struct PaddleInput
    {
        public readonly Vector3 Translation, Rotation;
        public readonly Vector2 PlayerMove;
        public PaddleInput(Vector3 translation,Vector3 rotation,Vector2 playerMove)
        { Translation=translation;Rotation=rotation;PlayerMove=playerMove; }
    }
    [Serializable] public sealed class InspectionContact
    {
        public float time;
        public string surface;
        public Vector3 point, normal, incomingVelocity, incomingSpin, velocity, spin;
    }
    [Serializable] public sealed class InspectionFrame
    {
        public float time;
        public Vector3 position, velocity, spin;
    }
    public sealed class InspectionWorld : IDisposable
    {
        public const string Version="pickleball-inspection-v1-provisional";
        public const float Dt=1f/240f;
        public readonly PicklebotEnvironmentFixtureV1 Fixture;
        public SimulationConfigV1 Configuration=>Fixture.Configuration;
        public GameObject Root=>Fixture.Root;
        public readonly Rigidbody Ball;
        public readonly PaddleMotor[] Motors=new PaddleMotor[2];
        public readonly InspectionRules Rules=new();
        public readonly List<InspectionContact> Contacts=new();
        public readonly List<InspectionFrame> Frames=new();
        public InspectionPreset Preset { get; private set; }
        public float Elapsed { get; private set; }
        public float FirstReboundHeight { get; private set; }
        public bool ReboundComplete { get; private set; }
        public bool RulesEnabled=>Preset==InspectionPreset.Serve;
        public bool AtTimeLimit=>Elapsed>=20;
        private readonly Scene scene;
        private readonly PhysicsScene physics;
        private readonly List<(Collider collider,Vector3 point,Vector3 normal)> pending=new();
        private readonly List<Material> visuals=new();
        private readonly GameObject granite;
        private readonly PhysicsMaterial graniteMaterial;
        private readonly Transform[] markers=new Transform[2];
        private bool rose;
        public InspectionWorld(bool visible)
        {
            scene=SceneManager.CreateScene("PickleballInspection-"+Guid.NewGuid().ToString("N"),new CreateSceneParameters(LocalPhysicsMode.Physics3D));
            physics=scene.GetPhysicsScene();
            Fixture=PicklebotEnvironmentFactoryV1.Create("Full-size pickleball / provisional outdoor acrylic");
            Ball=Fixture.Environment.Ball;
            var near=Fixture.Environment.Paddle;
            // Reuse geometry, materials and parameter definitions. The training
            // episode lifecycle is not used by this free-running inspection scene.
            UnityEngine.Object.DestroyImmediate(Ball.GetComponent<BallContactReporterV1>());
            UnityEngine.Object.DestroyImmediate(Fixture.Environment);
            SceneManager.MoveGameObjectToScene(Root,scene);
            var far=UnityEngine.Object.Instantiate(near.gameObject,Root.transform).GetComponent<Rigidbody>();
            near.name="PaddleNear";far.name="PaddleFar";
            Motors[0]=new PaddleMotor(near,-1);Motors[1]=new PaddleMotor(far,1);
            Ball.gameObject.AddComponent<InspectionContacts>().World=this;
            granite=GameObject.CreatePrimitive(PrimitiveType.Cube);granite.name="Granite reference slab";granite.transform.SetParent(Root.transform);
            granite.transform.position=new Vector3(-2,-.051f,-2);granite.transform.localScale=new Vector3(.5f,.102f,.5f);
            graniteMaterial=new PhysicsMaterial("Provisional granite") {bounciness=Configuration.GraniteRestitution,bounceCombine=PhysicsMaterialCombine.Multiply,
                dynamicFriction=0,staticFriction=0,frictionCombine=PhysicsMaterialCombine.Multiply};
            granite.GetComponent<Collider>().sharedMaterial=graniteMaterial;
            Ball.solverIterations=Ball.solverVelocityIterations=12;
            Ball.sleepThreshold=0;Ball.maxAngularVelocity=Configuration.MaximumBallAngularSpeed;
            foreach(var c in Root.GetComponentsInChildren<Collider>())c.contactOffset=.001f;
            if(visible)BuildPresentation();
            else foreach(var r in Root.GetComponentsInChildren<Renderer>())r.enabled=false;
            Reset(InspectionPreset.CourtDrop);
        }
        public void Reset(InspectionPreset preset)
        {
            Preset=preset;Elapsed=FirstReboundHeight=0;ReboundComplete=rose=false;pending.Clear();Contacts.Clear();Frames.Clear();
            Rules.BeginServe(-1,1);
            Motors[0].Reset(new Vector3(0,0,-4.6f),new Vector3(0,1,-4),Quaternion.identity);
            Motors[1].Reset(new Vector3(0,0,5.8f),new Vector3(0,1,5.2f),Quaternion.Euler(0,180,0));
            Vector3 p=new(0,1+CourtGeometryV1.BallRadius,-2),v=Vector3.zero;
            granite.SetActive(preset==InspectionPreset.GraniteDrop);
            Root.transform.Find("CourtSurface").GetComponent<Collider>().enabled=preset!=InspectionPreset.GraniteDrop;
            if(preset==InspectionPreset.GraniteDrop)p=new Vector3(-2,1.9812f+CourtGeometryV1.BallRadius,-2);
            if(preset==InspectionPreset.AngledBounce) { p=new Vector3(0,1.4f,-3);v=new Vector3(2,-2,6); }
            if(preset==InspectionPreset.FlatContact) { p=new Vector3(0,1.24f,-2.5f);v=new Vector3(0,0,-7); }
            if(preset==InspectionPreset.BrushUp) { p=new Vector3(0,1.35f,-2.5f);v=new Vector3(0,0,-7); }
            if(preset==InspectionPreset.BrushDown) { p=new Vector3(0,1.12f,-2.5f);v=new Vector3(0,0,-7); }
            if(preset==InspectionPreset.Serve)
            {
                p=new Vector3(1.5f,.8f,-6.9f);v=new Vector3(-2.7f,5.5f,12);
                Motors[0].Reset(new Vector3(1.5f,0,-7.3f),new Vector3(1.5f,1,-7),Quaternion.identity);
                Motors[1].Reset(new Vector3(-1.5f,0,6.1f),new Vector3(-1.5f,1,5.5f),Quaternion.Euler(0,180,0));
            }
            // A paused local physics scene must show the reset pose before its
            // first simulation step. Rigidbody setters alone defer render sync.
            Ball.transform.SetPositionAndRotation(p,Quaternion.identity);
            Ball.position=p;Ball.rotation=Quaternion.identity;Ball.linearVelocity=v;Ball.angularVelocity=Vector3.zero;Ball.WakeUp();
            var trail=Ball.GetComponent<TrailRenderer>();if(trail!=null)trail.Clear();
            Physics.SyncTransforms();UpdateMarkers();RecordFrame();
        }
        public void Step(int selected=0,Vector3 translation=default,Vector3 rotation=default,Vector2 playerMove=default,bool demonstration=false)
        {
            if(AtTimeLimit)return;
            if(selected<0||selected>1)throw new ArgumentOutOfRangeException(nameof(selected));
            if(demonstration&&Elapsed<.3f&&translation==Vector3.zero)
            {
                if(Preset==InspectionPreset.FlatContact)translation=new Vector3(0,0,.4f);
                if(Preset==InspectionPreset.BrushUp)translation=new Vector3(0,.4f,.4f);
                if(Preset==InspectionPreset.BrushDown)translation=new Vector3(0,-.4f,.4f);
            }
            var input=new PaddleInput(translation,rotation,playerMove);
            StepBoth(selected==0?input:default,selected==1?input:default);
        }
        public void StepBoth(PaddleInput near,PaddleInput far)
        {
            if(AtTimeLimit)return;
            for(int i=0;i<2;i++)
            {
                var input=i==0?near:far;
                Motors[i].Step(input.Translation,input.Rotation,input.PlayerMove,Dt);
                if(RulesEnabled)Rules.ObservePlayer(i==0?-1:1,Motors[i].FeetInKitchen,Motors[i].PlayerVelocity.sqrMagnitude<.0001f,Dt);
            }
            var forces=AerodynamicModelV1.Evaluate(Ball.linearVelocity,Ball.angularVelocity,Configuration.AerodynamicParameters);
            Ball.AddForce(forces.TotalForce+Configuration.Gravity*Ball.mass,ForceMode.Force);
            Ball.angularVelocity*=AerodynamicModelV1.AngularVelocityMultiplier(Dt,Configuration.AerodynamicParameters);
            // Incoming values are sampled immediately before the solver step.
            // They are not a sub-step measurement at the exact contact instant.
            var incomingVelocity=Ball.linearVelocity;var incomingSpin=Ball.angularVelocity;
            physics.Simulate(Dt);Elapsed+=Dt;
            foreach(var contact in pending)
            {
                string name=contact.collider.name;
                int paddle=-1;
                if(contact.collider.attachedRigidbody==Motors[0].Body)paddle=0;
                if(contact.collider.attachedRigidbody==Motors[1].Body)paddle=1;
                if(paddle>=0 && name=="RoundedHittingFace")
                {
                    var result=PaddleSpinTransferV1.Evaluate(Ball.position,Ball.linearVelocity,Ball.angularVelocity,
                        Motors[paddle].ContactVelocity(contact.point),contact.point,contact.normal,Configuration);
                    Ball.linearVelocity=result.LinearVelocity;Ball.angularVelocity=result.AngularVelocity;
                    if(RulesEnabled)Rules.Hit(paddle==0?-1:1,Motors[paddle].FeetInKitchen);
                    name=paddle==0?"PaddleNear":"PaddleFar";
                }
                else if(name=="CourtSurface"||name=="OutCatchFloor"||name=="Granite reference slab")
                {
                    if(RulesEnabled)Rules.Bounce(contact.point);
                    if((Preset==InspectionPreset.CourtDrop||Preset==InspectionPreset.GraniteDrop)&&!rose&&Ball.linearVelocity.y>0)rose=true;
                }
                else if(paddle>=0 && RulesEnabled)Rules.Hit(paddle==0?-1:1,Motors[paddle].FeetInKitchen);
                // Net contact is not itself a fault. A net-touch ball can land legally.
                Contacts.Add(new InspectionContact {time=Elapsed,surface=name,point=contact.point,normal=contact.normal,
                    incomingVelocity=incomingVelocity,incomingSpin=incomingSpin,velocity=Ball.linearVelocity,spin=Ball.angularVelocity});
            }
            pending.Clear();
            if(rose&&!ReboundComplete)
            {
                FirstReboundHeight=Mathf.Max(FirstReboundHeight,Ball.position.y-CourtGeometryV1.BallRadius);
                if(Ball.linearVelocity.y<=0)ReboundComplete=true;
            }
            var p=Ball.position;
            if(RulesEnabled && (p.y<-.5f||Mathf.Abs(p.x)>5||Mathf.Abs(p.z)>10))Rules.Lost();
            if(!float.IsFinite(p.x)||!float.IsFinite(p.y)||!float.IsFinite(p.z))throw new InvalidOperationException("Non-finite ball state.");
            UpdateMarkers();RecordFrame();
        }
        private void RecordFrame()=>Frames.Add(new InspectionFrame {time=Elapsed,position=Ball.position,velocity=Ball.linearVelocity,spin=Ball.angularVelocity});
        public void Contact(Collider collider,Vector3 point,Vector3 normal)=>pending.Add((collider,point,normal));
        private void BuildPresentation()
        {
            foreach(var r in Root.GetComponentsInChildren<Renderer>())Paint(r.gameObject,new Color(.10f,.35f,.48f));
            Paint(Ball.gameObject,new Color(1,.87f,.10f));
            for(int i=0;i<2;i++)
            {
                var face=Motors[i].Body.transform.Find("RoundedHittingFace");
                Paint(face.gameObject,i==0?new Color(1,.35f,.12f):new Color(.15f,.75f,1));
                Paint(Motors[i].Body.transform.Find("NonContactHandle").gameObject,new Color(.15f,.15f,.15f));
                var marker=GameObject.CreatePrimitive(PrimitiveType.Cylinder);marker.name=i==0?"Orange player footprint":"Blue player footprint";
                marker.transform.SetParent(Root.transform);marker.transform.localScale=new Vector3(PaddleMotor.PlayerRadius*2,.007f,PaddleMotor.PlayerRadius*2);
                UnityEngine.Object.DestroyImmediate(marker.GetComponent<Collider>());Paint(marker,i==0?new Color(1,.35f,.12f):new Color(.15f,.75f,1));markers[i]=marker.transform;
            }
            foreach(var c in Fixture.NetColliders)Paint(c.gameObject,new Color(.7f,.8f,.8f));
            float width=CourtGeometryV1.CourtWidth,length=CourtGeometryV1.CourtLength,kitchen=CourtGeometryV1.NonVolleyZoneDepth;
            foreach(float sign in new[]{-1f,1f})
            {
                Line(new Vector3(sign*(width/2-.0254f),.003f,0),new Vector3(.0508f,.003f,length),Color.white);
                Line(new Vector3(0,.003f,sign*(length/2-.0254f)),new Vector3(width,.003f,.0508f),Color.white);
                Line(new Vector3(0,.004f,sign*(kitchen-.0254f)),new Vector3(width,.003f,.0508f),Color.white);
                Line(new Vector3(0,.003f,sign*(length/2+kitchen)/2),new Vector3(.0508f,.003f,length/2-kitchen),Color.white);
                Line(new Vector3(0,.001f,sign*kitchen/2),new Vector3(width-.1016f,.001f,kitchen-.0508f),new Color(.11f,.45f,.35f));
            }
            var trail=Ball.gameObject.AddComponent<TrailRenderer>();trail.time=.35f;trail.startWidth=.022f;trail.endWidth=.003f;
            trail.material=Ball.GetComponent<Renderer>().sharedMaterial;
        }
        private void UpdateMarkers()
        {
            for(int i=0;i<2;i++)if(markers[i]!=null)markers[i].position=Motors[i].PlayerPosition+Vector3.up*.009f;
        }
        private void Line(Vector3 p,Vector3 size,Color color)
        {
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name="Non-contact court marking";go.transform.SetParent(Root.transform);
            go.transform.position=p;go.transform.localScale=size;UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());Paint(go,color);
        }
        private void Paint(GameObject go,Color color)
        {
            var r=go.GetComponent<Renderer>();if(r==null)return;
            var m=new Material(Shader.Find("Universal Render Pipeline/Lit")??Shader.Find("Standard")){color=color};visuals.Add(m);r.sharedMaterial=m;
        }
        public void Dispose()
        {
            Fixture.Destroy();foreach(var m in visuals)UnityEngine.Object.DestroyImmediate(m);
            UnityEngine.Object.DestroyImmediate(graniteMaterial);
            if(scene.IsValid()&&scene.isLoaded)SceneManager.UnloadSceneAsync(scene);
        }
    }
}
