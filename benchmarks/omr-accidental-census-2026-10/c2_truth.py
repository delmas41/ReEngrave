"""2.197 C2: the hand-boxed truth on the Brahms record cells, in PAGE pixels.
Sources: (A) v18-complete-breitkopf label cells of pdf pages 1,2,3 -- mapped onto the record's cell_box by the cell manifest's (system,page-level
staff,measure); the mapping is CHECKED by comparing the label cell's canonical h/w with the record cell's (agrees to 0.1% on all 36 cells);
(B) data/hand-truth/pages/imslp317803/0.json (page 0, boxes already in page px, cell ids s<sys>-st<staff>-m<cell>).
Writes truth_brahms.json: items with page/system/staff(local)/cell, label class, type, page box, neighbours.
usage: c2_truth.py REPO_MAIN SLICE_OBS_JSONL OUT.json T1_CELLS.json"""
import sys, json, glob, pathlib, collections
REPO = pathlib.Path(sys.argv[1]); obs_path = sys.argv[2]; out = sys.argv[3]
names = json.load(open(REPO / "tools/omr/training/deepscoresv2_208_classes.json"))
ACC = {59: ("flat", "A"), 60: ("flat", "A"), 61: ("natural", "A"), 62: ("natural", "A"), 63: ("sharp", "A"), 64: ("sharp", "A"), 65: ("dsharp", "A"),
       66: ("dflat", "A"), 170: ("flat", "B"), 171: ("natural", "B"), 172: ("sharp", "B"), 173: ("dsharp", "B"), 174: ("dflat", "B")}
KEY = {67: "flat", 68: "natural", 69: "sharp"}
def kind_of(name):
    n = name.lower()
    for t, k in (("doubleflat", "dflat"), ("doublesharp", "dsharp"), ("flat", "flat"), ("natural", "natural"), ("sharp", "sharp")):
        if t in n: return k
cb = {}
for l in open(obs_path):
    if '"cell_box"' in l:
        o = json.loads(l)
        if o["quantity"] == "cell_box":
            s = o["subject"].split("/"); cb[tuple(int(x) for x in s[1:])] = o["value"]
def local_staff(page, system, pstaff):
    n = sum(len({k[2] for k in cb if k[0] == page and k[1] == s}) for s in {k[1] for k in cb if k[0] == page} if s < system)
    return pstaff - n
rows = {}
for f in glob.glob(str(REPO / "benchmarks/**/*cells*.json"), recursive=True):
    try: d = json.load(open(f))
    except Exception: continue
    rs = d if isinstance(d, list) else d.get("cells") if isinstance(d, dict) else []
    for r in rs or []:
        if isinstance(r, dict) and "cell_id" in r and r["cell_id"] not in rows: rows[r["cell_id"]] = r
cells_v18 = json.load(open(sys.argv[4]))     # c2a_enum.py output
items, heads = [], []
lab_dir = REPO / "data/user-labeled"
v18 = [p for p in lab_dir.glob("v18*")][0]
for key, lst in cells_v18.items():
    if not key.startswith("v18"): continue
    _, ed, pg = key.split("|"); pg = int(pg)
for f in sorted(v18.glob("labels/*.txt")):
    r = rows.get(f.stem)
    if not r or r.get("page") not in (1, 2, 3): continue
    pg = int(r["page"]); sysi = r["system_index"]; ls = local_staff(pg, sysi, r["staff_index"]); ci = r["measure_index"]
    rect = cb.get((pg, sysi, ls, ci))
    if rect is None: print("NO RECORD CELL", f.stem); continue
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    for l in f.read_text().splitlines():
        p = l.split()
        if len(p) < 5: continue
        c = int(p[0]); cx, cy, bw, bh = (float(x) for x in p[1:5])
        box = [rect[0] + (cx - bw / 2) * w, rect[1] + (cy - bh / 2) * h, rect[0] + (cx + bw / 2) * w, rect[1] + (cy + bh / 2) * h]
        if c in ACC or c in KEY:
            items.append(dict(src="v18", cell_label=f.stem, page=pg, system=sysi, staff=ls, cell=ci, cls=names[c], cid=c,
                              type=(ACC[c][0] if c in ACC else KEY[c]), label_family=("accidental" if c in ACC else "key"),
                              series=(ACC[c][1] if c in ACC else "K"), box=box, cell_rect=rect))
        elif "notehead" in names[c].lower() or names[c].startswith("rest"):
            heads.append(dict(page=pg, system=sysi, staff=ls, cell=ci, cls=names[c], box=box))
# (B) page 0
p0 = json.load(open(REPO / "data/hand-truth/pages/imslp317803/0.json"))
cid = {c["id"]: c for c in p0["cells"]}
for b in p0["boxes"]:
    c = cid.get(b["cell_id"])
    if not c or c.get("kind") != "measure": continue
    cls = b["cls"]; low = cls.lower()
    sysi, ls, ci = c["system"], c["staff"], c["measure"]
    ls = local_staff(0, sysi, ls)
    rect = cb.get((0, sysi, ls, ci))
    if low.startswith("accidental") or low.startswith("key"):
        fam = "key" if low.startswith("key") else "accidental"
        items.append(dict(src="p0", cell_label=b["cell_id"], page=0, system=sysi, staff=ls, cell=ci, cls=cls, cid=None, type=kind_of(cls), label_family=fam,
                          series="p0", origin=b["origin"], box=b["rect"], cell_rect=rect))
    elif "notehead" in low or low.startswith("rest"):
        heads.append(dict(page=0, system=sysi, staff=ls, cell=ci, cls=cls, box=b["rect"]))
print(collections.Counter((i["src"], i["label_family"], i["type"]) for i in items))
json.dump(dict(items=items, heads=heads), open(out, "w"))
