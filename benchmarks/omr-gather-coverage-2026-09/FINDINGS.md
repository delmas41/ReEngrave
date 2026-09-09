# What the GATHER stage collects, and what it cannot name

Sean, 2026-09-09: *"I just found that we were not tracking chords - notes
aligning in a bar. I want to know how many other things we are missing because
we are not gathering them OR we are collecting them in the wrong place."*

```bash
python3 -m tools.omr.staged.gather_coverage            # the two lists
python3 -m tools.omr.staged.gather_coverage --json     # machine-readable
```

---

## ⚠️ READ THIS FIRST: THE CHORD GAP IS CLOSED, AND NOT BY THIS BRANCH

This file was first written on a branch cut before 31 commits landed on main.
In that window, **parallel sessions found the same gaps and FIXED them**:

* **`Q.EVENT`** — *"which glyphs of a bar sound TOGETHER — one event, N
  noteheads"* — is the chord quantity. Its own docstring settles `x_position`
  beside it: the x POSITION is a measurement `GLYPH_BOX` already carries, the
  SIMULTANEITY is the interpretation.
* **`Q.REST`** — whose docstring records the same finding this file reported:
  *"a rest was detected … reached `GLYPH_BOX`, and NOTHING ANYWHERE DECLARED
  THE ABSENCE."*
* **`gather_glyph_families`** gathers `ARC_BOX`, `ARTICULATION_MARK`,
  `DYNAMIC_LETTER` and `WEDGE_BOX` — the four naming gaps this file named.

**So the headline of the first draft is history.** It is kept, corrected, in
§5, because the corrections are the finding: this file asserted open gaps that
were closed, which is *fixed-then-kept-open-in-prose*, the fault CLAUDE.md
records having already cost this project real time twice. It very nearly
shipped a third time.

⚠️ **AND THE TOOL'S OWN GUARD MISSED IT.** See §4. That is the durable lesson
here, more than any count below.

---

## 1. The headline, on the merged tree

| | count |
|---|--:|
| quantities `record.Q` declares | 66 |
| **OBSERVED by a gatherer** | **37** |
| declared and only ever ABSTAINED on | 2 |
| declared, never gathered at all | 6 |
| legacy quantities the record cannot NAME | **7** |
| detector families with no gather quantity (of 35) | **15** |
| unaccounted (must be 0) | 0 |

**One decision is still starved**: `DIRECTION` wants `DIRECTION_WORD`, which
`gather_direction_text` only ever abstains on (`NOT_IMPLEMENTED`). It was six.

---

## 2. The two faults, which are still different

**NOT GATHERED** — no row carries it. `fermata` remains the clean case: two
detector classes, Beethoven 5 detects 36 against a truth of 36, the exporter
writes them, and `record.Q` has no name for one.

**COLLECTED IN THE WRONG PLACE** — the ink IS in the log, under a name no
consumer can ask for, because `gather_detections` files every detection as
`Q.GLYPH_BOX` and `Evidence` refuses a quantity the decision did not declare.
⚠️ This was the larger half and it is the half that got fixed: four of the five
starved stubs were naming gaps, and `gather_glyph_families` closed all four.

⚠️ **The reason "is x gathered?" gives a useless YES still stands.** A
notehead's x sits inside its `Q.GLYPH_BOX` tuple. Nothing could ask for onset,
and — the property the record exists for — nothing could ABSTAIN on it either.

---

## 3. What is STILL missing

**Seven legacy event keys with no name in the record**, down from eleven:

| key | what it is |
|---|---|
| `voices` / `voice_index` | the staff-measure's 1–2 voice streams. ⚠️ MusicXML pairs `<slur>` WITHIN a `<voice>`, so `Q.ARC_OWNER` depends on a quantity the record cannot express |
| `stem_direction` | up \| down, from `transcribe._stem_direction`. `Q.STEM` carries the stem's BOX, not its direction — and direction is what the divisi veto runs on |
| `tied_to_next` / `tied_from_prev` | the tie CHAIN. `Q.ARC_KIND` decides tie-vs-slur for one arc; nothing names the chain between two events |
| `fermata` | detected, exported, no `Q` |
| `ornaments` | trill / turn / mordent / tremolo; the tenth export gap |

**Fifteen detector families with no gather quantity**, led by **`accidental`
(8 classes)** — and that one is recorded deliberately in
`FAMILY_Q_IS_ELSEWHERE`: `Q.ACCIDENTAL` exists but is an EVALUATE consequence,
the pitch respelled once the key settles, not a reading of the printed glyph.
⚠️ An in-bar accidental is **SCOPE, not a mark** — it holds to the barline
(`transcribe.py:2210` implements exactly that) — and a span is a shape the
record has nowhere to put. Then `tremolo` (5, the detector produces none),
`grace` (4, the documented ceiling), `ornament` (4), and eleven singletons
including `ottava`, where a miss costs every note in the span an octave.

---

## 4. ⚠️ THE GUARD HAD THE BUG IT EXISTS TO PREVENT

`test_no_vocabulary_entries_still_have_no_vocabulary` compared lowercased
names for **exact equality**, so the legacy key `events` never matched
`Q.EVENT` — singular against plural. The entry stayed in `NO_VOCABULARY` for a
day after main closed it, and the stale claim reached a PR body, CLAUDE.md, a
project brief and this file. The same class of miss left the `rest` family
mapped to `None` after `Q.REST` landed.

Nothing caught it on its own terms. What caught it was **a different test** —
`test_every_declared_stub_is_reported_with_its_input_state` failing with
*"ARC_KIND is no longer input-starved"* during a trial merge.

Three repairs, all pinned:

* `q_covering()` normalises singular/plural. ⚠️ Deliberately **not** a
  substring test — `stem_direction` would match `Q.STEM` under one, and those
  are different quantities.
* `test_no_family_is_mapped_to_None_while_a_Q_exists` asks the vocabulary
  rather than trusting the table, and `FAMILY_Q_IS_ELSEWHERE` records the one
  deliberate exemption with its reason.
* `test_the_elsewhere_exemptions_are_still_needed` evicts an exemption whose
  `Q` has gone.

**The lesson worth carrying: an anti-drift check is itself an artefact that
drifts.** This one was written, reviewed, run RED to prove it load-bearing —
and was still wrong in a way its own subject matter predicted.

---

## 5. The first draft's figures, kept as history

Measured on the branch before the merge, and **not comparable** to §1 — they
describe a tree that no longer exists:

| | first draft | now |
|---|--:|--:|
| declared | 63 | 66 |
| observed | 31 | 37 |
| declared, ungathered | 10 | 6 |
| stubs starved | 6 | 1 |
| legacy keys unnameable | 11 | 7 |

The claim *"all six declared stubs are also starved at gather"* was true when
written and is now true of one. The claim *"16 of 35 families have no
quantity"* is now 15. **Neither is quotable.**

---

## 6. What this still does NOT say

⚠️ **No arm was run and no page was read.** Every figure is a property of the
tree, so nothing here says how OFTEN a missing quantity would fire. **Measure
REACH before accuracy.**

⚠️ The class space read here is the committed 146-name DSv2 list, not the
208-name production space. Families are the unit; a per-CLASS count from here
is a floor.

⚠️ This tool does not overlap `tools/omr/staged/inventory.py`, which landed on
main in the same window: that one is a derived inventory of the 21 DECISIONS,
this one of the gather-stage QUANTITIES, the legacy event vocabulary and the
detector class space. They share the `gather.py` AST walk and nothing else.
