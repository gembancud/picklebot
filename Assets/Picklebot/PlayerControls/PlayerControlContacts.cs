using System;
using UnityEngine;

namespace Picklebot.PlayerControls
{
    // Equal-mass, frictionless, inelastic horizontal discs. The small prototype
    // jump cannot clear another player's torso, so airborne bodies still collide.
    // Bounds are a lab safety enclosure (root coordinates), not pickleball lines.
    public static class PlayerControlContacts
    {
        public const float Radius = .28f;
        public sealed class Result
        {
            public readonly Vector2[] positions, velocities, contactDeltaVelocity;
            public readonly int events;
            internal Result(Vector2[] p, Vector2[] v, Vector2[] delta, int events)
            { positions=p; velocities=v; contactDeltaVelocity=delta; this.events=events; }
        }

        public static Result Solve(Vector2[] positions, Vector2[] velocities, int[] sides, float dt)
        {
            if(positions==null || velocities==null || sides==null || positions.Length!=4 || velocities.Length!=4 || sides.Length!=4)
                throw new ArgumentException("Exactly four independent players are required.");
            if(!float.IsFinite(dt) || dt<=0 || dt>.05f) throw new ArgumentOutOfRangeException(nameof(dt));
            var p=(Vector2[])positions.Clone();var v=(Vector2[])velocities.Clone();
            for(int i=0;i<4;i++)
            {
                if(!Finite(p[i]) || !Finite(v[i]) || (sides[i]!=-1 && sides[i]!=1) ||
                    Mathf.Abs(p[i].x)>4.20001f || p[i].y*sides[i]<.37999f || p[i].y*sides[i]>8.10001f)
                    throw new ArgumentException("Invalid player state or enclosure side.");
                for(int j=0;j<i;j++) if((p[i]-p[j]).sqrMagnitude<(2*Radius-1e-5f)*(2*Radius-1e-5f))
                    throw new ArgumentException("Initial bodies overlap; reset must provide a feasible state.");
            }
            float remaining=dt;int events=0;
            while(remaining>0)
            {
                float first=remaining+1;int a=-1,b=-1;Vector2 normal=default;
                for(int i=0;i<4;i++)
                {
                    Wall(i,p[i].x+4.2f,v[i].x,Vector2.right);
                    Wall(i,4.2f-p[i].x,-v[i].x,Vector2.left);
                    Wall(i,p[i].y*sides[i]-.38f,v[i].y*sides[i],Vector2.up*sides[i]);
                    Wall(i,8.1f-p[i].y*sides[i],-v[i].y*sides[i],Vector2.down*sides[i]);
                    for(int j=i+1;j<4;j++)
                    {
                        var d=p[i]-p[j];var relative=v[i]-v[j];
                        float closing=Vector2.Dot(d,relative),speed2=relative.sqrMagnitude;
                        if(closing>=-1e-7f || speed2<1e-12f) continue;
                        float c=d.sqrMagnitude-4*Radius*Radius;
                        float discriminant=closing*closing-speed2*c;
                        if(discriminant<0) continue;
                        // Stable smaller quadratic root; touching pairs use t=0.
                        float time=c<=0 ? 0 : c/(-closing+Mathf.Sqrt(discriminant));
                        if(time<=remaining && time<first)
                        { first=time;a=i;b=j;normal=(d+relative*time).normalized; }
                    }
                }
                if(a<0)
                { for(int i=0;i<4;i++)p[i]+=v[i]*remaining;break; }
                for(int i=0;i<4;i++)p[i]+=v[i]*first;
                remaining-=first;
                float closingSpeed=Vector2.Dot(v[a]-(b<0?Vector2.zero:v[b]),normal);
                if(closingSpeed>=0) throw new InvalidOperationException("Non-closing contact selected.");
                var impulse=-closingSpeed*normal/(b<0?1:2);
                v[a]+=impulse;if(b>=0)v[b]-=impulse;
                if(++events>256) throw new InvalidOperationException("Contact solver did not converge; no result may be applied.");

                void Wall(int player,float gap,float speed,Vector2 inward)
                {
                    if(speed>=-1e-7f) return;
                    float time=Mathf.Max(0,gap)/-speed;
                    if(time<=remaining && time<first) { first=time;a=player;b=-1;normal=inward; }
                }
            }
            var delta=new Vector2[4];for(int i=0;i<4;i++)delta[i]=v[i]-velocities[i];
            return new Result(p,v,delta,events);
        }
        private static bool Finite(Vector2 v)=>float.IsFinite(v.x)&&float.IsFinite(v.y);
    }
}
