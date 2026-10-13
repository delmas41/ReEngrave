"""ROADMAP 2.101 probe: what each rule decided on a held-out record, and the
page proxies after export. DIAGNOSIS ONLY -- reads a record, writes JSON.

    python3 probe_reach.py REC.json OUT.json     # run with cwd = the tree whose
                                                 # code should export the record

Run it from the tree that GATHERED the record (base tree for base record, arm
tree for arm record), so the exporter and the proxies are that tree's own.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402


def pages_of(subject: str):
    # "glyph/PAGE/..." "cell/PAGE/..."
    p = subject.split("/")
    return int(p[1]) if len(p) > 1 and p[1].lstrip("-").isdigit() else None


def main(rec_path, out_path):
    res = load_record(rec_path)
    R = res["record"]
    prov = res.get("provenance") or {}
    out = {"commit": prov.get("commit"), "dirty": prov.get("dirty")}

    vq = Counter()      # (quantity, decider, outcome, reason)
    for v in R["verdicts"]:
        o = v["outcome"]
        o = o if isinstance(o, str) else str(o)
        vq["|".join((v["quantity"], str(v["decider"]), o, str(v["reason"])))] += 1
    out["verdicts"] = dict(vq)

    oq = Counter()      # (quantity, reader)
    for o in R["observations"]:
        oq["|".join((o["quantity"], str(o["reader"])))] += 1
    out["observations"] = dict(oq)
    aq = Counter()
    for a in R["abstentions"]:
        aq["|".join((a["quantity"], str(a["reader"]), str(a["reason"])))] += 1
    out["abstentions"] = dict(aq)

    # detail-key flags the rules under test write
    flags = Counter()
    keys = ("tip_unread", "clef_glyph_overruled_by_locator", "shared_word",
            "recovered", "thin_stroke", "unboxed", "bare_stem")
    for row in list(R["verdicts"]) + list(R["observations"]):
        d = row.get("detail") or {}
        for k in d:
            if any(s in k for s in keys):
                flags[k + ("|" + str(row["quantity"]))] += 1
    out["detail_flags"] = dict(flags)
    kinds = Counter()
    for v in R["verdicts"]:
        if str(v["decider"]).startswith(("recover", "work_roster")) or "worn" in str(v["reason"]):
            kinds[v["quantity"] + "|" + str(v["decider"]) + "|" + str(v["reason"])] += 1
    out["worn_label_like"] = dict(kinds)

    # export + proxies with THIS tree's code
    from tools.omr.staged import export as X
    from tools.omr import acceptance as A
    xml, report = X.to_musicxml(res)
    out["proxies"] = A.machine_proxies(xml, report)
    out["export_counters"] = {
        k: report.get("written", {}).get(k) for k in report.get("written", {})}
    out["notes_not_written"] = report.get("notes_not_written")
    out["bars_held_out_sum"] = {k: v for k, v in (report.get("bars_held_out_sum") or {}).items()
                                if k != "held"}
    out["held_list"] = [list(h) if not isinstance(h, dict) else h
                        for h in ((report.get("bars_held_out_sum") or {}).get("held") or [])][:2000]
    out["part_join"] = report.get("part_join")
    Path(out_path).with_suffix(".musicxml").write_text(xml)
    Path(out_path).write_text(json.dumps(out, indent=1, default=str))
    print("ok", out_path, len(xml))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
