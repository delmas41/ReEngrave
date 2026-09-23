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
from typing import Any


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
_OUTPUT_ONLY_ARGS = ("out", "musicxml", "lilypond", "progress")


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
    from . import weight_routing as weight_routing_mod

    pages = parse_pages(args.pages)

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

    if args.musicxml:
        from . import export as staged_export
        xml, report = staged_export.to_musicxml(result)
        Path(args.musicxml).write_text(xml)
        cov = Path(args.musicxml + ".coverage.json")
        cov.write_text(json.dumps(report, indent=2, default=str))
        print(f"wrote {args.musicxml} and {cov}")

    # ⚠️⚠️ IMPORTED HERE, AFTER THE GATHER -- the same rule `--musicxml`
    # follows and for the same reason: `staged/export.py` says so in its own
    # comment (`export._pad_tacet_span`'s neighbourhood) because an editor
    # importing the exporter BEFORE a long unattended gather finishes means
    # an edit made mid-run reaches an already-imported module's OLD code
    # while its line numbers report the NEW file. `tools.omr.staged.lilypond`
    # imports `export` itself, so this import is transitively the same one.
    if args.lilypond:
        from . import lilypond as staged_lily
        ly_text, ly_report = staged_lily.to_lilypond(result)
        Path(args.lilypond).write_text(ly_text)
        ly_cov = Path(args.lilypond + ".coverage.json")
        ly_cov.write_text(json.dumps(ly_report, indent=2, default=str))
        print(f"wrote {args.lilypond} and {ly_cov}")

    _report(result)
    if args.musicxml:
        staged_export._report(report)
    if args.lilypond:
        staged_lily._report(ly_report)
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
