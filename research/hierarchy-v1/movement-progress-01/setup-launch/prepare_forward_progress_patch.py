"""Prepare reviewable source proposal only; never mutate the project."""
from pathlib import Path
import difflib
import hashlib
import json

ROOT = Path('F:/dev/picklebot')
OUT = Path(__file__).resolve().parent / 'forward-progress-proposal'
FILES = [
    'Assets/Picklebot/PlayerControlsIntegration/PlayerContactDrillV3.cs',
    'Assets/Picklebot/PlayerLearning/PlayerMlDrillsV3.cs',
    'Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs',
    'Assets/Picklebot/PlayerLearning/PlayerHeadlessBootstrapV3.cs',
]
OLD = {p: (ROOT / p).read_text(encoding='utf-8-sig') for p in FILES}
NEW = dict(OLD)

def replace(path, old, new, count=1):
    assert NEW[path].count(old) == count, (path, old, NEW[path].count(old))
    NEW[path] = NEW[path].replace(old, new)

drill, run, worker, startup = FILES
replace(drill,
    '        private PlayerMovementPositionRewardV3 movementPositionReward;',
    '        private PlayerMovementPositionRewardV3 movementPositionReward;\n'
    '        public readonly bool MovementForwardProgressRewardEnabled;\n'
    '        private readonly PlayerMovementFlightRewardV3 movementForwardProgress;\n'
    '        public float MovementForwardProgressReward=>movementForwardProgress?.TotalReward??0;\n'
    '        public int MovementForwardProgressRewardedSteps=>movementForwardProgress?.RewardedSteps??0;')
replace(drill, 'float movementPositionReward=0,string movementPattern="court")',
    'float movementPositionReward=0,string movementPattern="court",bool movementForwardProgressReward=false)')
replace(drill,
    '            PlayerMovementPositionRewardV3.ValidateBudget(movementPositionReward);',
    '            if(movementForwardProgressReward&&(cooperative||movementRange<=0||!IsRallyFeed(task)))\n'
    '                throw new ArgumentException("Forward flight reward requires a solo positive-range movement rally feed.");\n'
    '            MovementForwardProgressRewardEnabled=movementForwardProgressReward;\n'
    '            if(movementForwardProgressReward)movementForwardProgress=new PlayerMovementFlightRewardV3();\n'
    '            PlayerMovementPositionRewardV3.ValidateBudget(movementPositionReward);')
replace(drill,
    '            bool legalLanding=FaceContact&&NetCrossed&&rules.Events.Any(e=>e.kind=="bounce"&&e.time>faceTime&&e.position.z*(Player<2?1:-1)>0);',
    '            bool legalLanding=FaceContact&&NetCrossed&&rules.Events.Any(e=>e.kind=="bounce"&&e.time>faceTime&&e.position.z*(Player<2?1:-1)>0);\n'
    '            // Reward accounting only: actual flight after an accepted face contact.\n'
    '            // The first legal landing closes this signal even if volley momentum\n'
    '            // keeps the physical drill alive; later faults still determine success.\n'
    '            if(movementForwardProgress!=null)Reward+=movementForwardProgress.Advance(\n'
    '                Match.World.Ball.position.z*(Player<2?1:-1),FaceContact,rules.Dead,Done||Match.Tick>=7200,legalLanding);')
replace(drill,
    'private void Finish(string outcome,float reward){Done=true;Outcome=outcome;Reward+=reward;}',
    'private void Finish(string outcome,float reward){movementForwardProgress?.Stop();Done=true;Outcome=outcome;Reward+=reward;}')

replace(run,
    '        public float movementPositionRewardScale,movementPositionReward;',
    '        public float movementPositionRewardScale,movementPositionReward;\n'
    '        public bool movementForwardProgressRewardEnabled;\n'
    '        public float movementForwardProgressReward;\n'
    '        public int movementForwardProgressRewardedSteps;')
