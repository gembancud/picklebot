using System;
using System.Collections.Generic;
using Picklebot.Doubles;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration
{
    [Serializable]
    public sealed class PlayerRallyResultV2
    {
        public int winner,hits,score0,score1,server;
        public float duration;
        public Fault fault;
        public List<DoublesContact> contacts;
    }
    // Explicit serving/reset assistance; live rallies use only the four policies.
    public sealed class PlayerGameV2:IDisposable
    {
        public readonly PlayerControlMatch Match;
        public readonly PlayerServeSkillV2 Serve=new PlayerServeSkillV2();
        public readonly List<PlayerRallyResultV2> Rallies=new List<PlayerRallyResultV2>();
        public int PhysicsSteps {get;private set;}
        public int AssistedServeSteps {get;private set;}
        public int AssistedResetSteps {get;private set;}
        public bool Complete=>Match.World.Rules.GameWinner>=0;
        public string Failure {get;private set;}
        private float deadAt=-1;
        private int rallyServer;
        private readonly bool[] clearing=new bool[4];
        public PlayerGameV2(bool visible,IPlayerPolicyV2[] policies,int seed,int[] identities=null,PlayerContactCalibrationV2 calibration=null)
        {Match=new PlayerControlMatch(visible,calibration);Match.AttachPolicies(policies,seed,identities);rallyServer=Match.World.Rules.Server;}
        public void Step()
        {
            if(Failure!=null)throw new InvalidOperationException("Game is failed: "+Failure);
            if(Complete)return;
            try
            {
                var rules=Match.World.Rules;
                if(rules.Dead)
                {
                    if(deadAt<0)deadAt=Match.World.Time;
                    Match.StepAgents((i,a)=>ResetAction(i));AssistedResetSteps++;
                }
                else if(rules.Phase==RallyPhase.AwaitServe)
                {
                    var serve=Serve.Action(Match);
                    Match.StepAgents((i,a)=>i==rules.Server?serve:default);AssistedServeSteps++;
                }
                else Match.StepAgents();
                PhysicsSteps++;
                if(rules.Dead&&deadAt<0)deadAt=Match.World.Time;
                if(rules.Dead&&Match.World.Time-deadAt>=1&&rules.ResolveRally())
                {
                    Rallies.Add(new PlayerRallyResultV2{winner=rules.Winner,hits=rules.Hits,fault=rules.LastFault,
                        score0=rules.Score[0],score1=rules.Score[1],duration=Match.World.Time,server=rallyServer,contacts=new List<DoublesContact>(Match.World.Contacts)});
                    if(!Complete)
                    {Match.ResetRally();Serve.Reset();Array.Clear(clearing,0,4);deadAt=-1;rallyServer=rules.Server;}
                }
            }
            catch(Exception error)
            {Failure=error.GetType().Name+": "+error.Message;throw;}
        }
        private PlayerActionV2 ResetAction(int player)
        {
            var body=Match.World.Players[player];var state=Match.Controls.StateFor(player);
            var values=default(PlayerActionV2).ToArray();
            values[2]=Mathf.DeltaAngle(player<2?0:180,state.facingYaw)/180;
            if(!Match.World.Rules.VolleyMomentumPending(player))return new PlayerActionV2(values);
            if(body.BothFeetOutside)clearing[player]=false;
            else if(Match.World.Time-deadAt>=1&&new Vector2(state.velocity.x,state.velocity.z).magnitude<.03f)clearing[player]=true;
            if(clearing[player])
            {
                var local=Quaternion.Euler(0,-state.facingYaw,0)*(Vector3.forward*body.Side);
                values[0]=local.x/(3*.72f);values[1]=local.z/((local.z>=0?3.8f:2.3f)*.72f);
            }
            return new PlayerActionV2(values);
        }
        public void Dispose()=>Match.Dispose();
    }
}
