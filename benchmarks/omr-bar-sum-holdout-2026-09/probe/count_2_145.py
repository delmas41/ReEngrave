"""ROADMAP 2.145 -- count notehead boxes whose INK is rest-shaped with no rest box beside them.
usage: count_2_145.py ROWS.json [OUT.json]      (ROWS from cache_2_145.py; STAGED GATHER rows + ADJUDICATE verdicts)

The witness is the 2.99 decision (`adjudicate_unboxed_ink_is_a_rest`) run over the cluster of ink a notehead box
covers, coverage zeroed (as controls_2_99.py), i.e. a reading of the INK. The bar is never consulted.
Two readings are taken: the shipped windows ("strict") and the same windows with the staff step set to the
middle line ("step-free": a rest in a second voice sits off the middle; 2.99 abstains on it by design).
"""
import collections
import json
import sys

sys.path.insert(0, ".")
from tools.omr.staged import adjudicate  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Log, Q, READERS  # noqa: E402

adjudicate._ensure_decisions()
KEYS = ("width_spaces", "height_spaces", "staff_step", "n_pieces", "fill", "max_column_share", "mass_y",
        "column_profile", "covered_by", "right_head", "first_cell", "left_of_header", "header_known",
        "touches_cell_edge")


def read_ink(row, step=None):
    """What the 2.99 decision says of this cluster with nothing covering it: 'eighth'|'quarter'|'abstain:r'|'not:r'."""
    log = Log()
    g = R.glyph(0, 0, 0, 1, 350000)
    det = {x: row.get(x) for x in KEYS}
    if step is not None:
        det["staff_step"] = step
    det.update(coverage=0.0, bbox_canonical=[0, 0, 1, 1], bbox_page_px=[0.0, 0.0, 1.0, 1.0])
    log.observe(g, Q.UNBOXED_REST_SHAPE, row["height_spaces"], reader=READERS.CV_UNBOXED_REST_SHAPE,
                frame="cell:1", **det)
    log.freeze()
    adjudicate.run(log, order=(Q.UNBOXED_INK_IS_A_REST,))
    v = log.verdict(Q.UNBOXED_INK_IS_A_REST, g)
    if v.outcome.value == "decided":
        return str(v.value) if v.value else "not:" + (v.reason or "")
    return "abstain:" + (v.reason or "")


def cover(a, b):
    iw = min(a[2], b[2]) - max(a[0], b[0])
    ih = min(a[3], b[3]) - max(a[1], b[1])
    s = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return 0.0 if iw <= 0 or ih <= 0 or s <= 0 else iw * ih / s


def main(path, out=None):
    d = json.load(open(path))
    B, V = d["boxes"], d["verdicts"]
    bycell = collections.defaultdict(list)
    for s, (c, sc, bb) in B.items():
        if bb:
            bycell["/".join(s.split("/")[:5])].append(s)
    tab = collections.Counter()
    hits = []
    ctrl = {"stemmed_reads_rest": [], "stemless_not_rest_shaped": []}
    for row in d["shape"]:
        by = [b for b in (row.get("covered_by") or []) if b != "ledgerLine"]
        if not by or not all(b.startswith("notehead") for b in by) or (row.get("coverage") or 0) < 0.3:
            continue
        cell = "/".join(row["subject"].split("/")[:5])
        heads = [s for s in bycell[cell] if B[s][0].startswith("notehead") and cover(B[s][2], row["bbox_page_px"]) >= 0.5]
        if not heads:
            continue
        h = max(heads, key=lambda s: cover(B[s][2], row["bbox_page_px"]))
        v = V.get(h, {})
        nn = v.get("notehead_is_not_a_notehead")
        refused = bool(nn and nn[0] == "decided" and nn[1] is True)
        hs = v.get("head_stem")
        stemless = bool(hs and hs[0] == "abstained" and hs[2] == "no_stem")
        dur = v.get("duration")
        strict, free = read_ink(row), read_ink(row, step=4.0)
        key = (B[h][0], "refused" if refused else "standing", "stemless" if stemless else "stemmed/other",
               strict.split(":")[0] if strict in ("eighth", "quarter") else "-",
               free.split(":")[0] if free in ("eighth", "quarter") else "-")
        tab[key] += 1
        rec_ = {"head": h, "class": B[h][0], "page_bbox": B[h][2], "score": B[h][1], "strict": strict, "free": free,
                "step": row["staff_step"], "w": row["width_spaces"], "h": row["height_spaces"]}
        if not refused and not stemless and strict in ("eighth", "quarter"):
            ctrl["stemmed_reads_rest"].append(rec_)
        if not refused and stemless and free not in ("eighth", "quarter"):
            ctrl["stemless_not_rest_shaped"].append(rec_)
        if free in ("eighth", "quarter") and not refused and stemless:
            hits.append({"head": h, "cluster": row["subject"], "class": B[h][0], "strict": strict, "free": free,
                         "step": row["staff_step"], "w": row["width_spaces"], "h": row["height_spaces"],
                         "mass_y": row["mass_y"], "col": row["max_column_share"], "profile": row["column_profile"],
                         "coverage": row["coverage"], "dur": dur and dur[:2], "page_bbox": B[h][2],
                         "score": B[h][1]})
    print("covered-by-notehead clusters with a head box:", sum(tab.values()))
    for k, n in sorted(tab.items(), key=lambda x: -x[1])[:40]:
        print(f"{n:5d}", k)
    print("CANDIDATES (standing, stemless head box; ink read a rest step-free):", len(hits))
    print("  of which strict (shipped windows) reads a rest:", sum(1 for x in hits if x["strict"] in ("eighth", "quarter")))
    print("  with a DECIDED duration:", sum(1 for x in hits if x["dur"] and x["dur"][0] == "decided"))
    print("controls: stemmed heads whose ink reads a rest by shape alone:", len(ctrl["stemmed_reads_rest"]),
          "| stemless heads not rest-shaped:", len(ctrl["stemless_not_rest_shaped"]))
    if out:
        json.dump({"hits": hits, "controls": ctrl}, open(out, "w"), indent=1)


main(*sys.argv[1:])
