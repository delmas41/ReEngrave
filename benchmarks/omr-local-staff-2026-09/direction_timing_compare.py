import json, sys
sys.path.insert(0, '.')
from tools.omr.direction_lexicon import lookup
D = '/private/tmp/claude-501/'
for full, cap in (('dt_litolff_p2.json', 'dt_p2_cap64.json'), ('dt_brahms.json', 'dt_br_cap64.json')):
    f = json.load(open(D + full)); c = json.load(open(D + cap))
    fw = {w['cand']: w['text'] for w in f['full_words']}
    # words under cap: surya first (precedence), else tesseract from the full run's raw texts
    cw = {}
    for r in c['percrop_surya']:
        i = r['cand']
        t = r['text']
        if lookup(t):
            cw[i] = t
        elif lookup(f['raw_texts'][i]['tess']):
            cw[i] = f['raw_texts'][i]['tess']
    norm = lambda d: {k: v.lower().rstrip('.') for k, v in d.items()}
    print(full, 'full words', fw, '\n  cap words', cw, '\n  same:', norm(fw) == norm(cw),
          'percrop total', round(c['percrop_total'], 1), 'full surya', round(f['full_surya_total'], 1))
# E2 tight size test, offline, all pages
for fn in ('dt_litolff.json', 'dt_litolff_p1.json', 'dt_litolff_p2.json', 'dt_brahms.json'):
    r = json.load(open(D + fn))
    geo = r['geometry']
    k2 = [g['cand'] for g in geo if g['w_sp'] >= 4.3 and g['h_sp'] >= 1.2 and g['n_comp'] >= 4]
    lost = [w for w in r['full_words'] if w['cand'] not in k2]
    print(fn, 'cands', len(geo), 'kept by tight test', len(k2), 'accepted words lost', lost)
