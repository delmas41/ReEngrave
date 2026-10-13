import sys,collections; sys.path.insert(0,'.'); sys.path.insert(0,'out/probe')
from load import load
rec=load(sys.argv[1])
cellsp={}; boxes=collections.defaultdict(list)
for o in rec['observations']:
    q=o['quantity']
    if q=='cell_staff_space' and o['subject'].endswith('/0'): cellsp[o['subject'][5:]]=o['value']
    elif q=='glyph_box':
        s=o['subject'].split('/')
        if s[4]=='0': boxes['/'.join(s[1:4])].append((s[5],o['value'],o['score'],o['id']))
def iou(a,b):
    ax0,ay0,ax1,ay1=a[1],a[2],a[1]+a[3],a[2]+a[4]; bx0,by0,bx1,by1=b[1],b[2],b[1]+b[3],b[2]+b[4]
    iw=max(0,min(ax1,bx1)-max(ax0,bx0)); ih=max(0,min(ay1,by1)-max(ay0,by0)); i=iw*ih
    return i/(a[3]*a[4]+b[3]*b[4]-i+1e-9)
for st,bl in sorted(boxes.items()):
    sp=cellsp.get(st+'/0')
    keys=[b for b in bl if b[1][0].startswith(('key','accidentalFlat','accidentalSharp'))]
    kk=[b for b in bl if b[1][0].startswith('key')]
    if not kk: continue
    x0=min(b[1][1] for b in kk); x1=max(b[1][1]+b[1][3] for b in kk)
    for gi,v,sc,i in bl:
        if v[0].startswith(('rest','notehead','art','flag','fing','tie','arpeg')):
            cx=v[1]+v[3]/2
            if x0-.3*sp<=cx<=x1+.3*sp:
                best=max(((iou(v,b[1]),b[1][0],round((b[1][1]+b[1][3]/2-cx)/sp,2)) for b in keys),default=(0,'-',0))
                print(st,v[0],round(sc,2),'maxIoU key-shaped',round(best[0],2),best[1],'dx_sp',best[2],'nkey',len(kk),'span_sp',round((x1-x0)/sp,1))
