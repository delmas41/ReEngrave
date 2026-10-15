import sys,json
sys.path.insert(0,'.')
from tools.omr.preprocessing import render_page
from tools.omr.staged import gather as G
R=json.load(open('../../2.129/out/refusals_all.json'))
order=json.load(open('../out/h27_order.json'))
by={r['key']:r for r in R['refusals']}
pages={}
def pg(p):
    if p not in pages: pages[p]=render_page(R['pdf'],p,dpi=600).binary
    return pages[p]
def win(img,cx,cy,sp):
    bx=G._standard_head_box(cx,cy,sp); box=(bx[0],bx[2],bx[1]-bx[0],bx[3]-bx[2])
    m=G.notehead_ink_off_line(img,box,sp)
    return None if m is None else (m['windows']['center'],m['windows']['ring'])
res={}
for i,k in enumerate(order):
    r=by[k];A=r['box_page'];B=r['keeper_box_page']
    sp=(A[3]-A[1])/r['height_spaces']
    cx=(A[0]+A[2]+B[0]+B[2])/4; ys=sorted([(A[1]+A[3])/2,(B[1]+B[3])/2]); mid=(ys[0]+ys[1])/2
    img=pg(r['page']); line=[]
    for sh in (-2,-1,0,1,2):
        lo=mid-sp/2+sh*sp/2; hi=lo+sp
        a=win(img,cx,lo,sp); b=win(img,cx,hi,sp)
        line.append((sh,a,b))
    res[k]=line
    print(i,k[6:],'sp',round(sp,1),'dy',round((ys[1]-ys[0])/sp,2))
    for sh,a,b in line:
        f=lambda w: None if w is None else (round(w[0],2),round(w[1],2))
        print('    ',sh,f(a),f(b))
