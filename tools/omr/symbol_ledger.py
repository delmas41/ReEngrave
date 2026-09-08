"""A per-symbol ACCOUNT, not a score — every symbol on both sides gets a row.

Sean's commission, 2026-09-07:

    "I don't like the idea of the measure going blank if we can't figure it
    out. Every symbol and note and word should be accounted for both in our
    tests and in our process. The second quarter note of Bar 3 is a B should
    be a distinct decision and able to be traced back to a test where that
    was predetermined."

WHY THIS EXISTS
---------------
The headline metric is OMR-NED via `musicdiff`. Measured on 2026-09-07 over
the 20-row scan gate at the default `AllObjects` detail level, **92.5% of all
edits are bulk/unpaired charges** — `wrong note`, `entire measure
insert/delete`, `entire staff insert/delete` — and only 5,607 of 74,956 name a
specific error. `benchmarks/omr-wrongnote-decomposition-2026-09/FINDINGS.md`.

⚠️ The mechanism is a PREMATURE COMMITMENT. Without `Voicing`, musicdiff pairs
notes **by pitch** — it decides which note corresponds to which using the very
quantity under measurement. A wrong pitch destroys the correspondence, so the
error cannot be reported as a wrong pitch; it becomes a deletion plus an
insertion, and enough of those in a bar are charged as the whole bar. That is
circular in exactly the way this codebase refuses at `clef_correction.py:396`
and `:566`, `dossier.py:434` and `score_layouts.py:682`.

So the scores are trustworthy about DIRECTION (both A/B arms are scored
identically) and unreliable about ATTRIBUTION (what kind of error we have).
Attribution is what has been used to choose what to work on.

WHAT THIS DOES INSTEAD
----------------------
1. **Every truth symbol and every predicted symbol gets a row.** Nothing is
   aggregated away and nothing is dropped.

2. **Correspondence is decided by SEVERAL keys and adjudicated**, never by one
   chosen up front:

   | key | pairs on | blind to | contaminated for |
   |---|---|---|---|
   | `ord`   | ordinal position, counts equal | everything | nothing |
   | `onset` | beat position in the bar | pitch | duration (onset accrues durations) |
   | `pitch` | step + octave | duration | pitch |
   | `joint` | onset AND pitch | — | both (corroboration only) |

   ⚠️ **AN ATTRIBUTE IS ONLY REPORTED FROM A PAIRING THAT DID NOT USE IT.**
   `pitch` is assessable only where the basis includes `ord` or `onset`;
   `duration` only where it includes `ord` or `pitch`. Where no such basis
   exists the attribute is `not_assessable` and is COUNTED AS SUCH — never
   silently scored, never silently dropped.

3. ⚠️ **"COULD NOT ESTABLISH CORRESPONDENCE" IS A FIRST-CLASS OUTCOME, NOT A
   CHARGE.** Today that case is billed as though we misread the bar, which is
   a different and much stronger claim than the data supports. Here it is
   `uncorresponded`, with the tier that failed named on the row
   (`part_unresolved`, `measure_unresolved`, `bar_alignment_ambiguous`).

4. **Rows are addressable the way Sean addresses them** — part / bar / beat —
   so *"the second quarter of bar 3"* is `SymbolAddress(part=…, measure=3,
   onset_ql=1.0)` and a test can assert on it.

THE THREE TIERS, IN ORDER, EACH ABSTAINING RATHER THAN GUESSING
---------------------------------------------------------------
**Tier 1, PART.** ⚠️ Upstream and the biggest bucket — `entire staff
insert/delete` is 16,777 edits on the scan gate, larger than everything about
notes. Printed scores condense (`Violoncello e Basso`), suppress tacet staves
and split divisi, so a printed staff carries a SET of reference parts. This
module does not infer that map: it takes the HAND-VERIFIED one already in
`benchmarks/omr-scan-e2e-2026-09/works.json` (`staves[i].parts`), the same
input `mxl_verdicts` uses, on the same terms as the measure window — input,
never derived. Where the printed staff count and our part count disagree the
join ABSTAINS and every symbol of that page is `uncorresponded/part_unresolved`.

**Tier 2, MEASURE.** The window is input too (`first_ref_measure`). Our export
numbers a page's bars from 1, so the map is an offset. Where the bar COUNT
disagrees with the verified window the offset is a HYPOTHESIS, recorded as
`measure_map="hypothesised"` on every row it produced, and headline figures
are reported over verified cells with the hypothesised ones stated apart.

**Tier 3, SYMBOL.** The multi-key adjudication above, inside one
(staff, measure) cell.

WHAT IT CANNOT MEASURE — an inventory, not a silence
----------------------------------------------------
* **It compares two ENCODINGS, not the page.** `page_truth.py` already does
  the page-level job for pages we render, and its lesson applies here: a
  clef is printed at every system and declared once. Both sides here are
  MusicXML so the convention is shared, but a symbol the PRINT carries and
  neither file encodes is invisible to this instrument, exactly as it is to
  OMR-NED.
* **Chord members' pitch verdicts are contaminated and are flagged.** Chord
  members share an onset, so `onset` cannot order them; both sides order a
  chord by pitch, which makes the within-chord pairing pitch-derived. Those
  rows carry `chord_member=True` and their pitch verdicts are reported
  separately. (~25% of predicted notes on the Brahms row.)
* **It says nothing about scans' ink.** Like OMR-NED it sees only what
  reached the file.

SELF-CHECK — the `page_truth.render_fidelity` equivalent
--------------------------------------------------------
`page_truth` exists in its current form because that harness caught ITSELF
being wrong: Verovio draws one accidental per `<alter>`, not per
`<accidental>`, so the accidental family reported recall 0.257 and had to be
excluded. An instrument that cannot detect its own failure is the thing this
project keeps getting burned by. Three controls, all runnable:

* `self_check_identity(path)` — score a file against ITSELF. Every row must be
  `matched_exact`; any other outcome is a defect in the instrument, not in the
  pipeline. **This is the positive control for every count.**
* `cross_check_note_extraction(path)` — this module's extractor against
  `training/musicxml_truth.load_truth`, an INDEPENDENT parser. Disagreement on
  note counts or onsets fails loudly.
* `benchmarks/omr-symbol-ledger-2026-09/mutation_matrix.py` — inject one known
  error of each kind and assert the ledger names that kind and no other.

    python3 -m tools.omr.symbol_ledger pred.musicxml truth.musicxml
    python3 -m tools.omr.symbol_ledger --self-check truth.musicxml
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable, Sequence
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

#: Every symbol family this instrument accounts for, and what one row of it
#: means. An inventory rather than a filter: a family absent from a file
#: produces zero rows, and that zero is reported.
FAMILIES: dict[str, str] = {
    "note": "one sounding notehead (a chord contributes one row per head)",
    "rest": "one printed rest",
    "dynamic": "a point dynamic — <dynamics> inside a <direction>",
    "hairpin": "a <wedge> — crescendo/diminuendo/stop",
    "word": "a <words> direction — 'legato', 'Allegro con brio'",
    "metronome": "a <metronome> direction",
    "slur": "one <slur> endpoint (start or stop) on a note",
    "tie": "one <tied> endpoint on a note (the NOTATION, not the <tie>)",
    "articulation": "one mark inside <articulations>",
    "ornament": "one mark inside <ornaments>",
    "fermata": "a <fermata> on a note or a barline",
    "clef": "a <clef> in <attributes>",
    "key": "a <key> in <attributes>",
    "time": "a <time> in <attributes>",
    "barline": "a <barline> with a bar-style or a repeat",
}

#: Attributes compared per family, in the order they are reported. The FIRST
#: entry of `note` and `rest` is special-cased by the assessability rule.
COMPARED_ATTRS: dict[str, tuple[str, ...]] = {
    "note": ("pitch", "duration_ql", "type", "dots", "accidental", "grace"),
    "rest": ("duration_ql", "type", "dots"),
    "dynamic": ("text",),
    "hairpin": ("wedge",),
    "word": ("text",),
    "metronome": ("text",),
    "slur": ("endpoint",),
    "tie": ("endpoint",),
    "articulation": ("mark",),
    "ornament": ("mark",),
    "fermata": (),
    "clef": ("clef",),
    "key": ("fifths",),
    "time": ("beats", "beat_type", "symbol"),
    "barline": ("bar_style", "repeat"),
}

#: Which correspondence keys are BLIND to which attribute. A verdict on an
#: attribute is only reported from a basis containing a key blind to it —
#: this is the whole anti-circularity rule, in one table.
KEY_BLIND_TO: dict[str, frozenset[str]] = {
    "ord":   frozenset({"pitch", "duration_ql", "type", "dots", "accidental",
                        "grace", "text", "wedge", "endpoint", "mark", "clef",
                        "fifths", "beats", "beat_type", "symbol", "bar_style",
                        "repeat"}),
    "onset": frozenset({"pitch", "accidental", "grace", "text", "wedge",
                        "endpoint", "mark", "clef", "fifths", "beats",
                        "beat_type", "symbol", "bar_style", "repeat"}),
    "pitch": frozenset({"duration_ql", "type", "dots", "text", "wedge",
                        "endpoint", "mark", "clef", "fifths", "beats",
                        "beat_type", "symbol", "bar_style", "repeat"}),
    "joint": frozenset(),
}

OUTCOMES = (
    "matched_exact",
    "matched_attribute_error",
    "missing",
    "spurious",
    "uncorresponded",
    "ambiguous",
)

UNCORRESPONDED_REASONS = (
    "part_unresolved",
    "measure_unresolved",
    "bar_alignment_ambiguous",
)

_ALTER_TEXT = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"}
_DYNAMIC_WORDS = {
    "p", "pp", "ppp", "pppp", "ppppp", "pppppp",
    "f", "ff", "fff", "ffff", "fffff", "ffffff",
    "mp", "mf", "sf", "sfp", "sfpp", "fp", "rf", "rfz", "sfz", "sffz", "fz",
    "n", "pf", "sfzp",
}

_ONSET_Q = 6  # decimal places onsets are rounded to before they are compared


# ---------------------------------------------------------------------------
# The row
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Symbol:
    """One printed thing, on one side, addressed the way Sean addresses it."""

    side: str                 # "truth" | "pred"
    part_index: int
    part_name: str
    measure: int              # as numbered in ITS OWN file
    onset_ql: float           # beat position within the bar
    family: str
    voice: str
    ordinal: int              # index within (part, measure, family), doc order
    attrs: dict[str, Any] = field(default_factory=dict)
    chord_member: bool = False

    @property
    def uid(self) -> str:
        return (f"{self.side}:p{self.part_index}:m{self.measure}"
                f":{self.family}:{self.ordinal}")

    def describe(self) -> str:
        """`Violin 1 bar 3 beat 2 note F#4` — the address, in Sean's words."""
        beat = self.onset_ql + 1.0
        head = f"{self.part_name or ('part %d' % self.part_index)} bar {self.measure} beat {beat:g}"
        if self.family == "note":
            return f"{head} note {self.attrs.get('pitch')}"
        if self.family == "rest":
            return f"{head} rest {self.attrs.get('type')}"
        bits = " ".join(f"{k}={v}" for k, v in self.attrs.items() if v not in (None, ""))
        return f"{head} {self.family} {bits}".rstrip()


