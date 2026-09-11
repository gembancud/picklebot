using System;
using UnityEngine;

namespace Picklebot.Doubles
{
    // Explicit opt-in adapter data. The default legacy controller never sets it.
    public struct PlayerBodyFrame
    {
        public Vector3 position,velocity,pelvis,shoulder,leftFoot,rightFoot,leftHip,rightHip,leftKnee,rightKnee;
        public Vector3 paddlePosition,paddleVelocity,paddleAngularVelocity;
        public Quaternion paddleRotation;
        public bool articulatedUpperBody;
        public Vector3 rightElbow,rightWrist;
        public Quaternion torsoRotation;
        public float yaw,leftFootYaw,rightFootYaw,offHandLift;
        public bool touchesKitchen,bothFeetOutside,balanceRecovered;
    }
    public sealed partial class PlayerBody
    {
        private bool externalDriven;
        private PlayerBodyFrame externalFrame;
        public void ApplyExternalFrame(PlayerBodyFrame frame,bool initialize=false)
        {
            foreach(var v in new[]{frame.position,frame.velocity,frame.pelvis,frame.shoulder,frame.leftFoot,frame.rightFoot,
                frame.leftHip,frame.rightHip,frame.leftKnee,frame.rightKnee,frame.paddlePosition,frame.paddleVelocity,frame.paddleAngularVelocity})
                if(!float.IsFinite(v.x)||!float.IsFinite(v.y)||!float.IsFinite(v.z))throw new ArgumentException("Non-finite body frame.");
            if(!float.IsFinite(frame.offHandLift)||frame.offHandLift<0||frame.offHandLift>140)throw new ArgumentException("Off-hand lift outside bounds.");
            var q=frame.paddleRotation;float norm=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;
            if(!float.IsFinite(norm)||Mathf.Abs(norm-1)>.001f||!float.IsFinite(frame.yaw)||!float.IsFinite(frame.leftFootYaw)||!float.IsFinite(frame.rightFootYaw))
                throw new ArgumentException("Invalid body rotation.");
            if(Vector3.Distance(frame.paddlePosition+q*GripLocal,frame.shoulder)>.62001f)
                throw new ArgumentException("External hand exceeds arm reach.");
            if(frame.articulatedUpperBody)
            {
                var t=frame.torsoRotation;float n=t.x*t.x+t.y*t.y+t.z*t.z+t.w*t.w;
                var e=frame.rightElbow;var w=frame.rightWrist;var h=frame.paddlePosition+q*GripLocal;
                if(!float.IsFinite(n)||Mathf.Abs(n-1)>.001f||!float.IsFinite(e.x)||!float.IsFinite(e.y)||!float.IsFinite(e.z)
                    ||Mathf.Abs(Vector3.Distance(frame.shoulder,e)-ArmUpper)>.0001f
                    ||!float.IsFinite(w.x)||!float.IsFinite(w.y)||!float.IsFinite(w.z)
                    ||Mathf.Abs(Vector3.Distance(e,w)-.25f)>.0001f
                    ||Mathf.Abs(Vector3.Distance(w,h)-.06f)>.0001f)
                    throw new ArgumentException("Invalid articulated arm or torso frame.");
            }
            if(!externalDriven&&!initialize)throw new InvalidOperationException("Initialize external control at rally reset first.");
            if(externalDriven&&initialize)throw new InvalidOperationException("Cannot reinitialize during external control; reset the rally first.");
            externalDriven=true;externalFrame=frame;
            Position=frame.position;Velocity=frame.velocity;LeftFoot=frame.leftFoot;RightFoot=frame.rightFoot;
            PaddleVelocity=frame.paddleVelocity;AngularVelocity=frame.paddleAngularVelocity;
            if(initialize)
            { Paddle.position=frame.paddlePosition;Paddle.rotation=q;Paddle.transform.SetPositionAndRotation(frame.paddlePosition,q); }
            else { Paddle.MovePosition(frame.paddlePosition);Paddle.MoveRotation(q); }
            ExternalPose();
        }
        private void ExternalPose()
        {
            var f=externalFrame;var rotation=f.articulatedUpperBody?f.torsoRotation:Quaternion.Euler(0,f.yaw,0);
            var up=f.articulatedUpperBody?rotation*Vector3.up:Vector3.up;
            var chest=f.shoulder-rotation*Vector3.right*.19f-up*.04f;
            Segment(0,f.pelvis,chest,.18f);Sphere(1,chest+up*.25f,new Vector3(.23f,.28f,.23f));
            Torso.height=Mathf.Max(.38f,(f.articulatedUpperBody?Vector3.Distance(chest,f.pelvis):chest.y-f.pelvis.y)+.3f);Torso.transform.position=(f.pelvis+chest)*.5f;
            Torso.transform.rotation=f.articulatedUpperBody?Quaternion.FromToRotation(Vector3.up,chest-f.pelvis):Quaternion.identity;
            var hand=f.paddlePosition+f.paddleRotation*GripLocal;
            var elbow=f.articulatedUpperBody?f.rightElbow:Bend(f.shoulder,hand,f.shoulder+rotation*Vector3.right*.1f-Vector3.up*.3f-f.paddleRotation*Vector3.forward*.5f,ArmUpper,ArmLower);
            Segment(2,f.shoulder,elbow,.055f);Segment(3,elbow,f.articulatedUpperBody?f.rightWrist:hand,.043f);Sphere(12,hand,Vector3.one*.085f);
            var other=f.shoulder-rotation*Vector3.right*.38f;
            // A single learned shoulder lift rotates the existing off-hand arm pose.
            // It preserves reach and elbow geometry while exposing release height.
            var lift=Quaternion.AngleAxis(f.articulatedUpperBody?-f.offHandLift:0,Vector3.right);
            var otherHand=other+rotation*(lift*new Vector3(-.09f,-.35f,.27f));
            var otherElbow=Bend(other,otherHand,other+rotation*(lift*new Vector3(-.4f,-.3f,-.1f)),ArmUpper,ArmLower);
            Segment(4,other,otherElbow,.055f);Segment(5,otherElbow,otherHand,.043f);Sphere(13,otherHand,Vector3.one*.085f);
            Segment(6,f.rightHip,f.rightKnee,.075f);Segment(7,f.rightKnee,f.rightFoot,.055f);
            Segment(8,f.leftHip,f.leftKnee,.075f);Segment(9,f.leftKnee,f.leftFoot,.055f);
            Sphere(10,f.rightFoot,new Vector3(.13f,.11f,.28f));parts[10].rotation=Quaternion.Euler(0,f.rightFootYaw,0);
            Sphere(11,f.leftFoot,new Vector3(.13f,.11f,.28f));parts[11].rotation=Quaternion.Euler(0,f.leftFootYaw,0);
        }
    }
}
