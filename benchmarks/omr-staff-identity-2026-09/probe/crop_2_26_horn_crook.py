"""ROADMAP 2.26 -- crops for Sean, the Horn-crook question.

`probe_2_26_holdout.py` found that ALL 956 Brahms 1/i (Breitkopf 317803)
noteheads/rests held out under `staff_not_identified` sit on 42 staves, and
every one of the 42 is a HORN staff, never the condensed `Violoncello e
Basso` case CLAUDE.md names (that case never fires on this document at all
-- 0 `family_block` inferences, matching roadmap 2.1b's own measurement).

The mechanism, read straight off the record (no new evidence gathered):
Brahms 1 writes 4 horns on 2 braced staves, crooked in C and in Es. On the
document's widest system (the reference lineup `adjudicate_slot_index`
picks against, `system/2/1`), the margin OCR reads BOTH staves in full --
`"(C) Hr."` (slot 5) and `"Hr. (Es)"` (slot 6) -- and both decide `Horn`.
On every OTHER (short) system, the SAME pair reads `"(C) Hr."` on the first
staff (decides `Horn`, alias `hr`) and a bare crook fragment -- `"(Es)"`,
once just `"(C)"` -- on the second, with NO instrument root at all. The
lexicon correctly abstains `not_in_lexicon` on the bare fragment (measured
40 of 42 exactly this shape, `"(C) Hr."` / `"(Es)"`; 2 minor OCR variants,
`"(C) Hr"` and `"(C)"`). And even where the FIRST staff's `Hr.` resolves,
`adjudicate_instrument` reduces `"(C) Hr."` to the generic name `Horn` --
the crook is read but not carried forward -- so `adjudicate_slot_index`'s
name-pairing sees `Horn` appearing TWICE in the reference (slots 5 and 6)
and cannot force a pairing: `ambiguous_pairing`. The bare-fragment staff,
carrying no name at all, is not a trailing block (Horn sits mid-lineup, at
5/6 of 14) so `_place_in_family_block` correctly declines it too:
`unnamed_in_short_system`.

**The crook text that would settle both abstentions is already ON THE
RECORD** (`Q.MARGIN_LABEL`) and is thrown away twice: once when
`adjudicate_instrument` collapses `"(C) Hr."` to bare `Horn`, and once more
when the bare fragment is asked to name an INSTRUMENT rather than compared,
as a crook, against the reference's own already-decided crook text. Neither
throw is a print convention -- it is possibly a value computed and unread
(named library-wide, `feedback_find_export_gaps.md` /
`project_value_computed_and_unread.md`) -- but whether the plate's convention
is what this diagnosis assumes (a bare parenthetical crook, no instrument
word, ALWAYS continues the staff directly above it, and never denotes an
unrelated instrument's own crook) is a page-reading claim CLAUDE.md rule 3
asks to confirm before code, not to assume. Hence: crops, not a patch.

Renders 8 system-header crops (both staves of the pair, full margin column,
several pages, plus the two shapes that are NOT the clean pair -- one where
only ONE horn staff exists at all with no partner to eliminate against, one
where BOTH staves read only a bare crook) and the reference system for
comparison. `VERDICT_none_yet: null` on every manifest row.

    python3 benchmarks/omr-staff-identity-2026-09/probe/crop_2_26_horn_crook.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged import export as X  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

RECORD = (REPO_ROOT / "library/_shared-records/"
          "brahms1-breitkopf-mvt1-whole-20260929.record.json")
PDF = (REPO_ROOT / "library/editions/brahms/symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
OUT_DIR = Path(__file__).resolve().parent.parent / "out" / "print"
# ⚠️ MUST MATCH THE GATHER'S OWN DPI, not a cosmetic choice: `Q.STAFF_LINES`
# is in pixel coordinates AT THE GATHER'S RASTER (`provenance.settings.args
# .dpi`, 600 for this record -- CLAUDE.md notes the CLI default is 600, the
# web app's is 300, and the two are not interchangeable). Rendering at any
# other DPI silently shows the WRONG staff under a correctly-computed band
# -- caught here by eye (first draft used 400 and drew "Horn" bands over
# "2.Viol."/"Br").
DPI = 600

# (page, system, [staff ordinals to show]) -- picked to cover every shape
# the probe found, spread across the movement.
CASES = [
    (7, 0, [4, 5], "clean pair -- Hr. decides, (Es) abstains"),
    (20, 0, [5, 6], "clean pair, second occurrence order (5,6 not 4,5)"),
    (15, 1, [5, 6], "clean pair, another page"),
    (22, 0, [4, 5], "clean pair, another page"),
    (9, 1, [5], "ONLY ONE horn staff gathered here -- no partner to "
                "eliminate against, ambiguous_pairing alone"),
    (23, 1, [5], "ONLY ONE horn staff gathered here -- second instance"),
    (26, 1, [5, 6], "BOTH staves read only a bare crook -- (C) then (Es), "
                    "neither resolves"),
    (2, 1, [5, 6], "REFERENCE system (widest, 14 staves) -- both staves "
                   "read IN FULL, 'Hr.' present on both, and this is the "
                   "lineup every other system is judged against"),
]


def main() -> int:
    import fitz
    from PIL import Image, ImageDraw, ImageFont

    result = load_record(str(RECORD))
    rec = X.Record(result)
    doc = fitz.open(str(PDF))
    font = ImageFont.load_default(size=22)
    big = ImageFont.load_default(size=30)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for n, (page, system, staves, note) in enumerate(CASES, 1):
        name = f"o226-{n:02d}"
        pm = doc[page].get_pixmap(dpi=DPI)
        im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
              if pm.n >= 3 else
              Image.frombytes("L", (pm.width, pm.height), pm.samples)
              .convert("RGB"))

        rows = []
        ys = []
        for st in staves:
            key = f"staff/{page}/{system}/{st}"
            lr = rec.obs(Q.STAFF_LINES, key)
            sr = rec.obs(Q.STAFF_SPACING, key)
            ml = rec.obs(Q.MARGIN_LABEL, key)
            iv = rec.verdict(Q.INSTRUMENT, key)
            sv = rec.verdict(Q.SLOT_INDEX, key)
            lines = lr[-1]["value"] if lr else None
            spacing = sr[-1]["value"] if sr else 30.0
            text = ml[-1]["value"] if ml else None
            rows.append({
                "staff": key, "ordinal": st,
                "lines": lines, "spacing": spacing,
                "margin_text": text,
                "instrument": (iv.get("value") or {}).get("name")
                              if iv and iv["outcome"] == "decided" else None,
                "instrument_outcome": iv["outcome"] if iv else "absent",
                "instrument_reason": iv.get("reason") if iv else None,
                "slot_outcome": sv["outcome"] if sv else "absent",
                "slot_reason": sv.get("reason") if sv else None,
            })
            if isinstance(lines, list):
                ys.extend(lines)

        if not ys:
            manifest.append({"n": n, "case": [page, system, staves],
                             "note": note, "REFUSED": "no staff geometry"})
            continue

        sp = max((r["spacing"] or 30.0) for r in rows)
        cy0 = max(0, int(min(ys) - 3.5 * sp))
        cy1 = min(im.height, int(max(ys) + 3.5 * sp))
        cx0 = 0
        cx1 = min(im.width, int(im.width * 0.42))
        crop = im.crop((cx0, cy0, cx1, cy1))

        overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        colours = [(0, 130, 60), (30, 90, 255), (200, 90, 0)]
        for i, r in enumerate(rows):
            rgb = colours[i % len(colours)]
            lines = r["lines"] or []
            if not lines:
                continue
            top = (min(lines) - cy0)
            bot = (max(lines) - cy0)
            od.rectangle([0, top, crop.width, bot], fill=rgb + (55,))
            for ly in lines:
                y = ly - cy0
                if 0 <= y < crop.height:
                    od.line([(0, y), (crop.width, y)], fill=rgb + (220,),
                            width=3)
            label = (f"ord {r['ordinal']}  text={r['margin_text']!r}  "
                     f"inst={r['instrument']!r} ({r['instrument_outcome']}"
                     f"{'/' + r['instrument_reason'] if r['instrument_reason'] else ''})  "
                     f"slot={r['slot_outcome']}"
                     f"{'/' + r['slot_reason'] if r['slot_reason'] else ''}")
            ty = max(0, top + (bot - top) / 2 - 15)
            tw = od.textlength(label, font=big)
            od.rectangle([4, ty - 3, 4 + tw + 10, ty + 33], fill=(255, 255, 255, 235),
                        outline=rgb + (255,), width=3)
            od.text((8, ty), label, fill=rgb + (255,), font=big)

        crop = Image.alpha_composite(crop.convert("RGBA"), overlay).convert("RGB")
        band_h = 100
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        cd.text((6, 4), f"{name}  pdf idx {page}  system {system}  {note}",
                fill=(0, 0, 0), font=font)
        cd.text((6, 32), "Q: does a bare crook '(C)'/'(Es)' with no 'Hr.' "
                          "ALWAYS mean 'this staff continues the Horn staff "
                          "above it' -- never a different instrument's own "
                          "crook?", fill=(120, 0, 0), font=font)
        cd.text((6, 60), "If yes: slot_index can pair it by matching the "
                          "crook substring against the reference's own "
                          "decided Horn labels, never by guessing order.",
                fill=(0, 0, 0), font=font)
        out_im.save(OUT_DIR / f"{name}.png")

        manifest.append({
            "n": n, "file": f"{name}.png", "page": page, "system": system,
            "note": note, "rows": rows,
            "question": ("bare crook '(C)'/'(Es)' with no 'Hr.' always "
                        "continues the Horn staff above it, and the crook "
                        "text itself picks which of the two reference Horn "
                        "slots -- yes / no / sometimes"),
            "VERDICT_none_yet": None,
        })
        print(f"wrote {name}.png  ({[ (r['ordinal'], r['margin_text']) for r in rows]})")

    (OUT_DIR / "o226-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.26",
        "record": str(RECORD),
        "pdf": str(PDF.relative_to(REPO_ROOT)),
        "dpi": DPI,
        "question": ("Does a bare parenthetical crook ('(C)' / '(Es)') with "
                    "no instrument word, on a staff immediately below a "
                    "decided Horn staff at the SAME slot region, ALWAYS mean "
                    "'this staff is the Horn pair's other crook, continuing "
                    "the label above it' -- never an unrelated instrument's "
                    "own independent crook annotation?"),
        "crops": manifest,
    }, indent=2))
    print(f"manifest -> {OUT_DIR / 'o226-manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
