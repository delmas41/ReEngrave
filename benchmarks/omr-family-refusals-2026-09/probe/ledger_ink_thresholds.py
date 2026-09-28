import sys, json, pathlib, bisect
sys.path.insert(0, str(pathlib.Path.cwd()))
sys.path.insert(0, 'benchmarks/omr-family-refusals-2026-09/probe')
from ledger_ink_hist import populations
from tools.omr.staged.record_io import load_record
rec = load_record(sys.argv[1])['record']
ink, pops = populations(rec)
N = pops['NEG_inside'] + pops['NEG_online']
P = pops['POS_on']
T = pops['TARGET']


def auc(p, n):
    ns = sorted(n)
    s = 0.0
    for a in p:
        lo = bisect.bisect_left(ns, a); hi = bisect.bisect_right(ns, a)
        s += lo + 0.5 * (hi - lo)
    return s / len(p) / len(ns)


def c(r):
    return r[1] - (r[2] or 0.0)

out = {}
for name, f in (("under", lambda r: r[1]), ("contrast", c),
                ("RED_background", lambda r: r[2] or 0.0)):
    out[name] = {k: round(auc([f(r) for r in pops[k]], [f(r) for r in N]), 3)
                 for k in ("POS_on", "POS_near", "POS_kept")}
print("AUC vs NEG (inside+online):", json.dumps(out))
print("RED: AUC of the SWAPPED measure (background read as under) vs the real one")
for t in (0.02, 0.05, 0.1, 0.15, 0.2):
    print(f"under<={t}: POS_on {sum(r[1]<=t for r in P)}/{len(P)}  POS_near {sum(r[1]<=t for r in pops['POS_near'])}  NEG {sum(r[1]<=t for r in N)}/{len(N)}  TARGET {sum(r[1]<=t for r in T)}/{len(T)}")
print('POS_on lowest under', sorted(round(r[1], 3) for r in P)[:8])
for u in (0.4, 0.5, 0.55, 0.6):
    for cc in (0.0, 0.1, 0.2, 0.3, 0.4):
        kp = sum(r[1] >= u and c(r) >= cc for r in P)
        kn = sum(r[1] >= u and c(r) >= cc for r in N)
        kt = sum(r[1] >= u and c(r) >= cc for r in T)
        print(f"under>={u} contrast>={cc}: POS_on {kp}/{len(P)} ({kp/len(P):.2f})  NEG {kn}/{len(N)} ({kn/len(N):.3f})  TARGET {kt}")
