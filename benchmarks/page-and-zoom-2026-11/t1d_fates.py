"""ROADMAP 2.307 T1d -- EXPORT's fate (`written` or the refusal reason) of named glyphs, OFF and ON, for tracing a bar that got worse.

    python3 benchmarks/page-and-zoom-2026-11/t1d_fates.py SLICES_DIR PLATE GLYPH [GLYPH ...]

Replays ADJUDICATE..EXPORT as `lane_report --from adjudicate` does, once per arm, in this process, and prints each glyph's fate from
`export._place_notes` plus whether it is a hidden copy ON. Measure only.
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..")))

import os
import sys


def main():
    root, plate, subs = sys.argv[1], sys.argv[2], sys.argv[3:]
    os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
    from tools.omr.staged import export as E
    from tools.omr.staged import lane_report as LR
    from tools.omr.staged.review import rerun as RR
    real = E._place_notes
    got = {}

    def place(rec, runs, **kw):
        out = real(rec, runs, **kw)
        got["fates"] = dict(kw.get("fates") or {})
        got["hidden"] = set(getattr(rec, "hidden_copies", ()) or ())
        got["rec"] = rec
        return out
    E._place_notes = place
    for arm in ("0", "1"):
        os.environ["OMR_PAGE_OWNED_VIEW"] = arm
        rec = LR.load_slices(LR.slice_dir(plate, root))
        rec["verdicts"] = []
        log, _ = RR.rebuild_gather(rec)
        RR.run_stages(log)
        result = {"record": log.to_json(), "summary": log.summary()}
        del log
        E.to_musicxml(result)
        r = got["rec"]
        print("== OMR_PAGE_OWNED_VIEW=%s" % arm)
        for s in subs:
            own = r.verdict("glyph_owner", s)
            print("  ", s, "fate:", got["fates"].get(s), "| hidden copy:", s in got["hidden"], "| owner:",
                  (own or {}).get("outcome"), (own or {}).get("value"), (own or {}).get("reason"))
        # every hidden copy in the same cells
        cells = {"/".join(s.split("/")[:5]) + "/" for s in subs}
        for h in sorted(got["hidden"]):
            if any(h.startswith(c) for c in cells):
                print("   hidden in these cells:", h)


if __name__ == "__main__":
    main()
