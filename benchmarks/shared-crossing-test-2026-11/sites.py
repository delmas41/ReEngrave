"""2.294 step 1: CROSSING SITES on the page ink canvas (2.293 `LedgerInk`) and what single ownership does there.

SITE (definition). Per pair of fine kinds (a, b), a != b, neither staff_line: the CONTACT pixels X_ab = (ink of a within 1 px of ink of b) | (ink of b within
1 px of ink of a) | (ink standing in both kinds); a site = one 8-connected cluster of X_ab (merged within 2 px) of at least MIN_CONTACT px. Marks = the kinds'
ink on the page ledger's one-owner answer (`fam_eff`, the union over views). JOINS (a beam on its stem, a stem on its head, a flag on its stem, a ledger line
beside a head) and HEADER STRUCTURE (clef/key/meter/bracket/word/barline among themselves) are counted but excluded from the test.
CLASSES at a site (neighbourhood = site bbox + MARGIN px): b refused (a verdict that refuses a real-looking box: REFUSE_REASONS, box overlaps the site) /
c weak (WEAK-state ink in the neighbourhood) / d unclaimed (NO OWNER ink of a mark-like class in the neighbourhood) / a nothing lost; e (a hole) is not
auto-detectable: only crops say.
usage: python3 sites.py SCRATCHDIR  (reads off/PLATE.pN.npz and PLATE.off.json)"""
import json, sys, pathlib, collections, re
import numpy as np, cv2
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import claim_readout as CR

MIN_CONTACT = 3
MARGIN = 6
NEAR = np.ones((3, 3), np.uint8)
MERGE = np.ones((5, 5), np.uint8)
HEADER = {"clef", "key", "meter", "bracket", "word", "barline"}
JOINS = {frozenset(p) for p in [("beam", "stem"), ("beam", "flag"), ("flag", "stem"), ("notehead", "stem"), ("ledger_line", "notehead"), ("flag", "notehead"),
                                ("beam", "notehead")]}
REFUSE_REASONS = ("claimed_by:barline", "claimed_by:page_claim", "claimed_by:whole_rest", "claimed_by:earlier_mark", "on_a_dynamic_letter", "on_a_rest",
                  "rest_has_a_stem", "rest_stroke_into_a_head", "rest_on_a_dynamic_letter", "is_an_arc_tail", "stem_end_ink_claimed", "tremolo_slash_crosses_stem",
                  "touches_a_head", "stroke_into_a_head", "on_a_read_meter", "claimed_by_another_class")
NONE_SKIP = ("staff_line_residue", "specks")


def in_scope(a, b):
    p = frozenset((a, b))
    if p in JOINS:
        return "join"
    if a in HEADER and b in HEADER:
        return "header"
    return "test"


def contact(ma, mb):
    return (ma & cv2.dilate(mb.astype(np.uint8), NEAR).astype(bool)) | (mb & cv2.dilate(ma.astype(np.uint8), NEAR).astype(bool))


def find_sites(masks, min_contact=MIN_CONTACT):
    """PURE. masks {kind: bool array} -> [{pair, scope, bbox, contact_px}] for every pair. (The control builds masks by hand.)"""
    out = []
    kinds = [k for k in masks if masks[k].any()]
    for i, a in enumerate(kinds):
        for b in kinds[i + 1:]:
            X = contact(masks[a], masks[b])
            if X.sum() < min_contact:
                continue
            n, lab, st, _ = cv2.connectedComponentsWithStats(cv2.dilate(X.astype(np.uint8), MERGE), connectivity=8)
            for j in range(1, n):
                x, y, w, h = (int(v) for v in st[j, :4])
                px = int((X[y:y + h, x:x + w] & (lab[y:y + h, x:x + w] == j)).sum())
                if px >= min_contact:
                    out.append(dict(pair=(a, b), scope=in_scope(a, b), bbox=(x, y, x + w, y + h), contact_px=px))
    return out


def control():
    """A stem crossing an arc is ONE site; the same two 5 px apart are none; a lone kind none."""
    a = np.zeros((60, 60), bool); b = np.zeros((60, 60), bool)
    a[10:50, 30] = True; b[30, 10:50] = True
    s1 = find_sites({"stem": a, "arc": b})
    b2 = np.zeros((60, 60), bool); b2[30, 36:56] = True
    s2 = find_sites({"stem": a, "arc": b2})
    s3 = find_sites({"stem": a})
    assert len(s1) == 1 and len(s2) == 0 and len(s3) == 0, (s1, s2, s3)
    return "control ok: crossing=1 site, 5 px apart=0, one kind=0"


