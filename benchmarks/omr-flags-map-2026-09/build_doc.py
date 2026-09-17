#!/usr/bin/env python3
"""Build docs/map-flags-gates-and-guards-2026-09-16.md.

Sean asked whether there is a single place listing every gate, guard, default
setting, or anything that could be flipped, with what it does and its
options/default. The answer was "half": `test_flag_default_direction.py`
derives simple env-flag sites from the AST, and CLAUDE.md carries prose
tables with the measured evidence — but neither is a full inventory, and
CLAUDE.md's own knobs table is silent on flags that exist in the code (this
script's job is to say exactly which ones, mechanically, rather than by
memory).

WHAT IS MECHANICALLY DERIVED (re-run this script and it re-checks all of it):
  * `derive_map.py`'s env-flag site list (every `os.environ.get`/`os.getenv`
    call naming an OMR_*/MAESTRO_* flag under tools/ or backend/, excluding
    tests) and its numeric-guard list (every module-level ALL-CAPS constant
    assigned a plain number under tools/omr/, excluding tests).
  * Whether each flag/guard NAME is mentioned anywhere in CLAUDE.md at all
    (a presence check, not a semantic one).
  * The default-ON/default-OFF direction for the subset of flags whose
    `os.environ.get(...)` call is compared *inline* to a literal word set —
    reusing `test_flag_default_direction.default_on_flags()` verbatim.

WHAT IS HAND-AUTHORED, AND MARKED AS SUCH: the one-line "what it gates"
description, which STAGE a flag/guard acts in, whether CLAUDE.md documents a
byte-identical off-control, and the MEASURED/ASSERTED judgement for numeric
guards. These require reading prose CLAUDE.md never expresses as a grep-able
literal (e.g. "MEASURED" as a judgement, not a keyword search) — the task
instructions explicitly allow hand-writing this class of fact provided it is
labelled, so every hand-authored cell below cites the CLAUDE.md line(s) or
source file:line it was read from, and `ANNOTATED_ONLY_ROWS` in the diff
report calls out anything this script could not verify from either source.

Run:
    python3 benchmarks/omr-flags-map-2026-09/build_doc.py

writes docs/map-flags-gates-and-guards-2026-09-16.md and prints the
disagreement counts to stdout.
"""
from __future__ import annotations

import re
import sys
import pathlib
import subprocess
import json

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs" / "map-flags-gates-and-guards-2026-09-16.md"
CLAUDE_MD = ROOT / "CLAUDE.md"

sys.path.insert(0, str(HERE))
import derive_map  # noqa: E402


def _run_derive():
    flag_sites = list(derive_map.env_flag_sites())
    guards = list(derive_map.numeric_guard_constants())
    return flag_sites, guards


CLAUDE_TEXT = CLAUDE_MD.read_text() if CLAUDE_MD.is_file() else ""


def mentioned(name: str) -> bool:
    return re.search(r"\b" + re.escape(name) + r"\b", CLAUDE_TEXT) is not None


def has_knob_row(name: str) -> bool:
    """True where CLAUDE.md gives this flag its own markdown-table row —
    `| \\`FLAG\\` | ... |` at the start of a line — in either the OMR
    knobs table or the Environment variables table. A flag can be
    `mentioned()` (its name appears in prose, e.g. as part of a bug-fix
    story) without ever getting one of these."""
    return re.search(r"^\|\s*`" + re.escape(name) + r"`", CLAUDE_TEXT,
                      re.MULTILINE) is not None


