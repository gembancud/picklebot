from pathlib import Path
import subprocess

root = Path('F:/dev/picklebot')
def before(relative):
    return subprocess.check_output(['git', '-c', 'safe.directory=F:/dev/picklebot', '-C', str(root), 'show', 'HEAD:' + relative])

relative = 'docs/CURRENT_STATE.md'
current = (root / relative).read_text(encoding='utf-8')
prefix = current.split('\n---\n', 1)[0] + '\n---\n'
assert prefix.startswith('# Active drill-mastery goal — fresh placement comparison complete')
(root / relative).write_bytes(prefix.encode('utf-8') + before(relative))

relative = 'docs/DRILL_MASTERY_GOAL.md'
original = before(relative)
current = (root / relative).read_text(encoding='utf-8')
replacement = current[current.index('Current work:'):current.index('\n\nApp status:')].encode('utf-8')
start = original.index(b'Current work:')
end = original.index(b'\n', start)
if original[end-1:end] == b'\r':
    end -= 1
(root / relative).write_bytes(original[:start] + replacement + original[end:])

for relative, marker in [('docs/HIERARCHICAL_CONTROL.md', '[Fresh frozen comparison]'),
                         ('docs/research/drill-mastery-coverage.md', '## Fresh placement follow-up')]:
    current = (root / relative).read_text(encoding='utf-8')
    addition = current[current.index(marker):].encode('utf-8')
    original = before(relative)
    assert marker.encode() not in original
    separator = b'\n' if original.endswith(b'\n') else b'\n\n'
    (root / relative).write_bytes(original + separator + addition)
print('Preserved every untouched documentation byte from HEAD; retained the fresh result edits.')
