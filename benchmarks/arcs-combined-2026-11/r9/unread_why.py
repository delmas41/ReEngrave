"""2.305 r9 -- for each arc of Sean's the file leaves UNREAD (tally.json), the page-ink runs whose ink lies in his arc's box and what the page pass did
with each (status, reason, each end's head or reason). Reads only.

    python3 unread_why.py OUTPREFIX     (needs OUTPREFIX.record.json, .tally.json)
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record  # noqa: E402


def main():
    pre = sys.argv[1]
    rec = load_record(pre + ".record.json")["record"]
    rows = json.load(open(pre + ".tally.json"))
    st = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "page_arc_binding" and v["subject"].startswith("page/0"):
            for x in (v.get("detail") or {}).get("runs") or ():
                st.setdefault(x["row"], []).append(x)
    runs = [o for o in rec["observations"] if o["quantity"] == "page_arc" and o.get("value") == "run" and o["subject"].startswith("page/0")
            or (o["quantity"] == "page_arc" and o.get("value") == "run" and "/0/" in o["subject"][:12])]
    for r in rows:
        if r["verdict"] != "unread":
            continue
        x0, y0, x1, y1 = r["rect"]
        print("HIS %s %s %s" % (r["id"], r["kind"], [round(v) for v in r["rect"]]))
        for o in runs:
            pts = (o.get("detail") or {}).get("points") or []
            inside = [p for p in pts if x0 - 20 <= p[0] <= x1 + 20 and y0 - 20 <= p[1] <= y1 + 20]
            if len(inside) < max(3, 0.3 * len(pts)):
                continue
            e = (o.get("detail") or {}).get("ends")
            for x in st.get(o["id"], [{"status": "no binding entry"}]):
                L, R = x.get("left") or {}, x.get("right") or {}
                print("    run %s staff %s ends %s..%s  %s %s  L=%s R=%s home=%s" % (
                    o["id"], (o.get("detail") or {}).get("staff"), [round(v) for v in e[0][:2]], [round(v) for v in e[1][:2]], x["status"], x.get("why"),
                    L.get("head") or L.get("unbound") or ("edge" if L.get("edge") else None), R.get("head") or R.get("unbound") or ("edge" if R.get("edge") else None),
                    x.get("home")))


if __name__ == "__main__":
    main()
