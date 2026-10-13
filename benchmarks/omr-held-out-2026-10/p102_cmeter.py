"""ROADMAP 2.102 probe: heads that stand in a meter sign's column.

A `noteheadXxx` box whose page-x centre lies within HALF A HEAD of a `timeSig*`
box on ANOTHER staff of the same system. Prints, per record, how many there are
and what ADJUDICATE did with each (refused as a notehead? duration?).

    python3 benchmarks/omr-held-out-2026-10/p102_cmeter.py REC [REC ...]
"""
import collections
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

for path in sys.argv[1:]:
    r = load_record(path)["record"]
    sigs = collections.defaultdict(list)       # (page, system) -> [(staff, xc)]
    heads = []
    for o in r["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        d = o.get("detail") or {}
        p = o["subject"].split("/")
        if str(o["value"][0]).startswith("timeSig"):
            sigs[(p[1], p[2])].append((p[3], d.get("x_center_page")))
        elif str(o["value"][0]).startswith("notehead"):
            bb = d.get("bbox_page_px")
            if bb:
                heads.append((o["subject"], d.get("x_center_page"), bb[2] - bb[0]))
    refused, dur = {}, {}
    for v in r["verdicts"]:
        if v["quantity"] == "notehead_is_not_a_notehead" and v["outcome"] == "decided" \
                and v["value"] is True:
            refused[v["subject"]] = v["reason"]
        if v["quantity"] == "duration" and v["decider"] == "adjudicate_duration":
            dur[v["subject"]] = v
    hit = collections.Counter()
    for s, xc, w in heads:
        p = s.split("/")
        for staff, sx in sigs.get((p[1], p[2]), ()):
            if staff != p[3] and sx is not None and abs(xc - sx) < 0.5 * w:
                d = dur.get(s)
                hit[(refused.get(s, "NOT refused"),
                     "-" if d is None else f"{d['outcome']}:{d['reason']}")] += 1
                break
    print(path.split("/")[-1], "heads in a meter column:", sum(hit.values()))
    for k, n in hit.most_common(8):
        print("   ", n, k)
