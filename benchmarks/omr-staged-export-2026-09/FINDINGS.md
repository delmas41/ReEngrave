# The staged pipeline can produce a file — and it says what it could not

`tools/omr/staged/export.py`, wired into the CLI as `--musicxml`:

```bash
python3 -m tools.omr.staged score.pdf --pages 2 --weights <...> \
    --musicxml out.musicxml          # + out.musicxml.coverage.json
python3 -m tools.omr.staged.export staged.json --out out.musicxml
```

The handoff's §3 said the staged path *"cannot produce a file"* — no file in
`staged/` mentioned `musicxml` or `lilypond`, and `grep -c staged export.py`
was 0. That is closed for MusicXML. Four real conductor's pages export, and
all four parse under **music21** (an independent reader, not ours):

| page | parts | join | `<note>` written | held back | measure rests | balanced |
|---|--:|---|--:|--:|--:|:--:|
| beethoven 984073 p2 | 12 | ordinal | 115 | 39 | 121 | ✅ |
| beethoven 984073 p3 | 11 | ordinal | 516 | 195 | 148 | ✅ |
| brahms 317803 p2 | **14** | **slot** | 664 | 351 | 60 | ✅ |
| mahler p2 | 19 | ordinal | 42 | 10 | 123 | ✅ |

---

## 1. ⚠️ WHAT THE EXPORTER FOUND: 2,541 DETECTED GLYPHS THE RECORD CANNOT CARRY

Pooled over those four pages, and each figure is the DETECTOR'S OWN count in
the log — the positive control that makes the zero a result:

| family | detector found | why nothing came out |
|---|--:|---|
| **rest** | **838** | ⚠️ **NO QUANTITY** — no `Q.REST`, no adjudicator, no stub, no `wants` |
| tie | 755 | `arc_kind`/`arc_owner` are stubs **and `arc_box` is never gathered** |
| dynamic | 543 | `dynamic` is a stub **and `dynamic_letter` is never gathered** |
| slur | 291 | as tie |
| fermata | 66 | ⚠️ **NO QUANTITY** |
| articulation | 41 | stub **and `articulation_mark` is never gathered** |
| ornament | 6 | ⚠️ **NO QUANTITY** |
| wedge | 1 | stub **and `wedge_box` is never gathered** |

⚠️⚠️ **RESTS ARE THE FINDING.** `grep -rn 'rest' tools/omr/staged/record.py`
returns three matches and all three are the word inside `*rest` unpacking or
"rests on". There is no rest quantity anywhere in the staged pipeline, so
nothing gathers one, nothing decides one, **and nothing declares its absence
either** — the four starved stubs at least abstain `not_implemented` 2,728
times a page. This is the detected-then-dropped family occurring inside the
architecture built to stop it, and it is the third instance recorded there
after `Ruling.detail` (`record_coverage.py`) and the four starved stubs.

It also means the whole-rest position — *a whole-rest glyph means the BAR* —
**cannot be honoured yet, and the exporter says so instead of pretending.** A
bar with no notes gets a measure rest because we read nothing in it, not
because we read silence, and the two are different claims.

## 2. The coverage record: four different zeros, reported apart

`export_coverage.py` answers "the truth has some and we emit zero" and needs a
truth file to do it. This needs none, because the record already holds which
decision was asked and what it answered:

    emitted       we wrote them
    abstained     the decision ran and declined — the system working
    stub          declared `stub=True` — scheduled work
    starved       ...and its input is never gathered — TWO pieces of work
    NO_QUANTITY   nobody has decided the family exists

Collapsing those into one "missing" number is how *"5 of 6 stubs are starved"*
stayed invisible. They are not interchangeable: `abstained` needs nothing,
`starved` needs a gather site **and** an adjudicator.

## 3. ⚠️ THE ACCOUNTING CONTROL IS READ, AND IT RAISES

Every notehead in the log is either written or counted as not-written, and the
two must sum to the `notehead_class` rows exactly. All four pages balance
(711 = 516 + 195, 1015 = 664 + 351, …).

`to_musicxml` **raises `Unbalanced`** rather than returning a flag, because
the flag has been tried: `symbol_ledger.coverage_check` computed exactly this
control, wrote `balanced=False` on 9 of 20 rows, and was read by nothing for
as long as it existed. A control nobody consults is not a control.
`test_staged_export.py` mutates `_place_notes` to swallow notes silently and
asserts the raise.

