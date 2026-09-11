using System;
using Picklebot.Doubles;
using Picklebot.PlayerControls;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration
{
    // Physical integration fixture. Caller supplies four independent decisions;
    // no actor transfer, automatic hitter selection or hidden serve skill here.
    public sealed class PlayerControlMatch : IDisposable
    {
        public readonly DoublesWorld World;
        public readonly PlayerControlWorld Controls=new PlayerControlWorld();
        public PlayerControlMatch(bool visible,PlayerContactCalibrationV2 calibration=null)
        {
            for(int i=0;i<4;i++)swings[i]=new PlayerIntentSwingV2(calibration);
            World=new DoublesWorld(visible);
            var positions=new Vector3[4];for(int i=0;i<4;i++)positions[i]=World.Players[i].Position;
            Controls.Reset(positions);for(int i=0;i<4;i++)Apply(i,true);
        }
        public PlayerDecisionLoopV2 Decisions { get; private set; }
        public int Tick { get; private set; }
        private readonly PlayerIntentSwingV2[] swings=new PlayerIntentSwingV2[4];
        private readonly PlayerActionV2[] applied=new PlayerActionV2[4];
        public PlayerActionV2 AppliedActionFor(int player)=>applied[player];
        public void ResetRally()
        {
            if(!World.Rules.Dead||World.Rules.GameWinner>=0)throw new InvalidOperationException("A resolved non-final rally is required.");
            World.ResetRally();var positions=new Vector3[4];for(int i=0;i<4;i++)positions[i]=World.Players[i].Position;
            Controls.Reset(positions);for(int i=0;i<4;i++)Apply(i,true);
            Tick=0;Array.Clear(applied,0,4);Decisions?.Reset();foreach(var swing in swings)swing.Reset();
        }
        public void AttachPolicies(IPlayerPolicyV2[] policies,int seed,int[] identityBySeat=null)
        {
            if(Tick!=0||Decisions!=null)throw new InvalidOperationException("Attach policies only once, before the first physics step.");
            Decisions=new PlayerDecisionLoopV2(policies,seed,identityBySeat);
        }
        public void StepAgents(Func<int,PlayerActionV2,PlayerActionV2> disclosedSkill=null)
        {
            if(Decisions==null)throw new InvalidOperationException("No V2 policies attached.");
            Decisions.Step((player,tick)=>PlayerObservationV2.Capture(this,player,tick,applied[player]),Tick);
            var movement=new PlayerControlCommand[4];var paddles=new PlayerPaddleCommand[4];
            var proposed=new PlayerActionV2[4];
            for(int i=0;i<4;i++)
            {
                var action=Decisions.ActionFor(i);
                if(!World.Rules.Dead&&World.Rules.Phase!=RallyPhase.AwaitServe)
                    action=swings[i].Action(this,i,action,Decisions.IntentFor(i));
                else swings[i].Reset();
                if(disclosedSkill!=null)action=disclosedSkill(i,action);
                proposed[i]=action;movement[i]=action.Movement(i);paddles[i]=action.Paddle();
            }
            Step(movement,paddles);Array.Copy(proposed,applied,4);
        }
        public void Step(PlayerControlCommand[] movement,PlayerPaddleCommand[] paddle)
        {
            Controls.Step(movement,paddle,DoublesWorld.Dt);
            for(int i=0;i<4;i++)Apply(i,false);
            World.Simulate();Tick++;
        }
        private void Apply(int i,bool initialize)
        {
            var root=Controls.StateFor(i);var body=Controls.PoseFor(i);var paddle=Controls.PaddleFor(i);
            var support=new PlayerSupportState(body.Left,body.Right,root,i<2?-1:1,DoublesRules.HalfWidth,DoublesRules.Kitchen);
            World.Players[i].ApplyExternalFrame(new PlayerBodyFrame{
                position=root.position,velocity=root.velocity,pelvis=body.Pelvis,shoulder=body.Shoulder,
                leftFoot=body.Left.center,rightFoot=body.Right.center,leftHip=body.LeftHip,rightHip=body.RightHip,
                leftKnee=body.LeftKnee,rightKnee=body.RightKnee,yaw=root.facingYaw,leftFootYaw=body.Left.yaw,rightFootYaw=body.Right.yaw,
                paddlePosition=paddle.position,paddleRotation=paddle.rotation,paddleVelocity=paddle.velocity,paddleAngularVelocity=paddle.angularVelocity,
                touchesKitchen=support.touchesKitchen,bothFeetOutside=support.bothFeetOutside,balanceRecovered=support.balanceRecovered},initialize);
        }
        public void Dispose()=>World.Dispose();
    }
}
