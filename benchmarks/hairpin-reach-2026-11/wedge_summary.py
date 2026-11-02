"""ROADMAP 2.254: per page and arm, the wedge reads (CV rows, letter refusals) and what ADJUDICATE made of them (wedge_anchor outcome/reason).
Writes DIR/<plate>.wedges.json (each ON read with its box and verdict) for the tile cutter.

    python3 benchmarks/hairpin-reach-2026-11/wedge_summary.py WORKDIR brahms
"""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.judged import iter_array  # noqa: E402


def page(sub):
    return int(sub.split("/")[1])


def main(work, plate):
    work = pathlib.Path(work)
    dump = {}
    for arm in ("off", "on"):
        rows = {}
        letters = collections.Counter()
        for it in iter_array(work / ("%s.%s.mini-record.json" % (plate, arm)), "observations"):
            if it.get("quantity") == "wedge_box" and it.get("reader") == "cv_hairpins":
                rows[it["subject"]] = {"subject": it["subject"], "kind": it["value"], "bbox": it["detail"].get("bbox_page_px"),
                                       "spacing": it["detail"].get("staff_spacing_px")}
        for it in iter_array(work / ("%s.%s.mini-record.json" % (plate, arm)), "abstentions"):
            if it.get("quantity") == "wedge_box" and (it.get("detail") or {}).get("why") == "letter":
                letters[page(it["subject"])] += 1
        out = collections.defaultdict(collections.Counter)
        for it in iter_array(work / ("%s.%s.mini-record.json" % (plate, arm)), "verdicts"):
            if it.get("quantity") == "wedge_anchor" and it["subject"] in rows:
                r = rows[it["subject"]]
                r["outcome"], r["reason"], r["value"] = it.get("outcome"), it.get("reason"), it.get("value")
                out[page(it["subject"])][(it.get("outcome"), it.get("reason"))] += 1
        per = collections.Counter(page(s) for s in rows)
        for p in sorted(per):
            print("%s %s p%d: %d CV wedge rows (%d refused as letters) -> %s" % (plate, arm.upper(), p, per[p], letters[p],
                                                                               dict(out[p])))
        dump[arm] = list(rows.values())
    (work / ("%s.wedges.json" % plate)).write_text(json.dumps(dump, indent=0, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:3])
