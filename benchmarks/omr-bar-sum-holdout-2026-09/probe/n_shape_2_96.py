"""ROADMAP 2.96: the SHAPE of the N (narrowed head) bars -- one head, one chord of
2+ heads, several columns -- by meter verdict, for bars whose record candidates
land the bar uniquely.   python3 .../n_shape_2_96.py <dump-dir>"""
import json,sys,collections
import pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
DUMP=sys.argv[1]
import classify_held_2_96 as K, classify_held_mvt_2_22 as C
for lab in ('lit','brah'):
    D=json.load(open(f'{DUMP}/{lab}-2.96.held.json'))
    P=json.load(open(f'{DUMP}/{lab}-part.json'))
    by={tuple(b['cell']):b for b in D['bars']}
    cnt=collections.Counter()
    for r in P['rows']:
        if r['tier']!='evidenced' or r['cause']!='N': continue
        b=by[tuple(r['cell'])]
        b['_overlap']=C.voices_overlap(b); K.mark_events(b); b['_groups']=K.refusal_groups(b)
        gs=[(k,o) for k,o in b['_groups'] if k=='N']
        nl=K.n_landings(b,r['T'],kinds=('N',))
        xs=[float(x['box'][1])+float(x['box'][3])/2 for x in b['refused_in_cell'] if x['refusal']=='duration_narrowed' and x.get('box')]
        heads=len(xs)
        sm=(b['system_meter'] or {}).get('outcome')
        shape=('1 chord of %d heads'%heads) if len(gs)==1 else '%d columns'%len(gs)
        cnt[(sm,'unique' if nl==1 else 'not unique/none',shape if heads<4 else 'many')]+=1
    print(lab)
    for k,v in sorted(cnt.items(), key=lambda kv:-kv[1])[:14]: print('  ',v,k)
