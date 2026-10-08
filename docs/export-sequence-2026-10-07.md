# The EXPORT sequence — what runs, in what order, and which orderings are real

**Date:** 2026-10-07. **Path:** STAGED (`tools/omr/staged/export.py`,
`lilypond.py`, `movements.py`, `__main__.py`). **Authority:**
`export.to_musicxml`, `export.build`, `export._part_xml`,
`lilypond.to_lilypond`, `movements.export_each`. This document is a reading
of the tree on that date; where it and the tree disagree, the tree is right
(CLAUDE.md rule 10).

Last of the per-stage sequence documents: GATHER
`docs/gather-sequence-2026-10-06.md`, ADJUDICATE
`docs/adjudicate-sequence-2026-10-07.md`, EVALUATE
`docs/evaluate-sequence-2026-10-07.md`, INFER
`docs/infer-sequence-2026-10-07.md`.

---

## 1. What happens around the stage (`__main__`)

1. The record is written (`--out`) **before** any export — so a crash in
   the exporter never loses the gather. The CLI imports the exporter after
   the gather for the same reason (CLAUDE.md §5b).
2. If `--movements` was given, the record is split per movement
   (`movements.split_result`): DOCUMENT-scope rows travel into every
   movement's file; every finer row goes to the one movement whose span
   holds its `(page, system)`; a row in no span is dropped from every file
   (rule 8 — never assigned to the nearest neighbour). Each movement is
   then exported as below to `<base>-mvtN.<ext>`.
3. `--musicxml` → `to_musicxml` → the file and its `.coverage.json`.
4. `--lilypond` → `to_lilypond` → the `.ly` and its `.coverage.json`.
5. `--pdf` → compiles the `.ly` with the `lilypond` binary, reusing the
   text `--lilypond` wrote when both were given, else writing one beside
   the PDF. `lilypond` absent: reported, the `.ly` kept, exit 0.
6. The console reports and the accounting summary.

`--through` anything but `infer` refuses all three outputs: the tests are
GATHER+ADJUDICATE only until further notice (§6b).

---

## 2. `to_musicxml`, in order

### 2a. `build(rec)` — record → runs → placed marks → parts

1. **Runs.** One `StaffRun` per `Q.MEASURE_PARTITION` verdict (page,
   system, staff; bar count DECIDED or 0). Each run reads its clef, key,
   meter (SYSTEM scope), part name — verdicts — and its staff spacing, line
   positions and cell boxes — observations, deliberately via `obs`, since
   no decision adjudicates them.
2. **Hold-out set.** Before any note is placed, and once: on a `slot` join,
   every run with no DECIDED `Q.SLOT_INDEX` is held out
   (`held_out_staves`). Computed here so the join below *consumes* it
   rather than re-deriving it.
3. **Notes** (`_place_notes`): every decided note, once per piece of ink.
   A note is written to its cell or refused under one named reason. The
   names, read off the `_drop` call sites (several are composed, so a
   grep for literals undercounts them): `staff_not_identified`;
   `not_a_notehead:<reason>` and `not_a_rest:<reason>` (the ADJUDICATE
   refusal's own reason word carried through, so "barline sliver" does
   not read as a generic shortfall); `owned_by_another_staff` (the loser
   of a contest is dropped, never moved) or
   `not_a_notehead:belongs_to_a_nearer_staff` — or, under
   `OMR_RELOCATE_AT_EXPORT`, a relocation whose refusals are
   `relocation_collides` and `owner_staff_has_no_measures`;
   `owner_not_read`; `duration_narrowed` / `duration_abstained` /
   `duration_absent` (and `rest_duration_*` — EXPORT refuses to argmax a
   narrowing); `no_pitch`; `ink_is_a_whole_rest`; `mark_group_duplicate`;
   `cell_past_the_last_bar`; `written_value_fits_no_note`. One `_drop`
   call site per reason, counting by reason and by system at once.
4. **Equality 1.** Per-system refusals sum to per-reason refusals, or
   `Unbalanced`.
5. **Marks onto placed notes**, each family into its own bucket:
   directions, arcs, articulations, dot roles (2.12c), fermatas, ornaments.
   After the notes, because a mark hangs on a notehead that has reached a
   cell.
