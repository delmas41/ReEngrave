import sys,collections; sys.path.insert(0,'.'); sys.path.insert(0,'out/probe')
from load import load
rec=load(sys.argv[1])
cellsp={}; boxes=collections.defaultdict(list)
for o in rec['observations']:
    q=o['quantity']
    if q=='cell_staff_space' and o['subject'].endswith('/0'):
        cellsp[o['subject'][5:]]=o['value']
    elif q=='glyph_box':
        s=o['subject'].split('/')
        if s[4]=='0': boxes['/'.join(s[1:4])].append((s[5],o['value'],o['score'],o['id']))
for st,bl in sorted(boxes.items()):
    sp=cellsp.get(st+'/0')
    for gi,v,sc,i in bl:
        if v[0].startswith('rest') and sp and v[1]<4*sp:
            print(st,gi,v,round(sc,2),'x/sp',round(v[1]/sp,2),round((v[1]+v[3])/sp,2),'keys:',[(b[1][0],round(b[1][1]/sp,2),round((b[1][1]+b[1][3])/sp,2)) for b in bl if b[1][0].startswith(('key','accid','clef'))])
