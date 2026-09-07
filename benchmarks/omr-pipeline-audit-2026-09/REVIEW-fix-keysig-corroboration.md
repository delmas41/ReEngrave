# Review — FIX AGENT J, `claude/fix-keysig-corroboration`

**Reviewer: Agent II**, author of the finding, at `553494e7`. Read-only; its test
file run (**39 passed**, 0.17 s, no pipeline), suite not run, no `scan_eval`.

## VERDICT: **APPROVE**

Two minor fixes below, neither blocking. The witness argument is right, it is
implemented as position and not value, and the wiring closes the gap that
blocked the clef sweep.

---

## 1. The witness argument — CORRECT, and the code does what the prose says

**The insight is real and it is better than what I gave the coordinator.** I said
the meter's witness does not transplant because a key change is staff-scope. That
was half the fact. The other half is that **a key change is an EVENT with a
position and a VALUE, and only the value is staff-scope** — the double barline is
printed at one bar on every staff of the system. Corroborating the event and not
the value is the correct resolution and I did not have it.

**The code tests position.** `drop_uncorroborated_key_changes` builds

```python
witnesses: Counter[int] = Counter()
for changes in per_staff.values():
    for change in changes:
        witnesses[change["measure_index"]] += 1
```

keyed on **`measure_index` alone** — no `before`, no `after`, no fifths anywhere
in the key. `_changes_in_staff` uses the value only to decide *that* a change
happened, never to match one staff against another. `MIN_WITNESSES = 2`, and
since the changing staff counts itself that means **one other staff**, pinned
from both sides by `test_one_witness_is_enough_and_none_is_not`.

**The proxy test is the right demonstration**: three staves changing at one bar
to **0 flats / 2 sharps / 3 sharps** — value corroboration reverts all three,
position corroboration keeps all three, and it asserts `reverted == 0, kept == 3`.

⚠️ **And a hazard I would have flagged is already pinned.**
`TestWitnessesAreCountedByMeasureIndex` builds two staves whose cell lists do not
line up (one lost a barline) and asserts they still witness each other. The code
correctly splits the two indices: `measure_index` for the shared bar identity,
`ordinal` for the walk over this staff's own list. Getting that backwards would
have silently broken the witness on exactly the pages with a dropped cell.

### Is *"the bar does not differ, the value does"* true of this corpus?

⚠️ **Unverifiable on this corpus, by them and by me — it contains no real
mid-staff key change to check against.** What I can say, and what I think should
go in the record:

**It is the WEAKER of the two available claims, and that is why it is safe.** The
meter guard's witness requires other staves to read *the same value*; this one
requires only that they change *at the same bar*. Every page on which the meter's
witness would hold, this one also holds; the converse is false. So relative to
the transplanted witness the guard **fails safe** — it can only be more
permissive of real music, never less. For a guard whose cost is unmeasurable,
that is the right direction, and it is a structural argument rather than a
corpus one, which is what makes it usable here.

## 2. ⚠️ MINOR — a documented number is wrong, and the cause is a class-prefix over-match

The module docstring states *"104 first-cell markers against 19 later-cell ones
(confidence 0.26-0.73)"*. My round-3 record says **15** later-cell cells at
0.26-0.70. Both are reproducible; they disagree because of the class filter.

`benchmarks/omr-keysig-corroboration-2026-09/probe/probe_witnesses.py:71` uses
`(x.get("class") or "").lower().startswith("key")`. Enumerated over the scan
fixtures, the later-cell `key*` classes outside the three real ones are:

```
{'keyboardPedalUp': 5}
```

**`keyboardPedalUp` is a pedal marking, not a key signature.** Under
`{keysharp, keyflat, keynatural}` the counts are 15 cells / 16 markers; under
`startswith("key")` they are 19 / 20, and the extra 0.73 confidence is a pedal
mark's.

