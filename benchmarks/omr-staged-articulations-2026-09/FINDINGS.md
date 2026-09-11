# `articulation_owner`: a stub filled, and why it is THREE repairs and not one

`gather_coverage` and `inventory` agreed that `articulation_owner` was one of
two stubs whose input is already gathered, and the handoff that ranked it
called those *"one repair each (write the adjudicator; inputs are gathered)"*.

**The tree says otherwise, and the difference is the whole point of this
benchmark.** Before this change:

```
$ grep -c articulations tools/omr/staged/export.py
0
$ grep -n '"articulation"' tools/omr/staged/export.py
    "articulation": (Q.ARTICULATION_OWNER, ("artic",), ()),   <- EMPTY counter
```

So the adjudicator alone would have produced a decision no file reads and no
counter can see — a fresh `decided_and_unwritten` row, which is **the bucket
the arc session had just emptied**, in the architecture built to stop exactly
that. `adjudicate_dynamic` decided for a day with `grep '<dynamics'` returning
zero; `arc_kind` decided 199 arcs a page with no `<slur>`. Both were found by
forensics. This lands the adjudicator, the emission and the counter together.

---

## 1. WHAT THE RULE IS — and what was NOT re-derived

`transcribe._attach_articulations_in_cell` has said it since the seventh export
gap closed: a mark goes to the notehead nearest it in X **on the side its own
class names**, within `_ARTIC_MAX_DX_NOTEHEAD_WIDTHS`.

* **The constant is IMPORTED**, and an AST test asserts `0.75` is not spelled
  in the staged module. It was swept over eight engraved works onto a flat
  plateau — 0.50 through 2.50 identical, 197 placed at precision 0.980, with a
  cliff below at 0.30 — so this project has paid for that number once.
* **The unit is a NOTEHEAD width, not the mark's own box**, which is the
  mistake the augmentation-dot gate paid 193 edits for.
* **The width is a MEDIAN**, so one merged blob cannot widen the limit for
  every mark in the bar.
* **A mark with no notehead on its declared side ABSTAINS.** 21 of 218 across
  the legacy corpus do, and abstaining is why that precision is 0.980.

⚠️ **The cell's own CANONICAL frame is correct here**, and saying so matters
because the decision one function up needs the opposite: a mark and its
notehead were cut from ONE cell and share a frame by construction, while
`arc_owner` asks about other staves and needs page pixels. A canonical x
compared across two staves is the fault that made `Q.ONSET_COLUMN` report
1,062 columns of nothing.

⚠️ **A fourth reason, `no_side_declared`, with ZERO REACH on this document.**
`class_aliases.COARSER_THAN_CANONICAL` records `articulationAccent` /
`Staccato` / `Tenuto` as coarser spellings carrying no side, and `_artic_side`
returns None rather than guessing. All 24 marks on Litolff `984073` p1-3 name a
side, so **the page cannot exercise that branch and it is tested directly
instead** — the alternative being a branch that is only ever green because
nothing reaches it.

---

## 2. THE INSTRUMENT — and why it is a DIFFERENT one from the arc work

⚠️⚠️ **THIS IS THE ADJUDICATE-ONLY CASE.** `Q.ARTICULATION_MARK` and
`Q.GLYPH_BOX` were both already gathered, so a saved record contains everything
the new rule needs and re-adjudicating it is a real A/B. The arc export was
**not** this case — it added `Q.CELL_BOX`, a GATHER change, to which
`readjudicate` is structurally blind. *Check which case you are in before
reaching for either instrument.*

The rebuild is verified by the tool that owns that check: `readjudicate.py
--control` on this record reproduces **1863 of 1863** duration verdicts
exactly, 0 differing, before any arm is read.

⚠️ **BOTH arms are re-adjudicated.** Using the record's SAVED verdicts as the
off arm would compare a rebuild against a pipeline run, and any difference
between those two would be billed to this rule.

---

## 3. REACH, BEFORE ANYTHING ELSE

| | |
|---|--:|
| `articulation_mark` rows, Litolff `984073` p1-3 | **24** |
| `articStaccatoAbove` / `Below` | 17 / 6 |
| `articTenutoBelow` | 1 |
| marks declaring no side | **0** |

⚠️ **24 marks over three pages is a SMALL population, and the number is stated
before any result** — a change that moves nothing because it is inert and one
that moves nothing because the page holds nothing to move are the same number.
The engraved corpus is a different world: one Mozart 40 page alone detects 102
staccati, and musicdiff charged back exactly 102 `insarticulation` edits for
them. **Nothing here should be read as a rate for engravings.**

## 4. THE RESULT — Litolff `984073` p1-3

One gather, adjudicated twice, the rule stubbed out in the off arm.

| | OFF | ON |
|---|--:|--:|
| `<articulations>` in the file | 0 | **14** |
| marks decided | 0 | 18 |
| marks abstained `no_notehead` | — | 6 |
| decided but owning notehead not written | — | 4 |
| notes / rests / slurs / ties / dynamics | 1075/432/23/49/132 | **identical** |

**The partition closes both ways**: 24 = 18 decided + 6 abstained, and
18 − 4 = 14 written. `articulation_balance` reports `balanced: True`.
Kinds written: 13 staccato, 1 tenuto.

