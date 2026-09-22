"""Reduce a full staged record to the rows the ink-first test reads.

⚠️ WHY THIS EXISTS. The four-page Breitkopf record is ~460 MB and
`library/_shared-records/` is gitignored, so the artefact that closes the
breakthrough document's named blocker would live on ONE MACHINE. The rows this
test actually reads -- `Q.INK`, `Q.GLYPH_BOX`, `Q.GLYPH_CONF`,
`Q.CELL_STAFF_SPACE` -- are a small fraction of that, and the single-page
predecessor (`omr-ink-first-2026-09/out/brahms1-breitkopf-p2.gather.json`,
7.9 MB) is committed for exactly this reason. This writes the four-page
equivalent so a cloud session with no weights and no `library/` can re-run the
test, extend it, or refute it.

⚠️ IT IS A PROJECTION, NOT A RECORD, and must not be described as one: it
carries NO verdicts, NO abstentions and only four of the sixty-nine
quantities. `--check` re-reads what it wrote and asserts the counts against the
source, because a projection that silently drops a field is this repo's
most-recorded defect (`works.json`'s `lines`, named in four places and dropped
by all four).

READ-ONLY with respect to `tools/`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

KEEP = ("ink", "glyph_box", "glyph_conf", "cell_staff_space")


def md5(path, chunk=1 << 22):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    print(f"reading {a.record} ({os.path.getsize(a.record)/1e6:.1f} MB) ...",
          flush=True)
    with open(a.record) as f:
        doc = json.load(f)
    log = doc["record"] if "record" in doc else doc
    obs = log["observations"]
    print(f"  {len(obs)} observations", flush=True)

    src_counts = {}
    kept = []
    for o in obs:
        q = o.get("quantity")
        src_counts[q] = src_counts.get(q, 0) + 1
        if q in KEEP:
            kept.append(o)
    print(f"  keeping {len(kept)} rows of {KEEP}", flush=True)

    out = {
        "note": ("A PROJECTION of a staged record onto the four quantities "
                 "the ink-first test reads. NOT a record: no verdicts, no "
                 "abstentions, 4 of 69 quantities."),
        "source_record": os.path.basename(a.record),
        "source_md5": md5(a.record),
        "source_bytes": os.path.getsize(a.record),
        "kept_quantities": list(KEEP),
        "source_quantity_counts": {k: src_counts[k] for k in sorted(src_counts)},
        "provenance": doc.get("provenance"),
        "settings": doc.get("settings"),
        "observations": kept,
    }
    with open(a.out, "w") as f:
        json.dump(out, f)
    print(f"wrote {a.out} ({os.path.getsize(a.out)/1e6:.1f} MB)", flush=True)

    # ── CONTROL: re-read and assert, because a lossy projection is silent ──
    with open(a.out) as f:
        back = json.load(f)
    ok = True
    for q in KEEP:
        want = src_counts.get(q, 0)
        got = sum(1 for o in back["observations"] if o.get("quantity") == q)
        flag = "ok" if got == want else "MISMATCH"
        if got != want:
            ok = False
        print(f"  CONTROL {q:20} source {want:>7}  projection {got:>7}  {flag}")
    if not kept:
        print("DEAD: nothing kept")
        return 2
    # a field-level control: the ink detail keys must survive whole
    ink = [o for o in back["observations"] if o["quantity"] == "ink"]
    if ink:
        need = {"ink_bbox_canonical", "bbox_page_px", "width_spaces",
                "height_spaces", "ink_area_px", "ink_fill",
                "ink_detector_coverage", "ink_n_components",
                "ink_share_of_cell", "cell_staff_space_px"}
        missing = need - set(ink[0]["detail"])
        print(f"  CONTROL ink detail keys        "
              f"{'ok' if not missing else 'MISSING ' + str(missing)}")
        if missing:
            ok = False
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
