# The four categories, and the definitions that make them countable

**Committed BEFORE any output was generated or inspected.** That ordering is
the point, and it is checkable: this file is alone in its own commit, and that
commit is an ancestor of the commit that produces the artefact. The plan says
so twice —

> ⚠️ Fix those categories BEFORE looking, or the count fits itself to what was
> found.
> — `docs/plan-2026-09-10-wire-first-then-reconcile.md` §6, Phase 2

If a definition below turns out to be wrong, it is corrected in a **new**
commit that says what changed and why. It is never amended, because an amended
commit destroys exactly the evidence this file exists to provide.

⚠️ The four category NAMES are the plan's and are not mine to replace:
**missing** / **wrong** / **spurious** / **would-not-notice**. What follows is
only the sharpening.

---

## 0. What is being counted — the UNIT, decided first

> **One unit = one FIX-ACTION: one edit a human would make in a score editor,
> counted at the largest scope that a single editorial gesture repairs.**

Not an element, not a bar, not an OMR-NED edit. The reason is the question
itself: Sean asked *"how much work would I have to do to clean it up"*, and
work is measured in gestures, not in XML nodes.

Three consequences, all deliberate:

* **A fix-action has a SCOPE, and the scope is part of the count.** Deleting
  one spurious note is one action. Deleting a whole spurious staff is also
  *one* action if one gesture does it (select staff, delete) — and the sheet
  records the scope beside it, so nobody can later read "1" as "one note".
* **The scope vocabulary is fixed in advance and is closed**: `element`,
  `chord`, `bar`, `staff-bar`, `staff-system`, `system`, `page`. A fix that
  fits none of these is recorded as `other` WITH A DESCRIPTION and is a
  finding about this scheme, not a judgement call made silently.
* **Re-entering a whole bar is ONE action at scope `staff-bar`**, even if the
  bar holds nine wrong notes. This is the single largest divergence from
  OMR-NED and it is intentional. CLAUDE.md records that musicdiff's
  amplification differs **6×–2× by error kind**, which is exactly what makes
  its buckets unrankable; a fix-action count is amplification-free by
  construction, because the human does the same amount of work either way.

⚠️ **The counter-hazard, stated because it is real:** a fix-action count
rewards a pipeline that fails in large contiguous blocks over one that fails in
scattered singles, and those are not equally good outputs — a scattered failure
is easier to MISS. That is why **`would-not-notice` is a category and not a
footnote**: the risk of a scattered error is that it survives the pass, and
this scheme has to surface that rather than bury it (§2c).

---

## 1. The four categories

### `missing` — the print has it, the file does not

The human must ADD something. The page prints a mark, a note, a staff, a bar;
our file does not carry it.

**Boundary:** `missing` is about ABSENCE, not about being unreadable. A note
the detector never found and a note a decision abstained on are both `missing`
to the human — the human's work is identical. **The record can tell them apart
and the counting sheet carries the machine's answer in a separate column**
(§3), so the distinction survives without being smuggled into the human's
judgement.

### `wrong` — the file has something there, and it says the wrong thing

The human must EDIT in place. There is an element in roughly the right place
with the wrong value: a note at the wrong pitch, a rest of the wrong length, a
clef naming the wrong line, a slur bound to the wrong notes.

### `spurious` — the file has something the print does not

The human must DELETE. Ink that was never printed, or a reading of real ink as
a symbol it is not (the 212 `arpeggiato` boxes on this very document, which
CLAUDE.md already records as misread stems and barlines, are the type case).

### `would-not-notice` — a real difference that costs zero work

It is a difference from the print, and **the human would ship the file without
touching it.**

---

## 2. The three hard calls, decided, with reasons

### 2a. Right pitch, wrong duration: ONE `wrong`, not `missing` + `spurious`

**Decided: one `wrong` at scope `element`.**

The rule that produces it, stated generally so it settles the cases nobody has
thought of yet:

> **If a single editorial gesture fixes it, it is ONE unit. Where an element
> is present at approximately the right place, the category is `wrong`,
> whatever field is at fault.**

A human selects that note and changes its duration: one gesture. Splitting it
into a deletion plus an insertion would double-count exactly the error kind
OMR-NED double-counts, and CLAUDE.md's account of why its buckets cannot rank
work is precisely that this doubling is not uniform across error kinds.

⚠️ **"Approximately the right place" needs a bound or it is not a rule.**
Bound: **the element is in the same bar of the same staff.** Cross that
boundary and it is `spurious` there plus `missing` here — genuinely two
gestures, because the human deletes in one place and adds in another.

### 2b. A staff that failed to pair: ONE unit at scope `staff-system`, and the scope is load-bearing

**Decided: one unit, scope `staff-system`, NEVER one-per-element.**

