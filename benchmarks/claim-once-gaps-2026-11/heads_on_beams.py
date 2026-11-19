"""2.322: head boxes whose ink lies on beam-role strokes (stroke map roles, beam_strokes.roles with the one-beam-count args), from gaps_page.py's npz + heads json.
    python3 heads_on_beams.py PLATE DATADIR"""
import collections, json, sys, pathlib
import numpy as np
plate, data = sys.argv[1], pathlib.Path(sys.argv[2])
heads = json.load(open(data / ("%s_heads.json" % plate)))
by = collections.defaultdict(list)
for h in heads: by[h["page"]].append(h)
out = []
ST_STAFF = 5
for pg, hs in by.items():
    z = np.load(data / ("%s_p%d.npz" % (plate, pg)))
    ink, rm, st, nn = z["ink"], z["rolemap"], z["state"], z["none"]
    for h in hs:
        x0, y0, x1, y1 = h["box"]
        m = ink[y0:y1, x0:x1] & (st[y0:y1, x0:x1] != ST_STAFF)
        n = int(m.sum())
        if not n: continue
        r = rm[y0:y1, x0:x1][m]
        bshare = float(np.isin(r, [1, 2, 3]).sum()) / n
        h2 = dict(h); h2["beam_role_share"] = round(bshare, 3); h2["span_hook_share"] = round(float(np.isin(r, [4, 5, 6]).sum()) / n, 3)
        out.append(h2)
json.dump(out, open(data / ("%s_heads2.json" % plate), "w"))
for lo in (0.1, 0.25, 0.5, 0.75):
    sel = [h for h in out if h["beam_role_share"] >= lo]
    print("beam-role stroke ink >= %.2f of the head box: boxes %d, written as notes %d, head-bit-owned px>0 %d" % (lo, len(sel), sum(h["written"] for h in sel), sum(1 for h in sel if h["head_any_px"] > 0)))
# the ones written with >=50%: show for crops
sel = sorted([h for h in out if h["beam_role_share"] >= 0.5 and h["written"]], key=lambda h: -h["beam_role_share"])
print("written, beam-role >= .5: %d" % len(sel))
for h in sel[:15]: print(h["subject"], h["box"], h["beam_role_share"], h["head_only_px"], h["ink"], h["written_as"])
