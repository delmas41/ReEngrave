"""usage: miniSlice.py SRC_TAG_DIR_OR_TAG PLATE PAGES OUTDIR  -> OUTDIR/PLATE/{observations,abstentions,verdicts}.jsonl (pages + doc-level rows)"""
import sys, json, os, re
sys.path.insert(0, '/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a26d61ddc53de8906')
from tools.omr.staged import lane_report as L
tag, plate, pages, out = sys.argv[1], sys.argv[2], {int(x) for x in sys.argv[3].split(',')}, sys.argv[4]
src = L.slice_dir(plate, tag)
d = os.path.join(out, plate)
os.makedirs(d, exist_ok=True)
for kind in ('observations', 'abstentions', 'verdicts'):
    n = 0
    with open(src / (kind + '.jsonl')) as f, open(os.path.join(d, kind + '.jsonl'), 'w') as g:
        for line in f:
            it = json.loads(line)
            pg = L.page_of(it.get('subject'))
            if pg is None or pg in pages:
                g.write(line); n += 1
    print(kind, n)
