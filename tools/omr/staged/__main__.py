"""CLI for the staged pipeline.

    # the three stages on a real PDF, with weights
    python3 -m tools.omr.staged score.pdf --pages 0-2 \
        --weights omr-weights/<file>.pt --out staged.json

    # no weights: every cell abstains READER_UNAVAILABLE and it still runs
    python3 -m tools.omr.staged score.pdf --pages 0

    # a FILE, plus the record of what did not reach it
    python3 -m tools.omr.staged score.pdf --pages 0 --weights <...> \
        --musicxml out.musicxml

    # MusicXML AND LilyPond from one gather, ROADMAP 3.1
    python3 -m tools.omr.staged score.pdf --pages 0 --weights <...> \
        --musicxml out.musicxml --lilypond out.ly

    # the A/B: compare against a legacy transcribe result
    python3 -m tools.omr.staged score.pdf --pages 0-2 --weights <...> \
        --against legacy.omr.json

⚠️ THIS RUNS NO BENCHMARK AND SCORES NOTHING. The divergence table is a
POPULATION, not a result: every `differ` row needs a human against the print
before it is a win or a loss.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional


def parse_pages(spec: str) -> list:
    out = []
    for part in (spec or "0").split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


#: ⚠️ ARGUMENTS THAT CHANGE WHERE THE OUTPUT GOES, NOT WHAT IT SAYS -- and
#: this is an EXCLUDE list on purpose. An INCLUDE list would silently drop a
#: new reading-affecting argument the day someone adds one, which is the
#: hand-list drift this repo keeps paying for; excluding means a new argument
#: is captured by DEFAULT and only a deliberate entry here opts it out.
#: ⚠️⚠️ `out` MUST be excluded or the guard it feeds becomes USELESS: two arms
#: of one A/B always write to different files, so including it would make
#: every pair look like a different configuration and
#: `regather_control.check_provenance` would accept a record compared with
#: itself -- the exact trap that guard exists to catch.
#: ⚠️ `pdf_out`, NOT `pdf` -- the positional `pdf` argument is the INPUT
#: score, and belongs in the settings stamp like any other reading-affecting
#: argument; only the NEW `--pdf` output flag (below, `dest="pdf_out"` for
#: exactly this reason -- argparse would otherwise collide it with the
#: positional) is output-only.
_OUTPUT_ONLY_ARGS = ("out", "musicxml", "lilypond", "pdf_out", "progress")


def _settings(args: Any = None) -> dict:
    """THE CONFIGURATION this record was built under, beside the tree.

    ⚠️⚠️ **THE COMMIT DOES NOT NAME THE CONFIGURATION, AND THIS COST A
    SESSION A RUN.** `_provenance` names the TREE and argues, correctly, that
    *anything that cannot uniquely name a tree must never compare equal to
    anything, including itself*. On a FLAG-DRIVEN pipeline that is not enough:
    two records from one clean commit with different `OMR_*` settings differ
    in content and were stamped IDENTICALLY. On 2026-09-17 a session could
    only recover an earlier run's flags by reverse-engineering them from the
    output -- 7,093 ink rows implying `OMR_INK`, an `out_of_scope` abstention
    count implying the scan gate -- and that worked only because those two
    happen to leave a trace. **A flag that changes a VALUE rather than a
    row's existence leaves none**, which is every meter flag.

    ⚠️ **ONLY THE OVERRIDES ARE NEEDED, and that is what makes this complete
    without enumerating anything.** A flag's DEFAULT is a property of the
    commit, which is already stamped -- so `commit` + the environment
    overrides + the arguments together determine the configuration, with no
    flag roster to drift. Sean, 2026-09-17, on why it is worth stamping:
    *"Settings are important because those will be things we can tweak later
    on."*

    ⚠️ `OMR_`-prefixed variables ONLY. Stamping the whole environment would
    put credentials (`ANTHROPIC_API_KEY`) into every record.
    """
    env = {k: v for k, v in sorted(os.environ.items())
           if k.startswith("OMR_")}
    out: dict = {"env_overrides": env}
    if args is not None:
        out["args"] = {k: v for k, v in sorted(vars(args).items())
                       if k not in _OUTPUT_ONLY_ARGS}
    return out


def _provenance() -> dict:
    """The commit this record was built from, and whether the tree was dirty.

    ⚠️ Best-effort and NEVER fatal: a record that cannot name its tree is
    still a valid record, and refusing to write one would trade a real
    transcription for a metadata nicety. It is the CONSUMER's job to refuse an
    unstamped comparison, which is where the decision belongs -- writing is
    not the place that can be wrong about it.
    """
    import subprocess
    here = str(Path(__file__).resolve().parent)

    def git(*args):
        # ⚠️ `check_output`, NEVER `subprocess.run` without `check=True`: run
        # returns a non-zero exit as EMPTY STDOUT WITH NO EXCEPTION, so
        # outside a git checkout the id would be `""` -- and two empty stamps
        # compare EQUAL. The meter session hit exactly that in its own guard.
        return subprocess.check_output(
            ["git", *args], stderr=subprocess.DEVNULL, cwd=here).decode().strip()

    out = {"commit": None, "dirty": None}
    try:
        # ⚠️⚠️ THE TWO FACTS ARE ATOMIC, AND THAT IS THE WHOLE POINT. An
        # earlier version set `commit` first and `dirty` second inside one
        # `try`, so a `git status` that failed left a record claiming a COMMIT
        # with dirtiness UNKNOWN -- and a consumer reading `dirty` as falsy
        # would call that tree CLEAN. A half-named tree is not a named tree.
        #
        # The general rule, from the meter session generalising my own dirty
        # rule back at me: ANYTHING THAT CANNOT UNIQUELY NAME A TREE MUST
        # NEVER COMPARE EQUAL TO ANYTHING, INCLUDING ITSELF. So both fields
        # are set together or neither is, and `None` is the only failure
        # value -- no magic string like "unknown", which two failing machines
        # would share.
        commit = git("rev-parse", "HEAD")
        dirty = bool(git("status", "--porcelain"))
        out["commit"], out["dirty"] = commit, dirty
    except Exception as exc:                       # noqa: BLE001
        out = {"commit": None, "dirty": None,
               "error": f"{type(exc).__name__}: {exc}"}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="The staged pipeline: GATHER -> ADJUDICATE -> EVALUATE")
    ap.add_argument("pdf")
    ap.add_argument("--pages", default="0")
    ap.add_argument("--weights", default=None,
                    help="A real path PINS the model, exactly as before. "
                         "Omit entirely to run with no detector at all -- "
                         "every cell abstains and the pipeline still "
                         "completes -- UNCHANGED by --route-weights below: "
                         "routing is an explicit request, never triggered "
                         "by mere absence, because the legacy CLI's own "
                         "'omit means route' convention would ask a "
                         "no-weights run (a cheap test, a cloud session "
                         "with no omr-weights/) to load a file that is not "
                         "there. Pass the literal string 'auto' to route.")
    ap.add_argument("--route-weights", action="store_true",
                    help="roadmap 3.2 (staged), mirroring the legacy CLI's "
                         "long-shipped default: with --weights omitted or "
                         "set to 'auto', classify the PDF's own domain "
                         "(input_domain.classify_pdf_domain, imported "
                         "rather than restated) and pick the scan- or "
                         "engraved-tuned checkpoint accordingly, recording "
                         "the verdict as `weight_routing` on the record. "
                         "Has no effect when --weights names a real file: "
                         "an explicit path always pins and never routes.")
    ap.add_argument("--no-weight-routing", action="store_true",
                    help="force OFF even where --route-weights (or "
                         "'--weights auto') was given -- the same escape "
                         "OMR_WEIGHT_ROUTING=0 is on the legacy path. Falls "
                         "back to the default (scan-tuned) weights with no "
                         "classification, never to no-detector.")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--against", default=None,
                    help="a legacy transcribe result JSON, for the divergence "
                         "table")
    ap.add_argument("--musicxml", default=None,
                    help="also EXPORT the run to MusicXML here. The coverage "
                         "report -- what the record could NOT carry -- goes "
                         "beside it as <path>.coverage.json.")
    # ⚠️ ROADMAP 3.1. `tools.omr.staged.lilypond` reuses `export.build()` and
    # its cross-bar `_pair_arcs`/`_place_wedges` passes over a FRESH `Record`
    # of its own -- it does not read the MusicXML `report` above -- so this
    # is independent of `--musicxml` and either may be given alone.
    ap.add_argument("--lilypond", default=None,
                    help="also EXPORT the run to a LilyPond .ly here. Its own "
                         "coverage report -- including marks LilyPond has no "
                         "syntax for (tremolo, dynamic-word directives) -- "
                         "goes beside it as <path>.coverage.json.")
    # ⚠️ ROADMAP 3.3, PART A / product definition (CLAUDE.md §1): "one
    # command, a whole movement, MusicXML and a LilyPond PDF". Before this,
    # a PDF needed a THIRD command (`lilypond out.ly` by hand, after
    # `--lilypond` wrote it). `--pdf` closes that -- it compiles the
    # LilyPond text with the `lilypond` BINARY, reusing the already-computed
    # `.ly` when `--lilypond` was also given (one `to_lilypond` call, not
    # two) and writing one anyway, beside the PDF, when it was not, so the
    # run still leaves the intermediate a musician (or a later `lilypond`
    # invocation) can use.
    ap.add_argument("--pdf", dest="pdf_out", default=None,
                    help="also RENDER the LilyPond output to a PDF here, via "
                         "the `lilypond` binary on PATH -- located the same "
                         "way `tools.omr.acceptance.lilypond_check` does "
                         "(`shutil.which('lilypond')`, never a hardcoded "
                         "path). If `lilypond` is not on PATH, the .ly is "
                         "still written and this exits 0 with a clear "
                         "message -- a missing renderer is not a failed "
                         "gather (CLAUDE.md rule 8: never turn 'cannot "
                         "render' into a silent success OR a crash).")
    # ⚠️⚠️ BOTH OCR RUNGS DEFAULT **ON** SINCE 2026-09-16 (Sean's call), and
    # the flags are `--no-surya` / `--no-ocr` so ABSENCE IS ON. The text
    # layer is free and reads NOTHING on a 19th-century scan (0 labels over
    # 75 staves on Litolff Beethoven 5 p.1-4); the OCR rungs are what
    # actually read that edition (50 of 75, and 50 of 50 CORRECT against
    # hand-read print truth).
    #
    # They were opt-in "because a default that silently changes a gather's
    # cost is a decision somebody should take deliberately". That decision is
    # now taken ON MEASUREMENT rather than on caution:
    # `benchmarks/omr-surya-staged-cost-2026-09/FINDINGS.md` -- 17.8 s/page
    # attributable, 93 s/page of a real gather (20.5% of it, drift-corrected
    # over six ABAB arms).
    #
    # ⚠️ The "~75% of a whole-work run" this comment once cited never
    # existed. The measured figure is 20.5%, and the reader that actually
    # dominates a staged run is `OMR_DIRECTION_TEXT` at ~267 s/page for SIX
    # accepted words on the same document -- which has been ON by default
    # since 2026-09-02 and is repriced in that same FINDINGS.
    # ⚠️ This comment used to cite "CLAUDE.md measures Surya at ~75% of a
    # whole-work run". No such measurement exists. The only same-pages pair
    # (benchmarks/omr-cleanup-count-2026-09 vs omr-part-join-phase2-2026-09,
    # both run_gather.sh, 2026-09-11) is +282 s over 4 pages, +17.8%, n=1 on
    # different trees -- and gather_direction_words already spawns Surya on
    # every page by default, so this flag saves one of TWO spawns. Scoped,
    # with the pre-registered experiment that settles it, in
    # docs/scope-surya-staged-optin-2026-09-16.md.
    ap.add_argument("--no-surya", dest="surya", action="store_false",
                    help="do NOT read margin labels with Surya. On by "
                         "default since 2026-09-16: measured at 93 s/page on "
                         "Litolff Beethoven 5 p1-4, buying 50 instrument "
                         "identities over 75 staves, 50 of 50 correct "
                         "against hand-read print truth, where the free text "
                         "layer reads ZERO. Without it Q.MARGIN_LABEL stays "
                         "empty and the part join falls back to staff "
                         "position.")
    ap.add_argument("--no-ocr", dest="ocr", action="store_false",
                    help="do NOT allow the Tesseract rung for margin labels. "
                         "Both rungs default ON together and should be "
                         "turned off together: Tesseract's measured value is "
                         "as an additive rung UNDER Surya, and alone its "
                         "error mode is in-word and RESOLVING (`Ki.Tr.` -> "
                         "Trumpet at high confidence), which in the staged "
                         "path nothing outranks.")
    ap.set_defaults(surya=True, ocr=True)
    # ⚠️⚠️ `roster` WAS THREADED END TO END WITH NO PRODUCER — the SECOND
    # missing producer found in this pipeline, after `pdf_path` cost 75 of 75
    # staves their margin labels on every staged run this repo had ever made.
    # `run_staged` -> `run_staged_on` -> `gather` -> `gather_external` all
    # took `roster`, every link FORWARDED it, and no call site anywhere in
    # `tools/` ever supplied one, so `Q.ROSTER_ENTRY` was dead on every run.
    # Found by `staged.wiring`, which exists so there is not a third.
    #
    # ⚠️ ON BY DEFAULT AND THAT IS A JUDGEMENT, not an oversight. The roster
    # is `source_kind: "catalog"` — read off the work's IMSLP page,
    # independent of the raster and of the MusicXML the benchmarks score
    # against — and `work_roster.roster_for_pdf` ABSTAINS (returns None) for
    # any PDF the store does not hold, which is every generated fixture and
    # every upload. So the default is a no-op everywhere it has no business
    # acting, and `--no-roster` turns it off outright.
    ap.add_argument("--work-id", default=None,
                    help="the score LIBRARY's work id (e.g. "
                         "`beethoven--symphony-5-op67`), for a PDF the store "
                         "does not hold. NOT the dossier's id.")
    ap.add_argument("--sheet", default=None,
                    help="a CONFIRMED fact sheet (tools.omr.factsheet). The "
                         "ONLY way a dossier reaches this pipeline.")
    ap.add_argument("--no-roster", action="store_true",
                    help="do not look the work's catalog roster up at all.")
    # ⚠️ ROADMAP 4.2. A whole work is several movements; a meter/key carry
    # must never cross one, and a document with more than one is exported as
    # one file PER MOVEMENT (see `tools.omr.staged.movements`). Human-
    # supplied, like `--sheet` -- an OPTION, never an `OMR_*` flag (CLAUDE.md
    # §7), because it is read once per run, not toggled.
    #
    # Grammar: comma-separated `NUMBER:START-END`, where START/END are a page
    # `P` or `P.S` (page and, where a movement starts mid-page, its first
    # system): `"1:0-11,2:12.1-20"` is movement 1 on pages 0-11 and movement 2
    # starting at page 12 system 1 through the end of page 20. Omit entirely
    # and the document is one movement, exactly as before this option
    # existed.
    ap.add_argument("--movements", default=None,
                    help="movement boundaries, e.g. '1:0-11,2:12.1-20' -- "
                         "see tools.omr.staged.movements.parse_movement_spec")
    ap.add_argument("--ink-rows", action="store_true",
                    help="file one Q.INK row per INK COMPONENT (the pre-"
                         "roadmap-1.1 form) instead of one aggregated row "
                         "per cell (the default since 1.1). The schema "
                         "change alone saves ~3-4%% of a record's compact "
                         "content (measured on the two shared records: "
                         "benchmarks/omr-ink-gather-2026-09/probe/"
                         "byte_share.py); the ~115 MB/page a full-component "
                         "Breitkopf gather runs is dominated by `arc_owner`'s "
                         "`considered` lists, unaffected by this flag (and "
                         "pooled in the FILE by `record_io` since 1.1b). Only "
                         "`tools/omr/positional_store.py` needs the "
                         "per-component form; pass this when feeding it.")
    ap.add_argument("--progress", action="store_true")
    args = ap.parse_args(argv)

    from . import legacy, pipeline
    from . import movements as movements_mod
    from . import weight_routing as weight_routing_mod

    pages = parse_pages(args.pages)
    # ⚠️ RAISES `movements_mod.MalformedMovementSpec` (a `ValueError`) ON A
    # BAD SPEC, loudly and before anything runs -- CLAUDE.md rule 8: a
    # `--movements` typo must never be read as "no movements given".
    movement_spans = (movements_mod.parse_movement_spec(args.movements)
                      if args.movements else None)

    # ⚠️ `weight_routing.resolve_staged_weights` never triggers on bare
    # omission (see --weights' own help text): `args.weights` is either a
    # real path (pins, no classification -- unchanged), the literal string
    # "auto", or None with --route-weights set (roadmap 3.2's own request
    # shape). Both of the last two route; anything else is a no-op, so a
    # plain `--pages 0` run with neither flag is BYTE-IDENTICAL to before
    # this landed -- checked by the CLI tests rather than assumed.
    weights_path, weight_routing, input_domain_classification = (
        weight_routing_mod.resolve_staged_weights(
            args.pdf, pages, weights=args.weights,
            route_weights=args.route_weights,
            no_weight_routing=args.no_weight_routing))

    detector = None
    if weights_path:
        from ..yolo_detector import YoloDetector
        detector = YoloDetector(weights_path)
        if args.progress and weight_routing:
            print(f"  weights routed: "
                  f"{weight_routing.get('verdict', weight_routing.get('mode'))}"
                  f" -> {Path(weights_path).name}", flush=True)

    # ⚠️⚠️ THERE IS NO `--dossier`, AND SEAN RULED ON 2026-09-21 THAT THERE
    # WILL NOT BE: *"let the dossier only reach the pipeline through a
    # confirmed sheet."* The original reason stands and is why -- a dossier is
    # generated from the same MusicXML the benchmarks score against, so the
    # scan gate is dossier-free BY PROTOCOL and a bare flag would put a truth
    # file inside a measurement path. What the ruling adds is the escape: a
    # sheet whose `movement.dossier_id` a HUMAN confirmed. The benchmark path
    # is then structurally unable to consume one rather than trusted not to,
    # because it passes no sheet and an unconfirmed sheet admits nothing.
    #
    # ⚠️ The FACT that one was admitted travels on the row (`admitted_by`), so
    # a later reader can see that a person took responsibility for it.
    dossier = None
    if args.sheet:
        from .. import factsheet as _fs
        sheet = json.loads(Path(args.sheet).read_text())
        dossier, why = _fs.dossier_for(sheet)
        print(f"SHEET: {args.sheet}")
        print(f"  dossier: {'ADMITTED' if dossier else 'refused'} -- {why}")

    roster = None
    if not args.no_roster:
        from ..work_roster import roster_for_pdf, work_roster as _by_id
        roster = (_by_id(args.work_id) if args.work_id
                  else roster_for_pdf(args.pdf))
        if args.progress:
            print(f"ROSTER: {roster.work_id if roster else 'none'}"
                  f"{'' if roster else ' (this PDF is not in the catalog)'}")

    # ⚠️ ONE gather, including under `--against`. The legacy side is loaded
    # BEFORE the run and handed in, so the divergence table is built from the
    # same log the adjudication report describes. Until 2026-09-08 this
    # re-ran prepare/gather/adjudicate a second time, which doubled the work
    # and compared against a different pass of a detector with documented
    # run-to-run jitter.
    result = pipeline.run_staged(
        args.pdf, pages, detector=detector, dpi=args.dpi,
        conf_threshold=args.conf, imgsz=args.imgsz, roster=roster,
        dossier=dossier,
        surya_fallback=args.surya, ocr_fallback=args.ocr,
        ink_component_rows=args.ink_rows,
        input_domain_classification=input_domain_classification,
        movements=movement_spans,
        legacy=legacy.load(args.against) if args.against else None,
        progress=args.progress)
    result["weight_routing"] = weight_routing

    # ⚠️⚠️ WHICH TREE BUILT THIS RECORD. Without it, comparing two records is
    # an unprovenanced A/B: `regather_control.py` reporting "MOVED: nothing"
    # reads as "my change is inert" when it is equally consistent with having
    # compared two runs of the SAME tree, or a file with itself. That is the
    # cached-arm trap the meter session found in its own `run_arms.py`, one
    # layer down -- and the shape this project keeps paying for, where the
    # failure is never a wrong answer but a RIGHT-LOOKING one.
    #
    # ⚠️ A DIRTY TREE IS NEVER EQUAL TO ITSELF: a SHA cannot tell two sets of
    # uncommitted edits apart, so `dirty` is recorded and any consumer must
    # refuse to treat two dirty stamps as different-or-same. That rule is the
    # meter session's, adopted rather than re-derived.
    prov = _provenance()
    # ⚠️ SETTINGS SIT BESIDE THE TREE, not inside it: the tree is a fact
    # about the CODE and the settings a fact about the RUN, and a consumer
    # comparing two records needs them apart to tell a code change from a
    # flag arm. See `_settings`.
    prov["settings"] = _settings(args)
    result["provenance"] = prov
    # ⚠️⚠️ ROADMAP 1.1b, 2026-09-22: COMPACT, NOT `indent=2`. A staged
    # record's own `record_slim.py` measured this format change ALONE
    # (isolated from its ink-summary change) as roughly half of that
    # tool's 48-51% size reduction on the two committed shared records --
    # a bigger, lower-risk lever than any per-quantity schema change,
    # because a short flat row (one `Q.INK` component, one entry of an
    # `arc_owner` `considered` array) pays `indent=2`'s per-leaf-line tax
    # far more than a deeply-nested one. When `args.out` is not given the
    # text still goes to stdout for a human to read -- rare in practice,
    # since every real gather passes `--out` -- and un-indented JSON on one
    # line is unreadable there, so that path alone still pretty-prints;
    # only the file actually WRITTEN to disk goes compact.
    #
    # ⚠️ AND POOLED (roadmap 1.1b, same day, `record_io`): the FILE spells a
    # verdict id list that repeats another list in its system as one pooled
    # copy plus the private ids, because an `arc_owner` verdict is 99 %
    # three copies of its system's ~1,800 glyph ids and there are 2,207 of
    # them on Breitkopf. `result` itself is NOT pooled -- `--musicxml` below
    # and every in-memory consumer see the plain dict -- and a reader of the
    # file goes through `record_io.load_record`, never bare `json.loads`.
    from .record_io import dumps_for_file
    file_text = dumps_for_file(result, separators=(",", ":"), default=str)
    if args.out:
        Path(args.out).write_text(file_text)
        print(f"wrote {args.out}")
    else:
        print(dumps_for_file(result, indent=2, default=str))

    # ⚠️ ROADMAP 4.2. `movement_spans` (above) is what `--movements` asked
    # for BEFORE the gather; `result` is what the record actually HOLDS
    # after it -- read back through `movements_mod.spans_from_result` so a
    # record loaded from disk (not built in this process at all) would take
    # the same branch. **A record with no `Q.MOVEMENT_SPANS` fact -- no
    # `--movements` was given -- returns `()` here and takes the EXACT
    # single-file path this CLI has always taken.**
    export_spans = (movements_mod.spans_from_result(result)
                    if (args.musicxml or args.lilypond or args.pdf_out)
                    else ())

    if not export_spans:
        if args.musicxml:
            from . import export as staged_export
            xml, report = staged_export.to_musicxml(result)
            Path(args.musicxml).write_text(xml)
            cov = Path(args.musicxml + ".coverage.json")
            cov.write_text(json.dumps(report, indent=2, default=str))
            print(f"wrote {args.musicxml} and {cov}")

        # ⚠️⚠️ IMPORTED HERE, AFTER THE GATHER -- the same rule `--musicxml`
        # follows and for the same reason: `staged/export.py` says so in its
        # own comment (`export._pad_tacet_span`'s neighbourhood) because an
        # editor importing the exporter BEFORE a long unattended gather
        # finishes means an edit made mid-run reaches an already-imported
        # module's OLD code while its line numbers report the NEW file.
        # `tools.omr.staged.lilypond` imports `export` itself, so this
        # import is transitively the same one.
        if args.lilypond:
            from . import lilypond as staged_lily
            ly_text, ly_report = staged_lily.to_lilypond(result)
            Path(args.lilypond).write_text(ly_text)
            ly_cov = Path(args.lilypond + ".coverage.json")
            ly_cov.write_text(json.dumps(ly_report, indent=2, default=str))
            print(f"wrote {args.lilypond} and {ly_cov}")

        # ⚠️⚠️ ROADMAP 3.3 PART A / CLAUDE.md §1's PRODUCT DEFINITION: "one
        # command, a whole movement, MusicXML and a LilyPond PDF". Before
        # this, a PDF needed `--lilypond` here PLUS a separate
        # `lilypond out.ly` invocation -- a second command, run by hand,
        # after the gather that produced `out.ly` had already finished.
        # `--pdf` closes that gap.
        #
        # ⚠️ REUSES `--lilypond`'s ALREADY-COMPUTED TEXT WHEN BOTH ARE
        # GIVEN -- never a second `to_lilypond(result)` call over the same
        # record, for the same "ONE gather" reason `--against` reuses the
        # loaded legacy result rather than re-running anything.
        if args.pdf_out:
            if args.lilypond:
                pdf_ly_report = ly_report
                ly_source = Path(args.lilypond)
            else:
                from . import lilypond as staged_lily
                pdf_ly_text, pdf_ly_report = staged_lily.to_lilypond(result)
                ly_source = Path(args.pdf_out).with_suffix(".ly")
                ly_source.write_text(pdf_ly_text)
                ly_cov = Path(str(ly_source) + ".coverage.json")
                ly_cov.write_text(
                    json.dumps(pdf_ly_report, indent=2, default=str))
                print(f"wrote {ly_source} and {ly_cov} "
                      f"(--lilypond not given -- one is needed to render a "
                      f"PDF, so this run wrote it anyway)")
            _render_pdf(ly_source, Path(args.pdf_out))

        _report(result)
        if args.musicxml:
            staged_export._report(report)
        if args.lilypond:
            staged_lily._report(ly_report)
        # ⚠️ LAST, ON PURPOSE (CLAUDE.md §1): "every bar the reader could not
        # read is MARKED as unread and never invented ... and the user must
        # see how many". Everything above is the per-stage / per-family
        # detail a session digs through; this is the one line Sean (or
        # anyone running the CLI) should be able to read without opening the
        # coverage JSON.
        if args.musicxml or args.lilypond:
            _print_accounting_summary(
                musicxml_report=report if args.musicxml else None,
                lilypond_report=ly_report if args.lilypond else None)
        return 0

    # ── ROADMAP 4.2: more than one movement -- one file set per movement ────
    _report(result)
    print(f"\n── MOVEMENTS: {len(export_spans)} "
          f"({', '.join(str(s['number']) for s in export_spans)}) ──",
          file=sys.stderr)
    ly_by_number: dict = {}
    if args.musicxml:
        from . import export as staged_export
        for number, path, _xml, rpt in movements_mod.export_each(
                result, export_spans, args.musicxml, staged_export.to_musicxml):
            print(f"── movement {number}: wrote {path} and "
                  f"{path}.coverage.json ──", file=sys.stderr)
            staged_export._report(rpt)
            _print_accounting_summary(musicxml_report=rpt,
                                      lilypond_report=None)
    if args.lilypond:
        from . import lilypond as staged_lily
        for number, path, ly_text, rpt in movements_mod.export_each(
                result, export_spans, args.lilypond, staged_lily.to_lilypond):
            ly_by_number[number] = ly_text
            print(f"── movement {number}: wrote {path} and "
                  f"{path}.coverage.json ──", file=sys.stderr)
            staged_lily._report(rpt)
    if args.pdf_out:
        from . import lilypond as staged_lily
        by_number = dict(movements_mod.split_result(result, export_spans))
        for span in export_spans:
            number = span["number"]
            pdf_path = movements_mod.movement_path(args.pdf_out, number)
            if number in ly_by_number:
                # Already written above by `--lilypond` -- reuse it rather
                # than a second `to_lilypond` call over the same movement,
                # the same "ONE gather" reason the single-movement path
                # reuses `--lilypond`'s text.
                ly_source = movements_mod.movement_path(args.lilypond, number)
            else:
                pdf_ly_text, pdf_ly_report = staged_lily.to_lilypond(
                    by_number[number])
                ly_source = movements_mod.movement_path(
                    Path(args.pdf_out).with_suffix(".ly"), number)
                ly_source.write_text(pdf_ly_text)
                ly_cov = Path(str(ly_source) + ".coverage.json")
                ly_cov.write_text(
                    json.dumps(pdf_ly_report, indent=2, default=str))
                print(f"wrote {ly_source} and {ly_cov} "
                      f"(--lilypond not given -- one is needed to render a "
                      f"PDF, so this run wrote it anyway)")
            _render_pdf(ly_source, pdf_path)
    return 0


def _render_pdf(ly_source: Path, pdf_out: Path) -> None:
    """Compile `ly_source` to `pdf_out` with the `lilypond` binary.

    ⚠️ THE SAME LOOKUP `tools.omr.acceptance.lilypond_check` USES (roadmap
    3.1b) -- `shutil.which("lilypond")`, never a hardcoded path or an env
    var this module would have to invent and keep in sync. `lilypond`
    absent is reported and this still exits 0 (CLAUDE.md rule 8: a missing
    renderer is "cannot tell", never converted into a crash OR a silent
    empty file called a success).
    """
    import shutil
    import subprocess

    binary = shutil.which("lilypond")
    if not binary:
        print(f"NO PDF: `lilypond` is not on PATH. Wrote {ly_source} -- "
              f"render it yourself once lilypond is installed "
              f"(`lilypond -o <dir> {ly_source}`).")
        return

    pdf_out = pdf_out.resolve()
    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [binary, "-o", str(pdf_out.parent), str(ly_source)],
            capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        print(f"NO PDF: `lilypond` did not finish within 1800s compiling "
              f"{ly_source}. Wrote {ly_source} -- render it yourself "
              f"(`lilypond -o <dir> {ly_source}`).")
        return
    log = (proc.stdout or "") + "\n" + (proc.stderr or "")

    # ⚠️ THE SAME TWO REGEXES `tools.omr.acceptance` confirmed against a real
    # `lilypond 2.24.4` run (roadmap 3.1b's own session) -- imported rather
    # than re-derived, so this call site and `lilypond_check` can never read
    # one stderr string differently. Deferred: `tools.omr.acceptance` is a
    # benchmark-harness module a plain gather-and-export run should not pay
    # to import unless a PDF was actually requested.
    from .. import acceptance as _acceptance
    barcheck_failures = len(_acceptance._BARCHECK_RE.findall(log))
    unterminated_ties = len(_acceptance._UNTERMINATED_TIE_RE.findall(log))

    produced = pdf_out.parent / (ly_source.stem + ".pdf")
    if produced != pdf_out and produced.is_file():
        produced.replace(pdf_out)
        produced = pdf_out
    ok = produced.is_file()

    print(f"lilypond exit {proc.returncode}: "
          f"{'wrote ' + str(pdf_out) if ok else 'NO PDF produced'}")
    print(f"  {barcheck_failures} bar-check failures, "
          f"{unterminated_ties} unterminated ties, from lilypond's own "
          f"stderr (CLAUDE.md §6a: a control, never a substitute for a "
          f"human reading the PDF)")
    if not ok:
        print(f"  ⚠️ lilypond exited {proc.returncode} and produced no PDF "
              f"-- log tail:\n{log[-2000:]}")


def _report(result: dict) -> None:
    adj = result["adjudication"]
    print("\n── ADJUDICATE ─────────────────────────────────────────", file=sys.stderr)
    print(f"  decided:   {adj['decided']}", file=sys.stderr)
    print(f"  abstained: {adj['abstained']}", file=sys.stderr)
    if adj["excluded_as_circular"]:
        print(f"  ⚠️ excluded as circular: {len(adj['excluded_as_circular'])}",
              file=sys.stderr)
    ag = result.get("agreement")
    if ag is not None:
        print("── GROUPS ─────────────────────────────────────────────",
              file=sys.stderr)
        for name, row in sorted(ag["per_redundancy"].items()):
            print(f"  {name}: {row['n_facts']} facts, "
                  f"{row['n_witnesses']} witnesses, "
                  f"{row['uninformative']} uninformative, {row['agreement']}",
                  file=sys.stderr)
        # ⚠️ A DECLARED redundancy that found nothing is named, because a zero
        # is a suspect and not a result.
        for key, gloss in (("declared_but_empty", "placed no fact"),
                           ("witnessed_by_nobody", "no witness spoke"),
                           ("checked_nothing",
                            "never two independent signals -- corroborated "
                            "NOTHING, however busy it looks")):
            if ag.get(key):
                print(f"  ⚠️ {key} ({gloss}): {ag[key]}", file=sys.stderr)
        print(f"  ⚠️ DISAGREEMENTS: {ag['n_disagreements']} "
              f"(each implicates its WHOLE group, not its dissenter)",
              file=sys.stderr)
    ev = result["evaluation"]
    print(f"── EVALUATE: {ev['counts']['fired']} fired, "
          f"{ev['counts']['skipped']} skipped", file=sys.stderr)
    # ⚠️ GUARDED ON THE KEY'S PRESENCE, NOT ON THE FLAG. With INFER off the
    # key is absent and nothing is printed, so the stderr report of a
    # flag-off run is identical to one from a tree with no INFER at all.
    # Reading the flag here instead would print "INFER: off" and break that.
    inf = result.get("inference")
    if inf is not None:
        print(f"── INFER: {inf['counts']['inferred']} inferred, "
              f"{inf['counts']['skipped']} skipped  "
              f"⚠️ every one is LABELLED and supersedes a recorded narrowing",
              file=sys.stderr)
    print(f"── DECLARED STUBS: {len(result['stubs']['decisions'])} decisions, "
          f"{len(result['stubs']['consequences'])} consequences", file=sys.stderr)
    if "divergence" in result:
        print(f"── DIVERGENCE: {result['divergence']['counts']}", file=sys.stderr)


def _print_accounting_summary(*, musicxml_report: Optional[dict],
                              lilypond_report: Optional[dict]) -> None:
    """CLAUDE.md §1, in plain words: *"every bar the reader could not read
    is MARKED as unread and never invented, and every staff is named or
    held out and counted"*. The `--musicxml` / `--lilypond` coverage reports
    already carry these numbers (`staged.export.coverage`,
    ROADMAP 2.8 / 3.5's `unread_bar_marks` / part-join provenance) -- this
    reads them, never recomputes them, so the console line and the JSON a
    session opens next can never disagree.

    Prefers the MusicXML report for the bar counts: `bars_with_events` (the
    denominator) is only computed while rendering `_part_xml`, which
    `--lilypond` alone does not run. `held out staves` is read off whichever
    report is present (both share the same part-join provenance).

    ⚠️⚠️ ROADMAP 3.5. THIS USED TO PRINT ONE NUMBER LABELLED "unread bars"
    THAT WAS ACTUALLY ONLY `bars_held_out_sum` -- a bar we read NOTHING in
    at all (`empty_bars_padded`, CLAUDE.md §1's own "unread") never reached
    this line. Both are printed now, by the SAME words `staged.export.
    UNREAD_BAR_MARK_WORDS` stamps into the file itself, so a session reading
    the console output and a musician reading the PDF see the same two
    reasons rather than one figure standing in for both.
    """
    held_out_staves = None
    for rpt in (musicxml_report, lilypond_report):
        if rpt and (rpt.get("part_join") or {}).get("held_out_staves") is not None:
            held_out_staves = rpt["part_join"]["held_out_staves"]
            break

    print("\n── ACCOUNTING (CLAUDE.md §1: every unread bar is MARKED, "
          "never invented) ──", file=sys.stderr)

    marks = (musicxml_report or {}).get("unread_bar_marks")
    if marks is not None:
        print(f"  unread bars (\"{marks['words']['unread']}\", read NOTHING): "
              f"{marks['unread']}", file=sys.stderr)
        print(f"  held-out bars (\"{marks['words'].get('bar_does_not_add_up', 'unread')}\"): "
              f"{marks['held_out_sum']}", file=sys.stderr)
        print(f"  total bars marked red in the file: {marks['written']} "
              f"(colour {marks['color']})", file=sys.stderr)
    else:
        print("  unread / held-out bars: not computed (needs --musicxml -- "
              "roadmap 2.8/3.5's hold-out and marking is that exporter's "
              "own accounting)", file=sys.stderr)

    if held_out_staves is not None:
        print(f"  staves held out: {held_out_staves} (the part join could "
              f"not NAME them, so they are held out of the file and "
              f"counted, never silently dropped -- "
              f"OMR_HOLD_OUT_UNIDENTIFIED)", file=sys.stderr)
    else:
        print("  staves held out: not computed", file=sys.stderr)

    census = (musicxml_report or lilypond_report or {}).get("status_census") or {}
    unaccounted = census.get("unaccounted")
    if unaccounted:
        print(f"  ⚠️ status_census.unaccounted is NOT EMPTY: {unaccounted} "
              f"-- a family the census cannot place; see "
              f"`python3 -m tools.omr.staged.trace --family <name>`",
              file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
