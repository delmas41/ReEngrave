"""The concert key by consensus, and every staff's written key by deduction.

⚠️ **EVIDENCE, NOT REPAIR.** Nothing here changes a reading. It reports, per
staff, what the page's own consensus says that staff SHOULD have printed and
what it did print. The reason is concrete rather than stylistic: on Beethoven 5
p1 the Viola read −1 against a truth of −3, and a consensus that *corrected* it
would have produced the right answer for the wrong reason and hidden the actual
defect — that staff's single accidental box sits at x 1161 against a
system-wide accidental band of 580–948, i.e. the reader matched something that
is probably not a flat. A contradiction is a QUESTION ("why does this staff
disagree"), and answering it is a different act from silencing it.

THE ARGUMENT (Sean, 2026-09-08), in the order it gets stronger:

  1. the bowed strings never disagree with each other about the key;
  2. more generally, only TRANSPOSING instruments may disagree with the
     concert-pitch ones — so if the flutes, oboes and strings agree, that is
     the established key;
  3. and given that key plus a known transposition, the WRITTEN signature is
     DEDUCIBLE, so a transposing staff stops being merely excluded from the
     evidence and becomes predicted, and therefore checkable.

(3) is the one this module is built around. `instruments.py` already carries
the field it needs: `Match.fifths_offset`, documented there as "written key =
concert key + this".

MEASURED SUPPORT, and its limits, in
`benchmarks/omr-string-key-agreement-2026-09/FINDINGS.md`: over the 149
reference encodings holding ≥2 resolvable string parts, 142 agree and 7 do not,
and the exclusions are legitimate (1095 are ≤2 parts; 501 are SATB choral, with
no strings to disagree). Of the seven, Holst's *Mercury* is genuinely BITONAL.
Scordatura (Mahler 4 mvt 2) is a further real exception absent from that corpus.
So the premise is strong, not universal — which is exactly why this reports and
does not decide.

THREE CONSTRAINTS, EACH MEASURED, EACH CHEAP TO GET WRONG:

  * **The octave trap.** The witness test is `chromatic % 12 == 0`, NEVER
    `chromatic == 0`. Contrabass is −12 — an OCTAVE transposition, which does
    not change the key signature — and the naive form drops the bass, the staff
    a witness rule most wants, being bottom-of-page and often unlabelled.
    Piccolo (+12), Contrabassoon, Guitar and Tenor have the same shape.

  * **A third category beside transposing / not: PRINTS NO SIGNATURE BY
    CONVENTION.** Natural brass and timpani are written without a key signature
    and take their accidentals inline. On Beethoven 5 p1 the concert-pitch set
    splits 8 to 2 for exactly this reason — Trombe in C and Timpani read 0
    against everyone else's −3 — so a UNANIMITY rule breaks on the most famous
    page in the repertoire while a MAJORITY rule survives.
    ⚠️ These staves are excluded from the WITNESS set (a trumpet votes 0
    whatever the key, which would corrupt the consensus it is meant to
    corroborate) but they are still JUDGED, because exempting them wholesale
    would hide a trumpet reading something that is neither 0 nor its prediction.
    The carve-out is exactly "predicted non-zero, read zero" and nothing wider.

  * **Genuine counter-examples exist.** Bitonality and scordatura are real
    engraving, not misreads. `MIN_WITNESSES` and the strict-majority rule exist
    so that a bitonal page ABSTAINS rather than being flattened: Mercury's
    strings read {−2, 3, −2, 3, 0}, which has no strict majority and therefore
    yields no consensus at all.

⚠️ Harp is `keyboard` in this repo's taxonomy, not `string`, and that is load
bearing rather than incidental — a harp's signature is chosen for PEDAL and
enharmonic reasons and genuinely may differ from the score's. Do not "fix" that
classification into `string`.
"""

from __future__ import annotations

import collections
import dataclasses
import json
from typing import Any, Iterable, Sequence

from . import instruments as _inst

#: Instruments conventionally engraved with NO key signature, their accidentals
#: written inline. Excluded from the witness set; still judged, but a reading of
#: 0 against a non-zero prediction is recorded as the convention rather than as
#: a contradiction.
#:
#: ⚠️ This is a claim about ENGRAVING PRACTICE, strongest in the 18th-19th
#: century repertoire this project reads, and it is NOT derivable from the
#: staff. A modern edition may well print a horn signature. That is why the
#: carve-out is narrow: it only ever explains a ZERO.
NO_SIGNATURE_CONVENTION: frozenset[str] = frozenset({
    "Timpani", "Horn", "Trumpet", "Cornet", "Flugelhorn",
})

