"""ROADMAP 2.219 phase 1 (read-only): boxes whose identity verdict says NOT a notehead, and how many are WRITTEN as notes
in the exported file (symbols.json hosts = what the MusicXML wrote). Match: host.rg == subject, else the 2.211 / lane_report.written_at
rule (a host on the same page whose centre lies inside the box)."""
import json, sys, collections, re
W='/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.204/out/lane-report/'
ARMS={'brahms':'2.204r3-brahms/work/brahms','litolff':'2.204r3-litolff/work/litolff','lit-p6':'2.204r3-lit-p6/work/litolff'}
def run(plate, arm, dump=None):
    base=W+ARMS[plate]+'.'+arm
    rec=json.load(open(base+'.mini-record.json')); sym=json.load(open(base+'.symbols.json'))
    hosts=[h for h in sym['hosts'] if h['kind']=='note']
    byrg=collections.defaultdict(list); bypage=collections.defaultdict(list)
    for h in hosts: byrg[h['rg']].append(h); bypage[h['page']].append(h)
    box={}
    for o in rec['observations']:
        if o['quantity']=='glyph_box': box[o['subject']]=o['detail']['bbox_page_px']
    ident={v['subject']:v for v in rec['verdicts'] if v['quantity']=='notehead_is_not_a_notehead'}
    notmap=collections.Counter(); written=collections.Counter(); wrows=[]
    values=collections.Counter()
    for s,v in ident.items():
        if v['outcome']!='decided' or v['value'] is not True: continue
        r=v['reason']; notmap[r]+=1
        hs=byrg.get(s)
        how='rg'
        if not hs:
            b=box.get(s); how='centre'
            if b:
                pg=int(s.split('/')[1])
                ins=[h for h in bypage[pg] if b[0]<=h['cx']<=b[2] and b[1]<=h['cy']<=b[3]]
                hs=ins
        if hs:
            written[(r,how)]+=1; wrows.append((s,r,how,hs[0]['type'],hs[0].get('blue'),hs[0]['part'],hs[0]['measure']))
    return notmap, written, wrows, len(hosts), len(ident)
if __name__=='__main__':
    for plate in ARMS:
        for arm in ('off','on'):
            n,w,rows,nh,ni=run(plate,arm)
            print(plate,arm,'hosts',nh,'identity verdicts',ni,'decided-not-a-head',dict(n),'WRITTEN',dict(w))
