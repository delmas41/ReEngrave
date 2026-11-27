import sys, numpy as np, pickle, time
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ae6bdd147632e2db9")
from tools.omr.staged import cell_map as CM
PDF="/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
S=sys.argv[1]
for p in [int(x) for x in sys.argv[2:]]:
    t=time.time()
    pws=CM.load_prepared(PDF,[p])[0][0]
    np.save(f"{S}/bin{p}.npy", pws.page.binary)
    st=[dict(i=s.staff_index,sys=s.system_index,top=float(s.top_y),bot=float(s.bottom_y),sp=float(s.line_spacing_px)) for s in pws.staves]
    pickle.dump(st, open(f"{S}/st{p}.pkl","wb"))
    print(p, pws.page.binary.shape, pws.page.binary.dtype, len(st), round(time.time()-t,1), flush=True)
