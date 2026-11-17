"""2.305 r10 -- for each r9 tile (key out/print/2.305-r9-key.json): the page-ink runs lying in the tile's ink boxes, or naming its two notes, and what
the page pass did with each (status, reason, each end), from a replayed record. Reads only.

    python3 why_tiles.py KEY.json PLATE AFTER_PREFIX [tile ...]
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record  # noqa: E402


def end(e):
    e = e or {}
    if e.get("head"):
        return "%s(%s sp)" % (e["head"].split("/", 3)[3], e.get("distance_spaces"))
    if e.get("edge"):
        return "EDGE"
    return "%s%s" % (e.get("unbound"), [c.split("/", 3)[3] if isinstance(c, str) else c for c in (e.get("candidates") or [])][:3])


def main():
    key = json.load(open(sys.argv[1]))["tiles"]
    plate, pre = sys.argv[2], sys.argv[3]
    want = {int(t) for t in sys.argv[4:]}
    rec = load_record(pre + ".record.json")["record"]
    st = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "page_arc_binding":
            for x in (v.get("detail") or {}).get("runs") or ():
                st.setdefault(x["row"], []).append(x)
    runs = [o for o in rec["observations"] if o["quantity"] == "page_arc" and o.get("value") == "run"]
    strokes = [o for o in rec["observations"] if o["quantity"] == "page_stroke"]
    for t in key:
        if t["plate"] != plate or (want and t["tile"] not in want):
            continue
        print("TILE %d %s %s -> %s  %s  boxes %s" % (t["tile"], t["file_said"], t["a"], t["b"], t["src"], [[round(v) for v in b] for b in t["ink_boxes"]]))
        for o in runs:
            pts = (o.get("detail") or {}).get("points") or []
            hit = any(b[0] - 10 <= p[0] <= b[2] + 10 and b[1] - 10 <= p[1] <= b[3] + 10 for b in t["ink_boxes"] for p in pts)
            for x in st.get(o["id"], [{"status": "no binding entry"}]):
                names = {x.get("start"), x.get("stop"), (x.get("left") or {}).get("head"), (x.get("right") or {}).get("head")}
                if hit or t["a"] in names or t["b"] in names:
                    e = (o.get("detail") or {}).get("ends") or [[0, 0], [0, 0]]
                    print("   run %s piece %s staff %s x %d..%d y %d..%d  %s %s kind=%s  L=%s R=%s home=%s w=%s" % (
                        o["id"], x.get("piece"), (o.get("detail") or {}).get("staff"), e[0][0], e[1][0], e[0][1], e[1][1], x["status"], x.get("why"),
                        x.get("kind"), end(x.get("left")), end(x.get("right")), x.get("home"), len(x.get("witnesses") or [])))
        n = 0
        for o in strokes:
            b = (o.get("detail") or {}).get("bbox_page_px") or o.get("value")
            if isinstance(b, list) and len(b) == 4 and all(isinstance(v, (int, float)) for v in b):
                for ib in t["ink_boxes"]:
                    if b[0] < ib[2] and b[2] > ib[0] and b[1] < ib[3] and b[3] > ib[1]:
                        n += 1
        print("   page strokes touching the ink boxes:", n)


if __name__ == "__main__":
    main()
