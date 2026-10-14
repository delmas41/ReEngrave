"""ROADMAP 2.113 -- clutter count. READ-ONLY over an existing record + the
judged-tiles index (2.106). Writes one small JSON. No gather.

    nice -n 15 python3 benchmarks/omr-clutter-count-2026-10/clutter_count.py \
        --record REC --doc litolff --out OUT.json
"""
import argparse, json, math, pathlib, random, statistics, sys
from collections import defaultdict, Counter
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import judged as J

READ_DUR = {"head_and_marks", "hollow_head_bare_stem", "hooks_counted",
            "stem_value_follows", "chord_mate_shares_the_stem"}
REST_DUR = {"rest_class", "whole_rest_means_the_bar"}
PARTS = {"stem", "flag", "structural"}   # attached parts / non-symbols: never "clutter"
RADII = {"touch": 0.25, "near": 1.0}      # staff spaces, box-to-box gap


def load(record):
    boxes, cat = {}, {}
    for o in J.iter_array(record, "observations"):
        s = o.get("subject", "")
        if not s.startswith("glyph/"):
            continue
        q = o["quantity"]
        if q in ("glyph_box", "arc_box"):
            b = (o.get("detail") or {}).get("bbox_page_px")
            if isinstance(b, list) and len(b) == 4 and (s not in boxes or o["reader"] == "detector"):
                boxes[s] = [float(x) for x in b]
                cat[s] = "arc" if q == "arc_box" else (o["detail"].get("category") or "?")
    ver = defaultdict(list)
    for v in J.iter_verdicts(record):
        s = v.get("subject", "")
        if s in boxes:
            ver[(s, v["quantity"])].append({k: v.get(k) for k in (
                "id", "subject", "quantity", "outcome", "value", "decider", "reason",
                "margin", "supersedes", "candidates", "detail")})
    S = {}
    for key, vs in ver.items():
        sup = {x["supersedes"] for x in vs if x.get("supersedes")}
        live = [x for x in vs if x["id"] not in sup] or vs
        S[key] = live[-1]
    return boxes, cat, S


def is_read(s, kind, S):
    def d(q): 
        v = S.get((s, q)); return v if v and v["outcome"] == "decided" and not str(v["decider"]).startswith("infer") else None
    if kind == "notehead":
        v = d("duration"); return bool(v and v["reason"] in READ_DUR)
    if kind == "rest":
        v = d("duration"); return bool(v and v["reason"] in REST_DUR)
    if kind == "dynamic":
        v = d("dynamic"); return bool(v and v["reason"] == "spelled")
    if kind == "arc":
        return bool(d("arc_kind"))
    if kind == "accidental":
        return bool(d("accidental"))
    return False


def gap(a, b):
    dx = max(0, max(a[0], b[0]) - min(a[2], b[2])); dy = max(0, max(a[1], b[1]) - min(a[3], b[3]))
    return math.hypot(dx, dy)


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy; u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - i
    return i / u if u else 0


