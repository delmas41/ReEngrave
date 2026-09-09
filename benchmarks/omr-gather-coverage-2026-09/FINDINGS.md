# What the GATHER stage collects, and what it cannot name

Sean, 2026-09-09: *"I just found that we were not tracking chords - notes
aligning in a bar. I want to know how many other things we are missing because
we are not gathering them OR we are collecting them in the wrong place."*

**The chord finding generalises, and it is the larger of the two faults.**
Answered with a derived tool rather than a written list:

```bash
python3 -m tools.omr.staged.gather_coverage            # the two lists
python3 -m tools.omr.staged.gather_coverage --json     # machine-readable
```

⚠️ **DERIVED, NOT TYPED, AND THAT IS THE WHOLE POINT.** The handoff that asked
for an inventory opens by correcting two false claims in its predecessor that
"cost real time"; CLAUDE.md carries a defect that stayed **fixed in the code and
open in prose for two days**, which then seeded a work order to close it again.
A hand-written list of what a stage collects is the exact shape that rots. Every
figure below comes from the AST of `gather.py`, from `record.Q`, from the
adjudicator registry's own `wants=`, from the legacy event dicts, and from the
committed class space. Re-run it; do not quote it from here.

---

## The headline

| | count |
|---|--:|
| quantities `record.Q` declares | 63 |
| **OBSERVED by a gatherer** | **31** |
| declared and only ever ABSTAINED on | 2 |
| declared, never gathered at all | 10 |
| **legacy quantities the record cannot NAME** | **11** |
| detector families with no quantity (of 35) | **16** |
| unaccounted (must be 0) | 0 |

---

## ⚠️ THE TWO FAULTS ARE DIFFERENT AND NEED DIFFERENT REPAIRS

Sean's question already contains the right split, and the measurement keeps it.

**NOT GATHERED** — no row of any kind carries it. `fermata` is the clean case:
the detector has two fermata classes, Beethoven 5 detects 36 against a truth of
36, the exporter writes them, and `record.Q` has no name for one.

**COLLECTED IN THE WRONG PLACE** — the ink IS in the log, under a name no
consumer can ask for. `gather_detections` files **every** detection as
`Q.GLYPH_BOX`, so slurs, ties, articulations and dynamic letters are all
present — and a decision declaring `wants=(Q.ARC_BOX,)` resolves to nothing,
because `Evidence` refuses a quantity the decision did not declare. The arc is
in the same log, three feet away, unreachable.

⚠️ **This is why "is x gathered?" gives a useless YES.** A notehead's x sits
inside its `Q.GLYPH_BOX` tuple, so onset looks covered. It is not: nothing can
ask for onset, and — the property the whole record exists for — **nothing can
ABSTAIN on it either.** An absent chord is indistinguishable from a chord
nobody looked for.

---

## LIST 1 — WHAT IS GATHERED TODAY (31 quantities)

| reader | quantities |
|---|---|
| `GEOMETRY` | `STAFF_LINES` `STAFF_SPACING` `STAFF_EXTENT` `STAFF_SKEW` `GAP_BRIDGING` `BRACKET_BLOCK` `BARLINE_COLUMN` `STAFF_ORDINAL` `SYSTEM_STAFF_COUNT` `NOTEHEAD_STAFF_POSITION` `GLYPH_BAND_DISTANCE` |
| `DETECTOR` | `GLYPH_BOX` `GLYPH_CONF` `NOTEHEAD_CLASS` `GLYPH_LADDER` `FLAG` `AUG_DOT` `TUPLET_MARKER` `BEAM_STROKE` `CLEF_GLYPH` `KEYSIG_MARKER` `METER_GLYPH` |
| `CV_LINES` | `STEM` `BEAM_STROKE` |
| `CV_LOCATOR` / `CV_HEADER` | `CLEF_LOCATED` `KEYSIG_RUN_POSITION` `KEYSIG_CLEF_FIT` |
| `TEMPLATE` | `METER_TEMPLATE` |
| `TEXT_LAYER` | `MARGIN_LABEL` |
| `DOSSIER` / `CATALOG` | `CLEF_SEED` `DOSSIER_FACT` `ROSTER_ENTRY` |

**Declared and only ever abstained on** — a reader that has never read:
`DIRECTION_WORD` (`NOT_IMPLEMENTED` — `gather_direction_text` is itself a stub)
and `SYSTEMIC_COLUMN` (`SYSTEM_TOO_SMALL` only).

