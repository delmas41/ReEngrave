"""2.281 step 1: the CORRECTED Brahms p0 arc key, built beside Sean's hand labels (data/hand-truth/pages/imslp317803/0.json is never edited).

    python3 key_brahms_p0_build.py     -> key-brahms-p0-corrected.json (arcs + the change list) and a summary on stdout

Sean's boxes are one per CELL (bar) and the labelling is incomplete across a barline (his 2.274 r3 key tiles 2, 5, 6: "those two boxes belong as one long box";
arcs are read at PAGE level).  This builds the arc list a page-level reader should be held to:
  * JOIN   two boxes whose facing ends sit within 1.5 sp of ONE barline (cell edge) and on one y line are the two halves of one arc; staff LABELS are ignored
           (many hand boxes sit in a neighbouring cell's pad: their label names the wrong staff);
  * DEDUPE boxes over the same mark (after joining: both x extents within 40 px and y bands overlapping) are one arc;
  * GHOST  tie boxes over no arc ink are dropped from scoring and listed (GHOST_IDS: the print shows a dotted half note and bare lines);
  * SPLIT  abutting boxes the old scorer chained into one "arc" come apart because each join is one-to-one per barline;
  * CROSS-SYSTEM  a tie whose right end reaches the system's last barline leaves the system: marked, not scorable on one page;
  * UNBOXED HALF  an arc end at a barline with nothing joined to it continues into a cell Sean did not box: the end is `open` and, where the page-ink run of the
           2.274 r3 census witnesses a longer extent, the extent is read off it (`ink_extent`).
Every change that is not Sean's own box is an ASSUMPTION for Sean (`assumed_for_sean`), listed with reason and evidence in `changes`.
Sean's answers used as truth: key tiles 2, 5, 6 (a barline-cut arc is ONE arc).  Tiles 7-12 are PENDING and nothing here treats them as answered
(ghosts = tile 10, half box = 11, chain = 08, cross-system = 07, nested = 09, bound-unwritten = 12): those categories are `assumed_for_sean`.
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRUTH = ROOT / "data/hand-truth/pages/imslp317803/0.json"
BUCKETS = ROOT / "probe/2.274-r3/buckets.json"           # the 2.274 r3 census: per printed arc, the page-ink run that witnesses it (used only to find an unboxed half's extent)
OUT = HERE / "key-brahms-p0-corrected.json"
SP = 32.0
EDGES = [2112, 2671, 3101, 3554, 4107, 4684, 5388]       # cell edges = barlines of the one system (identical on every staff)
LAST_EDGE = 5388
GHOST_IDS = {"q882", "q879", "q878", "q877", "q881"}     # staff 8 bar 1: five `tie` boxes (prefill-confirmed) over a dotted half note; no arc ink there on the print


# what the rules cannot see and the print shows (every row: crop look 2.281, assumed for Sean).  ids are Sean's hand box ids.
MANUAL_MERGE = [
    (["q639", "q647"], "dedupe_label", "two labels of ONE tie (chord 2720 -> chord 3185, staff 5 top): q639 2754-3094 and q647 2688-3095, then joined at 3101 with q660; the old scorer chained it with its neighbours"),
    (["q899", "q1073"], "gap_join", "one slur boxed in two pieces with the middle (4107-4371) unboxed: q899 3672-4107 and q1073 4371-4603 (staff 9, bar 5)"),
]
# an end the print shows running on into a cell nobody boxed: {box id: (side, new page x)}; evidence = the page-ink run of the 2.274 r3 census over the same arc, then a crop look
MANUAL_EXTEND = [
    ("q41", "L", 1666, "slur boxed from the barline only; the arc starts at the first note of bar 1 (x~1666) and crosses the barline at 2112 (Sean's tile 2/5 pattern)"),
    ("b4108", "L", 1666, "same slur one staff lower (staff 1): left half in bar 1 unboxed"),
    ("q949", "L", 1672, "slur boxed from the barline only (staff 8 region); left half in bar 1 unboxed"),
    ("q941", "L", 1994, "tie boxed from the barline only: the left half (1994-2112) unboxed"),
    ("q953", "R", 2742, "slur stub ending at the barline 2671; the arc runs on to 2742 in the next bar"),
    ("q1145", "R", 2254, "tie boxed to the barline only: the right half (2112-2254) unboxed"),
    ("q1538", "R", 4224, "tie boxed to the barline only: the right half (4107-4224) unboxed"),
]


def edge_of(x, tol=1.5 * SP):
    best = None
    for e in EDGES:
        if abs(x - e) <= tol and (best is None or abs(x - e) < abs(x - best)):
            best = e
    return best


def yc(r):
    return (r[1] + r[3]) / 2


def yov(a, b):
    return min(a[3], b[3]) - max(a[1], b[1])


def xov(a, b):
    return min(a[2], b[2]) - max(a[0], b[0])


def build():
    t = json.load(open(TRUTH))
    boxes = [b for b in t["boxes"] if b["cls"] in ("slur", "tie")]
    byid = {b["id"]: b for b in boxes}
    changes = []

    # ---- ghosts
    keep = [b for b in boxes if b["id"] not in GHOST_IDS]
    for b in boxes:
        if b["id"] in GHOST_IDS:
            changes.append(dict(change="drop_ghost", ids=[b["id"]], rect=[round(v) for v in b["rect"]], reason="tie box over a dotted half note and bare staff lines: no arc ink on the print (staff 8, bar 1); the detector refused it (`ink_is_a_staff_line`), no page-ink run, no head pair",
                                evidence="crop look 2.281 (strip s7_8) + 2.274 r3 census (no run, box_cov_kept 0); Sean's tile 10 on it is PENDING", assumed_for_sean=True))

    # ---- arcs start as one box each; boxes are joined at barlines, one-to-one, cheapest pair first
    arcs = [dict(ids=[b["id"]], rects=[b["rect"]], kinds=[b["cls"]], origins=[b["origin"]], joined=set()) for b in keep]

    def ends(a):
        return min(r[0] for r in a["rects"]), max(r[2] for r in a["rects"])

    def box(a):
        return [min(r[0] for r in a["rects"]), min(r[1] for r in a["rects"]), max(r[2] for r in a["rects"]), max(r[3] for r in a["rects"])]

    def collapse_dups():
        changed = True
        while changed:
            changed = False
            for i in range(len(arcs)):
                for j in range(i + 1, len(arcs)):
                    A, B = box(arcs[i]), box(arcs[j])
                    if abs(A[0] - B[0]) <= 40 and abs(A[2] - B[2]) <= 40 and yov(A, B) >= 0 and (A[2] - A[0]) < 20 * SP:
                        a, b = arcs[i], arcs[j]
                        changes.append(dict(change="dedupe_label", ids=a["ids"] + b["ids"], reason="two hand labels over one mark (both x extents within 40 px, y bands overlap): one arc counted once",
                                            kinds=sorted(set(a["kinds"] + b["kinds"])), evidence="2.274 r3 audit (P54/55/56, P91/92, P106/107) + crop look 2.281", assumed_for_sean=True))
                        a["ids"] += b["ids"]
                        a["rects"] += b["rects"]
                        a["kinds"] += b["kinds"]
                        a["origins"] += b["origins"]
                        del arcs[j]
                        changed = True
                        break
                if changed:
                    break

    collapse_dups()
    # join halves edge by edge: left candidates end near the edge, right candidates start near it
    for e in EDGES[:-1]:
        while True:
            best = None
            for i, a in enumerate(arcs):
                x0a, x1a = ends(a)
                lastbox = max(a["rects"], key=lambda r: r[2])
                if abs(lastbox[2] - e) > 40 or x1a - x0a < 40 or e in a["joined"]:
                    continue
                for j, b in enumerate(arcs):
                    if i == j:
                        continue
                    x0b, x1b = ends(b)
                    firstbox = min(b["rects"], key=lambda r: r[0])
                    if abs(firstbox[0] - e) > 40 or e in b["joined"]:
                        continue
                    ov = yov(lastbox, firstbox)
                    dy = abs(yc(lastbox) - yc(firstbox))
                    if ov < -10 or dy > 90:
                        continue
                    cost = dy + abs(x0b - x1a)
                    if best is None or cost < best[0]:
                        best = (cost, i, j)
            if best is None:
                break
            _, i, j = best
            a, b = arcs[i], arcs[j]
            changes.append(dict(change="join_halves", ids=a["ids"] + b["ids"], edge=e, kinds=sorted(set(a["kinds"] + b["kinds"])),
                                reason="two boxes meet at the barline x=%d on one y line: halves of ONE arc the page reads whole (Sean, 2.274 r3 tiles 2/5/6: 'those two boxes belong as one long box')" % e,
                                evidence="geometry (facing ends within 1.5 sp of the barline, y bands overlap, cheapest one-to-one pair) + crop look 2.281",
                                assumed_for_sean=len(set(a["kinds"] + b["kinds"])) > 1,
                                kind_conflict=len(set(a["kinds"] + b["kinds"])) > 1))
            a["ids"] += b["ids"]
            a["rects"] += b["rects"]
            a["kinds"] += b["kinds"]
            a["origins"] += b["origins"]
            a["joined"] |= b["joined"] | {e}
            del arcs[j]
    collapse_dups()

    # ---- the print-read corrections the rules cannot make
    def arc_of(hid):
        for a in arcs:
            if hid in a["ids"]:
                return a
    for ids, kind, why in MANUAL_MERGE:
        a, b = arc_of(ids[0]), arc_of(ids[1])
        if a is not b:
            changes.append(dict(change=kind, ids=a["ids"] + b["ids"], reason=why, evidence="crop look 2.281 (strips s4_6 / s9_10)", assumed_for_sean=True, kind_conflict=False))
            a["ids"] += b["ids"]
            a["rects"] += b["rects"]
            a["kinds"] += b["kinds"]
            a["origins"] += b["origins"]
            a["joined"] |= b["joined"]
            arcs.remove(b)
    for a in arcs:
        a["ext"] = {}
    for hid, side, xnew, why in MANUAL_EXTEND:
        a = arc_of(hid)
        a["ext"][side] = xnew
        changes.append(dict(change="extend_unboxed_half", ids=a["ids"], side=side, x=xnew, reason=why,
                            evidence="page-ink run (2.274 r3 census) over the same arc + crop look 2.281", assumed_for_sean=True))

    # ---- the page-ink run that witnesses each arc (used ONLY to find where an unboxed half ends; the claim is then looked at on a crop)
    B = json.load(open(BUCKETS))

    def runs_for(bx):
        got = []
        for r in B:
            if r["x0"] >= bx[0] - 6 and r["x1"] <= bx[2] + 6 and r["y0"] >= bx[1] - 6 and r["y1"] <= bx[3] + 6:
                for x in r["runs"]:
                    if x["cov"] >= 0.8:
                        got.append((x["ordinal"], round(x["run_x0"]), round(x["run_x1"])))
        return sorted(set(got))

    out = []
    for k, a in enumerate(arcs):
        bx = box(a)
        x0, x1 = bx[0], bx[2]
        kinds = a["kinds"]
        kind_counts = {c: sum(1 for q in kinds if q == c) for c in set(kinds)}
        longest = max(range(len(a["rects"])), key=lambda q: a["rects"][q][2] - a["rects"][q][0])
        kind = kinds[longest]
        hx0, hx1 = x0, x1
        x0 = a["ext"].get("L", x0)
        x1 = a["ext"].get("R", x1)
        ent = dict(id="K%03d" % k, ids=a["ids"], hand_x0=round(hx0), hand_x1=round(hx1), extended=sorted(a["ext"]), x0=round(x0), x1=round(x1), y0=round(bx[1]), y1=round(bx[3]), width_sp=round((x1 - x0) / SP, 1), kind=kind,
                   kind_conflict=len(kind_counts) > 1, kinds=kinds, nboxes=len(a["ids"]), origins=sorted(set(a["origins"])))
        first = min(a["rects"], key=lambda r: r[0])
        last = max(a["rects"], key=lambda r: r[2])
        eL = edge_of(first[0], 40)
        eR = edge_of(last[2], 40)
        ent["open_L"] = bool(eL is not None and eL not in a["joined"] and "L" not in a["ext"])      # starts at a barline, nothing joined, nothing known beyond it
        ent["open_R"] = bool(eR is not None and eR not in a["joined"] and "R" not in a["ext"])
        ent["cross_system"] = bool(kind == "tie" and x1 >= LAST_EDGE - 20)
        ent["runs"] = runs_for(bx)
        out.append(ent)
    return dict(boxes=boxes, arcs=out, changes=changes)


if __name__ == "__main__":
    r = build()
    print(len(r["boxes"]), "hand boxes ->", len(r["arcs"]), "arcs;", len(r["changes"]), "changes")
    import collections
    print(collections.Counter(c["change"] for c in r["changes"]))
    for a in r["arcs"]:
        if a["open_L"] or a["open_R"] or a["cross_system"]:
            print(a["id"], a["kind"], a["x0"], a["x1"], a["y0"], a["y1"], a["width_sp"], "nb", a["nboxes"], "L" if a["open_L"] else "-", "R" if a["open_R"] else "-", "XS" if a["cross_system"] else "", a["runs"])
    ARCS = r["arcs"]
    for a in ARCS:
        a["scorable"] = not a["cross_system"]
        a["pending_sean"] = []
        if a["kind_conflict"]:
            a["pending_sean"].append("kind: Sean's own boxes name both a tie and a slur over this one mark (page-facts: same pitch = tie, else slur; ask him or read the two notes)")
        if a["cross_system"]:
            a["pending_sean"].append("cross-system tie (key tile 7 is PENDING): its far end is on the next system, not scorable on this page")
    doc = dict(
        lane="2.281 step 1", page="Brahms p0 (imslp317803 pdf page 0)", hand_labels="data/hand-truth/pages/imslp317803/0.json (never edited)",
        built_by="benchmarks/omr-arc-binding-2026-10/key_brahms_p0_build.py", unit="page px at 600 dpi, sp = 32",
        counts=dict(hand_boxes=len(r["boxes"]), arcs=len(ARCS), scorable=sum(1 for a in ARCS if a["scorable"]), cross_system=sum(1 for a in ARCS if a["cross_system"]),
                    kind_conflict=sum(1 for a in ARCS if a["kind_conflict"]), ghosts_dropped=sum(1 for c in r["changes"] if c["change"] == "drop_ghost")),
        pending_sean_tiles=dict(tiles_7_to_12="pending: 07 cross-system, 08 chain, 09 nested/merged run, 10 ghost, 11 half box, 12 bound-but-unwritten; the key does not treat them as answered",
                                answered_truth="tiles 2, 5, 6 (a barline-cut arc is one arc); tile 4 (the old labelling is far off); tiles 1, 3 (a tie between two eighths; a basic slur)"),
        arcs=ARCS, changes=r["changes"])
    OUT.write_text(json.dumps(doc, indent=1))
    print("wrote", OUT, doc["counts"])
