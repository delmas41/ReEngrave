"""lane-farhead-5-6: which bound on the flank re-measure? Replays only the heads whose line the OLD refine MOVED (census OFF `refine`
y_out != y_in), under: B = skip the jut's own row only; C = + walk rungs move <= 1.0 line thickness (+1 px); D = + <= 0.5 thickness (+1).
Writes {variant: {subject: [pos, reason]}}. Read only.
  python3 farhead_5_6_variants.py <x7 extract> <doc> <census off.json> <out.json>"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import farhead_5_6_diag as D
import overnight_1004_report as R
from tools.omr.annotate import ledger_grid as lg

VARIANTS = {"G_contact_nojutskip": (None, True, False), "H_contact_1.0t_nojutskip": (1.0, True, False)}

if __name__ == "__main__":
    src, doc, census, out = sys.argv[1:5]
    off = json.loads(Path(census).read_text())
    subs = [s for s, v in off.items() if v.get("refine") and abs(v["refine"][1] - v["refine"][0]) > 0.01]
    subs.sort(key=lambda s: tuple(int(v) for v in s.split("/")[1:]))
    data, rep = D.load(src, doc)
    D.FH.READER_KEYWORDS["flank_refine_bounded"] = True
    res = {k: {} for k in VARIANTS}
    cur = None
    for s in subs:
        p = R.page_of(s)
        if cur is not None and p != cur:
            rep.gray.pop(cur, None)
        cur = p
        for k, mult in VARIANTS.items():
            lg.FLANK_REFINE_BOUND_THICKNESSES, lg.FLANK_REFINE_CONTACT, lg.FLANK_REFINE_SKIP_JUT = mult
            g, r, cap, gl, ctx = D.read_one(rep, data, s)
            res[k][s] = [r["pos"], r["reason"][:80]]
        if len(res["G_contact_nojutskip"]) % 200 == 0:
            print(len(res["G_contact_nojutskip"]), "of", len(subs), flush=True)
    Path(out).write_text(json.dumps(dict(subjects=subs, off={s: [off[s]["pos"], off[s]["reason"]] for s in subs}, variants=res)))
    print("wrote", out)