@dataclass
class LedgerRow:
    """The account of ONE symbol. Every symbol on both sides gets exactly one."""

    row_id: str
    side: str
    family: str
    outcome: str
    # address — the truth side's when there is one, else the prediction's
    part_index: int
    part_name: str
    measure: int | None            # reference measure number where known
    onset_ql: float | None
    voice: str
    ordinal: int
    description: str
    # correspondence
    partner_uid: str | None = None
    basis: tuple[str, ...] = ()            # keys that agreed on the partner
    basis_strength: str = ""               # "corroborated" | "single_key"
    dissenting: dict[str, str | None] = field(default_factory=dict)
    reason: str | None = None              # why uncorresponded / ambiguous
    measure_map: str = "verified"          # "verified" | "hypothesised" | "none"
    chord_member: bool = False
    condensed: bool = False                # truth side merged >1 reference part
    # attributes
    attrs: dict[str, Any] = field(default_factory=dict)
    partner_attrs: dict[str, Any] = field(default_factory=dict)
    attrs_wrong: tuple[str, ...] = ()
    attrs_not_assessable: tuple[str, ...] = ()
    uid: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["basis"] = list(self.basis)
        d["attrs_wrong"] = list(self.attrs_wrong)
        d["attrs_not_assessable"] = list(self.attrs_not_assessable)
        return d


# ---------------------------------------------------------------------------
# Extraction — one pass per part, one onset clock
# ---------------------------------------------------------------------------