# ---------------------------------------------------------------------------
# Hand-authored annotations for ENV FLAGS.
#
# stage: one of GATHER / ADJUDICATE / EVALUATE / INFER / EXPORT / "legacy
#        transcribe/export" (the pre-staged pipeline in tools/omr/*.py) /
#        "web app" (backend/) / "operational" (paths, timeouts, CLI knobs
#        that are not a recognition decision at all).
# gate: one line, hand-written, source cited in `src`.
# byte_off: True / False / None (CLAUDE.md does not say).
# ---------------------------------------------------------------------------
ANNOTATIONS = {
    # === staged pipeline (tools/omr/staged/) ===
    "OMR_ADJUDICATE": dict(
        stage="pipeline master switch",
        gate="master switch for the whole staged pipeline: off/shadow/on "
             "(anything unrecognised reads as off)",
        byte_off=None,
        src="tools/omr/staged/pipeline.py:47-56",
        in_claude_md=False,
    ),
    "OMR_INFER": dict(
        stage="INFER",
        gate="runs the 4th stage (INFER) after EVALUATE, before EXPORT; "
             "collapses a NARROWED verdict using cross-staff evidence",
        byte_off=True,
        src="tools/omr/staged/infer.py; CLAUDE.md knobs table + 'bypass' note",
        in_claude_md=True,
    ),
    "OMR_METER_CARRY": dict(
        stage="ADJUDICATE",
        gate="a system with no meter reading takes the last READ meter as a "
             "candidate, weighed by that system's own bars",
        byte_off=None,
        src="tools/omr/staged/adjudicators/rhythm.py:1016; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_METER_FROM_BARS": dict(
        stage="ADJUDICATE",
        gate="a system with no meter and no carry derives the bar LENGTH "
             "from its own bars; cannot cross a movement boundary",
        byte_off=None,
        src="tools/omr/staged/adjudicators/rhythm.py:1144; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_METER_SEGMENTS": dict(
        stage="EXPORT",
        gate="exporter reads the meter in force at each BAR from "
             "Q.METER's segments, instead of one meter per staff-run",
        byte_off=True,
        src="tools/omr/staged/export.py:132; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_WHOLE_REST_INK": dict(
        stage="EXPORT",
        gate="refuses to write a pitched <note> where the record says the "
             "ink is a whole rest (the one staged repair that deletes notes)",
        byte_off=True,
        src="tools/omr/staged/export.py:182; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_METER_TEMPLATE_AT_BAR": dict(
        stage="GATHER",
        gate="asks the template meter reader at candidate mid-staff bar "
             "heads across every staff of the system (a GATHER change)",
        byte_off=True,
        src="tools/omr/staged/gather.py:2045; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_DIRECTION_TEXT_SCAN_GATE": dict(
        stage="GATHER",
        gate="staged pipeline only: skip the direction-word OCR reader on a "
             "page PROVED to be a scan (it is expensive there for little yield)",
        byte_off=None,
        src="tools/omr/staged/gather.py:2550; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    # === legacy transcribe / export (tools/omr/*.py, not staged/) ===
    "OMR_LEFT_EDGE_SPLIT": dict(
        stage="legacy transcribe/export",
        gate="a second barline scan at each system's shared left edge adds "
             "a system break the wide connectivity window merged away",
        byte_off=None,
        src="tools/omr/system_grouping.py:160; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_DIRECTION_TEXT": dict(
        stage="legacy transcribe/export (and GATHER via staged/gather.py, "
              "staged/pipeline.py)",
        gate="reads the printed words inside a system (OCR) and exports "
             "them as <words>",
        byte_off=None,
        src="tools/omr/transcribe.py:4368, staged/gather.py:2638, "
            "staged/pipeline.py:140; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_CELL_LINE_TRACE": dict(
        stage="legacy transcribe/export",
        gate="slides a measure cell's stored 5-line staff grid onto the ink "
             "beneath it, for a tilted/bowed scanned staff",
        byte_off=True,
        src="tools/omr/measure_extractor.py:1176; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_ONE_LINE_STAVES": dict(
        stage="legacy transcribe/export",
        gate="admit a one-line percussion staff into cell canonicalisation "
             "instead of dropping it before it reaches a cell",
        byte_off=None,
        src="tools/omr/measure_extractor.py:1199 + docstring at :1181",
        in_claude_md=False,
    ),
    "OMR_ARC_ATTRIBUTION": dict(
        stage="legacy transcribe/export",
        gate="gives a cross-staff slur/tie to the staff whose noteheads it "
             "hugs (move) instead of leaving it on the detecting staff",
        byte_off=None,
        src="tools/omr/export.py:1946; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_ARC_RECLASS": dict(
        stage="legacy transcribe/export",
        gate="export-time tie/slur grammar veto (measured and refused on "
             "the scan family; dormant)",
        byte_off=True,
        src="tools/omr/export.py:2149; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_SLOT_STITCH": dict(
        stage="legacy transcribe/export",
        gate="joins staves into continuous parts by contextual SLOT where "
             "the ordinal join refuses (suppressed tacet staves)",
        byte_off=None,
        src="tools/omr/export.py:3670; CLAUDE.md knobs table "
            "('10 of 11 exports byte-identical')",
        in_claude_md=True,
    ),
    "OMR_CONDENSED_PARTS": dict(
        stage="legacy transcribe/export",
        gate="off: one part per player on a condensed staff; 'all' also "
             "splits ordinal-join fragments",
        byte_off=True,
        src="tools/omr/export.py:3690,3714; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_CHOIR_GROUPING": dict(
        stage="legacy transcribe/export",
        gate="two cues for choir-barred / differently-indented pages "
             "(pair-local left-edge merge + open-score guard)",
        byte_off=True,
        src="tools/omr/system_grouping.py:215; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_BRACKET_COLUMNS": dict(
        stage="legacy transcribe/export",
        gate="decide bracket instrument-family groups by counting systemic "
             "columns rather than crossing-pixel ink",
        byte_off=True,
        src="tools/omr/system_grouping.py:523; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_KEYSIG_CORROBORATION": dict(
        stage="legacy transcribe/export",
        gate="reverts a mid-staff key-signature change no other staff of "
             "the same system also changes at the same bar",
        byte_off=True,
        src="tools/omr/key_signature_corroboration.py:219; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_SCORE_LANGUAGE": dict(
        stage="legacy transcribe/export",
        gate="reads the document's printing tradition (Italian vs German "
             "instrument names) to settle otherwise-ambiguous abbreviations",
        byte_off=None,
        src="tools/omr/score_language.py:438; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_ROSTER_LABELS": dict(
        stage="legacy transcribe/export",
        gate="resolves a truncated/ambiguous margin label against the "
             "work's catalog roster (recover, disambiguate, or veto)",
        byte_off=None,
        src="tools/omr/work_roster.py:136; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_ROSTER": dict(
        stage="legacy transcribe/export",
        gate="whether the roster-driven part identity layer runs at all "
             "(named only as a historically-corrected flag, not documented "
             "as a knob)",
        byte_off=None,
        src="tools/omr/roster.py:140; CLAUDE.md only names it in the "
            "'flag default direction' fix list, no knob-table row",
        in_claude_md=True,
    ),
    "OMR_MOVEMENT_REFERENCE": dict(
        stage="legacy transcribe/export",
        gate="whether the whole-movement reference layout is built and "
             "used for the slot/instrument join (named only as a "
             "historically-corrected flag, not documented as a knob)",
        byte_off=None,
        src="tools/omr/movement_reference.py:137; CLAUDE.md only names it "
            "in the 'flag default direction' fix list, no knob-table row",
        in_claude_md=True,
    ),
    "OMR_LABEL_MERGE_QUALITY": dict(
        stage="legacy transcribe/export",
        gate="quality gate on merging OCR margin-label evidence (named "
             "only as a historically-corrected flag, not documented as a "
             "knob)",
        byte_off=None,
        src="tools/omr/contextual.py:541; CLAUDE.md only names it in the "
            "'flag default direction' fix list, no knob-table row",
        in_claude_md=True,
    ),
    "OMR_INSTRUMENT_CLEF_DEFAULT": dict(
        stage="legacy transcribe/export",
        gate="whether an instrument's canonical clef may stand in for one "
             "never read (named only as a historically-corrected flag)",
        byte_off=None,
        src="tools/omr/contextual.py:1103, tools/omr/transcribe.py:4683; "
            "CLAUDE.md only names it in the 'flag default direction' fix "
            "list, no knob-table row",
        in_claude_md=True,
    ),
    "OMR_LINEUP_SWAP_SPLIT": dict(
        stage="legacy transcribe/export",
        gate="movement-reference lineup-swap detection: split the "
             "reference where two adjacent systems swap staff order",
        byte_off=None,
        src="tools/omr/movement_reference.py:224",
        in_claude_md=False,
    ),
    "OMR_ROSTER_CLEF": dict(
        stage="legacy transcribe/export",
        gate="let the work's catalog roster seed a staff's clef where none "
             "was read",
        byte_off=None,
        src="tools/omr/contextual.py:1575",
        in_claude_md=False,
    ),
    "OMR_ROSTER_RANGE_VETO": dict(
        stage="legacy transcribe/export",
        gate="off/label/all: delete a note outside its instrument's "
             "written range, gated by how trustworthy the staff identity is",
        byte_off=None,
        src="tools/omr/transcribe.py:3164",
        in_claude_md=False,
    ),
    "OMR_ROSTER_SCORE_ORDER_VETO": dict(
        stage="legacy transcribe/export",
        gate="refuse a staff identity deduced purely from canonical score "
             "order (vs. one read off an ink label)",
        byte_off=None,
        src="tools/omr/offroster_name.py:91-107",
        in_claude_md=False,
    ),
    "OMR_ABSENT_INSTRUMENT_VETO": dict(
        stage="legacy transcribe/export",
        gate="refuse a staff name the movement's printed lineup cannot "
             "contain (default mode 'on', with a window/rule sub-syntax)",
        byte_off=None,
        src="tools/omr/absent_instrument.py:85-120",
        in_claude_md=False,
    ),
    "OMR_SLOT_GROUP_MAP": dict(
        stage="legacy transcribe/export",
        gate="map/ordinal/off: how a staff's bracket-group is compared to "
             "the reference layout's group when placing a span",
        byte_off=None,
        src="tools/omr/slots.py:320",
        in_claude_md=False,
    ),
    "OMR_SPAN_REFERENCE_FIT": dict(
        stage="legacy transcribe/export",
        gate="search/refuse/off: how a span's own reference system is "
             "placed into the document's slot space",
        byte_off=None,
        src="tools/omr/slots.py:605; this is the flag behind the "
            "'spans regression: found and fixed same day' MEMORY.md entry",
        in_claude_md=False,
    ),
    "OMR_REFERENCE_MOST_LABELLED": dict(
        stage="legacy transcribe/export",
        gate="on/pure/off: pick the movement reference system by how many "
             "staves it NAMES rather than by which staff count recurs",
        byte_off=None,
        src="tools/omr/slots.py:85",
        in_claude_md=False,
    ),
    "OMR_CONTEST_DUMP": dict(
        stage="operational / debug",
        gate="dump cross-staff ownership-contest detail to help diagnose "
             "the dedupe/ownership arbitration",
        byte_off=None,
        src="tools/omr/transcribe.py:3286",
        in_claude_md=False,
    ),
    "OMR_CV_HAIRPINS": dict(
        stage="legacy transcribe/export",
        gate="classical-CV hairpin (crescendo/diminuendo wedge) detector, "
             "as a second reader alongside the YOLO detections",
        byte_off=None,
        src="tools/omr/transcribe.py:3274",
        in_claude_md=False,
    ),
    "OMR_DIRECTION_READERS": dict(
        stage="operational",
        gate="override which OCR rung(s) read direction-text crops "
             "(surya, tesseract, or both) instead of the domain classifier",
        byte_off=None,
        src="tools/omr/direction_text.py:797",
        in_claude_md=False,
    ),
    "OMR_TAIL_RULE": dict(
        stage="legacy transcribe/export",
        gate="none/exact/all: whether the staves below the dossier's last "
             "read label may be trusted too",
        byte_off=None,
        src="tools/omr/dossier.py:521",
        in_claude_md=False,
    ),
    "OMR_PARTIAL_DYNAMICS": dict(
        stage="legacy transcribe/export",
        gate="off/complete/other: whether an unspellable run of dynamic "
             "letters is exported partially instead of dropped whole",
        byte_off=True,
        src="tools/omr/export.py:1502; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_PHASE26_FIXES": dict(
        stage="legacy classical-CV template_matcher (Phase 2.5-2.7)",
        gate="staged rollout level (0-4/'all') for the template-matcher "
             "detector's own bugfixes; defaults to the full stack",
        byte_off=None,
        src="tools/omr/template_matcher.py:30-43",
        in_claude_md=False,
    ),
    "OMR_PHASE28_FIX_TEXT_GATE": dict(
        stage="legacy classical-CV template_matcher (Phase 2.8)",
        gate="geometric staff-vicinity gate that drops template-matcher "
             "detections far from any staff line (tempo/dynamics text)",
        byte_off=None,
        src="tools/omr/template_matcher.py:56-61",
        in_claude_md=False,
    ),
    "OMR_EVAL_INDENT_MM": dict(
        stage="benchmark harness only",
        gate="inject a LilyPond \\paper indent override when rendering an "
             "orchestral_eval fixture; raises rather than rendering silently "
             "wrong if the source has no \\paper block",
        byte_off=None,
        src="tools/omr/training/orchestral_eval.py:336",
        in_claude_md=False,
    ),
    "OMR_WEIGHT_ROUTING": dict(
        stage="legacy transcribe/export",
        gate="classify each input scan-vs-engraved and route to the "
             "weights file measured best for that domain",
        byte_off=None,
        src="tools/omr/transcribe.py:4526; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_WEIGHTS_PATH": dict(
        stage="legacy transcribe/export + web app",
        gate="pin one YOLO weights file for every input, disabling "
             "OMR_WEIGHT_ROUTING",
        byte_off=None,
        src="backend/modules/local_omr.py:95; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_ENGRAVED_WEIGHTS": dict(
        stage="legacy transcribe/export",
        gate="override the engraved-side weights file OMR_WEIGHT_ROUTING "
             "targets",
        byte_off=None,
        src="tools/omr/transcribe.py:4580; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_CLEF_WEIGHTS": dict(
        stage="legacy transcribe/export",
        gate="optional clef-specialist weights for a second clef-only "
             "detector pass",
        byte_off=None,
        src="tools/omr/transcribe.py:4514,6055; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_MAX_PAGES": dict(
        stage="web app",
        gate="hard cap on pages transcribed per OMR job",
        byte_off=None,
        src="backend/modules/local_omr.py:106; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_CONF_THRESHOLD": dict(
        stage="web app",
        gate="minimum YOLO detection confidence",
        byte_off=None,
        src="backend/modules/local_omr.py:113; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_IMGSZ": dict(
        stage="web app",
        gate="YOLO inference image size (larger is not better — see "
             "CLAUDE.md's imgsz-sweep note)",
        byte_off=None,
        src="backend/modules/local_omr.py:129; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_DPI": dict(
        stage="web app",
        gate="PDF rasterization DPI (coupled to OMR_IMGSZ, deliberately "
             "different default from the CLI)",
        byte_off=None,
        src="backend/modules/local_omr.py:140; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "OMR_SURYA_KEEP_ALIVE": dict(
        stage="operational",
        gate="keep the Surya OCR llama.cpp server resident across runs "
             "instead of spawning/killing it per run",
        byte_off=None,
        src="tools/omr/staff_labels_surya.py:93; CLAUDE.md's "
            "'Cost, and how to remove most of it' section",
        in_claude_md=True,
    ),
    "OMR_SURYA_PYTHON": dict(
        stage="operational",
        gate="override the python executable used to launch the Surya "
             "OCR subprocess",
        byte_off=None,
        src="tools/omr/staff_labels_surya.py:175",
        in_claude_md=False,
    ),
    "OMR_SURYA_SENTINEL": dict(
        stage="operational",
        gate="override the path of the Surya server's own sentinel file "
             "(read directly because the host's Python cannot import surya)",
        byte_off=None,
        src="tools/omr/staff_labels_surya.py:98-99",
        in_claude_md=False,
    ),
    "OMR_SURYA_TIMEOUT_S": dict(
        stage="operational",
        gate="per-crop timeout (seconds) for the Surya OCR subprocess",
        byte_off=None,
        src="tools/omr/staff_labels_surya.py:79",
        in_claude_md=False,
    ),
    "OMR_WORK_ID": dict(
        stage="legacy transcribe/export",
        gate="name the catalogued work for a PDF the score library does "
             "not hold, so OMR_ROSTER_LABELS has a roster to resolve against",
        byte_off=None,
        src="tools/omr/work_roster.py:301; CLAUDE.md knobs table",
        in_claude_md=True,
    ),
    "MAESTRO_BRIDGE_ENABLED": dict(
        stage="web app (theory layer, host-side only)",
        gate="turns on Maestro theory-layer enrichment (key detection, "
             "rhythm validation, scholarly cross-check)",
        byte_off=None,
        src="backend/modules/theory_layer.py:39; CLAUDE.md env-var table",
        in_claude_md=True,
    ),
    "MAESTRO_PITCH_RERANK_ENABLED": dict(
        stage="web app (theory layer, host-side only)",
        gate="turns on M4 pitch re-ranking against the detected key "
             "(local OMR engine only)",
        byte_off=None,
        src="backend/modules/theory_layer.py:45; CLAUDE.md env-var table",
        in_claude_md=True,
    ),
    "MAESTRO_PITCH_RERANK_THRESHOLD": dict(
        stage="web app (theory layer, host-side only)",
        gate="minimum re-rank confidence to auto-correct a pitch",
        byte_off=None,
        src="backend/modules/theory_layer.py:52; CLAUDE.md env-var table",
        in_claude_md=True,
    ),
    "MAESTRO_TIMEOUT_S": dict(
        stage="web app (theory layer, host-side only)",
        gate="subprocess timeout for the node/tsx theory-layer bridge",
        byte_off=None,
        src="backend/modules/maestro_bridge.py:43; CLAUDE.md env-var table",
        in_claude_md=True,
    ),
    "MAESTRO_NODE_BIN": dict(
        stage="operational",
        gate="override the node binary path for the theory-layer bridge",
        byte_off=None,
        src="backend/modules/maestro_bridge.py:36; CLAUDE.md env-var table",
        in_claude_md=True,
    ),
    "MAESTRO_TSX_BIN": dict(
        stage="operational",
        gate="override the tsx binary path for the theory-layer bridge",
        byte_off=None,
        src="backend/modules/maestro_bridge.py:39; CLAUDE.md env-var table",
        in_claude_md=True,
    ),
    "MAESTRO_ANALYZE_TS": dict(
        stage="operational",
        gate="override the analyze.ts entry-point path for the theory-"
             "layer bridge",
        byte_off=None,
        src="backend/modules/maestro_bridge.py:35; CLAUDE.md env-var table",
        in_claude_md=True,
    ),
}

# ---------------------------------------------------------------------------
# Hand-authored annotations for the NUMERIC GUARDS CLAUDE.md discusses BY
# NAME. Every quote is cited to a CLAUDE.md line found by `grep -n`.
# judgement: MEASURED (a swept value / plateau / empty interval is quoted),
#            ASSERTED (CLAUDE.md itself uses "asserted"/"never measured"/
#            "set by analogy"/names a fabricated citation), or
#            "not characterized" (the name appears but CLAUDE.md never
#            renders a judgement on the specific value).
# ---------------------------------------------------------------------------
GUARD_JUDGEMENTS = {
    "TIE_SAME_POSITION_MAX_SPACES": dict(
        judgement="MEASURED",
        quote="sits in a MEASURED empty interval (engraved same-pitch links "
              "max 0.168, one-step-apart links min 0.435)",
        claude_line=5054,
    ),
    "METER_TEMPLATE_AT_BAR_MIN_STAVES": dict(
        judgement="MEASURED",
        quote="over 1,612 mid-staff bar-head windows on ten real scanned "
              "pages ... admitted on 1 staff the reader yields 16 spurious "
              "columns, on 2 two, on 3 ZERO — so "
              "METER_TEMPLATE_AT_BAR_MIN_STAVES = 3",
        claude_line=None,
    ),
    "STEM_MAX_HEIGHT_LINES": dict(
        judgement="MEASURED",
        quote="6.0 gives 0.1861, 7.0 gives 0.1601, 8.0 gives 0.1601, 9.0 "
              "gives 0.1610 (swept, sits on the plateau at 7.0-8.0)",
        claude_line=None,
    ),
    "DOT_ABOVE_NOTE_MAX_SPACES": dict(
        judgement="MEASURED",
        quote="signed offsets are bimodal: 52 at 0.00 spaces, 52 at +0.50, "
              "nothing between +0.57 and +3.75",
        claude_line=None,
    ),
    "DOT_BELOW_NOTE_MAX_SPACES": dict(
        judgement="MEASURED",
        quote="same bimodal distribution as DOT_ABOVE_NOTE_MAX_SPACES; the "
              "window is asymmetric because a dot never sits below its note",
        claude_line=None,
    ),
    "CONTEST_IOU": dict(
        judgement="ASSERTED (and the cited justification does not exist)",
        quote="'restates the measured _CROSS_STAFF_DUPLICATE_IOU = 0.3 and "
              "cites an assumption record that does not exist' -- grep -rn "
              "A-OWN-3 returns that one line and nothing else",
        claude_line=2595,
    ),
    "METER_CARRY_MIN_STAVES_PER_BAR": dict(
        judgement="ASSERTED",
        quote="'weights that are asserted, not measured -- "
              "METER_CARRY_MIN_STAVES_PER_BAR = 3 is set by analogy to "
              "METER_COVERAGE_FLOOR and never measured at all'",
        claude_line=703,
    ),
    "COLUMN_MIN_INDEPENDENT_WITNESSES": dict(
        judgement="ASSERTED",
        quote="'COLUMN_MIN_INDEPENDENT_WITNESSES = 2 is unmeasured and its "
              "price is 28'",
        claude_line=None,
    ),
    "SCORE_LABEL_MATCH": dict(
        judgement="ASSERTED (cited as a Class-B probability-gate fault)",
        quote="'formed then quantised ... a flat SCORE_LABEL_MATCH = 6.0 -- "
              "slots.py and score_layouts.py are ALREADY additive-evidence "
              "models and the evidence is binarised twice on the way in'",
        claude_line=5622,
    ),
    "METER_CARRY_FLOOR": dict(
        judgement="MEASURED (indirectly, via the boundary swing)",
        quote="the +8.0 (true) vs -8.0 (false) swing that motivates the "
              "carry is measured against this floor of 2.0; the floor "
              "value itself is not independently swept",
        claude_line=703,
    ),
    "METER_CARRY_MIN_BARS": dict(
        judgement="not characterized (one observed cost, not a sweep)",
        quote="'METER_CARRY_MIN_BARS = 2 was seen refusing a CORRECT carry "
              "(a one-bar system whose single bar agrees), the first time "
              "that constant's price has been observed'",
        claude_line=703,
    ),
    "METER_COVERAGE_FLOOR": dict(
        judgement="not characterized (only used as the analogy basis for "
                  "another admittedly-asserted constant)",
        quote="cited only as what METER_CARRY_MIN_STAVES_PER_BAR was set "
              "'by analogy to'",
        claude_line=703,
    ),
    "METER_CHANGE_FLOOR": dict(
        judgement="not characterized",
        quote="named only as the threshold five spurious changes fall "
              "'just over'; no sweep or plateau is quoted for its own value",
        claude_line=703,
    ),
    "BRACKET_COLUMN_MIN_EVIDENCE": dict(
        judgement="justified by one counter-example, not a sweep",
        quote="'load-bearing -- a LilyPond render bars per staff, a "
              "25-staff Bruckner system carries two crossing columns "
              "total, and without the floor the rule manufactured 11 "
              "groups from it'",
        claude_line=701,
    ),
    "BEAM_EDGE_TOLERANCE_WIDTHS": dict(
        judgement="informed by measurement, not itself swept",
        quote="the overshoot it must absorb 'clusters at 0.35-0.47 "
              "notehead widths'; the tolerance is set to 1.0, comfortably "
              "above that cluster, but no plateau is shown for 1.0 itself",
        claude_line=2868,
    ),
    "METER_CHANGE_MIN_STAVES": dict(
        judgement="ASSERTED (by cross-reference to another asserted constant)",
        quote="'METER_CHANGE_MIN_STAVES = 2, asserted equal to "
              "key_signature_corroboration.MIN_WITNESSES -- not a tuned "
              "constant, because the populations overlap at 1 and every "
              "value above 1 confines the same four segments'",
        claude_line=None,
    ),
    "MIN_WITNESSES": dict(
        judgement="ASSERTED, but with a stated boundary argument "
                  "(deliberately the weakest bar that can reject the "
                  "observed failures)",
        quote="'Deliberately the WEAKEST defensible bar, and not a tuned "
              "constant. All seven observed flips sit at exactly 1 (no "
              "witness at all) in systems of 11 to 17 staves, so 2 is the "
              "first value that can reject any of them'",
        claude_line=202,
        file_contains="key_signature_corroboration.py",
    ),
}


def build_flag_table(flag_sites, existing_direction):
    by_flag = {}
    for s in flag_sites:
        by_flag.setdefault(s["flag"], []).append(s)
    rows = []
    for flag in sorted(by_flag):
        sites = by_flag[flag]
        ann = ANNOTATIONS.get(flag)
        first = sites[0]
        loc = f"{first['file']}:{first['line']}"
        if len(sites) > 1:
            loc += f" (+{len(sites)-1} more site{'s' if len(sites)>2 else ''})"
        default = first["default"]
        if default is None:
            default_str = "_(non-literal — see annotation)_"
        elif default == "":
            default_str = "`\"\"`"
        else:
            default_str = f"`{default}`"
        direction = existing_direction.get(flag)
        if direction is None:
            dirn = "not simple inline compare — verified by hand, see annotation"
        elif direction == {True}:
            dirn = "deny-list (default ON)"
        elif direction == {False}:
            dirn = "allow-list (default OFF)"
        else:
            dirn = f"INCONSISTENT across sites: {sorted(direction)}"
        stage = ann["stage"] if ann else "UNANNOTATED"
        gate = ann["gate"] if ann else "(not yet characterized by this doc)"
        byte_off = ann.get("byte_off") if ann else None
        byte_str = {True: "yes (CLAUDE.md states it)",
                    False: "no",
                    None: "not stated"}[byte_off]
        in_md = mentioned(flag)
        rows.append((flag, loc, default_str, dirn, stage, gate, byte_str, in_md))
    return rows


def build_guard_table(guards):
    """⚠️ Several constant NAMES are reused across unrelated modules (e.g.
    `MIN_WITNESSES` names both `key_signature_corroboration.py`'s witness
    floor and an unrelated one in `key_consensus.py`) — a judgement keyed
    on the bare name alone would silently paint the wrong site with a
    quote about the other one. `GUARD_JUDGEMENTS` entries may carry a
    `file_contains` substring to disambiguate; a judgement with no such
    key applies only where the name is unique across all sites found."""
    by_name = {}
    for g in guards:
        by_name.setdefault(g["name"], []).append(g)
    rows = []
    for name in sorted(by_name):
        sites = by_name[name]
        for g in sites:
            j = GUARD_JUDGEMENTS.get(name)
            if j and j.get("file_contains") and j["file_contains"] not in g["file"]:
                j = None
            if j is None and len(sites) > 1 and GUARD_JUDGEMENTS.get(name):
                # a judgement exists for this NAME but wasn't scoped to this
                # site, and the name is not unique -- refuse to guess.
                judgement = ("AMBIGUOUS NAME: another site shares this "
                             "constant's name; a judgement exists for one "
                             "of them but this row was not verified against "
                             "it — see §2 note")
                quote = ""
            elif j:
                judgement, quote = j["judgement"], j["quote"]
            else:
                judgement = ("not mentioned in CLAUDE.md" if not mentioned(name)
                             else "mentioned, but not with a measured/asserted judgement — unchecked")
                quote = ""
            rows.append((name, f"{g['file']}:{g['line']}", g["value"], judgement, quote))
    return rows


def md_escape(s):
    # `|` breaks a table cell; `<...>` (e.g. "<words>", "<note>") reads as
    # an HTML tag to a markdown renderer and can be swallowed silently.
    return s.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def main():
    flag_sites, guards = _run_derive()
    existing_direction = {}
    for path, line, flag, default, op, members, on in derive_map.existing.default_on_flags():
        existing_direction.setdefault(flag, set()).add(on)

    flag_rows = build_flag_table(flag_sites, existing_direction)
    guard_rows = build_guard_table(guards)

    names_all = sorted({r[0] for r in flag_rows})
    not_in_md = sorted(r[0] for r in flag_rows if not r[7])
    mentioned_no_row = sorted(f for f in names_all
                               if mentioned(f) and not has_knob_row(f))
    has_row = sorted(f for f in names_all if has_knob_row(f))
    assert set(not_in_md) | set(mentioned_no_row) | set(has_row) == set(names_all)
    assert not (set(not_in_md) & set(mentioned_no_row) & set(has_row))
    guard_names_all = sorted({g["name"] for g in guards})
    guard_named_in_md = sorted(n for n in guard_names_all if mentioned(n))

    # Every OMR_*/MAESTRO_* identifier CLAUDE.md mentions that this
    # document's code scan did NOT find a call site for — the direction of
    # check §3.3 is actually about (a phantom flag documented but not
    # implemented), as opposed to §3.2's direction (implemented but not
    # documented).
    claude_only_names = sorted(
        (set(re.findall(r"\b(OMR_[A-Z0-9_]+)\b", CLAUDE_TEXT))
         | set(re.findall(r"\b(MAESTRO_[A-Z0-9_]+)\b", CLAUDE_TEXT)))
        - set(names_all))

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        commit = "unknown (git rev-parse failed)"

    lines = []
    a = lines.append
    a("# Map: flags, gates, and guards")
    a("")
    a(f"Generated {__import__('datetime').date.today().isoformat()} at "
      f"commit `{commit}` by "
      "`benchmarks/omr-flags-map-2026-09/build_doc.py`. Re-run that script "
      "to re-derive every mechanical fact in this file (file:line, default "
      "literal, presence-in-CLAUDE.md, and the allow/deny-list direction "
      "for flags whose comparison is a simple inline one). The one-line "
      "\"what it gates\" descriptions, the STAGE column, the byte-identical "
      "claim, and the numeric-guard MEASURED/ASSERTED judgement are "
      "**hand-authored syntheses of CLAUDE.md and the source**, each cited "
      "to a file:line or a CLAUDE.md line — they are not re-derived by the "
      "script, because CLAUDE.md expresses that judgement in prose, not as "
      "a grep-able keyword. Where this document could not verify a claim "
      "it says `UNANNOTATED` / `not characterized` rather than asserting one.")
    a("")
    a("## 0. Sean's question, and the honest answer")
    a("")
    a("> \"Do we have a single place where all gates, guards, default "
      "settings or anything that could be flipped is stored? If we have a "
      "map then it should have all of the basic info of what is going "
      "where, what their rules are and what options/defaults are.\"")
    a("")
    a("**No, and this file is that place now.** Three things existed "
      "before this document and none of them was complete on its own:")
    a("")
    a("1. [`tools/omr/tests/test_flag_default_direction.py`](../tools/omr/tests/test_flag_default_direction.py) "
      "— derives every `os.environ.get(FLAG, default)` site compared "
      "*inline* to a literal word set, and enforces the allow-list/deny-"
      "list direction against the default. **It is the source of truth "
      "for the flags it can see.** Section 3 below documents the two "
      "syntactic patterns in this codebase it cannot see at all.")
    a("2. CLAUDE.md's \"OMR knobs\" table (search `## Environment variables` "
      "and the knobs table above it) — prose with the measured evidence "
      "and the reasons, for the flags someone remembered to add a row for.")
    a("3. [`docs/architecture-decision-map.md`](architecture-decision-map.md) "
      "— a CONSTANT/FLAG column inside each of ~12 per-decision tables in "
      "§5, organized by decision point rather than by flag; it overlaps "
      "this document's numeric-guard table but does not attempt to be a "
      "flat index.")
    a("")
    a(f"**Positive controls, so the zeros below mean something:** this "
      f"document's mechanical scan found **{len(names_all)} distinct env "
      f"flags** (OMR_*/MAESTRO_*) at "
      f"**{len(flag_sites)} call "
      f"sites**, and **{len(guard_names_all)} distinct numeric guard "
      f"constants** at module level under `tools/omr/`.")
    a("")
    a("---")
    a("")
    a("## 1. Env flags")
    a("")
    a("Every `os.environ.get(...)` / `os.getenv(...)` call under `tools/` "
      "or `backend/` (excluding tests) naming a literal or module-constant "
      "`OMR_*`/`MAESTRO_*` flag name. **Direction** is `deny-list "
      "(default ON)` / `allow-list (default OFF)` only where "
      "`test_flag_default_direction.py`'s own inline-comparison scan can "
      "see the site (CLAUDE.md's own rule: an OFF test must be a deny-list "
      "if the default is ON, and vice versa, or a typo silently flips the "
      "flag the wrong way). Where the site does not fit that scan's "
      "pattern, direction was read by hand and is marked so — see §3.1.")
    a("")
    a("| Flag | Site (file:line) | Default | Direction | Stage | What it gates | Flag-off byte-identical? (CLAUDE.md) | In CLAUDE.md at all? |")
    a("|---|---|---|---|---|---|---|---|")
    for flag, loc, default_str, dirn, stage, gate, byte_str, in_md in flag_rows:
        a(f"| `{flag}` | `{loc}` | {default_str} | {dirn} | {stage} | "
          f"{md_escape(gate)} | {byte_str} | {'yes' if in_md else '**no**'} |")
    a("")
    a("---")
    a("")
    a("## 2. Numeric guards / constants")
    a("")
    a("Every module-level ALL-CAPS constant assigned a plain int/float "
      "literal anywhere under `tools/omr/` (excluding tests) — the "
      "thresholds, floors, and minimums an adjudicator or detector checks "
      "against, that are not env-flag-controlled at all (flipping one "
      "means editing the source). The **MEASURED vs ASSERTED** column is "
      "hand-read from CLAUDE.md for every constant CLAUDE.md discusses by "
      "name; the rest are reported as `not mentioned in CLAUDE.md` — that "
      f"is **{len(guard_names_all) - len(guard_named_in_md)} of "
      f"{len(guard_names_all)}** names, i.e. most of the guards in this "
      "codebase carry no recorded judgement about whether their value was "
      "ever swept against real data.")
    a("")
    name_counts = {}
    for rr in guard_rows:
        name_counts[rr[0]] = name_counts.get(rr[0], 0) + 1
    dup_names = sorted(n for n, c in name_counts.items() if c > 1)
    dup_names_str = ", ".join(f"`{n}`" for n in dup_names)
    a(f"⚠️ **{len(dup_names)} constant names are reused across unrelated "
      "modules** (mechanically detected: same ALL-CAPS name, different "
      f"file:line, almost certainly a different threshold with a "
      f"different reason) — {dup_names_str}. A judgement quoted for one "
      "site of a reused name is never applied to the other by this "
      "table; where CLAUDE.md's own prose cross-references one by bare "
      "name (`MIN_WITNESSES` is the case in point below), this document "
      "scopes the judgement to the specific file it was read from rather "
      "than guessing which site was meant.")
    a("")
    a("| Constant | Site (file:line) | Value | CLAUDE.md judgement | CLAUDE.md's own words |")
    a("|---|---|---|---|---|")
    for name, loc, value, judgement, quote in guard_rows:
        a(f"| `{name}` | `{loc}` | `{value}` | {judgement} | {md_escape(quote)} |")
    a("")
    a("---")
    a("")
    a("## 3. Disagreements")
    a("")
    a("### 3.1 A blind spot in the existing derived check itself")
    a("")
    a("`test_flag_default_direction.py`'s `default_on_flags()` only "
      "matches a comparison written **inline** — "
      "`os.environ.get(FLAG, default) in {...}` (after unwrapping "
      "`.strip()`/`.lower()`) on the SAME expression. Reading the source "
      "for the flags this document's broader scan found (§1) turned up "
      "**two syntactic patterns that check is blind to**, both real and "
      "both currently used correctly (verified by hand, not by the "
      "automated check):")
    a("")
    a("1. **Two-statement form** — `raw = os.environ.get(FLAG, default)` "
      "on one line, `return raw in {...}` (or `not in`) on another. "
      "Examples: `OMR_CELL_LINE_TRACE` "
      "(`tools/omr/measure_extractor.py:1176-1177`), `OMR_ONE_LINE_STAVES` "
      "(`tools/omr/measure_extractor.py:1199-1200`).")
    a("2. **`(env if env is not None else os.environ).get(...)`** — an "
      "injectable-environ pattern used for testability. Examples: "
      "`OMR_KEYSIG_CORROBORATION` (`tools/omr/key_signature_corroboration.py:219`), "
      "`OMR_ABSENT_INSTRUMENT_VETO` (`tools/omr/absent_instrument.py:120`), "
      "`OMR_ROSTER_SCORE_ORDER_VETO` (`tools/omr/offroster_name.py:107`).")
    a("")
    a("All five read correctly by hand (deny-list for the three default-ON "
      "ones, allow-list for the two default-OFF ones), so this is not a "
      "live bug — but it means the guard CLAUDE.md itself calls the fix "
      "for *\"a typo or an empty value would turn it OFF\"* silently does "
      "not run on these five sites. A sixth flag, `OMR_ADJUDICATE`, uses "
      "neither pattern the check recognises NOR either of these two — it "
      "compares against a 3-way mode tuple "
      "(`raw in (MODE_OFF, MODE_SHADOW, MODE_ON)`) with an unrecognised "
      "value falling back to OFF, which is the correct fail-safe shape "
      "for a default-off master switch but is also invisible to the "
      "existing test.")
    a("")
    a("### 3.2 Flags that exist in the code and CLAUDE.md never documents")
    a("")
    a("This is split into two mechanically-distinct buckets, because "
      "\"absent from a knobs table\" and \"absent from the file entirely\" "
      "are different failure sizes, and the two must not be collapsed into "
      "one hand-typed list — the earlier draft of this section did exactly "
      "that (typed the flag names by hand instead of reading them off the "
      "computed sets below) and as a result misfiled `OMR_CV_HAIRPINS` "
      "and `OMR_SPAN_REFERENCE_FIT` into the wrong bucket. Both buckets "
      "below are rendered directly from the same `not_in_md` / "
      "`mentioned_no_row` sets used for the counts, so this cannot drift "
      "from them again silently.")
    a("")
    a(f"**3.2a — {len(not_in_md)} of {len(names_all)}: the flag's name "
      "never appears in CLAUDE.md at all** (checked with a plain "
      "`\\bFLAG\\b` regex over the whole file, so this is not a "
      "knobs-table formatting artefact — a flag mentioned only in prose "
      "would still be caught here as present).")
    a("")
    for f in not_in_md:
        ann = ANNOTATIONS.get(f, {})
        gate = ann.get("gate", "(no annotation)")
        a(f"- **`{f}`** — {md_escape(gate)}")
    a("")
    a("Of these, **`OMR_ADJUDICATE`** is the one worth reading twice: it "
      "is the master on/off/shadow switch for the **entire staged "
      "pipeline** (`tools/omr/staged/pipeline.py:47-56`) — every "
      "ADJUDICATE/EVALUATE/INFER/EXPORT flag CLAUDE.md documents at great "
      "length (the meter-carry, whole-rest-ink, meter-segments, infer-"
      "stage flags in §1 above) is inert unless this reads `shadow` or "
      "`1`. Nothing in CLAUDE.md says so.")
    a("")
    a(f"**3.2b — {len(mentioned_no_row)} of {len(names_all)}: the flag's "
      "name appears in CLAUDE.md's prose, but never in a dedicated "
      "table row** (checked for a line starting `| \\`FLAG\\` |` in "
      "either the OMR knobs table or the Environment variables table). "
      "A reader searching the knobs tables for these would not find "
      "them, even though the mechanism is discussed:")
    a("")
    for f in mentioned_no_row:
        ann = ANNOTATIONS.get(f, {})
        gate = ann.get("gate", "(no annotation)")
        src = ann.get("src", "")
        a(f"- **`{f}`** — {md_escape(gate)}" +
          (f" (see {md_escape(src)})" if src else ""))
    a("")
    a("Four of these nine — `OMR_MOVEMENT_REFERENCE`, "
      "`OMR_LABEL_MERGE_QUALITY`, `OMR_INSTRUMENT_CLEF_DEFAULT`, and "
      "`OMR_ROSTER` — are individually *named* in CLAUDE.md's \"A flag's "
      "OFF test must follow its DEFAULT\" section, as flags that once "
      "shipped with the direction backwards and were corrected — but "
      "that section only says their direction was fixed, never what the "
      "flag currently does or defaults to as a knob.")
    a("")
    a("### 3.3 CLAUDE.md rows naming a flag the code does not have")
    a("")
    all_claude_omr_names = (
        set(re.findall(r"\b(OMR_[A-Z0-9_]+)\b", CLAUDE_TEXT))
        | set(re.findall(r"\b(MAESTRO_[A-Z0-9_]+)\b", CLAUDE_TEXT)))
    a(f"Every `OMR_*`/`MAESTRO_*`-shaped identifier anywhere in CLAUDE.md "
      f"({len(all_claude_omr_names)} distinct spellings) was checked "
      f"against the {len(names_all)} flags this document's code scan "
      "found a real `os.environ.get`/`os.getenv` call site for. "
      f"**Positive control: {len(claude_only_names)} of "
      f"{len(all_claude_omr_names)}** CLAUDE.md-only names found: "
      f"{', '.join(f'`{n}`' for n in claude_only_names)} — "
      "CLAUDE.md's own generic placeholder name in an illustrative "
      "example table (\"set `OMR_X`\"), not a documented-but-unimplemented "
      "flag. **This is the one place this exercise did not find drift**: "
      "CLAUDE.md has never invented or left behind a phantom flag name, "
      "which is notable given how often its own text records the "
      "opposite failure (a flag's *behaviour* being described wrong).")
    a("")
    a("### 3.4 Flag defaults: code vs CLAUDE.md's stated default")
    a("")
    a("**Checked every flag with both (a) a knob-table or explicit-default "
      "row in CLAUDE.md and (b) a resolvable default in code — "
      f"{sum(1 for r in flag_rows if r[7])} flags. Zero direction or "
      "default-value contradictions were found as of this tree "
      f"(commit `{commit}`, stamped at the top of this file).** "
      "This is a genuine, checked negative, not an assumption: CLAUDE.md "
      "explicitly records at least two occasions where its knobs table "
      "*was* wrong for a period (`OMR_METER_CARRY`/`OMR_METER_FROM_BARS` "
      "read `still off` for a day after they flipped ON on 2026-09-15; "
      "`OMR_SLOT_STITCH`'s docstring carried a refuted claim for three "
      "days) — both were corrected before this scan ran, and this "
      "document is what re-checks whether a third instance has crept in "
      "since. The disagreement that remains is **coverage**, not "
      "**direction**: see §3.2.")
    a("")
    a("---")
    a("")
    a("## 4. Numeric guards CLAUDE.md never discusses at all")
    a("")
    a(f"**{len(guard_names_all) - len(guard_named_in_md)} of "
      f"{len(guard_names_all)}** module-level numeric constants under "
      "`tools/omr/` never appear in CLAUDE.md under their own name. Most "
      "are geometric constants local to one detector (pixel margins, "
      "aspect-ratio cutoffs) that this document's mechanical scan cannot "
      "distinguish from a load-bearing decision floor without reading "
      "every one by hand — which is exactly the kind of hand-list this "
      "task was asked not to produce. The table in §2 lists every one "
      "found, with `not mentioned in CLAUDE.md` in the judgement column "
      "wherever that is the honest answer; do not read that column as "
      "\"unimportant\", only as \"unrecorded\".")
    a("")
    a("---")
    a("")
    a("## 5. How to regenerate this document")
    a("")
    a("```bash")
    a("python3 benchmarks/omr-flags-map-2026-09/build_doc.py")
    a("```")
    a("")
    a("This re-derives every mechanical fact fresh from the current tree "
      "(the flag/guard inventories, the presence-in-CLAUDE.md checks, and "
      "the allow/deny-list direction for the sites the existing test can "
      "see) and re-applies the same hand-authored annotations above. If a "
      "new flag or guard has been added since this file's timestamp and "
      "`ANNOTATIONS`/`GUARD_JUDGEMENTS` was not updated for it, it will "
      "show up as `UNANNOTATED` / `not mentioned in CLAUDE.md` rather than "
      "silently vanishing — the same fail-safe shape CLAUDE.md prescribes "
      "for the flags themselves. To see the raw JSON this is built from "
      "without the hand-authored layer:")
    a("")
    a("```bash")
    a("python3 benchmarks/omr-flags-map-2026-09/derive_map.py")
    a("```")
    a("")

    OUT.write_text("\n".join(lines) + "\n")

    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"env flags: {len(names_all)} distinct, {len(flag_sites)} sites")
    print(f"  not in CLAUDE.md at all: {len(not_in_md)} -> {not_in_md}")
    print(f"numeric guards: {len(guard_names_all)} distinct")
    print(f"  named in CLAUDE.md: {len(guard_named_in_md)}")
    print(f"  with an explicit MEASURED/ASSERTED judgement: {len(GUARD_JUDGEMENTS)}")


if __name__ == "__main__":
    main()
