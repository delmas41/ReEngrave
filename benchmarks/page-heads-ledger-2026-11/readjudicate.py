"""ROADMAP 2.290 build -- re-run ADJUDICATE..INFER on a gathered record's own GATHER rows with THIS tree and the env given, and write it back as a record
(the lane report's gather arm exports the verdicts a record carries: a record gathered through every stage keeps the gather-time verdicts, so an
ADJUDICATE-only change is measured only after this). Both arms of a pair must be re-run by the same tree.

    PYTHONPATH=. [OMR_...=1] python3 benchmarks/page-heads-ledger-2026-11/readjudicate.py IN.record.json OUT.record.json
"""
import json
import os
import sys

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")


def main(src, dst):
    from tools.omr.staged.review import rerun as RR
    d = json.load(open(src))
    rec = d.get("record", d)
    log, _ = RR.rebuild_gather({"observations": rec["observations"], "abstentions": rec.get("abstentions") or [], "verdicts": []})
    RR.run_stages(log)
    out = log.to_json()
    for k, v in rec.items():
        if k not in out:
            out[k] = v
    if "record" in d:
        d = dict(d, record=out, summary=log.summary())
    else:
        d = out
    json.dump(d, open(dst, "w"), default=str)
    print("re-adjudicated", src, "->", dst, len(out.get("verdicts") or []), "verdicts")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