def _read_xml(path: str | Path) -> ET.Element:
    p = Path(path)
    data = p.read_bytes()
    if p.suffix.lower() == ".mxl" or zipfile.is_zipfile(io.BytesIO(data)):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            root_name = None
            try:
                container = zf.read("META-INF/container.xml").decode("utf-8", "replace")
                cr = ET.fromstring(container)
                for rf in cr.iter():
                    if _tag(rf) == "rootfile" and rf.get("full-path"):
                        root_name = rf.get("full-path")
                        break
            except KeyError:
                pass
            if root_name is None:
                for n in zf.namelist():
                    if n.lower().endswith((".xml", ".musicxml")) and not n.startswith("META-INF"):
                        root_name = n
                        break
            if root_name is None:
                raise ValueError(f"{p}: no MusicXML inside the container")
            data = zf.read(root_name)
    # Parsed as BYTES on purpose: a MusicXML file carries an encoding
    # declaration, and handing a decoded `str` to a parser that honours one is
    # an error in some builds. Namespaces are stripped at read time by `_tag`.
    return ET.fromstring(data)


def _tag(el: ET.Element) -> str:
    return el.tag.split("}")[-1] if isinstance(el.tag, str) else ""


def _txt(el: ET.Element | None, default: str = "") -> str:
    if el is None or el.text is None:
        return default
    return el.text.strip()


def _int(el: ET.Element | None, default: int = 0) -> int:
    try:
        return int(float(_txt(el, str(default))))
    except ValueError:
        return default


def _part_names(root: ET.Element) -> dict[str, str]:
    out: dict[str, str] = {}
    pl = root.find("part-list")
    if pl is None:
        return out
    for sp in pl:
        if _tag(sp) == "score-part":
            out[sp.get("id", "")] = _txt(sp.find("part-name"))
    return out


def _clef_text(el: ET.Element) -> str:
    sign = _txt(el.find("sign")) or "?"
    line = _txt(el.find("line")) or ""
    oc = _txt(el.find("octave-change")) or ""
    s = f"{sign}{line}"
    return f"{s}{'%+d' % int(oc)}" if oc else s


def _direction_symbols(direction: ET.Element) -> list[tuple[str, dict[str, Any]]]:
    """Every printable thing inside one `<direction>`, as (family, attrs)."""
    out: list[tuple[str, dict[str, Any]]] = []
    for dt in direction.findall("direction-type"):
        for child in dt:
            t = _tag(child)
            if t == "dynamics":
                marks = [_tag(g) for g in child if _tag(g) != "other-dynamics"]
                other = [_txt(g) for g in child if _tag(g) == "other-dynamics"]
                text = "".join(marks) or "".join(other)
                out.append(("dynamic", {"text": text}))
            elif t == "wedge":
                out.append(("hairpin", {"wedge": child.get("type", "")}))
            elif t == "words":
                out.append(("word", {"text": _txt(child)}))
            elif t == "metronome":
                unit = _txt(child.find("beat-unit"))
                per = _txt(child.find("per-minute"))
                out.append(("metronome", {"text": f"{unit}={per}".strip("=")}))
    return out


def _note_symbols(note: ET.Element, onset_ql: float, part_index: int,
                  part_name: str, measure: int, side: str,
                  counters: Counter) -> list[Symbol]:
    """The note or rest, plus every notation attached to it."""
    out: list[Symbol] = []
    rest_el = note.find("rest")
    pitch_el = note.find("pitch")
    unp_el = note.find("unpitched")
    grace = note.find("grace") is not None
    chord = note.find("chord") is not None
    voice = _txt(note.find("voice"), "1")
    ntype = _txt(note.find("type")) or None
    dots = len(note.findall("dot"))
    accidental = _txt(note.find("accidental")) or None

    def _emit(family: str, attrs: dict[str, Any], *, chord_member: bool = False) -> Symbol:
        key = (part_index, measure, family)
        idx = counters[key]
        counters[key] += 1
        s = Symbol(side=side, part_index=part_index, part_name=part_name,
                   measure=measure, onset_ql=round(onset_ql, _ONSET_Q),
                   family=family, voice=voice, ordinal=idx, attrs=attrs,
                   chord_member=chord_member)
        out.append(s)
        return s

    if rest_el is not None:
        _emit("rest", {
            "duration_ql": None, "type": ntype, "dots": dots,
            "measure_rest": rest_el.get("measure") == "yes",
        })
    else:
        pitch = None
        src = pitch_el if pitch_el is not None else unp_el
        if src is not None:
            step = _txt(src.find("step") if pitch_el is not None else src.find("display-step")) or None
            oct_el = src.find("octave") if pitch_el is not None else src.find("display-octave")
            octave = _int(oct_el, 0) if oct_el is not None else None
            alter_el = src.find("alter")
            alter = 0
            if alter_el is not None:
                try:
                    alter = int(round(float(_txt(alter_el, "0"))))
                except ValueError:
                    alter = 0
            if step is not None and octave is not None and pitch_el is not None:
                pitch = f"{step}{_ALTER_TEXT.get(alter, '')}{octave}"
        _emit("note", {
            "pitch": pitch, "duration_ql": None, "type": ntype, "dots": dots,
            "accidental": accidental, "grace": grace,
        }, chord_member=chord)

    notations = note.find("notations")
    if notations is not None:
        for n in notations:
            t = _tag(n)
            if t == "slur":
                _emit("slur", {"endpoint": n.get("type", "")})
            elif t == "tied":
                _emit("tie", {"endpoint": n.get("type", "")})
            elif t == "fermata":
                _emit("fermata", {})
            elif t == "articulations":
                for a in n:
                    _emit("articulation", {"mark": _tag(a)})
            elif t == "ornaments":
                for a in n:
                    if _tag(a) != "accidental-mark":
                        _emit("ornament", {"mark": _tag(a)})
    return out


