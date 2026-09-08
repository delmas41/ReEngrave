import csv, sys, glob, os, collections
def read(pat, lab):
    c=sorted(glob.glob(pat))
    if not c: sys.exit(f"FATAL: no csv for {lab} at {pat}")
    rows=list(csv.reader(open(c[0]))); hdr=[h.strip() for h in rows[0]]
    i_gt=hdr.index('gtpath')
    out={}
    for r in rows[1:]:
        if len(r)<=i_gt: continue
        g=r[i_gt].strip()
        if not g.endswith('.musicxml'): continue   # skips the blank + Total rows
        out[os.path.basename(g).replace('.musicxml','')]={h:v.strip() for h,v in zip(hdr,r)}
    if not out: sys.exit(f"FATAL: parsed 0 data rows for {lab} — a zero table here "
                         f"would be a parser failure, not a result")
    return hdr,out
def num(v):
    try: return float(v)
    except Exception: return 0.0
A=read(sys.argv[1],"AllObjects"); B=read(sys.argv[2],"+NoteStaffPosition")
assert set(A[1])==set(B[1]), "arms scored different pair sets"
cats=[h for h in A[0] if h.endswith("OMR-ED") and "bad kern" not in h]
ta=collections.Counter(); tb=collections.Counter()
for n in A[1]:
    for c in cats:
        ta[c]+=num(A[1][n].get(c,0)); tb[c]+=num(B[1][n].get(c,0))
print(f"rows compared: {len(A[1])}")
print(f"{'bucket':32s}{'AllObjects':>12s}{'+StaffPos':>12s}{'delta':>10s}{'':>4s}")
for c in sorted(cats, key=lambda c:-ta[c]):
    if ta[c]==0 and tb[c]==0: continue
    print(f"{c.replace(' OMR-ED',''):32s}{ta[c]:12.0f}{tb[c]:12.0f}{tb[c]-ta[c]:+10.0f}")
print(f"{'TOTAL':32s}{sum(ta.values()):12.0f}{sum(tb.values()):12.0f}{sum(tb.values())-sum(ta.values()):+10.0f}")
print("\nPER-ROW 'wrong note':")
print(f"{'row':34s}{'AllObj':>9s}{'+StaffPos':>11s}{'delta':>9s}")
wn='wrong note OMR-ED'
for n in sorted(A[1], key=lambda n:-num(A[1][n][wn])):
    a,b=num(A[1][n][wn]),num(B[1][n][wn])
    print(f"{n:34s}{a:9.0f}{b:11.0f}{b-a:+9.0f}")
