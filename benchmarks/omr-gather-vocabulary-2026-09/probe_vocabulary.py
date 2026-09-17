#!/usr/bin/env python3
"""Does GATHER have a CATEGORY for everything a conductor's page can print?

Sean, 2026-09-16: *"does GATHER have all of the categories it needs to collect
everything that could be on a page?"*  This is the VOCABULARY question, not
the wiring one -- `tools/omr/staged/wiring.py` and `tools/omr/no_producer.py`
already ask whether a gathered value REACHES its consumer, and this asks
whether the ink has a name at all.

⚠️ IT STARTS WHERE `gather_coverage` STOPS, AND CORRECTS ITS CLASS SPACE.
`gather_coverage._detector_classes()` reads `deepscores_classes.py`, whose
`DEEPSCORES_V2_CLASSES` holds **146** names, under a docstring calling it
"the 208-class space".  The real vocabulary is committed one directory over
(`training/deepscoresv2_208_classes.json`, the file `class_aliases.vocabulary()`
already reads) and holds 208.  So that tool's family audit is derived from
70% of the vocabulary.  This probe recomputes it from the full 208 and prints
the DELTA, so the correction is a measurement rather than an assertion.

THE THREE-WAY GAP.  A category can be missing in three places and the repairs
differ, so they are never pooled:

  (a) NAMED BY THE DETECTOR, NO QUANTITY -- the class fires, `gather_detections`
      files it under `Q.GLYPH_BOX`, and no typed row ever carries it.
      Repair: declare a `Q` and a gatherer.  `gather_coverage` list 5 reports
      this already; this probe re-derives it over 208 and splits it into real
      notation vs not-notation with a reason each.

  (b) NO DETECTOR CLASS AND NO CV RUNG -- the ink is invisible to the whole
      pipeline.  **This is Sean's question and no existing tool reports it.**
      Repair: a reader, i.e. training data or a CV rung -- not a record change.

  (c) GATHERED AS THE WRONG KIND OF FACT -- the ink has a name and the record
      still cannot say what it means.  The worked case is in CLAUDE.md: an
      in-bar accidental is a SCOPE holding to the barline, and `Subject`
      addresses a POINT (`Kind` is DOCUMENT..GLYPH, a hierarchy of places,
      with no range).  Repair: a new shape of row.

GROUNDING (b) IN REPERTOIRE, NOT IN MEMORY.  CLAUDE.md records that the
predecessor document named `breath` and `glissando` as detector families from
musical memory and that neither is in the class space.  So every element here
comes from a COUNT over the committed reference encodings
(`library/reference/**.mxl`), parsed with `export_coverage.notation_index`
(imported, never restated), and every claim that a class does or does not
exist is checked against the 208 names by string.

⚠️ AN ENCODING TRUTH IS NOT A PAGE TRUTH, and this probe cannot fix that.
MusicXML writes a `<slur>` at each END where the engraver draws one arc; a
`<clef>` is declared once and printed every system; `<print>`/`<sound>` are
not ink at all.  So a COUNT here ranks how often a notation OCCURS in real
orchestral music, and is not a count of marks on a page.  Ranking is all it
is used for.

RUN
    python3 benchmarks/omr-gather-vocabulary-2026-09/probe_vocabulary.py
    python3 benchmarks/omr-gather-vocabulary-2026-09/probe_vocabulary.py --check

`--check` exits non-zero when an element the corpus shows is in no
adjudication bucket -- the `unaccounted()` discipline, so the table cannot go
stale as the corpus widens -- and ALSO when the automated class matcher
contradicts a hand verdict (a `NO_CATEGORY` element for which the 208 names do
hold a class is a wrong verdict, and the probe says so rather than printing it).

POSITIVE CONTROLS.  A zero is a result only beside the count of what the same
instrument DID find, so every section prints its own denominator, and the
probe exits 2 if the corpus parsed nothing.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from tools.omr.export_coverage import notation_index          # noqa: E402
from tools.omr import class_aliases                           # noqa: E402
from tools.omr.staged import gather_coverage as GC            # noqa: E402
from tools.omr.staged.record import Q, READERS, Kind          # noqa: E402

#: The reference corpus lives beside the main checkout and is gitignored.
#: `library_root()` resolves a worktree to the main checkout; this probe only
#: needs the reference half, so it takes the same path without importing the
#: library package (which pulls in more than a stdlib-only probe should).
REFERENCE = Path("/Users/seanjohnson/Desktop/ReEngrave/library/reference")

#: A part count at or above this reads as a conductor's score rather than a
#: chorale, a sonata or a lead sheet.  DERIVED from the encoding itself
#: (`<score-part>` count), never from the filename or the folder.
#: ⚠️ A THRESHOLD, not a fact: a Baroque concerto grosso sits under it and a
#: piano-vocal score can sit over it.  Both totals are printed so the split
#: can be checked rather than trusted.
ORCHESTRAL_MIN_PARTS = 8


# ─────────────────────────────────────────────────────────────────────────────
# 1. THE VOCABULARY -- reach first
# ─────────────────────────────────────────────────────────────────────────────

def detector_vocabulary() -> List[str]:
    """The 208 class names, through `class_aliases` rather than by re-reading.

    ⚠️ NOT `deepscores_classes.DEEPSCORES_V2_CLASSES`, which is a 146-name
    snapshot of an older release and is what `gather_coverage` audits against.
    """
    return class_aliases.vocabulary()


def snapshot_vocabulary() -> List[str]:
    """What `gather_coverage` actually audits -- for the delta, not for use."""
    return list(GC._detector_classes())


def cv_rungs() -> Dict[str, List[str]]:
    """Every non-DETECTOR reader, and the quantities it is observed producing.

    DERIVED from `gather_coverage.gathered()`, which reads the gatherers' own
    emit sites -- so a rung nobody runs cannot appear, and a rung added
    tomorrow appears without editing this probe.
    """
    out: Dict[str, List[str]] = {}
    for name, row in GC.gathered().items():
        for reader in row["readers"]:
            if reader.upper() == "DETECTOR":
                continue
            out.setdefault(reader, []).append(name)
    return {k: sorted(v) for k, v in sorted(out.items())}


def _family(class_name: str) -> str:
    """`gather_coverage`'s own family rule, imported rather than restated."""
    return GC._family(class_name)