⚠️ **Behaviour is unaffected**, and I checked rather than assumed: the guard
never filters on a detection class. It reads `measure["key_signature"]`, and
`_respell_measure` filters on `category == "notehead"`. The over-match is
confined to the probe and the docstring.

Also loose in the same sentence: 104 and 19 are both **cells**; the markers are
220 and 20. Calling them "markers" reads as a marker count and is wrong for the
first number by a factor of two.

**Fix:** narrow the probe's filter to the three key-signature classes, restate
the number as 15, and say "cells". It matters because the branch and the audit
record now carry different figures for the same population, and the audit's is
the one that has been quoted.

## 3. The re-read fix is GENERAL, not fitted

```python
before = None
for measure in measures[:change["ordinal"]]:
    if measure.get("key_signature"):
        before = measure["key_signature"]
```

It re-walks the staff from the start at revert time and takes the last non-`None`
key, so it reads whatever earlier reverts have already written, for any number of
prior changes and any values. It is not conditioned on the fixture's shape.

**And it reproduces the meter guard's own structure**, which is the corroboration
I would want: `rhythm.drop_uncorroborated_meter_changes` re-walks for the
identical reason. `test_a_later_change_gets_its_own_test_rather_than_being_swallowed`
pins the real `[2, 1, 1, 3]` shape and asserts `[2, 2, 2, 2]` — under the old bug
it would have been `[2, 2, 2, 1]`, restoring the first flip's own wrong reading.

## 4. Flag-off byte-identity — by construction, and asserted at the right level

The **only** call site is inside `if keysig_corroboration_enabled():`. So flag-off
is byte-identical by construction, not by measurement, and the measurement is a
control on top rather than the claim.

⚠️ **`test_the_call_is_gated_on_the_env_flag` is the test the clef sweep did not
have**: it does not check that "an `if` exists nearby" — it walks for an `ast.If`
whose **`test`** calls the flag function and whose **body** calls the guard. So
replacing the condition with `True` reddens it, which is the exact property
flag-off identity rests on. `test_both_imported_names_are_used` additionally
makes "call site deleted, import left behind" a failing state. Three wiring
tests, and the mutation that deletes the block reddens all three.

## 5. The precedence reproduction is right

`_respell_measure` implements inline accidental → accidental carried earlier in
this bar → key → diatonic, and the key granularity matches `_detections_for_cell`
exactly: the **carry** is keyed `(letter, octave)`, the **key** is keyed
`letter`. A drawn natural sets the carry to "no alteration" and blocks the key
for the rest of the bar on that letter+octave. It walks left-to-right in the
canonical frame because "carried from earlier" is an ordering fact and the
detection list is in detector order — correct, and a real trap avoided.

It also re-spells `pitch_candidates` by the same rules. Right call: those are on
**100% of noteheads** (5,896 across the two corpora), and leaving them spelled
against the reverted key would put a contradiction on every note it touched.

## 6. The XML-parse claim — METHOD verified, numbers not committed

`verify_semantics.py` uses `xml.etree.ElementTree`, extracts per-note
`(measure, step, alter, octave, duration, type)`, and **hard-asserts that the note
count and the `(step, octave)` sequence of every part are unchanged**, reporting
any field other than `alter` that moved. That is the right instrument, and the
warning is well-founded: difflib aligning an inserted `<alter>` across a run of
identical notes does make `<note>`/`<step>` appear to move.

⚠️ **Third build in a row with no committed artefact.** The 22-change / 15-note
figures are checkable in one command and are not in the repo. Not blocking — the
probe is committed and uses the fail-loud `_fixtures` helper — but a branch whose
subject is "record the evidence" should commit its own.

## 7. The limit — I ACCEPT the framing, and would add one sentence

Benefit measured 7/7; cost not measurable, because the corpus holds zero real
mid-staff key changes. The synthetic proxy shows the rule does not reject the
**shape** of a real change; it does not show the detector would **read** one on
two staves of a scanned page, and the write-up says so. That is honest and it is
the correct reason for default-OFF.