def extract_symbols(path: str | Path) -> tuple[list[Symbol], dict[str, Any]]:
    """Every symbol in a MusicXML file, with a consistent onset clock.

    Returns (symbols, meta). `meta` carries the per-part measure numbers, which
    the measure tier joins on, and any parse anomaly worth reporting.
    """
    root = _read_xml(path)
    names = _part_names(root)
    symbols: list[Symbol] = []
    counters: Counter = Counter()
    parts_meta: list[dict[str, Any]] = []
    anomalies: list[str] = []

    part_index = -1
    for part in root:
        if _tag(part) != "part":
            continue
        part_index += 1
        pid = part.get("id", "")
        pname = names.get(pid, "")
        divisions = 1
        measure_numbers: list[int] = []
        for measure in part:
            if _tag(measure) != "measure":
                continue
            raw = measure.get("number", "")
            try:
                mnum = int(raw)
            except ValueError:
                mnum = len(measure_numbers) + 1
                anomalies.append(f"part {part_index}: non-numeric measure number {raw!r}")
            measure_numbers.append(mnum)
            onset = 0.0
            # A note's onset must be the onset of the note it is chorded to.
            prev_onset = 0.0
            for el in measure:
                t = _tag(el)
                if t == "attributes":
                    d = el.find("divisions")
                    if d is not None:
                        divisions = _int(d, divisions) or 1
                    for a in el:
                        at = _tag(a)
                        if at == "clef":
                            symbols.append(_simple(side_of(path), part_index, pname, mnum,
                                                   onset, "clef", {"clef": _clef_text(a)}, counters))
                        elif at == "key":
                            symbols.append(_simple(side_of(path), part_index, pname, mnum,
                                                   onset, "key",
                                                   {"fifths": _int(a.find("fifths"), 0)}, counters))
                        elif at == "time":
                            symbols.append(_simple(side_of(path), part_index, pname, mnum,
                                                   onset, "time", {
                                                       "beats": _txt(a.find("beats")),
                                                       "beat_type": _txt(a.find("beat-type")),
                                                       "symbol": a.get("symbol") or None,
                                                   }, counters))
                elif t == "direction":
                    for fam, attrs in _direction_symbols(el):
                        symbols.append(_simple(side_of(path), part_index, pname, mnum,
                                               onset, fam, attrs, counters))
                elif t == "note":
                    chord = el.find("chord") is not None
                    grace = el.find("grace") is not None
                    here = prev_onset if chord else onset
                    got = _note_symbols(el, here, part_index, pname, mnum,
                                        side_of(path), counters)
                    dur = _int(el.find("duration"), 0) / (divisions or 1)
                    for s in got:
                        if s.family in ("note", "rest"):
                            s.attrs["duration_ql"] = round(dur, _ONSET_Q)
                    symbols.extend(got)
                    if not chord and not grace:
                        prev_onset = onset
                        onset += dur
                    elif chord:
                        pass
                    else:  # grace note: no time
                        prev_onset = onset
                elif t == "backup":
                    onset -= _int(el.find("duration"), 0) / (divisions or 1)
                    prev_onset = onset
                elif t == "forward":
                    onset += _int(el.find("duration"), 0) / (divisions or 1)
                    prev_onset = onset
                elif t == "barline":
                    style = _txt(el.find("bar-style")) or None
                    rep = el.find("repeat")
                    repeat = rep.get("direction") if rep is not None else None
                    if style or repeat:
                        symbols.append(_simple(side_of(path), part_index, pname, mnum,
                                               onset, "barline",
                                               {"bar_style": style, "repeat": repeat},
                                               counters))
                    ferm = el.find("fermata")
                    if ferm is not None:
                        symbols.append(_simple(side_of(path), part_index, pname, mnum,
                                               onset, "fermata", {}, counters))
        parts_meta.append({"index": part_index, "id": pid, "name": pname,
                           "measures": measure_numbers})
    meta = {"path": str(path), "parts": parts_meta, "anomalies": anomalies}
    return symbols, meta


_SIDE_OVERRIDE: dict[str, str] = {}


def side_of(path: str | Path) -> str:
    return _SIDE_OVERRIDE.get(str(path), "truth")


def _simple(side: str, part_index: int, pname: str, mnum: int, onset: float,
            family: str, attrs: dict[str, Any], counters: Counter) -> Symbol:
    key = (part_index, mnum, family)
    idx = counters[key]
    counters[key] += 1
    return Symbol(side=side, part_index=part_index, part_name=pname,
                  measure=mnum, onset_ql=round(onset, _ONSET_Q), family=family,
                  voice="", ordinal=idx, attrs=attrs)


def load_side(path: str | Path, side: str) -> tuple[list[Symbol], dict[str, Any]]:
    """`extract_symbols` with every row stamped `side`."""
    _SIDE_OVERRIDE[str(path)] = side
    try:
        syms, meta = extract_symbols(path)
    finally:
        _SIDE_OVERRIDE.pop(str(path), None)
    meta["side"] = side
    return syms, meta


# ---------------------------------------------------------------------------
# Correspondence — several keys, adjudicated
# ---------------------------------------------------------------------------


def _key_ord(sym: Symbol, i: int) -> str:
    return f"i{i}"


def _key_onset(sym: Symbol) -> str:
    return f"t{sym.onset_ql:.6f}"


def _key_pitch(sym: Symbol) -> str:
    p = sym.attrs.get("pitch")
    if not p:
        return "R" if sym.family == "rest" else "X"
    # step + octave: the notehead's PLACE, blind to the accidental, so a
    # spelling difference does not destroy the pairing the way `exact` would.
    letter = p[0]
    digits = ""
    for ch in reversed(p):
        if ch.isdigit() or (ch == "-" and digits):
            digits = ch + digits
        elif digits:
            break
    return f"{letter}{digits}"


def _key_attr(sym: Symbol, family: str) -> str:
    attrs = COMPARED_ATTRS.get(family, ())
    if not attrs:
        return family
    return "|".join(str(sym.attrs.get(a)) for a in attrs)


def lcs_pairs(a: Sequence[str], b: Sequence[str]) -> list[tuple[int, int]]:
    """Order-preserving longest common subsequence over two key sequences.

    A generic sibling of `training/measure_align.align_tokens`, which is not
    reused here because its weight function is staff-position specific (it
    reads a `P<n>` key and allows a one-step slop) and this instrument needs
    the SAME alignment procedure driven by several different keys so their
    verdicts are comparable.
    """
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return []
    score = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        row, prev = score[i], score[i - 1]
        ai = a[i - 1]
        for j in range(1, m + 1):
            best = prev[j] if prev[j] >= row[j - 1] else row[j - 1]
            if ai == b[j - 1] and prev[j - 1] + 1 > best:
                best = prev[j - 1] + 1
            row[j] = best
    pairs: list[tuple[int, int]] = []
    i, j = n, m
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1] and score[i][j] == score[i - 1][j - 1] + 1:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif score[i - 1][j] >= score[i][j - 1]:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs


@dataclass
class KeyProposal:
    name: str
    pairs: dict[int, int]            # truth index -> pred index
    abstained: bool = False
    note: str = ""


