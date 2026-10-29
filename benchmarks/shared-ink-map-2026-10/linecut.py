"""2.230 line-cut check (read-only on tools/): every WRITTEN note of the 2.220 m2b ON arm, its filed Q.HEAD_INK, its staff
position (line / space by rounded parity), and trim_head re-run on the page raster under variants that switch parts of the line
cut off IN MEMORY (monkeypatch; nothing in tools/ is edited).
usage: python3 linecut.py OUT_DIR"""
import collections, json, sys, os
import numpy as np

sys.path.insert(0, os.getcwd())
from tools.omr.staged import head_ink as HI
from tools.omr.staged import head_oval as HO
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

R = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-abe33f84eed18488d/out/lane-report/2.220-m2"
L = "/Users/seanjohnson/Desktop/ReEngrave/library/editions"
PDF = {"litolff": L + "/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": L + "/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)

_orig_bare, _orig_lr, _orig_led = HI._bare_line_pixels, HO._line_rows, HI.LEDGER_MIN_SPACES


def variant(name):
    HI._bare_line_pixels, HO._line_rows, HI.LEDGER_MIN_SPACES = _orig_bare, _orig_lr, _orig_led
    if name in ("no_cut", "no_bare"):
        HI._bare_line_pixels = lambda ink, lr: np.zeros_like(ink)
    if name in ("no_cut", "no_line_rows"):     # no staff rows, no ledger rows: nothing bare, no end-row trim
        HO._line_rows = lambda iw: np.zeros(iw.shape[0], bool)
        HI.LEDGER_MIN_SPACES = 50.0   # wider than any crop (~3 sp): no row survives; 1e6 made a 40M-px cv2 kernel
    if name == "no_led":
        HI.LEDGER_MIN_SPACES = 50.0   # wider than any crop (~3 sp): no row survives; 1e6 made a 40M-px cv2 kernel


VARIANTS = ("filed", "no_led", "no_bare", "no_line_rows", "no_cut")
rows = []
for plate in ("litolff", "brahms"):
    hi, pos = {}, {}
    for kind in ("observations", "abstentions"):
        for line in open("%s/slices/%s/%s.jsonl" % (R, plate, kind)):
            if '"head_ink"' in line or '"notehead_staff_position"' in line:
                o = json.loads(line)
                if o.get("quantity") == "head_ink":
                    d = dict(o.get("detail") or {})
                    d["value"], d["reason"] = o.get("value"), o.get("reason")
                    hi[o["subject"]] = d
                elif o.get("quantity") == "notehead_staff_position" and "value" in o:
                    pos[o["subject"]] = (o["value"], (o.get("detail") or {}).get("rounded"))
    S = json.load(open("%s/report-b/work/%s.on.symbols.json" % (R, plate)))
    notes = [h for h in S["hosts"] if h.get("kind") == "note"]
    pages = sorted({h["page"] for h in notes})
    for p in pages:
        pws = detect_staves(render_page(PDF[plate], p, dpi=600))
        pb = pws.page.binary
        sps = [(d["trimmed"][2] - d["trimmed"][0]) / d["extent_sp"][0] for s, d in hi.items()
               if s.startswith("glyph/%d/" % p) and d.get("trimmed") and d.get("extent_sp")]
        sp_page = float(np.median(sps))
        for h in notes:
            if h["page"] != p:
                continue
            s = h["rg"]
            d = hi.get(s) or {}
            box = d.get("page_box")
            if not box:
                continue
            sp = ((d["trimmed"][2] - d["trimmed"][0]) / d["extent_sp"][0]) if d.get("trimmed") and d.get("extent_sp") else sp_page
            pv, pr = pos.get(s, (None, None))
            r = dict(plate=plate, page=p, sub=s, box=box, sp=sp, pos=pv, rounded=pr, type=h.get("type"), chord=h.get("chord"),
                     filed_noh=d.get("not_one_head"), filed_ext=d.get("extent_sp"), filed_line_px=d.get("line_px_out"))
            for v in VARIANTS:
                variant(v)
                t = HI.trim_head(pb, box, sp, ())
                r[v] = None if t is None else dict(noh=t["not_one_head"], ext=t["extent_sp"], trimmed=t["trimmed"],
                                                    line_px=t["line_px_out"])
            variant("filed")
            rows.append(r)
        print(plate, p, "sp", round(sp_page, 2), "binary", pb.shape, flush=True)
json.dump(rows, open(out_dir + "/rows.json", "w"))


def where(r):
    if r["rounded"] is None:
        return "no_pos"
    k = "line" if r["rounded"] % 2 == 0 else "space"
    return k + ("_in" if 0 <= r["rounded"] <= 8 else "_out")


for plate in ("litolff", "brahms"):
    P = [r for r in rows if r["plate"] == plate]
    ctl = sum(1 for r in P if r["filed"] and r["filed"]["noh"] == r["filed_noh"] and r["filed"]["ext"] == r["filed_ext"])
    print("\n%s written notes with a head_ink row: %d; control (re-run 'filed' == record): %d" % (plate, len(P), ctl))
    for v in VARIANTS:
        c = collections.defaultdict(collections.Counter)
        for r in P:
            t = r[v]
            c[where(r)]["n"] += 1
            c[where(r)][(t or {}).get("noh") or "one_head"] += 1
        print("  %-13s" % v + "  ".join("%s n=%d small=%d tall=%d wide=%d nohink=%d" % (
            w, c[w]["n"], c[w]["too_small"], c[w]["too_tall"], c[w]["too_wide"], c[w]["no_head_ink"]) for w in sorted(c)))
    hs = collections.defaultdict(list)
    for r in P:
        for v in ("filed", "no_cut"):
            if r[v] and r[v]["ext"]:
                hs[(where(r), v)].append(r[v]["ext"][1])
    for k in sorted(hs):
        a = sorted(hs[k])
        print("  height_sp %-10s %-7s median %.2f  p10 %.2f  <0.6: %d of %d" % (k[0], k[1], a[len(a) // 2], a[len(a) // 10],
                                                                              sum(1 for x in a if x < 0.6), len(a)))
    sm = [r for r in P if r["filed"] and r["filed"]["noh"] == "too_small"]
    fixed = collections.Counter((where(r), (r["no_cut"] or {}).get("noh") or "one_head") for r in sm)
    print("  filed too_small -> no_cut verdict:", dict(fixed))
    wsm = collections.Counter("w<0.6" if r["filed"]["ext"][0] < 0.6 else "h<0.6" for r in sm)
    print("  filed too_small by axis:", dict(wsm))
