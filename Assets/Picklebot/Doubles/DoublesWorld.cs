using System;
using System.Collections.Generic;
using Picklebot.Core;
using Picklebot.Simulation;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Picklebot.Doubles
{
    [Serializable] public sealed class DoublesContact
    {
        public float time;public int player=-1;public string surface;
        public Vector3 point,normal,incoming,velocity,spin;
    }
    [Serializable] public sealed class DoublesFrame
    {public float time;public Vector3 ball;public Vector3[] players,paddles;public Quaternion[] rotations;}
    public sealed class DoublesWorld : IDisposable
    {
        public const float Dt=1f/240f;
        public readonly PicklebotEnvironmentFixtureV1 Fixture;
        public readonly Rigidbody Ball;
        public readonly PlayerBody[] Players=new PlayerBody[4];
        public readonly DoublesRules Rules;
        public readonly List<DoublesContact> Contacts=new();
        public readonly List<DoublesFrame> Frames=new();
        public float Time {get;private set;}
        public bool ServeBounced {get;private set;}
        public bool FixedBallServe {get;set;}
        public bool RecordFrames;
        public SimulationConfigV1 Configuration=>Fixture.Configuration;
        public GameObject Root=>Fixture.Root;
        private readonly Scene scene;
        private readonly PhysicsScene physics;
        private readonly List<(Collider collider,Vector3 point,Vector3 normal)> pending=new();
        private readonly List<Material> materials=new();
        private readonly Dictionary<Collider,int> bodyContacts=new();
        private readonly HashSet<Collider> paddleTouching=new();
        private readonly bool[] contactEpisode=new bool[4];
        private readonly float[] contactStarted=new float[4];
        public DoublesWorld(bool visible):this(visible,0) { }
        public DoublesWorld(bool visible,int initialServer,bool initialServerOnRight=true,int initialScore0=0,int initialScore1=0,int initialServerNumber=2,bool swapReceivingPlayers=false)
        {
            Rules=new DoublesRules(initialServer,initialServerOnRight,initialScore0,initialScore1,initialServerNumber,swapReceivingPlayers);
            scene=SceneManager.CreateScene("Doubles-"+Guid.NewGuid().ToString("N"),new CreateSceneParameters(LocalPhysicsMode.Physics3D));physics=scene.GetPhysicsScene();
            Fixture=PicklebotEnvironmentFactoryV1.Create("Doubles / outdoor acrylic / provisional");Ball=Fixture.Environment.Ball;var first=Fixture.Environment.Paddle;
            UnityEngine.Object.DestroyImmediate(Ball.GetComponent<BallContactReporterV1>());UnityEngine.Object.DestroyImmediate(Fixture.Environment);
            SceneManager.MoveGameObjectToScene(Root,scene);Ball.gameObject.AddComponent<DoublesContacts>().World=this;
            var skin=Material(new Color(.70f,.48f,.34f));var dark=Material(new Color(.08f,.11f,.16f));
            var court=Material(new Color(.08f,.32f,.43f));var white=Material(new Color(.85f,.92f,.92f));
            var orange=Material(new Color(1,.32f,.12f));var blue=Material(new Color(.13f,.55f,1));
            foreach(var r in Root.GetComponentsInChildren<Renderer>())r.sharedMaterial=court;
            var oldApron=Root.transform.Find("OutCatchFloor").GetComponent<Collider>();oldApron.enabled=false;
            var courtMaterial=Root.transform.Find("CourtSurface").GetComponent<Collider>().sharedMaterial;
            // A level acrylic apron. Separate strips avoid two coplanar ground
            // colliders beneath an in-bounds bounce.
            foreach(float s in new[]{-1f,1f})
            {
                Ground(new Vector3(s*4.524f,-.025f,0),new Vector3(2.952f,.05f,20),courtMaterial,court);
                Ground(new Vector3(0,-.025f,s*8.3528f),new Vector3(6.096f,.05f,3.2944f),courtMaterial,court);
            }
            Ball.GetComponent<Renderer>().sharedMaterial=Material(new Color(.96f,.96f,.1f));
            for(int i=0;i<4;i++)
            {
                var paddle=i==0?first:UnityEngine.Object.Instantiate(first.gameObject,Root.transform).GetComponent<Rigidbody>();paddle.name="Paddle-"+i;
                paddle.transform.Find("RoundedHittingFace").GetComponent<Renderer>().sharedMaterial=i<2?orange:blue;
                paddle.transform.Find("NonContactHandle").GetComponent<Renderer>().sharedMaterial=dark;
                Players[i]=new PlayerBody(i,paddle,Root.transform,i<2?orange:blue,skin,dark,visible);
                foreach(var c in Players[i].Root.GetComponentsInChildren<Collider>())bodyContacts.Add(c,i);
            }
            foreach(var c in Fixture.NetColliders)c.GetComponent<Renderer>().enabled=false;
            for(int n=0;n<=64;n++)
            {
                float x=Mathf.Lerp(-3.3528f,3.3528f,n/64f);float height=Mathf.Lerp(.8636f,.9144f,Mathf.Min(1,Mathf.Abs(x)/3.048f));
                Mark(new Vector3(x,height/2,0),new Vector3(.008f,height,.008f),dark);
            }
            for(int n=1;n<=8;n++)Mark(new Vector3(0,n*.1f,0),new Vector3(6.7056f,.008f,.008f),dark);
            for(int side=-1;side<=1;side+=2)
            {
                var post=GameObject.CreatePrimitive(PrimitiveType.Cylinder);post.name="NetPost";post.transform.SetParent(Root.transform);post.transform.position=new Vector3(side*3.3528f,.475f,0);post.transform.localScale=new Vector3(.06f,.475f,.06f);post.GetComponent<Renderer>().sharedMaterial=dark;
                var tape=new GameObject("Net tape");tape.transform.SetParent(Root.transform);var line=tape.AddComponent<LineRenderer>();line.positionCount=2;line.SetPosition(0,new Vector3(0,.8636f,0));line.SetPosition(1,new Vector3(side*3.3528f,.9144f,0));line.startWidth=line.endWidth=.028f;line.sharedMaterial=white;
            }
            foreach(float side in new[]{-1f,1f})
            {
                Mark(new Vector3(side*(3.048f-.0254f),.003f,0),new Vector3(.0508f,.003f,13.4112f),white);
                Mark(new Vector3(0,.003f,side*(6.7056f-.0254f)),new Vector3(6.096f,.003f,.0508f),white);
                Mark(new Vector3(0,.004f,side*(2.1336f-.0254f)),new Vector3(6.096f,.003f,.0508f),white);
                Mark(new Vector3(0,.003f,side*4.4196f),new Vector3(.0508f,.003f,4.572f),white);
            }
            Ball.solverIterations=Ball.solverVelocityIterations=12;Ball.sleepThreshold=0;Ball.maxAngularVelocity=Configuration.MaximumBallAngularSpeed;
            foreach(var c in Root.GetComponentsInChildren<Collider>())c.contactOffset=.001f;
            if(!visible)foreach(var r in Root.GetComponentsInChildren<Renderer>())r.enabled=false;
            else {var trail=Ball.gameObject.AddComponent<TrailRenderer>();trail.time=.25f;trail.startWidth=.02f;trail.endWidth=.001f;trail.sharedMaterial=Ball.GetComponent<Renderer>().sharedMaterial;}
            RecordFrames=visible;ResetRally();
        }
        private Material Material(Color color) {var m=new Material(Shader.Find("Universal Render Pipeline/Lit")??Shader.Find("Standard")){color=color};materials.Add(m);return m;}
        private void Mark(Vector3 p,Vector3 scale,Material material)
        {var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name="Court line / non-contact";go.transform.SetParent(Root.transform);go.transform.position=p;go.transform.localScale=scale;UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());go.GetComponent<Renderer>().sharedMaterial=material;}
        private void Ground(Vector3 p,Vector3 scale,PhysicsMaterial physical,Material visual)
        {var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name="OutCatchFloor";go.transform.SetParent(Root.transform);go.transform.position=p;go.transform.localScale=scale;go.GetComponent<Collider>().sharedMaterial=physical;go.GetComponent<Renderer>().sharedMaterial=visual;}
        public void ResetRally()
        {
            if(Rules.Dead)Rules.BeginRally();Time=0;ServeBounced=false;Contacts.Clear();Frames.Clear();pending.Clear();paddleTouching.Clear();Array.Clear(contactEpisode,0,4);
            for(int i=0;i<4;i++)Players[i].Reset(new Vector3(Rules.ServiceX(i),0,DoublesRules.Side(i/2)*(i==Rules.Server?7.65f:6.0f)));
            // A released drop serve starts at rest. All later speed and spin come
            // from gravity, aerodynamics and collisions, including paddle contact.
            var p=new Vector3(Rules.ServiceX(Rules.Server),1.4f,DoublesRules.Side(Rules.ServingTeam)*7.05f);
            Ball.transform.SetPositionAndRotation(p,Quaternion.identity);Ball.position=p;Ball.rotation=Quaternion.identity;Ball.linearVelocity=Ball.angularVelocity=Vector3.zero;Ball.WakeUp();
            var trail=Ball.GetComponent<TrailRenderer>();if(trail!=null)trail.Clear();Physics.SyncTransforms();
        }
        public void Contact(Collider collider,Vector3 point,Vector3 normal)=>pending.Add((collider,point,normal));
        public void ContactEnded(Collider collider)=>paddleTouching.Remove(collider);
        public bool IsPaddleContactActive(int player)
        {
            if(player<0||player>=Players.Length)throw new ArgumentOutOfRangeException(nameof(player));
            foreach(var collider in paddleTouching)
                if(collider.attachedRigidbody==Players[player].Paddle)return true;
            return false;
        }
        public void Simulate(bool suspendBallForces=false)
        {
            for(int i=0;i<4;i++)Rules.Feet(i,Players[i].FeetInKitchen,Players[i].BothFeetOutside,Players[i].BalanceRecovered,Time);
            for(int i=0;i<4;i++)
            {
                bool touching=false;foreach(var c in paddleTouching)if(c.attachedRigidbody==Players[i].Paddle)touching=true;
                if(!touching)contactEpisode[i]=false;
                else if(Time-contactStarted[i]>.1f)Rules.Fail(i/2,Fault.Carry,Time,default,i);
                // Body and carried paddle contact with the net is a player fault.
                if(Mathf.Abs(Players[i].Position.z)<1.2f||Mathf.Abs(Players[i].Paddle.position.z)<.4f)
                foreach(var c in Players[i].Root.GetComponentsInChildren<Collider>())foreach(var net in Fixture.NetColliders)
                    if(c.bounds.Intersects(net.bounds)&&Physics.ComputePenetration(c,c.transform.position,c.transform.rotation,net,net.transform.position,net.transform.rotation,out _,out _))Rules.TouchNet(i,Time);
                if(Mathf.Abs(Players[i].Paddle.position.z)<.4f)
                foreach(var c in Players[i].Paddle.GetComponentsInChildren<Collider>())foreach(var net in Fixture.NetColliders)
                    if(c.bounds.Intersects(net.bounds)&&Physics.ComputePenetration(c,c.transform.position,c.transform.rotation,net,net.transform.position,net.transform.rotation,out _,out _))Rules.TouchNet(i,Time);
            }
            var incoming=Ball.linearVelocity;
            // A held ball is positioned by its hand attachment. Dynamic forces
            // and spin decay resume on release; Unity rejects kinematic velocity writes.
            if(!Ball.isKinematic&&!suspendBallForces)
            {
                Ball.AddForce(Configuration.Gravity*Ball.mass+AerodynamicModelV1.Evaluate(incoming,Ball.angularVelocity,Configuration.AerodynamicParameters).TotalForce);
                Ball.angularVelocity*=AerodynamicModelV1.AngularVelocityMultiplier(Dt,Configuration.AerodynamicParameters);
            }
            Physics.SyncTransforms();physics.Simulate(Dt);Time+=Dt;
            var hitThisStep=new HashSet<int>();var faceThisStep=new HashSet<int>();bool floorThisStep=false;
            foreach(var c in pending)
            {
                int player=-1;for(int i=0;i<4;i++)if(c.collider.attachedRigidbody==Players[i].Paddle)player=i;
                string surface=c.collider.name;
                // A simultaneous handle callback must not consume face transfer.
                // Face physics and the once-per-player rule hit are independent.
                if(player>=0&&surface=="RoundedHittingFace"&&faceThisStep.Add(player))
                {
                    var result=PaddleSpinTransferV1.Evaluate(Ball.position,Ball.linearVelocity,Ball.angularVelocity,Players[player].ContactVelocity(c.point),c.point,c.normal,Configuration);
                    Ball.linearVelocity=result.LinearVelocity;Ball.angularVelocity=result.AngularVelocity;
                }
                if(player>=0&&hitThisStep.Add(player))
                {
                    bool continuing=contactEpisode[player];if(!continuing)contactStarted[player]=Time;contactEpisode[player]=true;
                    if(Rules.Phase==RallyPhase.AwaitServe)
                    {
                        var b=Players[player];bool legalFeet=Mathf.Abs(b.LeftFoot.z)-.14f>DoublesRules.HalfLength&&Mathf.Abs(b.RightFoot.z)-.14f>DoublesRules.HalfLength
                            &&b.LeftFoot.x*Rules.ServiceX(player)>0&&b.RightFoot.x*Rules.ServiceX(player)>0
                            &&Mathf.Abs(b.LeftFoot.x)+.065f<DoublesRules.HalfWidth&&Mathf.Abs(b.RightFoot.x)+.065f<DoublesRules.HalfWidth;
                        legalFeet&=b.LeftFoot.y<=.061f||b.RightFoot.y<=.061f;
                        if(FixedBallServe)Rules.FixedBallServe(player,legalFeet,Time);
                        else Rules.Serve(player,legalFeet,true,true,ServeBounced,false,false,false,Time);
                    }
                    else if(!continuing)Rules.Hit(player,Time,c.point);
                }
                else if(bodyContacts.TryGetValue(c.collider,out int body))Rules.BodyContact(body,Time);
                else if((surface=="CourtSurface"||surface=="OutCatchFloor")&&!floorThisStep)
                {floorThisStep=true;if(Rules.Phase==RallyPhase.AwaitServe)ServeBounced=true;else Rules.Bounce(c.point,Time);}
                else if(surface=="NetPost")Rules.PermanentObject(Time);
                Contacts.Add(new DoublesContact {time=Time,player=player,surface=surface,point=c.point,normal=c.normal,incoming=incoming,velocity=Ball.linearVelocity,spin=Ball.angularVelocity});
                if(player>=0)paddleTouching.Add(c.collider);
            }
            pending.Clear();
            if(!Rules.Dead&&(Ball.position.y<-.5f||Mathf.Abs(Ball.position.x)>6||Mathf.Abs(Ball.position.z)>10))Rules.Lost(Time);
            if(!Rules.Dead&&Time>30)Rules.Truncate(Time);
            if(Rules.Phase==RallyPhase.AwaitServe&&Time>10)Rules.Fail(Rules.ServingTeam,Fault.ServeTimeout,Time);
            if(!float.IsFinite(Ball.position.x)||!float.IsFinite(Ball.linearVelocity.y))throw new InvalidOperationException("Non-finite doubles ball state.");
            for(int i=0;i<4;i++)Players[i].Draw();
            if(RecordFrames&&Mathf.RoundToInt(Time/Dt)%4==0)
            {
                var f=new DoublesFrame {time=Time,ball=Ball.position,players=new Vector3[4],paddles=new Vector3[4],rotations=new Quaternion[4]};
                for(int i=0;i<4;i++){f.players[i]=Players[i].Position;f.paddles[i]=Players[i].Paddle.position;f.rotations[i]=Players[i].Paddle.rotation;}Frames.Add(f);
            }
        }
        public void Dispose()
        {Fixture.Destroy();foreach(var m in materials)UnityEngine.Object.DestroyImmediate(m);if(scene.IsValid()&&scene.isLoaded)SceneManager.UnloadSceneAsync(scene);}
    }
    public sealed class DoublesContacts : MonoBehaviour
    {
        public DoublesWorld World;
        private void OnCollisionEnter(Collision collision)
        {if(collision.contactCount>0){var p=collision.GetContact(0);World?.Contact(collision.collider,p.point,p.normal);}}
        private void OnCollisionExit(Collision collision)=>World?.ContactEnded(collision.collider);
    }
}