⚠️ **THE CONTROL LINE WAS A FALSE ALARM AND THE PROBE WAS AT FAULT.** The arm
reported *"outside the `<articulations>` blocks, the two files are DIFFERENT"*
while every family count was identical to the unit. `_mxl_note` emits
`<notations>` only when that list is non-empty, so a note whose ONLY mark is an
articulation gains a **wrapper** as well as the block inside it — and the
line-based strip removed the block and left the wrapper. **A control firing on
its own side effect**, which is how a real regression hides behind an expected
one. Replaced with a structural strip (drop the articulation elements, then
drop any `<notations>` left childless), proven on a minimal fixture where the
structural strip says IDENTICAL and the line-based one says DIFFERENT with the
wrapper as the only delta. ⚠️ The arm now also **NAMES** any difference it
reports rather than only flagging one — a control that says "different" and
stops sends the next reader to diff two 50k-line files by hand.

### 4b. ⚠️ Does the ENGRAVED constant hold on a scan? On this evidence, yes.

Distance from each attached mark to its notehead, in the constant's own unit
(limit **0.75**):

```
n=18   min 0.003   median 0.095   max 0.435
0.003 0.037 0.040 0.052 0.054 0.070 0.074 0.081 0.085 0.095
0.116 0.119 0.121 0.126 0.163 0.213 0.221 0.435
```

**The whole population sits under 0.44 against a cut at 0.75** — which is what
a plateau looks like from the inside. ⚠️ This is the question the arc work
forced: `_SLUR_ARC_PAD_NOTEHEADS` was measured the same way on an engraved page
and **its plateau does not exist on a scan**. This constant survives its first
look. ⚠️ n = 18, and it says nothing about the 6 marks that were REFUSED.

---

## 4c. THE SECOND PUBLISHER — reach measured, arm NOT yet run

Breitkopf Brahms 1 p0-3, gathered 2026-09-10: **196 articulation marks** —
95 `articStaccatoAbove`, 81 `Below`, 7 `articStaccatissimoAbove`, 7
`articAccentAbove`, 2 `articTenutoBelow`, 2 `articStaccatissimoBelow`, 1
`articAccentBelow`, 1 `articTenutoAbove`. **110 above / 86 below, and again
ZERO declaring no side** — so `no_side_declared` has zero reach on BOTH
publishers, and the coarse spellings `class_aliases` records never appear in
either scan.

⚠️ **The arm on that record was still running when this was written.** Its
reach is reported because reach is a property of the record; **no result is
claimed.** ⚠️ And that record was gathered by a tree that PREDATES this change
(its saved verdicts read `not_implemented: 196`, "DECLARED STUBS: 3"). GATHER
is untouched by this work so re-adjudicating it is a valid A/B — but it is a
pre-change tree's record, which is the *"benchmark arm silently reused from an
earlier tree"* shape this repo already records, so it is written down rather
than kept in someone's head.


---

## 5. ⚠️ THE MUTATION BATTERY — ten arms, and the one that broke the harness

Ten arms, **all red**, positive control green, tree clean afterwards.

| arm | |
|---|---|
| side test inverted | RED |
| the 0.75 limit removed | RED |
| MAX width, not median | RED |
| first head, not the nearest | RED |
| returns the MARK, not the head | RED |
| kind dropped from the verdict | RED |
| `no_side_declared` collapsed into `no_notehead` | RED |
| placement pass not called | RED |
| kwarg never reaches the renderer | RED |
| the counter deleted | RED |

⚠️⚠️ **THE FIRST RUN OF THIS BATTERY REPORTED TEN SURVIVORS WHILE HAVING
DELETED BOTH SOURCE FILES.** It copied to `/tmp/own.orig.py` and restored from
`/tmp/$(basename …).orig.py` — a **different name** — so `sed` wrote empty
files over `ownership.py` and `export.py`, pytest printed *"no tests ran"*, and
the classifier was `grep -q failed`, which an empty run does not match. **Every
arm read SURVIVED.** The work was uncommitted; it was recovered from the
backups that did exist under the other name.

That is the same defect caught the same day in the arc probe's battery and
**in the opposite direction**, which is the useful part:

> A battery can pass by refusing everything, **and it can pass by accepting
> everything.** Both look like a clean result, and neither is distinguishable
> from the real one by reading the summary line.

The rewrite (`probe/battery.sh`, kept beside this file):

* restores from **`git show HEAD:<path>`**, never a hand-named backup;
* **refuses a mutation that does not textually apply**, rather than writing an
  unchanged file and calling it an arm;
* classifies a run as **`BROKEN`** — not `SURVIVED` — when the harness produces
  no recognisable result, and asserts the exact expected pass count;
* checks the tree is clean at the end.

⚠️ **That guard earned its keep on its own first run**, catching `${=T}`: zsh
does not word-split a variable holding two paths, so pytest received one
nonexistent argument and ran nothing. It reported ten `BROKEN` instead of ten
false survivors. *The same zsh gotcha this repo already records for
`env $3`.*

---

## 6. WHAT THIS DOES NOT SAY

1. **No OMR-NED figure**, deliberately. The metric is symmetric and rewards
   emitting more symbols, and this change emits more symbols.
2. **No accuracy claim.** Nothing here compares a placed mark against a truth
   file. The legacy rule's 0.980 precision is the ENGRAVED corpus's and is
   quoted as the constant's provenance, not as this path's result.
3. **n = 1 document, 24 marks.** Breitkopf Brahms 1 is the second publisher
   this wants, for the same reason the dotted rest does.
4. ⚠️ **The engraved plateau has NOT been re-checked on a scan.** The arc work
   found that `_SLUR_ARC_PAD_NOTEHEADS`' plateau — measured the same way, on an
   engraved page — **does not exist on a scan**. The arm prints every attached
   mark's distance in the constant's own unit so the question stays visible;
   with 24 marks it cannot be answered here.