**What the balance reveals: 595 notes across four pages are HELD IN THE RECORD
AND ABSENT FROM THE FILE**, and the split is the actionable part —
`duration_narrowed` 441, `no_pitch` 142, `written_value_fits_no_note` 12.

⚠️ **`duration_narrowed` is the exporter refusing to decide, on purpose.** A
narrowed duration carries its candidates and each candidate's `support`, so an
argmax is one line away — and it would overturn, in the exporter and silently,
a call `adjudicate_duration` explicitly declined to make. That is *an argmax
with no floor*, the thing `Mode.COMPETITIVE`'s mandatory `margin_floor`
forbids one stage earlier. A `<note>` needs one duration, so the note is
dropped **and counted**.

## 4. The positions carried over from `tools/omr/export.py`

Nine "detected then dropped" bugs were paid for there. This is not a port —
it reuses the pure renderers (`_mxl_note`, `_mxl_attributes_block`,
`_mxl_measure_rest`, `_score_partwise`, `voicing.group_chords_in_measure`),
because those ARE the positions in executable form — and it restates every
rule that has to be re-derived on a different input. Each has a test:

| position | how it survives here |
|---|---|
| `divisions` is an **LCM, not a max** | computed over staged `duration` verdicts; a triplet's third makes it 48 on Beethoven p3, and plain music still gets 4 |
| `measure="yes"` **only where the meter is known** | 86 of 148 Beethoven p3 bars have no meter and are written without it |
| a dot is **one fact, not two** | `max(verdict dots, type prefix)` — summing wrote a double dot for every single one, 82 edits |
| the meter's `symbol` comes from **the glyph, never the numbers** | ⚠️ restated, not copied: the staged `raw` is `Q.METER_TEMPLATE`'s **matched letter**, unlike the legacy `raw` which `_propagated_meter` synthesises. `LETTER_METERS` is imported so the two cannot drift |
| a chord is written **lowest note first** | `group_chords_in_measure` already sorts it; MusicXML takes the first `<note>` as the chord's representative |
| a tuplet **scales the time and leaves `<type>` alone** | and only the ratio's own `members` are scaled — scaling the cell would shorten every untupleted note in it by a third |
| a staff whose clef abstained gets **no pitches, not treble** | 142 notes dropped `no_pitch` rather than defaulted |
| **a part is the same staff on every system** | consumed from the `part_partition` verdict, not re-derived |

## 5. ⚠️ THE PART JOIN IS THE VERDICT'S, INCLUDING WHERE THE VERDICT IS KNOWN TO BE WRONG

Brahms 1 p.2 prints 13 and 14 staves in its two systems, so the ordinal join
refuses; `adjudicate_part_partition` returns `join: "slot"` and the exporter
**honours it — 14 continuous parts instead of 27 fragments**, the same
structural result `OMR_SLOT_STITCH` produces on the legacy path, here from a
recorded decision rather than a flag.

That decision's own docstring records it measured **wrong on 3 of 27 staves on
this exact page** (it fails to continue *4 Hörner in Es* across a tacet break).
That is not a licence for the exporter to second-guess it — an exporter that
quietly disagrees with a decision is how a measured judgement goes missing.
What the exporter does instead is put `join_decided` / `join_used` in the
coverage record, so a reader of the FILE can find out without reading the
code. Where the slots were excluded as circular the verdict says
`deduced_anchor` and the exporter takes the fragment path, which is the legacy
behaviour and is still right: the alternative is grafting.

## 6. Not built, and why

* **LilyPond.** The MusicXML path is the one every consumer here uses and the
  one `export_coverage` compares. A LilyPond exporter would duplicate the
  model and add its own known-narrower rules (a slur cannot span two `\new
  Staff` contexts; `\<` … `\!` cannot be written under one note), none of
  which the staged record can exercise today because arcs and wedges are
  starved. Building it now would be writing rules for facts that do not exist.
* **Rests, arcs, articulations, dynamics, directions.** Not the exporter's to
  fix: §1. The order the record forces is GATHER first, then the adjudicator.
