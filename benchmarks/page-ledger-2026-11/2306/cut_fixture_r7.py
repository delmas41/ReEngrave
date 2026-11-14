"""2306 r7 real-case fixtures (CLAUDE rule 7: the pixels of marks Sean has named), cut from the r6 gathers (OMR_PAGE_STEMS=1).

  stitch: the two r6 stitched stems that bridged blank paper behind real losses (Litolff p9 glyph/9/0/2/1/0, 1.06 sp of empty column;
          p10 glyph/10/1/6/7/3) -- heads, vertical pieces, crossers, held -- around the page stem the record filed for that glyph.
  copies: Sean's r4 lost tiles 3, 11 (Litolff) and 7, 12 (Brahms), and r4 tile 5 (an eighth made a quarter): every page head of the
          tile's system seen from two staves, with the staff frames of that system (each staff's five lines per bar, page px) and the
          staff each copy was filed on -- so `page_stems.own_staff` is tested on the heads whose filed copies cost these notes.

Usage (cwd = a tree with the library): cut_fixture_r7.py LIT_REC [BRA_REC] OUT.json"""
import sys, os, json, importlib.util
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record

here = os.path.dirname(os.path.abspath(__file__))
src4 = open(os.path.join(here, "cut_fixture_r4.py")).read().split("\nlit = load_record")[0]
c4 = {}
exec(compile(src4, "cut_fixture_r4.py", "exec"), c4)
page_parts, cut = c4["page_parts"], c4["cut"]

lit_p = sys.argv[1]
bra_p = sys.argv[2] if len(sys.argv) > 3 else None   # LIT_REC BRA_REC OUT.json
out_p = sys.argv[-1]
lit = load_record(lit_p)["record"]
out = {"about": "ROADMAP 2.306 r7 real-case fixtures, cut by benchmarks/page-ledger-2026-11/2306/cut_fixture_r7.py from %s (page px, 600 dpi)."
       % os.path.basename(lit_p)}


def stem_box_of(rec, glyph):
    for o in rec["observations"]:
        if o["quantity"] == "page_stem" and o["subject"] == glyph and (o.get("detail") or {}).get("stem_box"):
            return [float(v) for v in o["detail"]["stem_box"]]
    return None


for name, glyph in (("stitch_p9", "glyph/9/0/2/1/0"), ("stitch_p10", "glyph/10/1/6/7/3")):
    p = int(glyph.split("/")[1])
    sb = stem_box_of(lit, glyph)
    if sb is None:
        out[name] = {"glyph": glyph, "missing": "no page_stem row with a stem_box"}
        continue
    out[name] = dict(page=p, glyph=glyph, stem_box=sb, **cut(page_parts(lit, p), sb[0] - 90, sb[1] - 40, sb[2] + 90, sb[3] + 40))

# copies: frames from the re-cut cells (page_owner's route), heads from the page_mark rows
from tools.omr.staged import claim_readout as CR, page_marks as PM, page_owner as PO, cell_map as CM


def copies(rec_path, tiles):
    src = CR.resolve_source(rec_path)
    res = {}
    for name, glyph in tiles:
        p = int(glyph.split("/")[1])
        system = "staff/%s/%s/" % (p, glyph.split("/")[2])
        rows = CR.read_rows(src, [p])
        pdf = CR.LIB / CR.edition_info(rows)["edition_path"]
        pws, cells, local, views, verify = PM.page_views(rows, pdf, p, CM.ROOT_DEFAULT)
        frames = PO.staff_frames(cells, local)
        fr = {k: [dict(x0=b.x0, x1=b.x1, ys=list(b.ys), sp=b.sp) for b in v] for k, v in frames.items() if k.startswith(system)}
        heads = []
        oval = {}
        for o in rows["observations"]:
            d = o.get("detail") or {}
            if o["quantity"] == "claimed_area" and d.get("source") == "page_head_one" and d.get("oval"):
                for m in d.get("members") or ():
                    oval[m] = d["oval"]
        gbox = {o["subject"]: o["detail"]["bbox_page_px"] for o in rows["observations"]
                if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")}
        filed = {}
        for o in rows["observations"]:
            if o["quantity"] == "page_stem":
                filed.setdefault(o["subject"], (o.get("detail") or {}).get("head"))
        for o in rows["observations"]:
            d = o.get("detail") or {}
            if o["quantity"] == "page_mark" and d.get("family") == "head":
                mem = d["members"]
                if not any(m.startswith("glyph/%s/%s/" % (p, glyph.split("/")[2])) for m in mem):
                    continue
                if len({"/".join(m.split("/")[:4]) for m in mem}) < 2:
                    continue
                b = next((oval[m] for m in mem if m in oval), None) or next((gbox[m] for m in mem if m in gbox), None)
                if b:
                    heads.append(dict(members=mem, box=[float(v) for v in b], filed_on=[m for m in mem if m in filed]))
        res[name] = dict(page=p, glyph=glyph, frames=fr, heads=heads)
        del pws, cells, views
    return res


out["copies"] = copies(lit_p, [("tile3", "glyph/4/1/2/5/1"), ("tile5", "glyph/4/1/2/4/11"), ("tile11", "glyph/9/0/2/0/6")])
if bra_p:
    out["copies"].update(copies(bra_p, [("tile7", "glyph/8/0/1/3/3"), ("tile12", "glyph/19/1/8/7/6")]))
json.dump(out, open(out_p, "w"), indent=0)
print({k: (v.get("missing") or (len(v.get("heads", [])), len(v.get("verticals", [])))) for k, v in out.items() if isinstance(v, dict) and "glyph" in v})
print({k: (len(v["heads"]), len(v["frames"])) for k, v in out.get("copies", {}).items()})
