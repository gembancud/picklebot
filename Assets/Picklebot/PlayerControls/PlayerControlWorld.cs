using System;
using UnityEngine;

namespace Picklebot.PlayerControls
{
    // Owns integration, not decisions: no teammate actions are exposed to players.
    // Trial states are committed only after the complete contact solve succeeds.
    [Serializable] public sealed class PlayerPaddleFailure
    {
        public int player;
        public Vector3 oldShoulder,shoulder,position,velocity,angularVelocity;
        public Quaternion rotation;
        public PlayerPaddleCommand command;
        public float yaw,dt;
    }
    public sealed class PlayerControlWorld
    {
        public PlayerPaddleFailure LastPaddleFailure {get;private set;}
        private PlayerControlMotor[] motors;
        private PlayerBodyPose[] poses;
        private PlayerPaddleControl[] paddles;
        public PlayerPaddleState PaddleFor(int player)=>paddles[player].State;
        public int PaddleReserveRecoveryFor(int player)=>paddles[player].ReserveRecoverySteps;
        public PlayerBodyPose PoseFor(int player)=>poses[player].Fork();
        private static readonly int[] Sides={-1,-1,1,1};
        public PlayerControlContacts.Result LastContacts { get; private set; }
        public PlayerControlWorld() { Reset(); }
        public PlayerControlState StateFor(int player)=>motors[player].State;
        public void Reset()=>Reset(new[]{new Vector3(-1.2f,0,-3),new Vector3(1.2f,0,-3),new Vector3(-1.2f,0,3),new Vector3(1.2f,0,3)});
        public void Reset(Vector3[] positions)
        {
            if(positions==null||positions.Length!=4)throw new ArgumentException("Four reset positions are required.");
            var points=new Vector2[4];for(int i=0;i<4;i++)
            { if(positions[i].y!=0)throw new ArgumentException("Reset requires flat-ground positions.");points[i]=new Vector2(positions[i].x,positions[i].z); }
            PlayerControlContacts.Solve(points,new Vector2[4],Sides,1f/240);
            motors=new PlayerControlMotor[4];poses=new PlayerBodyPose[4];paddles=new PlayerPaddleControl[4];LastContacts=null;LastPaddleFailure=null;
            for(int i=0;i<4;i++)
            {
                motors[i]=new PlayerControlMotor();
                motors[i].Reset(positions[i],i<2?0:180);
                poses[i]=new PlayerBodyPose(motors[i].State);
                paddles[i]=new PlayerPaddleControl(poses[i].Shoulder,motors[i].State.facingYaw);
            }
        }
        public void Step(PlayerControlCommand[] commands,float dt)
        { Step(commands,new[]{PlayerPaddleCommand.Ready,PlayerPaddleCommand.Ready,PlayerPaddleCommand.Ready,PlayerPaddleCommand.Ready},dt); }
        public void Step(PlayerControlCommand[] commands,PlayerPaddleCommand[] paddleCommands,float dt)
        {
            if(commands==null || commands.Length!=4) throw new ArgumentException("Four commands are required.");
            if(paddleCommands==null||paddleCommands.Length!=4)throw new ArgumentException("Four paddle commands are required.");
            var proposed=new PlayerControlMotor[4];var p=new Vector2[4];var v=new Vector2[4];
            for(int i=0;i<4;i++)
            {
                var before=motors[i].State;
                proposed[i]=motors[i].Fork();var after=proposed[i].Step(commands[i],dt);
                p[i]=new Vector2(before.position.x,before.position.z);
                v[i]=new Vector2(after.velocity.x,after.velocity.z);
            }
            var contacts=PlayerControlContacts.Solve(p,v,Sides,dt);
            for(int i=0;i<4;i++)proposed[i].ApplyHorizontalContact(contacts.positions[i],contacts.velocities[i]);
            var nextPoses=new PlayerBodyPose[4];
            for(int i=0;i<4;i++) { nextPoses[i]=poses[i].Fork();nextPoses[i].Step(proposed[i].State,dt); }
            var nextPaddles=new PlayerPaddleControl[4];
            for(int i=0;i<4;i++)
            {
                nextPaddles[i]=paddles[i].Fork();
                if(!nextPaddles[i].TryStep(poses[i].Shoulder,nextPoses[i].Shoulder,proposed[i].State.facingYaw,paddleCommands[i],dt))
                    {
                    var state=paddles[i].State;
                    LastPaddleFailure=new PlayerPaddleFailure{player=i,oldShoulder=poses[i].Shoulder,shoulder=nextPoses[i].Shoulder,
                        position=state.position,velocity=state.velocity,angularVelocity=state.angularVelocity,rotation=state.rotation,command=paddleCommands[i],yaw=proposed[i].State.facingYaw,dt=dt};
                    throw new InvalidOperationException("Player "+i+" paddle constraints are infeasible; entire trial rejected.");
                }
            }
            LastPaddleFailure=null;motors=proposed;poses=nextPoses;paddles=nextPaddles;LastContacts=contacts;
        }
    }
}
