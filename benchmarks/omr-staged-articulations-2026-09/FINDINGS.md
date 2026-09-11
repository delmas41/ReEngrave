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

<!--ARM-->

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