CLAUDE.md records the trap in the opposite direction — attributing structural
work by the `entire staff` bucket alone **systematically under-counts
fragmentation**, because a fragmented output pairs with MORE truth parts and so
*buys* `entire staff` while *paying* in `entire measure`. That is an argument
about a metric's buckets. Here the scope field carries what the metric could
not: **one action, but its scope says how much music it moves**, and the sheet
totals units and scopes separately so neither can hide the other.

⚠️ **Whose gesture is it?** A whole staff standing in the wrong part, or a part
split into per-system fragments, is repaired by one drag or one re-assignment
in an editor — provided the MUSIC on it is right. If the music on it is also
wrong, those are separate units: **the structural fix and the content fixes are
counted apart**, because doing one does not do the other.

### 2c. `would-not-notice` is **THE EDITOR'S** eye, and this is a choice

**Decided: the EDITOR — the person preparing this file for use.**
That is Sean, doing the pass. Not the engraver (who notices everything, which
would empty the category) and not the player (who notices almost nothing, which
would swallow it).

Operationally:

> Would you ship the file with this in it? If yes, it is `would-not-notice`.

⚠️ **This is the one subjective category and it is deliberately placed where
the subjectivity is visible**, rather than distributed invisibly through the
other three. Two counters may legitimately differ here and agree everywhere
else. It is a NOTICE-BOARD, not a residue: a large `would-not-notice` column is
itself a finding — it says the remaining differences are cosmetic.

⚠️ **What it must NOT absorb:** anything the editor would fix *if they saw it*
but might miss. That is `wrong` with a **`missable`** flag on the sheet, not
`would-not-notice`. The distinction is *cost zero* versus *cost hidden*, and
collapsing them would let the count launder the scattered-failure hazard of §0.

---

## 3. What the machine may and may not contribute

**The machine proposes. The human counts.** Every machine-produced cell in the
counting sheet is in a column named `proposed_*` and no proposed value is ever
summed into a total.

The machine is allowed to contribute exactly one thing the human cannot see and
the record can: **why a thing is absent.** Three states, kept apart, which is
the entire product of Phase 1:

| state | meaning | the human still counts it `missing` |
|---|---|---|
| `page_has_none` | no detection, and the print carries none either | no — it is not missing at all |
| `not_detected` | the detector found no ink | yes |
| `abstained` | the ink was found and a decision refused to read it | yes |

⚠️ `page_has_none` is a claim about the PRINT and the machine cannot make it
alone — it can only say *nothing was detected*. So the machine writes
`not_detected` and only the human's mark promotes it to `page_has_none`.
**A fallback must never convert "cannot tell" into a definite answer** —
CLAUDE.md's governing rule, and this is where it bites in this instrument.

---

## 4. Worked examples

⚠️ **Every example below is drawn from a finding ALREADY COMMITTED in this repo
before this file existed, deliberately** — no example comes from the artefact
this instrument is about to produce, because the whole point of committing the
definitions first is that they were not fitted to it. Real examples from the
artefact are added in a LATER commit, marked as such.

| case, and where it is already recorded | category | scope | why |
|---|---|---|---|
| `arpeggiato` ×212 on this document — 56×388 px boxes at conf 0.39, "a stem or a barline" (CLAUDE.md, GATHER section) | `spurious` | `element` | ink that is not that symbol; the human deletes each |
| a chord whose UPPER member is tied with `<tied>` written on the LOWEST note — 17 of 48 on Litolff (`benchmarks/omr-chord-tie-2026-09`) | `wrong` | `element` | the tie exists and names the wrong note: one edit |
| a bar with no detected events exported as a whole-measure rest where the page prints music (CLAUDE.md: `_mxl_empty_measure` cannot tell SILENT from UNREAD) | `missing` | `staff-bar` | the human re-enters the bar: one gesture |
| Brahms p2's 27 per-system fragments instead of 14 continuous parts (`OMR_SLOT_STITCH` entry) | `wrong` | `staff-system` | the music may be right; the PART is wrong — §2b |
| a `<slur>` and a `<tied>` swapped over two adjacent same-pitch heads (`OMR_ARC_RECLASS`) | `wrong` | `element` | one element, one wrong kind |
| `divisions` written 48 where 4 would do | `would-not-notice` | `element` | no editor ships a file differently for it |
| a `<direction>` word placed at the head of the bar rather than under its note (the staged exporter's DECLARED simplification) | `would-not-notice` | `element` | *unless* the editor is engraving — which is why §2c names whose eye it is |

---

## 5. What this scheme does NOT establish

* **It is not a metric and must not be driven down.** The plan: *the moment it
  becomes a number to drive down, it will be gamed the way OMR-NED was* — and
  the two are gamed in OPPOSITE directions, OMR-NED rewarding more symbols and
  a cleanup count rewarding fewer. It is read as *what should we fix next*.
* **It is not comparable across documents** until the same human has counted
  two, and probably not then: a page's density and print quality move every
  column.
* **Inter-counter agreement is unmeasured.** These definitions are written to
  make two counters agree; whether they do is a fact about people, and nobody
  has tested it. One counter's sheet is one counter's sheet.
