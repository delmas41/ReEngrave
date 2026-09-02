"""Is the second rung worth its keep, on the code as it stands TODAY?

Needs a cached transcription per page (`OMR_SCAN_CACHE`, default `cache-scan/`
beside this file) so it can re-ask the question in seconds without
re-transcribing: the candidates come from the cached detections, and only the
crops and the OCR are recomputed.

Everything since the union shipped — the band fix, the span fix, and two lexicon
tightenings — changed what each rung is shown and what the gate does with it. So
the question is re-asked from scratch: on the current code, what does Surya
alone accept, and what does the union accept, and does the union ever make a
reading WORSE rather than merely add one?
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import tools.omr.direction_text as dt
from tools.omr.direction_lexicon import lookup
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

#: The scan this was measured on, and the cache of its transcriptions. Both are
#: machine-local; point them elsewhere to re-ask the question on another print.
SCAN = Path(os.environ.get("OMR_SCAN_PDF", ROOT / "library/editions/beethoven/"
            "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
            "1870--imslp575951.pdf"))
CACHE = Path(os.environ.get("OMR_SCAN_CACHE", Path(__file__).parent / "cache-scan"))

surya_only, union, added, changed = 0, 0, [], []
for page_index in [int(a) for a in sys.argv[1:]] or [16, 22, 39, 78, 84]:
    cached = CACHE / f"p{page_index}.json"
    if not cached.is_file():
        print(f"no cached transcription at {cached}; see the module docstring",
              file=sys.stderr)
        raise SystemExit(2)
    page_dict = json.loads(cached.read_text())["pages"][0]
    page = render_page(SCAN, page_index, dpi=600)
    pws = detect_staves(page)
    spacing = float(np.median([s.line_spacing_px for s in pws.staves]))
    cands = dt.find_candidates(pws, page_dict)
    crops = [dt.crop_for(page, c, spacing) for c in cands]
    reads = {name: fn(crops) for name, fn in dt.default_readers()}

    for i, c in enumerate(cands):
        s = reads.get("surya", [""] * len(cands))[i]
        t = reads.get("tesseract", [""] * len(cands))[i]
        hs, ht = lookup(s), lookup(t)
        if hs:
            surya_only += 1
        if hs or ht:
            union += 1
        if ht and not hs:
            added.append((page_index, c.staff_index, s, ht.text))
        if hs and ht and hs.text.strip().lower().rstrip(".") != \
                ht.text.strip().lower().rstrip("."):
            changed.append((page_index, c.staff_index, hs.text, ht.text))
    print(f"page {page_index}: {len(cands)} candidates", flush=True)

print(f"\nsurya alone accepts   {surya_only}")
print(f"union accepts         {union}   (+{union - surya_only})")
print(f"\nwhat the second rung ADDS (surya said nothing usable):")
for p, s, raw, txt in added:
    print(f"   p{p} staff {s:2d}   surya {raw!r:34s} -> tesseract {txt!r}")
print(f"\ncrops where BOTH accept but name different words "
      f"(the only way the union can make a reading worse): {len(changed)}")
for p, s, a, b in changed:
    print(f"   p{p} staff {s:2d}   surya {a!r} vs tesseract {b!r}  -> surya wins")
