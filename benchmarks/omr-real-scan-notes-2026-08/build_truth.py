"""Written-pitch truth for the 1:1 parts of one scanned page — or nothing at all.

    python3 benchmarks/omr-real-scan-notes-2026-08/build_truth.py --page beet5-p2

Reads the Gradus MusicXML for the work, takes the parts that own a printed
staff by themselves over the page's bar range, and writes `truth/<page>.json`.

WHY THIS REFUSES MORE OFTEN THAN IT WRITES
------------------------------------------
Everything this benchmark reports is a fraction whose denominator comes from
here. Two things can silently poison it, and each has its own guard:

  CONDENSATION.  A printed score puts Flute 1 and Flute 2 on one staff while
  the MusicXML keeps them as two parts, so unioning them over-counts that
  staff. A prior attempt at a page-level truth set over-counted 7 of 11 staves
  by roughly 28% that way, and had no defensible note ORDER for another 2. So
  only parts that map 1:1 to a staff are scored, the excluded staves are listed
  in `pages.py` with the parts that share them, and this script re-checks the
  1:1 claim against the MusicXML rather than trusting the table.

  THE BAR RANGE.  It is the one input with no independent source: get it wrong
  and the truth is real music, correctly extracted, from the wrong place on the
  page — a number indistinguishable from a good one. `pages.py` records how it
  was read off the scan; this script then asserts it against what the pipeline's
  own Phase 1 makes of the same page, and REFUSES — non-zero exit, no file — if
  they disagree at all. That refusal is the feature. A tripwire you can talk
  past is not a tripwire, so there is deliberately no override flag.

Pitches are WRITTEN pitch, matching the dossier convention: what is printed on
the page is what a reader sees, and `docs/dossier-verification-plan.md` records
that a concert-pitch truth set makes every transposing staff false-flag.
MusicXML stores written pitch plus a `<transpose>`, so this needs no conversion
— but the transposition of every scored part is recorded so the choice stays
visible rather than assumed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from omr_run import layout, load_or_run  # noqa: E402
from pages import DEFAULT_WEIGHTS, gradus_path, page_config  # noqa: E402

TRUTH_DIR = HERE / "truth"


# --------------------------------------------------------------------------
# The tripwire
# --------------------------------------------------------------------------

def check_layout(cfg: dict[str, Any], result: dict[str, Any]) -> tuple[bool, list[str]]:
    """Hand-read page layout vs. what Phase 1 makes of the same page.

    Checks all three of system count, staff count and per-staff measure count,
    because each protects a different assumption: the systems and staves decide
    whether `staff_ordinal` names the instrument the ground-truth table says it
    does, and the measure counts decide whether the pipeline is reading the bars
    that the truth range covers.

    Every staff must match, not the majority. A truth builder should fail
    toward refusing.
    """
    want_systems = cfg["systems"]
    got = layout(result)
    lines: list[str] = []
    ok = True

    lines.append(f"  systems      hand {len(want_systems)}   phase1 {len(got)}"
                 f"   {'ok' if len(got) == len(want_systems) else 'MISMATCH'}")
    if len(got) != len(want_systems):
        return False, lines

    for i, (want_measures, staves) in enumerate(zip(want_systems, got)):
        n_staves = len(staves)
        staves_ok = n_staves == cfg["n_staves"]
        ok &= staves_ok
        lines.append(
            f"  system {i} staves   hand {cfg['n_staves']:>3}   phase1 {n_staves:>3}"
            f"   {'ok' if staves_ok else 'MISMATCH'}")
        distinct = sorted(set(staves))
        measures_ok = distinct == [want_measures]
        ok &= measures_ok
        seen = (str(distinct[0]) if len(distinct) == 1
                else "{" + ",".join(str(d) for d in distinct) + "}")
        lines.append(
            f"  system {i} measures hand {want_measures:>3}   phase1 {seen:>3}"
            f"   {'ok' if measures_ok else 'MISMATCH'}")
        if not measures_ok:
            lines.append(f"      per staff: {staves}")
            lines.extend(_measure_boundaries(result, i))
    return ok, lines


def _measure_boundaries(result: dict[str, Any], system: int,
                        staff: int = 0) -> list[str]:
    """Where Phase 1 put this system's barlines, so a refusal is actionable.

    A miscount is one barline in the wrong place, and printing the cell WIDTHS
    finds it faster than any amount of re-counting: a merged pair shows up as a
    cell about twice its neighbours', a split one as a pair of half-width cells.
    Compare against the scan at the same DPI.
    """
    try:
        staves = result["pages"][0]["systems"][system]["staves"]
        boxes = [m["bbox_page_px"] for m in staves[staff]["measures"]]
    except (KeyError, IndexError, TypeError):
        return ["      (no measure boxes in this run to localise it with)"]
    if not boxes or boxes[0] is None:
        return ["      (no measure boxes in this run to localise it with)"]

    edges = [round(boxes[0][0])] + [round(b[2]) for b in boxes]
    widths = [edges[i + 1] - edges[i] for i in range(len(edges) - 1)]
    return [
        f"      phase1 barlines, system {system} staff {staff} (px @ run dpi):",
        "        " + "  ".join(str(e) for e in edges),
        "      cell widths — a merged pair reads about double its neighbours:",
        "        " + "  ".join(str(w) for w in widths),
    ]


# --------------------------------------------------------------------------
# Truth extraction
# --------------------------------------------------------------------------

def _resolve_part(score: Any, name: str) -> tuple[int, Any]:
    hits = [(i, p) for i, p in enumerate(score.parts) if p.partName == name]
    if not hits:
        raise SystemExit(
            f"part {name!r} not in the Gradus score; it has: "
            + ", ".join(repr(p.partName) for p in score.parts))
    if len(hits) > 1:
        raise SystemExit(f"part name {name!r} is ambiguous ({len(hits)} matches)")
    return hits[0]


def _transposition(part: Any) -> int:
    inst = part.getInstrument(returnDefault=True)
    tr = getattr(inst, "transposition", None)
    if tr is None:
        return 0
    try:
        return int(tr.semitones)
    except (TypeError, ValueError, AttributeError):
        return 0


def part_truth(part: Any, first: int, last: int) -> dict[str, Any]:
    """Written pitches of one part over [first, last], in reading order.

    Chords are expanded to one entry per pitch, matching `part_sequences` in
    `tools/omr/training/end_to_end_eval.py`: counting chord OBJECTS instead
    hides a lot, since one exported "chord" of many pitches would read as a
    single note.
    """
    seq: list[list[Any]] = []
    by_measure: list[dict[str, Any]] = []
    seen = set()
    for m in part.getElementsByClass("Measure"):
        number = m.number
        if number is None or not (first <= number <= last):
            continue
        if number in seen:
            raise SystemExit(f"measure {number} appears twice in {part.partName!r}")
        seen.add(number)
        here: list[list[Any]] = []
        for element in m.flatten().notes:
            ql = float(element.duration.quarterLength)
            for pitch in element.pitches:
                here.append([pitch.nameWithOctave, ql])
        seq.extend(here)
        by_measure.append({"measure": number, "notes": here})

    missing = sorted(set(range(first, last + 1)) - seen)
    if missing:
        raise SystemExit(
            f"{part.partName!r} has no measure(s) {missing} — the bar range is "
            "outside the score")
    return {"sequence": seq, "by_measure": by_measure}


def build(cfg: dict[str, Any]) -> dict[str, Any]:
    from music21 import converter

    src = gradus_path(cfg["work_id"])
    score = converter.parse(str(src))
    first, last = cfg["first_measure"], cfg["last_measure"]

    # Re-derive the 1:1 claim rather than trusting the table: a scored staff
    # must be named by exactly one part, and every part must be accounted for
    # as either scored or explicitly excluded.
    scored_names = [p["gradus_part"] for p in cfg["parts"]]
    excluded_names = [n for e in cfg["excluded_staves"] for n in e["parts"]]
    all_names = [p.partName for p in score.parts]
    unaccounted = [n for n in all_names if n not in scored_names + excluded_names]
    if unaccounted:
        raise SystemExit(
            "these MusicXML parts are neither scored nor excluded in pages.py, "
            "so the page's staves are not fully explained: " + ", ".join(map(repr, unaccounted)))
    overlap = sorted(set(scored_names) & set(excluded_names))
    if overlap:
        raise SystemExit(f"part(s) both scored and excluded: {overlap}")

    parts_out = []
    for spec in cfg["parts"]:
        idx, part = _resolve_part(score, spec["gradus_part"])
        truth = part_truth(part, first, last)
        parts_out.append({
            "gradus_part": spec["gradus_part"],
            "gradus_part_index": idx,
            "printed": spec["printed"],
            "staff_ordinal": spec["staff_ordinal"],
            "transposition_semitones": _transposition(part),
            "n_notes": len(truth["sequence"]),
            **truth,
        })

    ordinals = [p["staff_ordinal"] for p in parts_out]
    if len(set(ordinals)) != len(ordinals):
        raise SystemExit(f"two parts claim the same staff ordinal: {ordinals}")
    if any(o >= cfg["n_staves"] for o in ordinals):
        raise SystemExit(f"staff ordinal out of range for {cfg['n_staves']} staves")

    return {
        "_about": [
            "Written-pitch note sequences for the parts that own one printed "
            "staff by themselves, over the bar range this page covers.",
            "Generated by build_truth.py, which refuses to write this file "
            "unless the hand-read page layout and the pipeline's Phase 1 agree.",
            "Pitch is WRITTEN pitch (what is printed), matching the dossier "
            "convention. Durations are in quarter notes.",
            "This is a scoring reference, NOT training labels: it carries no "
            "positions. The MXL->bounding-box path is closed (F1 0.064, "
            "benchmarks/omr-mxl-autolabel/FINDINGS.md) and this is not it.",
        ],
        "page_id": cfg["id"],
        "work_id": cfg["work_id"],
        "title": cfg["title"],
        "source_musicxml": str(src),
        "pdf": str(cfg["pdf"]),
        "page_index": cfg["page_index"],
        "dpi": cfg["dpi"],
        "measures": {"first": first, "last": last,
                     "per_system": cfg["systems"], "total": sum(cfg["systems"])},
        "bar_range_evidence": cfg["bar_range_evidence"],
        "n_staves": cfg["n_staves"],
        "excluded_staves": cfg["excluded_staves"],
        "total_notes": sum(p["n_notes"] for p in parts_out),
        "parts": parts_out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", default="beet5-p2")
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--fresh", action="store_true",
                    help="re-run the pipeline instead of reusing pipeline-runs/<page>.omr.json")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    cfg = page_config(args.page)
    print(f"page {cfg['id']}: {cfg['title']}")
    print(f"  pdf        {cfg['pdf']}  page_index {cfg['page_index']} @ {cfg['dpi']} dpi")
    print(f"  hand-read  mm.{cfg['first_measure']}-{cfg['last_measure']} "
          f"({sum(cfg['systems'])} bars over {len(cfg['systems'])} systems "
          f"{cfg['systems']}), {cfg['n_staves']} staves per system")

    print("\nTRIPWIRE — hand-read layout vs. pipeline Phase 1")
    result, run_file, cached = load_or_run(cfg, weights=args.weights, fresh=args.fresh)
    print(f"  run        {run_file}{' (cached)' if cached else ''}")
    ok, lines = check_layout(cfg, result)
    print("\n".join(lines))

    if not ok:
        print("\nREFUSED. The page this benchmark believes it is scoring and the "
              "page Phase 1 reports are not the same page.")
        print("No truth file was written. A wrong bar range produces a score "
              "indistinguishable from a real one, so this is a stop, not a warning.")
        print("Resolve it by re-reading the scan (pages.py records how the bar "
              "range was established) or by fixing Phase 1 — not by editing the "
              "hand count to match the pipeline, which would make the benchmark "
              "measure agreement with itself.")
        return 1

    print("  -> layout agrees; building truth")
    truth = build(cfg)

    out = args.out or (TRUTH_DIR / f"{cfg['id']}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(truth, indent=2) + "\n")

    print(f"\n{'part':22s} {'staff':>5s} {'transp':>6s} {'notes':>6s}")
    for p in truth["parts"]:
        print(f"{p['printed']:22s} {p['staff_ordinal']:>5d} "
              f"{p['transposition_semitones']:>6d} {p['n_notes']:>6d}")
    print(f"{'TOTAL':22s} {'':>5s} {'':>6s} {truth['total_notes']:>6d}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
