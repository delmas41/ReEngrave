"""Build OMR dossiers from MusicXML — the known facts a scan can be checked against.

`docs/dossier-verification-plan.md` asks for a hand-authored file per work
carrying meter, key, clefs, instrumentation and measure count. Those facts are
already sitting in the Gradus score library as MusicXML, where they are exact
rather than remembered, so this generates them instead of asking for typing.

    python3 -m tools.omr.training.build_dossiers --list
    python3 -m tools.omr.training.build_dossiers --only beethoven-sym5-mvt1
    python3 -m tools.omr.training.build_dossiers          # everything orchestral

WRITTEN, NOT CONCERT. Every clef and key signature here is what is PRINTED on
the page — a B-flat clarinet in a 3-flat movement is stored as `fifths: -1`,
because that is what the OMR reader will see. `docs/dossier-verification-plan.md`
warned that a concert-pitch dossier makes every transposing staff false-flag;
storing written facts removes the trap rather than compensating for it.
`transposition_semitones` is kept alongside so concert reasoning stays possible.

CONDENSATION. A printed score puts Flute 1 and Flute 2 on one staff; the
MusicXML keeps them as two parts. So part index does NOT reliably equal staff
index, and `benchmarks/omr-mxl-autolabel/FINDINGS.md` records an attempt to
force that join failing at F1 0.064. The dossier therefore also carries the
alignment-free SETS (`clefs_used`, `written_fifths_used`) that verification can
use without knowing which staff is which. See `tools/omr/dossier.py`.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCORE_DIR = Path(
    "/Users/seanjohnson/Desktop/gradus-vercel/public/scores"
)
DEFAULT_OUT_DIR = ROOT / "data" / "dossiers"

# Chorales and keyboard preludes are single-system textures the pipeline
# already handles; the dossier exists for the orchestral case. A name is
# orchestral if it isn't one of these.
_SKIP_PREFIXES = ("bwv", "bach-", "chorale")


def _is_orchestral(stem: str) -> bool:
    low = stem.lower()
    return not any(low.startswith(p) for p in _SKIP_PREFIXES)


def _clef_name(cl: Any) -> str | None:
    """music21 clef → the pipeline's clef vocabulary.

    Both sides name a clef by (family, which line it sits on), so this is a
    table lookup rather than a translation. `tools/omr/clef_geometry.py` owns
    the table; importing it keeps one definition.
    """
    from tools.omr.clef_geometry import CLEF_BY_FAMILY_LINE

    sign = getattr(cl, "sign", None)
    line = getattr(cl, "line", None)
    if sign is None or line is None:
        return None
    name = CLEF_BY_FAMILY_LINE.get(str(sign).upper(), {}).get(int(line))
    if name is None:
        return None
    # An octave-displaced clef is the same glyph with a marker; the pipeline
    # spells that as a suffix on the base name.
    shift = getattr(cl, "octaveChange", 0) or 0
    suffix = {1: "_8va", -1: "_8vb", 2: "_15ma", -2: "_15mb"}.get(int(shift))
    return name + suffix if suffix else name


def _measure_number(m: Any, fallback: int) -> int:
    n = getattr(m, "number", None)
    try:
        return int(n)
    except (TypeError, ValueError):
        return fallback


def dossier_from_score(path: Path, work_id: str) -> dict[str, Any]:
    """Read one MusicXML file into a dossier dict."""
    from music21 import clef as m21clef
    from music21 import converter
    from music21 import key as m21key
    from music21 import meter as m21meter

    score = converter.parse(str(path))
    parts_out: list[dict[str, Any]] = []
    meter_changes: list[dict[str, Any]] = []
    seen_meter: set[tuple[int, int, int]] = set()
    total_measures = 0

    for slot, part in enumerate(score.parts):
        measures = list(part.getElementsByClass("Measure"))
        total_measures = max(total_measures, len(measures))

        inst = part.getInstrument(returnDefault=True)
        transposition = getattr(inst, "transposition", None)
        semitones = 0
        if transposition is not None:
            try:
                semitones = int(transposition.semitones)
            except (TypeError, ValueError, AttributeError):
                semitones = 0

        written_clef: str | None = None
        written_fifths: int | None = None
        clef_changes: list[dict[str, Any]] = []
        key_changes: list[dict[str, Any]] = []

        for idx, m in enumerate(measures, start=1):
            number = _measure_number(m, idx)
            for cl in m.getElementsByClass(m21clef.Clef):
                name = _clef_name(cl)
                if name is None:
                    continue
                if written_clef is None:
                    written_clef = name
                elif name != (clef_changes[-1]["clef"] if clef_changes
                              else written_clef):
                    clef_changes.append({"measure": number, "clef": name})
            for ks in m.getElementsByClass(m21key.KeySignature):
                fifths = int(ks.sharps)
                if written_fifths is None:
                    written_fifths = fifths
                elif fifths != (key_changes[-1]["fifths"] if key_changes
                                else written_fifths):
                    key_changes.append({"measure": number, "fifths": fifths})
            for ts in m.getElementsByClass(m21meter.TimeSignature):
                entry = (number, int(ts.numerator), int(ts.denominator))
                # Every part restates the meter; the score has one.
                sig = (entry[1], entry[2])
                if not meter_changes or (
                    meter_changes[-1]["beats"],
                    meter_changes[-1]["beat_type"],
                ) != sig:
                    if entry not in seen_meter:
                        seen_meter.add(entry)
                        meter_changes.append({
                            "measure": number,
                            "beats": entry[1],
                            "beat_type": entry[2],
                        })

        parts_out.append({
            "slot": slot,
            "name": str(part.partName) if part.partName else f"part {slot}",
            "written_clef": written_clef,
            "written_fifths": written_fifths,
            "transposition_semitones": semitones,
            "clef_changes": clef_changes,
            "key_changes": key_changes,
            "measures": len(measures),
        })

    meter_changes.sort(key=lambda e: e["measure"])
    starting_meter = (
        {"beats": meter_changes[0]["beats"],
         "beat_type": meter_changes[0]["beat_type"]}
        if meter_changes else None
    )

    clefs_used = sorted({
        c for p in parts_out
        for c in [p["written_clef"]] + [ch["clef"] for ch in p["clef_changes"]]
        if c
    })
    fifths_used = sorted({
        f for p in parts_out
        for f in [p["written_fifths"]] + [ch["fifths"] for ch in p["key_changes"]]
        if f is not None
    })

    return {
        "schema_version": 3,
        "work_id": work_id,
        "source": {
            "kind": "musicxml",
            "path": str(path),
            "generated_by": "tools.omr.training.build_dossiers",
        },
        "title": str(score.metadata.title) if score.metadata else None,
        "composer": str(score.metadata.composer) if score.metadata else None,
        "total_measures": total_measures,
        "starting_meter": starting_meter,
        "meter_changes": meter_changes,
        "constant_meter": len(meter_changes) <= 1,
        "parts": parts_out,
        # Alignment-free facts — usable without knowing which staff is which.
        "clefs_used": clefs_used,
        "written_fifths_used": fifths_used,
        "n_parts": len(parts_out),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-dir", type=Path, default=DEFAULT_SCORE_DIR)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--only", action="append", default=None,
                    help="work_id to build (repeatable); default is all")
    ap.add_argument("--list", action="store_true",
                    help="list the works that would be built, then exit")
    args = ap.parse_args(argv)

    if not args.score_dir.is_dir():
        print(f"score dir not found: {args.score_dir}", file=sys.stderr)
        return 2

    paths = sorted(
        p for p in args.score_dir.iterdir()
        if p.suffix in (".mxl", ".musicxml") and _is_orchestral(p.stem)
    )
    if args.only:
        wanted = set(args.only)
        paths = [p for p in paths if p.stem in wanted]

    if args.list:
        for p in paths:
            print(p.stem)
        print(f"\n{len(paths)} works")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    ok = failed = 0
    for p in paths:
        out = args.out_dir / f"{p.stem}.json"
        try:
            d = dossier_from_score(p, p.stem)
        except Exception as exc:  # noqa: BLE001 — one bad file must not stop the run
            failed += 1
            print(f"FAIL {p.stem}: {type(exc).__name__}: {exc}", file=sys.stderr)
            traceback.print_exc(limit=1, file=sys.stderr)
            continue
        out.write_text(json.dumps(d, indent=2) + "\n")
        ok += 1
        print(f"{p.stem}: {d['n_parts']} parts, {d['total_measures']} measures, "
              f"meter {d['starting_meter']}, clefs {d['clefs_used']}, "
              f"fifths {d['written_fifths_used']}")

    print(f"\nwrote {ok} dossiers to {args.out_dir}"
          + (f"; {failed} failed" if failed else ""))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
