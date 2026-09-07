"""Undo mid-staff KEY-SIGNATURE changes that nothing on the page corroborates.

`OMR_KEYSIG_CORROBORATION` — **DEFAULT OFF**. Flag-off is byte-identical by
construction: `drop_uncorroborated_key_changes` is never called.

THE DEFECT
----------
Within thirty lines of `transcribe.py` three facts take the identical
unfloored per-cell overwrite — the clef, the key signature and the meter — and
the surviving-flip counts rank INVERSELY with their protection. Measured over
the 11 stored scan transcriptions (193 staves) and the 11 engraved ones (224):

    clef     2-entry allowlist, identity-gated, OFF   11 flips   /  0
    KEY SIG  no guard at all                           7 flips   /  0
    meter    `rhythm.drop_uncorroborated_meter_changes` 0 flips   /  0

The mechanism is exact. Where the slot fit abstains,
`transcribe._detect_key_sig_from_cell` falls back to COUNTING markers, so one
stray marker reads as one accidental whatever the staff was in — every one of
the seven flips lands on exactly one accidental. And the protection that does
exist is applied to the wrong cell: `skip_key_sig_detection` silences the
reader on cell 0 *because the cross-page vote already ruled*, then lets later
cells run — where the argument is strictly STRONGER, because on cell 0 the
reader looks at a printed key signature and on cell 11 it looks at ink that
resembles one. Measured over `keySharp` / `keyFlat` / `keyNatural`: **220
markers on 104 first cells** against **15 markers on 15 later cells**
(confidence 0.26-0.70, median 0.42), and **7 of those 15 change the key** —
the other 8 re-read a key already in effect. On the engraved family it is 486
markers on 176 first cells and **ZERO later cells**, which is why that family
shows no flips and cannot price this.

⚠️ The later-cell figure was 19 cells at 0.26-0.73 in the first draft of this
docstring and in the audit's own record. Both came from a probe matching
`startswith("key")`, which also catches `keyboardPedalUp` — a PEDAL marking.
The guard never reads a detection class (it reads `measure["key_signature"]`,
and `_respell_measure` filters on `category == "notehead"`), so no behaviour
depended on it. ⚠️ Under the named classes I measure 15 cells carrying 15
markers, one each; the audit reports 16 markers and that one is not
reproducible here.

WHICH WITNESS, AND WHY NOT THE OTHER TWO
----------------------------------------
This is `rhythm.drop_uncorroborated_meter_changes` in SHAPE — a page-scope
pass that reverts an uncorroborated mid-staff change — but its WITNESS does
not transplant, and getting that wrong is the way to break real music. A meter
change is corroborated by other staves reading THE SAME METER, because a meter
is one fact shared by the system. A key signature is not: transposing
instruments genuinely carry different keys at the same bar, so "the other
staves read something else" is not evidence of anything.

What DOES transplant is the POSITION. A key change is printed at one bar of
one system, behind a double barline, on every staff of that system — the
VALUE differs per transposition, the BAR does not. So the witness here
corroborates the EVENT and not the value: a mid-staff key change stands only
where another staff of the same system also changes key at the same measure
index.

Measured against the seven (`benchmarks/omr-keysig-corroboration-2026-09/`):

    W1  contradicts a cross-page vote that already spoke for this staff  5 / 7
    W2  another staff of the same system changes at the same measure     0 / 7
    W3  the reading's own confidence                                     — see below

**W2 is the witness**: all seven are the only staff of their system to change
at that bar, in systems of 11 to 17 staves.

W1 — the staff's own cross-page vote — is REPORTED, not decided on, and the
reason is a scope argument rather than a coverage one. The vote reads the
staff's HEADER; it is authoritative about the key the staff OPENS in and says
nothing about whether the key changes at bar 6. So it cannot be allowed to
veto a corroborated change, and where a change is uncorroborated W2 has
already condemned it. It reaches 5 of 7 rather than 7 because two of the
flips are on staves the vote never spoke for. It is recorded per revert
because on those five it is the sharper evidence: on beethoven-sym5-575951-p1
the vote said *"rejected: 1 flat differs from the system's 3 flats on too
little"* and the mid-staff overwrite installed exactly that rejected 1 flat;
on mahler-sym5-p2 it said *"kept: agrees with the system's 4 sharps"* and a
single `keySharp` at confidence 0.33 destroyed it to 1 sharp.

W3 — the reading's own confidence — is REFUSED as a primary. The seven sit at
0.26-0.57 inside a later-cell population running 0.26-0.73, so separating
them needs a fitted constant; and the corpus holds no real mid-staff key
change to fit it against, which makes such a constant unfalsifiable by
construction. That is the shape this project has refused before (the ink-
coverage and whitespace-gutter discriminators in `time_signature_locator`).

⚠️ **W2 IS THE WEAKER OF THE TWO CLAIMS, AND THAT IS WHY IT IS USABLE HERE.**
The meter's witness needs other staves to read the same VALUE; this one needs
only that they change at the same BAR. Every page on which the transplanted
witness would hold, this one holds too — the converse is false. So relative to
the wrong witness the guard **fails safe structurally, not empirically**, which
is what makes it shippable while its cost cannot be measured. (Credit: the
reviewer of this branch, who also supplied the sharper framing of the defect —
a key change is an event with a POSITION and a VALUE, and only the value is
staff-scope.)

A fourth candidate — same-instrument agreement across systems, the shape
`contextual._fill_defaulted_clefs` uses — is unavailable here for two
reasons: the part-to-slot join is produced by the contextual post-pass, which
runs AFTER this point and abstains on most pages, and a mid-staff change is a
within-system event that a different system's staff cannot witness.

⚠️ WHAT THIS CANNOT MEASURE
---------------------------
**The corpus contains ZERO real mid-staff key changes** — 0 corroborated
changes across 417 staves of both families. So the benefit is measurable (do
the seven spurious flips stop?) and the COST is not (does the guard block a
real change?). That asymmetry is the whole reason this ships default-OFF. The
closest available proxy is a synthetic page carrying a real, system-wide key
change, which `tests/test_key_signature_corroboration.py` builds and asserts
survives — a proxy, not a measurement of the cost on real music.

⚠️ **AND THERE IS CONCRETE REASON TO EXPECT THAT COST TO BE NON-TRIVIAL
RATHER THAN NEGLIGIBLE.** A real change has to be DETECTED on two staves of
one system at the same bar for W2 to keep it. Later-cell key markers appear on
**15 cells across 11 scanned pages** — about 1.4 per page, over systems of 11
to 27 staves — and no two of the 15 share a bar. On that detection density,
two staves agreeing on one bar is not the common case, so a genuine mid-staff
key change on a scan would more likely be reverted than kept. That argues for
default-OFF rather than against the rule.

⚠️ REVERTING THE KEY IS NOT ENOUGH ON ITS OWN
---------------------------------------------
Unlike the meter — which nothing re-derives per note — the key signature is
consumed INLINE while the cell is read: `transcribe._detections_for_cell`
spells every notehead's pitch against `active_key_sig` at the moment it builds
it, and MusicXML then carries `<key>` and each note's `<alter>` separately. A
pass that reverted `measure["key_signature"]` alone would emit a `<key>` of
two flats over notes still spelled with one — a self-inconsistent page, which
is the "detected then dropped" family this project keeps paying for, inverted.
So the revert re-spells the noteheads it un-keys, reproducing the precedence
`_detections_for_cell` uses (inline accidental > carried in this measure >
key signature > none) and touching only the notes that fall through to the
key. A note carrying its own accidental, or inheriting one from earlier in its
own bar, is left exactly as it was.

⚠️ THE LILYPOND EXPORTER NEVER EMITTED A MID-STAFF KEY CHANGE AT ALL.
`export._lily_staff_block` writes one `\\key` per staff from the STAFF-level
opening signature and never reads `measure["key_signature"]`, so under this
flag the LilyPond output is byte-identical on four of the five rows that change
and moves only where notes were re-spelled. That is a pre-existing export gap,
wider than this guard and not addressed by it.

MEASURED WITH
-------------
Export-only, over the stored transcriptions — no detector, no weights, seconds
rather than hours. Every probe routes through
`benchmarks/omr-pipeline-audit-2026-09/probe/_fixtures.py` and exits 2 on an
empty fixture set.

    probe_key_signature_flips.py   (omr-pipeline-audit-2026-09) the defect
    probe_witnesses.py             W1 / W2 / W3 against the seven
    ab_export.py                   before | before | flag-off | flag-on
    verify_semantics.py            what moved, read with an XML parser
    diff_lines.py                  the raw line diff, and the exposed notes

⚠️ Those probes deliberately do NOT call `_fixtures.chdir_root()`: it cds to
the MAIN checkout, whose `tools/omr` need not contain this module, and every
arm would then import the same unchanged code and report a clean identical
A/B — the failure the A/B exists to rule out. Code from this worktree,
fixtures from wherever they live.
"""
from __future__ import annotations

