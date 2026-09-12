from pathlib import Path
import hashlib,json,uuid
R=Path('F:/dev/picklebot');W=Path(__file__).resolve().parent
p=R/'Assets/Picklebot/PlayerLearning/PlayerRecoveryScheduleV3.cs'
source=json.loads((R/'artifacts/hierarchy-v1/right-acquisition-01/source-records.json').read_text(encoding='utf-8'))
assert hashlib.sha256(p.read_bytes()).hexdigest()==source['files'][p.relative_to(R).as_posix()]
s=p.read_text(encoding='utf-8')
s=s.replace('focusPattern!="lateral"&&focusPattern!="axes"','focusPattern!="lateral"&&focusPattern!="axes"&&focusPattern!="lateral-right"')
s=s.replace('Recovery focus must be lateral or axes.','Recovery focus must be lateral, axes, or fixed lateral-right.')
hook='            bool air=block<48,left=block<40||block>=48&&block<60;'
assert s.count(hook)==1
s=s.replace(hook,'            // New acquisition-retention arm: preserve the first128 maintenance resets;\n            // focus on the same fixed rightward range that the acquisition run learned.\n            if(focusPattern=="lateral-right")return new Episode(block<48?"rally-air-feed":"rally-bounce-feed","lateral-right","focus",lateralRange,0);\n'+hook)
s=s.replace('(pattern!="lateral"&&pattern!="axes")','(pattern!="lateral"&&pattern!="axes"&&pattern!="lateral-right")').replace('Recovery mix requires solo lateral or axes practice','Recovery mix requires solo lateral, axes or fixed-right practice')
p.write_bytes(s.encode())
test=R/'Assets/Picklebot/PlayerLearning/Tests/PlayerRightReturnRetentionV1Tests.cs';assert not test.exists()
test.write_bytes((W/'PlayerRightReturnRetentionV1Tests.cs').read_bytes())
test.with_suffix('.cs.meta').write_bytes(('fileFormatVersion: 2\nguid: '+uuid.uuid4().hex+'\n').encode())
runner=(W/'test_right_acquisition.py').read_text(encoding='utf-8').replace('right-acquisition-tests-','right-retention-tests-')
(W/'test_right_retention.py').write_bytes(runner.encode())
(W/'right-retention-tests-metadata.json').write_bytes(json.dumps(dict(testFilter='PlayerRightReturnRetentionV1Tests|PlayerRecoveryScheduleV3Tests|PlayerRightReturnAcquisitionV1Tests|PlayerInterleavedRecoveryV3Tests'),indent=2).encode())
print('Prepared opt-in fixed-right recovery focus and physical-reset coverage tests')
