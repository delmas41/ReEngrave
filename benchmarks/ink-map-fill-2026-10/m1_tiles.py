"""2.220 m1: two clean blind-tile sets from the m1_measure.py output (read-only). Set A: written halves whose trimmed-head slit < 0.18.
Set B: 12 written quarters the reader marks not_one_head (seed 2220, spread over plates and box widths).
Needs the scratchpad m_<plate>.json + lit.json / bra.json that m1_measure.py wrote.
    python3 benchmarks/ink-map-fill-2026-10/m1_tiles.py"""
import json, pathlib, random, sys, shutil
WT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WT))
from tools.omr.staged import lane_report as LR
S = pathlib.Path('/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad')
PAGES = {'litolff': (4, 6), 'brahms': (5, 14)}
README = ("# 2.220 m1 tiles (read-only)\n\nEach picture is a piece of a scanned score page with ONE orange box on it and nothing else drawn.\n\n"
          "The orange box is a place where we wrote a note into the file; what is inside it: half note, filled note, or not a note?\n\n"
          "Answer by tile number. Our key is in `../key.json`, outside this folder, and is not for the reader.\n")
rows = []
for plate, pages in PAGES.items():
    d = json.load(open(S / ('lit.json' if plate == 'litolff' else 'bra.json')))
    for r in json.load(open(S / f'm_{plate}.json')):
        if r['p'] in pages:
            r['plate'] = plate; r['det'] = d['boxes'][r['s']]['page']; rows.append(r)


def item(r, box, **kw):
    return dict(plate=r['plate'], page=r['p'], box=[float(v) for v in box], rg=r['s'], kind='note', role='case',
                written=r['written'], slit=r['slit'], noh=r['noh'], trimmed=r['trimmed'], det=r['det'], **kw)


def cut(items, name):
    out = WT / 'out' / 'print' / name
    out.mkdir(parents=True, exist_ok=True)
    res = LR.cut_tiles(items, out)
    (out / 'tiles' / 'README.md').write_text(README)
    shutil.copy(out / 'tiles' / 'sheet.png', out / 'sheet.png')
    print(name, res)


rng = random.Random(2220)
A = [item(r, r['trimmed'] or r['det']) for r in rows if r['written'] == 2.0 and (r['slit'] or 0) < 0.18]
print('A candidates', len(A))
rng.shuffle(A)
cut(A, '2.220-m1-misses')

Q = [r for r in rows if r['written'] == 1.0 and r['noh']]
print('B candidates', len(Q), {p: sum(r['plate'] == p for r in Q) for p in PAGES})
chosen = []
for plate in PAGES:
    P = sorted([r for r in Q if r['plate'] == plate], key=lambda r: r['det'][2] - r['det'][0])
    thirds = [P[i * len(P) // 3:(i + 1) * len(P) // 3] for i in range(3)]
    for t in thirds:
        rng.shuffle(t)
        got = 0
        for r in t:
            it = item(r, r['det'])
            if any(LR._same_ink(it, x) for x in chosen):
                continue
            chosen.append(it); got += 1
            if got == 2: break
rng.shuffle(chosen)
cut(chosen, '2.220-m1-notonehead')
