"""lane-staccato-unread: count the dots the reader leaves unread (`dot_role` abstained), by reason and by what the page
shows, and (given a second replay) what changed.  Input is the JSON of `staccato_unread_replay.py`.

    python3 staccato_unread_counts.py BEFORE.json [AFTER.json] [--label lito]

GEOMETRY, stated before any count, all in the PAGE frame, in staff spaces (sp) of the dot's own cell:
  STACCATO-LIKE   a real (not-refused) head, of ANY cell/owner, whose centre is within 0.5 sp of the dot's centre in x, with
                  the dot's centre OUTSIDE that head's y-extent and no farther than 2.0 sp from its nearest edge
                  (= `ownership.dot_stacked_under_a_note`, the reader's own stacked test).
  LENGTHENING-LIKE a real head whose right edge is left of the dot's left edge by <= 1.0 sp, with the dot's centre within 1.0 sp
                  of the head's centre in y (not staccato-like).
  NEITHER         everything else.
"""
import collections, json, sys

STAC_X, STAC_GAP, LEN_GAP, LEN_Y = 0.5, 2.0, 1.0, 1.0


def kind_of(d):
    pb, sp = d["pb"], d["space"]
    if not pb or not sp or not d["box"] or not d["box"][2]:
        return "no_page_box"
    k = (pb[2] - pb[0]) / d["box"][2]
    spp = sp * k
    if spp <= 0:
        return "no_page_box"
    cx, cy = (pb[0] + pb[2]) / 2, (pb[1] + pb[3]) / 2
    stac = leng = False
    for h in d["heads"]:
        if (h["np"] or {}).get("v") is True or not h["pb"]:
            continue
        b = h["pb"]
        if abs(cx - (b[0] + b[2]) / 2) <= STAC_X * spp and not (b[1] <= cy <= b[3]):
            gap = (b[1] - cy) if cy < b[1] else (cy - b[3])
            if gap <= STAC_GAP * spp:
                stac = True
        if 0 <= pb[0] - b[2] <= LEN_GAP * spp and abs(cy - (b[1] + b[3]) / 2) <= LEN_Y * spp:
            leng = True
    if stac:
        return "staccato_like"
    if leng:
        return "lengthening_like"
    return "neither"


def census(R):
    c = collections.Counter()
    unread = collections.Counter()
    for k, d in R["dots"].items():
        r = d["role"] or {}
        c["dots"] += 1
        if r.get("o") == "decided":
            c["decided_" + str(r.get("v"))] += 1
        else:
            c["unread"] += 1
            unread[(r.get("r"), kind_of(d))] += 1
    return c, unread


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    B = json.load(open(a[0]))
    cb, ub = census(B)
    print("BEFORE", dict(cb))
    for (why, kind), n in sorted(ub.items(), key=lambda t: -t[1]):
        print(f"   unread {n:5d}  reason={why}  page shows: {kind}")
    if len(a) > 1:
        A = json.load(open(a[1]))
        ca, ua = census(A)
        print("AFTER ", dict(ca))
        for (why, kind), n in sorted(ua.items(), key=lambda t: -t[1]):
            print(f"   unread {n:5d}  reason={why}  page shows: {kind}")
        ch = collections.Counter()
        for k, d in B["dots"].items():
            e = A["dots"].get(k)
            if e is None:
                ch["missing_after"] += 1
                continue
            rb, ra = d["role"] or {}, e["role"] or {}
            sb = rb.get("v") if rb.get("o") == "decided" else "UNREAD"
            sa = ra.get("v") if ra.get("o") == "decided" else "UNREAD"
            if sb != sa:
                ch[f"{sb} -> {sa}"] += 1
        print("CHANGED", dict(ch))


if __name__ == "__main__":
    main()
