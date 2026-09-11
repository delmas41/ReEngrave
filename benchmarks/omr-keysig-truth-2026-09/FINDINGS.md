# The key signature, against a hand-read print truth

**Litolff Beethoven 5 mvt 1, pdf pages 1-4 — the four pages of the first
cleanup count. 75 printed staves, 7 systems, 12 instruments.**

Sean stopped the first cleanup pass and named key signatures as one of seven
complaints. This measures them against the print rather than against a metric,
because for once the right answer is available for the whole page.

---

## 1. THE ANSWER FIRST: this is NOT a clef problem

The brief asked directly whether the key signatures are *"a clef result wearing
a key-signature costume"*, because the module's own documentation says the
reader inherits the clef problem — a wrong clef chooses a wrong slot table and
yields wrong signatures rather than abstentions, and *"bass staves defaulted to
treble read 3 flats as 2 sharps"*, which is exactly the shape of the `-2` and
the `1` in the shipped file.

**It is not.** Over the same 75 staves the clef reads **68 correct, 6
abstained, 1 wrong** — and, decisively:

> **All ten wrong key readings sit on a staff whose clef was read CORRECTLY.**

The single wrong clef (p2/s1 Fagotti, read `tenor` against a printed bass
header — the staff changes to tenor at bar 37 and the run took the change)
produces an **abstention**, not a wrong key. That is the designed behaviour
working: `adjudicate_key_signature` matches the fit against the settled clef
and abstains `run_fits_no_slot_table` when they disagree.

So the clef guard is doing its job, and the key signatures are the key
reader's own.

---

## 2. The truth, and where it comes from

`truth.json`, committed, hand-read off the print at 600 dpi staff by staff.
Sean, reading the same pages independently:

> *"the key signatures are inconsistent - they should all be 3 flats (Cm/Eb
> maj) except Cl. which is 1 flat and the tr and cor which have no key
> signature."*

The two agree on every staff he names. ⚠️ **He did not mention the timpani**;
the print gives it none either (Timpani in C.G., bass clef, empty header), so
the hand reading **adds** one instrument to his statement rather than
contradicting it. The truth is a function of the INSTRUMENT — a B-flat
clarinet writes a tone up, so 1 flat; horns in E-flat, trumpets and timpani in
C are written with no signature at all — which is why it could be stated
before any output was looked at.

⚠️ **The instrument join is HAND-SUPPLIED and could not have come from the
record.** CLAUDE.md already records that `instrument` abstains `no_evidence` on
22 of 22 staves of this artefact and all twelve parts are named
`Staff p1-s0-N`. The lineups in `truth.json` are read off each system's own
margin labels, and they are **not all the same**: three different 11-staff
lineups occur on these four pages, and one system prints 8. **A staff's ordinal
within its system does not name its instrument**, which matters in §6.

---

## 3. The grade, before

`grade_artefact.py`, run against the committed `system-map-p1-p4.json`, which
the cleanup-count README states is *"derived by calling export.build; asserted
against the emitted XML measure-for-measure"* — so grading it grades the file,
and the 132 MB record is not needed.

⚠️ **Two grades, because two questions have different answers.**

| | correct | wrong | abstained |
|---|--:|--:|--:|
| **READING** — what `adjudicate_key_signature` did | **16** | **10** | **49** |

| | right | WRONG |
|---|--:|--:|
| **FILE** — what a human cleaning up sees | **33** | **42** |

⚠️ **The file cannot say "I could not tell".** A staff whose key abstained is
exported with no `<key>` element, and a missing key is no accidentals to any
reader. So an abstention comes out **right in the file** on the 18
staff-systems that genuinely print none (horns, trumpets, timpani) and
**wrong** on the other 57. 17 of the 33 "right" rows are abstentions that
happen to land on a zero-signature instrument. **A count of parts reading `-3`
is not the score**, and neither is a count of abstentions.

**Dominant defect: ABSENCE.** 49 of 75 staves — 65% — produce no reading at
all. That is nearly five times the wrong-value count.