import os
from collections import Counter
from typing import Any

#: Env var. Absent or "0"/"false"/"off" ⇒ the pass never runs.
ENV_FLAG = "OMR_KEYSIG_CORROBORATION"

#: How many staves of a system must change key at the same measure for the
#: change to stand — the staff itself plus one witness.
#:
#: ⚠️ Deliberately the WEAKEST defensible bar, and not a tuned constant. All
#: seven observed flips sit at exactly 1 (no witness at all) in systems of 11
#: to 17 staves, so 2 is the first value that can reject any of them. The
#: sibling meter guard uses `max(2, round(0.5 * n_staves))`, which here would
#: demand 9 witnesses on a 17-staff Mahler system — and mid-staff key markers
#: are detected in only 15 cells across 193 scanned staves, so a
#: fraction-of-the-system bar would revert a genuine key change that only two
#: staves happened to be read on. Requiring one witness keeps the guard as far
#: from a real change as the evidence allows.
MIN_WITNESSES = 2

_ALT_CHARS = "#b"


def enabled(env: dict[str, str] | None = None) -> bool:
    """Whether `OMR_KEYSIG_CORROBORATION` turns this pass on. Default OFF."""
    raw = (env if env is not None else os.environ).get(ENV_FLAG, "")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _split_pitch(pitch: str) -> tuple[str, str | None, int] | None:
    """`'Bb3'` → `('B', 'b', 3)`; `'C4'` → `('C', None, 4)`.

    ⚠️ NOT `transcribe._parse_diatonic_pitch`, which parses the pitch BEFORE
    an alteration is folded in and returns None for `'Bb3'`. What is recorded
    on a notehead is the spelled pitch, so the alteration has to come off
    again before a new one can go on.
    """
    if not pitch or pitch[0] not in "ABCDEFG":
        return None
    i = 1
    while i < len(pitch) and pitch[i] in _ALT_CHARS:
        i += 1
    alt = pitch[1:i] or None
    try:
        return pitch[0], alt, int(pitch[i:])
    except ValueError:
        return None


