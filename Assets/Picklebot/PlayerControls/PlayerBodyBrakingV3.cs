using System;
using UnityEngine;

namespace Picklebot.PlayerControls
{
    // Grounded movement feasibility only: no ball, aiming or policy targets.
    // Opposing court enclosures remain at least .76 m apart, so the .56 m
    // body discs can meet only their partner on the same side.
    public static class PlayerBodyBrakingV3
    {
        private static float SafeClosing(float gap,float acceleration,float dt)
        {
            double distance=Math.Max(0,gap),dv=(double)acceleration*dt;
            double twiceAD=2*acceleration*distance;
            float speed=(float)(twiceAD/(Math.Sqrt(dv*dv+twiceAD)+dv));
            return speed<=0?0:BitConverter.Int32BitsToSingle(BitConverter.SingleToInt32Bits(speed)-1);
        }

        public static Vector2[] Constrain(Vector2[] positions,Vector2[] previous,Vector2[] requested,int[] sides,float acceleration,float dt)
        {
            if(positions==null||previous==null||requested==null||sides==null||positions.Length!=4||previous.Length!=4||requested.Length!=4||sides.Length!=4)
                throw new ArgumentException("Four body states required.");
            if(!float.IsFinite(acceleration)||acceleration<=0||!float.IsFinite(dt)||dt<=0||dt>.05f)
                throw new ArgumentException("Finite positive motion bounds required.");
            var candidate=(Vector2[])requested.Clone();var partner=new int[4];
            for(int i=0;i<4;i++)
            {
                if(!float.IsFinite(positions[i].x)||!float.IsFinite(positions[i].y)||!float.IsFinite(previous[i].x)||!float.IsFinite(previous[i].y)||!float.IsFinite(requested[i].x)||!float.IsFinite(requested[i].y))throw new ArgumentException("Finite body states required.");
                int found=-1;
                for(int j=0;j<4;j++)if(j!=i&&sides[j]==sides[i]){if(found>=0)throw new ArgumentException("Two bodies per court side required.");found=j;}
                if(found<0)throw new ArgumentException("A partner on each court side is required.");partner[i]=found;
                candidate[i]=PlayerEnclosureBrakingV3.Constrain(positions[i],previous[i],candidate[i],sides[i],acceleration,dt);
            }
            var normals=new Vector2[4];var closingLimits=new float[4];var weights=new float[4];bool needsProjection=false;
            for(int i=0;i<4;i++)if(i<partner[i])
            {
                int j=partner[i];var separation=positions[i]-positions[j];float length=separation.magnitude;
                if(length<2*PlayerControlContacts.Radius-1e-5f)throw new ArgumentException("Overlapping body reset.");
                var normal=separation/length;normals[i]=normal;
                // Conservative relative braking reserve leaves effort for walls
                // and tangential motion. The existing hard contact solve remains.
                closingLimits[i]=SafeClosing(Mathf.Max(0,length-2*PlayerControlContacts.Radius-1e-5f),acceleration*.5f,dt);
                weights[i]=Mathf.Max(previous[i].magnitude,candidate[i].magnitude);
                weights[j]=Mathf.Max(previous[j].magnitude,candidate[j].magnitude);
                if(Vector2.Dot(candidate[j]-candidate[i],normal)>closingLimits[i])needsProjection=true;
            }
            if(!needsProjection)return candidate;
            var individualCorrections=new Vector2[4];var pairCorrections=new Vector2[4];
            // Dykstra projection with fixed per-body mobility weights. A body
            // whose old and requested velocities are both zero remains stationary.
            // Both moving bodies can share a correction within their effort bounds,
            // including when the leading player requests sudden braking.
            for(int iteration=0;iteration<256;iteration++)
            {
                for(int i=0;i<4;i++)
                {
                    var input=candidate[i]+individualCorrections[i];
                    var output=PlayerEnclosureBrakingV3.Constrain(positions[i],previous[i],input,sides[i],acceleration,dt);
                    individualCorrections[i]=input-output;candidate[i]=output;
                }
                for(int i=0;i<4;i++)if(i<partner[i])
                {
                    int j=partner[i];var a=candidate[i]+pairCorrections[i];var b=candidate[j]+pairCorrections[j];
                    float excess=Vector2.Dot(b-a,normals[i])-closingLimits[i];var nextA=a;var nextB=b;
                    if(excess>0)
                    {
                        float sum=weights[i]+weights[j];if(sum<=0)throw new InvalidOperationException("No approaching body can supply braking.");
                        nextA+=normals[i]*(excess*weights[i]/sum);nextB-=normals[i]*(excess*weights[j]/sum);
                    }
                    pairCorrections[i]=a-nextA;pairCorrections[j]=b-nextB;candidate[i]=nextA;candidate[j]=nextB;
                }
                bool valid=true;
                for(int i=0;i<4;i++)
                {
                    var checkedVelocity=PlayerEnclosureBrakingV3.Constrain(positions[i],previous[i],candidate[i],sides[i],acceleration,dt);
                    if((checkedVelocity-candidate[i]).magnitude>1e-6f||(candidate[i]-previous[i]).magnitude>acceleration*dt+1e-5f)valid=false;
                    if(i<partner[i]&&Vector2.Dot(candidate[partner[i]]-candidate[i],normals[i])>closingLimits[i]+1e-6f)valid=false;
                }
                if(valid)return candidate;
            }
            throw new InvalidOperationException("Body/wall braking constraints did not converge; no state committed.");
        }
    }
}
