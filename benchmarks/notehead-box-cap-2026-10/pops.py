"""ROADMAP 2.222 measure: populations for an upper size limit on a notehead box. STAGED, read-only.

Input: the census extract pickle written by `python3 benchmarks/page-claim-order-2026-10/census.py extract` (branch
lane-2.221-m0; reads the 2.202f ON-arm saved gathers of the frozen sample, nothing is re-run). Set CENSUS_PKL to override.
Every box size is in the OWN STAFF's spaces (staff_spacing of the staff the glyph key names), width and height separately.

Populations (each named by where it came from):
  A  head box with exactly ONE written note in the exported MusicXML (host rg == glyph key, matched by page + box)
  B  head box with TWO OR MORE written notes in the exported file (one box, several written heads)
  C_clef / C_dyn  detector clef / dynamic-letter boxes whose centre is on the staff (top line - 1 sp .. bottom line + 1 sp)
  D  head-class boxes (any, not only written) overlapping a clef / dynamic box by >= 25% of the head's area
"""
import collections, os, pathlib, pickle
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
PKL = pathlib.Path(os.environ.get("CENSUS_PKL", "/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-agent-manager-workflow-356c39/7e1ea73e-2fd3-4d6c-a450-36868f7e14c0/scratchpad/census-extract.pkl"))
CLEFS = ("clefG", "clefF", "clefCAlto", "clefCTenor")
DYNS = ("dynamicF", "dynamicP", "dynamicS", "dynamicM", "dynamicZ", "dynamicR")


def inter_area(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def load():
    data = pickle.loads(PKL.read_bytes())
    out = {}
    for plate, D in data.items():
        rows = D["rows"]
        sp = {r["subject"]: float(r["value"]) for r in rows["staff_spacing"]}
        lines = {r["subject"]: r["value"] for r in rows["staff_lines"]}
        ext = {r["subject"]: r["value"] for r in rows["staff_extent"]}
        boxes = {}
        for r in rows["glyph_box"]:
            b = r["detail"].get("bbox_page_px")
            if not b:
                continue
            p = r["subject"].split("/")            # glyph/pg/sy/st/cell/i
            sk = "staff/%s/%s/%s" % (p[1], p[2], p[3])
            if sk not in sp:
                continue
            s = sp[sk]
            boxes[r["subject"]] = dict(key=r["subject"], page=int(p[1]), cls=r["value"][0], box=[float(x) for x in b], staff=sk, sp=s,
                                       w=(b[2] - b[0]) / s, h=(b[3] - b[1]) / s, cx=(b[0] + b[2]) / 2, cy=(b[1] + b[3]) / 2)
        hostbox = collections.defaultdict(list)
        for h in D["hosts"]:
            if h["kind"] == "note":
                hostbox[h["rg"]].append(h)
        heads = {k: v for k, v in boxes.items() if v["cls"].startswith("notehead")}
        A, B, unmatched = {}, {}, 0
        for rg, hs in hostbox.items():
            g = heads.get(rg)
            ok = g is not None and all(g["page"] == h["page"] and inter_area(g["box"], h["box"]) > 0.8 * (g["box"][2] - g["box"][0]) * (g["box"][3] - g["box"][1]) for h in hs)
            if not ok:
                unmatched += len(hs)
                continue
            (A if len(hs) == 1 else B)[rg] = g
        nv = {v["subject"]: v for v in D["verdicts"]["notehead_is_not_a_notehead"]}

        def onstaff(g):
            ys = lines[g["staff"]]
            e = ext[g["staff"]]
            return ys[0] - g["sp"] <= g["cy"] <= ys[-1] + g["sp"] and e[0] <= g["cx"] <= e[1]
        clefs = [g for g in boxes.values() if g["cls"] in CLEFS and onstaff(g)]
        dyns = [g for g in boxes.values() if g["cls"] in DYNS and onstaff(g)]
        by_page = collections.defaultdict(list)
        for g in clefs + dyns:
            by_page[g["page"]].append(g)
        D_ = {}
        for k, g in heads.items():
            ha = (g["box"][2] - g["box"][0]) * (g["box"][3] - g["box"][1])
            for o in by_page[g["page"]]:
                if inter_area(g["box"], o["box"]) >= 0.25 * ha:
                    D_[k] = o["cls"]
                    break
        out[plate] = dict(boxes=boxes, heads=heads, A=A, B=B, clefs=clefs, dyns=dyns, D=D_, unmatched=unmatched,
                          live={k for k in heads if nv.get(k, {}).get("value") is False}, hosts=D["hosts"])
    return out


if __name__ == "__main__":
    P = load()
    q = lambda xs, p: float(np.percentile(xs, p)) if len(xs) else float("nan")
    for plate, X in P.items():
        print("==", plate, "heads", len(X["heads"]), "live", len(X["live"]), "A", len(X["A"]), "B", len(X["B"]), "unmatched notes", X["unmatched"],
              "clef_onstaff", len(X["clefs"]), "dyn_onstaff", len(X["dyns"]), "D", len(X["D"]))
        for name, grp in (("A", list(X["A"].values())), ("B", list(X["B"].values())), ("C_clef", X["clefs"]), ("C_dyn", X["dyns"]),
                          ("D_heads", [X["heads"][k] for k in X["D"]])):
            if not grp:
                continue
            for dim in ("w", "h"):
                v = [g[dim] for g in grp]
                print("  %-8s %s n=%d min %.2f p1 %.2f p5 %.2f p50 %.2f p95 %.2f p99 %.2f p99.5 %.2f max %.2f" % (name, dim, len(v), min(v), q(v, 1), q(v, 5), q(v, 50), q(v, 95), q(v, 99), q(v, 99.5), max(v)))
