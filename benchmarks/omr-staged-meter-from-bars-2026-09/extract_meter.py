"""Pull the `Q.METER` verdicts out of a staged run, in reading order.

⚠️ READS THE RECORD, NOT AN EXPORT. The question is what the DECISION
concluded and on what basis, and an exported `<time>` cannot say whether a
meter was read, carried, derived from bars, or refused for want of a
spelling.
"""
import json
import sys


def meters(path):
    rec = json.load(open(path))["record"]
    out = []
    for v in rec.get("verdicts", []):
        if v.get("quantity") != "meter":
            continue
        out.append({"subject": v["subject"], "outcome": v["outcome"],
                    "reason": v.get("reason"), "value": v.get("value"),
                    "detail": v.get("detail")})
    return out


if __name__ == "__main__":
    rows = meters(sys.argv[1])
    if len(sys.argv) > 2:
        json.dump(rows, open(sys.argv[2], "w"), indent=2, default=str)
    for r in rows:
        val = r["value"] or {}
        segs = val.get("segments") or []
        extra = ""
        d = r["detail"] or {}
        if r["reason"] == "derived_from_bars":
            extra = (f"  length={d.get('length')} support={d.get('support')} "
                     f"({d.get('bars_agree')}+/{d.get('bars_disagree')}-) "
                     f"form<-{d.get('form_borrowed_from')}")
        elif r["reason"] == "bars_name_a_length_without_a_form":
            extra = (f"  length={d.get('length')} support={d.get('support')} "
                     f"({d.get('bars_agree')}+/{d.get('bars_disagree')}-) "
                     f"forms={d.get('candidate_forms')}")
        elif r["reason"] in ("carried", "carry_outweighed_by_the_bars"):
            extra = (f"  support={d.get('support')} "
                     f"({d.get('bars_agree')}+/{d.get('bars_disagree')}-)")
        print(f"{r['subject']:16s} {r['outcome']:9s} {str(r['reason']):36s} "
              f"{val.get('raw')}"
              f"{'  segments=' + str([(s.get('from_cell'), s.get('raw')) for s in segs]) if len(segs) > 1 else ''}"
              f"{extra}")