⚠️ **`STEM` nearly appeared here as a false negative.** It is observed through a
loop variable — `for quantity, kind in ((Q.STEM, "stems"), …)` — so the first
version of the tool reported it ungathered and accused `adjudicate_duration` of
starving on it. The AST walker resolves loop-bound quantities and
`test_a_loop_bound_quantity_is_seen_as_observed` pins it, run RED with the
resolver disabled. **A coverage tool's own blind spot manufactures findings.**

---

## LIST 2 — WHAT COULD BE GATHERED

Three independent sources, because each finds gaps the others cannot.

### 2a. The chord family — the legacy pipeline carries it, the record cannot name it

These are keys on the event dicts `voicing.py` builds and `export.py` consumes.
The current reader has already proved it needs every one.

| key | what it is | why its absence is a hole |
|---|---|---|
| **`events`** | the ordered simultaneities a staff-measure resolves to | `Q.MEASURE_PARTITION` says where the BARS are; nothing says what is inside one |
| **`kind`** | chord \| rest — which event a glyph belongs to | **the chord itself.** `group_chords_in_measure` groups noteheads within 0.6 notehead widths in x, with a divisi veto on stem direction and a mode-vote over the group's durations — a tolerance, a veto and a vote, i.e. a full ADJUDICATION with no subject, no input and no verdict in the record |
| **`x_position`** | the event's ONSET, the axis events sort on | raw x is inside `Q.GLYPH_BOX`, which is exactly why it reads as covered |
| **`voices`** / `voice_index` | the staff-measure's 1–2 voice streams | MusicXML pairs `<slur>` WITHIN a `<voice>` — so `Q.ARC_OWNER` already depends on a quantity the record cannot express |
| **`stem_direction`** | up \| down, from `transcribe._stem_direction` | `Q.STEM` carries the stem's BOX and not its direction — and direction is what the divisi veto runs on |
| **`tied_to_next` / `tied_from_prev`** | the tie CHAIN between two events | `Q.ARC_KIND` decides tie-vs-slur for ONE arc; nothing names the chain |
| **`fermata`** | detected, exported, 36-for-36 on Beethoven 5 | no `Q` |
| **`ornaments`** | trill / turn / mordent / tremolo | the tenth export gap; `Q.ARTICULATION_MARK` is a different family |

### 2b. Five decisions declare evidence NOBODY gathers

⚠️ **THE STRUCTURAL FINDING, AND IT IS THE ONE THAT CHANGES A WORK PLAN.**

The handoff records six declared stubs and reads them as six adjudicators left
to write. **All six are also starved at the gather stage** — every one wants at
least one measurement no gatherer emits:

| stub | ungathered input | is the ink there? |
|---|---|---|
| `arc_kind`, `arc_owner` | `ARC_BOX` | yes — 2 classes, filed under `GLYPH_BOX`. **NAMING gap** |
| `articulation_owner` | `ARTICULATION_MARK` | yes — 10 classes. **NAMING gap** |
| `dynamic` | `DYNAMIC_LETTER` | yes — 12 classes. **NAMING gap** |
| `wedge_anchor` | `WEDGE_BOX` | yes — 2 hairpin classes. **NAMING gap** |
| `direction` | `DIRECTION_WORD` | no — the gatherer is a stub too. **READING gap** |

So **a stub is not one repair, it is two**, and writing the adjudicator alone
would leave it abstaining for lack of evidence — honest, and still not a working
stage. Four of the five are naming gaps, which are cheap: the ink is already in
the log and the work is a gatherer that files it under a quantity a decision can
declare.

**The 15 non-stub decisions are all fed** — no real decision is starved. That is
the reassuring half and it is measured, not assumed.

#### 2b-addendum — ⚠️ FOUR OF THE FIVE CLOSED IN THE MERGE, and the finding is
#### CONFIRMED rather than contradicted (2026-09-09, merge of four sessions)

Everything above was measured on this session's own branch and the committed
`out/gather-coverage.json` still records that state — it is a frozen fact and
is not rewritten. **The merged tree is different**, and only the merged tree is
the pipeline:

