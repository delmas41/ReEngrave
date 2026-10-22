"""2.167c probe 2: mechanical features of each held-by-sum bar (no judgement).
For each non-doubled held bar: stems up/down, same-onset up/down pairs, a two-voice candidate from the shipped splitter and
whether it would fill the bar, one-voice sum, overfull/short, unequal values at one x, chord sizes.
usage: c2_features.py HELD.json COVERAGE.json OUT.json"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.voicing import split_events_into_voices   # noqa: E402

rows = json.load(open(sys.argv[1]))
cov = json.load(open(sys.argv[2]))
H = {(b['page'], b['system'], b['staff'], b['cell']) for b in cov['bars_held_out_sum']['held']}
out = []
for r in rows:
    k = (r['page'], r['system'], r['staff'], r['cell'])
    if k not in H:
        continue
    h = r['held']
    want, div = h['want_units'], h['divisions']
    evs = r['events']
    chords = [e for e in evs if e['kind'] == 'chord']
    rests = [e for e in evs if e['kind'] == 'rest']
    up = [e for e in chords if e.get('stem_direction') == 'up']
    dn = [e for e in chords if e.get('stem_direction') == 'down']
    nodir = [e for e in chords if e.get('stem_direction') not in ('up', 'down')]
    tol = 25.0
    pairs = [(u, d) for u in up for d in dn if abs(u['x_position'] - d['x_position']) <= tol]
    total = sum(e['units'] for e in evs)
    cand = None
    try:
        shim = [dict(e, noteheads=e['heads'], x_position=e['x_position']) for e in evs]
        cand = split_events_into_voices(shim)
    except Exception as ex:
        cand = None
    cand_sums = None
    cand_fill = None
    if cand and len(cand) == 2:
        key = {id(s): s for s in shim}
        idx = {id(s): i for i, s in enumerate(shim)}
        cand_sums = [sum(evs[idx[id(s)]]['units'] for s in st) for st in cand]
        cand_fill = all(c == want for c in cand_sums)
    # one stem, one value: events at nearly one x with different units
    cols = {}
    for e in chords:
        cols.setdefault(round(e['x_position'] / tol), []).append(e)
    diff_val_same_x = sum(1 for v in cols.values() if len({e['units'] for e in v}) > 1)
    out.append(dict(page=r['page'], system=r['system'], staff=r['staff'], cell=r['cell'], name=r['name'], clef=r['clef'],
                    want=want, total=total, over=total > want, n_events=len(evs), n_chords=len(chords), n_rests=len(rests),
                    n_up=len(up), n_down=len(dn), n_nodir=len(nodir), n_pairs=len(pairs),
                    max_heads=max([len(e['heads']) for e in chords] or [0]),
                    cand_streams=len(cand) if cand else None, cand_sums=cand_sums, cand_fill=cand_fill,
                    diff_val_same_x=diff_val_same_x, why=r['why'], div=div,
                    two_voice_written=len(h['voices']) > 1, n_streams_judged=len(h['voices']),
                    guessed=sum(1 for e in evs for hh in e['heads'] if hh.get('guess')) + sum(1 for e in rests if (e['rest'] or {}).get('guess')),
                    ))
json.dump(out, open(sys.argv[3], 'w'))
import collections
C = collections.Counter
print('bars', len(out), 'over', sum(o['over'] for o in out), 'short', sum(not o['over'] for o in out))
print('two-voice judged', sum(o['two_voice_written'] for o in out))
print('both stem dirs present', sum(1 for o in out if o['n_up'] and o['n_down']))
print('both dirs, same-onset pairs', sum(1 for o in out if o['n_pairs']))
print('cand 2 streams & fill', sum(1 for o in out if o['cand_fill']))
print('over & both dirs', sum(1 for o in out if o['over'] and o['n_up'] and o['n_down']))
print('over & pairs', sum(1 for o in out if o['over'] and o['n_pairs']))
print('over & nodir>0', sum(1 for o in out if o['over'] and o['n_nodir']))
print('over & max_heads>=2', sum(1 for o in out if o['over'] and o['max_heads'] >= 2))
print('over & diff_val_same_x', sum(1 for o in out if o['over'] and o['diff_val_same_x']))
print('short & both dirs', sum(1 for o in out if not o['over'] and o['n_up'] and o['n_down']))
print('total/want ratio (over):', C(round(o['total'] / o['want'], 2) for o in out if o['over']).most_common(8))
print('want-total (short) quarters:', C(round((o['want'] - o['total']) / o['div'], 2) for o in out if not o['over']).most_common(10))
print('overshoot quarters:', C(round((o['total'] - o['want']) / o['div'], 2) for o in out if o['over']).most_common(10))
print('why', C(w for o in out for w in o['why']).most_common(6))
print('guessed in held bars', sum(o['guessed'] for o in out), 'bars with guess', sum(1 for o in out if o['guessed']))
