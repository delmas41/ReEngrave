"""Can the five unmapped scan-gate rows carry a `staves` map AT ALL?

Asked of the CONSUMER, not of the note. `page_normalise.normalise` is the
function the `entire staff` bucket is about, and it takes exactly two inputs:
the trimmed truth and the map. It never sees the prediction, so the recorded
objection to a Mahler map — "a positional join to the prediction's parts would
be wrong from staff 13 on" — is an objection to a DIFFERENT consumer
(`scan_eval.note_recall`, which does `p_parts[i]` against `staves[i]`).

Four questions per row:

  1. does the candidate map account for every reference part?
  2. is every part the map folds in as `absent` actually SILENT in this row's
     window? (a fold of a SOUNDING part would hide a real failure)
  3. does `page_normalise.normalise` accept it, and what does it produce?
  4. is the fold TARGET arbitrary — i.e. does moving the absent parts to a
     different staff leave the output unchanged? (the control that makes the
     arbitrariness harmless rather than merely unnoticed)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))
sys.path.insert(0, str(HERE))

import page_normalise                      # noqa: E402
import candidate_maps                      # noqa: E402
from music21 import chord, converter, note  # noqa: E402

if "--patched" in sys.argv:
    import normalise_patched
    normalise_patched.apply()

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")
OUT = HERE / "mappable.json"


def sounding_parts(truth: Path) -> dict[int, int]:
    """part index -> number of sounding events over the whole trimmed file."""
    sc = converter.parse(str(truth))
    counts = {}
    for i, p in enumerate(sc.parts):
        n = sum(1 for el in p.recurse().notesAndRests
                if isinstance(el, (note.Note, chord.Chord)))
        counts[i] = n
    return counts


def main() -> int:
    rows = []
    for rid, spec in candidate_maps.CANDIDATES.items():
        truth = REC / f"{rid}.truth.musicxml"
        sc = converter.parse(str(truth))
        n_parts = len(sc.parts)
        counts = sounding_parts(truth)

        flat = candidate_maps.flat(rid)
        printed = candidate_maps.printed_only(rid)
        absent = candidate_maps.absent_parts(rid)

        named = sorted({i for s in flat for i in s["parts"]})
        printed_named = sorted({i for s in printed for i in s["parts"]})
        dup = [i for i in named
               if sum(s["parts"].count(i) for s in flat) > 1]

        rec = {
            "row_id": rid,
            "n_reference_parts": n_parts,
            "n_map_entries": len(flat),
            "covers_every_part": named == list(range(n_parts)),
            "unnamed_parts": [i for i in range(n_parts) if i not in named],
            "duplicate_named_parts": dup,
            "absent_parts": absent,
            "absent_all_silent": all(counts.get(i, 0) == 0 for i in absent),
            "absent_sounding": {i: counts[i] for i in absent
                                if counts.get(i, 0)},
            "printed_only_covers": len(printed_named),
            "unrepresentable_printed_staves":
                candidate_maps.UNREPRESENTABLE.get(rid, []),
        }

        # 3. the consumer
        try:
            out, report = page_normalise.normalise(truth, flat)
            rec["normalise"] = {
                "accepted": True,
                "n_source_parts": report["n_source_parts"],
                "n_output_parts": report["n_output_parts"],
                "measure_census": report["measure_census"],
                "exact_duplication_share": report["exact_duplication_share"],
                "divisi_share": report["divisi_share"],
            }
        except Exception as exc:                       # noqa: BLE001
            rec["normalise"] = {"accepted": False,
                                "error": f"{type(exc).__name__}: {exc}"}

        # 4. is the fold target arbitrary?
        if absent and rec["normalise"].get("accepted"):
            alt = [dict(s, parts=[i for i in s["parts"] if i not in absent])
                   for s in flat]
            # put every absent part on the LAST entry instead of wherever the
            # candidate put it
            alt[-1] = dict(alt[-1], parts=alt[-1]["parts"] + absent)
            a_xml = HERE / "_tmp" / f"{rid}.a.musicxml"
            b_xml = HERE / "_tmp" / f"{rid}.b.musicxml"
            a_xml.parent.mkdir(parents=True, exist_ok=True)
            page_normalise.write(truth, flat, a_xml)
            page_normalise.write(truth, alt, b_xml)
            a = _content(a_xml)
            b = _content(b_xml)
            rec["fold_target_control"] = {
                "moved_absent_to": alt[-1]["name"],
                "identical_content": a == b,
                "n_parts_a": len(a), "n_parts_b": len(b),
            }
        rows.append(rec)
        print(json.dumps(rec, indent=1, ensure_ascii=False))

    OUT.write_text(json.dumps({"rows": rows}, indent=1,
                              ensure_ascii=False) + "\n")
    print("wrote", OUT)
    return 0


def _content(xml: Path):
    """Per-part sounding content, order-independent within a part."""
    sc = converter.parse(str(xml))
    out = []
    for p in sc.parts:
        toks = []
        for el in p.recurse().notesAndRests:
            if isinstance(el, note.Rest):
                toks.append(("R", float(el.duration.quarterLength)))
            elif isinstance(el, chord.Chord):
                toks.append((tuple(sorted(x.nameWithOctave for x in el.pitches)),
                             float(el.duration.quarterLength)))
            elif isinstance(el, note.Note):
                toks.append(((el.pitch.nameWithOctave,),
                             float(el.duration.quarterLength)))
            else:   # Unpitched — the one-line percussion parts
                toks.append((("UNPITCHED",),
                             float(el.duration.quarterLength)))
        out.append(tuple(toks))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
