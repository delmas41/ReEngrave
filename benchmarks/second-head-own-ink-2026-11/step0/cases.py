import json
M="/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reengrave-manager-20261124-12f953/out/print/lost-chord-heads/lost_chord_heads_litolff_24.manifest.json"
m=json.load(open(M))
CASES={}
for t in m['tiles']:
    CASES['T%d'%t['tile']]=dict(page=t['page'],box=t['refused_box_page_px'],why=t['detail_reason'],written=t['written_head']['box_page_px'],cell=t['cell'])
CASES['A3']=dict(page=2,box=[2478.2,2083.2,2508.4,2110.6],why='dyad_ink:not_one_head:too_wide',written=[2480.9,2064.0,2505.3,2085.1],cell='cell/2/1/0/14')
CASES['A18']=dict(page=6,box=[2299.7,704.1,2323.4,727.0],why='dyad_ink:not_one_head:too_wide',written=[2296.0,687.0,2323.4,709.8],cell='cell/6/0/2/11')
GOOD_SHAPE=['T3','T6','T16','T19','T21','A3','A18']
NOT_HEAD=['T8','T14','T15','T18','T20']
SLIVER=['T2','T9','T11','T13','T22']
