from pathlib import Path
import json, hashlib, datetime
here = Path(__file__).resolve().parent
base = Path('F:/dev/picklebot/artifacts/hierarchy-v1/wide-movement-fixture-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
changed = {}
assert not (base/'fixture-script-revision-01.json').exists()
assert not any(here.glob('wide-fixture-*.json'))
for ordinal in range(0,512,64):
    original = here / f'wide-fixture-{ordinal:04}.cs'
    output = here / f'wide-fixture-v2-{ordinal:04}.cs'
    code = original.read_text(encoding='utf-8-sig')
    assert 'Picklebot.PlayerControlsIntegration.PlayerStrokeAimV3' in code
    code = code.replace('Picklebot.PlayerControlsIntegration.PlayerStrokeAimV3','Picklebot.PlayerControls.PlayerStrokeAimV3')
    code = code.replace('UnityEngine.FindObjectsInactive.Include,UnityEngine.FindObjectsSortMode.None','UnityEngine.FindObjectsInactive.Include')
    with output.open('x',encoding='utf-8',newline='\n') as handle: handle.write(code)
    changed[output.name] = dict(sha256=sha(output), original=original.name, originalSha256=sha(original))
with (base/'fixture-script-revision-01.json').open('x',encoding='utf-8') as handle:
    json.dump(dict(reason='First fixture failed compilation before execution: PlayerStrokeAimV3 belongs to Picklebot.PlayerControls, not PlayerControlsIntegration. Also use current FindObjectsByType overloads.',
                   changedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),runtimeSourceChanged=False,previousResetOutputs=0,
                   originalScriptsPreserved=True,files=changed),handle,indent=2)
print(json.dumps(dict(correctedScripts=len(changed),runtimeSourceChanged=False,priorResetOutputs=0)))