#: Concert-pitch instruments that may nonetheless print a DIFFERENT signature
#: from the score's, so they may not establish it. They are still judged.
#:
#: ⚠️ Harp is the case: its signature is chosen for PEDAL and enharmonic
#: reasons -- a harpist may want C-flat major where the score says B major --
#: so it is a fact about the instrument's mechanism and not about the key.
#: This repo classifies Harp as `keyboard` rather than `string`, which already
#: keeps it out of the string-only form of the argument; this keeps it out of
#: the general one. ⚠️ DECLARED, NOT MEASURED: no corpus here prices how often
#: a harp actually departs, so this is the conservative reading of a known
#: mechanism, and it costs at most one witness on a page that has many.
MAY_DIFFER_NOT_A_WITNESS: frozenset[str] = frozenset({"Harp"})

#: Fewest concert-pitch staves that may establish a key. Below this the page
#: has not corroborated anything and the module abstains.
MIN_WITNESSES = 3

#: Share of the witnesses the winning value must hold before a key is DECLARED.
#:
#: ⚠️ NOT A TUNED CONSTANT -- it is the weakest form of the premise. The claim
#: is that concert-pitch instruments AGREE, so any dissent among them is
#: already evidence the premise is failing here, and a bare strict majority is
#: not agreement at all. Measured, that mattered: on Tchaikovsky 6 mvt1 m161
#: the witnesses split 7 to 6, a strict majority admitted it, the winning side
#: was the WRONG one (the movement's second subject is in D major, and the six
#: reading 2 sharps were right), and the module confidently flagged six correct
#: staves. 7/13 = 0.538 abstains under this; 2/3 = 0.667 and 8/8 = 1.0 stand.
MAJORITY_SHARE = 0.60

#: A score prints no key signatures when this share of the staves that SHOULD
#: show one printed nothing instead. Deliberately high: the cost of a false
#: positive here is silence about real contradictions, so it must take a
#: near-sweep and not a majority.
NO_SIGNATURE_SHARE = 0.80
#: ...over at least this many staves, so a two-staff misread cannot trip it.
NO_SIGNATURE_MIN_STAVES = 3

# ── outcomes ────────────────────────────────────────────────────────────────
AGREES = "agrees"
CONTRADICTS = "contradicts"
CONVENTION_NO_SIGNATURE = "convention_no_signature"
NO_READING = "no_reading"
NO_INSTRUMENT = "no_instrument"
KEY_DEPENDENT_UNKNOWN = "key_dependent_transposition_unknown"
#: An unpitched instrument has NO key to be right or wrong about.
UNPITCHED = "unpitched"


@dataclasses.dataclass(frozen=True)
class StaffKey:
    """One staff's inputs: who it is, and what key it was read as."""

    staff_index: int
    label: str | None = None
    read_fifths: int | None = None
    #: Override the lexicon — for truth rows and tests.
    instrument: str | None = None
    fifths_offset: int | None = None


@dataclasses.dataclass(frozen=True)
class StaffVerdict:
    staff_index: int
    label: str | None
    instrument: str | None
    fifths_offset: int | None
    read: int | None
    expected: int | None
    outcome: str
    is_witness: bool

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class Consensus:
    concert_fifths: int | None
    n_witnesses: int
    tally: dict[int, int]
    reason: str
    staves: tuple[StaffVerdict, ...]
    strength: str = "none"          # unanimous | majority | none
    no_signature_score: bool = False

    @property
    def contradictions(self) -> tuple[StaffVerdict, ...]:
        return tuple(s for s in self.staves if s.outcome == CONTRADICTS)

    def as_dict(self) -> dict[str, Any]:
        return {
            "concert_fifths": self.concert_fifths,
            "n_witnesses": self.n_witnesses,
            "tally": {str(k): v for k, v in sorted(self.tally.items())},
            "reason": self.reason,
            "strength": self.strength,
            "no_signature_score": self.no_signature_score,
            "n_contradictions": len(self.contradictions),
            "staves": [s.as_dict() for s in self.staves],
        }



