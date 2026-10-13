"""ROADMAP 2.101: list what each rule decided that BASE did not, per score.

    python3 cases.py OUT.json  DOC=BASE_REC:ARM_REC [DOC=...]

For each doc, FINAL verdict per (subject, quantity) = the last verdict in file
order (ids ascend). A "case" is a subject whose final answer in ARM was filed by
one of the rules under test and differs from BASE's. Nothing is re-decided here.
"""
import json
import sys
from collections import defaultdict

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402


def final(R):
    last = {}
    for v in R["verdicts"]:
        last[(v["subject"], v["quantity"])] = v
    return last


def box_of(R_idx, subject):
    """page box of a glyph from the detector's own row, else the unboxed-rest row"""
    for o in R_idx.get(subject, ()):
        if o["quantity"] in ("glyph_box", "unboxed_rest_shape", "narrow_box_shape"):
            b = (o.get("detail") or {}).get("bbox_page_px")
            if b:
                return b
    return None


def short(v):
    if v is None:
        return None
    return {"outcome": str(v["outcome"]), "value": v["value"], "decider": v["decider"],
            "reason": v["reason"]}


def main():
    out = {}
    for spec in sys.argv[2:]:
        doc, pair = spec.split("=")
        bp, ap = pair.split(":")
        base = load_record(bp)["record"]
        arm = load_record(ap)["record"]
        fb, fa = final(base), final(arm)
        idx = defaultdict(list)
        for o in arm["observations"]:
            idx[o["subject"]].append(o)
        cases = []
        for key, v in fa.items():
            subject, q = key
            d = str(v["decider"])
            reason = str(v["reason"])
            rule = None
            if q == "unboxed_ink_is_a_rest" and d == "adjudicate_unboxed_ink_is_a_rest":
                if str(v["outcome"]) == "decided" and reason in ("rest8th_shape", "restQuarter_shape"):
                    rule = "2.99_rest_decided"
                elif reason == "stem_stroke_not_a_rest" or reason.startswith("thin_stroke"):
                    rule = "2.99_refused_stroke"
                elif str(v["outcome"]) == "abstained" and reason == "shape_cannot_tell":
                    rule = "2.99_abstained_shape"
            elif q == "notehead_is_an_eighth_rest" and d == "adjudicate_narrow_box_is_an_eighth_rest":
                if str(v["outcome"]) == "decided":
                    rule = ("2.80b_decided_true" if v["value"] is True else "2.80b_decided_false")
            elif q == "duration":
                b = fb.get(key)
                if reason == "hollow_head_bare_stem" and str(v["outcome"]) == "decided":
                    tu = (v.get("detail") or {}).get("tip_unread")
                    rule = ("2.88_half_tip_unread" if tu else "2.88_half_other") + ("" if b and b["reason"] != reason else "_same_as_base")
                elif d == "infer:collapse_bare_stem_by_bar":
                    rule = "2.81_bare_stem_by_bar"
                elif d == "size_unboxed_rest":
                    rule = "2.99_sized"
                elif d == "size_reinstated_rest":
                    rule = "2.80b_sized"
                elif d == "reconcile_duration":
                    rule = "2.80_reconcile" + ("" if b and b["decider"] != d else "_same_as_base")
            if rule is None:
                continue
            cases.append({"rule": rule, "subject": subject, "quantity": q,
                          "arm": short(v), "base": short(fb.get(key)),
                          "box_page_px": box_of(idx, subject)})
        # base-only 2.88 halves (decided in base, not in arm)
        for key, v in fb.items():
            if key[1] == "duration" and v["reason"] == "hollow_head_bare_stem":
                a = fa.get(key)
                if a is None or a["reason"] != "hollow_head_bare_stem":
                    cases.append({"rule": "2.88_half_lost_vs_base", "subject": key[0],
                                  "quantity": "duration", "arm": short(a), "base": short(v),
                                  "box_page_px": box_of(idx, key[0])})
        # staff naming base -> arm
        nb = {k[0]: v for k, v in fb.items() if k[1] == "instrument"}
        na = {k[0]: v for k, v in fa.items() if k[1] == "instrument"}
        for s, v in na.items():
            b = nb.get(s)
            nm = lambda x: (x["value"] or {}).get("name") if x and isinstance(x.get("value"), dict) else None  # noqa: E731
            if nm(b) != nm(v) or str(b["outcome"] if b else None) != str(v["outcome"]):
                cases.append({"rule": "2.93-95_staff_naming", "subject": s, "quantity": "instrument",
                              "arm": short(v), "base": short(b), "box_page_px": None})
        out[doc] = cases
        cnt = defaultdict(int)
        for c in cases:
            cnt[c["rule"]] += 1
        print(doc, dict(cnt))
    json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)


main()
