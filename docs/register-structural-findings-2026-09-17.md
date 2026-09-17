# The structural findings register — collected, deliberately NOT ranked

Sean, 2026-09-16: *"we will be able to document what the real bottlenecks are
as well as better prioritize the remaining work... big picture fixes that get
prioritized once we have them all."*

**Collecting and ranking are two acts, and this document only does the first.**
The plan says why: *the moment it becomes a number to drive down it will be
gamed the way OMR-NED was*. This project has already paid twice for ranking by
the loudest signal — musicdiff's buckets amplify 6×–2× by error kind and cannot
rank work, and *attributing structural work by the `entire staff` bucket alone
systematically under-counts fragmentation*. So nothing here carries a priority
number. What it carries instead is the thing that **makes** ranking possible: a
statement of what KIND of fix each finding needs.

```bash
# the derived half — regenerates itself, cannot rot
python3 benchmarks/omr-plumbing-2026-09/probe/collect.py \
        --edges benchmarks/omr-plumbing-2026-09/out/matrix/edges.json
```

---

## 1. The taxonomy, and why it is ordered

Seven kinds. Each is a different repair, a different cost and a different blast
radius — which is the whole reason the register is worth more than a list.

| kind | the fault | who can state it |
|---|---|---|
| **VOCABULARY** | no category exists for the ink | `gather_coverage`, `probe_vocabulary` |
| **WIRING** | the value exists and nothing reads it | `reach`, `wiring`, `edges` |
| **FRAME** | the value exists in units the reader cannot answer in | `wiring` |
| **SHAPE** | the record has nowhere to PUT the fact | ⚠️ nobody — judgement |
| **REACH** | the wire is sound; no ROW was ever made for the ink | `edges`, the detector |
| **ARCHITECTURE** | the fix crosses a stage boundary, or needs a stage | ⚠️ nobody — judgement |
| **INSTRUMENT** | the measuring tool is wrong | ⚠️ found by accident, every time |

⚠️⚠️ **THE KINDS ARE ORDERED BY DEPENDENCY, AND THAT IS THE PRIORITISATION
TOOL.** *A missing category costs nothing until there is a reader that would
have filled it* — and a reader costs nothing until something consumes what it
produces. So **VOCABULARY < WIRING < REACH**: a fix only pays once everything
DOWNSTREAM of it is already connected. That is the wire-first plan's own
argument arriving from the instruments, and it is why a bare list of gaps
sorted by occurrence count would rank the work wrongly: the largest
VOCABULARY gap can be worth less than a small WIRING one sitting below it.

⚠️⚠️ **AND REACH IS NOT THE TERMINUS, WHICH IS THE WHOLE POINT OF HAVING
STAGES.** Sean, 2026-09-17: *"Reach is the hardest part but that is why we have
all these stages. When the ink is unreadable there are a lot of other
inferences and deductions that can help us make sense of what something is.
Which is why we need information flowing even if it is a blob that we have not
yet figured out. That is the point of the architecture."*

An earlier draft of this section called REACH *"the one kind that cannot be
fixed by connecting anything"*. **That is wrong, and it is wrong in the
direction that would have mis-ranked every remaining piece of work.** REACH
splits in two, and only one half is about the detector:

⚠️⚠️ **AND THE SPLIT THIS SECTION FIRST DREW — "undetected" against "unnamed"
— IS ITSELF A CATEGORY ERROR.** Sean, 2026-09-17: *"Missing doesn't make sense
to me. We can only gather what we see. We may or may not be able to classify it
correctly initially - or at all - but ink is ink. There is nothing that should
be classified as unseen - only unclassified."*

He is right, and the correction goes deeper than vocabulary. **GATHER's
population should be THE INK ON THE PAGE; the detector is one CLASSIFIER over
that ink, not the authority on what exists.** Today GATHER's population IS the
detector's output — so ink the detector did not fire on produces no row at all,
and the record says *nothing here* when the truth is *something here, unnamed*.

**That is the ABSENT/DECLINED collapse `record.py` exists to prevent, happening
to ink itself, at the base of the pipeline.** Every other quantity in this
system is careful to distinguish *we could not look* from *we looked and could
not say*. Ink is the one place where the distinction was never available,
because there is no row to carry it.

So there is ONE gap, not two: **ink with no row.** Whether we can name it is a
separate, later, REVISABLE question — which is exactly why the row has to exist
before the naming is attempted. A blob is not a failure state; it is the
evidence every later stage is entitled to argue over.

The resolving evidence is SIDEWAYS, and the architecture is built for exactly
that: a blob at one bar on one staff is noise; the same blob at the same bar
across ten staves is a printed event, and where three of ten staves DO classify
it, the classified minority names what the majority corroborates. That is not
a new idea to be invented — it is `A-DUR-5`, recorded in `ASSUMPTIONS.md` as
**UNBUILT AND WANTED** since 2026-09-09.

