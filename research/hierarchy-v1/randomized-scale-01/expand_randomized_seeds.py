from pathlib import Path
R=Path('F:/dev/picklebot')
def edit(rel,a,b):
 p=R/rel;s=p.read_text(encoding='utf-8');assert a in s;s=s.replace(a,b);p.write_bytes(s.replace('\n','\r\n').encode())
edit('Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs',
 'if(manifest.firstSeed<minimum||end>minimum+100000L)',
 'bool expanded=manifest.movementRecoveryMix&&manifest.movementPattern=="randomized";\n            if(expanded)minimum=manifest.mode=="training"?2000000:4000000;\n            long capacity=expanded&&manifest.mode=="training"?1000000L:100000L;\n            if(manifest.firstSeed<minimum||end>minimum+capacity)')
edit('Assets/Picklebot/PlayerLearning/PlayerMlDrillsV3.cs',
 'int seedMaximum = seedMinimum + 100000;',
 'int seedMaximum = seedMinimum + 100000;\n            if(MovementRecoveryMix&&MovementPattern=="randomized") {seedMinimum=RequireTrainer?2000000:4000000;seedMaximum=seedMinimum+(RequireTrainer?1000000:100000);}')
edit('Assets/Picklebot/PlayerControlsIntegration/PlayerContactDrillV3.cs',
 '(seed>=1300000&&seed<1400000)))',
 '(seed>=1300000&&seed<1400000)||(seed>=2000000&&seed<3000000)||(seed>=4000000&&seed<4100000)))')
print('Explicit new training/development seed ranges; old final seeds remain forbidden.')