6. **The join** — consumes `Q.PART_PARTITION`: `ordinal` when every system
   has the same staff count; `slot` when the slots survived; else
   `fragments` (one part per system-staff, every one unidentified). On the
   slot join a condensed Cello/Contrabass staff is doubled onto both slots
   (`_condensed_double`, 2.1b). Parts the join could not name are recorded
   in `provenance["unidentified_parts"]`.

### 2b. Part-level passes — after the join, before any bar is rendered

7. `_divisions(parts)`.
8. **Arc pairing** (`_pair_arcs`): a part pass, because an arc is merged
   along a *part* across system junctions. Must follow the join and
   precede the render, where the marks are read.
9. **Wedges** (`_place_wedges`): a part pass too — overlapping hairpins
   need `number=` levels no per-measure pass can see.
10. **Document bar numbering** (`_document_bar_offsets`): a fact about the
    document's systems, written onto parts — only the join says which runs
    are one part. Then the printed-bar-number check (2.13; a report, never
    fed back). Then `spans` (each system's bar count, for tacet padding)
    and `meters` (per system, off the runs — one read of `Q.METER`).

### 2c. The render (`_part_xml`), per part, per bar

11. Tacet walk: a system this part is absent from is padded with
    full-measure rests **only if** its meter is known; without one the bars
    are counted (`tacet_bars_not_padded_without_meter`), never sized by a
    default. A part the join could not identify is never padded
    (`tacet_spans_declined_unidentified_part`).
12. Per bar: the meter at this bar (a change holds until a printed return;
    a carried meter is `in_force`); `<attributes>` when clef/key/time
    change; the cell's events; the voice split, computed once; the
    **bar-sum hold-out** (`_bar_holds_out`: per voice, every voice must
    fill, a chord is one event, a lone measure rest IS the bar, no meter no
    verdict, never by position — a pickup is held with the rest and
    named); then, only if not held, the **unread-mark** question
    (`Q.UNREAD_MARK`, recorded for every bar it fires on, holding out only
    if `UNREAD_MARK_HOLDS_OUT`, today False); an eventless bar → a marked
    measure rest with `measure="yes"` withheld (we read nothing, not
    silence); the meter-return marker (2.12k). A held bar's notes are
    refused at render through the same `_drop` discipline
    (`_drop_at_render`) and its marks reach each family's own bucket
    (`_held_bar_marks`).
13. `_score_partwise` assembles the file.

### 2d. The report and the equalities — after the render

14. `coverage()`: every notation family, four different zeros apart
    (abstained / stub / starved / no quantity).
15. **Equality 2** (re-asserted after the render, because the render adds
    refusals): per-system = per-reason, or `Unbalanced`.
16. `bars_held_out_sum` with every held bar **named** (page, system,
    staff, cell, measure number, part); `possibly_unread_mark` (the whole
    population) and `bars_held_out_unread_mark` (the actually-held subset).
17. **Equality 3**: unread-bar marks written = unread + held-by-sum +
    held-by-unread-mark, or `Unbalanced`.
18. Per-family partitions: arcs (with `bar_does_not_add_up` subtracted
    before the residue is named), articulations (`==`), dot roles (`==`),
    ornaments (`==`), wedges (`==` of written + not-written against
    *decided*, not rows — abstentions are decisions, not drops; it was a
    `<=` for one afternoon and hid ten hairpins), direction words (`==`
    with two named residues), fermatas (a partition, `<=`, because a
    hoist legitimately collapses two marks into one element).
19. **The accounting control**: noteheads + rests in the log = written −
    duplicated-across-voices − doubled-to-condensed + not-written, or
    `Unbalanced`. `to_musicxml` raises; it never returns a flag nobody
    reads.

---

## 3. `to_lilypond`, in order — and where it diverges

Same `Record`, same `build`, same `_pair_arcs` / `_place_wedges` /
`_document_bar_offsets` / `_divisions`, same per-bar readers (`_events`,
`_voice_split`, `_bar_holds_out`, `_meter_return_marker`, the
unread-bar-mark table). Then its own `_staff_block` per part and a
`\score` wrapper. Its report asserts two equalities: unread-bar marks
written = unread + held-by-sum, and meter-return marks written = found.

**Where it diverges.** A bar `_bar_holds_out` holds out is counted in
`counters["bars_held_out_sum"]` and `notes_held_out_sum`, as in MusicXML —
but the notes it refuses are **not added to `dropped`** (there is no
`drops` callback into `_collect_bars`) and `to_lilypond` **asserts no
notes balance**. So for one record, `notes_not_written_total` in the
`.ly.coverage.json` is the build-time figure only, smaller than the
`.musicxml.coverage.json` figure by exactly the held-out notes, and no
equality catches it. See §5.

---

## 4. Does order matter?

Yes, and almost all of it is forced by data flow rather than convention:

- Runs before anything (every placement needs a cell to land in).
- The hold-out set before note placement (`_place_notes` refuses
  `staff_not_identified` from it) and before the join (which consumes it).
- Notes before marks (a mark hangs on a placed note).
- The join before arcs, wedges and numbering (all three are facts about a
  *part*).
- Arcs and wedges before the render (the render reads the marks they
  attached).
- Numbering before the render (a measure is named by its document
  offset; the tacet spans come off the same tally).
- Render before the equalities that include render-time refusals —
  equality 2 is asserted twice for exactly this reason.

What is *not* forced: the order of the six mark families in `build` step
5 (each reads notes, none reads another family), and the order of the
per-family partitions in the report. Nothing reads the report's own
earlier keys except `arcs_not_written`, which subtracts `held_marks`
computed during the render.

**How a misorder would fail.** Loudly, in most cases: the three
`Unbalanced` equalities and the per-family `balanced` fields are built to
go False when a refusal reaches one counter and not another, and the
`<=`-for-an-afternoon story in the wedge control is the recorded reason
they are equalities. The exception is the LilyPond path (§3), where the
missing accounting is not a misorder but an absent control.

---

## 5. Examination

**Should anything move?** No. Every forced edge in §4 is honoured and
every one is stated at its call site in `to_musicxml`. The MusicXML
exporter is the best-guarded stage in the pipeline: three raising
equalities and seven per-family controls, each with a named residue.

**Finding: the LilyPond exporter has no notes balance.** `to_lilypond`
reuses every reader `to_musicxml` does and asserts two of its four
equalities (unread-bar marks, meter returns) but not the accounting
control, and its render-time hold-outs never reach `dropped`. The PDF is
the artefact a musician opens; its sidecar saying fewer notes were
withheld than the MusicXML sidecar for the same record is the "detected
then dropped on the way out" shape (`feedback_find_export_gaps`) in the
report rather than the file. The bars themselves ARE marked in the PDF
(the unread-bar-mark equality covers that); what is wrong is the count
beside them.

*Built the same day (ROADMAP 2.64, Sean: "Yes"):* `_collect_bars` and
`_staff_block` take the same `drops=` callback `_part_xml` takes, so a
held bar's notes are refused through `_drop` by reason and by system;
`to_lilypond` then asserts the same two note equalities `to_musicxml`
asserts, over the same counters and the same formula, and reports
`balance`. The `.ly` text is unchanged. The control is
`TestTheNotesBalanceIsAssertedHereToo`, run RED first: one record
exported both ways, the two sidecars' `notes_not_written_total` agree (3,
where the `.ly` side read 0 before); a bar that adds up balances at zero;
a forced miscount raises `Unbalanced`.

**Known, not new.** `OMR_RELOCATE_AT_EXPORT` (2.58, default OFF) and
`OMR_MARK_GROUPS` (2.58b) change what `_place_notes` refuses; the balance
is unchanged by construction and says so (`relocated_heads_written` is
informational). `UNREAD_MARK_HOLDS_OUT` is False: the unread-mark
decision is recorded on every bar it fires on and holds out none. The
slot join is known wrong on 3 of 27 staves on the one page it was
measured on, and the exporter honours it rather than second-guessing —
the provenance block says which join was used.

---

## 6. What changed (this document only)

`ASSUMPTIONS.md` gains A-EXPORT-1: the forced order inside
`to_musicxml` and the equalities that guard it. ROADMAP 2.64 (§5) is the
one code change: the LilyPond exporter now asserts the notes balance.