---

## 2. The derived half — regenerated, never typed

`collect.py` pools four instruments. **Do not copy its numbers into this
document**; a hand-copied figure is exactly what rots, and this file has the
scars of that pattern recorded in CLAUDE.md a dozen times over.

| source | question | command |
|---|---|---|
| `reach` | does anything read this quantity AT ALL? | `python3 -m tools.omr.staged.reach --check` |
| `wiring` | frame / detail / roundtrip faults | `python3 -m tools.omr.staged.wiring --check` |
| `no_producer` | a parameter threaded with no supplier | `python3 -m tools.omr.no_producer --check` |
| `edges` | which declared CONNECTIONS ever carried a value | `probe/edges.py out/matrix/*.record.json` |

⚠️ `collect.py` prints a per-source count and says **SOURCE SILENT** where one
did not run, because *a source that did not run and a source that found
nothing are the same zero* — the ABSENT/DECLINED distinction, applied to the
register itself.

---

## 3. The judged half — findings no instrument can state

### 3.0 ⚠️⚠️ THE KEYSTONE — unclassified ink, and the consumers already waiting for it

`A-DUR-5`, `tools/omr/staged/ASSUMPTIONS.md:931`, **unbuilt**. It is listed in
that file's own table as item 7, *"undefined blobs of ink — ❌ not built"*.

**Why it is the keystone rather than one more gap: it is the only finding in
this register that CONVERTS one kind into another.** A raster pass in GATHER
that keeps unnamed ink as rows turns a REACH/UNDETECTED finding — the terminal
kind — into REACH/UNNAMED, which the sideways machinery can resolve. Nothing
else here moves a finding down the dependency order.

⚠️ **It cannot be built from the detection record, and that is MEASURED, not
assumed.** Beethoven 5 / Litolff p.62 cell 8 prints a meter on every staff; we
classify it on **2 of 17**, and the other 15 carry **no unclassified detection
at that column** — the ink was never detected at all. So this needs a RASTER
pass, not a re-weighting of what is already recorded. The precedent is in the
tree: `direction_text._blank_detections` already subtracts every detection from
the page's ink so that *"find the text"* becomes *"find the ink"*. The same
subtraction, **kept as rows rather than consumed for OCR**, is the whole
mechanism.

**⚠️⚠️ THE CONSUMERS ARE ALREADY BUILT AND ARE WAITING ON THE PRODUCER.** This
is the register's sharpest inversion — everywhere else in this project the
value exists and nothing reads it; here the readers exist and nothing produces
the value:

| consumer | what it does with alignment | state |
|---|---|---|
| `Q.ONSET_COLUMN` | measures cross-staff simultaneity — **1,483 real instants against a phase-shuffled null's 2,409** | built; consumed by INFER rule 1 |
| the groups layer | `unanimous` / `majority` / `split` across staves and systems | built |
| `Verdict.correlated` | partitions witnesses by whether their provenance sets intersect | built |
| INFER | the one stage licensed to weigh sideways evidence | built, `OMR_INFER` |

Sean's *"the same unrecognizable blob on every system at bar 51"* is an
onset-column question in every respect except that the rows do not exist.

⚠️⚠️ **AND NOTHING MAY BE FILTERED AT THE GATHER SITE, INCLUDING STAFF
RESIDUE.** Sean, 2026-09-17: *"even staff residue should go through the process
and hopefully our rules and measurements will determine at the appropriate
stage that it is just that - staff residue."*

A threshold applied in GATHER is a DECISION taken in the wrong stage, and it is
the only kind that is irreversible: **a row that was never created cannot be
reconsidered by any later stage.** Residue, barlines, stems and speckle are not
false rows — they are correctly gathered ink that a later decision should NAME.
So the deliverable is the COMPOSITION of the population, never a rate reached
by removing things, and *"what is this ink?"* becomes an ADJUDICATE question
with its own evidence and its own recorded abstention.

⚠️ **The discriminator is probably ALIGNMENT, which is already the measurement.**
Staff residue aligns with the STAFF LINES — horizontal, at a line's own y,
running the staff's width. A printed mark aligns ACROSS STAVES at a column —
vertical, one x, several staves at once. Different geometries, so the analysis
that shows blobs are worth having should also show residue separating out.
**If it does not separate, that is a more important finding than the feature.**

⚠️ What this does NOT establish: nobody has measured how much ink a raster
subtraction would actually recover on a real page, or what it would cost in
false rows. The 2-of-17 figure says the detection record cannot answer; it does
not say the raster can.



Each of these is a **judgement**, hand-written, with its evidence. They are
here because the derived half structurally cannot reach them.

