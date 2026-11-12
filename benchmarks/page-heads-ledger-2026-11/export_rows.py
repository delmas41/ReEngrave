"""ROADMAP 2.290 build -- the OFF-is-identical control: ADJUDICATE..EXPORT of a gathered record's own GATHER rows on the tree this runs FROM (run it from
this lane's tree and from a `git archive` of main), the MusicXML written to OUT; diff the two files.

    cd TREE && PYTHONPATH=. python3 /path/export_rows.py REC.record.json OUT.musicxml
"""
import json
import os
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main(src, dst):
    from tools.omr.staged import export as E
    from tools.omr.staged.review import rerun as RR
    d = json.load(open(src))
    rec = d.get("record", d)
    log, _ = RR.rebuild_gather({"observations": rec["observations"], "abstentions": rec.get("abstentions") or [], "verdicts": []})
    RR.run_stages(log)
    xml, _report = E.to_musicxml({"record": log.to_json(), "summary": log.summary()})
    open(dst, "w").write(xml)
    print("wrote", dst, len(xml))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
