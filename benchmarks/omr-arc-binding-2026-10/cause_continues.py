"""2.281 step 2: WHY does `arc_claim.bind_end` refuse with `continues_in_another_curve`?  Measure every such refusal in a re-adjudicated record (flag OMR_PAGE_ARC_WRITE on).

    python3 cause_continues.py RECORD.json [--page N] [--key]       (--key: judge each refusal against the corrected Brahms p0 key; page 0 only)

For each run end the page-arc binder left unbound as `continues_in_another_curve`: the ink's end, the closest head the binder itself named, the OTHER run's facing end that tripped
the test (rule: another run's end stands nearer this end than the closest head does AND nearer than it stands to the head), and how far each stands from the head in spaces
(`d_end` this end to the head, `d_other_head` the other end to the head).  Two shapes are told apart without a new number:
    MEETING   the other end stands AT the head this end stops at (its own closest head is the same one): two arcs meet at a note, A ends on it, B starts on it;
    CONTINUES the other end stands AWAY from the head (nearer this end than to any head): this run is half of one arc.
With --key a refusal is judged by the key: two key arcs meeting at the place = MEETING is truth; ONE key arc spanning both = CONTINUES is truth (the refusal is right).
"""
import json
import pathlib
import sys
import collections

HERE = pathlib.Path(__file__).resolve().parent
KEY = json.load(open(HERE / "key-brahms-p0-corrected.json"))
ANCHOR_IN_SPACES = 0.8


def load(path, page):
    rec = json.load(open(path))
    obs = rec["observations"]
    boxes = {}
    for o in obs:
        b = (o.get("detail") or {}).get("bbox_page_px")
        if b and str(o["subject"]).startswith("glyph/%d/" % page):
            boxes.setdefault(o["subject"], [float(v) for v in b])
    rows = {o["id"]: o for o in obs if o["quantity"] == "page_arc" and o["value"] == "run" and str(o["subject"]) == "page/%d" % page}
    vs = [v for v in rec["verdicts"] if v["quantity"] == "page_arc_binding" and v["subject"] == "page/%d" % page]
    return boxes, rows, (vs[-1]["detail"]["runs"] if vs and vs[-1].get("detail") else [])


def head_c(b):
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, b[2] - b[0], b[3] - b[1]


def run_ends(row):
    d = row["detail"]
    e = d.get("core_ends") or d.get("ends")
    return [(float(e[0][0]), float(e[0][1])), (float(e[1][0]), float(e[1][1]))], float(d["space_page_px"]), list(d.get("staff") or [0, 0])


def key_verdict(ex, ey, ox, oy, side, sp):
    """the corrected key: two arcs meeting here, or one arc spanning this end and the other end?"""
    near = lambda k, y: k["y0"] - 4 * sp <= y <= k["y1"] + 4 * sp
    for k in KEY["arcs"]:
        if k["x0"] + 2.5 * sp < min(ex, ox) and k["x1"] - 2.5 * sp > max(ex, ox) and near(k, ey):
            return "one key arc spans both (%s)" % k["id"]
    A = [k for k in KEY["arcs"] if near(k, ey) and abs((k["x1"] if side == "right" else k["x0"]) - ex) <= 3 * sp]
    B = [k for k in KEY["arcs"] if near(k, oy) and abs((k["x0"] if side == "right" else k["x1"]) - ox) <= 3 * sp]
    if A and B and {k["id"] for k in A} != {k["id"] for k in B}:
        return "two key arcs meet (%s | %s)" % (",".join(k["id"] for k in A), ",".join(k["id"] for k in B))
    return "key silent"


def measure(path, page=0, use_key=False):
    boxes, rows, runs = load(path, page)
    peers = {}
    for e in runs:
        if e.get("row") in rows:
            peers.setdefault(e["row"], []).append(e)
    heads = {k: head_c(b) for k, b in boxes.items()}
    out = []
    for e in runs:
        unb = e.get("unbound") or {}
        for side, u in unb.items():
            if u.get("unbound") != "continues_in_another_curve":
                continue
            row = rows.get(e["row"])
            if row is None:
                continue
            ends, sp, staff = run_ends(row)
            ex, ey = ends[0] if side == "left" else ends[1]
            sgn = -1 if side == "left" else 1
            hk = (u.get("candidates") or [None])[0]
            if hk not in heads:
                continue
            hx, hy, hw, hh_ = heads[hk]
            d_end = (abs(hx - ex) + abs(hy - ey)) / sp
            # the other ends the binder compared: facing ends of the other runs of the same staff
            best = None
            offs = []
            for oid, orow in rows.items():
                if oid == e["row"]:
                    continue
                oends, osp, ostaff = run_ends(orow)
                if ostaff != staff:
                    continue
                ox, oy = oends[1] if side == "left" else oends[0]         # a left end's facing end is another run's RIGHT end
                if (ox - ex) * sgn <= -ANCHOR_IN_SPACES * sp:
                    continue
                d_o_end = abs(ox - ex) + abs(oy - ey)
                d_o_head = abs(ox - hx) + abs(oy - hy)
                if d_o_end < min(d_end * sp, d_o_head):
                    offs.append((ox, oy))
                    if best is None or d_o_end < best[0]:
                        best = (d_o_end, ox, oy, d_o_head, oid)
            if best is None:
                shape = dict(shape="no_offender_found")
                out.append(dict(run=e["ordinal"], side=side, head=hk, d_end=round(d_end, 2), **shape))
                continue
            d_o_end, ox, oy, d_o_head, oid = best
            # the other end's own closest head (over every head box of the page's glyph rows near it)
            near = sorted(heads.items(), key=lambda kv: abs(kv[1][0] - ox) + abs(kv[1][1] - oy))[:1]
            other_head = near[0][0] if near else None
            at_head = (other_head == hk) or (d_o_head / sp <= 1.5)
            shape = "MEETING" if at_head and d_end <= 1.5 else ("CONTINUES" if not at_head else "MEETING_far_end")
            at = lambda x, y, s_: -1.6 * sp < (hx - x) * s_ <= 1.6 * sp and abs(hy - y) <= 2.5 * sp
            released = at(ex, ey, sgn) and all(at(x, y, -sgn) for x, y in offs)
            rec = dict(released_by_rule=released, run=e["ordinal"], side=side, head=hk, d_end=round(d_end, 2), d_other_end=round(d_o_end / sp, 2), d_other_head=round(d_o_head / sp, 2),
                       other_head=other_head, same_head=other_head == hk, shape=shape, other_run=orows_ord(rows, oid), x=round(ex))
            if use_key:
                rec["key"] = key_verdict(ex, ey, ox, oy, side, sp)
            out.append(rec)
    return out


def orows_ord(rows, oid):
    return rows[oid]["detail"].get("ordinal")


if __name__ == "__main__":
    argv = sys.argv[1:]
    page = int(argv[argv.index("--page") + 1]) if "--page" in argv else 0
    res = measure(argv[0], page, "--key" in argv)
    print(len(res), "continues_in_another_curve refusals;", dict(collections.Counter(r["shape"] for r in res)))
    for r in res:
        print(r)
    if "--key" in argv:
        print(dict(collections.Counter((r["shape"], r.get("key", "").split(" (")[0]) for r in res)))
        print("released by the 2.281 rule vs the key:", dict(collections.Counter((r.get("released_by_rule"), r.get("key", "").split(" (")[0]) for r in res)))
