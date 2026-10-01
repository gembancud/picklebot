from pathlib import Path
import shutil
root=Path('F:/dev/picklebot')
p=root/'Assets/Picklebot/PlayerLearning/Editor/ExecutionBuildV1.cs'
s=p.read_text();a='finally{EditorSceneManager.RestoreSceneManagerSetup(previous);}'
assert a in s
s=s.replace(a,'''finally
            {
                if(previous.Length>0 && Array.Exists(previous,s=>s.isLoaded) && Array.Exists(previous,s=>s.isActive) &&
                    Array.TrueForAll(previous,s=>!s.isLoaded || !string.IsNullOrEmpty(s.path)))
                    EditorSceneManager.RestoreSceneManagerSetup(previous);
                else EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            }''')
p.write_text(s,encoding='utf-8')
shutil.copyfile(root/'artifacts/hierarchy-v1/source-records.json',root/'artifacts/hierarchy-v1/source-records-build01.json')
p=Path(__file__).parent/'build.py';s=p.read_text().replace('execution-build-01','execution-build-02').replace('build-console.log','build-console-02.log').replace('record=dict(sourceIdentity=identity,','record=dict(directory=str(BUILD),sourceIdentity=identity,');p.write_text(s,encoding='utf-8')
p=root/'tools/mlagents-training/run_execution_smoke_v1.py';s=p.read_text().replace("binary=BASE/'execution-build-01'","binary=Path(build['directory'])");p.write_text(s,encoding='utf-8')