| stub | ungathered input, this branch | ungathered input, MERGED | closed by |
|---|---|---|---|
| `arc_kind`, `arc_owner` | `ARC_BOX` | — **fed** | `gather_glyph_families` |
| `articulation_owner` | `ARTICULATION_MARK` | — **fed** | `gather_glyph_families` |
| `dynamic` | `DYNAMIC_LETTER` | — **fed, AND NO LONGER A STUB** | `gather_dynamic_letters` + `adjudicate_dynamic` |
| `wedge_anchor` | `WEDGE_BOX` | — **fed** | `gather_wedge_boxes` (detector + CV rung) |
| `direction` | `DIRECTION_WORD` | `DIRECTION_WORD` — **still starved** | — |

Two sibling sessions landed exactly the four gatherers this section called
*"NAMING gaps, and cheap: the ink is already in the log"*, without having read
this finding. So:

- **`a stub is two repairs, not one` is CORROBORATED, not overturned.** The
  dynamics session did BOTH repairs for `dynamic` — gatherer and adjudicator —
  and it is the only one of the six that now decides anything. The four that
  got only the gatherer are still stubs: they abstain honestly, which is
  precisely what this section predicted a half-repair would produce.
- **The remaining starvation is exactly the one READING gap.** `direction` was
  already named as the only one, and it is the only one left.
- **The work plan changes accordingly**: four of the five are now ONE repair
  each — write the adjudicator — and the evidence is waiting in the log.

⚠️ **This was found by a TEST, not by re-reading the prose.**
`test_every_declared_stub_is_reported_with_its_input_state` failed on the
merged tree with `5 != 6`, exactly as its own docstring promised it would, and
now pins both halves: five stubs, and only `direction` starved.

### 2c. Sixteen detector families no quantity names

The class space is what the page already offers. 35 families, 146 classes;
**16 families have no quantity of their own**, so their ink reaches the log only
as an anonymous `Q.GLYPH_BOX`:

| family | classes | note |
|---|--:|---|
| **`rest`** | **11** | ⚠️ **no rest quantity of any kind.** A rest is half of every duration decision and a whole-measure rest means the BAR — the fix that corrected 1,251 attribute errors |
| **`accidental`** | **8** | in-bar accidentals. `Q.KEYSIG_MARKER` covers the signature only; `Q.ACCIDENTAL` is an EVALUATE consequence, not a reading |
| `tremolo` | 5 | the detector produces zero of these — a known detection gap, now visible as a vocabulary gap too |
| `grace` | 4 | the documented pre-fill ceiling: 0 `Small` detections on any page |
| `ornament` | 4 | with 2a above |
| `keyboard`, `strings`, `fermata` | 2 each | pedal marks, bowings, fermatas |
| `arpeggiato`, `brace`, `caesura`, `coda`, `ottava`, `repeat`, `segno`, `unpitched` | 1 each | `repeat` is the standing "repeat signs dropped on export" TODO |

⚠️ **`export_coverage.py` warns that auditing the class space for "classes
nothing consumes" calls accidentals CONSUMED — because they are, into pitch.**
That warning is respected: this asks whether a family has its **own name in the
record**, never whether something eventually uses it. A `None` here is never
"the ink is lost".

---

## Anti-drift

Both tables are contracts, not lists:

* `unaccounted()` fails on a legacy event key in neither `LEGACY_TO_Q` nor
  `NO_VOCABULARY`, so widening the event dict cannot silently widen the blind
  spot — which is how `kind`, `x_position` and `voices` came to be missing.
* `class_space_coverage()["unmapped"]` fails on a detector family missing from
  `FAMILY_TO_Q`.
* `test_no_vocabulary_entries_still_have_no_vocabulary` fails the day a gap is
  FILLED, so a closed entry must leave the table — the same contract
  `export_coverage.KNOWN_GAPS` holds.
* `test_every_declared_stub_is_reported_with_its_input_state` fails if a stub
  stops being starved, which is when §2b must be re-read.

## What this does NOT say

⚠️ **No arm was run and no page was read.** Every figure is a property of the
tree: which quantities a gatherer emits, which a decision declares, which
classes exist. It does not say how OFTEN a missing quantity would fire on a real
page, and it cannot — that needs a run with weights, which a cloud container has
not got. **Measure REACH before accuracy** on anything ranked from this file.

⚠️ **The class space read here is the committed 146-name DSv2 list**, not the
208-name production space (two annotation sets concatenated, see
`class_aliases.py`). Families are the unit, and the duplicate-name block adds no
family — but a per-CLASS count taken from here is a floor, not a total.
