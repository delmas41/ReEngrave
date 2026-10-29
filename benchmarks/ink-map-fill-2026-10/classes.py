import json, collections, sys
R = json.load(open(sys.argv[1] + '/rows.json'))
def sz(r):
    if r['h'] < 0.9: return 'short<0.9'
    if r['h'] > 1.8: return 'tall>1.8'
    if r['w'] < 1.1: return 'narrow<1.1'
    if r['w'] > 1.9: return 'wide>1.9'
    return 'head-sized'
for plate, rows in R.items():
    print('==', plate)
    A = [r for r in rows if r['file']=='F' and 'H' in (r['slit'], r['win']) and 'F' not in (r['slit'], r['win'])]
    B = [r for r in rows if r['file']=='H' and 'F' in (r['slit'], r['win']) and 'H' not in (r['slit'], r['win'])]
    X = [r for r in rows if r['file'] and r['slit'] in 'HF' and r['win'] in 'HF' and r['slit'] != r['win']]
    for name, L in (('A written BLACK, ink says hollow (none says filled)', A), ('B written HOLLOW, ink says filled (none hollow)', B), ('X written, slit and window disagree', X)):
        print(' ', name, len(L))
        print('     size', dict(collections.Counter(sz(r) for r in L)), 'online', sum(r['online'] for r in L), 'twin', sum(bool(r['twin']) for r in L), 'det', dict(collections.Counter(r['det'] for r in L)), 'blue', sum(bool(r['blue']) for r in L))
    U = [r for r in rows if not r['file']]
    tw = lambda r: any(t[2] for t in r['twin'])
    UH = [r for r in U if r['slit']=='H' or r['win']=='H']
    print('  not written', len(U), '| ink reads hollow on', len(UH))
    print('     of those, twin written', sum(tw(r) for r in UH), '| refused not-a-notehead', sum(1 for r in UH if r['nn'][1] is True and not tw(r)))
    rest = [r for r in UH if not tw(r) and r['nn'][1] is not True]
    print('     remainder', len(rest), 'size', dict(collections.Counter(sz(r) for r in rest)), 'det', dict(collections.Counter(r['det'] for r in rest)))
    print('     remainder duration outcome/reason', collections.Counter((r['du_o'], r['du_r']) for r in rest).most_common(8))
    print('     nn reasons among refused', collections.Counter(r['nn'][2] for r in UH if r['nn'][1] is True and not tw(r)).most_common(6))
    # not_head_sized at file
    nhs = [r for r in rows if r['hff'] and r['hff'].get('not_head_sized')]
    print('  not_head_sized filed', len(nhs), '| written', sum(1 for r in nhs if r['file']), 'as', dict(collections.Counter(r['ftype'] for r in nhs if r['file'])), '| ink says H', sum(1 for r in nhs if 'H' in (r['slit'], r['win'])), '| fill null', sum(1 for r in nhs if r['hff'].get('fill') is None))
    nh2 = [r for r in nhs if r['file']=='F' and r['hff'].get('fill') is None and 'H' in (r['slit'],r['win'])]
    print('  not_head_sized, fill null, written BLACK, ink says H:', len(nh2), dict(collections.Counter(sz(r) for r in nh2)))
