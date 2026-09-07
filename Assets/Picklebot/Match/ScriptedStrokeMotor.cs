using Picklebot.Core;
using Picklebot.Inspection;
using UnityEngine;

namespace Picklebot.Match
{
    // Explicit contact assistance. This controller is not a learned policy.
    // It predicts a stroke but never writes ball velocity or ball position.
    public sealed class ScriptedStrokeMotor
    {
        public bool Planned { get; private set; }
        public Vector3 Impact { get; private set; }
        public float ImpactAt { get; private set; }
        public float Swing { get; private set; }
        private Vector3 normal;
        private float nextPlan;
        public void Reset() { Planned=false;nextPlan=0; }
        private static void Fly(ref Vector3 p,ref Vector3 v,ref Vector3 spin,SimulationConfigV1 c,float dt)
        {
            v+=(c.Gravity+AerodynamicModelV1.Evaluate(v,spin,c.AerodynamicParameters).TotalForce/c.BallMass)*dt;
            spin*=AerodynamicModelV1.AngularVelocityMultiplier(dt,c.AerodynamicParameters);p+=v*dt;
        }
        public void Plan(InspectionWorld w,int index,bool bounced,Vector2 goal)
        {
            if(w.Elapsed<nextPlan || (Planned&&ImpactAt-w.Elapsed<.16f))return;
            nextPlan=w.Elapsed+.05f;
            int side=index==0?-1:1;
            var p=w.Ball.position;var v=w.Ball.linearVelocity;var spin=w.Ball.angularVelocity;
            if(v.z*side<.1f)return;
            bool allowed=bounced||w.Rules.CanVolley;
            var m=w.Motors[index];float dt=InspectionWorld.Dt;
            for(int step=1;step<=720;step++)
            {
                Fly(ref p,ref v,ref spin,w.Configuration,dt);
                if(p.y<CourtGeometryV1.BallRadius&&v.y<0)
                {
                    if(p.z*side<=0)return;
                    if(allowed&&bounced)return;
                    p.y=CourtGeometryV1.BallRadius;v.y=-v.y*w.Configuration.CourtRestitution;
                    v.x*=.97f;v.z*=.97f;allowed=true;bounced=true;
                }
                float time=step*dt;
                if(!allowed||time<.12f||p.z*side<2.6f||p.y<.55f||p.y>1.3f)continue;
                var travel=new Vector2(p.x-m.PlayerPosition.x,p.z-m.PlayerPosition.z).magnitude;
                if(travel>3f*time+.85f || Mathf.Abs(p.x)>4.2f||Mathf.Abs(p.z)>8.2f)continue;
                if(!Stroke(p,v,new Vector3(goal.x,.037f,-side*goal.y),w.Configuration,out var n,out float speed))continue;
                Impact=p;normal=n;Swing=speed;ImpactAt=w.Elapsed+time;Planned=true;return;
            }
        }
        private static bool Stroke(Vector3 p,Vector3 incoming,Vector3 target,SimulationConfigV1 c,out Vector3 n,out float speed)
        {
            n=Vector3.forward;speed=0;float best=float.PositiveInfinity;
            foreach(float duration in new[]{1.1f,1.3f,1.5f,1.7f,1.9f})
            {
                var desired=(target-p)/duration-Vector3.up*c.Gravity.y*duration*.5f;
                for(int iteration=0;iteration<6;iteration++)
                {
                    var end=p;var velocity=desired;var spin=Vector3.zero;
                    int steps=Mathf.RoundToInt(duration/InspectionWorld.Dt);
                    for(int i=0;i<steps;i++)Fly(ref end,ref velocity,ref spin,c,InspectionWorld.Dt);
                    desired+=(target-end)/duration*1.3f;
                }
                var delta=desired-incoming;var candidate=delta.normalized;
                float swing=Vector3.Dot(incoming,candidate)+delta.magnitude/(1+c.PaddleRestitution);
                if(candidate.z*(target.z-p.z)<=0||candidate.y<-.2f)continue;
                float cost=Mathf.Abs(swing)+Mathf.Max(0,swing-PaddleMotor.MaxSpeed)*10;
                if(cost<best) {best=cost;n=candidate;speed=Mathf.Clamp(swing,-PaddleMotor.MaxSpeed,PaddleMotor.MaxSpeed);}
            }
            return float.IsFinite(best);
        }
        public PaddleInput Input(InspectionWorld w,int index)
        {
            var m=w.Motors[index];int side=index==0?-1:1;
            var targetRotation=Planned?Quaternion.LookRotation(normal):Quaternion.LookRotation(Vector3.forward*-side);
            Vector3 target=Planned?Impact-normal*(CourtGeometryV1.BallRadius+.008f)-targetRotation*Vector3.up*(CourtGeometryV1.PaddleHandleLength/2):
                new Vector3(m.PlayerPosition.x,1,m.PlayerPosition.z-side*.45f);
            var feet=Planned?new Vector3(Impact.x,0,side*Mathf.Max(2.55f,side*Impact.z+.45f)):
                new Vector3(0,0,side*4.1f);
            var move=new Vector2(feet.x-m.PlayerPosition.x,feet.z-m.PlayerPosition.z)*2;
            Vector3 feed=Vector3.zero;
            if(Planned)
            {
                float phase=w.Elapsed-ImpactAt;
                target+=normal*Swing*Mathf.Clamp(phase,-.16f,.10f);
                if(phase>-.16f&&phase<.10f)feed=normal*Swing;
            }
            var velocity=feed+(target-m.Body.position)*25-m.PlayerVelocity;
            var delta=targetRotation*Quaternion.Inverse(m.Body.rotation);delta.ToAngleAxis(out float angle,out var axis);
            if(angle>180)angle-=360;
            var angular=angle==0?Vector3.zero:axis*(angle*Mathf.Deg2Rad*12/PaddleMotor.MaxAngularSpeed);
            return new PaddleInput(Vector3.ClampMagnitude(velocity/PaddleMotor.MaxSpeed,1),Vector3.ClampMagnitude(angular,1),Vector2.ClampMagnitude(move,1));
        }
    }
}
