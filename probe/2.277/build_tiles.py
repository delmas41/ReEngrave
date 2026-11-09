"""2.277: the 12 blind tiles for Sean ("Is the boxed mark a note?") -> out/print/2.277/ (key.json outside the tile folder).
Cases (7): boxes newly refused BY a claim (flag ON dump): barline heads / rests (Litolff, Brahms), an accidental and an arpeggiato on a barline.
Controls (5): real heads that must stay -- a head beside a barline held 0.1-0.3 (kept), heads held 0.5+ by an ARC trace (kept, MARK_ONLY), a head under a dynamic.
One thin orange box (the lane_report cut), nothing else drawn.  usage: build_tiles.py OUTDIR [seed]"""
import json, os, pathlib, random, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from tools.omr.staged import lane_report as LR
from tools.omr.staged import stroke_owner as SO

out = pathlib.Path(sys.argv[1])
rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 2277)
TAG = "20261104-night"
PL = {"litolff": "out/2.277/dump.litolff.on2.json", "brahms": "out/2.277/dump.brahms.on.json"}
pool = {k: [] for k in ("new_head", "new_rest", "new_acc", "new_arp", "ctl_barline_low", "ctl_arc", "ctl_dyn")}
bp = {}
for plate, f in PL.items():
    D = json.load(open(f))
    for line in open(LR.slice_dir(plate, TAG) / "observations.jsonl"):
        if '"glyph_box"' in line[:300]:
            o = json.loads(line)
            if o["quantity"] == "glyph_box":
                bp[o["subject"]] = o["detail"]["bbox_page_px"]
    for r in D["rows"]:
        fam = SO.family_of(r["cls"], r.get("cat"))
        tot, by = 0.0, {}
        for o, sh, cov, ink, k, own in r["strokes"]:
            if not ink:
                continue
            tot += ink * sh
            if own and own[0] in ("decided", "merged") and own[1] and own[1] != fam:
                by[own[1]] = by.get(own[1], 0) + ink * sh
        if not tot:
            continue
        fate = next(iter(r["fate"].values()), [None, None])
        top = max(by, key=by.get) if by else None
        sh = by[top] / tot if top else 0.0
        item = (plate, r["sub"], round(sh, 2), str(fate[1]))
        if fate[0] is True and str(fate[1]).startswith("claimed_by:barline"):
            if fam == "head":
                pool["new_head"].append(item)
            elif fam == "rest":
                pool["new_rest"].append(item)
            elif fam == "accidental":
                pool["new_acc"].append(item)
            elif fam == "mark":
                pool["new_arp"].append(item)
        elif fam == "head" and fate[0] is False and top == "barline" and 0.1 <= sh < 0.3:
            pool["ctl_barline_low"].append(item)
        elif fam == "head" and fate[0] is False and top == "arc_trace" and sh >= 0.5:
            pool["ctl_arc"].append(item)
        elif fam == "head" and fate[0] is False and top == "word" and sh >= 0.25:
            pool["ctl_dyn"].append(item)
BAD = {"glyph/8/1/8/0/11", "glyph/4/0/6/9/5", "glyph/4/1/1/0/10"}      # crops that came out solid black (a scan border): looked at and dropped
want = (("new_head", 4, "case"), ("new_rest", 1, "case"), ("new_acc", 2, "case"),   # arpeggiato boxes dropped: their crops came out solid black (off the print) twice
        ("ctl_barline_low", 3, "control"), ("ctl_arc", 2, "control"), ("ctl_dyn", 1, "control"))
items = []
for k, n, role in want:
    p = [x for x in pool[k] if x[1] not in BAD and not (k == "new_arp" and x[1].split("/")[4] == "0")]   # cell 0 arpeggiato boxes sit in the black scan margin
    print(k, len(p))
    for plate, sub, sh, why in rng.sample(p, min(n, len(p))):
        if sub in bp:
            items.append(dict(plate=plate, page=int(sub.split("/")[1]), box=bp[sub], role=role, subject=sub, kind=k, share=sh, reason=why))
rng.shuffle(items)
out.mkdir(parents=True, exist_ok=True)
print(LR.cut_tiles(items, out, readme_extra="\n**Question for 2.277, every tile:** is the boxed mark a note? (yes / no; if it is another mark, say which.)\n"))
for n, it in enumerate(items, 1):
    print(n, it["role"], it["kind"], it["share"], it["reason"], it["subject"])