def neighbours(subs, boxes, cat, S, ss, byp):
    """{radius_name: {'read': n, 'any': n, 'kinds': Counter}} for the union of subs."""
    out = {r: {"read": 0, "any": 0, "kinds": Counter()} for r in RADII}
    page = subs[0].split("/")[1]
    subset = set(subs)
    for k in byp[page]:
        if k in subset: continue
        kb, kk = boxes[k], cat[k]
        if kk in PARTS: continue
        best = None
        for s in subs:
            if iou(boxes[s], kb) > 0.7: best = "dup"; break
            g = gap(boxes[s], kb) / ss
            best = g if best is None else min(best, g)
        if best == "dup": continue
        rd = is_read(k, kk, S)
        for r, lim in RADII.items():
            if best <= lim:
                out[r]["any"] += 1; out[r]["kinds"][kk + ("+READ" if rd else "")] += 1
                if rd: out[r]["read"] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True); ap.add_argument("--doc", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rec = pathlib.Path(a.record)
    idx = json.load(open(J.INDEX_PATH))
    boxes, cat, S = load(rec)
    byp = defaultdict(list)
    for k in boxes: byp[k.split("/")[1]].append(k)
    nh = [b[3]-b[1] for k, b in boxes.items() if cat[k] == "notehead"]
    ss = statistics.median(nh)   # a notehead is ~1 staff space tall
    rows, skipped = [], Counter()
    for r in idx["tiles"]:
        if r["followup"] or r.get("control") or r["subject_kind"] != "glyph": continue
        subs = r["subjects"] or [r["subject"]]
        if r["doc"] not in (a.doc, None): skipped["other_doc"] += 1; continue
        if any(s not in boxes for s in subs): skipped["subject_not_in_record"] += 1; continue
        if r["doc"] is None:
            if not r["page_box"]: skipped["no_doc_no_box"] += 1; continue
            if not all(J.box_matches(boxes[s], r["page_box"]) for s in subs):
                skipped["box_mismatch"] += 1; continue
            by = "page_box"
        else:
            by = "manifest" + ("+box" if r["page_box"] and all(J.box_matches(boxes[s], r["page_box"]) for s in subs) else "")
            if r["page_box"] and "+box" not in by: skipped["box_mismatch"] += 1; continue
        status, note, margin = J.score_row(r, S)
        nb = neighbours(subs, boxes, cat, S, ss, byp)
        rows.append({"item": r["item"], "tile": r["tile"], "subjects": subs, "answer": r["answer"],
                     "qkind": r["question_kind"], "akind": r["answer_kind"], "status": status,
                     "note": note, "doc_by": by, "kind": cat[subs[0]],
                     **{f"{rn}_read": nb[rn]["read"] for rn in RADII},
                     **{f"{rn}_any": nb[rn]["any"] for rn in RADII},
                     "near_kinds": dict(nb["near"]["kinds"]), "touch_kinds": dict(nb["touch"]["kinds"])})
    # population + sanity controls (seeded; same neighbour code as the tiles)
    rng = random.Random(113)
    heads = [k for k in boxes if cat[k] == "notehead"]
    pop = []
    for k in rng.sample(heads, min(600, len(heads))):
        nb = neighbours([k], boxes, cat, S, ss, byp)
        pop.append({"s": k, "read_head": is_read(k, "notehead", S),
                    **{f"{rn}_read": nb[rn]["read"] for rn in RADII}, **{f"{rn}_any": nb[rn]["any"] for rn in RADII},
                    "near_kinds": dict(nb["near"]["kinds"])})
    # sanity PRESENT: a notehead whose chord mate (same mark_group, size>=2) is READ -> must see it
    groups = defaultdict(list)
    for o in J.iter_array(rec, "observations"):
        if o["quantity"] == "mark_group" and (o.get("detail") or {}).get("family") == "notehead" and o["subject"] in boxes:
            groups[o["value"]].append(o["subject"])
    chord = []
    for g, ms in groups.items():
        if len(ms) >= 2 and len(chord) < 300:
            for m in ms[:1]:
                nb = neighbours([m], boxes, cat, S, ss, byp)
                mates_read = sum(is_read(x, "notehead", S) for x in ms if x != m)
                chord.append({"s": m, "mates": len(ms) - 1, "mates_read": mates_read, "near_read": nb["near"]["read"], "near_any": nb["near"]["any"]})
    json.dump({"population": pop, "chord_sanity": chord}, open(a.out.replace("rows-", "pop-"), "w"))
    json.dump({"record": str(rec), "doc": a.doc, "staff_space_px": ss, "skipped": dict(skipped),
               "n_glyph_boxes": len(boxes), "rows": rows}, open(a.out, "w"), indent=0)
    print(a.doc, "rows", len(rows), dict(Counter(x["status"] for x in rows)), "skipped", dict(skipped), "ss", round(ss, 1))

main()
