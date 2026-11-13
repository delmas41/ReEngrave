"""Lost ties whose bar shows no stem-direction change: what differs there (bar quantities) and what the tie partner's bar shows."""
import sys, os
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "diag_twins.py")).read().split("for kind in")[0]
exec(src)
for rg, hs in HA.items():
    na = sum(len((h.get("sub") or {}).get("tie") or ()) for h in hs)
    nb = sum(len((h.get("sub") or {}).get("tie") or ()) for h in HB.get(rg, ()))
    if na > nb and classify(bar_rg(rg)) == "none":
        a = [(h.get("pitch"), h.get("onset"), h["sub"].get("tie")) for h in hs]
        b = [(h.get("pitch"), h.get("onset"), (h.get("sub") or {}).get("tie")) for h in HB.get(rg, ())]
        bar = bar_rg(rg)
        dq = sorted({q for (q, s) in set(IA.get(bar, {})) | set(IB.get(bar, {})) if sig(IA.get(bar, {}).get((q, s))) != sig(IB.get(bar, {}).get((q, s)))})
        print(rg, a, b, dq)