⚠️ **What I would add, because it points the same way and is measurable:** on the
scan family later-cell key markers appear on **19 cells across 11 pages** (15
under the corrected filter) and on the engraved family on **zero**. A real change
would have to be detected on **two staves of the same system at the same bar**,
against an observed density of roughly 1.4 such cells per page scattered across
11-27 staves. So there is a concrete reason to expect the guard's cost on real
music to be non-trivial rather than negligible — which strengthens default-OFF
rather than undermining it, and is better in the record than left as an unknown.

---

## Adjudication 1 — LilyPond mid-staff key: real, and it must NOT go on `KNOWN_GAPS`

**Confirmed.** `_lily_staff_block` writes `\key` at `export.py:547` and `:549`
only, and its body contains **zero** references to `key_signature` at measure
level. One `\key` per staff, never a change.

**It is NOT the tenth gap in the numbered family, and `KNOWN_GAPS` is the wrong
home** — this is a scope point, not a severity one. `export_coverage` compares
**MusicXML**; an entry for a LilyPond-only drop could never fire and never close,
so it would sit there permanently unfalsifiable. That is precisely the state
`test_the_inventory_has_no_stale_entries` exists to prevent, and CLAUDE.md
already set the precedent for this exact case: the LilyPond dynamics drop is
recorded as *"not on `KNOWN_GAPS` because `export_coverage` compares MusicXML"*.

**Right home:** a LilyPond-side coverage list, which does not exist. **Interim:**
record it as a fourth member of the known LilyPond-only drops beside beams,
directions and dynamics. Worth noting the asymmetry is now four items deep — that
is the argument for building the list, and it is a commission rather than a fix.

## Adjudication 2 — `active_key_sig_by_staff`: REAL, and it is three, not one

**Confirmed, and pre-existing — not this branch's.** The read at
`transcribe.py:4800` and the write at `:5160` use the identical
`(p, sys_idx, staff_idx)` tuple, and each tuple is processed exactly once, so the
read can never find an entry. The carry never fires; the staff always falls
through to `alterations_for_fifths(seeded_fifths or 0)`.

⚠️ **The same pattern is on all three carries:**

| dict | read | write | live? |
|---|---|---|---|
| `active_clef_by_staff` | `:4626`, `:4778` | `:5159` | **dead** |
| `active_key_sig_by_staff` | `:4800` | `:5160` | **dead** |
| `active_time_sig_by_staff` | `:4812` | `:5161` | **dead** |

And no reading of the tuple rescues it: `staff_idx` is numbered **across the
page**, so system 1's staves carry different indices from system 0's, and a
"carry from the previous system" could not be expressed by this key even in
principle.

**The clef has a working carry by another route** — `clef_continuity`
(`:4761`, `:4780`, `:5163`, `:5166`) — which is what makes `active_clef_by_staff`
recognisable as vestigial rather than merely broken.

⚠️ **Consequence worth carrying into the record:** because the key carry never
fires, every staff re-seeds from the header vote on every system. That is part of
why `key_signature_final` was stale on **19 of 26** scan staves in my round-3
measurement — the field records a change against a baseline the carry was
supposed to have supplied.

## What I want on the record as good

- **Finding the resolution I did not have**, and getting the safe direction of it:
  corroborating the event is strictly weaker than corroborating the value, so
  the guard cannot be less permissive than the transplanted witness would be.
- **Refusing confidence as the primary witness**, with the reason stated as an
  unfalsifiability argument rather than a preference — a constant fitted against
  a corpus containing zero positives cannot be tested, and the project has
  refused that shape before.
- **Reporting the 22 output changes as a COST**, with an instrument that could
  have contradicted it, and warning that the naive reading looks alarming.
- **Deleting `key_signature_final` when no change survives** — unprompted, and it
  is the one place this pass can act on the stale-`*_final` family.
