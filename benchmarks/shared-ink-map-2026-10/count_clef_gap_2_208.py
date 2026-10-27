"""ROADMAP 2.208: how many staves of the frozen sample have NO cell-0 clef claim, and how many detector boxes stand in that clef slot.

Reads the 20261022-night record's per-page slices (`lane_report.ensure_slices`), SAMPLE pages only (the context page is never counted).
A staff is counted when it has a cell-0 `leading_column` claim (the register ran on it) and no cell-0 `clef` area claim of any standing.
The slot is [column right edge, key claim's left edge], or +3 sp where the record holds no key claim (these records predate 2.183/2.187
ON, so none exists). A box counts when its centre is in the slot and it is not itself an owner class. Prints the totals and writes the
staves to gap_<plate>.json for the crop check. Records are from BEFORE the fix: this is the count the lane opened on.
"""
import json,sys,collections,re
S='/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/'
PAGES={'litolff':{2,4,6,8,9,10,11,16},'brahms':{0,4,5,8,12,14,19,25}}
def load(slicedir,plate):
    staff=collections.defaultdict(lambda: dict(clef_claim=[],col=None,key=[],loc=[],meter=[],sp=None))
    boxes=collections.defaultdict(list)
    for l in open(f'{S}{slicedir}/{plate}/observations.jsonl'):
        if '"staff/' not in l and '"glyph/' not in l: continue
        d=json.loads(l); sub=d['subject']; q=d['quantity']
        if sub.startswith('staff/'):
            s=staff[sub]
            if q=='claimed_area':
                dt=d['detail']
                if dt.get('unit')!='area' or dt.get('cell')!=0: continue
                o=dt['owner']
                if o=='clef': s['clef_claim'].append((dt['standing'],dt.get('source'),d['value']))
                elif o=='leading_column': s['col']=d['value']
                elif o=='key_signature': s['key'].append(d['value'])
                elif o=='meter': s['meter'].append(d['value'])
                s['sp']=dt.get('space_page_px') or s['sp']
            elif q=='clef_located': s['loc'].append((d['frame'],d['value']))
        elif sub.startswith('glyph/') and q=='glyph_box' and d['frame']=='cell:0':
            boxes[sub.rsplit('/',2)[0].replace('glyph','staff')].append((sub,d['value'][0],d['detail']['bbox_page_px'],d['value']))
    return staff,boxes
if __name__=='__main__':
    slicedir=sys.argv[1] if len(sys.argv)>1 else 'lane-report-slices-20261022-night'
    for plate in ('litolff','brahms'):
        staff,boxes=load(slicedir,plate)
        pages=collections.defaultdict(lambda:[0,0,0,0,0])
        tot=collections.Counter(); gapboxes=[]
        for sub,s in staff.items():
            if s['col'] is None and not s['clef_claim']: continue   # not a cell-0 staff with register
            p=sub.split('/')[1]
            if int(p) not in PAGES[plate]: continue
            read=[c for c in s['clef_claim'] if c[0]=='READ']
            tot['staves']+=1
            if read: tot['clef_claim_READ']+=1; continue
            tot['no_clef_claim']+=1
            if s['loc']: tot['no_claim_but_loc']+=1
            if s['col'] is None: tot['no_col']+=1; continue
            right=s['col'][2]
            key_lo=min([k[0] for k in s['key']],default=None)
            if key_lo is None: tot['no_key_claim']+=1
            hi=key_lo if key_lo is not None else right+3*(s['sp'] or 16)
            nb=[]
            for g,cls,bb,v in boxes.get(sub,[]):
                if str(cls).startswith(('clef','gClef','fClef','cClef','key','brace','bracket','staff','timeSig')): continue
                cx=(bb[0]+bb[2])/2
                if right-1<=cx<hi and (s['clef_claim']==[]) :
                    nb.append((g,cls,[round(x) for x in bb]))
            if nb: tot['staves_with_gap_boxes']+=1
            tot['gap_boxes']+=len(nb)
            for g,cls,bb in nb: tot['gap_'+('notehead' if 'notehead' in cls else 'rest' if 'rest' in cls.lower() else 'other')]+=1
            gapboxes.append((sub,right,key_lo,nb))
        print(plate,dict(tot))
        json.dump(gapboxes,open(f'gap_{plate}.json','w'))
