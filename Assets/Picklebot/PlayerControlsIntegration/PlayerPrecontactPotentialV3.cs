using System;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // Optional reward accounting only. No commands, predicted trajectory or physics writes.
    public sealed class PlayerPrecontactPotentialV3
    {
        public const float Gamma=.99f, Scale=.25f, DistanceScale=.5f;
        public const int DecisionTicks=12;
        public float InitialPotential {get;}
        public float PreviousPotential {get;private set;}
        public float TotalReward {get;private set;}
        public double DiscountedReward {get;private set;}
        public int Transitions {get;private set;}
        public int LastDecisionTick {get;private set;}
        public bool Settled {get;private set;}
        public PlayerPrecontactPotentialV3(float initialPotential,float trainerGamma)
        {
            if(!float.IsFinite(trainerGamma)||trainerGamma!=Gamma)throw new ArgumentException("Precontact shaping requires trainer gamma0.99.");
            CheckPotential(initialPotential);InitialPotential=PreviousPotential=initialPotential;
        }
        private static void CheckPotential(float value)
        {if(!float.IsFinite(value)||value < -Scale || value > 0)throw new ArgumentOutOfRangeException(nameof(value));}
        private float Add(float next)
        {
            CheckPotential(next);float reward=Gamma*next-PreviousPotential;
            DiscountedReward+=Math.Pow(Gamma,Transitions)*reward;
            TotalReward+=reward;PreviousPotential=next;Transitions++;return reward;
        }
        public float AtDecision(int tick,float nextPotential)
        {
            if(Settled||tick!=LastDecisionTick+DecisionTicks)throw new InvalidOperationException("Exactly one shaping transition per policy decision is required.");
            CheckPotential(nextPotential);float reward=Add(nextPotential);LastDecisionTick=tick;return reward;
        }
        public float AtTerminal(int tick)
        {
            if(Settled||tick<=LastDecisionTick||tick>LastDecisionTick+DecisionTicks)throw new InvalidOperationException("Terminal settlement must follow the final full or partial policy transition exactly once.");
            float reward=Add(0);Settled=true;return reward;
        }
        private static void CheckVector(Vector3 v)
        {if(!float.IsFinite(v.x)||!float.IsFinite(v.y)||!float.IsFinite(v.z))throw new ArgumentException("Finite geometry required.");}
        public static float Measure(Vector3 ball,Vector3 faceCenter,Quaternion faceRotation,Vector3 faceSize,float cornerRadius,float ballRadius)
        {
            CheckVector(ball);CheckVector(faceCenter);CheckVector(faceSize);
            float norm=faceRotation.x*faceRotation.x+faceRotation.y*faceRotation.y+faceRotation.z*faceRotation.z+faceRotation.w*faceRotation.w;
            if(!float.IsFinite(norm)||norm<1e-12f||!float.IsFinite(cornerRadius)||!float.IsFinite(ballRadius)||ballRadius<=0||cornerRadius<=0||faceSize.z<=0||faceSize.x<=2*cornerRadius||faceSize.y<=2*cornerRadius)throw new ArgumentException("Invalid face approach geometry.");
            var local=Quaternion.Inverse(faceRotation.normalized)*(ball-faceCenter);
            float x=Mathf.Max(0,Mathf.Abs(local.x)-(faceSize.x*.5f-cornerRadius));
            float y=Mathf.Max(0,Mathf.Abs(local.y)-(faceSize.y*.5f-cornerRadius));
            float z=Mathf.Abs(Mathf.Abs(local.z)-(faceSize.z*.5f+ballRadius));
            float distance=Mathf.Sqrt(x*x+y*y+z*z);
            if(!float.IsFinite(distance))throw new ArgumentException("Geometry distance overflow.");
            return -Scale*(1-Mathf.Exp(-distance/DistanceScale));
        }
    }
}
