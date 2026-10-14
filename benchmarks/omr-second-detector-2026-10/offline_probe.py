"""2.114 round 2 item 2 follow-up: does leaving the staff line's own rows out (2.73 `notehead_ink_off_line`) and a head-centred standard box
separate Sean's confirmed hollow heads from his confirmed black heads? Page raster frame (600 dpi), spacing = the page's staff space."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staged import record_io
from tools.omr.staged.gather import notehead_ink_off_line, notehead_ink_under
LIT = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
BRA = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
man = json.load(open("out/print/2.114-second-detector/manifest.json"))["tiles"]
ans = json.load(open("out/print/2.114-second-detector/answers.json"))
TILES = {1: None}
rows = []
for tag, pdf, pg, doc in (("lit", LIT, 1, "litolff"), ("bra", BRA, 0, "brahms")):
    gray = render_page(Path(pdf), pg, dpi=600).rgb
    gray = gray if gray.ndim == 2 else gray[..., :3].mean(axis=2)
    img = np.where(gray < 128, 0, 255).astype(np.uint8)
    obs = record_io.load_record(f"runs/2.114/ab/rec-{tag}-on.json")["record"]["observations"]
    sp = {o["subject"]: o["value"] for o in obs if o["quantity"] == "staff_spacing"}
    for t in man:
        h = t["hidden"]
        if h["doc"] != doc: continue
        n = t["n"]; a = ans[f"tile_{n:02d}"]["answer"]
        if a == "not a note" or n in (1, 8, 14): continue
        g = h["key"]; parts = g.split("/")
        spc = sp.get(f"staff/{parts[1]}/{parts[2]}/{parts[3]}") or 15.75
        x0, y0, x1, y1 = h["rect"]
        out = {}
        for name, b in (("box", (x0, y0, x1 - x0, y1 - y0)),
                        ("std", ((x0 + x1) / 2 - 0.7 * spc, (y0 + y1) / 2 - 0.55 * spc, 1.4 * spc, 1.1 * spc))):
            r = notehead_ink_under(img, b); o = notehead_ink_off_line(img, b, spc)
            out[name] = (None if r is None else (round(r["windows"]["center"], 2), round(r["windows"]["ring"], 2)),
                         None if o is None else (round(o["windows"]["center"], 2), round(o["windows"]["ring"], 2)))
        rows.append((n, a, g, out))
for n, a, g, out in sorted(rows):
    print(n, a.ljust(7), g.ljust(18), "box raw/off", out["box"][0], out["box"][1], "| std(box-centre) raw/off", out["std"][0], out["std"][1])
