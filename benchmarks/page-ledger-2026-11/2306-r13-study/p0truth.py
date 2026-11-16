"""2.306 r13 study, Q3: both readers against Sean's hand-labelled Brahms page 0 (data/hand-truth/pages/imslp317803/0.json: his noteheads and his
stems). Who says it is right: Sean's labels. Per notehead of HIS: his stem = the stem label touching it (direction = the side it runs out);
OLD = the cell join's stem row (page px) and direction; NEW = the page stem. Per head box of OURS that is on none of his noteheads: does each
reader give it a stem (a stem on a non-note)? Usage (cwd = repo root): p0truth.py"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
D = load("bra")
ups = cell_up(D)
T = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
his_heads = [b for b in T["boxes"] if b["cls"].startswith("notehead")]
his_stems = [b["rect"] for b in T["boxes"] if b["cls"] == "stem"]
other = [b for b in T["boxes"] if not b["cls"].startswith("notehead") and b["cls"] not in ("stem", "ledgerLine", "tie", "slur", "beam", "brace", "text", "barlineSingle", "barlineDouble")]


def touch(s, h, tol):
    return s[0] <= h[2] + tol and s[2] >= h[0] - tol and s[1] <= h[3] + tol and s[3] >= h[1] - tol


def col(a, b):
    ov = min(a[3], b[3]) - max(a[1], b[1])
    return abs((a[0] + a[2]) / 2.0 - (b[0] + b[2]) / 2.0) <= 10 and ov >= 0.5 * min(a[3] - a[1], b[3] - b[1])


ours = {g: h for g, h in D["heads"].items() if pg(g) == 0}
c = collections.Counter()
detail = []
used = set()
for hh in his_heads:
    r = hh["rect"]
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    st = [s for s in his_stems if touch(s, r, 4)]
    want = None
    if st:
        s = max(st, key=lambda s: s[3] - s[1])
        want = "up" if (r[1] - s[1]) > (s[3] - r[3]) else "down"
    mine = [g for g, h in ours.items() if h["box"][0] - 2 <= cx <= h["box"][2] + 2 and h["box"][1] - 2 <= cy <= h["box"][3] + 2 and is_real(D, g, "on")]
    used.update(g for g, h in ours.items() if h["box"][0] - 2 <= cx <= h["box"][2] + 2 and h["box"][1] - 2 <= cy <= h["box"][3] + 2)
    if not mine:
        c["his notehead: no real head box of ours on it"] += 1
        continue
    if not st:
        c["his notehead has no stem label (whole note / unlabelled)"] += 1
    best = {}
    for who in ("OLD", "NEW"):
        res = "none"
        for g in mine:
            if who == "OLD":
                o = old_answer(D, g)
                b = stem_page_box(D, ups, o["stem"]) if o["stem"] else None
                d = o["direction"]
            else:
                n = new_answer(D, g)
                b = n["row"].get("stem_box") if n["read"] else None
                d = n["direction"]
                if not n["read"] and n["how"] == "two_voices":
                    res = "two_voices" if res == "none" else res
            if b is None:
                continue
            if not st:
                res = "stem where he labels none"
            elif any(col(b, s) for s in st):
                res = "his stem, his direction" if d == want else ("his stem, direction %s" % ("unknown" if d is None else "WRONG"))
                break
            else:
                res = "a stem, NOT his"
        best[who] = res
        if st:
            c[(who, res)] += 1
        else:
            c[(who, "no-stem head: " + res)] += 1
    detail.append((hh["id"], mine[0], want, best))
print("Sean's Brahms p0: noteheads %d, stems %d" % (len(his_heads), len(his_stems)))
for k, v in sorted(c.items(), key=lambda t: str(t[0])):
    print("  %4d  %s" % (v, k))
# our head boxes on none of his noteheads
c2 = collections.Counter()
ex = []
for g, h in ours.items():
    if g in used:
        continue
    b = h["box"]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    what = next((o["cls"] for o in other if o["rect"][0] - 3 <= cx <= o["rect"][2] + 3 and o["rect"][1] - 3 <= cy <= o["rect"][3] + 3), "nothing he labelled a mark (or a stem/beam/slur)")
    o, n = old_answer(D, g), new_answer(D, g)
    real = is_real(D, g, "on")
    c2[("box not on his notehead", "kept as a real head" if real else "refused / other staff's copy")] += 1
    if o["stem"]:
        c2[("OLD stems it", "kept" if real else "refused/copy", "written OFF" if g in D["written_off"] else "not written")] += 1
        if real:
            ex.append((g, what, "written" if g in D["written_off"] else ""))
    if n["read"]:
        c2[("NEW stems it", "kept" if real else "refused/copy", "written ON" if g in D["written_on"] else "not written")] += 1
print("our head boxes on page 0 that stand on none of his noteheads:")
for k, v in sorted(c2.items(), key=lambda t: str(t)):
    print("  %4d  %s" % (v, " | ".join(k)))
print(" OLD-stemmed kept boxes that are not his noteheads:", ex[:40])
json.dump(detail, open(S + "/r13/p0truth.json", "w"))