def _alterations(key: dict[str, Any] | None) -> dict[str, str]:
    return dict((key or {}).get("alterations") or {})


def _respell_measure(
    measure: dict[str, Any],
    new_alterations: dict[str, str],
) -> int:
    """Re-spell every notehead of `measure` whose alteration came from the key.

    Mirrors `transcribe._detections_for_cell`'s precedence exactly — inline
    accidental, then an accidental carried from earlier in this same measure,
    then the key signature, then nothing — and only the last-but-one branch is
    rewritten. Returns how many noteheads changed spelling.

    ⚠️ The walk is left-to-right in the CANONICAL frame (`bbox[0]`), because
    "carried from earlier in this measure" is an ordering fact, and the
    detection list is emitted in detector order rather than in reading order.
    """
    noteheads = [
        d for d in measure.get("detections", [])
        if d.get("category") == "notehead" and d.get("pitch")
    ]
    noteheads.sort(key=lambda d: (d.get("bbox") or [0])[0])
    explicit: dict[tuple[str, int], str | None] = {}
    changed = 0
    for nh in noteheads:
        parsed = _split_pitch(nh["pitch"])
        if parsed is None:
            continue
        letter, _old_alt, octave = parsed
        inline = nh.get("accidental")
        if inline is not None:
            # The engraver drew it. Nothing about the key can move it — but it
            # does set the carry for the rest of this bar.
            explicit[(letter, octave)] = None if inline == "natural" else inline
            continue
        if (letter, octave) in explicit:
            continue  # carried from earlier in this bar; not the key's doing
        new_alt = new_alterations.get(letter)
        rebuilt = f"{letter}{new_alt or ''}{octave}"
        if rebuilt != nh["pitch"]:
            nh["pitch"] = rebuilt
            changed += 1
        # `pitch_candidates` are spelled by the same rules, per candidate.
        for cand in nh.get("pitch_candidates") or []:
            cp = _split_pitch(cand.get("pitch") or "")
            if cp is None:
                continue
            c_letter, _c_alt, c_octave = cp
            if (c_letter, c_octave) in explicit:
                continue
            c_new = new_alterations.get(c_letter)
            cand["pitch"] = f"{c_letter}{c_new or ''}{c_octave}"
    return changed


def _summary(key: dict[str, Any] | None) -> tuple[int, int] | None:
    if not key:
        return None
    return key.get("sharps"), key.get("flats")


