"""IS A THIRD PLATE REACHABLE? -- §5's falsification needs one, and n = 2.

The handoff's falsification for this lane is explicit: *"if the convention's
agreement on heads we already read falls below ~90% on a third publisher, it is
not a reader."* It is 95.9 (Litolff) and 98.2 (Breitkopf). Two plates is not a
population, and both are the SAME two this whole thread has ever used.

⚠️ WHAT A THIRD PLATE HAS TO SUPPLY, which is more than a PDF. The convention
probe reads `staff_lines`, `notehead_class` and `glyph_box.bbox_page_px` off a
STAGED RECORD, and scores itself against that record's own `stem_direction`
verdicts. So a third publisher means a third RECORD -- a gather, with weights --
not merely a third file. This says which candidates exist and what each would
cost, and it deliberately does not claim one has been run.

`data/score-library/catalog.json` is COMMITTED (only the PDF bytes are
gitignored), so this question is answerable with no library at all.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = HERE.parents[1] / "data" / "score-library" / "catalog.json"

#: The two plates every figure on this thread comes from, by IMSLP id.
HELD = {"984073": "Litolff Beethoven 5 (the record)",
        "317803": "Breitkopf Brahms 1 (the record)"}

#: The two works a third plate would be most comparable on -- same music, so
#: the only thing that changes is the PRINTING, which is what §5 asks about.
WORKS = ("beethoven--symphony-5", "brahms--symphony-1")


def main() -> int:
    if not CATALOG.is_file():
        print(f"DEAD: no catalog at {CATALOG}", file=sys.stderr)
        return 2
    cat = json.loads(CATALOG.read_text())
    entries = cat.get("entries") or []
    if not entries:
        print("DEAD: catalog holds no entries", file=sys.stderr)
        return 2

    rows = []
    for e in entries:
        if e.get("kind") != "edition" and "editions" not in str(e.get("kind")):
            if not str(e.get("path", "")).endswith(".pdf"):
                continue
        wid = str(e.get("work_id") or "")
        if wid not in WORKS:
            continue
        rows.append(e)

    if not rows:
        print(f"DEAD: catalog names no edition of {WORKS}", file=sys.stderr)
        return 2

    print(f"catalog: {len(entries)} entries; {len(rows)} editions of the two "
          f"works this thread measures\n")
    print(f"{'work':<26} {'publisher':<34} {'imslp':>8} {'pages':>6} "
          f"{'image_type':<16} held")
    for e in sorted(rows, key=lambda r: (str(r.get("work_id")),
                                         str(r.get("publisher")))):
        ident = str(e.get("imslp_id") or "")
        mark = "<- THE RECORD" if ident in HELD else ""
        print(f"{str(e.get('work_id')):<26} "
              f"{str(e.get('publisher'))[:34]:<34} {ident:>8} "
              f"{str(e.get('n_pages') or '?'):>6} "
              f"{str(e.get('image_type') or '?')[:16]:<16} {mark}")

    fresh = [e for e in rows if str(e.get("imslp_id")) not in HELD]
    print(f"\n{len(fresh)} candidate third plates of the SAME MUSIC.")
    print("⚠️ Each needs a GATHER (weights) to become a record before the "
          "convention can be scored on it. `image_type` is IMSLP's own label, "
          "not a measurement of legibility.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
