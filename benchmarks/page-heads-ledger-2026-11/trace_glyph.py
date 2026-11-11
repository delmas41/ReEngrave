"""ROADMAP 2.290 r1 -- READ-ONLY: every row (gather and verdict) the replayed log holds for given glyph subjects.
    PYTHONPATH=. python3 benchmarks/page-heads-ledger-2026-11/trace_glyph.py SLICES_DIR PLATE PAGE GLYPH_KEY [GLYPH_KEY ...]
"""
import json, os, sys
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")

def main(slices, plate, page, keys):
    from tools.omr.staged import conservation as C
    from tools.omr.staged.review import rerun as RR
    rec = C.load_pages(plate, [page], slices)
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    keys = set(keys)
    for r in log.all_rows():
        sub = getattr(r, "subject", None)
        k = sub.to_key() if hasattr(sub, "to_key") else str(sub)
        if k in keys:
            d = getattr(r, "detail", None) or {}
            s = json.dumps(d, default=str)
            print(k, "|", r.quantity, "|", str(getattr(r, "value", None))[:90], "|", getattr(r, "reader", None), "|", s[:420])

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4:])
