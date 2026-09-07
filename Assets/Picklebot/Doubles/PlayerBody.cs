using System.Collections.Generic;
using UnityEngine;

namespace Picklebot.Doubles
{
    // Analytic, kinematic IK. The same constrained hand pose controls the paddle
    // and the visible arm. This is not a learned muscle or balance simulation.
    public sealed class PlayerBody
    {
        public const float Speed=3.8f, Acceleration=14f, PaddleSpeed=12f, PaddleAcceleration=100f;
        public const float AngularSpeed=12f, ArmUpper=.32f, ArmLower=.31f, Radius=.28f;
        public static readonly Vector3 GripLocal=new(0,-.1397f,0);
        public readonly int Id;
        public readonly Rigidbody Paddle;
        public Vector3 Position { get; private set; }
        public Vector3 Velocity { get; private set; }
        public Vector3 PaddleVelocity { get; private set; }
        public Vector3 AngularVelocity { get; private set; }
        public Vector3 LeftFoot { get; private set; }
        public Vector3 RightFoot { get; private set; }
        public Vector3 Hand=>Paddle.position+Paddle.rotation*GripLocal;
        public Vector3 Shoulder=>Position+new Vector3(-Side*.19f,shoulderHeight,0);
        public bool FeetInKitchen=>FootInKitchen(LeftFoot)||FootInKitchen(RightFoot);
        public bool BothFeetOutside=>!FeetInKitchen&&LeftFoot.y<.061f&&RightFoot.y<.061f;
        public bool BalanceRecovered=>Velocity.z*-Side<=.02f&&BothFeetOutside;
        public int Side=>Id<2?-1:1;
        private float shoulderHeight=1.36f, stepProgress=1;
        private int steppingFoot;
        private Vector3 stepFrom,stepTo;
        private readonly Transform[] parts;
        public readonly GameObject Root;
        public readonly CapsuleCollider Torso;
        public PlayerBody(int id,Rigidbody paddle,Transform parent,Material shirt,Material skin,Material dark,bool visible)
        {
            Id=id;Paddle=paddle;Root=new GameObject("Player "+(id+1)+" / kinematic IK");Root.transform.SetParent(parent);
            var trunk=new GameObject("PlayerBodyContact-"+id);trunk.transform.SetParent(Root.transform);
            Torso=trunk.AddComponent<CapsuleCollider>();Torso.radius=.19f;Torso.height=.9f;Torso.contactOffset=.001f;
            parts=new Transform[14];
            string[] names={"Torso","Head","Right upper arm","Right forearm","Left upper arm","Left forearm","Right thigh","Right shin","Left thigh","Left shin","Right shoe","Left shoe","Right hand grip","Left hand"};
            for(int i=0;i<parts.Length;i++)
            {
                var go=GameObject.CreatePrimitive(i==10||i==11?PrimitiveType.Cube:i==1||i>=12?PrimitiveType.Sphere:PrimitiveType.Capsule);
                go.name=names[i];go.transform.SetParent(Root.transform);
                if(i==0||i>=12)Object.DestroyImmediate(go.GetComponent<Collider>());
                else go.GetComponent<Collider>().contactOffset=.001f;
                var r=go.GetComponent<Renderer>();r.sharedMaterial=i==1||i==3||i==5||i>=12?skin:i==0||i==2||i==4?shirt:dark;r.enabled=visible;parts[i]=go.transform;
            }
        }
        public static bool FootInKitchen(Vector3 foot)=>foot.y<.08f&&Mathf.Abs(foot.x)<=DoublesRules.HalfWidth+.065f&&Mathf.Abs(foot.z)<=DoublesRules.Kitchen+.14f;
        public void Reset(Vector3 position)
        {
            Position=position;Velocity=PaddleVelocity=AngularVelocity=Vector3.zero;shoulderHeight=1.36f;stepProgress=1;
            LeftFoot=Position+new Vector3(Side*.16f,.055f,0);RightFoot=Position+new Vector3(-Side*.16f,.055f,0);
            var rot=Quaternion.LookRotation(Vector3.forward*-Side);
            var p=position+new Vector3(-Side*.19f,1.10f,-Side*.46f);
            Paddle.transform.SetPositionAndRotation(p,rot);Paddle.position=p;Paddle.rotation=rot;
            FeetAndPose(0);
        }
        public static Vector3 Bend(Vector3 root,Vector3 target,Vector3 hint,float first,float second)
        {
            var d=target-root;float distance=Mathf.Clamp(d.magnitude,.005f,first+second-.0001f);var axis=d.sqrMagnitude<1e-8f?Vector3.down:d.normalized;
            var bend=Vector3.ProjectOnPlane(hint-root,axis).normalized;if(bend.sqrMagnitude<.01f)bend=Vector3.Cross(axis,Vector3.forward).normalized;
            if(bend.sqrMagnitude<.01f)bend=Vector3.right;
            float along=(first*first-second*second+distance*distance)/(2*distance);
            return root+axis*along+bend*Mathf.Sqrt(Mathf.Max(0,first*first-along*along));
        }
        public void Step(Vector3 moveTarget,Vector3 paddleTarget,Quaternion targetRotation,Vector3 feedVelocity,PlayerBody partner,float dt)
        {
            var old=Position;moveTarget.y=0;
            var wanted=Vector3.ClampMagnitude((moveTarget-Position)*4,Speed);
            var separation=Position-partner.Position;separation.y=0;
            if(separation.magnitude<.85f)wanted+=separation.normalized*(.85f-separation.magnitude)*8;
            Velocity=Vector3.MoveTowards(Velocity,Vector3.ClampMagnitude(wanted,Speed),Acceleration*dt);
            var next=Position+Velocity*dt;
            next.x=Mathf.Clamp(next.x,-4.2f,4.2f);next.z=Side*Mathf.Clamp(next.z*Side,.38f,8.1f);
            separation=next-partner.Position;separation.y=0;
            if(separation.magnitude<Radius*2)next=partner.Position+(separation.sqrMagnitude<1e-6f?Vector3.right*(Id%2==0?1:-1):separation.normalized)*Radius*2;
            Position=next;Velocity=(next-old)/dt;
            shoulderHeight=Mathf.MoveTowards(shoulderHeight,Mathf.Clamp(paddleTarget.y+.20f,.72f,1.5f),1.6f*dt);
            var facing=Quaternion.LookRotation(Vector3.forward*-Side);
            var local=Quaternion.Inverse(facing)*targetRotation;var angles=local.eulerAngles;
            angles=new Vector3(Mathf.Clamp(Mathf.DeltaAngle(0,angles.x),-65,65),Mathf.Clamp(Mathf.DeltaAngle(0,angles.y),-105,105),Mathf.Clamp(Mathf.DeltaAngle(0,angles.z),-85,85));
            targetRotation=facing*Quaternion.Euler(angles);
            var rotation=Quaternion.RotateTowards(Paddle.rotation,targetRotation,AngularSpeed*Mathf.Rad2Deg*dt);
            var delta=rotation*Quaternion.Inverse(Paddle.rotation);delta.ToAngleAxis(out float angle,out var axis);if(angle>180)angle-=360;
            AngularVelocity=angle==0?Vector3.zero:axis*angle*Mathf.Deg2Rad/dt;
            var targetHand=paddleTarget+rotation*GripLocal;
            targetHand=Shoulder+Vector3.ClampMagnitude(targetHand-Shoulder,ArmUpper+ArmLower-.01f);
            var wantedPaddle=targetHand-rotation*GripLocal;
            var speed=Vector3.ClampMagnitude(feedVelocity+(wantedPaddle-Paddle.position)*28,PaddleSpeed);
            PaddleVelocity=Vector3.MoveTowards(PaddleVelocity,speed,PaddleAcceleration*dt);
            var newPaddle=Paddle.position+PaddleVelocity*dt;
            // Reach is a hard limit after movement and rotation, not a visual stretch.
            var hand=Shoulder+Vector3.ClampMagnitude(newPaddle+rotation*GripLocal-Shoulder,ArmUpper+ArmLower-.01f);
            newPaddle=hand-rotation*GripLocal;PaddleVelocity=(newPaddle-Paddle.position)/dt;
            Paddle.MovePosition(newPaddle);Paddle.MoveRotation(rotation);
            FeetAndPose(dt);
        }
        public Vector3 ContactVelocity(Vector3 point)=>PaddleVelocity+Vector3.Cross(AngularVelocity,point-Paddle.position);
        public void Draw()=>Pose();
        private void FeetAndPose(float dt)
        {
            var leftGoal=Position+new Vector3(Side*.16f,.055f,0)+Velocity*.10f;
            var rightGoal=Position+new Vector3(-Side*.16f,.055f,0)+Velocity*.10f;
            if(stepProgress>=1)
            {
                float ld=Vector3.Distance(LeftFoot,leftGoal),rd=Vector3.Distance(RightFoot,rightGoal);
                if(Mathf.Max(ld,rd)>.18f)
                {steppingFoot=ld>rd?0:1;stepFrom=steppingFoot==0?LeftFoot:RightFoot;stepTo=steppingFoot==0?leftGoal:rightGoal;stepProgress=0;}
            }
            if(stepProgress<1)
            {
                stepProgress=Mathf.Min(1,stepProgress+dt/.14f);float t=stepProgress*stepProgress*(3-2*stepProgress);
                var foot=Vector3.Lerp(stepFrom,stepTo,t)+Vector3.up*Mathf.Sin(stepProgress*Mathf.PI)*.08f;
                if(steppingFoot==0)LeftFoot=foot;else RightFoot=foot;
            }
            Torso.transform.position=Position+Vector3.up*(shoulderHeight-.3f);Pose();
        }
        private void Segment(int i,Vector3 a,Vector3 b,float radius)
        {parts[i].position=(a+b)*.5f;parts[i].rotation=Quaternion.FromToRotation(Vector3.up,b-a);parts[i].localScale=new Vector3(radius*2,(b-a).magnitude*.5f,radius*2);}
        private void Sphere(int i,Vector3 p,Vector3 size) {parts[i].position=p;parts[i].localScale=size;}
        private void Pose()
        {
            var pelvis=Position+Vector3.up*Mathf.Min(.85f,shoulderHeight-.48f);var chest=Position+Vector3.up*(shoulderHeight-.04f);
            Segment(0,pelvis,chest,.18f);Sphere(1,Position+Vector3.up*(shoulderHeight+.21f),new Vector3(.23f,.28f,.23f));
            var shoulder=Shoulder;var hand=Hand;
            var elbow=Bend(shoulder,hand,shoulder+new Vector3(-Side*.5f,-.3f,Side*.15f),ArmUpper,ArmLower);
            Segment(2,shoulder,elbow,.055f);Segment(3,elbow,hand,.043f);Sphere(12,hand,Vector3.one*.085f);
            var other=Position+new Vector3(Side*.19f,shoulderHeight,0);var otherHand=Position+new Vector3(Side*.28f,shoulderHeight-.35f,-Side*.27f);
            var otherElbow=Bend(other,otherHand,other+new Vector3(Side*.4f,-.3f,Side*.1f),ArmUpper,ArmLower);
            Segment(4,other,otherElbow,.055f);Segment(5,otherElbow,otherHand,.043f);Sphere(13,otherHand,Vector3.one*.085f);
            for(int leg=0;leg<2;leg++)
            {
                var hip=pelvis+Vector3.right*((leg==0?-Side:Side)*.13f);var foot=leg==0?RightFoot:LeftFoot;
                var knee=Bend(hip,foot,hip+new Vector3(0,-.2f,-Side),.46f,.46f);
                Segment(6+leg*2,hip,knee,.075f);Segment(7+leg*2,knee,foot,.055f);
                Sphere(10+leg,foot+new Vector3(0,0,-Side*.045f),new Vector3(.13f,.11f,.28f));parts[10+leg].rotation=Quaternion.identity;
            }
        }
    }
}
