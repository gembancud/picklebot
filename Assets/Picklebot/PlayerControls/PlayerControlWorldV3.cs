using System;
using System.Collections.Generic;
using UnityEngine;
namespace Picklebot.PlayerControls
{
    // Four independent articulated bodies. No decisions or ball access in this kernel.
    public sealed class PlayerControlWorldV3
    {
        private PlayerControlMotor[] roots;
        private PlayerBodyPose[] legs;
        private PlayerUpperBodyBoundedV3[] upper;
        private float[] turnRates;
        private PlayerJointMotorV3[] offHands;
        private static readonly int[] Sides={-1,-1,1,1};
        public int RejectedPlayer {get;private set;}=-1;
        public PlayerControlState StateFor(int i)=>roots[i].State;
        public PlayerBodyPose PoseFor(int i)=>legs[i].Fork();
        public PlayerUpperBodyBoundedV3 UpperFor(int i)=>upper[i].Fork();
        public float TurnRateFor(int i)=>turnRates[i];
        public float OffHandAngleFor(int i)=>offHands[i].Angle;
        public float OffHandRateFor(int i)=>offHands[i].Rate;
        public PlayerControlWorldV3(Vector3[] positions,float[] initialOffHandAngles=null)
        {
            if(positions==null||positions.Length!=4)throw new ArgumentException("Four start positions required.");
            if(initialOffHandAngles!=null&&(initialOffHandAngles.Length!=4||Array.Exists(initialOffHandAngles,a=>!float.IsFinite(a)||a<0||a>140)))throw new ArgumentException("Four bounded initial off-hand angles required.");
            var p=new Vector2[4];for(int i=0;i<4;i++){if(positions[i].y!=0)throw new ArgumentException("Flat reset required.");p[i]=new Vector2(positions[i].x,positions[i].z);}
            PlayerControlContacts.Solve(p,new Vector2[4],Sides,PlayerJointMotorV3.Dt);
            roots=new PlayerControlMotor[4];legs=new PlayerBodyPose[4];upper=new PlayerUpperBodyBoundedV3[4];turnRates=new float[4];offHands=new PlayerJointMotorV3[4];
            for(int i=0;i<4;i++)
            {offHands[i]=new PlayerJointMotorV3(initialOffHandAngles==null?0:initialOffHandAngles[i],0,140,180,900);roots[i]=new PlayerControlMotor();roots[i].Reset(positions[i],i<2?0:180);legs[i]=new PlayerBodyPose(roots[i].State);upper[i]=new PlayerUpperBodyBoundedV3(legs[i].Pelvis,Quaternion.Euler(0,roots[i].State.facingYaw,0));}
        }
        public bool TryStep(PlayerActionV3[] actions)
        {
            if(actions==null||actions.Length!=4)throw new ArgumentException("Four independently chosen actions required.");
            // Retry only rejected horizontal movement requests. Every attempt
            // forks the last committed world and repeats collision and joint checks.
            var scales=new[]{1f,1f,1f,1f};
            while(true)
            {
                if(TryStepCandidate(actions,scales))return true;
                int rejected=RejectedPlayer;
                if(scales[rejected]<=0)return TryPlanarProjection(actions,scales,rejected);
                scales[rejected]=Mathf.Max(0,scales[rejected]-.25f);
            }
        }
        private bool TryPlanarProjection(PlayerActionV3[] actions,float[] scales,int player)
        {
            // Only used after speed reduction fails. Search nearby planar requests;
            // there is no ball, target shot, or change to the other action channels.
            var requested=Vector2.ClampMagnitude(new Vector2(actions[player][0],actions[player][1]),1);
            var candidates=new List<Vector2>(27);
            foreach(float fraction in new[]{.25f,.5f,1f})
                for(int x=-1;x<=1;x++)for(int z=-1;z<=1;z++)
                {
                    var target=Vector2.ClampMagnitude(new Vector2(x,z),1);
                    var candidate=Vector2.Lerp(requested,target,fraction);
                    if(!candidates.Contains(candidate))candidates.Add(candidate);
                }
            candidates.Sort((a,b)=>(a-requested).sqrMagnitude.CompareTo((b-requested).sqrMagnitude));
            scales[player]=1;
            foreach(var candidate in candidates)
                if(TryStepCandidate(actions,scales,player,candidate))return true;
            RejectedPlayer=player;return false;
        }
        private bool TryStepCandidate(PlayerActionV3[] actions,float[] movementScales,int projectedPlayer=-1,Vector2 projectedMovement=default)
        {
            const float dt=PlayerJointMotorV3.Dt;
            var r=new PlayerControlMotor[4];var l=new PlayerBodyPose[4];var u=new PlayerUpperBodyBoundedV3[4];
            var hands=new PlayerJointMotorV3[4];var yawRates=new float[4];var p=new Vector2[4];var v=new Vector2[4];
            for(int i=0;i<4;i++)
            {
                var old=roots[i].State;r[i]=roots[i].Fork();hands[i]=offHands[i].Fork();hands[i].Step(actions[i][17]*140);
                // Root turning also needs acceleration bounds; no instant yaw-rate jump.
                yawRates[i]=old.grounded?Mathf.MoveTowards(turnRates[i],actions[i][2]*180,720*dt):turnRates[i];
                var movement=actions[i].Movement(old.facingYaw+yawRates[i]*dt);
                if(i==projectedPlayer)movement.move=projectedMovement;
                movement.move*=movementScales[i];
                var state=r[i].Step(movement,dt,Sides[i]);
                p[i]=new Vector2(old.position.x,old.position.z);v[i]=new Vector2(state.velocity.x,state.velocity.z);
            }
            var previousVelocity=new Vector2[4];for(int i=0;i<4;i++){var old=roots[i].State;previousVelocity[i]=new Vector2(old.velocity.x,old.velocity.z);}
            v=PlayerBodyBrakingV3.Constrain(p,previousVelocity,v,Sides,14,dt);
            var contacts=PlayerControlContacts.Solve(p,v,Sides,dt);
            for(int i=0;i<4;i++)
            {
                r[i].ApplyHorizontalContact(contacts.positions[i],contacts.velocities[i]);
                l[i]=legs[i].Fork();l[i].Step(r[i].State,dt);u[i]=upper[i].Fork();
                if(!u[i].TryStep(actions[i].TorsoTarget,actions[i].ArmTarget,l[i].Pelvis,Quaternion.Euler(0,r[i].State.facingYaw,0)))
                {RejectedPlayer=i;return false;}
            }
            roots=r;legs=l;upper=u;turnRates=yawRates;offHands=hands;RejectedPlayer=-1;return true;
        }
    }
}
