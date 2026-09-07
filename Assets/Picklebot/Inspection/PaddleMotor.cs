using System;
using UnityEngine;

namespace Picklebot.Inspection
{
    public sealed class PaddleMotor
    {
        public const float Reach=1.15f, MinHeight=.25f, MaxHeight=2.5f, PlayerRadius=.22f;
        public const float MaxSpeed=5f, Acceleration=24f, MaxAngularSpeed=6f, AngularAcceleration=30f;
        public Vector3 PlayerPosition { get; private set; }
        public Vector3 LinearVelocity { get; private set; }
        public Vector3 AngularVelocity { get; private set; }
        public Vector3 PlayerVelocity { get; private set; }
        public readonly Rigidbody Body;
        private readonly int side;
        public PaddleMotor(Rigidbody body,int playerSide) { Body=body;side=playerSide; }
        public void Reset(Vector3 player,Vector3 paddle,Quaternion rotation)
        {
            PlayerPosition=player;LinearVelocity=AngularVelocity=PlayerVelocity=Vector3.zero;
            Body.transform.SetPositionAndRotation(paddle,rotation);
            Body.position=paddle;Body.rotation=rotation;
        }
        public bool FeetInKitchen=>Mathf.Abs(PlayerPosition.x)<=Picklebot.Core.CourtGeometryV1.HalfWidth+PlayerRadius &&
            Mathf.Abs(PlayerPosition.z)<=Picklebot.Core.CourtGeometryV1.NonVolleyZoneDepth+PlayerRadius;
        public void Step(Vector3 translation,Vector3 rotation,Vector2 movement,float dt)
        {
            if(!Finite(translation)||!Finite(rotation)||!float.IsFinite(movement.x)||!float.IsFinite(movement.y))throw new ArgumentException("Non-finite motor input.");
            var requested=new Vector3(movement.x,0,movement.y);
            PlayerVelocity=Vector3.MoveTowards(PlayerVelocity,Vector3.ClampMagnitude(requested,1)*3f,12f*dt);
            var oldPlayer=PlayerPosition;var next=oldPlayer+PlayerVelocity*dt;
            next.x=Mathf.Clamp(next.x,-4.5f,4.5f);next.z=side*Mathf.Clamp(side*next.z,.35f,8.5f);
            PlayerPosition=next;PlayerVelocity=(next-oldPlayer)/dt;
            LinearVelocity=Vector3.MoveTowards(LinearVelocity,Vector3.ClampMagnitude(translation,1)*MaxSpeed,Acceleration*dt);
            AngularVelocity=Vector3.MoveTowards(AngularVelocity,Vector3.ClampMagnitude(rotation,1)*MaxAngularSpeed,AngularAcceleration*dt);
            var desired=Body.position+(LinearVelocity+PlayerVelocity)*dt;
            desired.y=Mathf.Clamp(desired.y,MinHeight,MaxHeight);
            var horizontal=new Vector3(desired.x-next.x,0,desired.z-next.z);
            horizontal=Vector3.ClampMagnitude(horizontal,Reach);
            desired.x=next.x+horizontal.x;desired.z=side*Mathf.Max(.08f,side*(next.z+horizontal.z));
            // Record actual motion after reach limits for contact-point spin.
            var delta=desired-Body.position;
            delta=Vector3.ClampMagnitude(delta,MaxSpeed*dt);
            LinearVelocity=delta/dt-PlayerVelocity;
            Body.MovePosition(Body.position+delta);
            float angle=AngularVelocity.magnitude*dt;
            if(angle>0)Body.MoveRotation(Quaternion.AngleAxis(angle*Mathf.Rad2Deg,AngularVelocity.normalized)*Body.rotation);
        }
        public Vector3 ContactVelocity(Vector3 point)=>LinearVelocity+PlayerVelocity+Vector3.Cross(AngularVelocity,point-Body.position);
        private static bool Finite(Vector3 v)=>float.IsFinite(v.x)&&float.IsFinite(v.y)&&float.IsFinite(v.z);
    }
}
