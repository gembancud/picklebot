using Picklebot.Core;
using UnityEngine;
namespace Picklebot.Doubles
{
    public enum StrokeKind { Flat, Topspin, Slice }
    // Interception and inverse flight are explicit assistance. Contact residuals
    // can be fitted separately without changing or steering the ball in flight.
    public sealed class StrokeController
    {
        public bool Planned {get;private set;}
        public Vector3 Impact {get;private set;}
        public float ImpactAt {get;private set;}
        public Vector3 Normal {get;private set;}
        public float Swing {get;private set;}
        public StrokeKind Kind;
        public float TimingBias,PitchBias,BrushBias,SpeedScale=1,BrushScale=1;
        private float nextPlan;
        public void Reset(){Planned=false;nextPlan=0;}
        public static void Fly(ref Vector3 p,ref Vector3 v,ref Vector3 spin,SimulationConfigV1 c,float dt)
        {v+=(c.Gravity+AerodynamicModelV1.Evaluate(v,spin,c.AerodynamicParameters).TotalForce/c.BallMass)*dt;spin*=AerodynamicModelV1.AngularVelocityMultiplier(dt,c.AerodynamicParameters);p+=v*dt;}
        public bool Plan(DoublesWorld w,int id,Vector2 goal,bool force=false)
        {
            if(!force&&(w.Time<nextPlan||(Planned&&ImpactAt-w.Time<.13f)))return Planned;
            nextPlan=w.Time+.05f;var m=w.Players[id];int side=m.Side;
            var p=w.Ball.position;var v=w.Ball.linearVelocity;var spin=w.Ball.angularVelocity;
            bool serve=w.Rules.Phase==RallyPhase.AwaitServe;
            bool bounced=serve?w.ServeBounced:w.Rules.Bounced,allowed=bounced||w.Rules.CanVolley;
            if(!serve&&v.z*side<.1f)return false;
            for(int step=1;step<=720;step++)
            {
                Fly(ref p,ref v,ref spin,w.Configuration,DoublesWorld.Dt);
                if(p.y<CourtGeometryV1.BallRadius&&v.y<0)
                {
                    if(p.z*side<=0||bounced)return false;
                    p.y=CourtGeometryV1.BallRadius;v.y=-v.y*w.Configuration.CourtRestitution;v.x*=.97f;v.z*=.97f;allowed=bounced=true;
                }
                float time=step*DoublesWorld.Dt;
                if(!allowed||time<.13f||p.z*side<2.65f||p.y<.52f||p.y>1.25f||Mathf.Abs(p.x)>3.7f||Mathf.Abs(p.z)>7.5f)continue;
                var feet=FeetTarget(p,side,serve);float travel=Vector3.Distance(feet,m.Position);
                if(travel>PlayerBody.Speed*time+.12f)continue;
                if(!Stroke(p,v,new Vector3(goal.x,CourtGeometryV1.BallRadius,-side*goal.y),w.Configuration,out var normal,out float speed))continue;
                Impact=p;Normal=Quaternion.AngleAxis(PitchBias,Vector3.Cross(Vector3.up,normal).normalized)*normal;
                Swing=speed*SpeedScale;ImpactAt=w.Time+time+TimingBias;Planned=true;return true;
            }
            return false;
        }
        private static Vector3 FeetTarget(Vector3 impact,int side,bool serve)=>new(impact.x+side*.38f,0,side*Mathf.Max(serve?7.3f:2.6f,side*impact.z+.43f));
        private static bool Stroke(Vector3 p,Vector3 incoming,Vector3 target,SimulationConfigV1 c,out Vector3 n,out float speed)
        {
            n=Vector3.forward;speed=0;float best=float.PositiveInfinity;
            foreach(float duration in new[]{1.0f,1.25f,1.5f,1.75f})
            {
                var desired=(target-p)/duration-c.Gravity*duration*.5f;
                for(int k=0;k<5;k++)
                {
                    var end=p;var v=desired;var spin=Vector3.zero;int steps=Mathf.RoundToInt(duration/DoublesWorld.Dt);
                    for(int i=0;i<steps;i++)Fly(ref end,ref v,ref spin,c,DoublesWorld.Dt);
                    desired+=(target-end)/duration*1.3f;
                }
                var delta=desired-incoming;var candidate=delta.normalized;
                float swing=Vector3.Dot(incoming,candidate)+delta.magnitude/(1+c.PaddleRestitution);
                if(candidate.z*(target.z-p.z)<=0||candidate.y<-.35f)continue;
                // Prefer a moderate flight time. Very slow contact motion is
                // sensitive to small face-position errors with a real hand grip.
                float cost=Mathf.Abs(swing-4)+Mathf.Max(0,swing-10)*10+Mathf.Abs(duration-1.25f);
                if(cost<best){best=cost;n=candidate;speed=Mathf.Clamp(swing,-10,10);}
            }
            return float.IsFinite(best);
        }
        public void Step(DoublesWorld w,int id,Vector3 recovery)
        {
            var m=w.Players[id];int side=m.Side;bool serve=w.Rules.Phase==RallyPhase.AwaitServe;
            var rotation=Quaternion.LookRotation(Planned?Normal:Vector3.forward*-side);
            var target=Planned?Impact-Normal*(CourtGeometryV1.BallRadius+.008f)-rotation*Vector3.up*.0635f:
                m.Position+new Vector3(-side*.19f,1.1f,-side*.46f);
            var feet=Planned?FeetTarget(Impact,side,serve):recovery;Vector3 feed=Vector3.zero;
            if(Planned)
            {
                float phase=w.Time-ImpactAt;
                var brush=Vector3.ProjectOnPlane(Vector3.up,Normal).normalized*((Kind==StrokeKind.Topspin?2.4f:Kind==StrokeKind.Slice?-2.4f:0)*BrushScale+BrushBias);
                var stroke=Normal*Swing+brush;
                target+=stroke*Mathf.Clamp(phase,-.06f,.055f);
                if(phase>-.06f&&phase<.055f)feed=stroke;
            }
            m.Step(feet,target,rotation,feed,w.Players[id^1],DoublesWorld.Dt);
        }
    }
}
