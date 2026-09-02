"""Surya against Tesseract on direction crops cut from a SCAN.

`FINDINGS.md` finding 5 records that Surya fails by returning the empty string,
which is indistinguishable from "there is no text here". On engraved pages that
was a nuisance fixed by upscaling. On a scan it is the dominant failure: the
candidate step proposes real words and the reader says nothing about most of
them.

The question this answers is narrow and worth separating from everything else:
**is the silence a property of the crop, or of the reader?** If a second OCR
reads the same crop, the crop is fine and the rung is the problem. If both are
silent, the crop is the problem and no amount of reader-swapping helps.

    python3 benchmarks/omr-direction-text-2026-09/bakeoff_readers_on_scan.py \\
        /tmp/scan-crops --out /tmp/bakeoff.json

Reads every PNG in a directory with both engines and prints them side by side.
The crops come from `eval_on_scan.py --crops-dir`, so they are exactly what the
shipped reader was shown — not a re-cut of the page.

⚠️ **Reading a crop is not the same as accepting it.** Both columns are raw OCR;
`direction_lexicon.lookup` still has to accept the string, and a garbled read
that the lexicon refuses buys nothing. The report therefore shows what each
engine returned AND what the lexicon does with it, because a rung that turns
silence into refusals is not an improvement.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.omr.direction_lexicon import lookup            # noqa: E402

# The settings come FROM the shipped rung rather than being restated here. This
# harness has to read RAW — the whole point is the raw-versus-stripped column —
# so it cannot simply call `read_crops_text`, which strips. Importing the
# constants is what stops the two drifting into measuring different things.
from tools.omr.staff_labels_tesseract import (PSM_LINE,   # noqa: E402
                                              UPSCALE,
                                              strip_line_fragments)


def read_tesseract(image) -> str:
    """Tesseract's RAW reading — the shipped rung's settings, without its
    `strip_line_fragments`, so the two columns can be compared."""
    import pytesseract                                     # noqa: PLC0415

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    work = cv2.resize(gray, None, fx=UPSCALE, fy=UPSCALE,
                      interpolation=cv2.INTER_CUBIC)
    return pytesseract.image_to_string(work, config=f"--psm {PSM_LINE}").strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("crops_dir", type=Path)
    ap.add_argument("--glob", default="*.png")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    paths = sorted(args.crops_dir.glob(args.glob))
    if not paths:
        print(f"no crops matching {args.glob} in {args.crops_dir}", file=sys.stderr)
        return 2
    images = [cv2.imread(str(p)) for p in paths]

    from tools.omr.staff_labels_surya import read_crops_text
    surya = read_crops_text(images)
    tess = [read_tesseract(im) for im in images]

    rows = []
    for path, s, t in zip(paths, surya, tess):
        stripped = strip_line_fragments(t)
        rows.append({"crop": path.name, "surya": s, "tesseract": t,
                     "tesseract_stripped": stripped,
                     "surya_accepted": bool(lookup(s)),
                     "tesseract_accepted": bool(lookup(t)),
                     "tesseract_stripped_accepted": bool(lookup(stripped))})

    print(f"{'crop':34s} {'surya':>26s}  {'tesseract':>26s}")
    for r in rows:
        mark = lambda ok: "+" if ok else " "                # noqa: E731
        print(f"{r['crop']:34s} {r['surya']!r:>26s}{mark(r['surya_accepted'])} "
              f"{r['tesseract']!r:>26s}{mark(r['tesseract_accepted'])}")

    n = len(rows)
    s_read = sum(1 for r in rows if r["surya"])
    t_read = sum(1 for r in rows if r["tesseract"])
    s_ok = sum(1 for r in rows if r["surya_accepted"])
    t_ok = sum(1 for r in rows if r["tesseract_accepted"])
    t_ok_stripped = sum(1 for r in rows if r["tesseract_stripped_accepted"])
    union = sum(1 for r in rows
                if r["surya_accepted"] or r["tesseract_stripped_accepted"])
    both_silent = sum(1 for r in rows if not r["surya"] and not r["tesseract"])
    print(f"\n{n} crops")
    print(f"  surya      read {s_read:3d}   lexicon-accepted {s_ok:3d}")
    print(f"  tesseract  read {t_read:3d}   lexicon-accepted {t_ok:3d} raw, "
          f"{t_ok_stripped:3d} with staff-line fragments stripped")
    print(f"  UNION (what ships)                    {union:3d}")
    print(f"  both silent {both_silent} — for these the CROP is the problem, "
          f"not the rung")
    if args.out:
        args.out.write_text(json.dumps(rows, indent=1) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
