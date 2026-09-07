"""Run fixed-seed Unity checks after training. Requires Play mode."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('trainer',ROOT/'scripts/competition-train.py')
trainer=importlib.util.module_from_spec(spec);spec.loader.exec_module(trainer)
path='Assets/Picklebot/Competition/Models/strategy.json'
for mode,count in [('self',100),('near',100),('far',100),('centre',20)]:
    report=trainer.collect(840000,count,f'{mode}-final','' if mode=='centre' else path,mode)
    print(mode, len(report['points']), 'points; mean returns',sum(p['returns'] for p in report['points'])/count,flush=True)
trainer.collect(840000,3,'repeat-final',path,'self')
print('Three-seed repeat complete.',flush=True)