def refusals(rec):
    boxes = {o["subject"]: o["detail"].get("bbox_page_px") for o in rec["observations"] if o["quantity"] == "glyph_box"}
    out = []
    for v in rec["verdicts"] + rec["abstentions"]:
        r = str(v.get("reason"))
        refused = v.get("value") is True or v.get("outcome") == "abstained" or ("outcome" not in v)
        if r in REFUSE_REASONS and refused and v["subject"] in boxes and boxes[v["subject"]]:
            m = re.match(r"glyph/(\d+)/", v["subject"])
            out.append(dict(page=int(m.group(1)), subject=v["subject"], q=v["quantity"], reason=r, box=boxes[v["subject"]]))
    return out


def classify(page, sites, z, refs):
    ink, st, nc = z["ink"], z["state"], z["none_class"]
    skip = [CR.NONE_CLASSES.index(n) + 1 for n in NONE_SKIP]
    for s in sites:
        x0, y0, x1, y1 = s["bbox"]
        X0, Y0, X1, Y1 = max(0, x0 - MARGIN), max(0, y0 - MARGIN), x1 + MARGIN, y1 + MARGIN
        s["refused"] = [r["reason"] + ":" + r["q"].split("_is_")[0] for r in refs
                        if r["box"][0] <= X1 and r["box"][2] >= X0 and r["box"][1] <= Y1 and r["box"][3] >= Y0]
        sub = (slice(Y0, Y1), slice(X0, X1))
        weak = int(((st[sub] == CR.ST_WEAK) & ink[sub]).sum())
        none = (st[sub] == CR.ST_NONE) & ink[sub] & ~np.isin(nc[sub], skip)
        s["weak_px"], s["none_px"] = weak, int(none.sum())
        s["class"] = "b" if s["refused"] else ("c" if weak >= 8 else ("d" if s["none_px"] >= 12 else "a"))
        s["page"] = page
    return sites


def main():
    d = pathlib.Path(sys.argv[1])
    print(control())
    allsites = []
    summ = {}
    for plate, pages in (("brahms", (0, 14)), ("litolff", (1, 2))):
        rec = json.load(open(d / ("%s.off.json" % plate)))
        refs = refusals(rec)
        for pg in pages:
            z = dict(np.load(d / "off" / ("%s.p%d.npz" % (plate, pg))))
            ink, fam = z["ink"], z["fam"]
            masks = {k: ((fam & CR.FINE_BIT[k]) != 0) & ink for k in CR.FINE_KINDS if k != "staff_line"}
            sites = find_sites(masks)
            sites = classify(pg, sites, z, [r for r in refs if r["page"] == pg])
            for s in sites:
                s["plate"] = plate
            Xall = np.zeros(ink.shape, bool)
            for s in sites:
                if s["scope"] == "test":
                    x0, y0, x1, y1 = s["bbox"]
                    a, b = s["pair"]
                    sl = (slice(y0, y1), slice(x0, x1))
                    Xall[sl] |= contact(masks[a][sl], masks[b][sl])
            near = cv2.dilate(Xall.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool) & ink
            nonstaff = int((ink & (z["state"] != CR.ST_STAFF)).sum())
            summ[(plate, pg)] = dict(ink=int(ink.sum()), nonstaff=nonstaff, contact_px=int(Xall.sum()), near_px=int(near.sum()))
            allsites += sites
    for plate in ("brahms", "litolff"):
        T = collections.defaultdict(collections.Counter)
        P = collections.defaultdict(collections.Counter)
        for s in allsites:
            if s["plate"] != plate:
                continue
            k = "%s x %s [%s]" % (s["pair"] + (s["scope"],))
            T[k][s["class"]] += 1
            T[k]["n"] += 1
            P[k]["contact_px"] += s["contact_px"]
        print("\n== %s: sites by pair (n; classes a nothing lost / b refused / c weak / d unclaimed; contact px)" % plate)
        for k in sorted(T, key=lambda k: (not k.endswith("[test]"), -T[k]["n"])):
            c = T[k]
            print("  %-40s n=%-4d a%-4d b%-3d c%-3d d%-3d  contact_px=%d" % (k, c["n"], c["a"], c["b"], c["c"], c["d"], P[k]["contact_px"]))
        for (pl, pg), m in summ.items():
            if pl == plate:
                print("  page %d: ink %d, non-staff %d, contact px (test scope) %d = %.2f%% of ink; ink within 3 px of a contact %d = %.1f%% of ink, %.1f%% of non-staff"
                      % (pg, m["ink"], m["nonstaff"], m["contact_px"], 100.0 * m["contact_px"] / m["ink"], m["near_px"], 100.0 * m["near_px"] / m["ink"],
                         100.0 * m["near_px"] / m["nonstaff"]))
    t = [s for s in allsites if s["scope"] == "test"]
    print("\nTEST-scope sites total %d; classes %s; excluded joins %d, header %d" % (
        len(t), dict(collections.Counter(s["class"] for s in t)),
        sum(s["scope"] == "join" for s in allsites), sum(s["scope"] == "header" for s in allsites)))
    json.dump(allsites, open(d / "sites.json", "w"), default=str)


main()