replace(run,
    '        public bool trainerConnected, alignedDecisions, randomMatchContext, movementRecoveryMix, interleavedRecovery, optimizerDiagnostics;',
    '        public bool trainerConnected, alignedDecisions, randomMatchContext, movementRecoveryMix, interleavedRecovery, optimizerDiagnostics;\n'
    '        public bool movementForwardProgressReward;')
replace(run,
    '        public float MovementRange,MovementTiming,MovementStartVariation,MovementPositionReward;',
    '        public float MovementRange,MovementTiming,MovementStartVariation,MovementPositionReward;\n'
    '        public bool MovementForwardProgressReward; // Optional focus-only measured post-contact flight feedback.')
replace(run,
    '        public static bool IsMovementTask(string task)=>',
    '        public static void ValidateMovementForwardProgressReward(string task,float range,bool enabled)\n'
    '        {\n'
    '            if(enabled&&(task!="movement-maintenance"||!float.IsFinite(range)||range<=0||range>1))\n'
    '                throw new ArgumentException("Forward flight reward requires solo movement practice with a positive bounded range.");\n'
    '        }\n'
    '        public static bool IsMovementTask(string task)=>')
replace(run,
    '                    movementPattern=Drill.MovementPattern,movementPositionRewardScale=Drill.MovementPositionRewardScale,movementPositionReward=Drill.MovementPositionReward,',
    '                    movementPattern=Drill.MovementPattern,movementPositionRewardScale=Drill.MovementPositionRewardScale,movementPositionReward=Drill.MovementPositionReward,\n'
    '                    movementForwardProgressRewardEnabled=Drill.MovementForwardProgressRewardEnabled,movementForwardProgressReward=Drill.MovementForwardProgressReward,movementForwardProgressRewardedSteps=Drill.MovementForwardProgressRewardedSteps,')
replace(run,
    'movementPositionReward:NewMovementChallenge(index)?MovementPositionReward:0,movementPattern:MovementPatternForEpisode(index));',
    'movementPositionReward:NewMovementChallenge(index)?MovementPositionReward:0,movementPattern:MovementPatternForEpisode(index),movementForwardProgressReward:NewMovementChallenge(index)&&MovementForwardProgressReward);')
replace(run,
    '            ValidateMovementPositionReward(Task,MovementRange,MovementPositionReward);',
    '            ValidateMovementPositionReward(Task,MovementRange,MovementPositionReward);\n'
    '            ValidateMovementForwardProgressReward(Task,MovementRange,MovementForwardProgressReward);')
replace(run,
    'movementPositionReward=MovementPositionReward,movementPattern=MovementPattern, initialHoldLift',
    'movementPositionReward=MovementPositionReward,movementForwardProgressReward=MovementForwardProgressReward,movementPattern=MovementPattern, initialHoldLift')
replace(run,
    '                stats.Add(movement+"PositionReward",episode.movementPositionReward);',
    '                stats.Add(movement+"PositionReward",episode.movementPositionReward);\n'
    '                stats.Add(movement+"ForwardProgressRewardEnabled",episode.movementForwardProgressRewardEnabled?1:0);\n'
    '                stats.Add(movement+"ForwardProgressReward",episode.movementForwardProgressReward);\n'
    '                stats.Add(movement+"ForwardProgressRewardedSteps",episode.movementForwardProgressRewardedSteps);')

replace(worker,
    '        public string movementPattern="court";',
    '        public bool movementForwardProgressReward;\n'
    '        public string movementPattern="court";')
replace(worker,
    '            PlayerMlDrillsV3.ValidateMovementPositionReward(manifest.task,manifest.movementRange,manifest.movementPositionReward);',
    '            PlayerMlDrillsV3.ValidateMovementPositionReward(manifest.task,manifest.movementRange,manifest.movementPositionReward);\n'
    '            PlayerMlDrillsV3.ValidateMovementForwardProgressReward(manifest.task,manifest.movementRange,manifest.movementForwardProgressReward);')
