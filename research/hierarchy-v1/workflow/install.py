from pathlib import Path
import shutil, uuid
root=Path('F:/dev/picklebot')
stage=Path(__file__).resolve().parent
def replace(rel,old,new):
    p=root/rel
    raw=p.read_bytes(); old=old.replace('\n','\r\n').encode(); new=new.replace('\n','\r\n').encode()
    assert raw.count(old)==1,(rel,old[:100],raw.count(old))
    p.write_bytes(raw.replace(old,new))
learning='Assets/Picklebot/PlayerLearning/'
for name in ['PlayerExecutionGoalV1.cs','PlayerExecutionDrillsV1.cs']:
    shutil.copyfile(stage/name,root/learning/name)
    (root/learning/(name+'.meta')).write_text('fileFormatVersion: 2\nguid: '+uuid.uuid4().hex+'\n',encoding='utf-8')
agent=learning+'PlayerMlAgentV3.cs'
replace(agent,'        private Func<bool> releaseAvailable;','''        private Func<bool> releaseAvailable;
        private Func<PlayerExecutionGoalV1> captureGoal;
        private float[] policyObservation;
        public PlayerExecutionGoalV1 LastGoal { get; private set; }
        public float[] LastPolicyObservation => policyObservation == null ? null : (float[])policyObservation.Clone();
        public void BindGoal(Func<PlayerExecutionGoalV1> goal)
        {
            var behavior = GetComponent<Unity.MLAgents.Policies.BehaviorParameters>();
            if (isActiveAndEnabled || goal == null || behavior == null ||
                behavior.BehaviorName != PlayerExecutionGoalV1.BehaviorName ||
                behavior.BrainParameters.VectorObservationSize != PlayerExecutionGoalV1.ObservationCount)
                throw new InvalidOperationException("Bind execution goals before activation with the explicit 136-observation behavior.");
            captureGoal = goal;
        }''')
replace(agent,'public void ClearCommand() { command = default; ObservedTick = -1; }','public void ClearCommand() { command = default; ObservedTick = -1; LastGoal = null; policyObservation = null; }')
replace(agent,'            sensor.AddObservation(LastObservation.ToArray());','''            LastGoal = captureGoal == null ? null : captureGoal();
            if (captureGoal != null && LastGoal == null) throw new InvalidOperationException("Execution goal is missing.");
            policyObservation = LastGoal == null ? LastObservation.ToArray() : LastGoal.Observe(LastObservation);
            sensor.AddObservation(policyObservation);''')
drills=learning+'PlayerMlDrillsV3.cs'
replace(drills,'        public const string CurriculumVersion', '        public PlayerExecutionDrillsV1 ExecutionGoals { get; private set; }\n        public const string CurriculumVersion')
replace(drills,'            private float reward;','            private float reward;\n            private PlayerExecutionGoalV1[] goals;')
replace(drills,'behavior.BehaviorName = PlayerMlAgentV3.BehaviorName;','behavior.BehaviorName = owner.ExecutionGoals == null ? PlayerMlAgentV3.BehaviorName : PlayerExecutionGoalV1.BehaviorName;')
replace(drills,'behavior.BrainParameters.VectorObservationSize = PlayerObservationV3.Count;','behavior.BrainParameters.VectorObservationSize = owner.ExecutionGoals == null ? PlayerObservationV3.Count : PlayerExecutionGoalV1.ObservationCount;')
replace(drills,'                    agent.Received += (current, actions) =>','                    if (owner.ExecutionGoals != null) agent.BindGoal(() => goals[seat]);\n                    agent.Received += (current, actions) =>')
replace(drills,'                foreach(var old in group.GetRegisteredAgents().ToArray())group.UnregisterAgent(old);','                goals = owner.ExecutionGoals?.Goals(Drill);\n                foreach(var old in group.GetRegisteredAgents().ToArray())group.UnregisterAgent(old);')
replace(drills,'                reward += Drill.Reward;\n                if(owner.CooperativePairs)group.AddGroupReward(Drill.Reward);else Agents[Drill.Player].AddReward(Drill.Reward);','''                float stepReward = Drill.Reward;
                if (Drill.Done && owner.ExecutionGoals != null) stepReward += owner.ExecutionGoals.Finish(Drill,goals[Drill.Player]);
                reward += stepReward;
                if(owner.CooperativePairs)group.AddGroupReward(stepReward);else Agents[Drill.Player].AddReward(stepReward);''')
replace(drills,'            var academy = Academy.Instance;','''            ExecutionGoals = GetComponent<PlayerExecutionDrillsV1>();
            if (ExecutionGoals != null && !ExecutionGoals.enabled) ExecutionGoals = null;
            ExecutionGoals?.Prepare(this);
            var academy = Academy.Instance;''')
replace(drills,'Report = new MlDrillReportV3 { status = "running",','Report = new MlDrillReportV3 { contract = ExecutionGoals == null ? PlayerMlAgentV3.ContractVersion : PlayerExecutionGoalV1.Contract, status = "running",')
replace(drills,'observation = agent.LastObservation.ToArray(), physical = agent.LastCommand.ToArray(),','observation = agent.LastPolicyObservation, physical = agent.LastCommand.ToArray(),')
replace('Assets/Picklebot/PlayerControlsIntegration/PlayerContactDrillV3.cs','        public float Reward {get;private set;}','        public float Reward {get;private set;}\n        public float FaceContactTime => faceTime;')
print('Execution goal adapter installed; legacy observation/action contract preserved.')