def propose_pairings(truth: list[Symbol], pred: list[Symbol],
                     family: str) -> list[KeyProposal]:
    """What each correspondence key says, independently.

    ⚠️ `ord` ABSTAINS when the counts differ. A purely positional pairing
    across unequal counts is a guess — one missing symbol shifts every later
    one — and this project's house rule is to abstain rather than guess, the
    way `dossier` abstains when staff count != part count.
    """
    out: list[KeyProposal] = []

    if len(truth) == len(pred):
        out.append(KeyProposal("ord", {i: i for i in range(len(truth))}))
    else:
        out.append(KeyProposal("ord", {}, abstained=True,
                               note=f"counts differ {len(truth)} vs {len(pred)}"))

    if family in ("note", "rest"):
        ot = [_key_onset(s) for s in truth]
        op = [_key_onset(s) for s in pred]
        out.append(KeyProposal("onset", dict(lcs_pairs(ot, op))))
        pt = [_key_pitch(s) for s in truth]
        pp = [_key_pitch(s) for s in pred]
        if family == "note":
            out.append(KeyProposal("pitch", dict(lcs_pairs(pt, pp))))
        else:
            out.append(KeyProposal("pitch", {}, abstained=True,
                                   note="a rest has no pitch"))
        jt = [f"{x}@{y}" for x, y in zip(ot, pt)]
        jp = [f"{x}@{y}" for x, y in zip(op, pp)]
        out.append(KeyProposal("joint", dict(lcs_pairs(jt, jp))))
    else:
        ot = [_key_onset(s) for s in truth]
        op = [_key_onset(s) for s in pred]
        out.append(KeyProposal("onset", dict(lcs_pairs(ot, op))))
        at = [_key_attr(s, family) for s in truth]
        ap = [_key_attr(s, family) for s in pred]
        out.append(KeyProposal("pitch", dict(lcs_pairs(at, ap)),
                               note="identity key: this family's compared attributes"))
        jt = [f"{x}@{y}" for x, y in zip(ot, at)]
        jp = [f"{x}@{y}" for x, y in zip(op, ap)]
        out.append(KeyProposal("joint", dict(lcs_pairs(jt, jp))))
    return out


@dataclass
class Adjudication:
    partner: dict[int, int]                       # truth idx -> pred idx (agreed)
    basis: dict[int, tuple[str, ...]]
    dissent: dict[int, dict[str, str | None]]     # truth idx -> key -> what it said
    ambiguous: set[int]
    pred_taken: dict[int, int]                    # pred idx -> truth idx


def adjudicate(proposals: list[KeyProposal], n_truth: int,
               n_pred: int) -> Adjudication:
    """One partner per truth symbol, or an explicit ambiguity.

    A key that abstained votes for nothing. A truth symbol whose non-abstaining
    keys name DIFFERENT partners is `ambiguous` — the competing proposals are
    kept on the row rather than broken to produce a tidy table.
    """
    partner: dict[int, int] = {}
    basis: dict[int, tuple[str, ...]] = {}
    dissent: dict[int, dict[str, str | None]] = {}
    ambiguous: set[int] = set()
    live = [p for p in proposals if not p.abstained]
    for i in range(n_truth):
        votes: dict[int | None, list[str]] = defaultdict(list)
        for p in live:
            votes[p.pairs.get(i)].append(p.name)
        named = {k: v for k, v in votes.items() if k is not None}
        if not named:
            continue
        if len(named) > 1:
            ambiguous.add(i)
            dissent[i] = {name: (f"pred[{k}]" if k is not None else None)
                          for k, names in votes.items() for name in names}
            continue
        j = next(iter(named))
        partner[i] = j
        basis[i] = tuple(sorted(named[j]))
        if votes.get(None):
            dissent[i] = {name: None for name in votes[None]}
    # A pred symbol may be claimed by two truth symbols only if the keys
    # disagree; the LCS itself is injective, so this can only happen across
    # keys — and any such truth symbol is already ambiguous above.
    pred_taken: dict[int, int] = {}
    for i, j in partner.items():
        if j in pred_taken:
            ambiguous.add(i)
            ambiguous.add(pred_taken[j])
        else:
            pred_taken[j] = i
    for i in list(ambiguous):
        partner.pop(i, None)
        basis.pop(i, None)
    pred_taken = {j: i for i, j in partner.items()}
    return Adjudication(partner, basis, dissent, ambiguous, pred_taken)


def assessable(attr: str, basis: Iterable[str]) -> bool:
    """⚠️ THE ANTI-CIRCULARITY RULE. An attribute may only be reported from a
    pairing established by at least one key BLIND to it."""
    return any(attr in KEY_BLIND_TO.get(k, frozenset()) for k in basis)


