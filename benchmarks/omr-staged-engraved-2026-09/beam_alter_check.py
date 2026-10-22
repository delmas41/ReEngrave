"""`<beam>` and `<alter>` on ENGRAVED ink — the 09-21 emission's first
second-printing contact.

`benchmarks/omr-sounding-pitch-2026-09` landed both and measured them on TWO
SCANS. The 09-21 handoff §6 item 4 says the engraved family is where beams
matter and has never been run: the legacy beam work measured **430 of 449
edits as `editbeam`** there. This runs it.

    python3 benchmarks/omr-staged-engraved-2026-09/beam_alter_check.py \
        --ours out/engraved-p0.musicxml \
        --truth out/fixture/<stem>.musicxml \
        --bars 7 --truth-first-bar 1 --page-svg out/fixture/<stem>-p1.svg

Four questions, three of which can fail on their own:

  1. STRUCTURE   does every `begin` at a beam level have its `end`? A file that
                 does not is malformed, and no count would say so.
  2. COUNT       ours against the truth ENCODING's own `<beam>` elements over
                 the same bars. ⚠️ This is an ENCODING comparison and NOT a
                 page one: the page draws one beam STROKE per group and
                 MusicXML writes one `<beam>` per note per level, so the two
                 are different units and the page-truth `beam` family (which
                 `score_reading` already scores) answers a different question.
  3. SEQUENCE    per part, the whole `(number, type)` list end to end. A count
                 that agrees over a wrong distribution is the failure mode.
  4. FLAGS       re-render OUR file with Verovio and count the `flag` glyphs it
                 draws. A note that should be beamed and is not gets a flag, so
                 this is an independent witness that needs no alignment at all
                 — the check the sibling lane used (flags 574 -> 82).

`<alter>` is checked the same way, and ⚠️ the ACCIDENTAL family is deliberately
NOT compared against the rendered page: `page_truth.render_fidelity` declares
it unreliable because Verovio draws one accidental per `<alter>` rather than
per `<accidental>`. The ENCODING's `<alter>` is the right truth for a SOUNDING
alteration, and that is what is compared here.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import warnings
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))


def per_part(xml: Path, first: int, n: int) -> List[Dict[str, Any]]:
    """Beams and alters of each part, over `n` bars from `first` (1-based)."""
    root = ET.parse(str(xml)).getroot()
    out = []
    for p in root.findall("{*}part"):
        bars = p.findall("{*}measure")[first - 1: first - 1 + n]
        beams: List[Tuple[str, str]] = []
        alters: List[str] = []
        open_at: Counter = Counter()
        unbalanced = 0
        for m in bars:
            for note in m.findall("{*}note"):
                for b in note.findall("{*}beam"):
                    num = b.get("number") or "1"
                    kind = (b.text or "").strip()
                    beams.append((num, kind))
                    if kind == "begin":
                        open_at[num] += 1
                    elif kind == "end":
                        if open_at[num] == 0:
                            unbalanced += 1
                        else:
                            open_at[num] -= 1
                a = note.find("{*}pitch/{*}alter")
                if a is not None:
                    step = note.findtext("{*}pitch/{*}step") or "?"
                    octv = note.findtext("{*}pitch/{*}octave") or "?"
                    alters.append(f"{step}{octv}:{a.text}")
        unbalanced += sum(open_at.values())
        out.append({"beams": beams, "alters": alters,
                    "unbalanced_levels": unbalanced,
                    "n_bars": len(bars)})
    return out


def verovio_flags(xml: Path) -> Dict[str, int]:
    """What Verovio DRAWS for this file: beams and flags, per page."""
    try:
        import verovio  # type: ignore
    except ImportError:
        return {"error": "verovio not installed"}
    from tools.omr.page_truth import VEROVIO_OPTIONS
    tk = verovio.toolkit()
    tk.setOptions(dict(VEROVIO_OPTIONS))
    if not tk.loadData(xml.read_text()):
        return {"error": "verovio could not load the file"}
    flags = beams = 0
    for i in range(tk.getPageCount()):
        svg = tk.renderToSVG(i + 1)
        flags += len(re.findall(r'class="flag bounding-box"', svg))
        beams += len(re.findall(r'class="beam bounding-box"', svg))
    return {"pages": tk.getPageCount(), "flag": flags, "beam": beams}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ours", type=Path, required=True)
    ap.add_argument("--truth", type=Path, required=True)
    ap.add_argument("--bars", type=int, required=True)
    ap.add_argument("--truth-first-bar", type=int, default=1)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    O = per_part(args.ours, 1, args.bars + 4)     # our file starts at bar 1
    T = per_part(args.truth, args.truth_first_bar, args.bars)
    print(f"REACH: {len(O)} parts ours, {len(T)} truth; "
          f"truth bars {args.truth_first_bar}.."
          f"{args.truth_first_bar + args.bars - 1}")
    if len(O) != len(T):
        print("REFUSED: part counts differ; the ordinal join is a guess here.")
        return 2

    ob = sum(len(r["beams"]) for r in O)
    tb = sum(len(r["beams"]) for r in T)
    oa = sum(len(r["alters"]) for r in O)
    ta = sum(len(r["alters"]) for r in T)
    bad = sum(r["unbalanced_levels"] for r in O)
    if ob == 0 and tb == 0:
        print("DEAD: neither side carries a <beam> over these bars.")
        return 2

    print(f"\n1. STRUCTURE  unbalanced beam levels in OUR file: {bad}"
          f"   {'OK' if bad == 0 else '⚠️ MALFORMED'}")
    print(f"2. COUNT      <beam>  ours {ob:5d}  truth {tb:5d}"
          f"   delta {ob - tb:+d}")
    print(f"              <alter> ours {oa:5d}  truth {ta:5d}"
          f"   delta {oa - ta:+d}")

    seq_beam = sum(1 for a, b in zip(O, T) if a["beams"] == b["beams"])
    seq_alt = sum(1 for a, b in zip(O, T) if a["alters"] == b["alters"])
    print(f"3. SEQUENCE   parts whose whole <beam> list matches:  "
          f"{seq_beam} of {len(T)}")
    print(f"              parts whose whole <alter> list matches: "
          f"{seq_alt} of {len(T)}")

    print(f"\n   per part (beams ours/truth, alters ours/truth):")
    for i, (a, b) in enumerate(zip(O, T)):
        mark = "" if (a["beams"] == b["beams"] and a["alters"] == b["alters"]) \
            else "   <--"
        print(f"   {i:2d}  beams {len(a['beams']):3d}/{len(b['beams']):3d}  "
              f"alters {len(a['alters']):3d}/{len(b['alters']):3d}{mark}")

    print(f"\n4. FLAGS (Verovio re-renders OUR file; a note that should be "
          f"beamed and is not gets a flag)")
    print(f"   ours : {verovio_flags(args.ours)}")
    print(f"   truth: {verovio_flags(args.truth)}"
          f"   ⚠️ the truth is the WHOLE excerpt, not these bars — read the "
          f"flag/beam RATIO, never the totals")

    out = {"beams_ours": ob, "beams_truth": tb, "alters_ours": oa,
           "alters_truth": ta, "unbalanced": bad,
           "parts_beam_sequence_exact": seq_beam,
           "parts_alter_sequence_exact": seq_alt,
           "verovio_ours": verovio_flags(args.ours)}
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=1, default=str))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
