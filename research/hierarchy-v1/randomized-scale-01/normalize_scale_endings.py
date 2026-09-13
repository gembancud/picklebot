from pathlib import Path
import subprocess
R=Path('F:/dev/picklebot')
for rel in ['Assets/Picklebot/PlayerControlsIntegration/PlayerContactDrillV3.cs','Assets/Picklebot/PlayerLearning/PlayerMlDrillsV3.cs','Assets/Picklebot/PlayerLearning/PlayerWorkerPlanV3.cs']:
 old=subprocess.check_output(['git','-c','safe.directory=F:/dev/picklebot','-C',str(R),'show','HEAD:'+rel])
 p=R/rel;current=p.read_bytes();normalized=current.replace(b'\r\n',b'\n')
 if b'\r\n' in old:normalized=normalized.replace(b'\n',b'\r\n')
 assert current.replace(b'\r\n',b'\n')==normalized.replace(b'\r\n',b'\n')
 p.write_bytes(normalized)
 print(rel,'CRLF' if b'\r\n' in old else 'LF')