def families_over(vocab: Iterable[str]) -> Dict[str, List[str]]:
    fams: Dict[str, List[str]] = {}
    for c in vocab:
        fams.setdefault(_family(c), []).append(c)
    return {k: sorted(set(v)) for k, v in sorted(fams.items())}


def case_a_over_full_vocabulary() -> Dict[str, object]:
    """Case (a), recomputed over the FULL 208 instead of the 146 snapshot.

    Uses `gather_coverage.FAMILY_Q` -- its own hand-maintained family -> Q
    table with its stated reasons -- so this changes the POPULATION and not
    the judgement.  A family the table does not mention is reported as new.
    """
    full = families_over(detector_vocabulary())
    snap = families_over(snapshot_vocabulary())
    table = GC.FAMILY_TO_Q

    unnamed_full = {f: cs for f, cs in full.items() if not table.get(f)}
    unnamed_snap = {f: cs for f, cs in snap.items() if not table.get(f)}
    return {
        "families_full": len(full),
        "families_snapshot": len(snap),
        "classes_full": len(set(detector_vocabulary())),
        "classes_snapshot": len(set(snapshot_vocabulary())),
        "unnamed_full": unnamed_full,
        "unnamed_snapshot": unnamed_snap,
        "families_only_in_full": sorted(set(full) - set(snap)),
        "families_unknown_to_table": sorted(f for f in full if f not in table),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. THE CORPUS -- what real orchestral encodings contain
# ─────────────────────────────────────────────────────────────────────────────

def _mxl_text(path: Path) -> Optional[str]:
    """The root score document, compressed (.mxl) or not (.musicxml/.xml)."""
    if path.suffix.lower() != ".mxl":
        return path.read_text("utf-8", "replace")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        root = None
        if "META-INF/container.xml" in names:
            try:
                c = ET.fromstring(z.read("META-INF/container.xml"))
                for node in c.iter():
                    tag = node.tag.rsplit("}", 1)[-1]
                    if tag == "rootfile" and node.get("full-path"):
                        root = node.get("full-path")
                        break
            except ET.ParseError:
                root = None
        if root is None or root not in names:
            cands = [n for n in names
                     if n.endswith((".xml", ".musicxml"))
                     and not n.startswith("META-INF")]
            if not cands:
                return None
            root = cands[0]
        return z.read(root).decode("utf-8", "replace")


_SCORE_PART = re.compile(r"<score-part\b")


def survey_corpus(limit: Optional[int] = None,
                  seed: int = 20260916) -> Dict[str, object]:
    """Element counts over the reference corpus, split by part count.

    Returns per-element totals for the whole corpus and for the orchestral
    subset, plus the denominators every zero has to be read against.
    """
    files = sorted(p for pat in ("*.mxl", "*.musicxml", "*.xml")
                   for p in REFERENCE.rglob(pat))
    if limit is not None and limit < len(files):
        files = random.Random(seed).sample(files, limit)

    all_counts: Counter = Counter()
    orch_counts: Counter = Counter()
    all_files: Counter = Counter()          # element -> files it appears in
    orch_files: Counter = Counter()
    n_ok = n_orch = n_fail = 0
    fail_examples: List[str] = []

    for path in files:
        try:
            xml = _mxl_text(path)
            if xml is None:
                raise ValueError("no root document in container")
            index = notation_index(xml)
        except Exception as exc:                              # noqa: BLE001
            n_fail += 1
            if len(fail_examples) < 5:
                fail_examples.append(f"{path.name}: {type(exc).__name__}: {exc}")
            continue
        n_ok += 1
        parts = len(_SCORE_PART.findall(xml))
        orchestral = parts >= ORCHESTRAL_MIN_PARTS
        if orchestral:
            n_orch += 1
        for name, el in index.items():
            all_counts[name] += el.count
            all_files[name] += 1
            if orchestral:
                orch_counts[name] += el.count
                orch_files[name] += 1

    return {
        "files_found": len(files),
        "files_parsed": n_ok,
        "files_orchestral": n_orch,
        "files_failed": n_fail,
        "failures": fail_examples,
        "all_counts": all_counts,
        "orch_counts": orch_counts,
        "all_files": all_files,
        "orch_files": orch_files,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. THE ADJUDICATION -- one verdict per element, with its reason
# ─────────────────────────────────────────────────────────────────────────────
#
# ⚠️ HAND-WRITTEN, AND THE PROBE CHECKS IT RATHER THAN TRUSTING IT.  Mapping a
# MusicXML element onto printed ink is a musical judgement and cannot be
# derived -- what CAN be derived is whether the 208 names hold a plausible
# class for it, and `contradictions()` below fails the run when a hand verdict
# of NO_CATEGORY sits on an element the matcher CAN place.  So the automated
# half bounds the hand half in the direction that matters (a missed category).

#: An element that is not printed ink: encoding bookkeeping, playback, or
#: layout.  `export_coverage.NOT_NOTATION` makes the same distinction for its
#: own three cases and is IMPORTED rather than duplicated; these are the rest.
NOT_INK: Dict[str, str] = {
    "note": "the container, not a mark",
    "rest": "the container for a rest glyph; the GLYPH is `restWhole` etc.",
    "pitch": "the sounding value; the ink is a notehead's POSITION + clef",
    "step": "part of <pitch>", "octave": "part of <pitch>",
    "alter": "the sounding alteration; the INK is <accidental>, counted apart",
    "duration": "divisions arithmetic, never printed",
    "voice": "a stream id; the ink is stem direction and vertical placement",
    "type": "the written value; the INK is notehead + flag + beam",
    "dot": "counted as ink under <augmentation-dot>? no -- this IS the dot",
    "staff": "which staff of a multi-staff part; placement, not a mark",
    "divisions": "the tick resolution of the file",
    "backup": "encoding cursor movement", "forward": "encoding cursor movement",
    "attributes": "a container", "measure": "a container",
    "notations": "a container", "articulations": "a container",
    "ornaments": "a container", "technical": "a container",
    "direction": "a container", "direction-type": "a container",
    "dynamics": "a container; the letters are counted individually",
    "time-modification": "the tuplet ratio as arithmetic; the INK is <tuplet>",
    "actual-notes": "part of <time-modification>",
    "normal-notes": "part of <time-modification>",
    "normal-type": "part of <time-modification>",
    "normal-dot": "part of <time-modification>",
    "key": "a container", "time": "a container",
    "fifths": "the key as a NUMBER; the ink is keySharp/keyFlat, counted apart",
    "mode": "major/minor, never printed",
    "beats": "the meter numerator; the ink is a timeSig digit",
    "beat-type": "the meter denominator; the ink is a timeSig digit",
    "sign": "part of <clef>", "line": "part of <clef>",
    "clef-octave-change": "the 8 under a clef -- INK, counted at <clef>",
    "staves": "how many staves a part prints; structure, not a mark",
    "instrument": "which instrument sounds; not a mark",
    "transpose": "the part's transposition; never printed as such",
    "diatonic": "part of <transpose>", "chromatic": "part of <transpose>",
    "octave-change": "part of <transpose>",
    "offset": "where a direction sounds vs where it prints",
    "display-step": "where an unpitched note SITS -- a notehead position",
    "display-octave": "where an unpitched note SITS -- a notehead position",
    "unpitched": "a percussion note; its ink is a notehead, already named",
    "tuplet-actual": "part of <tuplet>'s display spec",
    "tuplet-normal": "part of <tuplet>'s display spec",
    "tuplet-number": "the tuplet DIGIT -- ink, counted at <tuplet>",
    "tuplet-type": "part of <tuplet>'s display spec",
    "beat-unit": "part of <metronome>", "beat-unit-dot": "part of <metronome>",
    "per-minute": "part of <metronome>",
    "root": "a container", "root-step": "part of <harmony>",
    "root-alter": "part of <harmony>", "kind": "part of <harmony>",
    "bass": "part of <harmony>", "bass-step": "part of <harmony>",
    "bass-alter": "part of <harmony>", "degree": "part of <harmony>",
    "degree-value": "part of <harmony>", "degree-alter": "part of <harmony>",
    "degree-type": "part of <harmony>", "inversion": "part of <harmony>",
    "figure": "part of <figured-bass>", "figure-number": "part of <figured-bass>",
    "prefix": "part of <figured-bass>", "suffix": "part of <figured-bass>",
    "extend": "part of <figured-bass> / <lyric>",
    "lyric": "sung text -- real ink, and OUT OF SCOPE: this project reads "
             "orchestral scores and the vocal rows are a separate question",
    "text": "part of <lyric>", "syllabic": "part of <lyric>",
    "elision": "part of <lyric>", "humming": "part of <lyric>",
    "end-line": "part of <lyric>", "end-paragraph": "part of <lyric>",
    "level": "editorial markup, never ink",
    "footnote": "editorial markup, never ink",
    "listening": "playback", "play": "playback", "listen": "playback",
    "other-play": "playback", "ipa": "playback",
    "midi-instrument": "playback", "instrument-change": "playback",
    "instrument-sound": "playback", "assess": "playback",
    "wait": "playback", "other-listening": "playback",
    "chord": "a marker that this note shares the previous note's onset; the "
             "INK is a second notehead on one stem, and `Q.EVENT` names it",
    "instruments": "how many instruments a part holds; not a mark",
    # Layout. `export_coverage.NOT_NOTATION` settles `print` with the same
    # reason ("it positions ink; it is not ink"); these are its children and
    # its siblings, listed so this probe's population is closed.
    "system-layout": "layout", "system-margins": "layout",
    "left-margin": "layout", "right-margin": "layout",
    "system-distance": "layout", "top-system-distance": "layout",
    "staff-layout": "layout", "staff-distance": "layout",
    "measure-layout": "layout", "measure-distance": "layout",
    "page-layout": "layout", "page-margins": "layout",
    "page-height": "layout", "page-width": "layout",
    "staff-size": "layout — the CUE-SIZE ratio, a rendering property",
    "appearance": "layout", "line-width": "layout", "note-size": "layout",
    "top-margin": "layout", "bottom-margin": "layout",
    "measure-style": "a container for <multiple-rest> / <measure-repeat>",
    "tuplet-dot": "part of <tuplet>'s display spec",
    "notation": "⚠️ NOT a MusicXML element -- an encoder's typo observed in "
                "this corpus, kept here so the population stays closed and the "
                "count is not silently dropped",
    "score-instrument": "a part-header declaration; not a mark",
}

#: Verdicts.  The first three mean "the pipeline has a category"; only
#: NO_CATEGORY is Sean's question.
DETECTOR = "DETECTOR_CLASS"
CV = "CV_RUNG"
NOT_NOTATION = "NOT_INK"
MISSING = "NO_CATEGORY"
#: Case (c): the ink HAS a category and the category is the wrong SHAPE, so
#: the record still cannot say what the mark means.  A different repair from
#: either (a) or (b), and pooling it with (b) would over-count the reader work.
WRONG_SHAPE = "WRONG_SHAPE"

#: element -> (verdict, the 208-class names or rung that cover it, reason)
#:
#: ⚠️ ONLY the ink-bearing elements.  Everything in NOT_INK above is settled
#: there and is not repeated.
ADJUDICATION: Dict[str, Tuple[str, str, str]] = {
    # ── covered by a detector class ────────────────────────────────────────
    "accidental": (WRONG_SHAPE, "accidentalFlat/Natural/Sharp/DoubleSharp/"
                                "DoubleFlat (+Small), 8 fine classes",
                   "CASE (c), and ALSO case (a): `FAMILY_TO_Q['accidental']` "
                   "is None, so the glyph reaches the log only as an anonymous "
                   "`Q.GLYPH_BOX` -- and the fact it states is a SCOPE holding "
                   "to the barline (`transcribe.py:2210`), which no point-"
                   "addressed row can carry"),
    "staff-lines": (WRONG_SHAPE, "staff (134, 207) + GEOMETRY "
                                 "(Q.STAFF_LINES)",
                    "CASE (c): `Q.STAFF_LINES` is FIVE y positions and "
                    "`staff_detector` finds five-line staves, so a one-line "
                    "percussion rule has no shape to be filed as -- CLAUDE.md "
                    "records 11 real one-line staves dropped on Mahler 5"),
    "beam": (DETECTOR, "beam (121, 200) + CV_LINES",
             "read by classical CV; the detector class is kept as a union"),
    "tie": (DETECTOR, "tie (122, 201)", "Q.ARC_BOX"),
    "tied": (DETECTOR, "tie (122, 201)", "the notational half of the same ink"),
    "slur": (DETECTOR, "slur (120, 199)", "Q.ARC_BOX"),
    "stem": (DETECTOR, "stem (41, 160) + CV_LINES", "Q.STEM"),
    "fermata": (DETECTOR, "fermataAbove/Below (80, 81, 180, 181)",
                "Q.FERMATA_MARK"),
    "staccato": (DETECTOR, "articStaccatoAbove/Below (72, 73), "
                           "articulationStaccato (176)", "Q.ARTICULATION_MARK"),
    "accent": (DETECTOR, "articAccentAbove/Below (70, 71), "
                         "articulationAccent (175)", "Q.ARTICULATION_MARK"),
    "tenuto": (DETECTOR, "articTenutoAbove/Below (74, 75), "
                         "articulationTenuto (177)", "Q.ARTICULATION_MARK"),
    "staccatissimo": (DETECTOR, "articStaccatissimoAbove/Below (76, 77)",
                      "Q.ARTICULATION_MARK"),
    "strong-accent": (DETECTOR, "articMarcatoAbove/Below (78, 79), "
                                "articulationMarcato* (178, 179)",
                      "marcato; Q.ARTICULATION_MARK"),
    "trill-mark": (DETECTOR, "ornamentTrill (103, 197)", "Q.ORNAMENT_MARK"),
    "turn": (DETECTOR, "ornamentTurn (104)", "Q.ORNAMENT_MARK"),
    "inverted-turn": (DETECTOR, "ornamentTurnInverted (105)",
                      "Q.ORNAMENT_MARK"),
    "mordent": (DETECTOR, "ornamentMordent (106)", "Q.ORNAMENT_MARK"),
    "tremolo": (DETECTOR, "tremolo1-5 (42-46), tremoloMark (161)",
                "class present; the CHECKPOINT produces zero -- a DETECTION "
                "ceiling already recorded in CLAUDE.md, not a vocabulary gap"),
    "wedge": (CV, "cv_hairpins + dynamicCrescendo/DiminuendoHairpin "
                  "(124, 125, 203, 204)", "Q.WEDGE_BOX"),
    "clef": (DETECTOR, "clefG/CAlto/CTenor/F/UnpitchedPercussion/8/15 (5-11)",
             "Q.CLEF_GLYPH + the CV locator"),
    "grace": (DETECTOR, "graceNote* (99-102, 196) + the *Small noteheads",
              "class present; 0 Small detections ever produced -- a DETECTION "
              "ceiling recorded in CLAUDE.md, not a vocabulary gap"),
    "cue": (DETECTOR, "noteheadFullSmall (156), notehead*Small (25, 27, ...)",
            "same Small-notehead ceiling as <grace>"),
    "arpeggiate": (DETECTOR, "arpeggiato (109), arpeggio (198)",
                   "class present and MISREAD -- CLAUDE.md records 98 and 86 "
                   "firings on two pages that are stems or barlines"),
    "up-bow": (DETECTOR, "stringsUpBow (108)", "no quantity: case (a)"),
    "down-bow": (DETECTOR, "stringsDownBow (107)", "no quantity: case (a)"),
    "pedal": (DETECTOR, "keyboardPedalPed (110), keyboardPedalUp (111)",
              "no quantity: case (a)"),
    "octave-shift": (DETECTOR, "ottavaBracket (135)",
                     "no quantity: case (a); the 8va DIGIT has no class of its "
                     "own and the bracket is one class for a SPAN -- case (c)"),
    "caesura": (DETECTOR, "caesura (82)", "no quantity: case (a)"),
    "segno": (DETECTOR, "segno (3, 139)", "no quantity: case (a)"),
    "coda": (DETECTOR, "coda (4, 140)", "no quantity: case (a)"),
    "notehead": (DETECTOR, "notehead* (24-39, 156-158)",
                 "the ELEMENT names a SHAPE (x, diamond, slash); the 208 hold "
                 "only black/half/whole/doubleWhole, so an x-notehead is read "
                 "as a black one -- a shape gap inside a covered family"),
    "words": (CV, "SURYA / TEXT_LAYER (direction_text)", "Q.DIRECTION_WORD"),
    "instrument-name": (CV, "TEXT_LAYER / SURYA (margin labels)",
                        "Q.MARGIN_LABEL"),
    "part-name-display": (CV, "TEXT_LAYER / SURYA (margin labels)",
                          "Q.MARGIN_LABEL"),
    "display-text": (CV, "TEXT_LAYER / SURYA (margin labels)",
                     "the text inside <part-name-display>"),
    "cancel": (DETECTOR, "accidentalNatural (61, 171), keyNatural (68)",
               "the naturals cancelling an old key signature at a key change; "
               "the glyphs are classed, and `Q.KEYSIG_MARKER` reads the "
               "sharps and flats -- whether a CANCELLATION is told apart from "
               "a new signature is a reading question, not a vocabulary one"),
    "pppppp": (DETECTOR, "dynamicP (93, 190)", "Q.DYNAMIC_LETTER"),
    "spiccato": (DETECTOR, "articStaccatissimoAbove/Below (76, 77)",
                 "spiccato is engraved as the staccatissimo wedge"),
    "multiple-rest": (WRONG_SHAPE, "restHBar (123, 202) + numeral* (144-153)",
                      "CASE (c): a MULTI-MEASURE REST is ONE mark standing for "
                      "N BARS, and both halves are classed -- the H-bar and "
                      "the digits above it.  What is missing is that the "
                      "record's finest address is a CELL, i.e. one bar, so "
                      "nothing can say `this glyph IS bars 12-27`.  On a "
                      "conductor's page this is the commonest span of all"),
    "other-dynamics": (DETECTOR, "dynamicP/M/F/S/Z/R (93-98, 190-195)",
                       "letters are classed; the SPELLING is the exporter's"),
    "p": (DETECTOR, "dynamicP (93, 190)", "Q.DYNAMIC_LETTER"),
    "pp": (DETECTOR, "dynamicP", "Q.DYNAMIC_LETTER"),
    "ppp": (DETECTOR, "dynamicP", "Q.DYNAMIC_LETTER"),
    "pppp": (DETECTOR, "dynamicP", "Q.DYNAMIC_LETTER"),
    "ppppp": (DETECTOR, "dynamicP", "Q.DYNAMIC_LETTER"),
    "f": (DETECTOR, "dynamicF (95, 192)", "Q.DYNAMIC_LETTER"),
    "ff": (DETECTOR, "dynamicF", "Q.DYNAMIC_LETTER"),
    "fff": (DETECTOR, "dynamicF", "Q.DYNAMIC_LETTER"),
    "ffff": (DETECTOR, "dynamicF", "Q.DYNAMIC_LETTER"),
    "fffff": (DETECTOR, "dynamicF", "Q.DYNAMIC_LETTER"),
    "mf": (DETECTOR, "dynamicM + dynamicF", "Q.DYNAMIC_LETTER"),
    "mp": (DETECTOR, "dynamicM + dynamicP", "Q.DYNAMIC_LETTER"),
    "sf": (DETECTOR, "dynamicS + dynamicF", "Q.DYNAMIC_LETTER"),
    "sfz": (DETECTOR, "dynamicS/F/Z", "Q.DYNAMIC_LETTER"),
    "sffz": (DETECTOR, "dynamicS/F/Z", "Q.DYNAMIC_LETTER"),
    "sfp": (DETECTOR, "dynamicS/F/P", "Q.DYNAMIC_LETTER"),
    "fp": (DETECTOR, "dynamicF + dynamicP", "Q.DYNAMIC_LETTER"),
    "fz": (DETECTOR, "dynamicF + dynamicZ", "Q.DYNAMIC_LETTER"),
    "rf": (DETECTOR, "dynamicR + dynamicF", "Q.DYNAMIC_LETTER"),
    "rfz": (DETECTOR, "dynamicR/F/Z", "Q.DYNAMIC_LETTER"),
    "sfpp": (DETECTOR, "dynamicS/F/P", "Q.DYNAMIC_LETTER"),
    "n": (DETECTOR, "dynamic letters", "niente; Q.DYNAMIC_LETTER"),
    "tuplet": (DETECTOR, "tuplet1-9 (112, 113, 126-132), tupletBracket (133)",
               "Q.TUPLET_MARKER"),
    "fingering": (DETECTOR, "fingering0-5 (114-119)",
                  "no quantity: case (a); rare on a conductor's score"),
    "repeat": (DETECTOR, "repeatDot (2, 138)",
               "⚠️ THE DOTS ONLY.  The thick-thin BARLINE that carries them is "
               "not in the 208 and no barline-TYPE classifier exists "
               "(CLAUDE.md, A-DUR-6): half-covered, and the half that decides "
               "the traversal order is the missing half"),
    "barline": (CV, "GEOMETRY (Q.BARLINE_COLUMN)",
                "a barline is FOUND by classical CV; its TYPE is not read -- "
                "see <repeat> and <ending>"),
    "bar-style": (CV, "GEOMETRY (Q.BARLINE_COLUMN)",
                  "light-heavy / heavy-light / dashed: the column is found, "
                  "the STYLE is not classified anywhere"),

    # ── no detector class, no CV rung: SEAN'S QUESTION ─────────────────────
    "ending": (MISSING, "-",
               "a VOLTA bracket (1., 2.) -- not in the 208, no CV rung, and "
               "its absence means the printed order is not the playing order"),
    "glissando": (MISSING, "-",
                  "a straight line between two noteheads, usually with the "
                  "word `gliss.`; no class, and the WORD alone would reach "
                  "direction_text without the line it labels"),
    "slide": (MISSING, "-", "glissando's unlabelled twin; same gap"),
    "breath-mark": (MISSING, "-",
                    "the comma over a staff; `caesura` (82) is the RAILROAD "
                    "TRACKS, a different mark -- checked against the 208, not "
                    "recalled"),
    "rehearsal": (MISSING, "-",
                  "a boxed letter or number above the top staff.  `numeral` "
                  "(189) is the COARSE numeral class CLAUDE.md records as "
                  "covering meters, tuplet digits, fingerings AND measure "
                  "numbers under one name, and it names no BOX; the "
                  "direction_text rung gates on a 181-word musical lexicon, "
                  "which a bare `A` cannot pass"),
    "dashes": (MISSING, "-",
               "the dotted continuation after `cresc.` / `dim.` that says how "
               "far it runs; no class, and a SPAN besides -- (b) and (c) at "
               "once"),
    "metronome": (MISSING, "-",
                  "a note glyph plus `= 120`.  No class; the note glyph would "
                  "be read as a notehead IN THE MARGIN, and `export_coverage` "
                  "already carries it as an unconditional export gap"),
    "bracket": (MISSING, "-",
                "a direction BRACKET (the horizontal line with end hooks over "
                "a passage).  Distinct from the system bracket, which "
                "CLAUDE.md separately records as absent from the 208"),
    "wavy-line": (MISSING, "-",
                  "a trill's continuation squiggle; the trill HEAD is classed "
                  "(103) and its extent is not"),
    "open-string": (MISSING, "-", "the small `o` over a note; no class"),
    "mute": (MISSING, "-",
             "`con sordino` as a TECHNICAL mark rather than as words.  The "
             "direction_text rung would have to read it, and its lexicon is "
             "measured at 140 terms -- see the lexicon control"),
    "stopped": (MISSING, "-",
                "the `+` over a note -- a HORN stopping mark, so it is an "
                "orchestral mark and not only a string one; no class"),
    "harmonic": (MISSING, "-", "the small circle for a string harmonic"),
    "non-arpeggiate": (MISSING, "-",
                       "the square bracket forbidding a roll; no class"),
    "soft-accent": (MISSING, "-", "no class"),
    "detached-legato": (MISSING, "-",
                        "tenuto AND staccato on one note.  Both marks ARE "
                        "classed separately, so this is a COMBINATION the "
                        "vocabulary cannot name as one thing"),
    "accidental-mark": (MISSING, "-",
                        "a small accidental printed ABOVE an ornament.  The "
                        "accidental classes exist; what is missing is that it "
                        "belongs to the ornament and not to a notehead -- a "
                        "vocabulary gap in ATTRIBUTION"),
    "harmony": (MISSING, "-",
                "a chord symbol.  Real ink, and ⚠️ NOT an orchestral one: it "
                "is counted here because the corpus holds continuo and "
                "keyboard encodings, and the orchestral column is what ranks "
                "it"),
    "figured-bass": (MISSING, "-",
                     "the continuo figures under a bass line.  Same caveat as "
                     "<harmony>: real, and mostly not on a conductor's page"),
    "other-notation": (MISSING, "-", "by definition unnamed"),
    "other-direction": (MISSING, "-", "by definition unnamed"),
    "other-articulation": (MISSING, "-", "by definition unnamed"),
    "other-technical": (MISSING, "-", "by definition unnamed"),
    "other-ornament": (MISSING, "-", "by definition unnamed"),
    "inverted-mordent": (MISSING, "-",
                         "⚠️ THE 208 HOLD `ornamentMordent` (106) AND NO "
                         "INVERTED FORM.  The two are different marks (one "
                         "carries a slash) and mean different notes, so this "
                         "is a real gap inside a covered family"),
    "schleifer": (MISSING, "-", "no class"),
    "haydn": (MISSING, "-", "no class"),
    "delayed-turn": (MISSING, "-", "ornamentTurn placed late; no class"),
    "delayed-inverted-turn": (MISSING, "-", "no class"),
    "vertical-turn": (MISSING, "-", "no class"),
    "inverted-vertical-turn": (MISSING, "-", "no class"),
    "shake": (MISSING, "-", "no class"),
    "tremolo-mark": (MISSING, "-", "no class under this spelling"),
    "double-tongue": (MISSING, "-", "no class"),
    "triple-tongue": (MISSING, "-", "no class"),
    "fingernails": (MISSING, "-", "no class"),
    "hammer-on": (MISSING, "-", "no class"),
    "pull-off": (MISSING, "-", "no class"),
    "bend": (MISSING, "-", "no class"),
    "tap": (MISSING, "-", "no class"),
    "heel": (MISSING, "-", "organ pedalling; no class"),
    "toe": (MISSING, "-", "organ pedalling; no class"),
    "thumb-position": (MISSING, "-", "no class"),
    "pluck": (MISSING, "-", "no class"),
    "snap-pizzicato": (MISSING, "-", "no class"),
    "string": (MISSING, "-", "the roman numeral naming a string; no class"),
    "fret": (MISSING, "-", "no class"),
    "arrow": (MISSING, "-", "no class"),
    "handbell": (MISSING, "-", "no class"),
    "brass-bend": (MISSING, "-", "no class"),
    "flip": (MISSING, "-", "no class"),
    "smear": (MISSING, "-", "no class"),
    "doit": (MISSING, "-", "a jazz brass rip upward; no class"),
    "scoop": (MISSING, "-", "a jazz brass scoop; no class"),
    "open": (MISSING, "-",
             "the `o` marking an OPEN brass note, the partner of <stopped>; "
             "no class"),
    "half-muted": (MISSING, "-", "no class"),
    "golpe": (MISSING, "-", "no class"),
    "principal-voice": (MISSING, "-", "the Hauptstimme bracket; no class"),
    "staff-divide": (MISSING, "-", "no class"),
    "image": (MISSING, "-", "an embedded picture; not our problem"),
    "percussion": (MISSING, "-", "a percussion pictogram; no class"),
    "accordion-registration": (MISSING, "-", "no class"),
    "string-mute": (MISSING, "-", "no class"),
    "scordatura": (MISSING, "-", "no class"),
    "harp-pedals": (MISSING, "-", "a harp pedal diagram; no class"),
    "eyeglasses": (MISSING, "-", "no class"),
    "damp": (MISSING, "-", "no class"),
    "damp-all": (MISSING, "-", "no class"),
    "measure-numbering": (MISSING, "-",
                          "⚠️ MusicXML states the CONVENTION, not the number; "
                          "the printed measure number itself is ink the "
                          "exploration doc already ranks as free ground truth "
                          "for a bar count we currently derive from geometry"),
}


def _normalise(name: str) -> str:
    return name.lower().replace("-", "")


def class_matches(element: str, vocab: Iterable[str]) -> List[str]:
    """208-class names plausibly naming this element, by string alone.

    The AUTOMATED half.  Deliberately generous -- it exists to catch a hand
    verdict of NO_CATEGORY sitting on ink the vocabulary does hold, so a false
    positive here costs a line of explanation and a false negative costs the
    finding.
    """
    token = _normalise(element)
    if len(token) < 3:
        return []
    return sorted({c for c in vocab
                   if token in _normalise(c) or _normalise(c) in token})


def contradictions(vocab: Iterable[str]) -> List[Tuple[str, List[str]]]:
    """NO_CATEGORY verdicts the class matcher can place after all."""
    out = []
    for element, (verdict, _, _) in sorted(ADJUDICATION.items()):
        if verdict != MISSING:
            continue
        hits = class_matches(element, vocab)
        if hits:
            out.append((element, hits))
    return out


#: Contradictions that are REAL and explained, so `--check` does not fail on
#: them.  Each is the matcher being fooled by a shared substring.
CONTRADICTION_EXPLAINED: Dict[str, str] = {
    "tremolo-mark": "matches tremoloMark (161), which is the COARSE block's "
                    "one tremolo class -- the element is still not a "
                    "distinct mark and <tremolo> above carries the family",
    "string": "matches stringsUpBow/stringsDownBow by substring; a string "
              "NUMBER is not a bowing",
    "open": "matches nothing musical -- it is a substring of no class; kept "
            "here only if a future vocabulary adds one",
    "bracket": "matches `ottavaBracket` and `tuplet/tupleBracket` by "
               "substring.  A DIRECTION bracket is neither an octave line nor "
               "a tuplet marker, and CLAUDE.md separately records that no "
               "class names a SYSTEM bracket either",
    "percussion": "matches `clefUnpitchedPercussion` -- a CLEF, not a "
                  "pictogram",
    "staff-divide": "matches `staff`, the five-line staff itself",
}


# ─────────────────────────────────────────────────────────────────────────────
# 4. CASE (c) -- a span has nowhere to live
# ─────────────────────────────────────────────────────────────────────────────

#: MusicXML elements that are inherently a RANGE, not a point.  Each is either
#: paired by `type="start"/"stop"` or holds a `number=` level.
SPAN_ELEMENTS: Tuple[str, ...] = (
    "slur", "tied", "wedge", "octave-shift", "dashes", "bracket", "pedal",
    "glissando", "slide", "tuplet", "ending", "wavy-line", "principal-voice",
    "multiple-rest",
)


#: Ink that a conductor's page prints and `notation_index` can NEVER see,
#: because MusicXML does not encode it inside `<measure>`.  Counted separately
#: by regex over the whole document so the blind spot is a measurement rather
#: than a caveat.
_HEADER_INK = {
    "part-group": re.compile(r"<part-group\b"),
    "group-symbol": re.compile(r"<group-symbol[^>]*>([a-z]+)</group-symbol>"),
    "group-barline": re.compile(r"<group-barline"),
}


def header_ink(limit: Optional[int] = None,
               seed: int = 20260916) -> Dict[str, object]:
    """The bracket, the brace and the group barline -- outside `<measure>`.

    ⚠️ THE ONE CASE-(b) ITEM THE ELEMENT CENSUS IS STRUCTURALLY BLIND TO, and
    CLAUDE.md already records its verdict from the other side: *"Nothing
    detects a bracket -- `bracket` is not in the 208-class space (only
    `tupletbracket`, a tuplet marker)"*, which is why `OMR_BRACKET_COLUMNS`
    INFERS family boundaries from where the interior barlines stop instead.
    `brace` IS a class (0, 136) and has no quantity -- case (a), not (b).
    Counted here so the two are told apart by a number.
    """
    files = sorted(p for pat in ("*.mxl", "*.musicxml", "*.xml")
                   for p in REFERENCE.rglob(pat))
    if limit is not None and limit < len(files):
        files = random.Random(seed).sample(files, limit)
    symbols: Counter = Counter()
    groups = barlines = n_ok = 0
    for path in files:
        try:
            xml = _mxl_text(path)
        except Exception:                                     # noqa: BLE001
            continue
        if xml is None:
            continue
        n_ok += 1
        groups += len(_HEADER_INK["part-group"].findall(xml))
        barlines += len(_HEADER_INK["group-barline"].findall(xml))
        symbols.update(_HEADER_INK["group-symbol"].findall(xml))
    return {"files": n_ok, "part_group": groups,
            "group_barline": barlines, "group_symbol": dict(symbols)}


def lexicon_control() -> Dict[str, object]:
    """Can the ONE rung that reads free text reach a rehearsal mark or a
    metronome number?

    ⚠️ ASKED, NOT ASSUMED.  Three case-(b) entries above rest on the claim
    that `direction_text` cannot stand in for a missing class, so the claim is
    put to the shipped lexicon.  The accepted words beside the refused ones
    are the positive control: a lexicon that refused everything would make the
    refusals meaningless.
    """
    from tools.omr.direction_lexicon import TERMS, lookup
    probes = ["A", "B", "C", "12", "120", "Allegro", "cresc.", "dolce"]
    return {
        "terms": len(TERMS),
        "answers": {p: (lookup(p).text if lookup(p) else None) for p in probes},
    }


def span_report(counts: Counter) -> Dict[str, object]:
    """How much of the corpus is span-shaped, and whether a span can be filed.

    `record.Kind` is a HIERARCHY OF PLACES (DOCUMENT > PAGE > SYSTEM > STAFF >
    CELL > GLYPH) and `Subject` addresses exactly one of them, so the record
    can say *this glyph* and never *from this glyph to that one*.  Derived
    here rather than asserted: the Kind members are read off the enum.
    """
    return {
        "kinds": [k.value for k in Kind],
        "has_range_kind": any("span" in k.value or "range" in k.value
                              for k in Kind),
        "span_elements_present": {e: counts[e] for e in SPAN_ELEMENTS
                                  if counts[e]},
        "span_total": sum(counts[e] for e in SPAN_ELEMENTS),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Report
# ─────────────────────────────────────────────────────────────────────────────

def build(limit: Optional[int]) -> Dict[str, object]:
    vocab = detector_vocabulary()
    corpus = survey_corpus(limit=limit)
    all_counts: Counter = corpus["all_counts"]                # type: ignore
    orch_counts: Counter = corpus["orch_counts"]              # type: ignore

    settled = set(NOT_INK) | set(export_not_notation())
    unaccounted = sorted(e for e in all_counts
                         if e not in ADJUDICATION and e not in settled)

    rows = []
    for element, count in all_counts.items():
        if element in settled:
            verdict, cover, why = NOT_NOTATION, "-", (
                NOT_INK.get(element) or export_not_notation()[element])
        elif element in ADJUDICATION:
            verdict, cover, why = ADJUDICATION[element]
        else:
            continue
        rows.append({
            "element": element, "verdict": verdict, "covered_by": cover,
            "reason": why, "count_all": count,
            "count_orch": orch_counts.get(element, 0),
            "files_all": corpus["all_files"][element],        # type: ignore
            "files_orch": corpus["orch_files"][element],      # type: ignore
        })

    return {
        "vocabulary": {
            "detector_classes": len(vocab),
            "detector_classes_distinct": len(set(vocab)),
            "snapshot_classes": len(set(snapshot_vocabulary())),
            "record_Q_declared": len(GC.declared()),
            "record_Q_observed": sum(1 for r in GC.gathered().values()
                                     if r["observed_by"]),
            "cv_rungs": cv_rungs(),
        },
        "case_a": case_a_over_full_vocabulary(),
        "corpus": {k: corpus[k] for k in
                   ("files_found", "files_parsed", "files_orchestral",
                    "files_failed", "failures")},
        "rows": sorted(rows, key=lambda r: -r["count_orch"]),
        "unaccounted": unaccounted,
        "contradictions": [(e, h) for e, h in contradictions(vocab)
                           if e not in CONTRADICTION_EXPLAINED],
        "case_c": span_report(orch_counts),
        "lexicon": lexicon_control(),
        "header_ink": header_ink(limit),
    }


def export_not_notation() -> Dict[str, str]:
    """`export_coverage`'s own three, imported so the two cannot drift."""
    from tools.omr.export_coverage import NOT_NOTATION as N
    return dict(N)


def render(rep: Dict[str, object]) -> None:
    v = rep["vocabulary"]                                      # type: ignore
    c = rep["corpus"]                                          # type: ignore
    a = rep["case_a"]                                          # type: ignore

    print("═══ GATHER VOCABULARY ═══")
    print("\n─── 1. REACH: what the vocabulary IS ───")
    print(f"  detector class space         {v['detector_classes']} "
          f"({v['detector_classes_distinct']} distinct names)")
    print(f"  ...what gather_coverage audits {v['snapshot_classes']}"
          f"   ⚠️ a 146-name SNAPSHOT of an older release")
    print(f"  record.Q declared            {v['record_Q_declared']}")
    print(f"  record.Q observed by GATHER  {v['record_Q_observed']}")
    print(f"  non-detector readers         {len(v['cv_rungs'])}")
    for rung, qs in v["cv_rungs"].items():
        print(f"      {rung:<14} {len(qs):2d} quantities  "
              f"{', '.join(qs[:4])}{' ...' if len(qs) > 4 else ''}")

    print(f"\n  corpus: {c['files_parsed']} of {c['files_found']} .mxl parsed, "
          f"{c['files_orchestral']} with >= {ORCHESTRAL_MIN_PARTS} parts, "
          f"{c['files_failed']} failed")
    for f in c["failures"]:
        print(f"      failed: {f}")

    print("\n─── 2. CASE (a): a detector class no quantity names ───")
    print(f"  families over the FULL {a['classes_full']} classes: "
          f"{a['families_full']}, of which unnamed {len(a['unnamed_full'])}")
    print(f"  families over the {a['classes_snapshot']}-class snapshot: "
          f"{a['families_snapshot']}, of which unnamed "
          f"{len(a['unnamed_snapshot'])}")
    only = sorted(set(a["unnamed_full"]) - set(a["unnamed_snapshot"]))
    print(f"  ⚠️ families the snapshot cannot see at all: "
          f"{', '.join(only) if only else 'none'}")
    if a["families_unknown_to_table"]:
        print(f"  ⚠️ families FAMILY_Q has no entry for: "
              f"{', '.join(a['families_unknown_to_table'])}")
    for fam, classes in sorted(a["unnamed_full"].items()):
        print(f"      {fam:<16} {len(classes):2d}  {', '.join(classes[:4])}"
              f"{' ...' if len(classes) > 4 else ''}")

    rows: List[dict] = rep["rows"]                             # type: ignore
    missing = [r for r in rows if r["verdict"] == MISSING]
    covered = [r for r in rows if r["verdict"] in (DETECTOR, CV)]
    print("\n─── 3. CASE (b): ink with NO category anywhere ───")
    print(f"  ranked by occurrences in the {c['files_orchestral']} "
          f"orchestral encodings")
    print(f"  {'element':<22} {'orch':>9} {'files':>6} {'all':>9}   why")
    for r in missing:
        if not r["count_all"]:
            continue
        print(f"  {r['element']:<22} {r['count_orch']:>9} "
              f"{r['files_orch']:>6} {r['count_all']:>9}   "
              f"{r['reason'][:78]}")
    zeros = [r["element"] for r in missing if not r["count_all"]]
    print(f"\n  POSITIVE CONTROL: {len(covered)} element kinds ARE covered "
          f"(detector class or CV rung), "
          f"{sum(r['count_orch'] for r in covered):,} orchestral occurrences")
    print(f"  {len(missing) - len(zeros)} uncovered kinds OCCUR; "
          f"{len(zeros)} adjudicated uncovered and never seen in this corpus "
          f"(reported, not counted)")

    shape = [r for r in rows if r["verdict"] == WRONG_SHAPE]
    cc = rep["case_c"]                                         # type: ignore
    print("\n─── 4. CASE (c): the category exists and is the wrong SHAPE ───")
    for r in shape:
        print(f"  {r['element']:<22} {r['count_orch']:>9} orch   "
              f"{r['covered_by']}")
        print(f"      {r['reason']}")
    print("\n  4b. THE STRUCTURAL FORM: a SPAN has nowhere to be filed")
    print(f"  record.Kind = {', '.join(cc['kinds'])}")
    print(f"  a Kind naming a range: {cc['has_range_kind']}")
    print(f"  span-shaped occurrences in orchestral encodings: "
          f"{cc['span_total']:,}")
    for e, n in sorted(cc["span_elements_present"].items(),
                       key=lambda kv: -kv[1]):
        print(f"      {e:<18} {n:>9,}")

    hi = rep["header_ink"]                                     # type: ignore
    print("\n─── 4c. CASE (b) the element census is BLIND to: header ink ───")
    print(f"  <part-group> over {hi['files']} files: {hi['part_group']:,}  "
          f"(<group-barline> {hi['group_barline']:,})")
    for sym, n in sorted(hi["group_symbol"].items(), key=lambda kv: -kv[1]):
        state = {
            "brace": "class `brace` (0, 136), NO QUANTITY -- case (a)",
            "none": "no symbol is printed -- not ink",
        }.get(sym, "NO CLASS -- case (b)")
        print(f"      group-symbol={sym:<10} {n:>7,}   {state}")

    lx = rep["lexicon"]                                        # type: ignore
    print("\n─── 5. CONTROL: can direction_text stand in for a class? ───")
    print(f"  the shipped lexicon holds {lx['terms']} terms")
    for probe, answer in lx["answers"].items():
        print(f"      lookup({probe!r:<10}) -> "
              f"{answer if answer else 'REFUSED'}")

    print("\n─── 6. CONTROLS ───")
    print(f"  unaccounted elements (must be 0): {len(rep['unaccounted'])}"
          f"  {', '.join(rep['unaccounted'][:12])}")
    print(f"  matcher contradicts a NO_CATEGORY verdict (must be 0): "
          f"{len(rep['contradictions'])}  {rep['contradictions'][:6]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero on an unaccounted element, a "
                         "contradiction, or a dead instrument")
    ap.add_argument("--limit", type=int, default=None,
                    help="sample this many .mxl files (default: all)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not REFERENCE.is_dir():
        print(f"REFERENCE corpus not found at {REFERENCE} -- this probe needs "
              f"the machine-local score library and cannot run without it.",
              file=sys.stderr)
        return 2

    rep = build(args.limit)
    if args.json:
        out = dict(rep)
        print(json.dumps(out, indent=2, default=str))
    else:
        render(rep)

    parsed = rep["corpus"]["files_parsed"]                     # type: ignore
    if not parsed:
        print("\nDEAD INSTRUMENT: no file parsed.", file=sys.stderr)
        return 2
    if args.check:
        bad = bool(rep["unaccounted"]) or bool(rep["contradictions"])
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
