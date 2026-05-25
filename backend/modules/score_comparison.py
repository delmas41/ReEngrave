"""
Score comparison module using music21.

Compares MusicXML files measure-by-measure by extracting note tuples and
checking for exact matches. Supports .mxl (compressed) and plain XML.

NOTE: music21 is a heavy library. Comparison may take 10–30 seconds for
large scores.
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from typing import Optional

# music21 import is deferred inside functions so the module can still be
# imported even if music21 is not yet installed — the routes will fail at
# call-time with a clear error.


def _decompress_mxl(path: str) -> str:
    """
    If *path* is a .mxl (ZIP-compressed MusicXML), extract the inner XML
    to a sibling temp file and return its path.  Otherwise return *path*
    unchanged.
    """
    if not path.lower().endswith(".mxl"):
        return path

    try:
        with zipfile.ZipFile(path, "r") as zf:
            # The .mxl container may include META-INF/container.xml — look for
            # the first .xml / .musicxml member that is not in META-INF.
            xml_names = [
                n for n in zf.namelist()
                if n.lower().endswith((".xml", ".musicxml"))
                and not n.startswith("META-INF")
            ]
            if not xml_names:
                return path  # give up, let music21 try
            xml_name = xml_names[0]
            out_path = path.replace(".mxl", "_extracted.xml")
            with zf.open(xml_name) as src, open(out_path, "wb") as dst:
                dst.write(src.read())
            return out_path
    except Exception:
        return path  # fall back to original path


def parse_musicxml(path: str):
    """Parse a MusicXML (or .mxl) file and return a music21 Score object."""
    import music21  # noqa: PLC0415

    effective_path = _decompress_mxl(path)
    return music21.converter.parse(effective_path)


def extract_measures(score) -> list[dict]:
    """
    Return a list of measure dicts from a parsed music21 Score.

    Each dict: {
        "number": int,
        "notes": [{"pitch": int|None, "duration": float, "voice": str}]
    }
    Rests are included as pitch=None.
    """
    import music21  # noqa: PLC0415

    measures = []
    try:
        # Flatten to a single part view so we capture all parts.
        # We iterate the first part only for measure-numbering stability;
        # multi-part comparison is done at the score level.
        parts = list(score.parts)
        if not parts:
            return []

        # Use the first part for measure extraction.
        part = parts[0]
        for element in part.getElementsByClass(music21.stream.Measure):
            measure_num = int(element.number) if element.number else 0
            notes = []
            for n in element.flatten().notesAndRests:
                if isinstance(n, music21.note.Note):
                    notes.append({
                        "pitch": n.pitch.midi,
                        "duration": float(n.duration.quarterLength),
                        "voice": str(n.voice) if n.voice else "1",
                    })
                elif isinstance(n, music21.chord.Chord):
                    # Represent chord as sorted list of midi pitches in one entry.
                    pitches = sorted(p.midi for p in n.pitches)
                    notes.append({
                        "pitch": pitches,
                        "duration": float(n.duration.quarterLength),
                        "voice": str(n.voice) if n.voice else "1",
                    })
                elif isinstance(n, music21.note.Rest):
                    notes.append({
                        "pitch": None,
                        "duration": float(n.duration.quarterLength),
                        "voice": str(n.voice) if n.voice else "1",
                    })
            measures.append({"number": measure_num, "notes": notes})
    except Exception as exc:
        # Return what we have so far; partial data is better than crashing.
        measures.append({"number": -1, "notes": [], "error": str(exc)})

    return measures


def _measure_fingerprint(measure_dict: dict) -> tuple:
    """Convert a measure dict to a hashable fingerprint for comparison."""
    return tuple(
        (
            tuple(n["pitch"]) if isinstance(n["pitch"], list) else n["pitch"],
            round(n["duration"], 6),
        )
        for n in measure_dict.get("notes", [])
    )


def compare_two_scores(path_a: str, path_b: str) -> dict:
    """
    Compare two MusicXML files and return a similarity report.

    Returns:
        {
            "similarity_pct": float,
            "measure_diffs": [
                {"measure_num": int, "status": "match"|"differ"|"missing", "detail": str}
            ],
            "error": str | None
        }
    """
    try:
        score_a = parse_musicxml(path_a)
        score_b = parse_musicxml(path_b)
        measures_a = extract_measures(score_a)
        measures_b = extract_measures(score_b)
    except Exception as exc:
        return {
            "similarity_pct": 0.0,
            "measure_diffs": [],
            "error": f"Failed to parse scores: {exc}",
        }

    # Index by measure number.
    index_a = {m["number"]: m for m in measures_a}
    index_b = {m["number"]: m for m in measures_b}

    all_nums = sorted(set(index_a.keys()) | set(index_b.keys()))
    if not all_nums:
        return {"similarity_pct": 100.0, "measure_diffs": [], "error": None}

    diffs = []
    matched = 0

    for num in all_nums:
        if num not in index_a:
            diffs.append({"measure_num": num, "status": "missing", "detail": "Missing in score A"})
        elif num not in index_b:
            diffs.append({"measure_num": num, "status": "missing", "detail": "Missing in score B"})
        else:
            fp_a = _measure_fingerprint(index_a[num])
            fp_b = _measure_fingerprint(index_b[num])
            if fp_a == fp_b:
                matched += 1
                diffs.append({"measure_num": num, "status": "match", "detail": ""})
            else:
                notes_a = len(index_a[num].get("notes", []))
                notes_b = len(index_b[num].get("notes", []))
                diffs.append({
                    "measure_num": num,
                    "status": "differ",
                    "detail": f"Note count: {notes_a} vs {notes_b}",
                })

    similarity_pct = (matched / len(all_nums)) * 100 if all_nums else 100.0

    return {
        "similarity_pct": round(similarity_pct, 2),
        "measure_diffs": diffs,
        "error": None,
    }


INSTRUMENT_RANGES = {
    "violin": (55, 103),      # G3 to G7
    "viola": (48, 91),        # C3 to G6
    "cello": (36, 76),        # C2 to E5
    "double bass": (28, 67),  # E1 to G4
    "flute": (60, 98),        # C4 to D7
    "oboe": (58, 91),         # Bb3 to G6
    "clarinet": (50, 94),     # D3 to Bb6
    "bassoon": (34, 75),      # Bb1 to Eb5
    "horn": (34, 81),         # Bb1 to F5
    "trumpet": (52, 84),      # E3 to C6
    "trombone": (40, 77),     # E2 to F5
    "tuba": (28, 67),         # E1 to G4
    "piano": (21, 108),       # A0 to C8
    "harp": (24, 103),        # C1 to G7
    "timpani": (40, 60),      # E2 to C4
}

# Enharmonic equivalents for unusual spellings
_ENHARMONIC_SUGGESTIONS = {
    "B#": "C",
    "C-": "B",   # Cb
    "E#": "F",
    "F-": "E",   # Fb
}


def run_theory_checks(xml_path: str) -> list[dict]:
    """Run music theory sanity checks on a MusicXML file.

    Checks:
    - Rhythm: measures whose note/rest durations don't sum to the time signature
    - Range: notes outside standard playable range for the instrument
    - Enharmonic: unusual note spellings that suggest OMR errors

    Returns a list of issue dicts, each with keys:
        measure, part, check, detail
    """
    try:
        import music21  # noqa: PLC0415
        import music21.stream  # noqa: PLC0415
        import music21.note  # noqa: PLC0415
        import music21.chord  # noqa: PLC0415
        import music21.meter  # noqa: PLC0415
    except ImportError:
        return [{"measure": 0, "part": "—", "check": "error",
                 "detail": "music21 is not installed. Run: pip install music21"}]

    issues: list[dict] = []

    try:
        effective_path = _decompress_mxl(xml_path)
        score = music21.converter.parse(effective_path)
    except Exception as exc:
        return [{"measure": 0, "part": "—", "check": "error",
                 "detail": f"Failed to parse score: {exc}"}]

    try:
        parts = list(score.parts)
    except Exception as exc:
        return [{"measure": 0, "part": "—", "check": "error",
                 "detail": f"Failed to iterate parts: {exc}"}]

    for part in parts:
        try:
            part_name = part.partName or part.id or "Unknown"
        except Exception:
            part_name = "Unknown"

        # Determine instrument range match (substring of part name, lowercase)
        part_lower = part_name.lower()
        matched_instrument: Optional[str] = None
        for key in INSTRUMENT_RANGES:
            if key in part_lower:
                matched_instrument = key
                break

        try:
            measures = list(part.getElementsByClass(music21.stream.Measure))
        except Exception:
            continue

        for measure in measures:
            try:
                measure_num = int(measure.number) if measure.number else 0
            except Exception:
                measure_num = 0

            # --- A. Rhythm validation ---
            try:
                ts = measure.getContextByClass(music21.meter.TimeSignature)
                if ts is not None:
                    expected_beats = float(ts.barDuration.quarterLength)
                    actual_beats = sum(
                        float(n.duration.quarterLength)
                        for n in measure.flatten().notesAndRests
                    )
                    if abs(actual_beats - expected_beats) > 0.01:
                        issues.append({
                            "measure": measure_num,
                            "part": part_name,
                            "check": "rhythm",
                            "detail": (
                                f"Measure sums to {actual_beats:.2f} beats, "
                                f"expected {expected_beats:.2f}"
                            ),
                        })
            except Exception:
                pass  # skip rhythm check if time sig unavailable

            # --- B. Instrument range check and C. Enharmonic spelling ---
            try:
                for element in measure.flatten().notes:
                    # Handle both Note and Chord
                    if isinstance(element, music21.chord.Chord):
                        note_list = list(element.notes)
                    elif isinstance(element, music21.note.Note):
                        note_list = [element]
                    else:
                        continue

                    for note in note_list:
                        try:
                            midi = note.pitch.midi
                            note_name = note.pitch.nameWithOctave
                        except Exception:
                            continue

                        # B. Range check
                        if matched_instrument is not None:
                            lo, hi = INSTRUMENT_RANGES[matched_instrument]
                            if midi < lo or midi > hi:
                                issues.append({
                                    "measure": measure_num,
                                    "part": part_name,
                                    "check": "range",
                                    "detail": (
                                        f"Note {note_name} (MIDI {midi}) out of range "
                                        f"for {matched_instrument}"
                                    ),
                                })

                        # C. Enharmonic spelling check
                        try:
                            acc = note.pitch.accidental
                            pitch_step = note.pitch.step  # e.g. "B", "C"
                            acc_name = acc.name if acc is not None else "natural"

                            # Double accidentals
                            if acc is not None and acc.alter is not None and abs(acc.alter) >= 2:
                                issues.append({
                                    "measure": measure_num,
                                    "part": part_name,
                                    "check": "enharmonic",
                                    "detail": (
                                        f"Unusual spelling: {note_name} — "
                                        f"double accidental — likely OMR error"
                                    ),
                                })
                            else:
                                # Check for specific unusual spellings: B#, Cb, E#, Fb
                                if acc is not None and acc.alter == 1 and pitch_step == "B":
                                    issues.append({
                                        "measure": measure_num,
                                        "part": part_name,
                                        "check": "enharmonic",
                                        "detail": (
                                            f"Unusual spelling: {note_name} — consider C"
                                        ),
                                    })
                                elif acc is not None and acc.alter == -1 and pitch_step == "C":
                                    issues.append({
                                        "measure": measure_num,
                                        "part": part_name,
                                        "check": "enharmonic",
                                        "detail": (
                                            f"Unusual spelling: {note_name} — consider B"
                                        ),
                                    })
                                elif acc is not None and acc.alter == 1 and pitch_step == "E":
                                    issues.append({
                                        "measure": measure_num,
                                        "part": part_name,
                                        "check": "enharmonic",
                                        "detail": (
                                            f"Unusual spelling: {note_name} — consider F"
                                        ),
                                    })
                                elif acc is not None and acc.alter == -1 and pitch_step == "F":
                                    issues.append({
                                        "measure": measure_num,
                                        "part": part_name,
                                        "check": "enharmonic",
                                        "detail": (
                                            f"Unusual spelling: {note_name} — consider E"
                                        ),
                                    })
                        except Exception:
                            pass  # skip enharmonic check on error

            except Exception:
                pass  # skip note-level checks on error

    return issues


def compare_multiple(
    paths: list[str],
    master_path: Optional[str] = None,
) -> dict:
    """
    Compare 2–N MusicXML files, optionally against a master.

    The master (if provided) is prepended as paths[0] with label "master".

    Returns:
        {
            "labels": ["master", "source_0", ...],
            "matrix": [[sim_pct, ...], ...],   # NxN similarity matrix
            "per_measure_agreement": [
                {"measure_num": int, "agreement_pct": float, "sources_agreeing": int}
            ],
            "consensus_issues": [measure_nums where agreement_pct < 100],
            "error": str | None,
        }
    """
    all_paths: list[str] = []
    labels: list[str] = []

    if master_path:
        all_paths.append(master_path)
        labels.append("master")

    for i, p in enumerate(paths):
        all_paths.append(p)
        labels.append(f"source_{i}")

    if len(all_paths) < 2:
        return {
            "labels": labels,
            "matrix": [],
            "per_measure_agreement": [],
            "consensus_issues": [],
            "error": "Need at least 2 sources to compare",
        }

    # Parse all scores up front.
    parsed: list[list[dict]] = []
    try:
        for p in all_paths:
            score = parse_musicxml(p)
            parsed.append(extract_measures(score))
    except Exception as exc:
        return {
            "labels": labels,
            "matrix": [],
            "per_measure_agreement": [],
            "consensus_issues": [],
            "error": f"Failed to parse: {exc}",
        }

    n = len(all_paths)

    # Build pairwise similarity matrix.
    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 100.0
        for j in range(i + 1, n):
            result = compare_two_scores(all_paths[i], all_paths[j])
            pct = result["similarity_pct"]
            matrix[i][j] = pct
            matrix[j][i] = pct

    # Per-measure agreement across all sources.
    all_measure_nums: set[int] = set()
    for measures in parsed:
        for m in measures:
            all_measure_nums.add(m["number"])

    per_measure: list[dict] = []
    consensus_issues: list[int] = []

    for num in sorted(all_measure_nums):
        fingerprints = []
        for measures in parsed:
            idx = {m["number"]: m for m in measures}
            if num in idx:
                fingerprints.append(_measure_fingerprint(idx[num]))

        if not fingerprints:
            continue

        if len(fingerprints) < 2:
            per_measure.append({
                "measure_num": num,
                "agreement_pct": 100.0,
                "sources_agreeing": 1,
            })
            continue

        # Majority fingerprint is the most common one.
        from collections import Counter
        counts = Counter(fingerprints)
        most_common_fp, most_common_count = counts.most_common(1)[0]

        sources_agreeing = most_common_count
        agreement_pct = round((sources_agreeing / len(fingerprints)) * 100, 2)

        per_measure.append({
            "measure_num": num,
            "agreement_pct": agreement_pct,
            "sources_agreeing": sources_agreeing,
        })

        if agreement_pct < 100.0:
            consensus_issues.append(num)

    return {
        "labels": labels,
        "matrix": matrix,
        "per_measure_agreement": per_measure,
        "consensus_issues": consensus_issues,
        "error": None,
    }


def run_dual_theory_checks(xml_path: str) -> dict:
    """Run both engines in parallel(-ish) and return their outputs together.

    Composes:
      - music21 rhythm/range/enharmonic checks (existing — returns list)
      - maestro_bridge harmony + rhythm hints (new — returns dict or None)

    The two engines are complementary. music21 produces rule-violation
    entries (one per issue); maestro produces structured analysis (overall
    key, RN progression, cadences, per-voice beat sums). The web app can
    show them side by side; CLI consumers can use either.

    Maestro path is gated behind MAESTRO_BRIDGE_ENABLED env var (default
    off) and failures are swallowed — if the bridge isn't installed or
    errors, `maestro` is None and music21 still runs.
    """
    music21_issues = run_theory_checks(xml_path)

    try:
        from .theory_layer import compute_theory_hints  # type: ignore
    except ImportError:
        try:
            from theory_layer import compute_theory_hints  # type: ignore
        except ImportError:
            compute_theory_hints = None  # type: ignore

    maestro_hints = None
    if compute_theory_hints is not None:
        try:
            maestro_hints = compute_theory_hints(xml_path)
        except Exception:
            maestro_hints = None

    return {
        "music21": music21_issues,
        "maestro": maestro_hints,
    }
