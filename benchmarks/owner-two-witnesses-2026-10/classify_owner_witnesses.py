import json,sys,collections
pages=json.load(open('/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.216/benchmarks/lane-report/sample.json'))['plates']
def cls(s,v,reach,farl):
    r=v['reason']; o=v['outcome']
    if r=='stem_disagrees': return 'DISAGREE'
    if r=='ledger_witnesses_disagree': return 'ledger_vs_ledger'
    if r=='stem_toward_staff': return 'STEM_ONLY'
    if o=='decided' and r in('ledger_note_first','ledger_owner_density','ledger_direction','ledger_refuted','ladder','hairpin_separates'):
        if v['stem_agrees']: return 'AGREE'
        return 'LEDGER_ONLY(stem agrees-or-silent)'
    if o=='abstained': return 'NEITHER(abstain:'+str(r)+')'
    if r in('distance','range_veto','staff_band','staff_band_no_box','group_owner'): return 'NEITHER(decided by '+r+')'
    return 'other:'+str(r)
for plate in sys.argv[1:]:
    d=json.load(open(plate+'.json')); samp=set(pages[plate]['pages'])
    for scope in('all','frozen'):
        C=collections.Counter(); F=collections.Counter()
        for s,v in d['ver'].items():
            pg=int(s.split('/')[1])
            if scope=='frozen' and pg not in samp: continue
            far = s in d['reach'] or s in d['farl']
            c=cls(s,v,d['reach'],d['farl'])
            (F if far else C)[c]+=1
        print(plate,scope,'FAR (has head_stem_reach or far_head_owner_ledger):',sum(F.values()),dict(F.most_common()))
        print('   near/other:',sum(C.values()),dict(C.most_common()))
