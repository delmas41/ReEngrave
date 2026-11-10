"""2.282 step 1 (STAGED, read-only): KIND (b) -- kept head boxes whose OWN INK reads as an accidental (sharp / natural / flat by the shipped 2.201/2.247 stroke
reader `accidental_family`), with no accidental box over it. Same code the accidental boxes are read with, run on a head box. Decides nothing.
For each kept head box: members = strokes under the box grown along touching strokes (one accidental's size), type = read_type, and whether another kept
head stands to its right within RIGHT_SP at about its height (page-facts s3: an accidental stands left of its head).
usage: c3_sharpheads.py SLICE_DIR PLATE OUT.json [pages]"""
import collections
import json
import sys
from types import SimpleNamespace

sys.path.insert(0, ".")
from tools.omr.staged import accidental_family as AF      # noqa: E402

d, plate, out = sys.argv[1:4]
pages = {int(x) for x in sys.argv[4].split(",")} if len(sys.argv) > 4 else None
RIGHT_SP = 3.0

glyph = {}
cells = collections.defaultdict(list)
strokes = collections.defaultdict(dict)       # cell -> ordinal -> Stroke-like
gshare = {}
sp_of = {}
for line in open(d + "/observations.jsonl"):
    if not ('"glyph_box"' in line or '"stroke"' in line or '"glyph_strokes"' in line or '"cell_staff_space"' in line):
        continue
    o = json.loads(line)
    q = o["quantity"]
    sub = o["subject"]
    if q == "cell_staff_space":
        sp_of[sub] = o["value"]
        continue
    if not sub.startswith("glyph/"):
        continue
    parts = sub.split("/")
    page = int(parts[1])
    if pages is not None and page not in pages:
        continue
    cell = "cell/" + "/".join(parts[1:5])
    if q == "glyph_box":
        dd = o["detail"] or {}
        if dd.get("bbox_page_px"):
            glyph[sub] = dict(cls=o["value"][0], cbox=o["value"][1:5], page=page, pbox=dd["bbox_page_px"], score=o.get("score"), cell=cell)
            cells[cell].append(sub)
    elif q == "glyph_strokes":
        gshare[sub] = list(zip(o["value"], (o["detail"] or {}).get("shares") or [1.0] * len(o["value"])))
        for a, b in ((o["detail"] or {}).get("partial") or ()):
            gshare[sub].append((a, b))
    elif q == "stroke":
        ordn = int(parts[5]) - 375000
        dd = o["detail"]
        if ordn < 0:
            continue
        strokes[cell][ordn] = SimpleNamespace(kind=o["value"], box=tuple(dd["stroke_box"]), length_sp=float(dd.get("length_spaces") or 0),
                                              touches=[(int(a), float(b)) for a, b in (dd.get("touches") or ())], parts=[],
                                              sp=float(dd.get("staff_space_local_px") or 0), page=dd.get("bbox_page_px"))

kept = {}
verds = collections.defaultdict(dict)
for line in open(d + "/verdicts.jsonl"):
    if '"notehead_is_not_a_notehead"' not in line and '"accidental_is_not_an_accidental"' not in line:
        continue
    v = json.loads(line)
    sub = v["subject"]
    if v["quantity"] == "notehead_is_not_a_notehead":
        if v["outcome"] == "decided" and v["reason"] == "notehead":
            kept[sub] = v
    else:
        verds[sub]["acc"] = (v["outcome"], v["reason"], v["value"])


def ov(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / max(1.0, min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])))


rows = []
for sub in kept:
    g = glyph.get(sub)
    if g is None or not str(g["cls"]).lower().startswith("notehead"):
        continue
    st = strokes.get(g["cell"], {})
    sh = [(i, s) for i, s in gshare.get(sub, []) if i in st]
    if not sh:
        continue
    sp = next((st[i].sp for i, _ in sh if st[i].sp), 0.0) or sp_of.get(g["cell"], 0.0)
    if not sp:
        continue
    x, y, w, h = g["cbox"]
    # ordinals are cell-local and the stroke list is addressed by ordinal: build a dense list
    mx = max(st)
    dense = [st.get(i) or SimpleNamespace(kind="blob", box=(0, 0, 0, 0), length_sp=0.0, touches=[], parts=[], sp=sp) for i in range(mx + 1)]
    ext = AF.ink_members_and_extent([x, y, x + w, y + h], dense, sh, sp)
    if not ext["members"]:
        continue
    typ = AF.read_type(dense, ext["members"], sp, ext.get("refused_vertical") or ())
    # an accidental box over this ink, and another kept head to the right at about its height
    acc_over = [t for t in cells[g["cell"]] if str(glyph[t]["cls"]).lower().startswith("accidental") and ov(g["pbox"], glyph[t]["pbox"]) >= 0.3]
    px0, py0, px1, py1 = g["pbox"]
    spp = sp * (px1 - px0) / max(1.0, float(w))          # staff space in PAGE px (the box is the same box in two frames)
    right = [t for t in kept if t != sub and glyph.get(t, {}).get("cell") == g["cell"]
             and 0 <= (glyph[t]["pbox"][0] - px1) / spp <= RIGHT_SP and abs((glyph[t]["pbox"][1] + glyph[t]["pbox"][3]) / 2 - (py0 + py1) / 2) / spp <= 1.6]
    rows.append(dict(sub=sub, plate=plate, page=g["page"], cls=g["cls"], score=g["score"], page_box=g["pbox"], sp=sp, sp_page=spp,
                     type=typ["type"], why=typ.get("why"), margin=typ.get("margin"), n_stems=typ.get("n_stems"), n_members=typ.get("n_members"),
                     ink_box_cell=ext["box"], acc_box_over=acc_over, head_to_right=right))
json.dump(rows, open(out, "w"))
c = collections.Counter((r["type"], bool(r["acc_box_over"]), bool(r["head_to_right"])) for r in rows)
print(plate, "kept head boxes read", len(rows))
for k, n in sorted(c.items(), key=lambda x: -x[1]):
    print("  type=%-8s acc_box_over=%-5s head_to_right=%-5s : %d" % (k[0], k[1], k[2], n))
sh_rows = [r for r in rows if r["type"] == "sharp" and not r["acc_box_over"]]
print("sharp-reading head boxes, no accidental box:", len(sh_rows), "per page", dict(sorted(collections.Counter(r["page"] for r in sh_rows).items())))
