"""night 2026-10-07 read, step 1: ONE load of a record (record_io.load_record) feeds everything the read needs.

  python3 night_1007_extract.py <record.json> <tag> <xdir> <vso-scratch>

Writes <xdir>/<tag>.json (the 10-06 extraction: far-head / owner / census blocks, reused as is, plus the mark-group
rows `mark_group` {subject: [gid, category]} and the record's summary) and the verify script's extract
(<vso-scratch>/<tag>.extract.json) for the staff-line measure.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import night_1006_extract as E6
from tools.omr.staged.record_io import load_record
from tools.omr.staged.record import Q


def main(src, tag, xdir, vso):
    os.environ["VSO_SCRATCH"] = vso
    import verify_staff_line_offsets as V
    res = load_record(src)
    out = E6.from_result(res, src)
    mg = {}
    for o in res["record"]["observations"]:
        if o["quantity"] == Q.MARK_GROUP:
            mg[o["subject"]] = [o["value"], (o.get("detail") or {}).get("category")]
    out["mark_group"] = mg
    out["summary"] = res.get("summary")
    Path(xdir, f"{tag}.json").write_text(json.dumps(out))
    print(tag, "glyphs", len(out["glyphs"]), "mark_group rows", len(mg),
          "result keys", list(res.keys()), flush=True)
    V.extract_from(res, tag)
    print(tag, "done", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:5])