---

## 4. The three defect shapes the brief named, attributed

### Shape 1 — wrong VALUES (`-2`, `1`, `7`): the key reader, three mechanisms

Opened with `probe_readers.py`, which re-runs the readers on the same header
crops and records `n_accidentals`, `accidental`, `decided_by` and the number of
INFERRED slots per staff. Its control: it reproduces the shipped artefact's
verdicts on **71 of 75** staves (it cannot pass `occupied_boxes`, which GATHER
takes from the detector's boxes — that is the honest bound on everything here).

| mechanism | n | evidence |
|---|--:|---|
| **truncated run** — fewer flats found than printed | 6 | `n_accidentals` 1 or 2 with `accidental: b` where the print has 3; e.g. Fagotti reads `-1` on four separate systems |
| **one accidental, mis-shaped** | 3 | `n_accidentals: 1`, `decided_by: shape`, `accidental: #`. With a single accidental "position says nothing, so the ink does", and the shape test went the wrong way. One of the three (Trombe p4/s0) is on a header that prints **nothing** — a spurious run of one |
| **inference compounding** | 1 | the `7`. `n_accidentals: 4`, `inferred_slots: 3` — four matches fitted as seven sharps |

⚠️ **The `7` is the failure CLAUDE.md already records, and the guard the brief
asked me to check is present and working as designed.** The refusal to infer
lives in `key_signature_template`, whose comment names this exact case (*"five
matches on one staff were fitted as SEVEN sharps"*). `key_signature_locator`
deliberately **does** allow inference, and says why: it loses accidentals to
broken ink and cannot invent them. `max_inferred_ratio = 1.0` permits 4
observed to become 7 slots. **I did not touch it.** It is one staff of 75, the
constant sits on a documented rationale, and lowering it to catch this page
would be tuning a threshold on one edition against the reader's own stated
failure direction.

⚠️ **6 of the 10 are UNDER-counts of a 3-flat signature, and 10 of the 15 wrong
readings after the repair still are.** That is the single largest residue and
it is a recall problem, not a classification one.

### Shape 2 — parts that change key mid-part: TWO causes, and the larger is not the key

P1, P4, P9, P10 and P11 each change `<fifths>` mid-part on a movement that
changes key nowhere. Separating staff from part shows it is two different
faults added together:

* **the reader disagreeing with itself across systems.** The Fagotti is read
  `-3` once and `-1` four times; Violino II `-3`, `1`, `1`. Real, and shape 1's
  mechanisms are the cause.
* **the staff→part JOIN putting a correct reading in the wrong part.**
  **12 of the 75 staff-systems are joined to an instrument they are not**, all
  of them on the two systems whose printed lineup is not the canonical one:
  p3/s1 (8 staves — Oboi, Trombe and Timpani tacet) and p4/s0 (11 staves, but
  Timpani tacet and Violoncello and Basso printed APART). Both are stitched by
  ORDINAL, so on p3/s1 the printed Clarinet lands in the Oboe's part, the
  Fagotti in the Clarinet's, and the Viola in the **Timpani's**.

⚠️ **So `P7`, the part carrying seven sharps, is the Timpani's part and the
seven sharps were read on the VIOLA.** A reader inspecting the file part by
part cannot see that, and would file it against the timpani.

⚠️⚠️ **THIS IS NOT A KEY-SIGNATURE DEFECT AND MUST NOT BE COUNTED AS ONE.** It
is the defect CLAUDE.md already records from the cleanup count — *"the parts of
the file disagree about which bar they are in"* — measured from a second
direction, and it belongs to `_stitch_slots`. What is new here is that its
cause is nameable: **the two non-canonical systems have 8 and 11 staves and the
join trusts the COUNT**, so p4/s0's eleven staves are silently matched to the
eleven-staff lineup they are not.

### Shape 3 — correct-looking `-1` and absent signatures on the wrong staff

Answered by grading per staff against the instrument. The `-1`s split: the
Clarinet's four are **correct** (it is the one instrument that prints one
flat), and five more `-1`s on Fagotti/Viola/Violoncello are truncated 3-flat
runs. Of the 49 abstentions, **17 land on an instrument that prints no
signature and are right in the file by accident**; the other 32 are wrong.

---

## 5. A fourth mechanism the brief did not name, and it is the biggest single one

⚠️⚠️ **ELEVEN OF THE 75 STAVES HAD NO CLEF AND NO KEY SIGNATURE IN THEIR HEADER
CROP AT ALL.**

`probe_windows.py` measures every header window. On six of the seven systems
every window is **16.00 staff spaces** wide. On **page 2 system 1 all eleven
are 6.1-6.2 spaces** — and a clef alone is about 4 spaces, a 3-flat signature
about 8. Dumping the crops (`dump_headers.py`) shows what is in them: the
margin label and the systemic rule, and no music.

**The cause, measured (`probe_left_edge.py`).** The window's right edge is the
system's first barline at least `min_width_spaces` right of `x0`, and its own
comment says the margin exists to keep out *"the system's own initial rule"*.
But `x0` derives from `system_left_edge`, which is the **MINIMUM** of one
estimate per staff. On p2/s1 the eleven estimates are

    331, 345, 345, 263, 334, 334, 335, 347, 336, 336, 346

— ten agree within 16 px and **the fourth under-runs them by about 70 px**.
The minimum prefers it, `x0` lands at 255, the system's opening rule at 353
then clears the 47-px margin, and the window ends **on the rule**.

⚠️ **`system_left_edge`'s docstring asserts the invariant that makes the
minimum safe — *"the estimate can only ever be too far right and never too far
left ... nothing can under-run past the bracket into the instrument names"* —
and it is FALSE.** Corrected in place.

⚠️⚠️ **AND IT MADE BOTH READERS FAIL IN DIFFERENT-LOOKING WAYS WITH ONE CAUSE.**
`key_signature_locator` found no accidental run and abstained.
`key_signature_template` found a **clean window** and answered a confident
`fifths: 0` — *"a positive reading of 'no signature here'"*, its docstring's
own words — which is **a key signature fabricated out of a crop containing
none**. On a system printing three flats on eight staves that is eight
confident wrong answers. **The reader that can say "zero" is the one that must
never be given an empty window**, and nothing connected those two facts until
the crops were looked at.

---

## 6. What was repaired, what was refused, and why

### Repaired 1 — the header window's margin is anchored on the CONSENSUS

`staff_header.measure_header_window`. **The test is unchanged and the constant
is unchanged**; only what the margin is measured FROM moved, from the minimum
of the per-staff estimates to their **median** (`system_left_consensus`). The
minimum is the right statistic for where a window BEGINS — generous on purpose,
since starting early costs nothing and starting late loses the clef — and the
wrong one for asking how far right a barline must stand before it stops being
the opening rule.

Measured on the four pages: windows with a `barline` right edge **12 → 1**, the
eleven broken windows go 6.2 → 16.0 spaces, and **no other window moves**.

⚠️ **The median and not the mean**, because the estimates carry a documented
heavy tail on one side only — a staff whose anchor landed inside the music
walks left only to the first barline it meets and reports hundreds of pixels
too large (788, 983 and 1058 all occur on these pages). A mean follows those.

### Repaired 2 — the template reader is wired in as a SECOND witness, gaps only

`ASSUMPTIONS.md` **D20** already records that GATHER reads key signatures with
`key_signature_locator` alone, *"the weaker of the two readers this repo has,
by a margin measured on the very page the first shadow run used"*, and
prescribes the repair, the precedence and the hazard. This is that repair.

Measured here over 75 staves: the locator decides **16** correctly, the
template **28** — and they are **complementary, not ranked**. On page 1 the
template reads **12 of 12 right** and the locator 2; on page 2 system 0 the
locator reads 5 right and the template 4 different ones.

⚠️ **The precedence is INHERITED, not chosen.** The template answers GAPS ONLY,
which is the legacy path's own rule (*"the reader speaks only into GAPS"*).
Letting the fuller reading win is already priced and already refused there
(*"+1 on beet5-p2 and +2 on the Pastoral and a WRONG reading on the cleanest
page in the corpus"*) on documents this run does not have. Re-deciding it from
four pages of one edition would be exactly the corpus-of-one tuning this repo
forbids.

⚠️ **It is filed under a NEW quantity, `Q.KEYSIG_TEMPLATE_FIT`, and that is
load-bearing rather than tidy.** `adjudicate_clef` reads `Q.KEYSIG_CLEF_FIT`
and raises one `Term` per row, so filing a second reader's fits there would
silently double the weight of that evidence in the CLEF contest — a reading
change leaking into a decision it was never measured against. Asserted by a
test that runs the clef contest with and without template rows and requires the
verdict to be identical, with a positive control that the contest was decidable
at all.

⚠️ **The two repairs had to land together and in this order.** Wiring the
template in over the broken windows would have imported the eight fabricated
`0`s as real readings.

### Refused

* **Clamping `x0` itself** (arm B in `probe_window_repair.py`). It gains 5
  template readings and costs the locator 3 correct and 6 new wrong — 13
  correct against 16 — and it moves 19 windows instead of 11. Refused on
  measurement, not on taste.
* **`max_inferred_ratio`**, the constant behind the seven sharps. One staff of
  75; the constant has a documented rationale pointing the other way; tuning it
  here would be fitting one edition.
* **Any threshold in the locator or the template.** Nothing was tuned. The one
  change to a decision rule (the window anchor) replaces a statistic, not a
  number.
* **A cross-system vote over the key** — see §7.

---

## 7. The grade, after — and it is still not good

One page load, all arms read from the same `PageWithStaves`, so no segmentation
jitter enters the comparison.

| | correct | wrong | abstained |
|---|--:|--:|--:|
| READING, shipped (locator alone) | 16 | 10 | 49 |
| READING, repaired (locator else template) | **35** | **15** | **25** |

| | right | WRONG |
|---|--:|--:|
| FILE, shipped | 33 | 42 |
| FILE, repaired | **44** | **31** |

**12 staff-systems become right in the file and 1 becomes wrong** — the Corni
on p4/s1, where an abstention that was accidentally right became a template
`-1`. That is the one genuinely new harm and it is named rather than netted
away.

⚠️ **44 of 75 is not a good page.** Sean's judgement stands: the reading is
still wrong or missing on 31 of 75 staves. What has changed is that the
residue is now attributable.

⚠️ **The largest remaining lever is a CROSS-SYSTEM vote, and it is BLOCKED —
deliberately not built.** A staff's key is the same on every system of a
movement, and pooling all readings per instrument across these four pages would
recover 11-12 of the 12 instruments. `key_signature_vote.reconcile` already
implements exactly this for the legacy path — it took WTC I p.17 from 6/10 to
10/10 — and **the staged path consumes none of it.**

It must not be wired in yet, for a reason this file measured in §4:
**the staff→part join is wrong on 12 of 75 staff-systems.** A cross-system vote
keyed on that join would carry the Viola's seven sharps onto the Timpani's
part — which is precisely the recorded hazard behind `StaffCandidate.can_carry`
(*"one staff's spurious fifth sharp was carried onto every treble staff of five
systems, taking a page from 10 correct to 5 correct and 5 wrong"*). **The key
signature's next gain is downstream of the part join, not of any key reader.**

⚠️ The WITHIN-system value group stays refused, and `ASSUMPTIONS.md` is right
about why: transposing parts genuinely print different signatures at the same
bar, and this page is the proof — `-3`, `-1` and `0` all stand in one system.

---

## 8. What is NOT established

* **n = 1 document, 1 publisher, 4 pages, 75 staves.** Litolff `984073` is the
  *low-res bitonal* scan this repo already records as the pessimistic end of
  its corpus. A second publisher could change the ranking of the mechanisms in
  §4, not just the numbers.
* **No OMR-NED figure is claimed.** musicdiff does score `<key>`, but the
  eleven-work engraved benchmark and the 20-row scan gate were not run: the
  window change touches every page's header geometry and pricing it properly
  needs both gates, which is a separate job.
* **The probe is not the pipeline.** It cannot supply `occupied_boxes` and
  reproduces the shipped verdicts on 71 of 75 staves. Every number above
  carries that bound.
* **The 6 abstained clefs are not investigated.** They cost 6 key signatures by
  construction (`needs_clef`) and are someone else's measurement.
* **Two `wants` entries on `adjudicate_key_signature` are INERT** and were
  found by `inventory --check`, not by me: it declares `Q.KEYSIG_MARKER` (the
  detector's own `keySharp`/`keyFlat` boxes, gathered and never read) and
  `Q.DOSSIER_FACT`. The detector's markers are a **third** reader, already on
  the record, consumed by nothing. Not built here — it is a third precedence
  question and D20's prescription covers two readers, not three.
* **`checked_by` names a check that does not run.** The decision declares
  *"across the staves of a system the DELTA is shared"* and *"a key CHANGE is
  printed on every staff at the same bar (key_signature_corroboration --
  CONSUMED, default-ON)"*. Neither is reachable from the staged path:
  `key_signature_corroboration` is imported only by `transcribe.py`.

---

## 9. Reproducing

```bash
python3 benchmarks/omr-keysig-truth-2026-09/grade_artefact.py --check   # before, vs the shipped file
python3 benchmarks/omr-keysig-truth-2026-09/probe_windows.py            # the header windows
python3 benchmarks/omr-keysig-truth-2026-09/probe_left_edge.py          # the falsified invariant
python3 benchmarks/omr-keysig-truth-2026-09/dump_headers.py --page 2    # look at the crops
python3 benchmarks/omr-keysig-truth-2026-09/probe_readers.py            # both readers, per staff
python3 benchmarks/omr-keysig-truth-2026-09/probe_window_repair.py      # the three window arms
python3 benchmarks/omr-keysig-truth-2026-09/combine.py                  # the gaps-only precedence
python3 benchmarks/omr-keysig-truth-2026-09/file_grade.py               # what a human sees
```

Everything but `dump_headers.py` runs in well under a minute and needs no
detector, no Surya and no record — the header is read from geometry alone.

---

## 10. The downstream edge, named and NOT measured

`consequences.respell_accidental` takes `Q.KEY_SIGNATURE` as its CAUSE and
`Q.ACCIDENTAL` as its effect: *"the key settles, so the notes on this staff
carry its alterations."* So a staff that goes from abstaining to reading `-3`
does not only gain a `<key>` element — every pitch on it is re-spelled.

⚠️ **No claim is made about that here.** 12 more staff-systems now settle a key
on these four pages, and what it does to the pitches was not measured: it needs
a full re-gather and a note-level comparison, and the right instrument for it is
the cleanup count itself rather than anything in this directory. It is recorded
because a reader pricing this change by counting `<key>` elements would be
counting the smaller half.

⚠️ The direction is not obviously good either. The rule re-spells from whatever
key settles, so the **one new wrong reading** (a Corni `-1` where the print has
none) now re-spells that staff's notes as well — one staff-system of 75, and
the reason the new harm is named in §7 rather than netted against the 12 gains.

---

## 11. What the second reader COSTS

Measured on page 1 (12 staves, 4 candidate clefs each, 48 calls per reader):

| reader | calls | wall | per call |
|---|--:|--:|--:|
| `key_signature_locator` (already there) | 48 | 2.23 s | 47 ms |
| `key_signature_template` (added) | 48 | 2.06 s | 43 ms |

So GATHER's key-signature stage roughly **doubles**, at about **2 seconds per
12-staff page**. Against a four-page gather that is Surya-bound and takes tens
of minutes, it is not a consideration — but it is measured rather than waved
at, because "ask a second reader" is the kind of change that is cheap here and
would not be on a whole 88-page work (about 3 minutes added, still small
beside that run's direction-text half, which this repo already prices at 75%
of wall clock).

⚠️ **Both readers are asked once per CANDIDATE clef rather than once with the
settled one**, which is what makes it four calls and not one. That is GATHER's
existing design and not something this change introduced: the slot table is
chosen by the clef, so asking with a guess is guessing twice, and *which*
clefs the run fits is itself evidence about the clef.

---

## 12. The end-to-end confirmation: PARTIAL, and what it does and does not show

⚠️ **The controlled measurement in §7 is the probe, not a re-gather, and that
is deliberate rather than a shortfall.** Both repairs are GATHER changes — a
new quantity and a change to header geometry — so `readjudicate.py` is
STRUCTURALLY BLIND to them (it rebuilds from a saved record, and a new
quantity never enters) and `reexport_arm.py` has the mirror blind spot. Only
two full re-gathers can answer *"did GATHER change what ADJUDICATE sees"*, and
a re-gather carries detector jitter, which this repo has measured at
confidence swings of 0.83 → 0.69 on byte-identical code. The probe runs three
arms off ONE page load and has none of that.

**What was nonetheless attempted, and what it established.** A full staged run
over the same four pages on the landed tree:

⚠️ **RUN 1 STARVED, exactly as this repo's own escape clause says it would.**
`OMR_SURYA_KEEP_ALIVE=0` does NOT buy a private worker when a resident server
already exists — Surya attaches through its own sentinel — and a four-day-old
shared `llama-server` was serving a sibling session. The main process sat at
**0.0% CPU** for ~25 minutes after page 2's last cell, which is the "frozen
clock" picture that reads as a hang. It was killed **by its own PID** and the
shared server was left alone.

**RUN 2 ran Surya-free** (`OMR_DIRECTION_TEXT=0` and the `.venv-surya` symlink
moved aside), which is sound here because **no key-signature reader touches
Surya** — the header is read from geometry — and `instrument` already abstains
on 22 of 22 staves with Surya present. It stayed at 98-100% CPU throughout,
completed GATHER on all four pages, and reached ADJUDICATE:

    adjudicate clef:          472 verdicts so far
    adjudicate key_signature: 547 verdicts so far

The counter is CUMULATIVE, so **`adjudicate_key_signature` produced exactly
75 verdicts — one per printed staff, and the same 75 as the hand-read truth.**
`staff_group`, `measure_partition`, `staff_ordinal`, `instrument`, `slot_index`
and `clef` each produce 75 too, and `system_membership` 7, matching the seven
printed systems.

⚠️⚠️ **SO WHAT IS CONFIRMED IS THE WIRING, NOT THE FILE.** The repaired GATHER
runs to completion on a real four-page record, the new
`Q.KEYSIG_TEMPLATE_FIT` rows do not break it, and the key decision reaches
every printed staff. **The exported MusicXML was NOT produced**: the run was
stopped after `adjudicate_glyph_owner` had spent ~40 minutes at 100% CPU, a
decision this change does not touch and which a parallel session is actively
reworking. So there is no regenerated `<fifths>` table here, and §7's numbers
rest on the probe and its 71-of-75 reproduction of the shipped artefact.

**To finish it:** re-run `run_gather.sh`'s command against
`out/record-after.json`, then

```bash
python3 benchmarks/omr-cleanup-count-2026-09/export_arm.py \
        --record benchmarks/omr-keysig-truth-2026-09/out/record-after.json \
        --tag after --out-dir benchmarks/omr-keysig-truth-2026-09/out
python3 benchmarks/omr-keysig-truth-2026-09/grade_artefact.py \
        --map benchmarks/omr-keysig-truth-2026-09/out/system-map-after.json
```

`grade_artefact.py --map` exists for exactly this and is committed; it writes
`grade-after.json`. ⚠️ Read the result as a CONFIRMATION that the mechanism
reaches a file, never as a controlled delta against the shipped artefact —
that comparison carries detector jitter and, if run Surya-free, the absence of
`<words>` as well.