### 3.1 SHAPE — the record has no range, and three open items are all this
`record.Kind` is `document > page > system > staff > cell > glyph`: a hierarchy
of **places**, with nothing that spans. Span-shaped occurrences across the
1,745 committed encodings: slur 268,888 · tied 178,597 · tuplet 83,570 · wedge
50,823 · dashes 2,709 · wavy-line 1,647 · ending 558 · octave-shift 438 —
**587,590 total**.

⚠️ **NOT a claim that spans are unhandled.** They are handled, by filing ink on
an endpoint and pairing it later. The claim is about *where that work lives*:
every pairing rule is in the exporter or in `transcribe`, never a fact the
record can state. That is why the tie-chain work concluded *"a chain is a fact
about a PART and EXPORT cannot write a record row"* and `Q.TIE_LINK` was scoped
and deliberately not built. **Three separate open items in CLAUDE.md are this
one missing shape** — the tie chain, the arc chain, and the in-bar accidental
(*an accidental is SCOPE, not a mark: it holds to the barline*).

### 3.2 INSTRUMENT — the class-space audit reads 146 of 208 classes
`gather_coverage._detector_classes()` reads `deepscores_classes.py` (146 names,
its own header calling itself a *"~135 class"* snapshot) under a docstring
reading *"The 208-class space"*. The real vocabulary is committed one directory
over, and `class_aliases.vocabulary()` already reads it.

```bash
python3 -c "from tools.omr.training.deepscores_classes import DEEPSCORES_V2_CLASSES as C; print(len(C))"  # 146
python3 -c "from tools.omr import class_aliases as A; print(len(A.vocabulary()))"                         # 208
```

**Cost, measured: five families invisible to it** — `arpeggio`, `articulation`,
`leger`, `numeral`, `tuple` — exactly the coarse block at ids 136-207.
⚠️⚠️ `class_space_coverage`'s `__UNMAPPED__` branch, whose docstring promises a
wider class space will be *"a broken build rather than a silent blind spot"*,
**has never fired, because the wider class space never reached it.** Not a
behaviour bug — nothing but the report reads it — but the case-(a) list has
understated itself by five families for its whole life, and `numeral` is the
family carrying printed measure numbers and rehearsal marks.

### 3.3 ARCHITECTURE — EVALUATE cannot declare what it reads
ADJUDICATE declares `wants`; INFER declares `reads`; **EVALUATE declares only
`cause` and `effect`.** So a consequence can read a quantity it never declares,
and no instrument can check it — `inventory --check`'s inert-declaration test
and `wiring`'s FRAME question both work off a declaration that does not exist
here. This is why the EVALUATE column of every table in this audit is the
weakest one.

### 3.4 ARCHITECTURE — a saved record cannot replay through the fixpoint guard
`Verdict.single_pass_revision` is declared (`record.py:847`), **READ by the
fixpoint guard** (4 uses), and absent from `Verdict.to_json`. Reported
independently by `wiring` and by the INFER session. **Deliberately not fixed:**
adding a key to `to_json` changes every record in the tree, so every
byte-identity control over a record would report a difference that is not the
change under test.

### 3.5 VOCABULARY — the system bracket, already being paid for
`bracket` is not in the 208-class space and no CV rung reads one; `<part-group>`
appears 2,457 times and group symbols 1,038 times in the encodings.
**`OMR_BRACKET_COLUMNS` is a shipped, measured workaround for a vocabulary gap**
— the only finding in this register that is already paying for itself, and the
model for what "fixing" a VOCABULARY gap can look like without a detector.

### 3.6 REACH — the staged pipeline can receive neither a roster nor a dossier
`no_producer` reports `dossier` threaded through four layers with no supplier:
`--dossier` exists on `tools.omr.transcribe` and **not** on
`staged/__main__.py`, so `Q.DOSSIER_FACT` abstains on every staged run ever
made. The roster half was repaired 2026-09-15; the dossier half is open.

⚠️ This one matters more than its size suggests, because a dossier is the
project's only arbiter that **does not fall silent when the raster is bad** —
*if you want a second witness that does not fall silent exactly when it is
needed, it must not come off the same raster.*

---

## 4. What would change the ranking

Stated in advance, so the ranking cannot be fitted to what was found.

1. **The plumbing matrix finishing.** Until every connection has been exercised
   by a fixture that prints the relevant ink, a `NOT_EXERCISED` edge and a dead
   one look identical.
2. **A REACH count.** If the bottleneck is the detector rather than the wiring,
   most of this register is downstream of a problem none of it names.
3. **A second publisher.** Every figure in the derived half is from engraved
   LilyPond fixtures; the judged half is from encodings, not pages. An encoding
   truth is not a page truth.
4. **Sean's cleanup count.** The plan's own instrument for *what should we fix
   next* — and the only one of these four that measures the human's work
   rather than the machine's.
