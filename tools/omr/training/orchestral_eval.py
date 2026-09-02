"""End-to-end accuracy on REAL orchestral music, with truth that costs nothing.

`end_to_end_eval` measures the pipeline against three hand-authored fixtures:
one staff, two staves, four staves. That was the right first baseline, but it
tops out well below the texture this project actually exists for, and the
handoff notes that `ensemble` exists only because a lone staff is a different
problem from an ensemble one. Nothing measured a conductor's page.

The Gradus score library has ~97 orchestral movements as MusicXML — Beethoven
1-9, Brahms 1-4, Bruckner 5, Dvorak 9, Mahler 5, Mozart 40/41, Tchaikovsky 4/6,
Boléro. Rendering an excerpt of one back to PDF gives a dense orchestral page
whose every note is known exactly, for free, at eighteen staves.

ELEVEN OF THEM SINCE 2026-09-02, three before that — see
`accuracy_record.BENCHMARK_WORKS`, which is where the set and the reasons for it
live. A default run needs no flags and no fixtures on disk: every fixture is
regenerated from the score library by `excerpt()` below, into `--work-dir`.

    python3 -m tools.omr.training.orchestral_eval --works beethoven-sym5-mvt1
    python3 -m tools.omr.training.orchestral_eval --measures 1-8 --out after.json

WHAT THIS DOES AND DOES NOT MEASURE. The input is ENGRAVED, not scanned: no
foxing, no bleed-through, no skew, no broken staff lines. So a failure here is
a failure of recognition on dense music, and cannot be blamed on print quality
— which is exactly the confound that makes the orchestral numbers elsewhere in
this repository hard to read. It says nothing about scan robustness. Both
matter; this isolates one.

It also runs the dossier checks on the result, so the same command reports how
many disagreements the external-truth layer catches on a page whose true
content is known.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import fitz
from music21 import converter, expressions

from tools.omr import accuracy_record
from tools.omr.dossier import find_dossier, summarize
from tools.omr.export import to_musicxml
from tools.omr.training.end_to_end_eval import (
    DEFAULT_WEIGHTS,
    align,
    part_sequences,
    structure,
)
from tools.omr.transcribe import transcribe

ROOT = Path(__file__).resolve().parents[3]
BENCH_DIR = ROOT / "benchmarks" / "omr-orchestral-e2e"
SCORE_DIR = Path("/Users/seanjohnson/Desktop/gradus-vercel/public/scores")

# Kept small on purpose: an eighteen-part excerpt of even a few bars fills a
# page, and the point is density per page, not length.
DEFAULT_MEASURES = (1, 8)

#: The works a default run covers — ELEVEN since 2026-09-02, three before it.
#:
#: The list itself lives in `accuracy_record`, next to the record it defines,
#: because it is the benchmark's DEFINITION and not merely this script's
#: default: a pooled figure is a property of the work set it is pooled over, so
#: the two must be able to disagree with each other loudly and cannot be two
#: copies. `accuracy_record.check()` refuses a record whose stamp names a
#: different set. The per-work rationale is there too.
#:
#: `--works` still takes any work_id that has a dossier — including
#: `boulanger-printemps-mvt1`, which is deliberately not in the pooled set.
DEFAULT_WORKS = accuracy_record.BENCHMARK_WORKS


# ---------------------------------------------------------------------------
# Does the page carry what the truth claims?
# ---------------------------------------------------------------------------
#
# The fixture's contract is that every symbol is known by construction, because
# the page IS the truth, rendered. `musicxml2ly` quietly breaks that: on the
# Beethoven excerpt the truth carries 36 fermatas — 22 of them over rests — and
# the LilyPond it produces carries 14, all over notes. Not one of the 22 rest
# fermatas reaches the page.
#
# The cost is not the 22 symbols. Each of those bars holds nothing but a rest,
# so the fermata is the only thing distinguishing it, and musicdiff charges a
# whole-bar delete plus a whole-bar insert: **105 edits on the Beethoven page,
# for ink that was never printed.** A perfect reader is charged them too. That
# is a floor built into the instrument, and it went unnoticed for a day of work
# on the bucket it dominates.
#
# FIXED 2026-09-02 by COMPLETING THE RENDER, not by shrinking the truth. The
# truth is what the work IS — the fermatas over those rests are printed in
# every real edition of Beethoven 5, and a reader should be asked to read them
# — so the fixture pipeline restores what `musicxml2ly` dropped instead of
# deleting it from the truth. `_restore_rest_fermatas` re-reads the truth's
# fermata-on-rest measures and splits the generated `R2*8` runs to attach
# `\fermata` at exactly those bars (LilyPond ≥ 2.22 takes an articulation on a
# multi-measure rest directly). Every historical pooled figure predates this
# and carries a ~105-edit floor the current figures do not — see the
# discontinuity note beside the fix table in docs/next-steps-omr-2026-09-01.md.
#
# `render_shortfall` stays as the guard: it counts truth-vs-render occurrences
# on every run, so if the restoration ever breaks — or musicxml2ly drops
# something new — the run says so instead of silently re-growing the floor.

#: (name, how it appears in the truth XML, how it appears in the LilyPond).
#: Only symbols actually measured to go missing belong here — a speculative
#: entry would raise a warning nobody can act on.
RENDER_DROPS = (("fermata", "<fermata", "\\fermata"),)


def rest_fermata_ordinals(score) -> dict[int, list[int]]:
    """part index -> 1-based measure ordinals (within the excerpt) whose
    whole-measure rest carries a fermata.

    Ordinals count measures of the excerpt in order rather than trusting
    `Measure.number`, because the LilyPond side counts the same way and the two
    must agree by construction, pickup numbering conventions notwithstanding.
    """
    out: dict[int, list[int]] = {}
    for p_idx, part in enumerate(score.parts):
        for ordinal, meas in enumerate(part.getElementsByClass("Measure"),
                                       start=1):
            for rest in meas.recurse().getElementsByClass("Rest"):
                if any(isinstance(e, expressions.Fermata)
                       for e in rest.expressions):
                    out.setdefault(p_idx, []).append(ordinal)
                    break
    return out


# One VoiceOne block per part, in part order. The name must END in VoiceOne so
# `PartPOneFourVoiceOneLyricsOne` (a lyrics block) and `...VoiceTwo` (a second
# voice, which would print a duplicate mark) never match.
_PART_BLOCK_RE = re.compile(r"^Part\w*VoiceOne\s*=", re.M)

# A whole-measure rest run (`R2`, `R2*8`, `R2.`, `R1*3/4`, `R1*3/4*2`) or a bar
# check. Only uppercase-R runs advance by their count; a bar check advances by
# one unless a run in the same segment already did.
_MEASURE_EVENT_RE = re.compile(
    r"(?P<run>\bR(?P<dur>\d+\.*)(?P<frac>\*\d+/\d+)?(?:\*(?P<count>\d+)(?!\s*/))?)"
    r"|(?P<bar>\|)"
)

_BAR_COMMENT_RE = re.compile(r"[ \t]*%[ \t]*(\d+)")


def _matching_brace(text: str, open_pos: int) -> int:
    """Index of the `}` closing the `{` at `open_pos`."""
    depth = 0
    for i in range(open_pos, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise RuntimeError("unbalanced braces in generated LilyPond")


def _take_markup_postfix(body: str, pos: int) -> tuple[str, int]:
    """Consume `^\\markup { … }` groups attached after a rest run.

    A split run must keep such an attachment on its FIRST piece — the tempo
    text over Flute 1's `R2*8` belongs to bar 1, and leaving it after the last
    piece would silently move it to bar 6.
    """
    taken = ""
    while True:
        m = re.match(r"\s*[\^_-]\s*\\markup\s*(?=\{)", body[pos:])
        if not m:
            return taken, pos
        brace_open = pos + m.end()
        brace_close = _matching_brace(body, brace_open)
        taken += body[pos:brace_close + 1]
        pos = brace_close + 1


def _patch_block(body: str, ordinals: list[int]) -> str:
    """Attach `\\fermata` to the whole-measure rests at `ordinals` (1-based)."""
    runs: list[tuple[int, int, re.Match]] = []
    measure = 1
    advanced_by_run = False
    anchored = False
    for m in _MEASURE_EVENT_RE.finditer(body):
        if m.group("bar"):
            if advanced_by_run:
                advanced_by_run = False
            else:
                measure += 1
            # `| % n` names the measure ABOUT TO START, and musicxml2ly puts
            # one on every bar check — including one at the end of the header
            # (`\key es \major | % 1`), which is why the counter cannot simply
            # advance on `|`: that check precedes measure 1. So the FIRST
            # comment anchors the counter, and every later one must agree —
            # any drift means a bar check was missed and a fermata would land
            # on the wrong bar, which must fail loudly, not quietly.
            c = _BAR_COMMENT_RE.match(body, m.end())
            if c:
                n = int(c.group(1))
                if not anchored:
                    measure = n
                    anchored = True
                elif measure != n:
                    raise RuntimeError(
                        f"measure count drifted: bar comment says {n}, "
                        f"counter says {measure}"
                    )
        else:
            count = int(m.group("count") or 1)
            runs.append((measure, measure + count - 1, m, anchored))
            measure += count
            advanced_by_run = True

    if ordinals and not anchored:
        raise RuntimeError(
            "no `| % n` bar-number comments to anchor the measure count — "
            "refusing to guess where the fermata bars fall"
        )
    edits: list[tuple[int, int, str]] = []
    for a, b, m, run_anchored in runs:
        targets = [t for t in ordinals if a <= t <= b]
        if not targets:
            continue
        if not run_anchored:
            raise RuntimeError(
                f"a fermata bar ({targets}) falls in a rest run seen before "
                "the first bar-number comment — its span cannot be trusted"
            )
        base = f"R{m.group('dur')}{m.group('frac') or ''}"

        def piece(x: int, y: int) -> str:
            return base if x == y else f"{base}*{y - x + 1}"

        parts: list[str] = []
        pos = a
        for t in targets:
            if t > pos:
                parts.append(piece(pos, t - 1))
            parts.append(base + "\\fermata")
            pos = t + 1
        if pos <= b:
            parts.append(piece(pos, b))
        postfix, end = _take_markup_postfix(body, m.end())
        parts[0] += postfix
        edits.append((m.start(), end, " ".join(parts)))

    placed = sum(1 for a, b, m, _ in runs for t in ordinals if a <= t <= b)
    if placed != len(ordinals):
        raise RuntimeError(
            f"could not place every rest fermata: wanted bars {ordinals}, "
            f"whole-measure rest runs cover {[(a, b) for a, b, _, _ in runs]}"
        )
    for start, end, replacement in sorted(edits, reverse=True):
        body = body[:start] + replacement + body[end:]
    return body


def _restore_rest_fermatas(ly_text: str,
                           targets: dict[int, list[int]],
                           n_parts: int) -> str:
    """Re-attach the fermatas `musicxml2ly` drops from whole-measure rests."""
    blocks = list(_PART_BLOCK_RE.finditer(ly_text))
    if len(blocks) != n_parts:
        raise RuntimeError(
            f"found {len(blocks)} VoiceOne part blocks for {n_parts} parts — "
            "the part->block mapping is positional and cannot be trusted here"
        )
    spans: list[tuple[int, int, int]] = []  # (body_start, body_end, part_idx)
    for p_idx, m in enumerate(blocks):
        if p_idx not in targets:
            continue
        open_pos = ly_text.index("{", m.end())
        close_pos = _matching_brace(ly_text, open_pos)
        spans.append((open_pos + 1, close_pos, p_idx))
    for body_start, body_end, p_idx in sorted(spans, reverse=True):
        patched = _patch_block(ly_text[body_start:body_end],
                               sorted(targets[p_idx]))
        ly_text = ly_text[:body_start] + patched + ly_text[body_end:]
    return ly_text


def render_shortfall(truth_xml: Path, ly: Path) -> list[tuple[str, int, int]]:
    """`(symbol, in_truth, in_render)` for anything the render lost."""
    try:
        xml_text, ly_text = truth_xml.read_text(), ly.read_text()
    except OSError:
        return []
    out = []
    for name, xml_pat, ly_pat in RENDER_DROPS:
        in_truth, in_render = xml_text.count(xml_pat), ly_text.count(ly_pat)
        if in_render < in_truth:
            out.append((name, in_truth, in_render))
    return out


def excerpt(work_id: str, first: int, last: int,
            out_dir: Path) -> tuple[Path, Path, int]:
    """Write `<work>.musicxml` (the truth) and `<work>.pdf` (the input).

    Returns `(truth_xml, pdf, last_measure_used)` — see the page-fitting note
    inside.
    """
    src = None
    for suffix in (".mxl", ".musicxml"):
        candidate = SCORE_DIR / f"{work_id}{suffix}"
        if candidate.is_file():
            src = candidate
            break
    if src is None:
        raise FileNotFoundError(f"no score for {work_id} under {SCORE_DIR}")

    out_dir.mkdir(parents=True, exist_ok=True)
    parsed = converter.parse(str(src))
    n_parts = len(parsed.parts)

    # THE EXCERPT MUST FIT ON ONE PAGE, and that is not a cosmetic preference.
    # `export.to_musicxml` emits one <part> per (page, system, staff), so a part
    # is NOT continuous across a page break: transcribing three pages of a
    # 21-staff score yields 63 parts, not 21 parts three times as long. Scoring
    # a multi-page render therefore measures the exporter's page handling rather
    # than recognition, and scoring only page 0 against the FULL excerpt's truth
    # silently caps recall at the fraction of the music that landed on it —
    # which is what an 8-measure Brahms excerpt spanning 3 pages was doing.
    #
    # So shrink the range until LilyPond gives back a single page, and take the
    # truth from exactly that range. The number of measures actually used is
    # returned so the report can say what was measured.
    last_used = last
    while last_used >= first:
        score = parsed.measures(first, last_used)
        xml = out_dir / f"{work_id}.musicxml"
        score.write("musicxml", fp=str(xml))

        ly = out_dir / f"{work_id}.ly"
        subprocess.run(["musicxml2ly", "-o", str(ly), str(xml)],
                       check=True, capture_output=True)
        src_ly = ly.read_text()
        src_ly = src_ly.replace("\\header {", "\\header {\n  tagline = ##f")
        # Put back what musicxml2ly dropped, so the page carries what the
        # truth claims — see the RENDER_DROPS note above.
        rest_fermatas = rest_fermata_ordinals(score)
        if rest_fermatas:
            src_ly = _restore_rest_fermatas(src_ly, rest_fermatas,
                                            n_parts=n_parts)
        # PAPER MUST BE SIZED TO THE SCORE, and getting this wrong invalidates
        # the whole measurement. Rendering a 38-part Mahler page on A4 leaves
        # LilyPond ~1.0 staff-space between staves — the page becomes one
        # continuous ladder of evenly spaced lines with no visible boundary
        # between one staff and the next, which no staff detector can segment
        # and which real engraving never does. Measured on that excerpt:
        #
        #     paper   staves found   ambiguous ladders   inter-staff gap
        #     a4         31 / 38            5              1.0 spaces
        #     a3         38 / 38            0              1.8 spaces
        #     a2         38 / 38            0              4.3 spaces
        #
        # So the "staff phasing" failure that made Mahler look catastrophic was
        # an artifact of this fixture, not of the pipeline. Scale the sheet with
        # the part count instead.
        paper = "a4" if n_parts <= 20 else ("a3" if n_parts <= 40 else "a2")
        # A conductor's score is engraved small; 16pt is where real orchestral
        # prints sit.
        src_ly = (f'#(set-default-paper-size "{paper}")\n'
                  "#(set-global-staff-size 16)\n") + src_ly
        ly.write_text(src_ly)
        subprocess.run(["lilypond", "-s", "-o", work_id, f"{work_id}.ly"],
                       cwd=out_dir, check=True, capture_output=True)
        pdf = out_dir / f"{work_id}.pdf"
        with fitz.open(pdf) as doc:
            n_pages = doc.page_count
        if n_pages == 1 or last_used == first:
            return xml, pdf, last_used, ly
        last_used -= 1
    raise RuntimeError(f"{work_id}: could not fit any excerpt on one page")


def run_work(work_id: str, *, first: int, last: int, work_dir: Path,
             weights: str, dpi: int | None, use_dossier: bool,
             direction_text: bool = False) -> dict[str, Any]:
    truth_xml, pdf, last_used, ly = excerpt(work_id, first, last, work_dir)
    dossier = find_dossier(work_id) if use_dossier else None

    # dpi=None takes `transcribe`'s default rather than restating it here.
    opts = {"dpi": dpi} if dpi is not None else {}
    result = transcribe(pdf_path=pdf, pages=[0], weights=weights,
                        dossier=dossier, progress=False,
                        read_direction_text=direction_text, **opts)
    omr_xml = work_dir / f"{work_id}.omr.musicxml"
    omr_xml.write_text(to_musicxml(result))
    # The transcription itself, beside the export. Every attribution pass so far
    # has had to re-run the pipeline to see a detection — a page takes minutes,
    # so the analysis gets written against a run that is not the one being
    # scored. The fixtures directory is gitignored scratch, so keeping the JSON
    # costs nothing and makes the next diagnosis offline and exact.
    (work_dir / f"{work_id}.omr.json").write_text(
        json.dumps(result, default=str) + "\n"
    )

    page = result["pages"][0]
    truth_struct = structure(truth_xml)
    omr_struct = structure(omr_xml)
    scores = align(part_sequences(truth_xml), part_sequences(omr_xml))

    return {
        "work_id": work_id,
        "measures": [first, last_used],
        # Kept so `--omr-ned` can score the pair after every work has run: the
        # pooled OMR-NED is only meaningful over the whole set, so it cannot be
        # computed here one work at a time.
        "truth_xml": str(truth_xml),
        "omr_xml": str(omr_xml),
        "truth": truth_struct,
        "omr": omr_struct,
        "detected": {
            "systems": len(page["systems"]),
            "staves": sum(len(s["staves"]) for s in page["systems"]),
        },
        "notes": scores,
        "rhythm_reconciliations": result.get("n_rhythm_reconciliations", 0),
        "dossier_warnings": summarize(result.get("dossier_warnings", [])),
        "dossier_used": dossier is not None,
        # Symbols the truth claims that the render never put on the page. See
        # `render_shortfall` — these are charged to us and are unreachable.
        "render_shortfall": render_shortfall(truth_xml, ly),
        "direction_text": result.get("direction_text"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--works", nargs="+", default=list(DEFAULT_WORKS))
    ap.add_argument("--measures", default=f"{DEFAULT_MEASURES[0]}-{DEFAULT_MEASURES[1]}",
                    help="measure range of the excerpt, e.g. 1-8")
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--dpi", type=int, default=None,
                    help="override the pipeline default")
    ap.add_argument("--no-dossier", action="store_true",
                    help="run without the dossier, to measure what it adds")
    ap.add_argument("--direction-text", action="store_true",
                    help="read the words printed inside each system with "
                         "Surya and export them as MusicXML <words> — the "
                         "`wrong direction` category, 151 of the 1715 pooled "
                         "edits at the 0.2449 baseline. Needs .venv-surya.")
    ap.add_argument("--work-dir", type=Path, default=BENCH_DIR / "fixtures")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--omr-ned", action="store_true",
                    help="also score each pair with OMR-NED, the Sheet Music "
                         "Benchmark metric, so the result is comparable to "
                         "published numbers (needs `python3 -m tools.omr.omr_ned "
                         "--bootstrap` once)")
    ap.add_argument("--record", action="store_true",
                    help="write the measured figure to the accuracy record and "
                         "into CLAUDE.md — the ONLY way a present-tense figure "
                         "should reach a document. Needs --omr-ned. See "
                         "tools/omr/accuracy_record.py")
    ap.add_argument("--omr-ned-detail", default="AllObjects",
                    help="musicdiff DetailLevel; NotesAndRests restricts the "
                         "score to pitch and rhythm, which is the closest "
                         "comparison to the note recall reported above")
    args = ap.parse_args(argv)

    first, _, last = args.measures.partition("-")
    first, last = int(first), int(last or first)

    header = (f"{'work':22s} {'bars':>5s} {'parts':>11s} {'measures':>10s} "
              f"{'notes':>12s} {'recall':>7s} {'prec':>6s} {'dur':>6s}  dossier")
    print(header)
    results = []
    # An enrichment that failed like a DEFECT, as opposed to abstaining. Kept
    # so the run can end non-zero: a benchmark that quietly measures a pipeline
    # with a documented pass broken is worse than one that refuses to report.
    broken_passes: list[tuple[str, str, str | None]] = []
    for work_id in args.works:
        try:
            r = run_work(work_id, first=first, last=last, work_dir=args.work_dir,
                         weights=args.weights, dpi=args.dpi,
                         use_dossier=not args.no_dossier,
                         direction_text=args.direction_text)
        except Exception as exc:  # noqa: BLE001 — one bad work must not stop the run
            print(f"{work_id:22s} FAILED: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            continue
        results.append(r)
        n = r["notes"]
        ctx = r.get("contextual") or {}
        if ctx.get("looks_like_a_bug"):
            broken_passes.append((work_id, "contextual", ctx.get("reason")))
        elif not ctx.get("available", True):
            print(f"{'':22s} note: contextual unavailable — "
                  f"{ctx.get('reason')}", file=sys.stderr)
        flags = r["dossier_warnings"]
        used = r["measures"][1] - r["measures"][0] + 1
        print(f"{work_id:22s} {used:>5d} "
              f"{r['omr']['parts']:>5d}/{r['truth']['parts']:<5d} "
              f"{r['omr']['measures']:>4d}/{r['truth']['measures']:<5d} "
              f"{n['omr_notes']:>5d}/{n['truth_notes']:<6d} "
              f"{n['pitch_recall']:>7.3f} {n['pitch_precision']:>6.3f} "
              f"{n['duration_rate']:>6.3f}  "
              + (", ".join(f"{k.replace('dossier_', '')}={v}"
                           for k, v in sorted(flags.items())) or "clean"))

    if args.omr_ned and results:
        # Imported here so the benchmark still runs with no musicdiff venv.
        from tools.omr import omr_ned as omr_ned_mod

        pairs = [(r["work_id"], r["omr_xml"], r["truth_xml"]) for r in results]
        try:
            scored = omr_ned_mod.score_batch(pairs, detail=args.omr_ned_detail)
        except omr_ned_mod.OmrNedError as exc:
            print(f"\nOMR-NED unavailable: {exc}", file=sys.stderr)
        else:
            by_name = {p["name"]: p for p in scored.get("pairs", [])}
            for r in results:
                r["omr_ned"] = by_name.get(r["work_id"])
            print()
            print(omr_ned_mod.format_report(scored))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {args.out}")

    if args.record:
        ar = accuracy_record

        # Each refusal is a way the record would state a figure for the whole
        # benchmark that is not one.
        if not args.omr_ned:
            print("\n--record needs --omr-ned", file=sys.stderr)
            return 1
        if broken_passes:
            print("\n--record refused: a pipeline pass failed, so these numbers "
                  "are not what the pipeline does", file=sys.stderr)
            return 1
        if set(args.works) != set(DEFAULT_WORKS):
            missing = sorted(set(DEFAULT_WORKS) - set(args.works))
            extra = sorted(set(args.works) - set(DEFAULT_WORKS))
            print(f"\n--record refused: the record is the figure for the whole "
                  f"benchmark, which is {len(DEFAULT_WORKS)} works, and this "
                  f"run covered {len(set(args.works))}"
                  + (f"; missing {missing}" if missing else "")
                  + (f"; not in the benchmark: {extra}" if extra else ""),
                  file=sys.stderr)
            return 1
        # A work that FAILED is silently absent from `results`, and the pooled
        # figure over what survived would be recorded as the benchmark's.
        if {r["work_id"] for r in results} != set(DEFAULT_WORKS):
            failed = sorted(set(DEFAULT_WORKS) - {r["work_id"] for r in results})
            print(f"\n--record refused: {failed} did not produce a result, so "
                  "the pooled figure would cover less than the benchmark",
                  file=sys.stderr)
            return 1
        run_name = (ar.DIRECTION_TEXT_RUN if args.direction_text
                    else ar.DEFAULT_RUN)
        previous = ar.load_record() if ar.RECORD_PATH.is_file() else None
        record = ar.record_from_results(results, run_name=run_name,
                                        previous=previous)
        ar.RECORD_PATH.parent.mkdir(parents=True, exist_ok=True)
        ar.RECORD_PATH.write_text(json.dumps(record, indent=2) + "\n")
        changed = ar.update(record)
        run = record["runs"][run_name]
        print(f"\nrecorded {run_name}: pooled {run['pooled']:.4f} on "
              f"{run['commit']}"
              + (f"; rewrote {', '.join(changed)}" if changed else
                 "; CLAUDE.md already agreed"))

    shortfalls = [(r["work_id"], r.get("render_shortfall") or []) for r in results]
    shortfalls = [(w, sf) for w, sf in shortfalls if sf]
    if shortfalls:
        print("\nUNREACHABLE BY CONSTRUCTION — the truth carries symbols its own\n"
              "render never drew, so these are charged to us and cannot be read:")
        for work_id, sf in shortfalls:
            for name, in_truth, in_render in sf:
                print(f"  {work_id}: {in_truth - in_render} of {in_truth} "
                      f"{name}s are in the truth but not on the page")

    if broken_passes:
        print("\nBROKEN, not abstaining — these are defects and the numbers "
              "above were measured without them:", file=sys.stderr)
        for work_id, pass_name, reason in broken_passes:
            print(f"  {work_id}: {pass_name}: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
