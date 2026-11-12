"""ROADMAP 2.290 r1 -- READ-ONLY: the stroke-owner verdict (and the strokes) of one cell, restricted to the strokes/boxes named.
    PYTHONPATH=. python3 benchmarks/page-heads-ledger-2026-11/trace_cell_owner.py SLICES_DIR PLATE PAGE CELL_KEY GLYPH_KEY
"""
import json, os, sys
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")

def main(slices, plate, page, cell_key, gkey):
    from tools.omr.staged import conservation as C
    from tools.omr.staged.review import rerun as RR
    rec = C.load_pages(plate, [page], slices)
    log, _ = RR.rebuild_gather(rec)
    RR.run_stages(log)
    for r in log.all_rows():
        sub = getattr(r, "subject", None)
        k = sub.to_key() if hasattr(sub, "to_key") else str(sub)
        if k == cell_key and r.quantity in ("stroke_owner",):
            s = json.dumps(r.detail or {}, default=str)
            i = s.find(gkey)
            print(k, r.quantity, str(r.value)[:100], len(s))
            print(s[:200])
            while i >= 0 and i < len(s):
                print("...", s[max(0, i - 300): i + 900])
                i = s.find(gkey, i + 900)
                break
            print("keys:", list((r.detail or {}).keys()))
            ic = (r.detail or {}).get("ink_consult") or {}
            print("ink_consult for glyph:", ic.get(gkey))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5])
