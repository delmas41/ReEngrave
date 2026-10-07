"""ROADMAP 2.58 / 2.58b -- rebuild a saved GATHER record to EVALUATE, then export.

No detector, no gather. A saved record holds GATHER rows (and, for a record
stopped `--through adjudicate`, no `Q.PITCH`), so this rebuilds a `Log` from
the GATHER rows, runs ADJUDICATE and EVALUATE on TODAY'S tree, and writes the
resulting record to a work file that `tools.omr.staged.export` reads.

    python3 benchmarks/omr-local-staff-2026-09/mark_identity_rebuild.py \
        REC.json OUT.json [--pages 3] [--control]

`--pages` keeps only those PDF page indices (document-level rows are kept).
`--groups` first files the mark-group rows (2.58b).
`--control` re-adjudicates and compares the `glyph_owner` outcome census with
the saved record's (a control that can fail: a tree that no longer reproduces
the record says so and the figures below it are not baselines).

Read the record ONLY through `record_io.load_record` (CLAUDE.md).
"""
import argparse
import collections
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.staged import adjudicate, evaluate                # noqa: E402
from tools.omr.staged import adjudicators, consequences          # noqa: E402,F401
from tools.omr.staged.record import Log, Subject                 # noqa: E402
from tools.omr.staged.record_io import load_record               # noqa: E402


def _page_of(subject: str):
    parts = subject.split("/")
    if parts[0] in ("document",):
        return None
    try:
        return int(parts[1])
    except (IndexError, ValueError):
        return None


def rebuild(rec: dict, pages=None) -> Log:
    log = Log()
    rows = [(r, "obs") for r in rec["observations"]]
    rows += [(r, "abs") for r in rec.get("abstentions", [])]
    rows.sort(key=lambda t: t[0]["id"])
    for r, kind in rows:
        if pages is not None:
            pg = _page_of(r["subject"])
            if pg is not None and pg not in pages:
                continue
        sub = Subject.from_key(r["subject"])
        detail = dict(r.get("detail") or {})
        if kind == "obs":
            log.observe(sub, r["quantity"], r["value"], reader=r["reader"],
                        frame=r["frame"], score=r.get("score"), **detail)
        else:
            log.abstain(sub, r["quantity"], reader=r["reader"],
                        frame=r["frame"], reason=r["reason"], **detail)
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("out")
    ap.add_argument("--pages", default=None, help="comma list of pdf indices")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--groups", action="store_true",
                    help="file Q.MARK_GROUP rows (ROADMAP 2.58b) off the "
                         "rebuilt GLYPH_BOX rows before adjudicating")
    ap.add_argument("--through", default="evaluate",
                    choices=["adjudicate", "evaluate"])
    a = ap.parse_args()
    pages = set(int(x) for x in a.pages.split(",")) if a.pages else None
    t0 = time.time()
    res = load_record(a.record)
    rec = res["record"]
    print(f"loaded in {time.time() - t0:.0f}s: {len(rec['observations'])} obs")
    log = rebuild(rec, pages)
    if a.groups:
        from tools.omr.staged import gather as G
        print("mark groups filed:", G.mark_groups_from_log(log))
    t1 = time.time()
    adjudicate.run(log)
    print(f"adjudicate {time.time() - t1:.0f}s")
    if a.through == "evaluate":
        t2 = time.time()
        evaluate.run(log)
        print(f"evaluate {time.time() - t2:.0f}s")
    out_rec = log.to_json()
    if a.control:
        def census(verdicts):
            c = collections.Counter()
            for v in verdicts:
                if v["quantity"] == "glyph_owner":
                    pg = _page_of(v["subject"])
                    if pages is None or pg in pages:
                        c[(v["outcome"], v.get("reason"))] += 1
            return c
        want, got = census(rec["verdicts"]), census(out_rec["verdicts"])
        same = want == got
        print("CONTROL glyph_owner (outcome, reason) census "
              + ("REPRODUCED" if same else "DIFFERS"))
        if not same:
            for k in sorted(set(want) | set(got), key=str):
                if want[k] != got[k]:
                    print(f"   {k}: saved {want[k]}  rebuilt {got[k]}")
    result = dict(res)
    result["record"] = out_rec
    Path(a.out).write_text(json.dumps(result, default=str))
    print(f"wrote {a.out} total {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
