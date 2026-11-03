"""ROADMAP 2.254: re-decide a gathered record on THIS tree (`review.rerun.rebuild_gather` + `run_stages`, the lane_report adjudicate
path), keeping its GATHER rows and provenance, with the flag set as asked. A record written by `python3 -m tools.omr.staged` carries the
verdicts of the tree that gathered it; a later ADJUDICATE change (here `ownership._hairpin_separates`) needs this before reuse.

    OMR_HAIRPIN_REACH=1 python3 benchmarks/hairpin-reach-2026-11/readjudicate.py IN.record.json OUT.record.json
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main(src, dst):
    from tools.omr.staged.record_io import load_record
    from tools.omr.staged.review import rerun as RR
    whole = load_record(str(src))
    rec = whole.get("record", whole)
    prov = rec.get("provenance") or whole.get("provenance")
    rec["verdicts"] = []
    log, _ = RR.rebuild_gather(rec)
    del rec, whole
    RR.run_stages(log)
    out = log.to_json()
    if prov is not None and isinstance(out, dict):
        out.setdefault("provenance", prov)
    pathlib.Path(dst).write_text(json.dumps(out, default=str))
    print("wrote", dst)


if __name__ == "__main__":
    main(*sys.argv[1:3])
