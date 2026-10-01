from pathlib import Path
changes={'completed512':'completed 512','same512':'same 512','underA/B':'under A/B','not2,048':'not 2,048',
         'all256':'all 256','pointwise95%':'pointwise 95%','practice:6.25':'practice: 6.25','18.75/25cm':'18.75/25 cm',
         'interleaved25%':'interleaved 25%',',25%':', 25%','and50%':'and 50%','batteries;50':'batteries; 50',
         'all512':'all 512','found174':'found 174','all32':'all 32'}
for path in [Path(__file__).with_name('report_wide_movement.py'),Path('F:/dev/picklebot/docs/research/execution-v1-wide-movement.md')]:
    content=path.read_bytes()
    for old,new in changes.items(): content=content.replace(old.encode(),new.encode())
    path.write_bytes(content)