def _parse_bare_key_offset(inst: "_inst.Instrument", label: str) -> int | None:
    """Whether a bare key token trails the alias ("Cor. D."), via the lexicon.

    `instruments._parse_bare_key` is private and takes the alias that fired, so
    this re-asks it per alias rather than reimplementing the regex -- the point
    is to stay on ONE definition of what naming a key looks like.
    """
    if not _inst.takes_key(inst):
        return None
    low = label.lower()
    for alias in _inst.aliases_of(inst):
        if alias in low:
            got = _inst._parse_bare_key(low, alias)
            if got is not None:
                return got
    return None


def _resolve(s: StaffKey) -> tuple[str | None, int | None, bool]:
    """→ (instrument name, fifths_offset, transposition_is_known).

    An explicit `instrument`/`fifths_offset` on the input wins over the
    lexicon, so a hand-verified truth row and a probe can both drive this
    without a margin reader.
    """
    if s.instrument is not None:
        return s.instrument, (s.fifths_offset or 0), s.fifths_offset is not None
    if not s.label:
        return None, None, False
    try:
        m = _inst.lookup(s.label)
    except Exception:                                          # noqa: BLE001
        return None, None, False
    if m is None:
        return None, None, False
    inst = m.instrument
    # ⚠️ `chromatic is None` means the transposition is KEY-DEPENDENT: the
    # instrument is built in a key and `lookup` falls back to
    # `default_fifths_offset` when the label does not say which. That default
    # is a CONVENTION, not a reading, so a staff resting on it may neither vote
    # nor be contradicted -- a clarinet in A judged as one in B-flat would
    # produce a confident FALSE contradiction, which is the one outcome this
    # module must not manufacture.
    #
    # ⚠️ AND THE OBVIOUS TEST FOR IT IS WRONG. Comparing `m.fifths_offset`
    # against `default_fifths_offset` cannot tell "named B-flat" from
    # "defaulted to B-flat", BECAUSE THE DEFAULT CLARINET IS THE B-FLAT ONE --
    # the two values coincide exactly where the label is most often explicit.
    # Measured on Beethoven 5 p1, that read `Clarinetti in B` as unknown and
    # let the one correctly-deduced transposing staff on the page escape
    # judgement. Ask the LABEL whether it names a key, which is what
    # `parse_in_key` is for, rather than inferring it from the answer.
    if inst.chromatic is not None and inst.chromatic % 12 == 0:
        known = True                       # concert pitch: nothing to name
    else:
        known = (_inst.parse_in_key(s.label) is not None
                 or _parse_bare_key_offset(inst, s.label) is not None)
    return inst.name, m.fifths_offset, known


def _is_witness(name: str | None, offset: int | None, known: bool) -> bool:
    """A staff may establish the concert key only if it prints it verbatim."""
    if name is None or offset is None or not known:
        return False
    if name in NO_SIGNATURE_CONVENTION or name in MAY_DIFFER_NOT_A_WITNESS:
        return False
    inst = next((i for i in _inst.INSTRUMENTS if i.name == name), None)
    if inst is None or inst.unpitched:
        return False
    if offset != 0:
        return False
    # THE OCTAVE TRAP — `% 12`, not `== 0`.
    return inst.chromatic is not None and inst.chromatic % 12 == 0


def _same_instrument_two_keys_read_alike(resolved) -> bool:
    """PROOF, needing no constant: the page contradicts itself.

    Two staves of ONE instrument built in DIFFERENT keys, printing the SAME
    signature, is impossible where signatures are printed. Holst's `Mercury`
    prints `Clarinet 1 in B-flat` and `Clarinet 1 in A` -- expectations +2 and
    -3 -- and both read 0.
    """
    by_inst: dict[str, set[tuple[int, int]]] = collections.defaultdict(set)
    for s, name, offset, known, _w in resolved:
        if name and known and offset is not None and s.read_fifths is not None:
            by_inst[name].add((offset, s.read_fifths))
    for pairs in by_inst.values():
        if len({o for o, _r in pairs}) > 1 and len({r for _o, r in pairs}) == 1:
            return True
    return False


