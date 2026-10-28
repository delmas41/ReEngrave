import json,collections
for plate in ("litolff","brahms"):
    d=json.load(open(f'{plate}.on.gathered.record.json')); d=d.get('record',d)
    obs=d['observations']
    box={};strokes=collections.defaultdict(list)
    for o in obs:
        if o['quantity']=='glyph_box' and o['detail'].get('bbox_page_px'): box[o['subject']]=o['detail']['bbox_page_px']
        elif o['quantity']=='stroke' and o['detail'].get('bbox_page_px'):
            p=o['subject'].split('/'); strokes[tuple(p[1:5])].append((o['value'],o['detail']['bbox_page_px'],o['detail']['length_spaces'],o['detail']['thickness_spaces']))
    off=json.load(open(f'{plate}.off.gathered.record.json')); off=off.get('record',off)
    on={v['subject']:v for v in d['verdicts'] if v['quantity']=='notehead_position'}
    fo={v['subject']:v for v in off['verdicts'] if v['quantity']=='notehead_position'}
    sp={'litolff':15.75,'brahms':32.0}[plate]
    c=collections.Counter(); n=0
    for s,v in fo.items():
        if v['outcome']!='decided' or on.get(s,{}).get('outcome')=='decided': continue
        n+=1; b=box[s]; xc=(b[0]+b[2])/2; yc=(b[1]+b[3])/2; w=b[2]-b[0]
        cell=tuple(s.split('/')[1:5]); kinds=set()
        for k,pb,L,t in strokes[cell]:
            if pb[0]-0.3*w<=xc<=pb[2]+0.3*w and abs((pb[1]+pb[3])/2-yc)<=0.9*sp:
                wide=(pb[2]-pb[0])>=w*1.3
                kinds.add(k+("-wide" if wide else ""))
        # the 'best' category
        for pref in ('horizontal','blob-wide','blob','curve','curve-wide','vertical','vertical-wide'):
            if pref in kinds: c[pref]+=1;break
        else: c['no stroke at the head']+=1
    print(plate,'old decided, new abstained:',n,dict(c))
