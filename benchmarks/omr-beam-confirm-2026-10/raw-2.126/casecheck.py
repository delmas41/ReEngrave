import sys, json
sys.path.insert(0, '.')
from tools.omr.staged import judged
CASES = {'q86': 'glyph/0/0/0/4/2', 'q93': 'glyph/0/0/0/4/9', 'q110': 'glyph/0/0/0/5/4', 'q118': 'glyph/0/0/0/5/12',
         'q1009': 'glyph/0/0/9/3/3', 'p6bar102': 'glyph/6/0/11/5/0'}
for tag, path in zip(sys.argv[1::2], sys.argv[2::2]):
    page0 = tag.endswith('0')
    subs = [s for s in CASES.values() if (s.startswith('glyph/0/') == page0)]
    st = judged.standing_for(__import__('pathlib').Path(path), subs, quantities=('duration', 'head_stem', 'stem_value'))
    print('==', tag)
    for name, sub in CASES.items():
        if sub not in subs:
            continue
        for q in ('head_stem', 'stem_value', 'duration'):
            v = st.get((sub, q))
            if v is None:
                print(f'  {name:9s} {q:11s} -')
                continue
            cands = [(c.get('value') or {}).get('written') for c in (v.get('candidates') or [])]
            val = v.get('value')
            wr = val.get('written') if isinstance(val, dict) else val
            d = v.get('detail') or {}
            print(f'  {name:9s} {q:11s} {v["outcome"]:9s} {str(v.get("reason")):28s} value={wr} cands={cands} decider={v.get("decider")}')