def _transposing_staves_all_read_zero(resolved, concert: int | None) -> bool:
    """The GENERAL case, and it is a whole repertoire rather than an edge.

    ⚠️ Sean, 2026-09-08: *"It is common for modern scores to have no key
    signatures."* The proof above only fires where the page happens to print
    one instrument in two different keys, which most scores do not -- so on
    its own it would leave every no-signature score charging each of its
    transposing staves, which is the module's worst failure mode (a confident
    contradiction against correct engraving) applied to a whole era.

    The general test asks the staves that SHOULD show something: of those whose
    deduced signature is non-zero, what fraction printed nothing? A signature-
    bearing score answers ~0 (a B-flat clarinet in C minor really does print
    one flat); a signature-less score answers 1.

    ⚠️ The denominator deliberately includes CONCERT-PITCH staves with a
    non-zero expectation. Restricting it to transposing staves alone would make
    an ordinary tonal page look signature-less as soon as its two horn staves
    were misread -- with a denominator of 2. On Beethoven 5 p1 the full
    denominator is 10 and only Trombe and Timpani read zero, so the ratio is
    0.2 and the rule stays quiet, which is the behaviour that matters.
    """
    if concert is None:
        return False
    expectant = [(s, offset) for s, _n, offset, known, _w in resolved
                 if known and offset is not None and s.read_fifths is not None
                 and concert + offset != 0]
    if len(expectant) < NO_SIGNATURE_MIN_STAVES:
        return False
    zeros = sum(1 for s, _o in expectant if s.read_fifths == 0)
    return zeros >= NO_SIGNATURE_SHARE * len(expectant)


def _score_prints_no_signatures(resolved, concert: int | None) -> bool:
    return (_same_instrument_two_keys_read_alike(resolved)
            or _transposing_staves_all_read_zero(resolved, concert))


def analyse(readings: Iterable[StaffKey]) -> Consensus:
    """Establish the concert key from the concert-pitch staves, then judge all.

    Abstains — `concert_fifths is None` — rather than guessing, whenever the
    witnesses are too few or fail to reach a STRICT majority. The tally is
    reported either way, because "the witnesses split 2/2/1" is itself the
    finding on a bitonal page.
    """
    rows = list(readings)
    resolved = []
    for s in rows:
        name, offset, known = _resolve(s)
        resolved.append((s, name, offset, known, _is_witness(name, offset, known)))

    votes = [s.read_fifths for s, _n, _o, _k, w in resolved
             if w and s.read_fifths is not None]
    tally = dict(collections.Counter(votes))
    n = len(votes)

    concert: int | None = None
    strength = "none"
    if n < MIN_WITNESSES:
        reason = f"too_few_witnesses ({n} < {MIN_WITNESSES})"
    else:
        top, count = collections.Counter(votes).most_common(1)[0]
        if count == n:
            concert, strength = top, "unanimous"
            reason = f"unanimous {count}/{n}"
        elif count * 2 > n and count >= MAJORITY_SHARE * n:
            concert, strength = top, "majority"
            reason = f"majority {count}/{n}"
        else:
            # Not agreement, only a plurality. A page whose concert-pitch
            # staves genuinely disagree lands here BY DESIGN, and so does one
            # where enough of them were misread to make the vote meaningless.
            reason = f"no_majority (best {count}/{n})"

    # ── the score that prints NO key signatures at all ──────────────────────
    # ⚠️ A SCORE-LEVEL convention, not an instrument one, and the narrow
    # brass-and-timpani carve-out below does not reach it. Holst's `Mercury`
    # is written without signatures throughout, so its clarinets read 0 against
    # predictions of +2 and -3 and every one of them would be charged as a
    # contradiction.
    #
    # The detector needs no threshold, because the page contradicts ITSELF:
    # two staves of the SAME instrument built in DIFFERENT keys, printing the
    # SAME signature, is impossible unless the signature is absent. Mercury
    # prints `Clarinet 1 in B-flat` and `Clarinet 1 in A` -- expectations +2
    # and -3 -- and both read 0.
    no_signature_score = _score_prints_no_signatures(resolved, concert)

    out: list[StaffVerdict] = []
    for s, name, offset, known, witness in resolved:
        expected = (None if concert is None or offset is None or not known
                    else concert + offset)
        inst_obj = next((i for i in _inst.INSTRUMENTS if i.name == name), None)
        if inst_obj is not None and inst_obj.unpitched:
            # ⚠️ `Instrument.unpitched` is documented as "exclude from key /
            # pitch reasoning" and the first cut honoured only half of it --
            # these staves were kept out of the WITNESS set and then JUDGED
            # anyway. Measured over 152 orchestral reference encodings, that
            # was the single largest source of false contradictions: Triangle,
            # Snare Drum, Cymbal, Tamtam, Gran Cassa and Glockenspiel all
            # resolve to `Percussion`, all print 0, and all were charged
            # against the score's key. A drum has no key.
            outcome = UNPITCHED
            expected = None
        elif name is None:
            outcome = NO_INSTRUMENT
        elif not known:
            outcome = KEY_DEPENDENT_UNKNOWN
        elif s.read_fifths is None:
            outcome = NO_READING
        elif expected is None:
            outcome = NO_READING if concert is None else NO_INSTRUMENT
        elif s.read_fifths == expected:
            outcome = AGREES
        elif s.read_fifths == 0 and expected != 0 and (
                name in NO_SIGNATURE_CONVENTION or no_signature_score):
            # Two carve-outs, both narrow, both only ever explaining a ZERO:
            # this instrument prints no signature by convention (natural brass,
            # timpani), or this whole SCORE does. Anything other than 0 is
            # still a contradiction.
            outcome = CONVENTION_NO_SIGNATURE
        else:
            outcome = CONTRADICTS
        out.append(StaffVerdict(
            staff_index=s.staff_index, label=s.label, instrument=name,
            fifths_offset=offset, read=s.read_fifths, expected=expected,
            outcome=outcome, is_witness=witness))

    return Consensus(concert_fifths=concert, n_witnesses=n, tally=tally,
                     reason=reason, staves=tuple(out), strength=strength,
                     no_signature_score=no_signature_score)