def _changes_in_staff(staff: dict[str, Any]) -> list[dict[str, Any]]:
    """Every mid-staff key CHANGE, as `{ordinal, measure_index, before, after}`.

    The staff's OPENING key is not a change (nothing precedes it) and is never
    a candidate here — which is the point: the opening signature is printed and
    the vote already ruled on it, while a later one is ink that resembled one.
    """
    out: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for i, measure in enumerate(staff.get("measures", [])):
        current = measure.get("key_signature")
        index = measure.get("measure_index")
        if index is None:
            index = i
        if (current is not None and previous is not None
                and _summary(current) != _summary(previous)):
            out.append({
                "ordinal": i,
                "measure_index": index,
                "before": previous,
                "after": current,
            })
        if current is not None:
            previous = current
    return out


def drop_uncorroborated_key_changes(
    page: dict[str, Any],
    *,
    min_witnesses: int = MIN_WITNESSES,
) -> dict[str, Any]:
    """Revert mid-staff key changes no other staff of the system corroborates.

    Mutates `page`. Returns
    `{"reverted": n, "respelled": n, "kept": n, "changes": [...]}` — `kept`
    counts corroborated changes left alone, so a caller can tell "nothing was
    wrong" from "nothing was looked at".

    Each reverted change is recorded on its staff under
    `key_signature_corroboration`, with `contradicted_vote` and the vote's own
    reason where the cross-page vote had spoken for that staff.
    """
    reverted = respelled = kept = 0
    records: list[dict[str, Any]] = []
    for system_index, system in enumerate(page.get("systems", [])):
        staves = system.get("staves", [])
        if not staves:
            continue
        per_staff = {id(st): _changes_in_staff(st) for st in staves}
        # A key change is printed at ONE BAR of the system. Corroborate the
        # bar, never the key — see the module docstring.
        witnesses: Counter[int] = Counter()
        for changes in per_staff.values():
            for change in changes:
                witnesses[change["measure_index"]] += 1
        for staff in staves:
            for change in per_staff[id(staff)]:
                if witnesses[change["measure_index"]] >= min_witnesses:
                    kept += 1
                    continue
                measures = staff.get("measures", [])
                # ⚠️ RE-READ at revert time, never the value `_changes_in_staff`
                # saw. A staff can carry two uncorroborated changes — the real
                # `[2 flats, 1 flat, 1 flat, 3 flats]` shape — and reverting the
                # first rewrites the key the second departs FROM. Taking the
                # captured value put that staff back to `[2, 2, 2, 1]`: the
                # second revert restored the first flip's own wrong reading.
                # `rhythm.drop_uncorroborated_meter_changes` re-walks for the
                # same reason.
                before = None
                for measure in measures[:change["ordinal"]]:
                    if measure.get("key_signature"):
                        before = measure["key_signature"]
                after_key = _summary(change["after"])
                new_alterations = _alterations(before)
                n_measures = 0
                for measure in measures[change["ordinal"]:]:
                    current = measure.get("key_signature")
                    if current is None:
                        continue
                    if _summary(current) != after_key:
                        break  # a later change takes over; it gets its own test
                    measure["key_signature"] = dict(before) if before else None
                    respelled += _respell_measure(measure, new_alterations)
                    n_measures += 1
                if not n_measures:
                    continue
                reverted += 1
                voted = staff.get("key_signature_source") == "header_vote"
                record = {
                    "system_index": system_index,
                    "staff_index": staff.get("staff_index"),
                    "measure_index": change["measure_index"],
                    # The key RESTORED, re-read above rather than the value
                    # captured before an earlier revert may have moved it.
                    "from": _summary(before),
                    "to": after_key,
                    "measures_reverted": n_measures,
                    "witnesses": witnesses[change["measure_index"]],
                    "staves_in_system": len(staves),
                    "contradicted_vote": voted,
                    "vote_reason": staff.get("key_signature_reason") if voted else None,
                }
                staff.setdefault("key_signature_corroboration", []).append(record)
                records.append(record)
            # The staff no longer ends anywhere but where it started unless a
            # change survived; `key_signature_final` would otherwise announce a
            # key change the file no longer contains.
            if "key_signature_final" in staff and not _changes_in_staff(staff):
                del staff["key_signature_final"]
    if reverted:
        page["uncorroborated_key_changes_reverted"] = reverted
        page["uncorroborated_key_changes"] = records
    return {
        "reverted": reverted,
        "respelled": respelled,
        "kept": kept,
        "changes": records,
    }
