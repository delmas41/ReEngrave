"""Fixture B — the meter CHANGES but its glyph is not printed.

⚠️ WHY THIS FIXTURE HAS TO EXIST. On a clean engraving the meter is printed
wherever it changes, and it is READ, so the carry is never asked to cross a
boundary and the bar reader is never asked to name anything. Fixture A
therefore cannot exercise the very rules it was built to settle — it shows
them not being needed.

The condition those rules exist for is the SCAN one: *the meter is printed and
we fail to read it* (Litolff p.17 sets `3` over `8` as heavy nearly-touching
digits the templates decline; p.62's change is classified on 2 staves of 17).
This reproduces exactly that, and nothing else: `\\once \\omit
Staff.TimeSignature` removes the GLYPH at the change while LilyPond keeps
barring the music in 3/4. So the ink is perfect everywhere, the bars really
are three quarter-notes long, and the only thing missing is the signature —
which is the scan's failure mode with legibility subtracted.

⚠️ It suppresses ONLY the change. The opening `4/4` is left printed on purpose,
because the carry needs a source that was genuinely READ.

    python3 benchmarks/omr-staged-meter-engraved-2026-09/hide_change_signature.py \
        --ly out/beethoven-sym5-mvt4-m145-175.ly --out-stem <stem>-hidden
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def hide(ly_path: Path, out_stem: str, marker: str = "\\time 3/4") -> dict:
    src = ly_path.read_text()
    n = src.count(marker)
    if not n:
        raise SystemExit(f"no {marker!r} in {ly_path}")
    # ⚠️ `\once \omit` at the SAME musical moment as the `\time`, so it removes
    # the signature LilyPond engraves there AND the courtesy copy it puts at
    # the end of the preceding line — they are one grob at one moment, drawn
    # twice.
    out = src.replace(marker, "\\once \\omit Staff.TimeSignature " + marker)
    dst = ly_path.with_name(out_stem + ".ly")
    dst.write_text(out)
    subprocess.run(["lilypond", "-s", "-o", out_stem, dst.name],
                   cwd=ly_path.parent, check=True, capture_output=True)
    pdf = ly_path.parent / (out_stem + ".pdf")
    import fitz
    with fitz.open(pdf) as doc:
        pages = doc.page_count
    return {"hidden_signatures": n, "ly": str(dst), "pdf": str(pdf),
            "n_pages": pages}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ly", required=True)
    ap.add_argument("--out-stem", required=True)
    # ⚠️ REQUIRED, NOT DEFAULTED, AND A DEFAULT COST A WHOLE ARM. This started
    # with `default="\\time 3/4"`, which is the CHANGE in the bar-155 fixture
    # and the OPENING in the bar-209 one — so the 209 run silently hid the
    # signature the carry needs as its SOURCE and left the change printed,
    # inverting the experiment. The tell was `system/0/0` abstaining
    # `no_evidence` where it had to read 3/4. Name the marker every time.
    ap.add_argument("--marker", required=True,
                    help=r"the LilyPond time signature to hide, e.g. '\time 4/4'")
    a = ap.parse_args()
    for k, v in hide(Path(a.ly), a.out_stem, a.marker).items():
        print(f"  {k}: {v}")