def compare_attrs(t: Symbol, p: Symbol, basis: Iterable[str],
                  family: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(wrong, not_assessable) over this family's compared attributes."""
    basis = tuple(basis)
    wrong: list[str] = []
    unknown: list[str] = []
    for a in COMPARED_ATTRS.get(family, ()):
        if not assessable(a, basis):
            unknown.append(a)
            continue
        tv, pv = t.attrs.get(a), p.attrs.get(a)
        if isinstance(tv, float) or isinstance(pv, float):
            same = (tv is not None and pv is not None
                    and abs(float(tv) - float(pv)) < 1e-6)
        else:
            same = tv == pv
        if not same:
            wrong.append(a)
    return tuple(wrong), tuple(unknown)


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------


@dataclass
class PartJoin:
    """Tier 1. Which truth parts one predicted staff carries, and on what."""

    pred_part: int
    truth_parts: tuple[int, ...]
    status: str                  # "resolved" | "unresolved"
    reason: str | None = None
    source: str = "works.json staves[].parts (hand-verified)"


@dataclass
class LedgerResult:
    row_id: str
    rows: list[LedgerRow]
    part_join: list[PartJoin]
    measure_map: dict[str, Any]
    meta: dict[str, Any]

    def counts(self) -> dict[str, int]:
        return dict(Counter(r.outcome for r in self.rows))

    def coverage_check(self) -> dict[str, Any]:
        """⚠️ THE ACCOUNTING CONTROL, and the reason a printed zero here is a
        result rather than a suspect.

        The invariant, stated exactly: **every TRUTH symbol owns exactly one
        row; every PRED symbol is either named as the partner on a truth row
        or owns a row of its own — never both, never neither.** A matched pair
        is ONE row accounting for TWO symbols, which is why this is not simply
        `len(rows) == n_truth + n_pred`.

        `balanced=False` is an instrument defect. Nothing downstream may quote
        a figure from an unbalanced ledger.
        """
        truth_uids = [r.uid for r in self.rows if r.side == "truth"]
        pred_own = [r.uid for r in self.rows if r.side == "pred"]
        partners = [r.partner_uid for r in self.rows if r.partner_uid]
        dup_truth = len(truth_uids) - len(set(truth_uids))
        pred_all = pred_own + partners
        dup_pred = len(pred_all) - len(set(pred_all))
        return {
            "truth_symbols_in": self.meta.get("n_truth_symbols"),
            "pred_symbols_in": self.meta.get("n_pred_symbols"),
            "truth_rows": len(truth_uids),
            "pred_rows_own": len(pred_own),
            "pred_as_partner": len(partners),
            "pred_accounted": len(set(pred_all)),
            "duplicate_truth_rows": dup_truth,
            "duplicate_pred_accounts": dup_pred,
            "balanced": (
                len(truth_uids) == self.meta.get("n_truth_symbols")
                and len(set(pred_all)) == self.meta.get("n_pred_symbols")
                and dup_truth == 0 and dup_pred == 0),
        }


def _merge_truth_parts_symbols(per_part: list[list[Symbol]]) -> list[Symbol]:
    """Several reference parts printed on ONE staff, as one onset-ordered list
    with unisons collapsed.

    The same modelling `training/measure_align.merge_truth_parts` makes and for
    the same reason: two flutes on one staff print `a2` as ONE notehead. ⚠️ It
    is a TRUTH-SIDE transformation only — nothing about the prediction enters
    it — so it cannot create the circularity this module exists to remove. It
    does use pitch, and that is recorded: a condensed staff's unison collapse
    is a pitch-keyed decision on the truth side, stated here rather than
    hidden.
    """
    if len(per_part) == 1:
        # ⚠️ DOCUMENT ORDER, NOT SORTED. Sorting a single part by pitch was the
        # first defect `self_check_identity` caught: it reorders a chord's
        # members relative to the same file's own document order, so `ord` and
        # `onset` propose one pairing and `pitch` another, and a file scored
        # against ITSELF came out `ambiguous` on every double stop.
        return list(per_part[0])
    seen: set[tuple[float, str, str]] = set()
    merged: list[Symbol] = []
    for syms in per_part:
        for s in syms:
            if s.family == "rest":
                # one part rests while the other plays: no rest is printed
                continue
            k = (round(s.onset_ql, _ONSET_Q), s.family,
                 str(s.attrs.get("pitch") or _key_attr(s, s.family)))
            if k in seen:
                continue
            seen.add(k)
            merged.append(s)
    # ⚠️ STABLE, keyed on onset ONLY. Within one onset the parts keep their
    # roster order (part 0's note before part 1's) — an order taken from the
    # STAFF MAP, not from pitch, so the condensed case does not smuggle a
    # pitch-derived ordering into the `ord` and `onset` keys. Whether the
    # engraver wrote a2 divisi top-down or bottom-up is unknown to us, so
    # every row from a condensed staff is flagged `condensed=True` and its
    # figures are reported apart.
    merged.sort(key=lambda s: (s.onset_ql, s.family))
    return merged


def build_ledger(*, row_id: str, pred_path: str | Path, truth_path: str | Path,
                 part_join: Sequence[PartJoin] | None = None,
                 first_ref_measure: int | None = None,
                 expected_measures: int | None = None,
                 families: Sequence[str] | None = None) -> LedgerResult:
    """Account for every symbol on both sides of one page.

    `part_join` is INPUT (tier 1). With none supplied the join is positional
    only where the part counts already agree; otherwise every symbol is
    `uncorresponded/part_unresolved`, which is the honest answer and the one
    this instrument exists to be able to give.
    """
    fams = set(families) if families else set(FAMILIES)
    pred_syms, pred_meta = load_side(pred_path, "pred")
    truth_syms, truth_meta = load_side(truth_path, "truth")
    pred_syms = [s for s in pred_syms if s.family in fams]
    truth_syms = [s for s in truth_syms if s.family in fams]

    n_pred_parts = len(pred_meta["parts"])
    n_truth_parts = len(truth_meta["parts"])

    if part_join is None:
        if n_pred_parts == n_truth_parts and n_pred_parts > 0:
            part_join = [PartJoin(i, (i,), "resolved",
                                  source="positional; part counts agree")
                         for i in range(n_pred_parts)]
        else:
            part_join = [PartJoin(i, (), "unresolved",
                                  reason=(f"no hand-verified staff map and part counts "
                                          f"differ ({n_pred_parts} predicted vs "
                                          f"{n_truth_parts} reference)"),
                                  source="none")
                         for i in range(n_pred_parts)]
    part_join = list(part_join)

    # ---- tier 2: the measure map -----------------------------------------
    pred_measures = sorted({m for p in pred_meta["parts"] for m in p["measures"]})
    truth_measures = sorted({m for p in truth_meta["parts"] for m in p["measures"]})
    if first_ref_measure is None:
        first_ref_measure = min(truth_measures) if truth_measures else 1
    offset = first_ref_measure - (min(pred_measures) if pred_measures else 1)
    n_pred_m = len(pred_measures)
    n_truth_m = expected_measures if expected_measures is not None else len(truth_measures)
    if n_pred_m == n_truth_m:
        measure_status = "verified"
        measure_reason = None
    else:
        measure_status = "hypothesised"
        measure_reason = (f"the page's verified window holds {n_truth_m} bars and the "
                          f"prediction emitted {n_pred_m}; the offset map is a "
                          f"hypothesis, not a correspondence")
    measure_map = {
        "offset": offset, "status": measure_status, "reason": measure_reason,
        "first_ref_measure": first_ref_measure,
        "pred_measures": n_pred_m, "truth_measures": n_truth_m,
    }

    # ---- index both sides -------------------------------------------------
    pred_by: dict[tuple[int, int, str], list[Symbol]] = defaultdict(list)
    for s in pred_syms:
        pred_by[(s.part_index, s.measure + offset, s.family)].append(s)
    truth_by: dict[tuple[int, int, str], list[Symbol]] = defaultdict(list)
    for s in truth_syms:
        truth_by[(s.part_index, s.measure, s.family)].append(s)

    rows: list[LedgerRow] = []
    seen_truth: set[str] = set()
    seen_pred: set[str] = set()

    def _row(sym: Symbol, outcome: str, **kw) -> LedgerRow:
        r = LedgerRow(
            row_id=row_id, side=sym.side, family=sym.family, outcome=outcome,
            part_index=sym.part_index, part_name=sym.part_name,
            measure=kw.pop("measure", sym.measure), onset_ql=sym.onset_ql,
            voice=sym.voice, ordinal=sym.ordinal,
            description=sym.describe(), chord_member=sym.chord_member,
            attrs=dict(sym.attrs), uid=sym.uid, **kw)
        rows.append(r)
        return r

    resolved = {pj.pred_part: pj for pj in part_join if pj.status == "resolved"}
    unresolved_reason = {pj.pred_part: (pj.reason or "the staff map does not resolve")
                         for pj in part_join if pj.status != "resolved"}
    joined_truth_parts = {tp for pj in resolved.values() for tp in pj.truth_parts}

    # ⚠️ THE CELL SET IS THE UNION OF BOTH SIDES', NOT THE PREDICTION'S.
    # Driving it off `pred_by` alone was a real defect, and the mutation
    # matrix is what caught it: delete the only <slur> of a bar and that
    # (staff, bar, slur) cell vanishes from the prediction, so the truth slur
    # was never visited and fell through to the leftover loop as
    # `uncorresponded/measure_unresolved` — the instrument reporting "I could
    # not establish correspondence" for a symbol whose correspondence was
    # perfectly well established and simply had no partner. That is the
    # measure going blank, in the instrument built to stop it.
    cells: set[tuple[int, int, str]] = set(pred_by)
    for pj in part_join:
        if pj.status != "resolved":
            continue
        for tp in pj.truth_parts:
            for (tpart, tmeas, fam) in truth_by:
                if tpart == tp:
                    cells.add((pj.pred_part, tmeas, fam))

    for (ppart, tmeasure, family) in sorted(cells):
        psyms = pred_by.get((ppart, tmeasure, family), [])
        if ppart not in resolved:
            for s in psyms:
                _row(s, "uncorresponded", reason="part_unresolved",
                     measure=tmeasure, measure_map="none")
                seen_pred.add(s.uid)
            continue
        if tmeasure not in truth_measures:
            for s in psyms:
                _row(s, "uncorresponded", reason="measure_unresolved",
                     measure=tmeasure, measure_map=measure_status)
                seen_pred.add(s.uid)
            continue
        pj = resolved[ppart]
        per_part = [truth_by.get((tp, tmeasure, family), []) for tp in pj.truth_parts]
        tsyms = _merge_truth_parts_symbols([x for x in per_part])
        for x in per_part:
            for s in x:
                seen_truth.add(s.uid)
        if not tsyms and not psyms:
            continue
        _account_cell(rows, _row, tsyms, psyms, family, tmeasure,
                      measure_status, seen_truth, seen_pred, row_id,
                      condensed=len(pj.truth_parts) > 1)

    # ---- what neither loop reached ---------------------------------------
    for s in truth_syms:
        if s.uid in seen_truth:
            continue
        if s.part_index not in joined_truth_parts:
            _row(s, "uncorresponded",
                 reason="part_unresolved", measure_map="none")
        else:
            _row(s, "uncorresponded", reason="measure_unresolved",
                 measure_map=measure_status)
        seen_truth.add(s.uid)
    for s in pred_syms:
        if s.uid in seen_pred:
            continue
        _row(s, "uncorresponded", reason="part_unresolved", measure_map="none")
        seen_pred.add(s.uid)

    meta = {
        "pred": pred_meta, "truth": truth_meta,
        "n_truth_symbols": len(truth_syms), "n_pred_symbols": len(pred_syms),
        "n_pred_parts": n_pred_parts, "n_truth_parts": n_truth_parts,
        "families": sorted(fams),
    }
    return LedgerResult(row_id, rows, list(part_join), measure_map, meta)


def _account_cell(rows: list[LedgerRow], _row, tsyms: list[Symbol],
                  psyms: list[Symbol], family: str, tmeasure: int,
                  measure_status: str, seen_truth: set[str],
                  seen_pred: set[str], row_id: str,
                  condensed: bool = False) -> None:
    """Tier 3, for one (staff, bar, family) cell."""
    proposals = propose_pairings(tsyms, psyms, family)
    adj = adjudicate(proposals, len(tsyms), len(psyms))
    prop_by_name = {p.name: p for p in proposals}

    for i, t in enumerate(tsyms):
        seen_truth.add(t.uid)
        if i in adj.ambiguous:
            _row(t, "ambiguous", reason="bar_alignment_ambiguous",
                 measure=tmeasure, measure_map=measure_status, condensed=condensed,
                 dissenting={k: v for k, v in (adj.dissent.get(i) or {}).items()})
            continue
        j = adj.partner.get(i)
        if j is None:
            _row(t, "missing", measure=tmeasure, measure_map=measure_status,
                 condensed=condensed, dissenting={k: None for k in (adj.dissent.get(i) or {})})
            continue
        p = psyms[j]
        seen_pred.add(p.uid)
        basis = adj.basis.get(i, ())
        wrong, unknown = compare_attrs(t, p, basis, family)
        outcome = "matched_exact" if not wrong else "matched_attribute_error"
        # ⚠️ ONE KEY IS ONE SIGNAL. A pairing named by a single key while the
        # others explicitly DECLINE is not corroborated, and an attribute
        # verdict taken from it is weaker than one taken from a pairing two
        # blind keys agree on. Measured shape: delete the 2nd note of a Bach
        # bar and every later note becomes `ambiguous` (onset says one
        # partner, pitch another) EXCEPT the one at the boundary, where only
        # `onset` names anything — and that lone row is where the instrument's
        # own residual pitch misattribution lives. It is reported, split out,
        # and never pooled with the corroborated verdicts.
        strength = "corroborated" if len(basis) > 1 else "single_key"
        _row(t, outcome, measure=tmeasure, measure_map=measure_status,
             condensed=condensed, partner_uid=p.uid, basis=basis,
             basis_strength=strength, attrs_wrong=wrong,
             attrs_not_assessable=unknown, partner_attrs=dict(p.attrs),
             dissenting=dict(adj.dissent.get(i) or {}))

    for j, p in enumerate(psyms):
        if p.uid in seen_pred:
            continue
        seen_pred.add(p.uid)
        if j in adj.pred_taken:
            continue
        claimed_by_ambiguous = any(
            pr.pairs.get(i) == j for i in adj.ambiguous
            for pr in proposals if not pr.abstained)
        if claimed_by_ambiguous:
            _row(p, "ambiguous", reason="bar_alignment_ambiguous",
                 measure=tmeasure, measure_map=measure_status, condensed=condensed)
        else:
            _row(p, "spurious", measure=tmeasure, measure_map=measure_status, condensed=condensed)


# ---------------------------------------------------------------------------
# Self-checks — an instrument that cannot detect its own failure is the thing
# this project keeps getting burned by
# ---------------------------------------------------------------------------


def self_check_identity(path: str | Path,
                        families: Sequence[str] | None = None) -> dict[str, Any]:
    """⚠️ THE POSITIVE CONTROL FOR EVERY COUNT. A file scored against itself.

    Every row must be `matched_exact`, every symbol must be accounted for, and
    nothing may be missing, spurious, ambiguous or uncorresponded. Any other
    outcome is a defect in THIS MODULE — a family whose extractor is
    order-unstable, a key that cannot pair a symbol with its own twin — and
    it fails loudly here instead of printing a clean table of zeros later.
    """
    res = build_ledger(row_id="self-check", pred_path=path, truth_path=path,
                       families=families)
    counts = res.counts()
    cov = res.coverage_check()
    bad = {k: v for k, v in counts.items() if k != "matched_exact"}
    offenders = [
        {"outcome": r.outcome, "family": r.family, "where": r.description,
         "reason": r.reason}
        for r in res.rows if r.outcome != "matched_exact"
    ][:20]
    return {
        "path": str(path), "ok": not bad and cov["balanced"],
        "counts": counts, "coverage": cov, "offenders": offenders,
        "by_family": dict(Counter(r.family for r in res.rows)),
    }


def cross_check_note_extraction(path: str | Path) -> dict[str, Any]:
    """This module's extractor against `training/musicxml_truth`, an
    INDEPENDENT parser of the same file.

    ⚠️ Two signals sharing an ancestor are one signal — these two do not share
    one. They were written separately, they walk the tree differently, and a
    disagreement about how many notes a file holds or where they sit means one
    of them is wrong.
    """
    from tools.omr.training.musicxml_truth import load_truth  # local: optional dep

    mine, _ = load_side(path, "truth")
    theirs = load_truth(path)
    mine_notes = [s for s in mine if s.family in ("note", "rest")]
    their_notes = [(pi, m.number, n)
                   for pi, p in enumerate(theirs.parts)
                   for m in p.measures for n in m.notes]
    mine_key = Counter((s.part_index, s.measure, round(s.onset_ql, 4),
                        s.attrs.get("pitch") or "R") for s in mine_notes)
    their_key = Counter((pi, mn, round(n.onset_ql, 4), n.pitch or "R")
                        for pi, mn, n in their_notes)
    only_mine = mine_key - their_key
    only_theirs = their_key - mine_key
    return {
        "path": str(path),
        "ok": not only_mine and not only_theirs,
        "n_mine": len(mine_notes), "n_theirs": len(their_notes),
        "only_mine": [list(map(str, k)) + [v] for k, v in list(only_mine.items())[:20]],
        "only_theirs": [list(map(str, k)) + [v] for k, v in list(only_theirs.items())[:20]],
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def summarise(res: LedgerResult) -> dict[str, Any]:
    """Counts that always add up, and the attribution the metric cannot give."""
    by_outcome = Counter(r.outcome for r in res.rows)
    by_family_outcome: dict[str, Counter] = defaultdict(Counter)
    for r in res.rows:
        by_family_outcome[r.family][r.outcome] += 1
    attr_wrong: Counter = Counter()
    attr_wrong_weak: Counter = Counter()
    attr_unknown: Counter = Counter()
    for r in res.rows:
        target = attr_wrong if r.basis_strength != "single_key" else attr_wrong_weak
        for a in r.attrs_wrong:
            target[f"{r.family}.{a}"] += 1
        for a in r.attrs_not_assessable:
            attr_unknown[f"{r.family}.{a}"] += 1
    uncorr = Counter(r.reason for r in res.rows if r.outcome == "uncorresponded")
    basis = Counter("+".join(r.basis) for r in res.rows if r.basis)
    return {
        "row_id": res.row_id,
        "outcomes": dict(by_outcome),
        "by_family": {k: dict(v) for k, v in sorted(by_family_outcome.items())},
        "attributes_wrong": dict(attr_wrong.most_common()),
        "attributes_wrong_single_key": dict(attr_wrong_weak.most_common()),
        "attributes_not_assessable": dict(attr_unknown.most_common()),
        "uncorresponded_reasons": dict(uncorr),
        "correspondence_basis": dict(basis.most_common()),
        "measure_map": res.measure_map,
        "part_join": {
            "resolved": sum(1 for p in res.part_join if p.status == "resolved"),
            "unresolved": sum(1 for p in res.part_join if p.status != "resolved"),
        },
        "coverage": res.coverage_check(),
    }


def rows_to_csv(rows: Iterable[LedgerRow]) -> str:
    import csv
    buf = io.StringIO()
    cols = ["row_id", "side", "family", "outcome", "reason", "part_index",
            "part_name", "measure", "onset_ql", "voice", "ordinal",
            "chord_member", "condensed", "measure_map", "basis",
            "basis_strength", "attrs_wrong",
            "attrs_not_assessable", "description", "partner_uid", "uid"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        d = r.to_dict()
        d["basis"] = "+".join(r.basis)
        d["attrs_wrong"] = "+".join(r.attrs_wrong)
        d["attrs_not_assessable"] = "+".join(r.attrs_not_assessable)
        w.writerow(d)
    return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pred", type=Path, nargs="?")
    ap.add_argument("truth", type=Path, nargs="?")
    ap.add_argument("--self-check", type=Path, default=None,
                    help="score a file against itself; every row must be matched_exact")
    ap.add_argument("--cross-check", type=Path, default=None,
                    help="this extractor against training/musicxml_truth")
    ap.add_argument("--families", nargs="+", default=None)
    ap.add_argument("--csv", type=Path, default=None)
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args(argv)

    if a.self_check:
        out = self_check_identity(a.self_check, a.families)
        print(json.dumps(out, indent=2))
        return 0 if out["ok"] else 1
    if a.cross_check:
        out = cross_check_note_extraction(a.cross_check)
        print(json.dumps(out, indent=2))
        return 0 if out["ok"] else 1
    if not a.pred or not a.truth:
        ap.error("pred and truth are required unless --self-check/--cross-check")
    res = build_ledger(row_id=a.pred.stem, pred_path=a.pred, truth_path=a.truth,
                       families=a.families)
    summary = summarise(res)
    print(json.dumps(summary, indent=2))
    if a.csv:
        a.csv.write_text(rows_to_csv(res.rows))
    if a.json:
        a.json.write_text(json.dumps([r.to_dict() for r in res.rows], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