replace(worker,
    'run.MovementPositionReward=Manifest.movementPositionReward;run.MovementPattern=Manifest.movementPattern;',
    'run.MovementPositionReward=Manifest.movementPositionReward;run.MovementForwardProgressReward=Manifest.movementForwardProgressReward;run.MovementPattern=Manifest.movementPattern;')
replace(startup,
    '            public bool trainerRequired;',
    '            public bool trainerRequired,movementForwardProgressReward;')
replace(startup,
    'trainerRequired=plan.RequireTrainer};',
    'trainerRequired=plan.RequireTrainer,movementForwardProgressReward=manifest.movementForwardProgressReward};')

helper = 'Assets/Picklebot/PlayerControlsIntegration/PlayerMovementFlightRewardV3.cs'
NEW[helper] = '''using System;
using UnityEngine;

namespace Picklebot.PlayerControlsIntegration
{
    // Observes measured post-contact ball positions. No physics, action or target access.
    public sealed class PlayerMovementFlightRewardV3
    {
        public const float MaximumReward=PlayerReturnProgressV3.MaximumReward;
        private PlayerReturnProgressV3 progress;
        public float TotalReward {get;private set;}
        public int RewardedSteps {get;private set;}
        public bool Started=>progress!=null;
        public bool Stopped {get;private set;}

        public float Advance(float canonicalZ,bool acceptedFaceContact,bool faulted,bool terminal,bool firstLegalLanding)
        {
            if(!float.IsFinite(canonicalZ))throw new ArgumentException("Finite measured ball position required.");
            // Stop before adding anything on a fault, deadline, or first landing.
            // In particular, a pending volley-momentum check cannot extend this signal.
            if(Stopped||faulted||terminal||firstLegalLanding){Stop();return 0;}
            if(progress==null)
            {
                if(acceptedFaceContact)progress=new PlayerReturnProgressV3(canonicalZ);
                return 0;
            }
            float reward=Mathf.Min(progress.Advance(canonicalZ),MaximumReward-TotalReward);
            if(reward>0){TotalReward+=reward;RewardedSteps++;}
            return reward;
        }
        public void Stop(){Stopped=true;}
    }
}
'''
NEW[helper+'.meta']='fileFormatVersion: 2\nguid: 2075882b624742cc87425c48b0b6658c\n'

OUT.mkdir(parents=True, exist_ok=True)
patch=[]
records=[]
for path, text in NEW.items():
    dest=OUT/'proposed'/path
    dest.parent.mkdir(parents=True, exist_ok=True)
    data=text.replace('\n','\r\n').encode('utf-8')
    dest.write_bytes(data)
    old=OLD.get(path,'')
    patch.extend(difflib.unified_diff(old.splitlines(True),text.splitlines(True),
        fromfile='a/'+path if path in OLD else '/dev/null',tofile='b/'+path))
    original=(ROOT/path).read_bytes() if path in OLD else None
    if original is not None:
        backup=OUT/'base'/path
        backup.parent.mkdir(parents=True,exist_ok=True)
        backup.write_bytes(original)
    records.append({'path':path,'oldSha256':hashlib.sha256(original).hexdigest() if original is not None else None,
        'newSha256':hashlib.sha256(data).hexdigest()})
patchdata=''.join(patch).encode('utf-8')
(OUT/'runtime.patch').write_bytes(patchdata)
(OUT/'runtime-manifest.json').write_text(json.dumps({'status':'proposal_not_applied_not_unity_tested',
    'scope':'Optional focus-only actual post-contact forward progress; physical controls and existing reward paths default unchanged.',
    'patchSha256':hashlib.sha256(patchdata).hexdigest(),'files':records},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'proposal':str(OUT),'runtimePatchSha256':hashlib.sha256(patchdata).hexdigest(),'files':len(records)}))