# ── adapters ────────────────────────────────────────────────────────────────

def _fifths_of(key_sig: Any) -> int | None:
    """`{'sharps': 0, 'flats': 3}` or an int → fifths. None if unreadable.

    ⚠️ The legacy pipeline writes the DICT and the staged one writes an INT.
    Accepting both here is a unit adapter, not a judgement — the same defect
    `be76d961` fixed in the divergence table, where a dict never equalled an
    int and every decided key row was DIFFER by construction.
    """
    if key_sig is None:
        return None
    if isinstance(key_sig, bool):
        return None
    if isinstance(key_sig, int):
        return key_sig
    if isinstance(key_sig, dict):
        if "fifths" in key_sig and isinstance(key_sig["fifths"], int):
            return key_sig["fifths"]
        sharps, flats = key_sig.get("sharps"), key_sig.get("flats")
        if isinstance(sharps, int) and isinstance(flats, int):
            return sharps - flats
        if isinstance(sharps, int):
            return sharps
        if isinstance(flats, int):
            return -flats
    return None


def readings_from_page(page: dict[str, Any]) -> list[StaffKey]:
    """Pull one `StaffKey` per staff out of a legacy `transcribe` page dict."""
    rows: list[StaffKey] = []
    idx = 0
    for system in page.get("systems", []) or []:
        for staff in system.get("staves", []) or []:
            label = (staff.get("instrument_label")
                     or staff.get("label") or None)
            name = staff.get("instrument") or None
            rows.append(StaffKey(
                staff_index=staff.get("staff_index", idx),
                label=label if isinstance(label, str) else None,
                read_fifths=_fifths_of(staff.get("key_signature")),
                instrument=name if isinstance(name, str) else None))
            idx += 1
    return rows


def analyse_result(result: dict[str, Any]) -> list[tuple[int, Consensus]]:
    """One consensus per page of a `transcribe` result."""
    out = []
    for i, page in enumerate(result.get("pages", []) or []):
        rows = readings_from_page(page)
        if rows:
            out.append((page.get("page_index", i), analyse(rows)))
    return out


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Key consensus over a transcription")
    ap.add_argument("result_json")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    result = json.loads(open(a.result_json).read())
    pages = analyse_result(result)
    if a.json:
        print(json.dumps([{"page": p, **c.as_dict()} for p, c in pages], indent=1))
        return 0
    for p, c in pages:
        print(f"\n── page {p}: concert={c.concert_fifths} "
              f"({c.reason}), witnesses={c.n_witnesses}, tally={c.tally}")
        for s in c.staves:
            flag = "  <-- CONTRADICTS" if s.outcome == CONTRADICTS else ""
            print(f"   {s.staff_index:>3} {str(s.instrument):<16}"
                  f"off={str(s.fifths_offset):>4} read={str(s.read):>4} "
                  f"exp={str(s.expected):>4}  {s.outcome}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
