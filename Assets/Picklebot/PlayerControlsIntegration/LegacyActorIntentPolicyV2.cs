using System;
using Picklebot.PlayerAgents;
using UnityEngine;
namespace Picklebot.PlayerControlsIntegration
{
    // Explicit historical checkpoint bridge, not a 96-input trained actor.
    // Only the frozen V1 prefix enters the network. V2 heading rotates movement
    // into body coordinates. New speed, stamina and collision limits still apply.
    public sealed class LegacyActorIntentPolicyV2:IPlayerIntentPolicyV2
    {
        private readonly PlayerActor actor;
        public PlayerActorModel Model=>actor.Model;
        public string Name=>"V1 checkpoint compatibility on V2 / "+actor.Name;
        public PlayerShotIntentV2 LastIntent { get; private set; }
        public PlayerPolicySample LastSample=>actor.LastSample;
        public LegacyActorIntentPolicyV2(PlayerActorModel model,bool sample=false)
        {actor=new PlayerActor(model,sample);}
        public PlayerActionV2 Decide(PlayerObservationV2 observation,System.Random random)
        {
            if(observation==null)throw new ArgumentNullException(nameof(observation));
            float sin=observation.values[54],cos=observation.values[55];
            if(Mathf.Abs(sin*sin+cos*cos-1)>.001f)throw new ArgumentException("V2 heading must be a unit sin/cos pair.");
            var prefix=new float[PlayerObservation.Count];Array.Copy(observation.values,prefix,prefix.Length);
            var old=actor.Decide(new PlayerObservation{player=observation.player,tick=observation.tick,values=prefix},random);
            LastIntent=new PlayerShotIntentV2(old.attempt,old.shot,true);
            var values=default(PlayerActionV2).ToArray();
            values[0]=cos*old.moveX-sin*old.moveZ;values[1]=sin*old.moveX+cos*old.moveZ;
            values[5]=1; // Explicit compatibility sprint request, subject to energy.
            return new PlayerActionV2(values);
        }
        public void Reset(){LastIntent=default;}
    }
}
